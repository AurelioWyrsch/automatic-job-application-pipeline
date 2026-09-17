"""`jobapply new <url>`: fetch first, confirm what the page says, then create the Application."""

import pytest

from jobapply.application import Application
from jobapply.errors import JobapplyError
from jobapply.posting import new_application
from tests.conftest import POSTING_HTML as HTML

URL = "https://jobs.acme.ch/job/1"


def recorder(answers: dict[str, str]):
    """An `ask` that records the defaults it was shown and answers from `answers` or with the default."""
    seen: dict[str, str | None] = {}

    def ask(label: str, default: str | None = None) -> str:
        seen[label] = default
        return answers.get(label) or default or ""

    ask.seen = seen  # type: ignore[attr-defined]
    return ask


def test_new_confirms_proposals_and_is_born_fetched(workspace):
    ask = recorder({"Company": "Acme"})
    app = new_application(workspace, URL, ask, download=lambda url: HTML)

    assert ask.seen == {"Company": "Acme AG", "Role / job title": "Data Scientist",
                        "Form URL (where you apply)": "https://jobs.acme.ch/apply/1", "Language of the documents": "de"}
    assert app.slug.endswith("-acme-data-scientist")
    assert app.data["company"] == "Acme" and app.data["posting_url"] == URL
    assert app.data["form_url"] == "https://jobs.acme.ch/apply/1"
    assert app.snapshot_html.read_text() == HTML and "# Data Scientist" in app.snapshot_md.read_text()
    posting = app.posting()
    assert posting["company"] == "Acme AG" and posting["reference"] == "REQ-1"
    assert [s.name for s in app.steps() if s.done] == ["new", "fetch"]


def test_posting_json_falls_back_to_confirmed_values_on_a_bare_page(workspace):
    ask = recorder({"Company": "Typed AG", "Role / job title": "Typed role"})
    app = new_application(workspace, URL, ask, download=lambda url: "<html><body>bare</body></html>")
    assert ask.seen["Company"] is None
    assert (app.posting()["company"], app.posting()["role"]) == ("Typed AG", "Typed role")


def test_explicit_values_are_not_asked(workspace):
    ask = recorder({})
    app = new_application(workspace, URL, ask, download=lambda url: HTML,
                          company="Given", role="Given role", form_url="https://f", language="en")
    assert ask.seen == {}
    assert app.data["company"] == "Given" and app.data["form_url"] == "https://f" and app.language_code == "en"


def test_download_failure_creates_nothing(workspace):
    def boom(url):
        raise JobapplyError("Could not load")

    with pytest.raises(JobapplyError, match="Could not load"):
        new_application(workspace, URL, recorder({}), download=boom)
    assert Application.list_folders(workspace) == []


def test_same_posting_is_refused(workspace):
    first = new_application(workspace, URL + "/", recorder({}), download=lambda url: HTML)
    with pytest.raises(JobapplyError, match=first.slug):
        new_application(workspace, URL + "#top", recorder({}), download=lambda url: HTML)
    assert Application.find_by_posting_url(workspace, URL) is not None
    assert Application.find_by_posting_url(workspace, URL + "?other=1") is None


def test_run_offers_to_continue_an_existing_application(workspace):
    from jobapply.run import choose_application

    existing = new_application(workspace, URL, recorder({}), download=lambda url: HTML)
    ask = recorder({"Continue which?": "n", "Posting URL (job description)": URL})
    chosen = choose_application(workspace, ask, download=lambda url: HTML)
    assert chosen.slug == existing.slug
    assert ask.seen[f"Continue {existing.slug} instead? (y/n)"] == "y"
    assert "Company" not in ask.seen


def test_by_email_application_copies_the_address_into_the_posting_contact(workspace):
    html = '<html><body><h1>Analyst</h1><a href="mailto:hr@acme.ch">Bewerben</a></body></html>'
    ask = recorder({"Company": "Acme"})
    app = new_application(workspace, URL, ask, download=lambda url: html)
    assert ask.seen["Form URL (where you apply)"] == "mailto:hr@acme.ch"
    assert app.applies_by_email and app.application_email == "hr@acme.ch"
    assert app.posting()["contact"]["email"] == "hr@acme.ch"
