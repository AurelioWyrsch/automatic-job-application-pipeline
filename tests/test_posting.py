from jobapply.application import EMPTY_POSTING
from jobapply.i18n import deep_merge
from jobapply.posting import apply_job_posting, find_job_postings, to_markdown

HTML = """<html><head><script type="application/ld+json">
{"@context":"https://schema.org","@graph":[{"@type":"Organization"},{"@type":"JobPosting","title":"Data Scientist",
"identifier":{"@type":"PropertyValue","name":"Acme","value":"REQ-1"},"hiringOrganization":{"name":"Acme AG"},
"jobLocation":{"address":{"streetAddress":"Weg 1","postalCode":"8000","addressLocality":"Zürich","addressCountry":"CH"}},
"description":"<p>Hi</p>"}]}</script></head>
<body><nav>x</nav><main><h1>Data Scientist</h1><p>Intro</p><ul><li>Python</li></ul></main></body></html>"""


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
