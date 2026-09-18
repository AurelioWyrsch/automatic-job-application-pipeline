"""jobapply command line.

Every verb is one checkpointed step; the human does everything in between and
always presses submit themselves.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from . import __version__
from .application import Application
from .errors import JobapplyError
from .workspace import Workspace

app = typer.Typer(
    help="Job-application pipeline: profile + templates -> PDFs -> pre-filled web forms. You press submit.",
    no_args_is_help=True,
    rich_markup_mode=None,
)

WorkspaceOpt = typer.Option(
    None, "--workspace", "-w", help="Workspace directory (default: $JOBAPPLY_WORKSPACE or ./workspace)."
)


def _ws(path: Optional[Path]) -> Workspace:
    return Workspace.locate(path)


def _ask(label: str, default: Optional[str] = None) -> str:
    while True:
        value = typer.prompt(label, default=default) if default else typer.prompt(label)
        if value and value.strip():
            return value.strip()


def _fail(exc: Exception) -> None:
    typer.secho(f"error: {exc}", fg=typer.colors.RED, err=True)
    raise typer.Exit(1)


@app.callback()
def _main(version: bool = typer.Option(False, "--version", help="Show version and exit.")):
    if version:
        typer.echo(f"jobapply {__version__}")
        raise typer.Exit()


@app.command()
def init(
    directory: Path = typer.Argument(Path("workspace"), help="Where to create the workspace."),
):
    """Create a new workspace with example data to edit."""
    try:
        ws = Workspace.init(directory)
    except JobapplyError as exc:
        _fail(exc)
    typer.echo(f"Workspace created at {ws.root}")
    typer.echo("Next: edit the files in profile/ and cover-letter-fixed.json, put PDFs into attachments/ and list them in attachments/manifest.json — or run the setup-workspace skill.")


@app.command()
def new(
    posting_url: Optional[str] = typer.Argument(None, help="URL of the Posting (job description)."),
    company: Optional[str] = typer.Option(None, "--company", "-c", help="Company name (overrides what the page says)."),
    role: Optional[str] = typer.Option(None, "--role", "-r", help="Role / job title (overrides what the page says)."),
    form_url: Optional[str] = typer.Option(None, "--form", "-f", help="URL of the Form, or mailto:<address> when applying by email (overrides the page's apply link)."),
    language: Optional[str] = typer.Option(None, "--lang", "-l", help="Language code (default: default_language in config.json)."),
    workspace: Optional[Path] = WorkspaceOpt,
):
    """Create an Application from a Posting URL: fetches the page, names the folder from what it
    says, saves the Snapshot and has the unattended Operator complete posting.json. Asks nothing."""
    from .posting import new_application
    from .run import extract_posting

    try:
        ws = _ws(workspace)
        posting_url = posting_url or _ask("Posting URL (job description)")
        typer.echo("Fetching the posting …")
        application = new_application(
            ws, posting_url, company=company, role=role, form_url=form_url, language=language,
        )
        typer.echo(f"Created {application.folder} (snapshot saved)")
        extract_posting(application)
    except JobapplyError as exc:
        _fail(exc)
    typer.echo(f"Next: jobapply run {application.slug}")


@app.command()
def fetch(
    ref: str = typer.Argument(..., help="Application slug (or unique part of it)."),
    workspace: Optional[Path] = WorkspaceOpt,
):
    """Download the Posting, save a Snapshot and extract what it can into posting.json."""
    from .posting import fetch_posting

    try:
        application = Application.find(_ws(workspace), ref)
        result = fetch_posting(application)
    except JobapplyError as exc:
        _fail(exc)
    typer.echo(f"Snapshot: {application.snapshot_html.name}, {application.snapshot_md.name}")
    if result.extracted:
        typer.echo(f"Extracted from JSON-LD: {', '.join(result.extracted)}")
    else:
        typer.echo("No structured JobPosting data on the page; posting.json left for you to complete.")
    typer.echo(f"Next: complete {application.posting_path.name} and write {application.cover_letter_path.name} "
               f"(by hand or with the extract-posting / draft-cover-letter skills), then: jobapply render {application.slug}")


@app.command()
def render(
    ref: str = typer.Argument(..., help="Application slug (or unique part of it)."),
    only: Optional[str] = typer.Option(None, "--only", help="Render only: cv | cover_letter | merged (the Dossier)"),
    keep_html: bool = typer.Option(False, "--keep-html", help="Also write the intermediate HTML into out/."),
    workspace: Optional[Path] = WorkspaceOpt,
):
    """Render CV, cover letter and the Dossier (one PDF: letter, CV, attachments) into the Application's out/ folder."""
    from .render import render_application
    from .run import show_preflight

    if only not in (None, "cv", "cover_letter", "merged"):
        _fail(JobapplyError("--only must be cv, cover_letter or merged"))
    try:
        application = Application.find(_ws(workspace), ref)
        show_preflight(application)
        produced = render_application(application, only=only, keep_html=keep_html)
    except JobapplyError as exc:
        _fail(exc)
    for kind, path in produced.items():
        typer.echo(f"{kind:13s} {path}")
    nxt = "email" if application.applies_by_email else "scan"
    typer.echo(f"Next: check the PDFs, then: jobapply {nxt} {application.slug}")


