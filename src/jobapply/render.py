"""Render Templates + Profile + Application into PDFs, and merge them with the Attachments."""

from __future__ import annotations

import base64
import mimetypes
import re
from pathlib import Path
from typing import Any

import markdown
from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateNotFound, select_autoescape
from markupsafe import Markup
from pypdf import PdfWriter

from .application import COVER_LETTER_WAIVED, Application
from .errors import JobapplyError
from .i18n import Language
from .preflight import preflight
from .workspace import FIXED_LETTER, Workspace, package_file


def _data_uri(path: Path | None) -> str | None:
    if path is None:
        return None
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"


def _bare_url(url: str) -> str:
    """The address as printed next to its label: no scheme, no www., no trailing slash."""
    return re.sub(r"^https?://(www\.)?", "", url).rstrip("/")


def _markdown(text: str) -> Markup:
    return Markup(markdown.markdown(text, extensions=["sane_lists"]))


def _environment(workspace: Workspace) -> Environment:
    search_path = [str(workspace.root / "templates"), str(package_file("templates"))]
    env = Environment(
        loader=FileSystemLoader(search_path),
        autoescape=select_autoescape(["html"]),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["md"] = _markdown
    env.filters["bare_url"] = _bare_url
    return env


def _register_language(env: Environment, lang: Language) -> None:
    env.filters["month_year"] = lang.month_year
    env.filters["date_range"] = lambda item: lang.date_range(item.get("start", ""), item.get("end"))
    env.filters["long_date"] = lang.long_date


def build_context(app: Application) -> dict[str, Any]:
    """Everything a Template can see, already resolved to the Application's Language."""
    lang = app.language
    ws = app.workspace
    profile = lang.resolve(app.profile(), "profile")
    posting = lang.resolve(app.posting(), "posting")
    if ws.is_home_country(posting["address"].get("country", "")):
        posting["address"]["country"] = ""  # a domestic letter never names the country
    letter = app.cover_letter()
    fixed = lang.resolve(ws.cover_letter_fixed(), FIXED_LETTER)
    attachments = [lang.resolve(e, "attachments") for e in app.selected_attachments()]
    return {
        "lang": lang.code,
        "profile": profile,
        "photo": _data_uri(ws.asset_path(profile.get("photo"))),
        "signature": _data_uri(ws.asset_path(profile.get("signature"))),
        "application": app.data,
        "posting": posting,
        "letter": letter,
        "fixed": fixed,
        "salutation": build_salutation(letter, fixed, posting),
        "subject": build_subject(letter, fixed, posting),
        "attachments": attachments,
        "style": app.style,
        "accent": ws.look_setting("accent") or "#0f6b78",
        "today": lang.long_date(),
        "documents": lang.pack["documents"],
        "labels": lang.pack.get("labels", {}),
    }


def build_salutation(letter: dict[str, Any], fixed: dict[str, Any], posting: dict[str, Any]) -> str:
    """Explicit letter.salutation wins; else a named pattern from the fixed file when the
    Posting names a contact; else the fixed default."""
    if letter.get("salutation"):
        return letter["salutation"]
    contact = posting.get("contact") or {}
    last_name = (contact.get("last_name") or "").strip()
    patterns = fixed.get("salutation_named") or {}
    if last_name and patterns:
        title = (contact.get("salutation") or "").strip()
        pattern = patterns.get(title) or patterns.get("_")
        if pattern:
            return pattern.format(
                salutation=title, first_name=(contact.get("first_name") or "").strip(), last_name=last_name,
            ).replace("  ", " ").strip()
    return fixed.get("salutation_default", "")


def build_subject(letter: dict[str, Any], fixed: dict[str, Any], posting: dict[str, Any]) -> str:
    """Explicit letter.subject wins; else "Bewerbung als {role}", with the reference number
    when the Posting has one (subject_default / subject_with_reference in the fixed file)."""
    if letter.get("subject"):
        return letter["subject"]
    role = (posting.get("role") or "").strip()
    reference = (posting.get("reference") or "").strip()
    pattern = fixed.get("subject_with_reference") if reference else None
    pattern = pattern or fixed.get("subject_default") or "{role}"
    return pattern.format(role=role, reference=reference).strip()


def render_html(app: Application, template_name: str, context: dict[str, Any]) -> str:
    env = _environment(app.workspace)
    _register_language(env, app.language)
    try:
        return env.get_template(template_name).render(**context)
    except TemplateNotFound as exc:
        raise JobapplyError(
            f"No template or style named {exc.name!r}: Styles are templates/styles/<name>.css, "
            f"bundled or in {app.workspace.root / 'templates'}"
        ) from exc


def html_to_pdf(html: str, out: Path, *, base_url: Path | None = None) -> None:
    from playwright.sync_api import sync_playwright

    out.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page()
        page.set_content(html, wait_until="load")
        page.emulate_media(media="print")
        page.pdf(path=str(out), format="A4", print_background=True, prefer_css_page_size=True)
        browser.close()


def merge_pdfs(parts: list[Path], out: Path) -> None:
    writer = PdfWriter()
    for part in parts:
        if part.suffix.lower() != ".pdf":
            raise JobapplyError(f"Cannot merge non-PDF attachment: {part.name} (convert it to PDF first)")
        writer.append(str(part))
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("wb") as fh:
        writer.write(fh)


def check_letter_ready(app: Application) -> None:
    letter = app.cover_letter()
    if letter.get("draft"):
        raise JobapplyError(
            f"{app.cover_letter_path} is still marked \"draft\": true. Write the letter, then set draft to false."
        )
    if not (letter.get("intro") or letter.get("body")):
        raise JobapplyError(f"{app.cover_letter_path} has no paragraphs in \"intro\" or \"body\".")


def render_application(app: Application, *, only: str | None = None, keep_html: bool = False) -> dict[str, Path]:
    """Render the CV, the Cover Letter (unless waived) and the Dossier, or just ``only``.
    Refuses while a Required Field is empty. Returns the produced paths."""
    docs = app.document_paths()
    produced: dict[str, Path] = {}
    report = preflight(app)
    if report.errors:
        raise JobapplyError("\n".join(report.errors))
    if only == "cover_letter" and app.cover_letter_waived:
        raise JobapplyError(COVER_LETTER_WAIVED)
    if "cover_letter" in docs and only in (None, "cover_letter"):
        check_letter_ready(app)
    context = build_context(app)

    if only in (None, "cv"):
        html = render_html(app, "cv.html", context)
        if keep_html:
            (app.out_dir / "cv.html").parent.mkdir(parents=True, exist_ok=True)
            (app.out_dir / "cv.html").write_text(html, encoding="utf-8")
        html_to_pdf(html, docs["cv"])
        produced["cv"] = docs["cv"]

    if "cover_letter" in docs and only in (None, "cover_letter"):
        html = render_html(app, "cover-letter.html", {**context, "style": app.letter_style})
        if keep_html:
            (app.out_dir / "cover-letter.html").write_text(html, encoding="utf-8")
        html_to_pdf(html, docs["cover_letter"])
        produced["cover_letter"] = docs["cover_letter"]

    if only in (None, "merged"):
        parts = dossier_parts(app)
        for part in parts:
            if part in docs.values() and not part.exists():
                raise JobapplyError(f"Cannot merge: {part.name} not rendered yet.")
        merge_pdfs(parts, docs["merged"])
        produced["merged"] = docs["merged"]

    return produced


def dossier_parts(app: Application) -> list[Path]:
    """The Dossier in Swiss order: Cover Letter (unless waived), CV, then the selected Attachments."""
    docs = app.document_paths()
    parts = [docs["cover_letter"]] if "cover_letter" in docs else []
    parts.append(docs["cv"])
    parts += [app.workspace.attachment_path(e["file"]) for e in app.selected_attachments()]
    return parts
