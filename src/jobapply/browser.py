"""The tool's Chrome: every page the tool opens and every PDF it prints goes through here.

Two ways to open a page. With the **Browser Session** (``session=True``) Chrome runs on the
Workspace's own profile in ``.browser/``, so a login the applicant made with ``jobapply login``
is there for the Posting fetch and the form session. Without it (``session=False``) the page
is what a visitor with no session sees, which is how the Form Check tells an Open Form from a
Gated Form. Either way the page is settled before the caller gets it: ``load`` (or
``domcontentloaded`` when headed, so a slow page does not hold the applicant), then up to
``settle_ms`` of quiet network for client-rendered content. A real idle is never required:
career sites keep polling, and the page as it is after the budget beats a reload cut off early.

Chrome is launched without the automation flag, so ``navigator.webdriver`` is false and sites
that park automated browsers on an interstitial show the real page.
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from .errors import JobapplyError
from .workspace import Workspace

SETTLE_MS = 5_000  # how long a page may keep loading after `load` before it is taken as is
GOTO_TIMEOUT_MS = 45_000

LOGIN_WALL_MARKERS = ("authwall", "/login", "/uas/login", "/checkpoint/", "/signin", "/sign-in", "/anmelden")

_STEALTH = {"ignore_default_args": ["--enable-automation"], "args": ["--disable-blink-features=AutomationControlled"]}


class BrowserClosed(JobapplyError):
    """The applicant closed Chrome themselves; for an interactive session that is not an error."""


def looks_like_login_wall(requested_url: str, final_url: str) -> bool:
    """A page that redirected to a login: LinkedIn's authwall, an ATS behind SSO, ..."""
    if final_url.split("?", 1)[0].rstrip("/") == requested_url.split("?", 1)[0].rstrip("/"):
        return False
    path = final_url.lower()
    return any(marker in path for marker in LOGIN_WALL_MARKERS)


def _channel(workspace: Workspace) -> str:
    return (workspace.config.get("browser") or {}).get("channel", "chrome")


@contextmanager
def visit(workspace: Workspace, url: str, *, session: bool, headed: bool = False,
          settle_ms: int = SETTLE_MS) -> Iterator[Any]:
    """Visit `url` and yield the settled page; Chrome closes when the block ends.

    A page that cannot be loaded raises JobapplyError. Chrome closed by the applicant during
    the block raises BrowserClosed instead of a Playwright error.
    """
    from playwright.sync_api import Error as PlaywrightError, sync_playwright

    with sync_playwright() as p:
        if session:
            workspace.browser_dir.mkdir(parents=True, exist_ok=True)
            context = p.chromium.launch_persistent_context(
                str(workspace.browser_dir), channel=_channel(workspace), headless=not headed,
                no_viewport=True, **_STEALTH)
            page = context.pages[0] if context.pages else context.new_page()
        else:
            context = p.chromium.launch(channel=_channel(workspace), headless=not headed, **_STEALTH)
            page = context.new_page()
        try:
            try:
                page.goto(url, wait_until="domcontentloaded" if headed else "load", timeout=GOTO_TIMEOUT_MS)
            except PlaywrightError as exc:
                raise JobapplyError(f"Could not load {url}: {str(exc).splitlines()[0]}") from exc
            if settle_ms:
                try:
                    page.wait_for_load_state("networkidle", timeout=settle_ms)
                except PlaywrightError:
                    pass
            try:
                yield page
            except PlaywrightError as exc:
                if not _closed_by_user(exc):
                    raise
                raise BrowserClosed("the browser was closed") from exc
        finally:
            try:
                context.close()
            except PlaywrightError as exc:  # one the applicant already closed raises, and that is fine
                if not _closed_by_user(exc):
                    raise


def _closed_by_user(exc: Exception) -> bool:
    """Playwright's TargetClosedError is not exported in every version; its message is stable."""
    return "has been closed" in str(exc)


def pdf(workspace: Workspace, documents: dict[Path, str]) -> None:
    """Print each HTML document to its path, all in one headless Chrome."""
    from playwright.sync_api import sync_playwright

    if not documents:
        return
    with sync_playwright() as p:
        browser = p.chromium.launch(channel=_channel(workspace), headless=True)
        page = browser.new_page()
        page.emulate_media(media="print")
        for out, html in documents.items():
            out.parent.mkdir(parents=True, exist_ok=True)
            page.set_content(html, wait_until="load")
            page.pdf(path=str(out), format="A4", print_background=True, prefer_css_page_size=True)
        browser.close()
