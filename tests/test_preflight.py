import json

from jobapply.preflight import preflight
from jobapply.workspace import PROFILE_FILES


def _write_profile(workspace, profile):
    """Write a merged Profile back into the four files, each keeping the keys it holds."""
    for name in PROFILE_FILES:
        path = workspace.profile_dir / name
        data = json.loads(path.read_text(encoding="utf-8"))
        for key in [k for k in data if not k.startswith("_")]:
            data[key] = profile[key]
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _set_profile(workspace, **changes):
    profile = workspace.profile()
    for dotted, value in changes.items():
        node = profile
        *parents, last = dotted.split(".")
        for part in parents:
            node = node[part]
        node[last] = value
    _write_profile(workspace, profile)


def test_complete_example_profile_passes(application):
    report = preflight(application)
    assert report.errors == []


def test_missing_required_field_is_an_error(workspace, application):
    _set_profile(workspace, **{"contact.phone": "", "personal.nationality": {"de": "", "en": ""}})
    report = preflight(application)
    assert any("contact.phone" in e for e in report.errors)
    assert any("personal.nationality" in e for e in report.errors)


def test_missing_recommended_field_is_a_warning(workspace, application):
    _set_profile(workspace, photo=None, **{"personal.birth_date": ""})
    report = preflight(application)
    assert report.errors == []
    assert any("photo" in w for w in report.warnings)
    assert any("personal.birth_date" in w for w in report.warnings)


def test_field_lists_come_from_config(workspace, application):
    _set_profile(workspace, **{"personal.permit": ""})
    workspace.config["profile_fields"] = {"required": ["personal.permit"], "recommended": []}
    report = preflight(application)
    assert report.errors == ["profile/profile.json: required field 'personal.permit' is empty"]
    assert not any("profile/" in w for w in report.warnings)


def test_render_refuses_a_profile_with_errors(workspace, application):
    import pytest
    from jobapply.errors import JobapplyError
    from jobapply.render import render_application
    _set_profile(workspace, **{"contact.email": ""})
    with pytest.raises(JobapplyError, match="contact.email"):
        render_application(application, only="cv")


def test_generic_salutation_is_a_warning_only_while_no_contact_is_known(application):
    assert any("contact person" in w for w in preflight(application).warnings)
    posting = application.posting()
    posting["contact"].update({"salutation": "Frau", "last_name": "Müller"})
    application.save_posting(posting)
    assert not any("contact person" in w for w in preflight(application).warnings)


def test_eszett_in_german_text_is_a_warning(workspace, application):
    _set_profile(workspace, **{"contact.street": "Musterstraße 12"})
    application.cover_letter_path.write_text(json.dumps({
        "draft": False, "subject": "", "salutation": "", "intro": ["Ich grüße Sie."], "body": [],
    }), encoding="utf-8")
    warnings = [w for w in preflight(application).warnings if "ß" in w]
    assert len(warnings) == 1
    assert "profile/" in warnings[0] and "cover-letter.json" in warnings[0]


def test_eszett_is_ignored_outside_german(workspace):
    from jobapply.application import Application
    _set_profile(workspace, **{"contact.street": "Musterstraße 12"})
    app = Application.create(workspace, company="Acme", role="Analyst", language="en", posting_url="u", form_url="v")
    assert not any("ß" in w for w in preflight(app).warnings)


def test_waived_letter_does_not_warn_about_the_contact_person(application):
    application.data["cover_letter"] = False
    application.save()
    assert not any("contact person" in w for w in preflight(application).warnings)
