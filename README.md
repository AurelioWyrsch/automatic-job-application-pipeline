# jobapply

A command-line job-application pipeline. Your data lives in one JSON profile; the tool renders your CV and cover letter to PDF, bundles them with your certificates, and pre-fills the employer's web form in a real browser window.

**It never presses submit.** Every step is a command you run; between steps you check and edit files; at the end you review the form and send it yourself.

## How it works

The short way: `jobapply run` asks for the two URLs, then does every automatic step and pauses wherever you need to act (write the letter, check the PDFs, review the form). Quit at any pause; `jobapply run <slug>` resumes there.

The individual steps, if you prefer to drive them yourself:

```
jobapply new     --company "Acme AG" --role "Data Scientist" --posting <url> --form <url> --lang de
jobapply fetch   <slug>     # saves a snapshot of the posting, extracts what it can into posting.json
   → you complete posting.json and write cover-letter.json   (or /extract-posting, /draft-cover-letter in Claude Code)
jobapply render  <slug>     # CV, cover letter and a merged PDF with your attachments into out/
   → you open the PDFs
jobapply scan    <slug>     # opens the form in Chrome, detects its fields, writes form-fields.json
   → you fix unmatched fields   (or /map-fields)
jobapply fill    <slug>     # fills the fields, uploads the files, leaves the browser open
   → you review and press submit
jobapply status             # which step every application is at
```

`scan` and `fill` work on whatever page the browser is showing and can be repeated, so multi-page forms are handled page by page. The browser profile is persistent, so a login survives between runs.

## Install

Requires Python ≥ 3.11 and Google Chrome (rendering and form filling both use it through Playwright).

```
python -m venv .venv && . .venv/bin/activate
pip install -e .
jobapply init workspace          # creates a workspace with fictional example data
export JOBAPPLY_WORKSPACE=$PWD/workspace   # or pass --workspace
```

## Your workspace

Everything personal lives in the workspace and is git-ignored in this repo; keep it in a private repository of its own if you like.

```
workspace/
  config.json              default language, extra language packs, browser channel
  profile.json             you: contact, summary, experience, education, skills, languages, certifications
  photo.png                optional photo used on the CV
  cover-letter.de.json     the half of the cover letter that is the same for every job, per language
  cover-letter.en.json
  field-synonyms.json      form labels → profile fields; add a label whenever scan misses one
  attachments/             PDFs to upload with every application + manifest.json (kind, date, title)
  templates/               optional overrides of cv.html, cover-letter.html, style.css
  applications/<slug>/     one folder per application (see docs/data-files.md)
  .browser/                the tool's own Chrome profile (logins)
```

Any string in `profile.json` can be a plain string or a language map `{"de": "...", "en": "..."}`. Rendering fails if a translation for the application's language is missing — on purpose. Dates are ISO (`2025-01`) and formatted per language. Other languages are added under `"languages"` in `config.json`.

## Claude Code

The repo ships three skills that operate on the files the CLI leaves for you: `/extract-posting <slug>`, `/draft-cover-letter <slug>`, `/map-fields <slug>`. The CLI itself contains no LLM and needs no API key; see `docs/adr/`.

## Vocabulary and decisions

- `CONTEXT.md` — the terms (Profile, Application, Posting, Form, Attachment, Field Map, …)
- `docs/adr/` — why the tool is shaped this way
- `docs/data-files.md` — every file in an application folder and the `value` syntax of the Field Map

## Development

```
pip install -e '.[dev]'
pytest
```
