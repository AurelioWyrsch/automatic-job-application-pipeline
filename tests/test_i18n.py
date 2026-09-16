import pytest

from jobapply.errors import JobapplyError
from jobapply.i18n import Language


def test_resolves_language_maps_recursively():
    lang = Language("en")
    data = {"title": {"de": "Hallo", "en": "Hello"}, "items": [{"de": "a", "en": "b"}], "plain": "x",
            "contact": {"city": "Widen", "phone": "1"}}
    assert lang.resolve(data) == {"title": "Hello", "items": ["b"], "plain": "x",
                                  "contact": {"city": "Widen", "phone": "1"}}


def test_missing_translation_fails_loudly():
    with pytest.raises(JobapplyError, match="Missing 'en' translation at profile.summary"):
        Language("en").resolve({"summary": {"de": "nur deutsch"}}, "profile")


def test_dates_per_language():
    de, en = Language("de"), Language("en")
    assert de.month_year("2025-01") == "01.2025"
    assert en.month_year("2025-01") == "Jan 2025"
    assert de.month_year(None) == "heute"
    assert en.date_range("2021-09", None) == "Sep 2021 – present"
    assert de.long_date("2026-09-16") == "16. September 2026"
    assert de.short_date("1998-04-12") == "12.04.1998"


def test_filenames():
    assert Language("de").filename("cv", "Mara", "Muster") == "Lebenslauf_MaraMuster.pdf"
    assert Language("en").filename("merged", "mara", "de la cruz") == "ApplicationDocuments_MaraDeLaCruz.pdf"


def test_unknown_language_needs_config():
    with pytest.raises(JobapplyError, match="not built in"):
        Language("fr")
    fr = Language("fr", {"fr": {"months": ["janvier"] * 12, "months_short": ["janv."] * 12, "present": "présent",
                                "date_month_year": "{month:02d}/{year}", "date_long": "{day} {month_name} {year}",
                                "documents": {"cv": "CV"}, "filenames": {"cv": "CV_{first}{last}.pdf"}}})
    assert fr.month_year("2025-03") == "03/2025"
