# jobapply

A job-application pipeline with an AI assistant in the steps that need judgment. Your data lives in one JSON profile in a private workspace; the CLI renders your CV and cover letter to PDF, bundles them with your certificates, and pre-fills the employer's web form in a real browser window. Where rules are not enough — reading the posting, drafting the letter, mapping an unfamiliar form, importing your existing documents — a coding agent (Claude Code or any agent that reads `SKILL.md` files) takes over through the [skills](#agent-skills) shipped in this repo, and writes its result into a file you review.

**It never presses submit.** Every step is a command you run; between steps you check and edit files; at the end you review the form and send it yourself. The CLI itself makes no LLM calls and needs no API key.

## Quick start

Requires Python ≥ 3.11 and Google Chrome (rendering and form filling both use it through Playwright).

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e .
jobapply init workspace        # creates ./workspace with fictional example data
```

Then fill the workspace — by hand (see below) or with the `/setup-workspace` skill, which walks you through placing your photo, CV and certificates and imports them — and start your first application:

```bash
jobapply run
```

`run` asks for the posting URL, fetches the page and proposes company, role and form URL for you to confirm, then works through every step and stops only where you're needed. `jobapply` finds `./workspace` automatically when you run it from the project folder; elsewhere pass `--workspace <dir>` or set `JOBAPPLY_WORKSPACE`.

## How a run goes

| Step   | Who        | What happens                                                                                                                                                                                                                    |
| ------ | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| new    | you        | `run` asks for the posting URL, fetches it and proposes company, role and form URL (from the page's JSON-LD, title or apply link); you confirm or correct them and choose the language                                          |
| fetch  | tool       | saves a snapshot of the posting (HTML + readable text) and extracts what it can into `posting.json` — done together with `new`; `jobapply fetch` re-fetches                                                                     |
| letter | you        | complete `posting.json`, write the job-specific half of the letter in `cover-letter.json` — by hand or with the `/extract-posting` and `/draft-cover-letter` skills; `[e]` opens the letter in your editor, `[d]` marks it done |
| render | tool       | CV, cover letter and the Dossier (letter, CV, then all attachments in one PDF) into `out/`; offers to open them                                                                                                                 |
| scan   | tool + you | opens the form in Chrome, detects every field, guesses what goes where, writes `form-fields.json`; you fix what it missed (or the `/map-fields` skill)                                                                          |
| fill   | tool       | fills the fields and uploads the files, then leaves the browser open                                                                                                                                                            |
| submit | you        | review the form and press the button                                                                                                                                                                                            |

Quit at any pause with `q`; `jobapply run <slug>` resumes at the same step, because progress is read from the files in the application folder. `jobapply back <slug>` undoes the last completed step. `jobapply status` shows every application, with what still blocks `render` (an empty required field) and what convention warns about.

Each step also exists as its own command (`new`, `fetch`, `render`, `scan`, `fill`) if you'd rather drive them yourself; `jobapply --help` lists them. `jobapply open <slug> [letter|posting|fields|folder]` opens a file in your editor (`"editor"` in `config.json`, e.g. `"code -r"`). `jobapply new <posting-url>` is all it takes to start one; `--company`, `--role`, `--form` and `--lang` skip the corresponding prompt. Any unique part of a slug works as the argument, e.g. `jobapply run acme`.

`scan` and `fill` act on whatever page the browser is showing and can be repeated, so multi-page forms are handled page by page (`[s]` scan, `[f]` fill, `[q]` quit inside the session). The browser profile is persistent, so a login survives between runs.

## Your workspace

Everything personal lives in the workspace and is git-ignored in this repo; keep it in a private repository of its own if you like.

```
workspace/
  config.json              default language, extra language packs, browser channel, required/recommended profile fields, Style and accent colour
  profile.json             you: contact, personal details, summary, experience, education, skills, languages, certifications, interests
  photo.jpg                optional photo used on the CV (path set in profile.json)
  cover-letter.de.json     the half of the cover letter that is the same for every job, per language
  cover-letter.en.json
  field-synonyms.json      form labels → profile fields; add a label whenever scan misses one
  sources/                 your current CV and old cover letters; read by the import-documents skill, never uploaded
  attachments/             PDFs to upload with every application + manifest.json (kind, date, title)
  templates/               optional overrides of cv.html, cover-letter.html, style.css; your own Styles in templates/styles/
  applications/<slug>/     one folder per application (see docs/data-files.md)
  .browser/                the tool's own Chrome profile (logins)
