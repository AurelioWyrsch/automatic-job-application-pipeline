"""Heuristic matching of Form fields to Profile values, documents and Attachments.

Two signals, no LLM:

1. the HTML ``autocomplete`` attribute (a web standard, reliable when present);
2. the Synonym Table (``field-synonyms.json``): labels per Language that
   identify a target, matched as whole words in the field's label, placeholder,
   name and id. The longest matching synonym wins; a hit in the visible label
   beats a hit in the technical name.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

# https://html.spec.whatwg.org/multipage/form-control-infrastructure.html#autofill
AUTOCOMPLETE_TARGETS = {
    "given-name": "profile:first_name",
    "family-name": "profile:last_name",
    "email": "profile:contact.email",
    "tel": "profile:contact.phone",
    "tel-national": "profile:contact.phone",
    "street-address": "profile:contact.street",
    "address-line1": "profile:contact.street",
    "postal-code": "profile:contact.postal_code",
    "address-level2": "profile:contact.city",
    "country-name": "profile:contact.country",
    "bday": "profile:personal.birth_date",
    "honorific-prefix": "profile:personal.salutation",
    "url": "profile:links.portfolio",
}

FILE_TARGET_PREFIXES = ("document:", "attachment:", "attachments:")


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)  # camelCase -> camel Case
    text = re.sub(r"[^a-zA-Z0-9]+", " ", text).strip().lower()
    return text


def _candidates(synonyms: dict[str, Any], lang: str) -> list[tuple[str, str]]:
    """(normalized synonym, target) pairs from the 'any' section plus the Language section."""
    pairs: list[tuple[str, str]] = []
    for section in ("any", lang):
        for target, labels in (synonyms.get(section) or {}).items():
            if target.startswith("_"):
                continue
            for label in labels:
                pairs.append((normalize(label), target))
    return pairs


def _contains_words(haystack: str, needle: str) -> bool:
    return re.search(rf"(?<![a-z0-9]){re.escape(needle)}(?![a-z0-9])", haystack) is not None


def match_field(field: dict[str, Any], synonyms: dict[str, Any], lang: str) -> tuple[str | None, str]:
    """Return (target, reason) for a scanned field, or (None, reason)."""
    is_file = field.get("type") == "file"
    if field.get("type") in ("checkbox", "radio"):
        return None, "checkbox/radio: set value by hand (literal:<option label> or literal:true)"

    if not is_file:
        auto = (field.get("autocomplete") or "").split()
        for token in auto:
            if token in AUTOCOMPLETE_TARGETS:
                return AUTOCOMPLETE_TARGETS[token], f"autocomplete={token}"

    texts = {
        "label": normalize(field.get("label") or ""),
        "hints": normalize(" ".join(field.get("hints") or [])),
        "placeholder": normalize(field.get("placeholder") or ""),
        "name": normalize(field.get("name") or ""),
        "id": normalize(field.get("id") or ""),
    }
    priority = ["label", "placeholder", "hints", "name", "id"]

    best: tuple[int, int, str, str] | None = None  # (-source rank, length, synonym, target)
    for synonym, target in _candidates(synonyms, lang):
        if not synonym:
            continue
        if is_file != target.startswith(FILE_TARGET_PREFIXES):
            continue
        for rank, source in enumerate(priority):
            if texts[source] and _contains_words(texts[source], synonym):
                key = (-rank, len(synonym), synonym, target)
                if best is None or key > best:
                    best = key
                break
    if best is None:
        return None, "no synonym matched"
    _, _, synonym, target = best
    if target == "attachments:all" and not field.get("multiple"):
        target = "document:merged"
    return target, f"synonym:{synonym}"
