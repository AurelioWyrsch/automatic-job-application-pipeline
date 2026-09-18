"""`jobapply new <url>` and `run <url>`: fetch first, take what the page says, ask nothing."""

import pytest

from jobapply.application import Application
from jobapply.errors import JobapplyError
from jobapply.posting import new_application
from tests.conftest import POSTING_HTML as HTML

URL = "https://jobs.acme.ch/job/1"


def test_new_takes_company_role_and_form_from_the_page(workspace):
    app = new_application(workspace, URL, download=lambda url: HTML)

    assert app.slug.endswith("-acme-ag-data-scientist")
    assert app.data["company"] == "Acme AG" and app.data["role"] == "Data Scientist"
    assert app.data["posting_url"] == URL and app.data["form_url"] == "https://jobs.acme.ch/apply/1"
    assert app.language_code == workspace.default_language
    assert app.snapshot_html.read_text() == HTML and "# Data Scientist" in app.snapshot_md.read_text()
    posting = app.posting()
    assert posting["company"] == "Acme AG" and posting["reference"] == "REQ-1"
    assert [s.name for s in app.steps() if s.done] == ["new", "fetch"]
    assert app.letter_untouched() and not app.posting_extracted()


def test_a_bare_page_names_the_folder_after_the_host(workspace):
    app = new_application(workspace, URL, download=lambda url: "<html><body>bare</body></html>")
    assert app.slug.endswith("-jobs-acme-ch") and not app.slug.endswith("-")
    assert app.data["company"] == "jobs.acme.ch" and app.data["role"] == ""
    assert app.data["form_url"] == URL  # no apply link: the Operator may correct it
    assert (app.posting()["company"], app.posting()["role"]) == ("", "")


def test_explicit_values_win_over_the_page(workspace):
    app = new_application(workspace, URL, download=lambda url: HTML,
                          company="Given", role="Given role", form_url="https://f", language="en")
    assert app.data["company"] == "Given" and app.data["form_url"] == "https://f" and app.language_code == "en"
    assert app.posting()["company"] == "Acme AG"  # posting.json keeps the page's own wording


def test_download_failure_creates_nothing(workspace):
    def boom(url):
        raise JobapplyError("Could not load")

    with pytest.raises(JobapplyError, match="Could not load"):
        new_application(workspace, URL, download=boom)
    assert Application.list_folders(workspace) == []


def test_same_posting_is_refused(workspace):
    first = new_application(workspace, URL + "/", download=lambda url: HTML)
    with pytest.raises(JobapplyError, match=first.slug):
        new_application(workspace, URL + "#top", download=lambda url: HTML)
    assert Application.find_by_posting_url(workspace, URL) is not None
    assert Application.find_by_posting_url(workspace, URL + "?other=1") is None


def test_run_with_a_url_continues_the_existing_application(workspace):
    from jobapply.run import is_url, start_application

    existing = new_application(workspace, URL, download=lambda url: HTML)
    assert start_application(workspace, URL + "#top", download=lambda url: HTML).slug == existing.slug
    assert is_url(URL) and is_url("mailto:hr@acme.ch") and not is_url("2026-09-18-acme")


def test_run_picker_starts_a_new_application_without_questions(workspace):
    from jobapply.run import choose_application

    seen = []

    def ask(label, default=None):
        seen.append(label)
        return URL

    app = choose_application(workspace, ask, download=lambda url: HTML)
    assert seen == ["Posting URL (job description)"]
    assert app.data["company"] == "Acme AG"


def test_by_email_application_copies_the_address_into_the_posting_contact(workspace):
    html = '<html><body><h1>Analyst</h1><a href="mailto:hr@acme.ch">Bewerben</a></body></html>'
    app = new_application(workspace, URL, download=lambda url: html)
    assert app.applies_by_email and app.application_email == "hr@acme.ch"
    assert app.posting()["contact"]["email"] == "hr@acme.ch"
