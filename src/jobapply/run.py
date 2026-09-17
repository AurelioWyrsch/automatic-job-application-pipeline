"""`jobapply run`: drive one Application through every step, pausing at each human checkpoint.

The state is derived from the files in the Application folder, so quitting at
any pause and running the command again resumes at the same place.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import typer

from .application import Application
from .errors import JobapplyError
from .posting import Ask, Download
from .workspace import Workspace


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


def choose_application(ws: Workspace, ask: Ask, download: Download | None = None) -> Application:
    """Pick an open Application by number, or start a new one from a Posting URL."""
    from .posting import new_application

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
    while True:
        posting_url = ask("Posting URL (job description)", None)
        existing = Application.find_by_posting_url(ws, posting_url)
        if existing is None:
            break
        if ask(f"Continue {existing.slug} instead? (y/n)", "y").lower().startswith("y"):
            return existing
    typer.echo("Fetching the posting …")
    app = new_application(ws, posting_url, ask, download=download)
    typer.echo(f"Created {app.folder}")
    return app


def run(app: Application) -> None:
    from .forms import form_session
    from .mail import open_mail_client, write_email
    from .posting import fetch_posting
    from .render import render_application

    show_preflight(app)
    last_blocker: Optional[str] = None
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
            typer.echo("letter — your turn: complete the posting and write the letter")
            if last_blocker == "letter":
                typer.secho(f"  still not ready: {steps['letter'].detail}", fg=typer.colors.YELLOW)
            typer.echo(f"  {app.posting_path}")
            typer.echo(f"  {app.cover_letter_path}")
            typer.echo(f"  With your agent: /extract-posting {app.slug}  then  /draft-cover-letter {app.slug}")
            answer = _prompt("Enter to re-check, e to open the letter in your editor, d when the letter is done, q to pause.",
                             "Enter/e/d/q", "c")
            if answer == "q":
                return
            if answer == "e":
                open_for_editing(app, "letter")
                continue
            if answer == "d":
                app.mark_letter_done()
            last_blocker = "letter"
            continue

        if not steps["render"].done:
            typer.echo("render: producing the PDFs …")
            show_preflight(app)
            for kind, path in render_application(app).items():
                typer.echo(f"  {kind:13s} {path.name}")
            answer = _prompt("Open the PDFs to check them?", "y/n/q", "y")
            if answer == "q":
                return
            if answer == "y":
                for path in app.document_paths().values():
                    _open(path)
                answer = _prompt("PDFs OK? Enter to continue, r to re-render after edits, q to pause.", "Enter/r/q", "c")
                if answer == "q":
                    return
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
                    return
                if answer == "y":
                    open_mail_client(email)
                continue
            typer.secho("all steps done — the email is composed; attaching the Dossier and sending is yours.",
                        fg=typer.colors.GREEN)
            return

        if not steps["fill"].done:
            start = "fill" if steps["scan"].done else "scan"
            typer.echo(f"{start}: opening the form in Chrome …")
            if start == "scan":
                typer.echo(f"  After the scan, fix unmatched fields in {app.field_map_path.name} (or the map-fields skill: {app.slug}), then choose [f].")
            form_session(app, start_with=start)
            if not any(s.done for s in app.steps() if s.name == "fill"):
                answer = _prompt("Form not filled yet. Enter to reopen the browser, q to pause.", "Enter/q", "c")
                if answer == "q":
                    return
            continue

        typer.secho("all steps done — the form was filled; submitting is yours.", fg=typer.colors.GREEN)
        return
