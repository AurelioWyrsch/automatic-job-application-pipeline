"""Scan a Form page into the Field Map and fill it back. Never clicks submit.

The browser is real Chrome with a persistent profile owned by the Workspace, so
logins survive between runs. Both ``scan`` and ``fill`` act on whatever page is
currently showing, so multi-page forms are handled one page at a time.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urldefrag

import typer

from .application import COVER_LETTER_WAIVED, Application
from .workspace import Workspace
from .errors import JobapplyError
from .fields_js import DETECT_FIELDS_JS
from .matching import match_field

STORED_FIELD_KEYS = (
    "selector", "type", "label", "hints", "placeholder", "name", "id",
    "autocomplete", "required", "multiple", "accept", "options",
)


# -- scanning ---------------------------------------------------------------------


def scan_page(page, app: Application) -> dict[str, Any]:
    synonyms = app.workspace.synonyms()
    lang = app.language_code
    fields: list[dict[str, Any]] = []
    for frame in page.frames:
        try:
            result = frame.evaluate(DETECT_FIELDS_JS)
        except Exception:  # cross-origin frames may refuse; skip them
            continue
        frame_key = "" if frame == page.main_frame else (frame.name or frame.url)
        for raw in result["fields"]:
            field = {k: raw.get(k) for k in STORED_FIELD_KEYS if k in raw}
            field["frame"] = frame_key
            target, reason = match_field(raw, synonyms, lang)
            field["value"] = target
            field["matched_by"] = reason
            fields.append(field)
    return {
        "url": urldefrag(page.url)[0],
        "title": page.title(),
        "scanned_at": _now(),
        "filled_at": None,
        "fields": fields,
    }


def merge_page(field_map: dict[str, Any], new_page: dict[str, Any]) -> dict[str, Any]:
    """Replace the page with the same URL, keeping values the applicant already set."""
    pages = field_map.setdefault("pages", [])
    for i, existing in enumerate(pages):
        if existing.get("url") == new_page["url"]:
            old_values = {(f.get("frame"), f["selector"]): f.get("value") for f in existing.get("fields", [])}
            for field in new_page["fields"]:
                previous = old_values.get((field.get("frame"), field["selector"]))
                if previous:
                    field["value"] = previous
                    field["matched_by"] = "kept from previous scan"
            pages[i] = new_page
            return field_map
    pages.append(new_page)
    return field_map


# -- value resolution ----------------------------------------------------------


class Resolver:
    def __init__(self, app: Application):
        self.app = app
        self.lang = app.language
        self.profile = self.lang.resolve(app.profile(), "profile")
        self.posting = self.lang.resolve(app.posting(), "posting")
        self.docs = app.document_paths()

    def resolve(self, target: str, field: dict[str, Any]) -> str | list[Path] | None:
        """A string to type/select, a list of files to upload, or None if nothing applies."""
        kind, _, arg = target.partition(":")
        if kind == "literal":
            return arg
        if kind == "profile":
            return self._format(self._path(self.profile, arg, "profile.json"), field)
        if kind == "posting":
            return self._format(self._path(self.posting, arg, "posting.json"), field)
        if kind == "document":
            if arg == "cover_letter" and self.app.cover_letter_waived:
                raise JobapplyError(f"{COVER_LETTER_WAIVED}; set this field to null or another document")
            if arg not in self.docs:
                raise JobapplyError(f"Unknown document {arg!r}; use cv, cover_letter or merged")
            path = self.docs[arg]
            if not path.exists():
                raise JobapplyError(f"{path.name} not rendered yet: run `jobapply render`")
            return [path]
        if kind == "attachment":
            return [self.app.workspace.attachment_path(arg)]
        if kind == "attachments":
            files = [self.app.workspace.attachment_path(e["file"]) for e in self.app.selected_attachments()]
            if arg == "all+documents":
                files = [self.docs[k] for k in ("cv", "cover_letter") if k in self.docs] + files
            return files
        raise JobapplyError(f"Unknown value target {target!r} (profile:, posting:, document:, attachment:, attachments:, literal:)")

    @staticmethod
    def _path(data: Any, dotted: str, origin: str) -> Any:
        node = data
        for part in dotted.split("."):
            if isinstance(node, list) and part.isdigit():
                node = node[int(part)]
            elif isinstance(node, dict) and part in node:
                node = node[part]
            else:
                raise JobapplyError(f"{origin} has no value at {dotted!r}")
        return node

    def _format(self, value: Any, field: dict[str, Any]) -> str | None:
        if value is None or value == "":
            return None
        if isinstance(value, (list, dict)):
            raise JobapplyError(f"Cannot type a {type(value).__name__} into a form field: {value!r}")
        text = str(value)
        if field.get("type") == "date":
            return text  # <input type=date> wants ISO
        if _looks_like_iso_date(text):
            return self.lang.short_date(text)
        return text


def _looks_like_iso_date(text: str) -> bool:
    parts = text.split("-")
    return len(parts) == 3 and all(p.isdigit() for p in parts) and len(parts[0]) == 4


# -- filling -----------------------------------------------------------------------


def fill_page(page, app: Application, page_entry: dict[str, Any]) -> dict[str, list[str]]:
    resolver = Resolver(app)
    report: dict[str, list[str]] = {"filled": [], "skipped": [], "failed": []}
    for field in page_entry.get("fields", []):
        title = field.get("label") or field.get("name") or field["selector"]
        target = field.get("value")
        if not target:
            report["skipped"].append(f"{title}  ({field.get('matched_by') or 'no value'})")
            continue
        try:
            value = resolver.resolve(target, field)
            if value is None:
                report["skipped"].append(f"{title}  ({target} is empty)")
                continue
            _apply(page, field, value)
            report["filled"].append(f"{title}  <- {target}")
        except JobapplyError as exc:
            report["failed"].append(f"{title}: {exc}")
        except Exception as exc:  # Playwright errors: keep going, tell the human
            report["failed"].append(f"{title}: {type(exc).__name__}: {str(exc).splitlines()[0]}")
    page_entry["filled_at"] = _now()
    return report


def _locator(page, field: dict[str, Any]):
    frame_key = field.get("frame") or ""
    if frame_key:
        frame = next((f for f in page.frames if f.name == frame_key or f.url == frame_key), None)
        if frame is None:
            raise JobapplyError(f"frame {frame_key!r} not found on this page")
        return frame.locator(field["selector"])
    return page.locator(field["selector"])


def _apply(page, field: dict[str, Any], value: str | list[Path]) -> None:
    kind = field.get("type")
    locator = _locator(page, field)

    if kind == "file":
        if not isinstance(value, list):
            raise JobapplyError("a file input needs document:/attachment:/attachments: as value")
        files = [str(p) for p in value]
        if len(files) > 1 and not field.get("multiple"):
            raise JobapplyError("input accepts one file; use document:merged or a single attachment:<file>")
        locator.first.set_input_files(files)
        return

    if isinstance(value, list):
        raise JobapplyError("files can only go into a file input")

    if kind == "select":
        option = _pick_option(field.get("options") or [], value)
        locator.first.select_option(value=option["value"]) if option else locator.first.select_option(label=value)
        return
    if kind == "radio":
        option = _pick_option(field.get("options") or [], value)
        if option is None:
            raise JobapplyError(f"no radio option matches {value!r}; options: {[o['label'] for o in field.get('options') or []]}")
        radio = _locator(page, {**field, "selector": f'{field["selector"]}[value="{option["value"]}"]'})
        radio.first.check()
        return
    if kind == "checkbox":
        locator.first.set_checked(value.strip().lower() in ("true", "1", "yes", "ja", "on", "x"))
        return

    locator.first.fill(value)


def _pick_option(options: list[dict[str, str]], wanted: str) -> dict[str, str] | None:
    wanted_l = wanted.strip().lower()
    for opt in options:
        if opt["label"].strip().lower() == wanted_l or opt["value"].strip().lower() == wanted_l:
            return opt
    for opt in options:
        if wanted_l and wanted_l in opt["label"].strip().lower():
            return opt
    return None


# -- the interactive session ---------------------------------------------------------


def persistent_context(playwright, workspace: Workspace, *, headless: bool):
    """Chrome on the Workspace's own profile (`.browser/`), so logins survive between runs and
    the Posting fetch sees the same session as the Form. Without --enable-automation Chrome
    reports navigator.webdriver = false, so sites that park automated browsers on an
    interstitial show the real page."""
    channel = (workspace.config.get("browser") or {}).get("channel", "chrome")
    workspace.browser_dir.mkdir(parents=True, exist_ok=True)
    return playwright.chromium.launch_persistent_context(
        str(workspace.browser_dir), channel=channel, headless=headless, no_viewport=True,
        ignore_default_args=["--enable-automation"],
        args=["--disable-blink-features=AutomationControlled"],
    )


def login_session(workspace: Workspace, url: str) -> None:
    """Open the profile headed so the applicant can log in to a site; the session stays in
    `.browser/`. The tool never sees the credentials."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        context = persistent_context(p, workspace, headless=False)
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(url, wait_until="domcontentloaded")
        typer.echo(f"Browser open at {url}")
        typer.echo("Log in there. The session is kept in the workspace's .browser/ profile; nothing is stored by this tool.")
        _prompt("Press Enter when you are logged in (closes the browser)")
        _close_quietly(context)


