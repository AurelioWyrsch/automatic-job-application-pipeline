"""An Application: one attempt at one job, living in its own folder.

Files inside ``applications/<slug>/``:

    application.json   urls, company, role, language, selected attachments, profile overrides
    snapshot.html      the Posting as fetched (raw DOM)
    snapshot.md        the Posting as readable text
    posting.json       facts extracted from the Posting, completed by the applicant
    cover-letter.json  the specific half of the Cover Letter
    form-fields.json   the Field Map (Applications with a web Form)
    email.md           the application email as composed (Applications that apply by email)
    out/               rendered PDFs
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from .errors import JobapplyError
from .i18n import Language, deep_merge
from .workspace import Workspace, _read_json, write_json

EMPTY_POSTING: dict[str, Any] = {
    "company": "",
    "role": "",
    "reference": "",
    "location": "",
    "workload": "",
    "contact": {"salutation": "", "first_name": "", "last_name": "", "email": "", "phone": ""},
    "address": {"company_line": "", "street": "", "postal_code": "", "city": "", "country": ""},
    "requirements": [],
    "description": "",
}

COVER_LETTER_WAIVED = 'this application waives the cover letter (application.json: "cover_letter": false)'

EMPTY_COVER_LETTER: dict[str, Any] = {
    "draft": True,
    "subject": "",
    "salutation": "",
    "intro": [],
    "body": [],
}


def slugify(text: str, max_length: int = 40) -> str:
    """ASCII, lower-case, dash-separated, cut at a word boundary so folder names stay readable."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    if len(text) > max_length:
        text = text[:max_length].rsplit("-", 1)[0] or text[:max_length]
    return text or "x"


def posting_key(url: str) -> str:
    """Two URLs name the same Posting when they differ only by fragment or trailing slash."""
    return url.split("#", 1)[0].strip().rstrip("/")


@dataclass
class Step:
    name: str
    done: bool
    detail: str = ""


