"""The `email` step: a by-email Application gets a covering message, not a Field Map."""

import json

import pytest

from jobapply.errors import JobapplyError
from jobapply.mail import compose_email, write_email


@pytest.fixture
def by_email(application):
    application.data["form_url"] = "mailto:hr@acme.ch"
    application.save()
    posting = application.posting()
    posting["contact"].update({"salutation": "Frau", "first_name": "Eva", "last_name": "Muster"})
    application.save_posting(posting)
    return application


def test_compose_uses_letter_subject_salutation_and_fixed_email_body(by_email):
    email = compose_email(by_email)
    assert email.to == "hr@acme.ch"
    assert email.subject == "Bewerbung als Data Scientist"
    lines = email.body.splitlines()
    assert lines[0] == "Sehr geehrte Frau Muster"
    assert "Gerne bewerbe ich mich als Data Scientist." in email.body
    assert "Freundliche Grüsse" in lines
    profile = by_email.workspace.profile()
    assert lines[-2] == f"{profile['first_name']} {profile['last_name']}"
    assert lines[-1] == profile["contact"]["phone"]
    assert [p.name for p in email.attachments] == [by_email.document_paths()["merged"].name]
    assert email.mailto_url().startswith("mailto:hr@acme.ch?subject=Bewerbung%20als%20Data%20Scientist&body=Sehr")


def test_write_email_needs_the_dossier_and_then_completes_the_step(by_email):
    with pytest.raises(JobapplyError, match="Render first"):
        write_email(by_email)
    merged = by_email.document_paths()["merged"]
    merged.parent.mkdir()
    merged.write_bytes(b"%PDF")
    email = write_email(by_email)
    text = by_email.email_path.read_text()
    assert text.startswith("To: hr@acme.ch\nSubject: Bewerbung als Data Scientist\n")
    assert str(merged) in text and email.as_markdown() == text
    assert {s.name: s.done for s in by_email.steps()}["email"]


def test_compose_refuses_a_web_form_application(application):
    with pytest.raises(JobapplyError, match="web Form"):
        compose_email(application)


def test_missing_email_body_is_reported(by_email):
    path = by_email.workspace.root / "cover-letter.de.json"
    fixed = json.loads(path.read_text())
    del fixed["email_body"]
    path.write_text(json.dumps(fixed))
    with pytest.raises(JobapplyError, match="email_body"):
        compose_email(by_email)
