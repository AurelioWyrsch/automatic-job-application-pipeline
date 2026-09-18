import json

import pytest

from jobapply.errors import JobapplyError
from jobapply.workspace import PROFILE_FILES


def test_profile_is_merged_from_the_four_files(workspace):
    assert PROFILE_FILES == ("profile.json", "experience.json", "education.json", "skills.json")
    profile = workspace.profile()
    assert profile["first_name"] == "Mara"
    assert profile["contact"]["city"] == "Zürich"
    assert profile["experience"][0]["employer"] == "Beispiel AG"
    assert profile["education"][0]["institution"] == "Hochschule Luzern"
    assert {"skills", "languages", "certifications"} <= profile.keys()
    assert "_comment" not in profile


def test_profile_file_names_the_file_holding_a_key(workspace):
    assert workspace.profile_file("contact.phone") == "profile/profile.json"
    assert workspace.profile_file("education") == "profile/education.json"
    assert workspace.profile_file("languages") == "profile/skills.json"
    assert workspace.profile_file("no_such_key") == "profile/"


def test_missing_profile_file_is_an_error(workspace):
    (workspace.profile_dir / "education.json").unlink()
    with pytest.raises(JobapplyError, match="education.json"):
        workspace.profile()


def test_key_in_two_profile_files_is_an_error(workspace):
    path = workspace.profile_dir / "skills.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["education"] = []
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(JobapplyError, match=r"'education'.*education\.json.*skills\.json"):
        workspace.profile()


def test_fixed_cover_letter_is_one_file_with_language_maps(workspace):
    fixed = workspace.cover_letter_fixed()
    assert fixed["sign_off"] == {"de": "Freundliche Grüsse", "en": "Kind regards"}
    assert set(fixed["salutation_named"]) == {"de", "en"}
    assert not (workspace.root / "cover-letter.de.json").exists()


def test_missing_fixed_cover_letter_names_the_file(workspace):
    (workspace.root / "cover-letter-fixed.json").unlink()
    with pytest.raises(JobapplyError, match="cover-letter-fixed.json"):
        workspace.cover_letter_fixed()


def test_style_settings_come_from_the_fixed_letter_file_before_config(workspace, application):
    path = workspace.root / "cover-letter-fixed.json"
    fixed = json.loads(path.read_text(encoding="utf-8"))
    assert application.style == fixed["style"] == "classic"
    fixed["style"], fixed["letter_style"], fixed["accent"] = "bar", "bare", "#123456"
    path.write_text(json.dumps(fixed), encoding="utf-8")
    workspace.config["style"] = "accent"
    assert application.style == "bar" and application.letter_style == "bare"
    assert workspace.look_setting("accent") == "#123456"
    del fixed["style"], fixed["letter_style"]
    path.write_text(json.dumps(fixed), encoding="utf-8")
    assert application.style == "accent" and application.letter_style == "accent"