class Application:
    def __init__(self, workspace: Workspace, folder: Path):
        self.workspace = workspace
        self.folder = folder
        if not self.json_path.exists():
            raise JobapplyError(f"{folder} has no application.json")
        self.data: dict[str, Any] = _read_json(self.json_path)

    # -- lookup / creation -------------------------------------------------------

    @classmethod
    def create(
        cls,
        workspace: Workspace,
        *,
        company: str,
        role: str,
        language: str,
        posting_url: str,
        form_url: str,
    ) -> "Application":
        workspace.language(language)  # validates the language exists
        slug = f"{date.today().isoformat()}-{slugify(company)}-{slugify(role)}"
        folder = workspace.applications_dir / slug
        if folder.exists():
            raise JobapplyError(f"Application folder already exists: {folder}")
        folder.mkdir(parents=True)
        data = {
            "company": company,
            "role": role,
            "language": language,
            "posting_url": posting_url,
            "form_url": form_url,
            "created": date.today().isoformat(),
            "status": "open",
            "attachments": [entry["file"] for entry in workspace.attachments_manifest()],
            "profile_overrides": {},
        }
        write_json(folder / "application.json", data)
        posting = deep_merge(EMPTY_POSTING, {"company": company, "role": role})
        write_json(folder / "posting.json", posting)
        write_json(folder / "cover-letter.json", dict(EMPTY_COVER_LETTER))
        return cls(workspace, folder)

    @classmethod
    def find(cls, workspace: Workspace, ref: str) -> "Application":
        """Find an Application by exact slug or by a unique substring of it."""
        apps_dir = workspace.applications_dir
        exact = apps_dir / ref
        if exact.is_dir():
            return cls(workspace, exact)
        candidates = [p for p in cls.list_folders(workspace) if ref.lower() in p.name.lower()]
        if len(candidates) == 1:
            return cls(workspace, candidates[0])
        if not candidates:
            raise JobapplyError(f"No application matches {ref!r} in {apps_dir}")
        names = "\n  ".join(p.name for p in candidates)
        raise JobapplyError(f"{ref!r} is ambiguous, matches:\n  {names}")

    @classmethod
    def find_by_posting_url(cls, workspace: Workspace, url: str) -> "Application | None":
        """The Application already created for this Posting, if any."""
        wanted = posting_key(url)
        for folder in cls.list_folders(workspace):
            app = cls(workspace, folder)
            if posting_key(app.data.get("posting_url") or "") == wanted:
                return app
        return None

    @staticmethod
    def list_folders(workspace: Workspace) -> list[Path]:
        if not workspace.applications_dir.exists():
            return []
        return sorted(
            p for p in workspace.applications_dir.iterdir()
            if p.is_dir() and (p / "application.json").exists()
        )

    # -- paths ----------------------------------------------------------------------

    @property
    def slug(self) -> str:
        return self.folder.name

    @property
    def json_path(self) -> Path:
        return self.folder / "application.json"

    @property
    def snapshot_html(self) -> Path:
        return self.folder / "snapshot.html"

    @property
    def snapshot_md(self) -> Path:
        return self.folder / "snapshot.md"

    @property
    def posting_path(self) -> Path:
        return self.folder / "posting.json"

    @property
    def cover_letter_path(self) -> Path:
        return self.folder / "cover-letter.json"

    @property
    def field_map_path(self) -> Path:
        return self.folder / "form-fields.json"

    @property
    def email_path(self) -> Path:
        return self.folder / "email.md"

    @property
    def out_dir(self) -> Path:
        return self.folder / "out"

    def editable(self, what: str) -> Path:
        """The file `jobapply open` shows for a short name: letter, posting, fields, email or folder."""
        paths = {"letter": self.cover_letter_path, "posting": self.posting_path,
                 "fields": self.field_map_path, "email": self.email_path, "folder": self.folder}
        if what not in paths:
            raise JobapplyError(f"Nothing called {what!r} to open; use one of {', '.join(paths)}")
        return paths[what]

    # -- data -----------------------------------------------------------------------

    @property
    def language_code(self) -> str:
        return self.data.get("language") or self.workspace.default_language

    @property
    def language(self) -> Language:
        return self.workspace.language(self.language_code)

    def save(self) -> None:
        write_json(self.json_path, self.data)

    @property
    def style(self) -> str:
        """The Style (templates/styles/<name>.css): application.json wins over config.json, default classic."""
        return self.data.get("style") or self.workspace.config.get("style") or "classic"

    @property
    def letter_style(self) -> str:
        """The Style of the Cover Letter alone (`letter_style`); defaults to the CV's, so a coloured
        CV can go with a plain black letter."""
        return self.data.get("letter_style") or self.workspace.config.get("letter_style") or self.style

    @property
    def applies_by_email(self) -> bool:
        """``"form_url": "mailto:..."``: the employer takes applications by email, so there is
        no Form to scan or fill; the `email` step composes the message instead."""
        return (self.data.get("form_url") or "").lower().startswith("mailto:")

    @property
    def application_email(self) -> str:
        """The address a by-email Application is sent to (the mailto: without any query)."""
        if not self.applies_by_email:
            return ""
        return self.data["form_url"][len("mailto:"):].split("?", 1)[0].strip()

    @property
    def cover_letter_waived(self) -> bool:
        """``"cover_letter": false`` in application.json: the Form wants no letter (ADR 0003)."""
        return self.data.get("cover_letter", True) is False

    def profile(self) -> dict[str, Any]:
        """The Profile with this Application's overrides applied (not yet language-resolved)."""
        return deep_merge(self.workspace.profile(), self.data.get("profile_overrides") or {})

    def posting(self) -> dict[str, Any]:
        if not self.posting_path.exists():
            return dict(EMPTY_POSTING)
        return deep_merge(EMPTY_POSTING, _read_json(self.posting_path))

    def save_posting(self, data: dict[str, Any]) -> None:
        write_json(self.posting_path, data)

    def cover_letter(self) -> dict[str, Any]:
        if not self.cover_letter_path.exists():
            return dict(EMPTY_COVER_LETTER)
        letter = deep_merge(EMPTY_COVER_LETTER, _read_json(self.cover_letter_path))
        # `intro` and `body` are lists of paragraphs, but a hand-typed file may hold one
        # string; blank lines then separate the paragraphs.
        for key in ("intro", "body"):
            if isinstance(letter[key], str):
                letter[key] = [p.strip() for p in letter[key].split("\n\n") if p.strip()]
        return letter

    def mark_letter_done(self) -> None:
        """The applicant declares the specific half finished: `draft` becomes false."""
        letter = self.cover_letter()
        letter["draft"] = False
        write_json(self.cover_letter_path, letter)

    def field_map(self) -> dict[str, Any]:
        if not self.field_map_path.exists():
            return {"pages": []}
        return _read_json(self.field_map_path)

    def save_field_map(self, data: dict[str, Any]) -> None:
        write_json(self.field_map_path, data)

    def selected_attachments(self) -> list[dict[str, Any]]:
        """Manifest entries selected for this Application, in upload/merge order."""
        manifest = {e["file"]: e for e in self.workspace.attachments_manifest()}
        selected = []
        for name in self.data.get("attachments") or []:
            if name not in manifest:
                raise JobapplyError(
                    f"application.json lists attachment {name!r} which is not in attachments/manifest.json"
                )
            selected.append(manifest[name])
        return sort_attachments(selected)

    def document_paths(self) -> dict[str, Path]:
        """Paths of the documents this Application renders, by kind: cv, cover_letter (unless
        waived), merged (the Dossier)."""
        lang = self.language
        profile = self.workspace.profile()
        first, last = profile.get("first_name", ""), profile.get("last_name", "")
        kinds = ["cv", "merged"] if self.cover_letter_waived else ["cv", "cover_letter", "merged"]
        return {kind: self.out_dir / lang.filename(kind, first, last) for kind in kinds}

    # -- progress -------------------------------------------------------------------

    def steps(self) -> list[Step]:
        docs = self.document_paths()
        letter = self.cover_letter()
        letter_written = self.cover_letter_waived or (
            not letter.get("draft") and bool(letter.get("intro") or letter.get("body")))
        if self.cover_letter_waived:
            letter_detail = "waived (application.json: cover_letter false)"
        elif letter.get("draft"):
            letter_detail = 'cover-letter.json still has "draft": true'
        elif not letter_written:
            letter_detail = "cover-letter.json has no intro/body paragraphs"
        else:
            letter_detail = ""
        steps = [
            Step("new", True, self.data.get("created", "")),
            Step("fetch", self.snapshot_html.exists(), "snapshot saved" if self.snapshot_html.exists() else ""),
            Step("letter", letter_written, letter_detail),
            Step("render", all(p.exists() for p in docs.values()),
                 ", ".join(p.name for p in docs.values() if p.exists())),
        ]
        if self.applies_by_email:
            composed = self.email_path.exists()
            steps.append(Step("email", composed, f"composed for {self.application_email}" if composed else ""))
            return steps
        field_map = self.field_map()
        pages = field_map.get("pages", [])
        filled = any(p.get("filled_at") for p in pages)
        steps.append(Step("scan", bool(pages), f"{sum(len(p.get('fields', [])) for p in pages)} fields" if pages else ""))
        steps.append(Step("fill", filled, max((p.get("filled_at") or "" for p in pages), default="")))
        return steps


    def undo_last_step(self) -> str | None:
        """Remove the artifact of the most recently completed step so `run` repeats it.
        Returns the step name, or None when only `new` is done."""
        done = [s.name for s in self.steps() if s.done and s.name != "new"]
        if self.cover_letter_waived and "letter" in done:
            done.remove("letter")  # nothing was produced, so nothing to reverse
        if not done:
            return None
        step = done[-1]
        if step == "email":
            self.email_path.unlink(missing_ok=True)
        elif step == "fill":
            field_map = self.field_map()
            for page in field_map.get("pages", []):
                page["filled_at"] = None
            self.save_field_map(field_map)
        elif step == "scan":
            self.field_map_path.unlink(missing_ok=True)
        elif step == "render":
            for path in self.document_paths().values():
                path.unlink(missing_ok=True)
        elif step == "letter":
            letter = self.cover_letter()
            letter["draft"] = True
            write_json(self.cover_letter_path, letter)
        elif step == "fetch":
            self.snapshot_html.unlink(missing_ok=True)
            self.snapshot_md.unlink(missing_ok=True)
        return step


ATTACHMENT_KIND_ORDER = ["reference", "diploma", "transcript", "certificate"]


def sort_attachments(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Order: Arbeitszeugnisse newest first, then diplomas, transcripts, certificates, then the rest."""
    def key(entry: dict[str, Any]):
        kind = entry.get("kind", "")
        rank = ATTACHMENT_KIND_ORDER.index(kind) if kind in ATTACHMENT_KIND_ORDER else len(ATTACHMENT_KIND_ORDER)
        return (rank, _neg_date(entry.get("date")))
    return sorted(entries, key=key)


def _neg_date(iso: str | None) -> str:
    """Sort key so newer dates come first; missing dates go last."""
    if not iso:
        return "~"
    padded = iso + "-01" * (2 - iso.count("-"))
    try:
        d = datetime.strptime(padded, "%Y-%m-%d")
    except ValueError as exc:
        raise JobapplyError(f"Bad date in attachments manifest: {iso!r}") from exc
    return str(10**8 - int(d.strftime("%Y%m%d")))
