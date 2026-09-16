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
