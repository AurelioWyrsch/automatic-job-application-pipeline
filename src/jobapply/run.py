"""`jobapply run`: drive one Application through every step, pausing only where the applicant is needed.

The state is derived from the files in the Application folder, so quitting at
any pause and running the command again resumes at the same place.

The sequence (ADR 0004 amendment): fetch; `extract-posting` with the unattended Operator;
then the Form Check in the background while the interactive Operator runs the letter
interview; render; and for an Open Form the browser opens and fills at once, for a Gated
Form the applicant takes over.
"""

from __future__ import annotations

import sys
import threading
from pathlib import Path
from typing import Callable, Optional

import typer

from .application import Application
from .errors import JobapplyError
from .operator import operator_command, reset_terminal, run_operator, run_unattended
from .posting import Download
from .workspace import Workspace

Ask = Callable[[str, str | None], str]


def _prompt(text: str, choices: str, default: str) -> str:
    typer.secho(f"\n{text}", bold=True)
    typer.echo(f"[{choices}] ", nl=False)
    sys.stdout.flush()
    try:
        line = sys.stdin.readline()
    except KeyboardInterrupt:
        return "q"
    if line == "":  # stdin closed: pause rather than loop on the default
        return "q"
    return line.strip().lower()[:1] or default


def _open(path) -> None:
    import subprocess

    try:
        subprocess.Popen(["xdg-open", str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        typer.echo(f"  open manually: {path}")


def open_for_editing(app: Application, what: str) -> Path:
    """Open one of the Application's files in the applicant's editor; returns the path."""
    import subprocess

    path = app.editable(what)
    command = app.workspace.editor_command() + [str(path)]
    try:
        proc = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    except OSError as exc:
        raise JobapplyError(f"Could not run {' '.join(command)}: {exc}") from exc
    # Editors like `code -r` hand the file to a running window and exit at once; a
    # terminal editor or a failing command is still running or has failed by now.
    try:
        _, stderr = proc.communicate(timeout=3)
    except subprocess.TimeoutExpired:
        return path
    if proc.returncode:
        raise JobapplyError(f"{' '.join(command)} failed: {(stderr or '').strip() or f'exit code {proc.returncode}'}\n"
                            f"Set \"editor\" in {app.workspace.root / 'config.json'} to a command that opens a file, e.g. \"code -r\".")
    return path


def show_preflight(app: Application) -> None:
    """Print what convention has to say: empty Required Fields (which will stop `render`) in red,
    Recommended Fields, a missing contact person and ß in German text in yellow."""
    from .preflight import preflight

    report = preflight(app)
    for line in report.errors:
        typer.secho(f"  ✗ {line}", fg=typer.colors.RED)
    for line in report.warnings:
        typer.secho(f"  ! {line}", fg=typer.colors.YELLOW)


def _progress(app: Application) -> str:
    return "  ".join(("✔ " if s.done else "· ") + s.name for s in app.steps())


# -- starting -----------------------------------------------------------------------


def is_url(ref: str) -> bool:
    return "://" in ref or ref.lower().startswith("mailto:")


def start_application(ws: Workspace, posting_url: str, download: Download | None = None) -> Application:
    """The Application for a Posting URL: the existing one, or a new one fetched and named
    from the page without a single question."""
    from .posting import new_application

    existing = Application.find_by_posting_url(ws, posting_url)
    if existing is not None:
        typer.echo(f"Continuing {existing.slug} (same Posting)")
        return existing
    typer.echo("Fetching the posting …")
    app = new_application(ws, posting_url, download=download)
    typer.echo(f"Created {app.folder}")
    return app


def choose_application(ws: Workspace, ask: Ask, download: Download | None = None) -> Application:
    """Pick an open Application by number, or start a new one from a Posting URL."""
    folders = Application.list_folders(ws)
    apps = [Application(ws, f) for f in folders]
    open_apps = [a for a in apps if not all(s.done for s in a.steps())]
    if open_apps:
        typer.secho("Open applications:", bold=True)
        for i, a in enumerate(open_apps, 1):
            done = [s.name for s in a.steps() if s.done]
            typer.echo(f"  {i}. {a.slug}   (done: {', '.join(done)})")
        typer.echo("  n. new application")
        while True:
            answer = ask("Continue which?", "n").strip().lower()
            if answer == "n":
                break
            if answer.isdigit() and 1 <= int(answer) <= len(open_apps):
                return open_apps[int(answer) - 1]
    typer.secho("New application", bold=True)
    posting_url = ask("Posting URL (job description)", None)
    return start_application(ws, posting_url, download=download)


# -- the unattended parts ------------------------------------------------------------


def extract_posting(app: Application) -> bool:
    """`extract-posting` with the unattended Operator, output straight to the terminal.
    Returns False when that mode is not set up."""
    typer.echo("extract: the Operator reads the posting …")
    result = run_unattended(app, "extract-posting")
    if result is None:
        typer.echo("  no unattended Operator (operator_unattended in config.json)")
        return False
    code, _ = result
    if code:
        typer.secho(f"  the Operator exited with code {code}", fg=typer.colors.YELLOW)
    app.reload()
    return True


class FormCheckJob(threading.Thread):
    """The Form Check plus, for an Open Form with unmatched fields, `map-fields` unattended.
    Runs in the background while the interview owns the terminal; its output is kept for
    `summary_lines`, never printed while it runs."""

    def __init__(self, app: Application, *, check=None, mapper=None):
        super().__init__(daemon=True, name=f"form-check {app.slug}")
        self.app = app
        self._check = check
        self._mapper = mapper or run_unattended
        self.result = None
        self.error = ""
        self.operator_note = ""
        self.operator_output = ""
        self.operator_code: int | None = None

    def run(self) -> None:
        from .forms import form_check

        try:
            self.result = (self._check or form_check)(self.app)
            if self.result.gated or not self.result.unmatched:
                return
            outcome = self._mapper(self.app, "map-fields", capture=True)
            if outcome is None:
                self.operator_note = "no unattended Operator: map the rest by hand or with the map-fields skill"
                return
            self.operator_code, self.operator_output = outcome
            self.result = self._recount()
        except Exception as exc:  # the interview must not die with the background job
            self.error = f"{type(exc).__name__}: {exc}"

    def _recount(self):
        from .forms import FormCheck

        fields = [f for page in self.app.field_map().get("pages", []) for f in page.get("fields", [])]
        return FormCheck(url=self.result.url, fields=len(fields), matched=sum(1 for f in fields if f.get("value")))

    def summary_lines(self) -> list[str]:
        if self.error:
            return [f"Form Check failed: {self.error}"]
        lines = [self.result.summary()] if self.result else []
        if self.operator_note:
            lines.append(self.operator_note)
        if self.operator_code:
            tail = [l for l in self.operator_output.splitlines() if l.strip()][-5:]
            lines.append(f"map-fields exited with code {self.operator_code}")
            lines += ["  " + l for l in tail]
        return lines


def start_form_check(app: Application, job: FormCheckJob | None, factory=FormCheckJob) -> FormCheckJob | None:
    """Start the Form Check in the background when the Application has a web Form nobody looked at yet."""
    if job is not None or app.applies_by_email or app.form_checked:
        return job
    typer.echo("check: looking at the Form in the background …")
    job = factory(app)
    job.start()
    return job


def finish_form_check(job: FormCheckJob | None) -> None:
    """Wait for the Form Check (never kill it) and print what it found."""
    if job is None:
        return
    if job.is_alive():
        typer.echo("  waiting for the Form Check …")
        job.join()
    for line in job.summary_lines():
        typer.echo(f"  {line}")


# -- the loop ---------------------------------------------------------------------------


def run(app: Application, *, check_factory=FormCheckJob) -> None:
    job: FormCheckJob | None = None
    reset_terminal()  # a killed Operator session leaves modes on that make our prompts unreadable
    try:
        job = _run(app, check_factory)
    finally:
        finish_form_check(job)


def _letter_interview(app: Application) -> None:
    """The interactive Operator: `extract-posting` first when nobody extracted the posting and
    the unattended mode is off, then `draft-cover-letter`."""
    if not app.posting_extracted() and operator_command(app.workspace, "extract-posting", app.slug, unattended=True) is None:
        typer.echo("  starting the Operator for extract-posting … (quit it to come back here)")
        run_operator(app, "extract-posting")
        app.reload()
    typer.echo("  starting the Operator for draft-cover-letter … (quit it to come back here)")
    code = run_operator(app, "draft-cover-letter")
    if code:
        typer.secho(f"  the Operator exited with code {code}", fg=typer.colors.YELLOW)
    app.reload()


def _run(app: Application, check_factory) -> FormCheckJob | None:
    from .forms import fields_left_to_applicant, form_session
    from .mail import open_mail_client, write_email
    from .posting import fetch_posting
    from .render import render_application

    show_preflight(app)
    last_blocker: Optional[str] = None
    job: FormCheckJob | None = None
    auto_started = False
    while True:
        steps = {s.name: s for s in app.steps()}
        typer.echo("")
        typer.secho(f"── {app.slug}", fg=typer.colors.BLUE)
        typer.echo(f"   {_progress(app)}")

        if not steps["fetch"].done:
            typer.echo("fetch: downloading the posting …")
            result = fetch_posting(app)
            typer.echo(f"  snapshot saved; extracted: {', '.join(result.extracted) or 'nothing structured'}")
            continue

        if not steps["letter"].done:
            if app.letter_untouched() and not app.posting_extracted():
                extract_posting(app)
            job = start_form_check(app, job, check_factory)
            interactive = operator_command(app.workspace, "draft-cover-letter", app.slug)
            if interactive is not None and app.letter_untouched() and not auto_started:
                auto_started = True
                _letter_interview(app)
                continue
            typer.echo("letter — your turn: complete the posting and write the letter")
            if last_blocker == "letter":
                typer.secho(f"  still not ready: {steps['letter'].detail}", fg=typer.colors.YELLOW)
            typer.echo(f"  {app.posting_path}")
            typer.echo(f"  {app.cover_letter_path}")
            if interactive is None:
                typer.echo(f"  With your agent: /extract-posting {app.slug}  then  /draft-cover-letter {app.slug}")
                answer = _prompt("Enter to re-check, e to open the letter in your editor, d when the letter is done, q to pause.",
                                 "Enter/e/d/q", "c")
            else:
                answer = _prompt("a to run the Operator (draft-cover-letter), Enter to re-check, "
                                 "e to open the letter in your editor, d when the letter is done, q to pause.",
                                 "a/Enter/e/d/q", "c")
            if answer == "q":
                return job
            if answer == "a" and interactive is not None:
                _letter_interview(app)
                continue
            if answer == "e":
                open_for_editing(app, "letter")
                continue
            if answer == "d":
                app.mark_letter_done()
            last_blocker = "letter"
            continue

        if job is not None:
            finish_form_check(job)
            job = None

        if not steps["render"].done:
            typer.echo("render: producing the PDFs …")
            show_preflight(app)
            for kind, path in render_application(app).items():
                typer.echo(f"  {kind:13s} {path.name}")
            answer = _prompt("Open the PDFs to check them?", "y/n/q", "y")
            if answer == "q":
                return None
            if answer == "y":
                for path in app.document_paths().values():
                    _open(path)
                answer = _prompt("PDFs OK? Enter to continue, r to re-render after edits, q to pause.", "Enter/r/q", "c")
                if answer == "q":
                    return None
                if answer == "r":
                    for path in app.document_paths().values():
                        path.unlink(missing_ok=True)
            continue

        if app.applies_by_email:
            if not steps["email"].done:
                typer.echo(f"email: composing the message to {app.application_email} …")
                email = write_email(app)
                typer.echo(f"  saved {app.email_path.name}\n")
                typer.echo("  " + email.as_markdown().replace("\n", "\n  "))
                answer = _prompt("Open it in your mail client? (attach the Dossier yourself, then send)", "y/n/q", "y")
                if answer == "q":
                    return None
                if answer == "y":
                    open_mail_client(email)
                continue
            typer.secho("all steps done — the email is composed; attaching the Dossier and sending is yours.",
                        fg=typer.colors.GREEN)
            return None

        if not steps["fill"].done:
            if not app.form_checked:
                typer.echo("check: looking at the Form …")
                job = check_factory(app)
                job.start()
                finish_form_check(job)
                job = None
                continue
            if app.form_gated:
                typer.echo(f"fill — your turn: the Form is gated ({app.field_map().get('reason') or 'login'}).")
                typer.echo(f"  {app.data.get('form_url')}")
                for path in app.document_paths().values():
                    typer.echo(f"  {path}")
                answer = _prompt("f to open the Form in the tool's browser (log in, then [s] scan and [f] fill), q to stop here.",
                                 "f/q", "q")
                if answer == "f":
                    form_session(app, start_with="scan")
                    continue
                return None
            left = fields_left_to_applicant(app)
            if left:
                typer.echo("fill: these fields are yours to answer in the browser:")
                for line in left:
                    typer.echo(f"  · {line}")
            typer.echo("fill: opening the form in Chrome and filling it …")
            form_session(app, start_with="fill", wait_for_page=False)
            if not any(s.done for s in app.steps() if s.name == "fill"):
                answer = _prompt("Form not filled yet. Enter to reopen the browser, q to pause.", "Enter/q", "c")
                if answer == "q":
                    return None
            continue

        typer.secho("all steps done — the form was filled; submitting is yours.", fg=typer.colors.GREEN)
        return None
