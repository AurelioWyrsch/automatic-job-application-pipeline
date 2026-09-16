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
    typer.echo("Next: edit profile.json, cover-letter.<lang>.json, put PDFs into attachments/ and list them in attachments/manifest.json.")


@app.command()
def new(
    company: Optional[str] = typer.Option(None, "--company", "-c", help="Company name."),
    role: Optional[str] = typer.Option(None, "--role", "-r", help="Role / job title."),
    posting_url: Optional[str] = typer.Option(None, "--posting", "-p", help="URL of the Posting (job description)."),
    form_url: Optional[str] = typer.Option(None, "--form", "-f", help="URL of the Form (where you apply)."),
    language: Optional[str] = typer.Option(None, "--lang", "-l", help="Language code (default from config)."),
    workspace: Optional[Path] = WorkspaceOpt,
):
    """Create an Application. Asks for anything not given as an option."""
    try:
        ws = _ws(workspace)
        company = company or _ask("Company")
        role = role or _ask("Role / job title")
        posting_url = posting_url or _ask("Posting URL (job description)")
        form_url = form_url or _ask("Form URL (where you apply)", default=posting_url)
        language = language or _ask("Language of the documents", default=ws.default_language)
        application = Application.create(
            ws, company=company, role=role, language=language,
            posting_url=posting_url, form_url=form_url,
        )
    except JobapplyError as exc:
        _fail(exc)
    typer.echo(f"Created {application.folder}")
    typer.echo(f"Next: jobapply fetch {application.slug}")


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
               f"(by hand or with /extract-posting and /draft-cover-letter), then: jobapply render {application.slug}")


@app.command()
def render(
    ref: str = typer.Argument(..., help="Application slug (or unique part of it)."),
    only: Optional[str] = typer.Option(None, "--only", help="Render only: cv | cover_letter | merged"),
    keep_html: bool = typer.Option(False, "--keep-html", help="Also write the intermediate HTML into out/."),
    workspace: Optional[Path] = WorkspaceOpt,
):
    """Render CV, cover letter and the merged PDF into the Application's out/ folder."""
    from .render import render_application

    if only not in (None, "cv", "cover_letter", "merged"):
        _fail(JobapplyError("--only must be cv, cover_letter or merged"))
    try:
        application = Application.find(_ws(workspace), ref)
        produced = render_application(application, only=only, keep_html=keep_html)
    except JobapplyError as exc:
        _fail(exc)
    for kind, path in produced.items():
        typer.echo(f"{kind:13s} {path}")
    typer.echo(f"Next: check the PDFs, then: jobapply scan {application.slug}")


@app.command()
def scan(
    ref: str = typer.Argument(..., help="Application slug (or unique part of it)."),
    workspace: Optional[Path] = WorkspaceOpt,
):
    """Open the Form in the browser and write the Field Map (form-fields.json)."""
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
def run(
    ref: Optional[str] = typer.Argument(None, help="Application slug; omit to pick one or start a new one."),
    workspace: Optional[Path] = WorkspaceOpt,
):
    """Walk an Application through every step, pausing wherever you need to act. Re-run to resume."""
    from .run import choose_application, run as run_pipeline

    try:
        ws = _ws(workspace)
        application = Application.find(ws, ref) if ref else choose_application(ws, _ask)
        run_pipeline(application)
    except JobapplyError as exc:
        _fail(exc)


@app.command()
def status(
    ref: Optional[str] = typer.Argument(None, help="Application slug; omit for all."),
    workspace: Optional[Path] = WorkspaceOpt,
):
    """Show which steps each Application has completed."""
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
