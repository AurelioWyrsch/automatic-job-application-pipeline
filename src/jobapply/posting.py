"""Fetch a Posting: save a Snapshot and extract structured facts when the page offers them.

Deterministic only. Many job boards embed a schema.org ``JobPosting`` JSON-LD
block; when present it fills posting.json. Otherwise only the page title and
``<h1>`` are read (for company and role), and the applicant (or the
/extract-posting skill) completes posting.json by hand.

``new_application`` is the `jobapply new` flow: the page is fetched *before* the
Application exists, so its company and role can name the folder.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup, Tag

from .application import Application
from .errors import JobapplyError
from .workspace import Workspace

Download = Callable[[str], str]


@dataclass
class FetchResult:
    extracted: list[str] = field(default_factory=list)


LOGIN_WALL_MARKERS = ("authwall", "/login", "/uas/login", "/checkpoint/", "/signin", "/sign-in", "/anmelden")


def looks_like_login_wall(requested_url: str, final_url: str) -> bool:
    """A Posting that redirected to a login page: LinkedIn's authwall, an ATS behind SSO, ..."""
    if final_url.split("?", 1)[0].rstrip("/") == requested_url.split("?", 1)[0].rstrip("/"):
        return False
    path = final_url.lower()
    return any(marker in path for marker in LOGIN_WALL_MARKERS)


def download(url: str, workspace: Workspace) -> str:
    """Load the page in headless Chrome on the Workspace's browser profile, so JS-rendered
    postings work and a site the applicant logged in to (`jobapply login`) stays readable."""
    from playwright.sync_api import Error as PlaywrightError, sync_playwright

    from .forms import persistent_context

    with sync_playwright() as p:
        context = persistent_context(p, workspace, headless=True)
        page = context.pages[0] if context.pages else context.new_page()
        try:
            page.goto(url, wait_until="networkidle", timeout=45_000)
        except PlaywrightError as exc:
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=45_000)
            except PlaywrightError:
                context.close()
                raise JobapplyError(f"Could not load {url}: {exc}") from exc
        final_url, html = page.url, page.content()
        context.close()
    if looks_like_login_wall(url, final_url):
        raise JobapplyError(
            f"{url} sent the browser to a login page ({final_url}).\n"
            f"  Log in once with: jobapply login {url}   then fetch again."
        )
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


@dataclass
class Proposal:
    """What `jobapply new` proposes from a Posting page before the applicant confirms it."""

    company: str = ""
    role: str = ""
    form_url: str = ""


def propose(html: str, posting_url: str, apply_labels: list[str]) -> Proposal:
    """Derive company, role and the apply link from a Posting page, deterministically.

    JSON-LD ``JobPosting`` first; otherwise the page title and ``<h1>``. The Form
    URL is the first anchor whose text is an apply label, else the Posting URL. An
    apply link that is a ``mailto:`` (no web Form) is kept as such, but a web link wins.
    """
    proposal = Proposal(form_url=posting_url)
    facts: dict[str, Any] = {}
    for jp in find_job_postings(html):
        apply_job_posting(facts, jp)
    soup = BeautifulSoup(html, "html.parser")
    company, role = _company_and_role_from_title(soup)
    proposal.company = facts.get("company") or company
    proposal.role = facts.get("role") or role
    link = _apply_link(soup, apply_labels)
    if link:
        proposal.form_url = urljoin(posting_url, link)
    return proposal


def _meta(soup: BeautifulSoup, prop: str) -> str:
    tag = soup.find("meta", attrs={"property": prop}) or soup.find("meta", attrs={"name": prop})
    return str(tag.get("content") or "").strip() if isinstance(tag, Tag) else ""


def _company_and_role_from_title(soup: BeautifulSoup) -> tuple[str, str]:
    """Read "Role | Company" / "Company – Role" titles. Leaves the company empty rather than
    guessing when the title's parts cannot be told apart from the role."""
    company = _meta(soup, "og:site_name")
    h1 = soup.find("h1")
    role = h1.get_text(" ", strip=True) if h1 else _meta(soup, "og:title")
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    parts = [p.strip() for p in re.split(r"\s+[|–—-]\s+", title) if p.strip()]
    if len(parts) < 2:
        return company, role
    if not role:
        return company or parts[-1], parts[0]
    others = [p for p in parts if not (p.startswith(role) or role.startswith(p))]
    if others and len(others) < len(parts):  # one part is the role, so the rest is the company
        company = company or others[-1]
    return company, role


def _label_key(text: str) -> str:
    return " ".join(re.sub(r"[^\w\s]", " ", text.lower()).split())


def _apply_link(soup: BeautifulSoup, apply_labels: list[str]) -> str:
    labels = {_label_key(label) for label in apply_labels}
    mailto = ""
    for anchor in soup.find_all("a", href=True):
        href = str(anchor["href"]).strip()
        if href.lower().startswith(("javascript:", "#")):
            continue
        if _label_key(anchor.get_text(" ", strip=True)) in labels:
            if not href.lower().startswith("mailto:"):
                return href
            mailto = mailto or "mailto:" + href[len("mailto:"):].split("?", 1)[0]
    return mailto


def _downloader(workspace: Workspace) -> Download:
    return lambda url: download(url, workspace)


def store_snapshot(app: Application, url: str, html: str) -> FetchResult:
    """Write the Snapshot into the Application and fill empty posting.json fields from JSON-LD."""
    app.snapshot_html.write_text(html, encoding="utf-8")
    app.snapshot_md.write_text(f"# Snapshot of {url}\n\n" + to_markdown(html), encoding="utf-8")
    result = FetchResult()
    posting = app.posting()
    for jp in find_job_postings(html):
        result.extracted += apply_job_posting(posting, jp)
    app.save_posting(posting)
    return result


def fetch_posting(app: Application) -> FetchResult:
    url = app.data.get("posting_url")
    if not url:
        raise JobapplyError("application.json has no posting_url")
    return store_snapshot(app, url, _downloader(app.workspace)(url))


def new_application(
    workspace: Workspace,
    posting_url: str,
    *,
    download: Download | None = None,
    company: str | None = None,
    role: str | None = None,
    form_url: str | None = None,
    language: str | None = None,
) -> Application:
    """Fetch the Posting and create the Application from what the page says, asking nothing.

    Company, role and Form URL come from the page (JSON-LD, title, apply link); a page that
    yields neither company nor role names the folder after the site's host, and the
    unattended `extract-posting` corrects application.json afterwards. The Language is the
    Workspace default. Explicit keyword values win. The Application is born with its
    Snapshot, so `fetch` is already done.
    """
    existing = Application.find_by_posting_url(workspace, posting_url)
    if existing:
        raise JobapplyError(f"This Posting already has an Application: {existing.slug}")
    html = (download or _downloader(workspace))(posting_url)
    proposal = propose(html, posting_url, workspace.apply_labels())
    company = company or proposal.company
    role = role or proposal.role
    if not company and not role:
        company = urlsplit(posting_url).hostname or "posting"
    form_url = form_url or proposal.form_url
    language = language or workspace.default_language
    app = Application.create(workspace, company=company, role=role, language=language,
                             posting_url=posting_url, form_url=form_url)
    posting = app.posting()
    posting["company"] = proposal.company
    posting["role"] = proposal.role
    if app.applies_by_email and not posting["contact"].get("email"):
        posting["contact"]["email"] = app.application_email
    app.save_posting(posting)
    store_snapshot(app, posting_url, html)
    return app
