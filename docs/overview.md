# Overview: commands, skills and files

One page to find your way back into the project. Details: [data-files.md](data-files.md) for the per-application formats, the README's "Your workspace" section for the Workspace files, `CONTEXT.md` for the vocabulary.

## CLI commands

| Command | What it does |
|---|---|
| `jobapply init <dir>` | Create a Workspace with the fictional example data |
| `jobapply login` | Open the Workspace's own Chrome profile to log in to a job site (session kept in `.browser/`) |
| `jobapply new <url>` | Fetch a Posting, propose company/role/form URL, create `applications/<slug>/` with `application.json`, the Snapshot and `posting.json` |
| `jobapply fetch <slug>` | Re-download the Posting → `snapshot.html/.md`, refill what it can in `posting.json` |
| `jobapply render <slug>` | CV, cover letter and Dossier PDFs → `out/`; blocks on Required Fields, warns on Recommended ones |
| `jobapply scan <slug>` | Open the Form in the browser → `form-fields.json` (the Field Map) |
| `jobapply fill <slug>` | Fill the mapped fields in the Form; never submits |
| `jobapply email <slug>` | `mailto:` Postings only: compose `email.md`, open the mail client (replaces scan/fill) |
| `jobapply run <slug>` | Walk all steps, pausing where you must act; re-run to resume |
| `jobapply back <slug>` | Undo the last completed step |
| `jobapply status [slug]` | Which steps are done, plus convention warnings |
| `jobapply list` | Application slugs |
| `jobapply open <slug> <file>` | Open an Application file in your editor (`config.json` → `editor`) |

## Agent skills

Five skills belong to the tool (`.agents/skills/`, symlinked from `.claude/skills/`). Everything else in that folder is the engineering workflow used to build the tool, not part of the product.

| Skill | Scope | Reads | Writes |
|---|---|---|---|
| `setup-workspace` | Workspace | – | places `photo.jpg`, `sources/`, `attachments/`; runs `init` if needed; hands over to `import-documents` |
| `import-documents` | Workspace | PDFs in `sources/`, `attachments/` | `profile.json`, `cover-letter.<lang>.json` (fixed halves), `attachments/manifest.json`, `config.json` |
| `extract-posting <slug>` | Application | `snapshot.md/html` | `posting.json` |
| `draft-cover-letter <slug>` | Application | `posting.json`, `profile.json`, `cover-letter.<lang>.json` | `cover-letter.json` (`intro`, `body`, `draft: false`) |
| `map-fields <slug>` | Application | `form-fields.json`, `profile.json`, `posting.json` | `form-fields.json` (`value` targets), `field-synonyms.json` |

## Which files need your input

Workspace level, once:

| File | Needs input? | Filled by |
|---|---|---|
| `profile.json` | Yes, entirely: the example data is fictional | `import-documents`, then you |
| `cover-letter.de.json` / `.en.json` | Yes: `about_me` and `closing` (the fixed half). Subject/salutation patterns and `email_body` are usable defaults | `import-documents`, then you |
| `attachments/manifest.json` | Yes, if you have attachments: one entry per PDF (`kind`, `date`, `title`) | `import-documents` |
| `config.json` | Mostly fine as shipped. Check `default_language`, `style`/`accent`, `editor`, `home_country`; `profile_fields` only when not applying in CH | you |
| `field-synonyms.json` | No; grows over time | `map-fields` |
| `photo.jpg` | Recommended Field: warns when missing | `setup-workspace` |

Per Application, created by `jobapply new`:

| File | Needs input? |
|---|---|
| `application.json` | Check `language`, `form_url`, `attachments`; optionally `style`, `letter_style`, `cover_letter: false`, `profile_overrides` |
| `posting.json` | Yes: `new`/`fetch` extract only what they can; `extract-posting` completes contact, address and requirements |
| `cover-letter.json` | Yes: `draft-cover-letter` writes `intro` (one sentence naming the role, rendered in the same paragraph as the fixed `about_me`) and `body` (the requirements), and sets `draft: false` |
| `form-fields.json` | After `scan`: every `value: null` needs a target → `map-fields` |
| `snapshot.*`, `email.md`, `out/` | No; outputs |

## How it chains

```
jobapply init ──► setup-workspace ──► import-documents
                   (photo, sources/,     (profile.json, cover-letter.<lang>.json,
                    attachments/)         manifest.json, config.json)

jobapply new <url> ──► application.json, snapshot.*, posting.json
        │
        ▼
  extract-posting <slug> ──► posting.json complete
        │
        ▼
  draft-cover-letter <slug> ──► cover-letter.json (draft: false)     "letter" step done
        │
        ▼
  jobapply render ──► out/ (CV, letter, Dossier)                     blocks on Required Fields
        │
        ├─ web Form:  jobapply scan ──► form-fields.json
        │                  │
        │             map-fields <slug> ──► values resolved, field-synonyms.json extended
        │                  │
        │             jobapply fill      (you press submit)
        │
        └─ mailto:   jobapply email ──► email.md   (you attach the Dossier and send)
```

`jobapply run <slug>` drives the lower chain and pauses at each skill step; `status` and `back` derive progress from which of these files exist, never from a state file ([data-files.md](data-files.md#how-progress-is-derived)).
