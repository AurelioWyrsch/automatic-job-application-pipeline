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
