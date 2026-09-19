"""`jobapply run`: the background Form Check, started once the letter step is done."""

import json

from jobapply.forms import FormCheck
from jobapply.run import FormCheckJob, start_form_check


def test_form_check_job_maps_leftovers_with_the_unattended_operator(application):
    calls = []

    def check(app):
        app.save_field_map({"pages": [{"url": "https://x", "fields": [
            {"selector": "#a", "label": "Vorname", "value": "profile:first_name"},
            {"selector": "#b", "label": "Gehalt", "value": None}]}]})
        return FormCheck(url="https://x", fields=2, matched=1)

    def mapper(app, skill, *, capture):
        calls.append((skill, capture))
        field_map = app.field_map()
        field_map["pages"][0]["fields"][1]["note"] = "yours"
        app.save_field_map(field_map)
        return 0, "mapped nothing\n"

    job = FormCheckJob(application, check=check, mapper=mapper)
    job.run()
    assert calls == [("map-fields", True)]
    assert job.summary_lines() == ["Form: open, 2 fields, 1 mapped, 1 unmatched"]


def test_form_check_job_skips_the_operator_for_gated_and_fully_matched_forms(application):
    calls = []
    mapper = lambda app, skill, *, capture: calls.append(skill)  # noqa: E731

    job = FormCheckJob(application, check=lambda app: FormCheck(url="u", gated_reason="login page at x"), mapper=mapper)
    job.run()
    assert job.summary_lines() == ["Form: gated (login page at x); fill it yourself"]
    job = FormCheckJob(application, check=lambda app: FormCheck(url="u", fields=3, matched=3), mapper=mapper)
    job.run()
    assert calls == []


def test_form_check_job_reports_failures_instead_of_raising(application):
    def boom(app):
        raise RuntimeError("chrome missing")

    job = FormCheckJob(application, check=boom)
    job.run()
    assert job.summary_lines() == ["Form Check failed: RuntimeError: chrome missing"]

    job = FormCheckJob(application, check=lambda app: FormCheck(url="u", fields=2, matched=1),
                       mapper=lambda app, skill, *, capture: (1, "line1\nboom\n"))
    job.run()
    assert job.summary_lines()[1:] == ["map-fields exited with code 1", "  line1", "  boom"]


def test_start_form_check_only_once_and_only_for_unchecked_web_forms(application):
    started = []

    class Fake:
        def __init__(self, app):
            started.append(app.slug)

        def start(self):
            pass

    job = start_form_check(application, None, Fake)
    assert started == [application.slug] and job is not None
    assert start_form_check(application, job, Fake) is job
    application.save_field_map({"pages": [], "gated": True})
    assert start_form_check(application, None, Fake) is None
    application.data["form_url"] = "mailto:hr@x.ch"
    application.field_map_path.unlink()
    assert start_form_check(application, None, Fake) is None
    assert started == [application.slug]


def test_letter_untouched_until_anyone_writes_into_it(application):
    assert application.letter_untouched()
    application.cover_letter_path.write_text(json.dumps({"draft": True, "intro": ["x"], "body": []}))
    assert not application.letter_untouched()
    application.data["cover_letter"] = False
    assert not application.letter_untouched()


def test_run_starts_the_form_check_only_once_the_letter_is_done_and_hands_it_back_on_pause(application, monkeypatch):
    """No unattended Operator may overlap the interview: the Form Check starts at the
    letter-done transition, and a pause during the PDF review returns the running job
    so `run` can wait for it."""
    import jobapply.render
    import jobapply.run as run_mod

    application.snapshot_html.write_text("<html></html>")
    application.cover_letter_path.write_text(json.dumps({"draft": True, "intro": ["Hallo"], "body": ["…"]}))
    events = []

    class Fake:
        def __init__(self, app):
            events.append("check started")

        def start(self):
            pass

    def prompt(text, choices, default):
        events.append(f"prompt: {text[:12]}")
        return "d" if text.startswith("a to run") or text.startswith("Enter to re-check") else "q"

    monkeypatch.setattr(run_mod, "_prompt", prompt)
    monkeypatch.setattr(run_mod, "operator_command", lambda *a, **k: None)
    monkeypatch.setattr(run_mod, "show_preflight", lambda app: None)
    monkeypatch.setattr(jobapply.render, "render_application", lambda app: {})

    job = run_mod._run(application, Fake)
    assert isinstance(job, Fake)
    assert events == ["prompt: Enter to re-", "check started", "prompt: Open the PDF"]