```

**Languages.** Any string in `profile.json` can be a plain string or a language map `{"de": "...", "en": "..."}`. Rendering fails if a translation for the application's language is missing — on purpose. Dates are ISO (`2025-01`) and formatted per language. German and English are built in; other languages are added under `"languages"` in `config.json`.

**Cover letter.** The letter is assembled as: your specific `intro` → fixed `about_me` → your specific `body` → fixed `closing`. The subject line is built from the posting (`subject_default` / `subject_with_reference`, e.g. "Bewerbung als {role}, Referenz {reference}") unless `cover-letter.json` sets its own. The salutation is built from the contact person in `posting.json` using the `salutation_named` patterns (`"Frau": "Sehr geehrte Frau {last_name}"` — Swiss letters put no comma after it), or falls back to `salutation_default`; `render` warns when no contact person is known. Markdown is allowed in paragraphs. There is no enclosure list: a form may accept fewer files than you have. A form that wants no letter at all: set `"cover_letter": false` in the application's `application.json` and the letter step is skipped.

**Required and recommended fields.** `config.json` lists which `profile.json` fields must be filled before `render` produces anything (`profile_fields.required`: name, address, phone, email, nationality, education, languages) and which only trigger a warning when empty (`recommended`: photo, birth date). The defaults follow German-speaking Swiss convention ([ADR 0003](docs/adr/0003-documents-follow-swiss-convention.md)); edit the lists for another country. `render`, `run` and `status` also warn about a ß in German text.

**Styles.** The PDFs' look is a Style, one CSS file in `templates/styles/`: `classic` (thin rules, monochrome — the default), `bar` (HSG-style: white capitals on coloured heading bars, dates right-aligned), `bare` (ETH-style: unlabelled personal line, small-caps headings, smaller photo) and `accent` (classic with the accent colour on name, headings and dates). Choose with `"style"` in `config.json`, or per application in `application.json`; `"letter_style"` (same places) gives the cover letter its own Style, e.g. `classic` for a plain black letter next to a `bar` CV; `"accent"` in `config.json` sets the one colour. Every Style keeps the page structure the Swiss templates share ([research](docs/research/swiss-cv-layout-and-design.md)); add your own as `workspace/templates/styles/<name>.css`.

**Attachments.** `manifest.json` gives each PDF a `kind` (`reference`, `diploma`, `transcript`, `certificate`), a `date` and a `title` per language. New applications select all of them; remove entries from `attachments` in an application's `application.json` to leave some out. Merge order: reference letters newest first, then diplomas, transcripts, certificates.

**Output names** follow the language: `Lebenslauf_<Name>.pdf`, `Motivationsschreiben_<Name>.pdf`, `Bewerbungsunterlagen_<Name>.pdf` (the Dossier) in German; `CV_…`, `CoverLetter_…`, `ApplicationDocuments_…` in English. Patterns live in the language packs.

## Form filling

Fields are matched by two deterministic signals: the HTML `autocomplete` attribute, and the Synonym Table in `field-synonyms.json` (labels per language, matched as whole words; longest match wins). File inputs get `document:cv`, `document:cover_letter`, `attachments:all` (multi-file) or `document:merged` (the Dossier, for a single "documents" slot). Checkboxes, radios and questions like salary or start date are left for you: set their `value` in `form-fields.json` (`literal:…`) or answer them in the browser.

**Sites that need a login** (LinkedIn postings, an ATS behind single sign-on): run `jobapply login` once — it opens the workspace's own Chrome profile on LinkedIn's login page (`jobapply login <url>` for another site), you log in, press Enter. Fetching and form filling both use that profile, so the session carries over; the tool never sees or stores your credentials. A fetch that lands on a login page fails with a hint instead of saving an empty snapshot.

Every ATS is different. Expect the first scan on a new platform to miss a few labels — add them to `field-synonyms.json` (or let `/map-fields` do it) and the next application on that platform goes smoother. Cross-origin iframes cannot be scanned; that's a browser limit.

## Agent skills

The judgment steps are handled by skills in `.agents/skills/`, written for any coding agent that reads `SKILL.md` files (Claude Code finds them via `.claude/skills/`; other agents read them from `.agents/skills/` or as plain instructions). Two set up the workspace:

- `setup-workspace` — asks where your photo, current CV, old cover letters and certificates go, checks the folders, then runs `import-documents`
- `import-documents` — reads the PDFs in `sources/` and `attachments/` and fills `profile.json`, the fixed cover-letter halves, `manifest.json` and `config.json`, and asks you for any required or recommended field no document covers; existing values win, translations are flagged; run it again after adding a document

Three take an application slug:

- `extract-posting` — completes `posting.json` from the snapshot (contact, address, requirements)
- `draft-cover-letter` — offers one sentence per posting requirement (or a question where your profile is silent), lets you pick and confirm three to five, then drafts `intro`/`body` in `cover-letter.json` as plain prose (leaves `draft: true`) and opens it in your editor
- `map-fields` — resolves unmatched fields in `form-fields.json` and teaches the Synonym Table

In Claude Code that's `/extract-posting <slug>` etc. The CLI itself contains no LLM and needs no API key; see `docs/adr/0001`.

## Vocabulary and decisions

- `CONTEXT.md` — the terms (Profile, Application, Posting, Form, Attachment, Field Map, Dossier, Style, Required Field, …)
- `docs/adr/` — why the tool is shaped this way; `docs/research/` — the Swiss application conventions the defaults follow, with sources
- `docs/data-files.md` — every file in an application folder, how progress is derived, and the `value` syntax of the Field Map

## Development

```
pip install -e '.[dev]'
pytest
```

Chrome-dependent paths (PDF rendering, scan/fill) are not covered by the unit tests; try them against a local HTML form.
