"""The Workspace: one applicant's private data, kept apart from the tool's code.

Layout::

    workspace/
      config.json            default language, language packs, browser settings
      profile/               the Profile, four files merged into one dict (ADR 0005):
        profile.json           identity, contact, links, personal, summary, interests
        experience.json        experience
        education.json         education
        skills.json            skills, languages, certifications
      field-synonyms.json    the Synonym Table
      cover-letter-fixed.json  the fixed half of the Cover Letter, every Language in one file
      attachments/           static documents + manifest.json
      templates/             optional overrides of the built-in Templates
      applications/          one folder per Application
      .browser/              the tool-owned persistent Chrome profile
"""

from __future__ import annotations

import json
import os
import shlex
import shutil
from importlib import resources
from pathlib import Path
from typing import Any

from .errors import JobapplyError
from .i18n import BUILTIN_LANGUAGES, Language, deep_merge

ENV_VAR = "JOBAPPLY_WORKSPACE"
DEFAULT_DIR = "workspace"
FIXED_LETTER = "cover-letter-fixed.json"
PROFILE_FILES = ("profile.json", "experience.json", "education.json", "skills.json")


def _read_json(path: Path) -> Any:
    if not path.exists():
        raise JobapplyError(f"Missing file: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise JobapplyError(f"Invalid JSON in {path}: {exc}") from exc


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def package_file(*parts: str) -> Path:
    """Path to a file shipped inside the jobapply package."""
    return Path(str(resources.files("jobapply").joinpath(*parts)))


class Workspace:
    def __init__(self, root: Path):
        self.root = root.resolve()
        if not (self.root / "config.json").exists():
            raise JobapplyError(
                f"{self.root} is not a workspace (no config.json). "
                f"Run `jobapply init` or pass --workspace / set ${ENV_VAR}."
            )
        self.config: dict[str, Any] = _read_json(self.root / "config.json")

    # -- discovery -------------------------------------------------------------

    @classmethod
    def locate(cls, explicit: Path | None) -> "Workspace":
        if explicit is not None:
            return cls(explicit)
        env = os.environ.get(ENV_VAR)
        if env:
            return cls(Path(env))
        return cls(Path.cwd() / DEFAULT_DIR)

    @classmethod
    def init(cls, root: Path) -> "Workspace":
        """Create a fresh Workspace from the bundled example data."""
        if (root / "config.json").exists():
            raise JobapplyError(f"{root} already is a workspace.")
        example = package_file("defaults", "workspace")
        shutil.copytree(example, root, dirs_exist_ok=True)
        (root / "applications").mkdir(exist_ok=True)
        (root / ".browser").mkdir(exist_ok=True)
        (root / ".gitignore").write_text(".browser/\n", encoding="utf-8")
        return cls(root)

    # -- paths ------------------------------------------------------------------

    @property
    def applications_dir(self) -> Path:
        return self.root / "applications"

    @property
    def attachments_dir(self) -> Path:
        return self.root / "attachments"

    @property
    def profile_dir(self) -> Path:
        return self.root / "profile"

    @property
    def browser_dir(self) -> Path:
        return self.root / ".browser"

    def template_path(self, name: str) -> Path:
        """A Workspace override wins over the Template shipped with the tool."""
        override = self.root / "templates" / name
        if override.exists():
            return override
        bundled = package_file("templates", name)
        if bundled.exists():
            return bundled
        raise JobapplyError(f"No template named {name!r} in {self.root / 'templates'} or bundled.")

    # -- data -------------------------------------------------------------------

    @property
    def default_language(self) -> str:
        return self.config.get("default_language", "de")

    def language(self, code: str) -> Language:
        return Language(code, self.config.get("languages"))

    def is_home_country(self, country: str) -> bool:
        """Whether a Posting's country is the applicant's own, in any spelling config.json lists."""
        spellings = self.config.get("home_country") or ["CH", "Schweiz", "Switzerland"]
        return country.strip().lower() in {s.lower() for s in spellings}

    def editor_command(self) -> list[str]:
        """How to open a file for editing: config "editor" (e.g. "code -r"), else the desktop default."""
        return shlex.split(self.config.get("editor") or "xdg-open")

    def apply_labels(self) -> list[str]:
        """Link texts that lead from a Posting to its Form, across every known Language
        (the Posting's language is unrelated to the one the applicant will choose)."""
        packs = deep_merge(BUILTIN_LANGUAGES, self.config.get("languages") or {})
        return [label for code, pack in sorted(packs.items()) if not code.startswith("_")
                for label in (pack.get("apply_labels") or [])]

    def profile(self) -> dict[str, Any]:
        """The Profile: the top-level keys of the four files in ``profile/``, merged (ADR 0005)."""
        return self._profile_and_origins()[0]

    def profile_file(self, dotted: str) -> str:
        """The Workspace-relative file that holds a dotted Profile path, for messages."""
        origins = self._profile_and_origins()[1]
        name = origins.get(dotted.split(".")[0])
        return f"profile/{name}" if name else "profile/"

    def _profile_and_origins(self) -> tuple[dict[str, Any], dict[str, str]]:
        profile: dict[str, Any] = {}
        origins: dict[str, str] = {}
        for name in PROFILE_FILES:
            data = _read_json(self.profile_dir / name)
            if not isinstance(data, dict):
                raise JobapplyError(f"profile/{name} must be a JSON object")
            for key, value in data.items():
                if key.startswith("_"):
                    continue
                if key in origins:
                    raise JobapplyError(
                        f"Profile key {key!r} appears in both profile/{origins[key]} and profile/{name}"
                    )
                profile[key] = value
                origins[key] = name
        return profile, origins

    def synonyms(self) -> dict[str, Any]:
        return _read_json(self.root / "field-synonyms.json")

    def save_synonyms(self, data: dict[str, Any]) -> None:
        write_json(self.root / "field-synonyms.json", data)

    def cover_letter_fixed(self) -> dict[str, Any]:
        """The fixed half of the Cover Letter, not yet language-resolved (values may be language maps)."""
        return _read_json(self.root / FIXED_LETTER)

    def look_setting(self, key: str) -> Any:
        """A Style setting (`style`, `letter_style`, `accent`): the applicant keeps them in
        cover-letter-fixed.json next to the document text; config.json is still honoured."""
        path = self.root / FIXED_LETTER
        fixed = _read_json(path) if path.exists() else {}
        return fixed.get(key) or self.config.get(key)

    def attachments_manifest(self) -> list[dict[str, Any]]:
        path = self.attachments_dir / "manifest.json"
        if not path.exists():
            return []
        data = _read_json(path)
        entries = data.get("attachments", data) if isinstance(data, dict) else data
        for entry in entries:
            file = self.attachments_dir / entry["file"]
            if not file.exists():
                raise JobapplyError(f"Attachment listed in manifest but missing: {file}")
        return entries

    def attachment_path(self, filename: str) -> Path:
        path = self.attachments_dir / filename
        if not path.exists():
            raise JobapplyError(f"Attachment not found: {path}")
        return path

    def asset_path(self, relative: str | None) -> Path | None:
        """Resolve a Profile asset such as the photo or signature, relative to the Workspace."""
        if not relative:
            return None
        path = self.root / relative
        if not path.exists():
            raise JobapplyError(f"Asset referenced in {self.profile_file('photo')} not found: {path}")
        return path
