"""Language handling: resolving per-field language maps and formatting dates.

Any string value in Profile or Application data may be either a plain string
or a map ``{"de": "...", "en": "..."}``. Resolving a map for a Language it
does not contain is an error, never a silent fallback - an employer notices a
German sentence in an English CV instantly.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from .errors import JobapplyError

# Built-in language packs. A Workspace's config.json may add or override
# entries under "languages" to support further languages.
BUILTIN_LANGUAGES: dict[str, dict[str, Any]] = {
    "de": {
        "months": ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
                   "August", "September", "Oktober", "November", "Dezember"],
        "months_short": ["Jan.", "Feb.", "März", "Apr.", "Mai", "Juni", "Juli",
                         "Aug.", "Sept.", "Okt.", "Nov.", "Dez."],
        "present": "heute",
        "date_month_year": "{month:02d}.{year}",
        "date_long": "{day}. {month_name} {year}",
        "date_short": "{day:02d}.{month:02d}.{year}",
        "date_range_separator": " – ",
        "documents": {
            "cv": "Lebenslauf",
            "cover_letter": "Motivationsschreiben",
            "merged": "Bewerbungsunterlagen",
        },
        "filenames": {
            "cv": "Lebenslauf_{first}{last}.pdf",
            "cover_letter": "Motivationsschreiben_{first}{last}.pdf",
            "merged": "Bewerbungsunterlagen_{first}{last}.pdf",
        },
        "labels": {
            "experience": "Berufserfahrung", "education": "Ausbildung", "skills": "Kenntnisse",
            "languages": "Sprachkenntnisse", "certifications": "Zertifikate", "interests": "Interessen",
            "birth_date": "Geburtsdatum", "nationality": "Nationalität", "permit": "Bewilligung",
            "marital_status": "Zivilstand",
            "portfolio": "Portfolio", "linkedin": "LinkedIn", "github": "GitHub",
        },
        "apply_labels": ["Jetzt bewerben", "Jetzt online bewerben", "Online bewerben", "Bewerben"],
    },
    "en": {
        "months": ["January", "February", "March", "April", "May", "June", "July",
                   "August", "September", "October", "November", "December"],
        "months_short": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul",
                         "Aug", "Sep", "Oct", "Nov", "Dec"],
        "present": "present",
        "date_month_year": "{month_short} {year}",
        "date_long": "{day} {month_name} {year}",
        "date_short": "{day:02d}/{month:02d}/{year}",
        "date_range_separator": " – ",
        "documents": {
            "cv": "CV",
            "cover_letter": "Cover letter",
            "merged": "Application documents",
        },
        "filenames": {
            "cv": "CV_{first}{last}.pdf",
            "cover_letter": "CoverLetter_{first}{last}.pdf",
            "merged": "ApplicationDocuments_{first}{last}.pdf",
        },
        "labels": {
            "experience": "Experience", "education": "Education", "skills": "Skills",
            "languages": "Languages", "certifications": "Certifications", "interests": "Interests",
            "birth_date": "Date of birth", "nationality": "Nationality", "permit": "Work permit",
            "marital_status": "Marital status",
            "portfolio": "Portfolio", "linkedin": "LinkedIn", "github": "GitHub",
        },
        "apply_labels": ["Apply now", "Apply online", "Apply"],
    },
}


def deep_merge(base: dict, override: dict) -> dict:
    """Return a new dict with ``override`` merged recursively into ``base``."""
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


class Language:
    """One Language's formatting rules, built from the built-ins plus config."""

    def __init__(self, code: str, config_languages: dict[str, Any] | None = None):
        pack = BUILTIN_LANGUAGES.get(code, {})
        extra = (config_languages or {}).get(code, {})
        merged = deep_merge(pack, extra)
        if not merged.get("months"):
            raise JobapplyError(
                f"Language '{code}' is not built in; define it under \"languages\" in config.json "
                f"(months, present, date_month_year, date_long, documents, filenames)."
            )
        self.code = code
        self.pack = merged
        self.known_codes = set(BUILTIN_LANGUAGES) | set(config_languages or {})

    def resolve(self, value: Any, path: str = "") -> Any:
        """Resolve a plain string or a language map to a string for this Language.

        Nested dicts and lists are resolved recursively so a whole Profile can
        be resolved once before templating.
        """
        if isinstance(value, dict):
            if _is_language_map(value, self.known_codes):
                if self.code not in value:
                    raise JobapplyError(
                        f"Missing '{self.code}' translation at {path or '<root>'}: {value}"
                    )
                return value[self.code]
            return {k: self.resolve(v, f"{path}.{k}" if path else k) for k, v in value.items()}
        if isinstance(value, list):
            return [self.resolve(v, f"{path}[{i}]") for i, v in enumerate(value)]
        return value

    def _parts(self, iso: str) -> tuple[int, int, int | None]:
        try:
            pieces = [int(p) for p in iso.split("-")]
        except ValueError as exc:
            raise JobapplyError(f"Bad ISO date '{iso}' (expected YYYY, YYYY-MM or YYYY-MM-DD)") from exc
        year = pieces[0]
        month = pieces[1] if len(pieces) > 1 else 1
        day = pieces[2] if len(pieces) > 2 else None
        return year, month, day

    def _fmt(self, pattern: str, iso: str) -> str:
        year, month, day = self._parts(iso)
        return pattern.format(
            year=year, month=month, day=day if day is not None else 1,
            month_name=self.pack["months"][month - 1],
            month_short=self.pack["months_short"][month - 1],
        )

    def month_year(self, iso: str | None) -> str:
        if not iso:
            return self.pack["present"]
        return self._fmt(self.pack["date_month_year"], iso)

    def long_date(self, iso: str | None = None) -> str:
        iso = iso or date.today().isoformat()
        return self._fmt(self.pack["date_long"], iso)

    def short_date(self, iso: str) -> str:
        return self._fmt(self.pack.get("date_short", "{year}-{month:02d}-{day:02d}"), iso)

    def date_range(self, start: str, end: str | None) -> str:
        return f"{self.month_year(start)}{self.pack['date_range_separator']}{self.month_year(end)}"

    def document_title(self, kind: str) -> str:
        return self.pack["documents"][kind]

    def filename(self, kind: str, first: str, last: str) -> str:
        pattern = self.pack["filenames"][kind]
        return pattern.format(first=_compact(first), last=_compact(last))



def _is_language_map(value: dict, known_codes: set[str]) -> bool:
    """A non-empty dict whose keys are all known language codes and whose values are strings."""
    return bool(value) and all(k in known_codes for k in value) and all(
        isinstance(v, str) for v in value.values()
    )


def _compact(name: str) -> str:
    return "".join(part.capitalize() for part in name.replace("-", " ").split())
