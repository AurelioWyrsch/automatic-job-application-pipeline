import pytest

from jobapply.errors import JobapplyError
from jobapply.forms import Resolver


def test_waived_cover_letter_cannot_be_uploaded(application):
    application.data["cover_letter"] = False
    application.save()
    resolver = Resolver(application)
    with pytest.raises(JobapplyError, match="waives the cover letter"):
        resolver.resolve("document:cover_letter", {})
    files = resolver.resolve("attachments:all+documents", {})
    assert [p.name for p in files][:1] == [application.document_paths()["cv"].name]
    assert len(files) == 5


# -- the Form Check -----------------------------------------------------------------

from jobapply.forms import FormCheck, classify_form, fields_left_to_applicant, record_form_check

FORM = "https://jobs.acme.ch/apply/1"


def _field(label, type_="text", value=None, **extra):
    return {"selector": f"#{label}", "type": type_, "label": label, "value": value, "matched_by": "", **extra}


def test_classify_form_gates_login_walls_passwords_and_empty_pages():
    assert classify_form(FORM, "https://jobs.acme.ch/login?next=/apply/1", [_field("email")]).startswith("login page")
    assert classify_form(FORM, FORM, [_field("email"), _field("password", "password")]) == "the page asks for a password"
    assert classify_form(FORM, FORM, []) == "no fillable fields on the page"
    assert classify_form(FORM, FORM + "?step=1", [_field("email")]) == ""


def test_record_form_check_writes_gated_or_the_page(application):
    result = record_form_check(application, None, "login page at https://x/login")
    assert result.gated and application.form_checked and application.form_gated
    field_map = application.field_map()
    assert field_map["pages"] == [] and field_map["gated"] is True and "login" in field_map["reason"]
    steps = {s.name: s for s in application.steps()}
    assert steps["scan"].done and "gated form" in steps["scan"].detail and not steps["fill"].done

    entry = {"url": FORM, "title": "Apply", "scanned_at": "t", "filled_at": None,
             "fields": [_field("Vorname", value="profile:first_name"), _field("Gehalt")]}
    result = record_form_check(application, entry, "")
    assert not result.gated and (result.fields, result.matched, result.unmatched) == (2, 1, 1)
    assert result.summary() == "Form: open, 2 fields, 1 mapped, 1 unmatched"
    assert not application.form_gated and "gated" not in application.field_map()
    assert application.undo_last_step() == "scan" and not application.form_checked


def test_fields_left_to_applicant_show_the_mappers_note(application):
    entry = {"url": FORM, "fields": [_field("Vorname", value="profile:first_name"),
                                     _field("Gehalt", note="salary: yours to answer"), _field("AGB", "checkbox")]}
    application.save_field_map({"pages": [entry]})
    assert fields_left_to_applicant(application) == ["Gehalt: salary: yours to answer", "AGB"]
