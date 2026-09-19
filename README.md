# jobapply

A job-application pipeline with an AI assistant in the steps that need judgment. Your data lives in a few JSON files in a private workspace; the CLI renders your CV and cover letter to PDF, bundles them with your certificates, and pre-fills the employer's web form in a real browser window. Where rules are not enough — reading the posting, drafting the letter, mapping an unfamiliar form, importing your existing documents — a coding agent (Claude Code or any agent that reads `SKILL.md` files) takes over through the [skills](#agent-skills) shipped in this repo, and writes its result into a file you review.

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

`jobapply run <posting-url>` starts an application from a posting and asks nothing: it fetches the page, names the folder from what the page says, has your Operator read the posting, then works through every step and stops only where you're needed. `run` without an argument lists your open applications to continue, or asks for the URL. `jobapply` finds `./workspace` automatically when you run it from the project folder; elsewhere pass `--workspace <dir>` or set `JOBAPPLY_WORKSPACE`.

## How a run goes

| Step   | Who        | What happens                                                                                                                                                                                                                    |
| ------ | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| new    | tool       | `run <url>` fetches the posting and takes company, role and form URL from the page (JSON-LD, title, apply link); the language is your `default_language`. Nothing is asked; a bare page names the folder after the site       |
| fetch  | tool       | saves a snapshot of the posting (HTML + readable text) and extracts what it can into `posting.json` — done together with `new`; `jobapply fetch` re-fetches                                                                     |
| extract | Operator  | the unattended Operator (`claude -p /extract-posting`) completes `posting.json` (contact, address, requirements) and corrects the form URL when the page's apply link was missed; you see one table                          |
| letter | you + Operator | your Operator starts `/draft-cover-letter` right in the terminal: it shows the posting facts, offers one sentence per requirement, you pick and confirm; then `[d]` marks the letter done. Any content in `cover-letter.json` brings the `[a]/[e]/[d]` menu back instead, so you can also write by hand |
| check  | tool + Operator | in the background once the letter is done, while the documents render and you check the PDFs: the Form Check visits the form **without your login**, detects the fields and has the unattended Operator map what the synonym table missed (`form-fields.json`). A form that shows a login or no fields is *gated* |
| render | tool       | CV, cover letter and the Dossier (letter, CV, then all attachments in one PDF) into `out/`; offers to open them, `[r]` re-renders after edits                                                                                     |
| email  | tool + you | only when `form_url` is a `mailto:` address: composes `email.md` and opens it in your mail client; you attach the Dossier and send — replaces scan, fill and submit                                                              |
| fill   | tool       | open form: Chrome opens on the form and fills the fields and uploads at once, then stays open; the fields that are yours (consent, salary, start date) were listed just before. Gated form: `[f]` opens Chrome for you to log in, `[s]` scan, `[f]` fill, or you upload the PDFs from `out/` yourself |
| submit | you        | review the form and press the button                                                                                                                                                                                            |

Quit at any pause with `q`; `jobapply run <slug>` resumes at the same step, because progress is read from the files in the application folder. `jobapply back <slug>` undoes the last completed step. `jobapply status` shows every application, with what still blocks `render` (an empty required field) and what convention warns about.

Each step also exists as its own command (`new`, `fetch`, `check`, `render`, `scan`, `fill`, `email`) if you'd rather drive them yourself; `jobapply --help` lists them. `jobapply render <slug> --only cv|cover_letter|merged` renders one document, `--keep-html` also writes the intermediate HTML into `out/`. `jobapply open <slug> [letter|posting|fields|email|folder]` opens a file in your editor (`"editor"` in `config.json`, e.g. `"code -r"`). `jobapply new <posting-url>` creates one without running it; `--company`, `--role`, `--form` and `--lang` override what the page says. Any unique part of a slug works as the argument, e.g. `jobapply run acme`.

`scan` and `fill` act on whatever page the browser is showing and can be repeated, so multi-page forms are handled page by page (`[s]` scan, `[f]` fill, `[q]` quit inside the session). The Browser Session (the Chrome profile in `.browser/`) is persistent, so a login survives between runs. The Form Check deliberately does not use it: a form you can only reach logged in is gated, and you open it yourself.

## Your workspace

Everything personal lives in the workspace and is git-ignored in this repo; keep it in a private repository of its own if you like.

