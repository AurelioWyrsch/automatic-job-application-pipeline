"""The Browser module: the pure parts. Chrome itself is exercised manually (CLAUDE.md)."""

import pytest

from jobapply import browser
from jobapply.errors import JobapplyError


def test_visit_translates_a_browser_the_applicant_closed(workspace, monkeypatch):
    """A Playwright "closed" error inside the block becomes BrowserClosed, a JobapplyError;
    any other Playwright error passes through."""
    from playwright.sync_api import Error as PlaywrightError

    class Page:
        url = "https://x"

        def goto(self, *a, **k):
            pass

        def wait_for_load_state(self, *a, **k):
            pass

    class Context:
        pages = [Page()]

        def close(self):
            raise PlaywrightError("Target page, context or browser has been closed")

    class Chromium:
        def launch_persistent_context(self, *a, **k):
            return Context()

    class Playwright:
        chromium = Chromium()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr("playwright.sync_api.sync_playwright", lambda: Playwright())

    with pytest.raises(browser.BrowserClosed):
        with browser.visit(workspace, "https://x", session=True):
            raise PlaywrightError("Target page, context or browser has been closed")
    assert issubclass(browser.BrowserClosed, JobapplyError)

    with pytest.raises(PlaywrightError, match="something else"):
        with browser.visit(workspace, "https://x", session=True):
            raise PlaywrightError("something else")


def test_channel_comes_from_config(workspace):
    assert browser._channel(workspace) == "chrome"
    workspace.config["browser"] = {"channel": "chromium"}
    assert browser._channel(workspace) == "chromium"
