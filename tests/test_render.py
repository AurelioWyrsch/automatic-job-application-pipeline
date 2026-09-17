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
    assert "Sehr geehrte Damen und Herren," in html
    assert "<strong>fett</strong>" in html
    assert "<li>eins</li>" in html
    # Beilagen: generated documents first, then attachments in merge order
    enclosures = html[html.index("Beilagen"):]
    assert [e for e in ("Lebenslauf", "Motivationsschreiben", "Zeugnis B", "Zeugnis A", "Diplom", "Cert")] == \
        sorted(("Lebenslauf", "Motivationsschreiben", "Zeugnis B", "Zeugnis A", "Diplom", "Cert"), key=enclosures.index)


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
