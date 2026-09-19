from jobapply.application import EMPTY_POSTING
from jobapply.i18n import deep_merge
from jobapply.posting import apply_job_posting, find_job_postings, propose, to_markdown
from tests.conftest import POSTING_HTML

HTML = POSTING_HTML


def test_json_ld_extraction_fills_only_empty_fields():
    posting = deep_merge(EMPTY_POSTING, {"company": "Already set"})
    jps = find_job_postings(HTML)
    assert len(jps) == 1
    updated = apply_job_posting(posting, jps[0])
    assert posting["company"] == "Already set"
    assert posting["role"] == "Data Scientist"
    assert posting["reference"] == "REQ-1"
    assert posting["address"]["city"] == "Zürich"
    assert posting["description"] == "Hi"
    assert "company" not in updated and "role" in updated


def test_markdown_snapshot_strips_chrome():
    md = to_markdown(HTML)
    assert "# Data Scientist" in md and "- Python" in md and "x" not in md.splitlines()[0]


def test_proposal_from_json_ld_and_apply_link():
    p = propose(HTML, "https://jobs.acme.ch/job/1", apply_labels=["Jetzt bewerben", "Bewerben"])
    assert (p.company, p.role) == ("Acme AG", "Data Scientist")
    assert p.form_url == "https://jobs.acme.ch/apply/1"


def test_proposal_falls_back_to_page_title():
    html = "<html><head><title>Data Engineer 80-100% | Bühler AG</title></head><body><h1>Data Engineer 80-100%</h1><a href='#top'>Bewerben</a></body></html>"
    p = propose(html, "https://buhler.ch/jobs/7", apply_labels=["Bewerben"])
    assert (p.company, p.role) == ("Bühler AG", "Data Engineer 80-100%")
    assert p.form_url == "https://buhler.ch/jobs/7"


def test_proposal_leaves_company_empty_when_title_is_ambiguous():
    html = "<html><head><title>Acme AG – Data Engineer 80-100%</title></head><body><h1>Data Engineer (80–100 %)</h1></body></html>"
    p = propose(html, "https://x.ch/j", apply_labels=[])
    assert (p.company, p.role) == ("", "Data Engineer (80–100 %)")


def test_apply_label_must_be_the_whole_link_text():
    html = ('<html><body><a href="/how">How to apply</a><a href="/go">Jetzt bewerben →</a></body></html>')
    p = propose(html, "https://x.ch/j", apply_labels=["Apply", "Jetzt bewerben"])
    assert p.form_url == "https://x.ch/go"


def test_proposal_from_bare_page_is_empty():
    p = propose("<html><body><p>nothing</p></body></html>", "https://x.ch/j", apply_labels=["Apply"])
    assert (p.company, p.role) == ("", "")


def test_login_wall_is_detected_from_the_redirect():
    from jobapply.browser import looks_like_login_wall
    job = "https://www.linkedin.com/jobs/view/123"
    assert looks_like_login_wall(job, "https://www.linkedin.com/authwall?trk=x&sessionRedirect=...")
    assert looks_like_login_wall("https://ats.example.com/job/1", "https://ats.example.com/login?next=/job/1")
    assert not looks_like_login_wall(job, job + "/?refId=abc")          # same page, tracking added
    assert not looks_like_login_wall(job, "https://ch.linkedin.com/jobs/view/123")  # locale redirect


def test_apply_link_may_be_a_mailto_when_no_web_form_exists():
    html = '<html><body><a href="mailto:hr@acme.ch?subject=Job">Jetzt bewerben</a></body></html>'
    p = propose(html, "https://x.ch/j", apply_labels=["Jetzt bewerben"])
    assert p.form_url == "mailto:hr@acme.ch"


def test_web_form_wins_over_mailto():
    # POSTING_HTML offers both "Bewerben" (mailto) and "Jetzt bewerben" (/apply/1), mailto first
    p = propose(HTML, "https://jobs.acme.ch/job/1", apply_labels=["Bewerben", "Jetzt bewerben"])
    assert p.form_url == "https://jobs.acme.ch/apply/1"
