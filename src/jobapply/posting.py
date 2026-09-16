"""Fetch a Posting: save a Snapshot and extract structured facts when the page offers them.

Deterministic only. Many job boards embed a schema.org ``JobPosting`` JSON-LD
block; when present it fills posting.json. Otherwise the Snapshot is saved and
the applicant (or the /extract-posting skill) completes posting.json by hand.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from bs4 import BeautifulSoup, Tag

from .application import Application
from .errors import JobapplyError


@dataclass
class FetchResult:
    extracted: list[str] = field(default_factory=list)


def download(url: str, channel: str = "chrome") -> str:
    """Load the page in headless Chrome so JS-rendered postings work too."""
    from playwright.sync_api import Error as PlaywrightError, sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(channel=channel, headless=True)
        page = browser.new_page()
        try:
            page.goto(url, wait_until="networkidle", timeout=45_000)
        except PlaywrightError as exc:
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=45_000)
            except PlaywrightError:
                browser.close()
                raise JobapplyError(f"Could not load {url}: {exc}") from exc
        html = page.content()
        browser.close()
    return html


def to_markdown(html: str) -> str:
    """A readable text version of the page: headings, paragraphs, lists; chrome stripped."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "nav", "header", "footer", "iframe", "form"]):
        tag.decompose()
    root = soup.find("main") or soup.find("article") or soup.body or soup
    lines: list[str] = []

    def walk(node: Tag) -> None:
        for child in node.children:
            if isinstance(child, Tag):
                name = child.name.lower()
                if name in ("h1", "h2", "h3", "h4"):
                    level = int(name[1])
                    lines.append("\n" + "#" * level + " " + child.get_text(" ", strip=True))
                elif name == "li":
                    lines.append("- " + child.get_text(" ", strip=True))
                elif name in ("p", "div", "section", "td", "th", "tr", "ul", "ol", "table", "span", "a", "strong", "em", "b", "i"):
                    if name in ("p",) or not any(isinstance(c, Tag) for c in child.children):
                        text = child.get_text(" ", strip=True)
                        if text:
                            lines.append(text)
                    else:
                        walk(child)
                elif name == "br":
                    continue
                else:
                    walk(child)
            else:
                text = str(child).strip()
                if text and node.name not in ("p",):
                    lines.append(text)

    walk(root)
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"
    return text


def find_job_postings(html: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    found: list[dict[str, Any]] = []
    for script in soup.find_all("script", attrs={"type": re.compile(r"application/ld\+json", re.I)}):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        found.extend(_collect_job_postings(data))
    return found


def _collect_job_postings(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [jp for item in data for jp in _collect_job_postings(item)]
    if isinstance(data, dict):
        types = data.get("@type")
        types = types if isinstance(types, list) else [types]
        if "JobPosting" in types:
            return [data]
        return [jp for v in data.get("@graph", []) for jp in _collect_job_postings(v)]
    return []


def _text(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("name") or value.get("value") or "")
    if isinstance(value, list):
        return ", ".join(_text(v) for v in value if _text(v))
    return str(value or "")


def _strip_html(text: str) -> str:
    return BeautifulSoup(text, "html.parser").get_text("\n", strip=True)


def apply_job_posting(posting: dict[str, Any], jp: dict[str, Any]) -> list[str]:
    """Fill empty posting.json fields from a JobPosting object. Returns the keys set."""
    updated: list[str] = []

    def put(path: tuple[str, ...], value: str) -> None:
        if not value:
            return
        target = posting
        for key in path[:-1]:
            target = target.setdefault(key, {})
        if not target.get(path[-1]):
            target[path[-1]] = value
            updated.append(".".join(path))

    put(("role",), _text(jp.get("title")))
    put(("company",), _text(jp.get("hiringOrganization")))
    ident = jp.get("identifier")
    put(("reference",), _text(ident.get("value") or ident.get("name")) if isinstance(ident, dict) else _text(ident))
    put(("workload",), _text(jp.get("employmentType")))
    put(("description",), _strip_html(_text(jp.get("description"))))

    loc = jp.get("jobLocation")
    loc = loc[0] if isinstance(loc, list) and loc else loc
    if isinstance(loc, dict):
        addr = loc.get("address") or {}
        if isinstance(addr, dict):
            put(("address", "street"), _text(addr.get("streetAddress")))
            put(("address", "postal_code"), _text(addr.get("postalCode")))
            put(("address", "city"), _text(addr.get("addressLocality")))
            put(("address", "country"), _text(addr.get("addressCountry")))
            put(("location",), ", ".join(x for x in (_text(addr.get("addressLocality")), _text(addr.get("addressCountry"))) if x))
        else:
            put(("location",), _text(addr))
    return updated


def fetch_posting(app: Application) -> FetchResult:
    url = app.data.get("posting_url")
    if not url:
        raise JobapplyError("application.json has no posting_url")
    channel = (app.workspace.config.get("browser") or {}).get("channel", "chrome")
    html = download(url, channel=channel)
    app.snapshot_html.write_text(html, encoding="utf-8")
    app.snapshot_md.write_text(f"# Snapshot of {url}\n\n" + to_markdown(html), encoding="utf-8")

    result = FetchResult()
    posting = app.posting()
    for jp in find_job_postings(html):
        result.extracted += apply_job_posting(posting, jp)
    app.save_posting(posting)
    return result
