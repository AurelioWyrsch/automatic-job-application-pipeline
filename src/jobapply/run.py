"""`jobapply run`: drive one Application through every step, pausing at each human checkpoint.

The state is derived from the files in the Application folder, so quitting at
any pause and running the command again resumes at the same place.
"""

from __future__ import annotations

import sys
from typing import Callable, Optional

import typer

from .application import Application
from .errors import JobapplyError
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


def choose_application(ws: Workspace, ask: Callable[[str, Optional[str]], str]) -> Application:
    """Pick an open Application by number, or create a new one."""
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
    company = ask("Company", None)
    role = ask("Role / job title", None)
    posting_url = ask("Posting URL (job description)", None)
    form_url = ask("Form URL (where you apply)", posting_url)
    language = ask("Language of the documents", ws.default_language)
    app = Application.create(ws, company=company, role=role, language=language,
                             posting_url=posting_url, form_url=form_url)
    typer.echo(f"Created {app.folder}")
    return app


def run(app: Application) -> None:
    from .forms import form_session
    from .posting import fetch_posting
    from .render import render_application

    last_blocker: Optional[str] = None
    while True:
        steps = {s.name: s for s in app.steps()}
        typer.echo("")
        typer.secho(f"── {app.slug}", fg=typer.colors.BLUE)

        if not steps["fetch"].done:
            typer.echo("Step 2/6  fetch: downloading the posting …")
            result = fetch_posting(app)
            typer.echo(f"  snapshot saved; extracted: {', '.join(result.extracted) or 'nothing structured'}")
            continue

        if not steps["letter"].done:
            typer.echo("Step 3/6  your turn: complete the posting and write the letter")
            if last_blocker == "letter":
                typer.secho(f"  still not ready: {steps['letter'].detail}", fg=typer.colors.YELLOW)
            typer.echo(f"  {app.posting_path}")
            typer.echo(f"  {app.cover_letter_path}   (set \"draft\": false when done)")
            typer.echo(f"  With your agent: /extract-posting {app.slug}  then  /draft-cover-letter {app.slug}")
            answer = _prompt("Press Enter when the letter is ready, q to pause here.", "Enter/q", "c")
            if answer == "q":
                return
            last_blocker = "letter"
            continue

        if not steps["render"].done:
            typer.echo("Step 4/6  render: producing the PDFs …")
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

        if not steps["fill"].done:
            start = "fill" if steps["scan"].done else "scan"
            typer.echo(f"Step 5/6  {start}: opening the form in Chrome …")
            if start == "scan":
                typer.echo(f"  After the scan, fix unmatched fields in {app.field_map_path.name} (or the map-fields skill: {app.slug}), then choose [f].")
            form_session(app, start_with=start)
            if not any(s.done for s in app.steps() if s.name == "fill"):
                answer = _prompt("Form not filled yet. Enter to reopen the browser, q to pause.", "Enter/q", "c")
                if answer == "q":
                    return
            continue

        typer.secho("Step 6/6  all steps done — the form was filled; submitting is yours.", fg=typer.colors.GREEN)
        return
