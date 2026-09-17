# Data files an Application is made of

Workspace root: `--workspace`, else `$JOBAPPLY_WORKSPACE`, else `./workspace`. Applications live in `<workspace>/applications/<slug>/`; `jobapply list` prints the slugs and `jobapply status <slug>` shows which steps are done.

| File | Written by | Purpose |
|---|---|---|
| `application.json` | `jobapply new`, applicant | `company`, `role`, `language`, `posting_url`, `form_url`, `attachments` (files from `attachments/manifest.json` to upload, in order), `profile_overrides` (deep-merged over `profile.json` for this Application only), `style` / `letter_style` (Style names for the CV and the letter, override `config.json`; the letter falls back to the CV's), `cover_letter` (`false` waives the letter: the `letter` step counts as done, `render` produces only CV and Dossier, `document:cover_letter` may not be used) |
| `snapshot.html`, `snapshot.md` | `jobapply new`, `jobapply fetch` | The Posting as fetched; `.md` is the readable text. `new` fetches before the folder exists so the page's company and role can name it |
| `posting.json` | `jobapply new`, `jobapply fetch`, applicant | Facts about the Posting used by the cover-letter Template: `company`, `role`, `reference`, `location`, `workload`, `contact.{salutation,first_name,last_name,email,phone}`, `address.{company_line,street,postal_code,city,country}` (the letter drops `country` when it is one of `home_country` in `config.json`), `requirements` (list of strings), `description` |
| `cover-letter.json` | applicant | The specific half of the letter: `draft` (must be `false` before render; `[d]` in `run` sets it), `subject` (empty = `subject_with_reference` from `cover-letter.<lang>.json` when `posting.reference` is set, else `subject_default`, both with `{role}`/`{reference}`), `salutation` (empty = built from `posting.contact` via `salutation_named` in `cover-letter.<lang>.json`, or `salutation_default` when no contact is known), `intro` (paragraphs, markdown), `body` (paragraphs, markdown). Letter order: `intro` → fixed `about_me` → `body` → fixed `closing`. |
| `form-fields.json` | `jobapply scan`, applicant | The Field Map: `pages[]`, each with `url` and `fields[]`. A field's `value` says what to fill; `null` means skip |
| `out/` | `jobapply render` | The PDFs: CV, cover letter (unless waived) and the Dossier (`merged`: letter → CV → selected Attachments). `render` refuses while a Required Field in `profile.json` is empty (`profile_fields.required` in `config.json`) and warns about Recommended Fields, a missing contact person and ß in German text |

## How progress is derived

There is no state file. `jobapply status`, `run` and `back` read the folder:

| Step | done when |
|---|---|
| new | `application.json` exists |
| fetch | `snapshot.html` exists |
| letter | `cover-letter.json` has `"draft": false` and at least one paragraph in `intro` or `body`; or `application.json` has `"cover_letter": false` |
| render | every PDF the Application produces exists in `out/` (three, or two when the letter is waived) |
| scan | `form-fields.json` has at least one page |
| fill | a page in `form-fields.json` has `filled_at` set |

`jobapply back <slug>` reverses the last completed step by removing exactly that artifact (for `letter` it sets `draft` back to `true`; for `fetch` it keeps `posting.json`).

## Field `value` targets

- `profile:<dotted.path>` — a value from `profile.json` (language maps resolved to the Application's language; ISO dates formatted per language, or kept ISO for `<input type=date>`)
- `posting:<dotted.path>` — a value from `posting.json`
- `document:cv` / `document:cover_letter` / `document:merged` — upload a rendered PDF (`merged` is the Dossier; `cover_letter` is an error on an Application that waives it)
- `attachment:<file>` — upload one file from `attachments/`
- `attachments:all` — upload every selected Attachment (multi-file inputs only); `attachments:all+documents` also prepends CV and cover letter (CV only when the letter is waived)
- `literal:<text>` — type the text; for selects/radios the option label; for checkboxes `true`/`false`

`field-synonyms.json` in the Workspace is the Synonym Table: `{"any": {target: [labels]}, "<lang>": {target: [labels]}}`. Labels are matched as whole words in the field's label, placeholder, name and id; the longest match wins.
