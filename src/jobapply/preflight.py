"""Check an Application's inputs against Swiss convention before documents are rendered (ADR 0003).

Required Fields produce errors and block ``render``; Recommended Fields and the
softer conventions (a named contact person, no ß in German text) produce warnings
that ``status``, ``run`` and ``render`` show but never act on.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from .application import Application
from .workspace import package_file


@dataclass
class PreflightReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def preflight(app: Application) -> PreflightReport:
    report = PreflightReport()
    profile = app.profile()
    fields = app.workspace.config.get("profile_fields") or _bundled_profile_fields()
    for dotted in fields.get("required", []):
        if _is_empty(_lookup(profile, dotted)):
            report.errors.append(f"profile.json: required field {dotted!r} is empty")
    for dotted in fields.get("recommended", []):
        if _is_empty(_lookup(profile, dotted)):
            report.warnings.append(f"profile.json: recommended field {dotted!r} is empty")

    letter = app.cover_letter()
    if not app.cover_letter_waived and not letter.get("salutation") \
            and not (app.posting().get("contact") or {}).get("last_name"):
        report.warnings.append(
            "posting.json names no contact person; the letter will open with the generic salutation"
        )

    if app.language_code == "de":
        lang = app.language
        texts = {
            "profile.json": lang.resolve(profile, "profile"),
            "cover-letter.json": letter,
            f"cover-letter.{lang.code}.json": lang.resolve(app.workspace.cover_letter_fixed(lang.code), "fixed"),
        }
        hits = [name for name, data in texts.items() if _contains_eszett(data)]
        if hits:
            report.warnings.append("ß in German text (Swiss spelling uses ss): " + ", ".join(hits))
    return report


def _bundled_profile_fields() -> dict[str, list[str]]:
    """A Workspace created before `profile_fields` existed falls back to the example config's lists."""
    config = json.loads(package_file("defaults", "workspace", "config.json").read_text(encoding="utf-8"))
    return config["profile_fields"]


def _lookup(data: Any, dotted: str) -> Any:
    node = data
    for part in dotted.split("."):
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            return None
    return node


def _is_empty(value: Any) -> bool:
    """Empty means None, "", [] or {} — or a language map whose every translation is empty."""
    if value is None or value == "" or value == [] or value == {}:
        return True
    if isinstance(value, dict):
        return all(_is_empty(v) for k, v in value.items() if not k.startswith("_"))
    return False


def _contains_eszett(data: Any) -> bool:
    if isinstance(data, str):
        return "ß" in data
    if isinstance(data, dict):
        return any(_contains_eszett(v) for k, v in data.items() if not k.startswith("_"))
    if isinstance(data, list):
        return any(_contains_eszett(v) for v in data)
    return False
