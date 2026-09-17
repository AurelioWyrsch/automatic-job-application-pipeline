import json

import pytest

from jobapply.errors import JobapplyError
from jobapply.render import build_context, check_letter_ready, render_html


def _write_letter(application):
    application.cover_letter_path.write_text(json.dumps({
        "draft": False, "subject": "Bewerbung als Data Scientist", "salutation": "",
        "intro": ["Erster Absatz mit **fett**."], "body": ["- eins\n- zwei"],
    }), encoding="utf-8")


def test_draft_letter_is_refused(application):
    with pytest.raises(JobapplyError, match="draft"):
        check_letter_ready(application)


def test_cv_html_renders_in_german(application):
    ctx = build_context(application)
    html = render_html(application, "cv.html", ctx)
    assert "Berufserfahrung" in html
    assert "01.2025 – heute" in html
    assert "Werkstudentin Data Analytics" in html
    assert 'src="data:image/png;base64,' in html


def test_cover_letter_html(application):
    _write_letter(application)
    ctx = build_context(application)
    html = render_html(application, "cover-letter.html", ctx)
    assert "<p>Sehr geehrte Damen und Herren</p>" in html  # Swiss: no comma after the salutation
    assert "<strong>fett</strong>" in html
    assert "<li>eins</li>" in html
    assert "Beilagen" not in html and "Zeugnis B" not in html  # no enclosure list (ADR 0003)


def test_english_application_uses_english_labels(workspace):
    from jobapply.application import Application
    app = Application.create(workspace, company="Acme", role="Analyst", language="en",
                             posting_url="u", form_url="v")
    html = render_html(app, "cv.html", build_context(app))
    assert "Experience" in html and "Jan 2025 – present" in html


def test_salutation_from_posting_contact():
    from jobapply.render import build_salutation
    fixed = {"salutation_default": "Sehr geehrte Damen und Herren,",
             "salutation_named": {"Frau": "Sehr geehrte Frau {last_name},", "Herr": "Sehr geehrter Herr {last_name},",
                                  "_": "Guten Tag {first_name} {last_name},"}}
    no_contact = {"contact": {}}
    assert build_salutation({}, fixed, no_contact) == "Sehr geehrte Damen und Herren,"
    assert build_salutation({}, fixed, {"contact": {"salutation": "Frau", "last_name": "Müller"}}) == "Sehr geehrte Frau Müller,"
    assert build_salutation({}, fixed, {"contact": {"salutation": "Herr", "last_name": "Meier"}}) == "Sehr geehrter Herr Meier,"
    assert build_salutation({}, fixed, {"contact": {"first_name": "Kim", "last_name": "Lee"}}) == "Guten Tag Kim Lee,"
    assert build_salutation({"salutation": "Liebe Anna"}, fixed, {"contact": {"salutation": "Frau", "last_name": "X"}}) == "Liebe Anna"


def test_letter_omits_the_home_country_in_the_address(application):
    _write_letter(application)
    posting = application.posting()
    posting["address"].update({"street": "Weg 1", "postal_code": "8000", "city": "Zürich", "country": "CH"})
    application.save_posting(posting)
    html = render_html(application, "cover-letter.html", build_context(application))
    assert "8000 Zürich" in html and ">CH<" not in html

    posting["address"].update({"city": "Berlin", "country": "Deutschland"})
    application.save_posting(posting)
    html = render_html(application, "cover-letter.html", build_context(application))
    assert ">Deutschland<" in html


def test_dossier_is_letter_then_cv_then_attachments(application):
    from jobapply.render import dossier_parts
    docs = application.document_paths()
    parts = dossier_parts(application)
    assert parts[:2] == [docs["cover_letter"], docs["cv"]]
    assert [p.name for p in parts[2:]] == ["zeugnis-b.pdf", "zeugnis-a.pdf", "diplom.pdf", "cert.pdf"]

    application.data["cover_letter"] = False
    application.save()
    parts = dossier_parts(application)
    assert parts[0] == application.document_paths()["cv"]
    assert len(parts) == 5


def test_subject_derived_from_posting_when_empty():
    from jobapply.render import build_subject
    fixed = {"subject_default": "Bewerbung als {role}", "subject_with_reference": "Bewerbung als {role}, Referenz {reference}"}
    assert build_subject({"subject": "Eigener Betreff"}, fixed, {"role": "X", "reference": "1"}) == "Eigener Betreff"
    assert build_subject({"subject": ""}, fixed, {"role": "Data Scientist", "reference": ""}) == "Bewerbung als Data Scientist"
    assert build_subject({}, fixed, {"role": "Data Scientist", "reference": "REQ-1"}) == "Bewerbung als Data Scientist, Referenz REQ-1"


def test_letter_without_subject_renders_the_default_subject(application):
    application.cover_letter_path.write_text(json.dumps({
        "draft": False, "subject": "", "salutation": "", "intro": ["Hallo."], "body": [],
    }), encoding="utf-8")
    check_letter_ready(application)  # subject is no longer required
    html = render_html(application, "cover-letter.html", build_context(application))
    assert "Bewerbung als Data Scientist" in html


def test_marital_status_appears_only_when_set(workspace, application):
    html = render_html(application, "cv.html", build_context(application))
    assert "Zivilstand" not in html
    profile = workspace.profile()
    profile["personal"]["marital_status"] = "ledig"
    (workspace.root / "profile.json").write_text(json.dumps(profile), encoding="utf-8")
    html = render_html(application, "cv.html", build_context(application))
    assert "Zivilstand" in html and "ledig" in html