def _close_quietly(context) -> None:
    """Close the browser context; one the applicant already closed raises, and that is fine."""
    from playwright.sync_api import Error as PlaywrightError

    try:
        context.close()
    except PlaywrightError as exc:
        if not _browser_was_closed(exc):
            raise


def _browser_was_closed(exc: Exception) -> bool:
    """Playwright's TargetClosedError is not exported in every version; its message is stable."""
    return "has been closed" in str(exc)


def form_session(app: Application, start_with: str) -> None:
    from playwright.sync_api import Error as PlaywrightError, sync_playwright

    url = app.data.get("form_url")
    if not url:
        raise JobapplyError("application.json has no form_url")
    if app.applies_by_email:
        raise JobapplyError(f"{app.slug} applies by email ({app.application_email}); there is no form to {start_with}. "
                            f"Use: jobapply email {app.slug}")
    with sync_playwright() as p:
        context = persistent_context(p, app.workspace, headless=False)
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(url, wait_until="domcontentloaded")
        typer.echo(f"Browser open at {url}")
        typer.echo("Log in and navigate to the form page if needed. Nothing is ever submitted by this tool.")
        _prompt("Press Enter when the page to work on is showing")

        action = start_with
        try:
            while True:
                if action == "scan":
                    _do_scan(page, app)
                elif action == "fill":
                    _do_fill(page, app)
                typer.echo("")
                answer = _prompt("[s] scan this page   [f] fill this page   [q] quit (closes the browser)", default="q")
                action = {"s": "scan", "f": "fill"}.get(answer.strip().lower()[:1], "quit")
                if action == "quit":
                    break
        except PlaywrightError as exc:
            if not _browser_was_closed(exc):
                raise
            # The applicant closed Chrome themselves: that ends the session, it is not an error.
            typer.secho("  the browser was closed", fg=typer.colors.YELLOW)
        _close_quietly(context)