@app.command()
def scan(
    ref: str = typer.Argument(..., help="Application slug (or unique part of it)."),
    workspace: Optional[Path] = WorkspaceOpt,
):
    """Open the Form in the browser (with your login) and write the Field Map (form-fields.json); `check` does it unattended."""
    from .forms import form_session

    try:
        application = Application.find(_ws(workspace), ref)
        form_session(application, start_with="scan")
    except JobapplyError as exc:
        _fail(exc)


@app.command()
def fill(
    ref: str = typer.Argument(..., help="Application slug (or unique part of it)."),
    workspace: Optional[Path] = WorkspaceOpt,
):
    """Open the Form and fill the mapped fields. Never submits."""
    from .forms import form_session

    try:
        application = Application.find(_ws(workspace), ref)
        form_session(application, start_with="fill")
    except JobapplyError as exc:
        _fail(exc)


@app.command()
def email(
    ref: str = typer.Argument(..., help="Application slug (or unique part of it)."),
    send: bool = typer.Option(True, "--open/--no-open", help="Hand the message to your mail client."),
    workspace: Optional[Path] = WorkspaceOpt,
):
    """Compose the application email (form_url is a mailto:) into email.md and open it in your
    mail client. You attach the Dossier and press send."""
    from .mail import open_mail_client, write_email

    try:
        application = Application.find(_ws(workspace), ref)
        message = write_email(application)
        if send:
            open_mail_client(message)
    except JobapplyError as exc:
        _fail(exc)
    typer.echo(message.as_markdown())
    typer.echo(f"Saved {application.email_path}. Attach the Dossier, check the text, send.")


@app.command()
def run(
    ref: Optional[str] = typer.Argument(None, help="Application slug, or a Posting URL to start from; omit to pick one."),
    workspace: Optional[Path] = WorkspaceOpt,
):
    """Walk an Application through every step, pausing only where you must act. Re-run to resume."""
    from .run import choose_application, is_url, run as run_pipeline, start_application

    try:
        ws = _ws(workspace)
        if ref and is_url(ref):
            application = start_application(ws, ref)
        elif ref:
            application = Application.find(ws, ref)
        else:
            application = choose_application(ws, _ask)
        run_pipeline(application)
    except JobapplyError as exc:
        _fail(exc)