```
workspace/
  config.json              default language, extra language packs, browser channel, required/recommended profile fields
  profile/                 you, four files merged into one Profile: profile.json (name, gender, contact, links, personal details, summary, interests),
                           experience.json, education.json, skills.json (skills, languages, certifications)
  photo.jpg                optional photo used on the CV (path set in profile/profile.json); a signature image for the letter goes the same way ("signature")
  cover-letter-fixed.json  the half of the cover letter that is the same for every job, every language in one file; also the Style and accent colour of the PDFs
  field-synonyms.json      form labels → profile fields; add a label whenever scan misses one
  sources/                 your current CV and old cover letters; read by the import-documents skill, never uploaded
  attachments/             PDFs to upload with every application + manifest.json (kind, date, title)
  templates/               optional overrides of cv.html, cover-letter.html, style.css; your own Styles in templates/styles/
  applications/<slug>/     one folder per application (see docs/data-files.md)
  .browser/                the tool's own Chrome profile (logins)
```

**Languages.** Any string in the Profile files can be a plain string or a language map `{"de": "...", "en": "..."}`; in `cover-letter-fixed.json` a map may also wrap a whole paragraph list or the salutation patterns. Rendering fails if a translation for the application's language is missing — on purpose. Dates are ISO (`2025-01`) and formatted per language. German and English are built in; other languages are added under `"languages"` in `config.json`.

**Cover letter.** The letter follows the YOU–ME–WE order every Swiss career service teaches (ADR 0006): your specific `intro` → fixed `about_me` → your specific `body` → your specific `outlook` → fixed `closing`. `intro` is one or two sentences naming the role and one concrete reason you want it (a task from the posting, a product, a project); it and the first `about_me` paragraph are rendered as a single paragraph, so the fixed text continues the opening without a line break. `body` answers two to four of the posting's requirements, each with evidence. `outlook` is one sentence on what you want to contribute (plus your Pensum or start date when the posting asks); it and the first `closing` paragraph form the last paragraph. The subject line is built from the posting (`subject_default` / `subject_with_reference`, e.g. "Bewerbung als {role}, Referenz {reference}") unless `cover-letter.json` sets its own. The salutation is built from the contact person in `posting.json` using the `salutation_named` patterns (`"Frau": "Sehr geehrte Frau {last_name}"` — Swiss letters put no comma after it), or falls back to `salutation_default`; `render` warns when no contact person is known. Markdown is allowed in paragraphs. There is no enclosure list: a form may accept fewer files than you have. A form that wants no letter at all: set `"cover_letter": false` in the application's `application.json` and the letter step is skipped.

**Required and recommended fields.** `config.json` lists which Profile fields (dotted paths such as `contact.phone`, no file name) must be filled before `render` produces anything (`profile_fields.required`: name, address, phone, email, nationality, education, languages) and which only trigger a warning when empty (`recommended`: photo, birth date). The defaults follow German-speaking Swiss convention ([ADR 0003](docs/adr/0003-documents-follow-swiss-convention.md)); edit the lists for another country. `render`, `run` and `status` also warn about a ß in German text.

**Styles.** The PDFs' look is a Style, one CSS file in `templates/styles/`: `classic` (thin rules, monochrome — the default), `bar` (HSG-style: white capitals on coloured heading bars, dates right-aligned), `bare` (ETH-style: unlabelled personal line, small-caps headings, smaller photo) and `accent` (classic with the accent colour on name, headings and dates). Choose with `"style"` in `cover-letter-fixed.json` (or `config.json`), or per application in `application.json`; `"letter_style"` (same places) gives the cover letter its own Style, e.g. `classic` for a plain black letter next to a `bar` CV; `"accent"` next to it sets the one colour. On the letter a Style only touches the subject line: `bar` and `accent` colour it, `classic` and `bare` leave the letter black, because the letter has none of the headings, photo or date columns the Styles restyle. Every Style keeps the page structure the Swiss templates share ([research](docs/research/swiss-cv-layout-and-design.md)); add your own as `workspace/templates/styles/<name>.css`.

**Attachments.** `manifest.json` gives each PDF a `kind` (`reference`, `diploma`, `transcript`, `certificate`), a `date` and a `title` per language. New applications select all of them; remove entries from `attachments` in an application's `application.json` to leave some out. Merge order: reference letters newest first, then diplomas, transcripts, certificates.