def _do_scan(page, app: Application) -> None:
    entry = scan_page(page, app)
    field_map = merge_page(app.field_map(), entry)
    app.save_field_map(field_map)
    matched = [f for f in entry["fields"] if f.get("value")]
    unmatched = [f for f in entry["fields"] if not f.get("value")]
    typer.echo(f"Scanned {len(entry['fields'])} fields on {entry['url']}")
    for f in matched:
        typer.echo(f"  ✔ {f.get('label') or f.get('name') or f['selector']:40.40s} -> {f['value']}  [{f['matched_by']}]")
    for f in unmatched:
        typer.echo(f"  · {f.get('label') or f.get('name') or f['selector']:40.40s}    ({f['matched_by']})")
    typer.echo(f"Field map written to {app.field_map_path}")
    typer.echo("Edit the \"value\" of unmatched fields (or run the map-fields skill), then choose [f] to fill.")


def _do_fill(page, app: Application) -> None:
    field_map = app.field_map()
    url = urldefrag(page.url)[0]
    entry = next((pg for pg in field_map.get("pages", []) if pg.get("url") == url), None)
    if entry is None:
        typer.echo(f"No scanned page for {url}. Choose [s] to scan it first.")
        return
    report = fill_page(page, app, entry)
    app.save_field_map(field_map)
    for line in report["filled"]:
        typer.echo(f"  ✔ {line}")
    for line in report["skipped"]:
        typer.echo(f"  · skipped {line}")
    for line in report["failed"]:
        typer.secho(f"  ✘ {line}", fg=typer.colors.RED)
    typer.echo(f"Filled {len(report['filled'])}, skipped {len(report['skipped'])}, failed {len(report['failed'])}.")
    typer.secho("Review the form in the browser and press submit yourself.", bold=True)


def _prompt(text: str, default: str = "") -> str:
    typer.echo(text, nl=False)
    typer.echo(" ", nl=False)
    sys.stdout.flush()
    try:
        line = sys.stdin.readline()
    except KeyboardInterrupt:
        return "q"
    return line.strip() or default


def _now() -> str:
    return datetime.now().replace(microsecond=0).isoformat()