@app.command()
def check(
    ref: str = typer.Argument(..., help="Application slug (or unique part of it)."),
    workspace: Optional[Path] = WorkspaceOpt,
):
    """The Form Check: visit the Form without your login, classify it Open or Gated and, for an
    Open Form, write the Field Map (form-fields.json), mapping leftovers with the unattended Operator."""
    from .operator import reset_terminal
    from .run import FormCheckJob

    reset_terminal()
    try:
        application = Application.find(_ws(workspace), ref)
        if application.applies_by_email:
            raise JobapplyError(f"{application.slug} applies by email; there is no Form to check.")
        job = FormCheckJob(application)
        job.run()
    except JobapplyError as exc:
        _fail(exc)
    for line in job.summary_lines():
        typer.echo(line)
    if job.error:
        raise typer.Exit(code=1)
    typer.echo(f"Field map: {application.field_map_path}")


@app.command()
def login(
    url: str = typer.Argument("https://www.linkedin.com/login", help="Login page to open; default LinkedIn."),
    workspace: Optional[Path] = WorkspaceOpt,
):
    """Open the workspace's browser so you can log in to a site whose postings or forms need it.
    The session is kept in .browser/; the tool never sees the credentials."""
    from .forms import login_session

    try:
        login_session(_ws(workspace), url)
    except JobapplyError as exc:
        _fail(exc)


@app.command("open")
def open_cmd(
    ref: str = typer.Argument(..., help="Application slug (or unique part of it)."),
    what: str = typer.Argument("letter", help="letter | posting | fields | email | folder"),
    workspace: Optional[Path] = WorkspaceOpt,
):
    """Open one of the Application's files in your editor (config.json "editor", e.g. "code -r")."""
    from .run import open_for_editing

    try:
        path = open_for_editing(Application.find(_ws(workspace), ref), what)
    except JobapplyError as exc:
        _fail(exc)
    typer.echo(f"Opened {path}")


@app.command()
def back(
    ref: str = typer.Argument(..., help="Application slug (or unique part of it)."),
    workspace: Optional[Path] = WorkspaceOpt,
):
    """Undo the last completed step (fill -> scan | email -> render -> letter -> fetch) so `run` repeats it."""
    try:
        application = Application.find(_ws(workspace), ref)
        step = application.undo_last_step()
    except JobapplyError as exc:
        _fail(exc)
    if step is None:
        typer.echo("Nothing to undo: only `new` is done.")
        return
    explanation = {
        "email": "removed email.md; the email will be composed again",
        "fill": "cleared the filled marker; the form will be filled again",
        "scan": "removed form-fields.json; the Form will be checked again",
        "render": "removed the PDFs in out/; they will be rendered again",
        "letter": 'set "draft": true in cover-letter.json; edit it and set draft to false again',
        "fetch": "removed the snapshot; the posting will be fetched again (posting.json kept)",
    }[step]
    typer.echo(f"Undid {step}: {explanation}.")
    typer.echo(f"Continue with: jobapply run {application.slug}")


@app.command()
def status(
    ref: Optional[str] = typer.Argument(None, help="Application slug; omit for all."),
    workspace: Optional[Path] = WorkspaceOpt,
):
    """Show which steps each Application has completed, and what convention warns about."""
    from .run import show_preflight

    try:
        ws = _ws(workspace)
        apps = [Application.find(ws, ref)] if ref else [Application(ws, f) for f in Application.list_folders(ws)]
    except JobapplyError as exc:
        _fail(exc)
    if not apps:
        typer.echo("No applications yet. Create one with: jobapply new ...")
        return
    for application in apps:
        typer.secho(application.slug, bold=True)
        typer.echo(f"  {application.data.get('company')} — {application.data.get('role')} [{application.language_code}]")
        for step in application.steps():
            mark = "✔" if step.done else "·"
            detail = f"  {step.detail}" if step.detail else ""
            typer.echo(f"  {mark} {step.name:7s}{detail}")
        try:
            show_preflight(application)
        except JobapplyError as exc:
            typer.secho(f"  ! {exc}", fg=typer.colors.YELLOW)


@app.command("list")
def list_cmd(workspace: Optional[Path] = WorkspaceOpt):
    """List Application slugs."""
    try:
        ws = _ws(workspace)
    except JobapplyError as exc:
        _fail(exc)
    for folder in Application.list_folders(ws):
        typer.echo(folder.name)


if __name__ == "__main__":
    app()
