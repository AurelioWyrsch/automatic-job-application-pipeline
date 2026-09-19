import json

from jobapply.application import Application


def test_create_and_find(workspace, application):
    assert application.slug.endswith("-acme-ag-data-scientist")
    assert Application.find(workspace, "acme").slug == application.slug
    assert application.data["attachments"] == ["cert.pdf", "diplom.pdf", "zeugnis-a.pdf", "zeugnis-b.pdf"]


def test_attachment_order(application):
    files = [e["file"] for e in application.selected_attachments()]
    assert files == ["zeugnis-b.pdf", "zeugnis-a.pdf", "diplom.pdf", "cert.pdf"]


def test_steps_reflect_files(application):
    steps = {s.name: s.done for s in application.steps()}
    assert steps == {"new": True, "fetch": False, "letter": False, "render": False, "scan": False, "fill": False}


def test_slug_is_cut_at_a_word_boundary():
    from jobapply.application import slugify
    assert slugify("Corealis Consulting AG") == "corealis-consulting-ag"
    assert slugify("Working Student – Data, Infrastructure & Integrations and/or AI/ML Application Development") == "working-student-data-infrastructure"
    assert len(slugify("x" * 100)) == 40


def test_undo_last_step_walks_backwards(application):
    import json
    application.cover_letter_path.write_text(json.dumps({"draft": False, "subject": "s", "intro": ["x"], "body": []}))
    assert [s.name for s in application.steps() if s.done] == ["new", "letter"]
    assert application.undo_last_step() == "letter"
    assert [s.name for s in application.steps() if s.done] == ["new"]
    assert application.undo_last_step() is None


def test_mark_letter_done_completes_the_letter_step(application):
    import json
    application.cover_letter_path.write_text(json.dumps({"draft": True, "subject": "s", "intro": ["x"], "body": []}))
    application.mark_letter_done()
    assert [s.name for s in application.steps() if s.done] == ["new", "letter"]
    assert application.cover_letter()["intro"] == ["x"]


def test_editable_paths(application):
    assert application.editable("letter") == application.cover_letter_path
    assert application.editable("posting") == application.posting_path
    assert application.editable("fields") == application.field_map_path
    assert application.editable("folder") == application.folder


def test_waived_cover_letter_skips_the_letter_step(application):
    application.data["cover_letter"] = False
    application.save()
    assert application.cover_letter_waived
    steps = {s.name: s for s in application.steps()}
    assert steps["letter"].done and "waived" in steps["letter"].detail
    assert sorted(application.document_paths()) == ["cv", "merged"]
    # nothing to reverse for the letter: back stops at `new`
    assert application.undo_last_step() is None


def test_by_email_application_has_an_email_step_instead_of_scan_and_fill(application):
    application.data["form_url"] = "mailto:hr@acme.ch?subject=x"
    application.save()
    assert application.application_email == "hr@acme.ch"
    assert [s.name for s in application.steps()] == ["new", "fetch", "letter", "render", "email"]
    application.email_path.write_text("To: hr@acme.ch\n")
    steps = {s.name: s for s in application.steps()}
    assert steps["email"].done and "hr@acme.ch" in steps["email"].detail
    assert application.undo_last_step() == "email"
    assert not application.email_path.exists()
    assert application.editable("email") == application.email_path


def test_cover_letter_accepts_intro_and_body_typed_as_strings(application):
    """A hand-written (or Operator-written) letter may hold a paragraph as one string; blank lines split paragraphs."""
    application.cover_letter_path.write_text(json.dumps({
        "draft": False, "intro": "Ihre Migration der Controlling-Reports ist genau meine Aufgabe als Werkstudentin.",
        "body": "Erster Absatz.\n\nZweiter Absatz.\n", "outlook": "Ein Pensum von 50 % passt für mich.",
    }), encoding="utf-8")
    letter = application.cover_letter()
    assert letter["intro"] == ["Ihre Migration der Controlling-Reports ist genau meine Aufgabe als Werkstudentin."]
    assert letter["body"] == ["Erster Absatz.", "Zweiter Absatz."]
    assert letter["outlook"] == ["Ein Pensum von 50 % passt für mich."]
    assert {s.name: s.done for s in application.steps()}["letter"] is True
