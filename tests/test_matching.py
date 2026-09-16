from jobapply.matching import match_field, normalize

SYN = {
    "any": {"document:cv": ["cv", "lebenslauf"], "attachments:all": ["dokumente", "documents"],
            "profile:contact.email": ["e-mail", "email"]},
    "de": {"profile:first_name": ["vorname"], "profile:last_name": ["nachname", "name"]},
    "en": {"profile:first_name": ["first name"], "profile:last_name": ["last name", "name"]},
}


def field(**kw):
    base = {"type": "text", "label": "", "hints": [], "placeholder": "", "name": "", "id": "", "autocomplete": "", "multiple": False}
    return {**base, **kw}


def test_normalize_splits_camel_case_and_accents():
    assert normalize("firstName") == "first name"
    assert normalize("Nationalität*") == "nationalitat"


def test_longest_synonym_wins():
    assert match_field(field(label="Last name"), SYN, "en")[0] == "profile:last_name"
    assert match_field(field(label="First name"), SYN, "en")[0] == "profile:first_name"


def test_label_beats_technical_name():
    assert match_field(field(label="Vorname", name="lastName"), SYN, "de")[0] == "profile:first_name"


def test_autocomplete_is_trusted():
    assert match_field(field(label="???", autocomplete="given-name"), SYN, "de") == ("profile:first_name", "autocomplete=given-name")


def test_file_inputs_only_match_file_targets():
    assert match_field(field(type="file", label="Vorname"), SYN, "de")[0] is None
    assert match_field(field(type="file", label="Lebenslauf"), SYN, "de")[0] == "document:cv"
    assert match_field(field(label="Lebenslauf"), SYN, "de")[0] is None


def test_single_file_documents_slot_gets_merged_pdf():
    assert match_field(field(type="file", label="Dokumente"), SYN, "de")[0] == "document:merged"
    assert match_field(field(type="file", label="Dokumente", multiple=True), SYN, "de")[0] == "attachments:all"


def test_whole_word_matching():
    assert match_field(field(label="Firmenname"), SYN, "de")[0] is None