**Output names** follow the language: `Lebenslauf_<Name>.pdf`, `Motivationsschreiben_<Name>.pdf`, `Bewerbungsunterlagen_<Name>.pdf` (the Dossier) in German; `CV_…`, `CoverLetter_…`, `ApplicationDocuments_…` in English. Patterns live in the language packs.

## Form filling

Fields are matched by two deterministic signals: the HTML `autocomplete` attribute, and the Synonym Table in `field-synonyms.json` (labels per language, matched as whole words; longest match wins). File inputs get `document:cv`, `document:cover_letter`, `attachments:all` (multi-file) or `document:merged` (the Dossier, for a single "documents" slot). Checkboxes, radios and questions like salary or start date are left for you: set their `value` in `form-fields.json` (`literal:…`) or answer them in the browser.

**Sites that need a login** (LinkedIn postings, an ATS behind single sign-on): run `jobapply login` once — it opens the workspace's own Chrome profile on LinkedIn's login page (`jobapply login <url>` for another site), you log in, press Enter. Fetching and form filling both use that profile, so the session carries over; the tool never sees or stores your credentials. A fetch that lands on a login page fails with a hint instead of saving an empty snapshot.

**Applications by email.** When the posting's apply button is a `mailto:` link, `new` proposes that address as the form URL (`"form_url": "mailto:hr@acme.ch"`; set it by hand for a posting that only prints the address). Such an application has no scan and fill; `email` composes the covering message — subject and salutation as on the letter, the `email_body` paragraphs from `cover-letter-fixed.json`, your name and phone — into `email.md`, hands it to your mail client and names the Dossier to attach. Attaching and sending stay yours.

Every ATS is different. Expect the first scan on a new platform to miss a few labels — add them to `field-synonyms.json` (or let `/map-fields` do it) and the next application on that platform goes smoother. Cross-origin iframes cannot be scanned; that's a browser limit.

## Agent skills

The judgment steps are handled by skills in `.agents/skills/`, written for any coding agent that reads `SKILL.md` files (Claude Code finds them via `.claude/skills/`; other agents read them from `.agents/skills/` or as plain instructions). Two set up the workspace:

- `setup-workspace` — asks where your photo, current CV, old cover letters and certificates go, checks the folders, then runs `import-documents`
- `import-documents` — reads the PDFs in `sources/` and `attachments/` and fills the Profile files in `profile/`, the fixed cover-letter halves, `manifest.json` and `config.json`, and asks you for any required or recommended field no document covers; existing values win, translations are flagged; run it again after adding a document

Three take an application slug:

- `extract-posting` — completes `posting.json` from the snapshot (contact, address, requirements) and corrects `application.json` where the tool guessed poorly; runs unattended
- `draft-cover-letter` — shows the posting facts for review, offers one sentence per posting requirement (or a question where your profile is silent), lets you pick and confirm two to four, then drafts `intro`/`body`/`outlook` in `cover-letter.json` as plain prose (leaves `draft: true`) and opens it in your editor
- `map-fields` — resolves unmatched fields in `form-fields.json`, notes which ones are yours, and teaches the Synonym Table; runs unattended inside the Form Check

In Claude Code that's `/extract-posting <slug>` etc. — but `jobapply run` starts them for you: `"operator"` in `config.json` is the interactive command (the letter interview), `"operator_unattended"` the one for `extract-posting` and `map-fields` (`claude -p …`), see `docs/adr/0004`. Each value is the full command line, so model, effort and permissions are yours to set there, e.g. `claude "/{skill} {slug}" --model sonnet --effort medium --add-dir {tool} --allowedTools Bash,Read,Write,Edit`; set one to `""` to run that skill yourself (`[a]` at the letter step is then the hint, and the Form Check leaves unmatched fields for you). The CLI itself contains no LLM and needs no API key; see `docs/adr/0001`.

## Vocabulary and decisions

- `CONTEXT.md` — the terms (Profile, Application, Posting, Form, Attachment, Field Map, Dossier, Style, Required Field, …)
- `docs/adr/` — why the tool is shaped this way; `docs/research/` — the Swiss application conventions the defaults follow, with sources
- `docs/overview.md` — one page: every command, every skill, which files need your input and how they chain
- `docs/data-files.md` — every file in an application folder, how progress is derived, and the `value` syntax of the Field Map

## Development

```
pip install -e '.[dev]'
pytest
```

Chrome-dependent paths (PDF rendering, the Form Check, scan/fill) are not covered by the unit tests; try them against a local HTML form (`jobapply check <slug>` with a `file://` form URL).
