# Data files an Application is made of

Workspace root: `--workspace`, else `$JOBAPPLY_WORKSPACE`, else `./workspace`. Applications live in `<workspace>/applications/<slug>/`; `jobapply list` prints the slugs and `jobapply status <slug>` shows which steps are done.

| File | Written by | Purpose |
|---|---|---|
| `application.json` | `jobapply new`, applicant | `company`, `role`, `language`, `posting_url`, `form_url`, `attachments` (files from `attachments/manifest.json` to upload, in order), `profile_overrides` (deep-merged over `profile.json` for this Application only) |
| `snapshot.html`, `snapshot.md` | `jobapply new`, `jobapply fetch` | The Posting as fetched; `.md` is the readable text. `new` fetches before the folder exists so the page's company and role can name it |
| `posting.json` | `jobapply new`, `jobapply fetch`, applicant | Facts about the Posting used by the cover-letter Template: `company`, `role`, `reference`, `location`, `workload`, `contact.{salutation,first_name,last_name,email,phone}`, `address.{company_line,street,postal_code,city,country}`, `requirements` (list of strings), `description` |
| `cover-letter.json` | applicant | The specific half of the letter: `draft` (must be `false` before render; `[d]` in `run` sets it), `register` (`formal` or `informal`, default `formal`), `subject`, `salutation` (empty = built from `posting.contact` via `salutation_named` in `cover-letter.<lang>.json`, or `salutation_default` when no contact is known), `intro` (paragraphs, markdown), `body` (paragraphs, markdown). Letter order: `intro` → fixed `about_me` → `body` → fixed `closing`. In `cover-letter.<lang>.json` any value may be a Register map `{"formal": …, "informal": …}`; the Application's `register` picks the variant |
| `form-fields.json` | `jobapply scan`, applicant | The Field Map: `pages[]`, each with `url` and `fields[]`. A field's `value` says what to fill; `null` means skip |
| `out/` | `jobapply render` | The PDFs |

## How progress is derived

There is no state file. `jobapply status`, `run` and `back` read the folder:

| Step | done when |
|---|---|
| new | `application.json` exists |
| fetch | `snapshot.html` exists |
| letter | `cover-letter.json` has `"draft": false` and at least one paragraph in `intro` or `body` |
| render | all three PDFs exist in `out/` |
| scan | `form-fields.json` has at least one page |
| fill | a page in `form-fields.json` has `filled_at` set |

`jobapply back <slug>` reverses the last completed step by removing exactly that artifact (for `letter` it sets `draft` back to `true`; for `fetch` it keeps `posting.json`).

## Field `value` targets

- `profile:<dotted.path>` — a value from `profile.json` (language maps resolved to the Application's language; ISO dates formatted per language, or kept ISO for `<input type=date>`)
- `posting:<dotted.path>` — a value from `posting.json`
- `document:cv` / `document:cover_letter` / `document:merged` — upload a rendered PDF
- `attachment:<file>` — upload one file from `attachments/`
- `attachments:all` — upload every selected Attachment (multi-file inputs only); `attachments:all+documents` also prepends CV and cover letter
- `literal:<text>` — type the text; for selects/radios the option label; for checkboxes `true`/`false`

`field-synonyms.json` in the Workspace is the Synonym Table: `{"any": {target: [labels]}, "<lang>": {target: [labels]}}`. Labels are matched as whole words in the field's label, placeholder, name and id; the longest match wins.
