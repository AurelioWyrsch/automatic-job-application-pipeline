# Overview: commands, skills and files

One page to find your way back into the project. Details: [data-files.md](data-files.md) for the per-application formats, the README's "Your workspace" section for the Workspace files, `CONTEXT.md` for the vocabulary.

## CLI commands

| Command | What it does |
|---|---|
| `jobapply init <dir>` | Create a Workspace with the fictional example data |
| `jobapply login` | Open the Workspace's own Chrome profile to log in to a job site (session kept in `.browser/`) |
| `jobapply new <url>` | Fetch a Posting, create `applications/<slug>/` from what the page says (no questions), save the Snapshot, then complete `posting.json` with the unattended Operator |
| `jobapply fetch <slug>` | Re-download the Posting → `snapshot.html/.md`, refill what it can in `posting.json` |
| `jobapply render <slug>` | CV, cover letter and Dossier PDFs → `out/`; blocks on Required Fields, warns on Recommended ones |
| `jobapply check <slug>` | The Form Check: visit the Form without your login, classify it Open or Gated, write `form-fields.json` (the Field Map) and map leftovers with the unattended Operator |
| `jobapply scan <slug>` | Open the Form in the browser with your login → `form-fields.json`; for Gated Forms and further pages |
| `jobapply fill <slug>` | Fill the mapped fields in the Form; never submits |
| `jobapply email <slug>` | `mailto:` Postings only: compose `email.md`, open the mail client (replaces scan/fill) |
| `jobapply run [<slug>\|<url>]` | Walk all steps, pausing only where you must act; a URL starts a new Application, nothing picks one; re-run to resume |
| `jobapply back <slug>` | Undo the last completed step |
| `jobapply status [slug]` | Which steps are done, plus convention warnings |
| `jobapply list` | Application slugs |
| `jobapply open <slug> <file>` | Open an Application file in your editor (`config.json` → `editor`) |

## Agent skills

Five skills belong to the tool (`.agents/skills/`, symlinked from `.claude/skills/`). Everything else in that folder is the engineering workflow used to build the tool, not part of the product.

| Skill | Scope | Reads | Writes |
|---|---|---|---|
| `setup-workspace` | Workspace | – | places `photo.jpg`, `sources/`, `attachments/`; runs `init` if needed; hands over to `import-documents` |
| `import-documents` | Workspace | PDFs in `sources/`, `attachments/` | `profile/*.json`, `cover-letter-fixed.json`, `attachments/manifest.json`, `config.json` |
| `extract-posting <slug>` | Application | `snapshot.md/html` | `posting.json`; corrects `application.json` (`form_url`, company, role, language) when the tool guessed poorly. Unattended |
| `draft-cover-letter <slug>` | Application | `posting.json`, `profile/*.json`, `cover-letter-fixed.json` | `cover-letter.json` (`intro`, `body`); shows the posting facts first for review. Interactive |
| `map-fields <slug>` | Application | `form-fields.json`, `profile/*.json`, `posting.json` | `form-fields.json` (`value` targets, `note` on fields left to you), `field-synonyms.json`. Unattended, inside the Form Check |

## Which files need your input

Workspace level, once:

| File | Needs input? | Filled by |
|---|---|---|
| `profile/` (`profile.json`, `experience.json`, `education.json`, `skills.json`; ADR 0005) | Yes, entirely: the example data is fictional | `import-documents`, then you |
| `cover-letter-fixed.json` | Yes: `about_me` and `closing` (the fixed half, every Language in one file); `style`/`letter_style`/`accent` for the look of the PDFs. Subject/salutation patterns and `email_body` are usable defaults | `import-documents`, then you |
| `attachments/manifest.json` | Yes, if you have attachments: one entry per PDF (`kind`, `date`, `title`) | `import-documents` |
| `config.json` | Mostly fine as shipped. Check `default_language`, `editor`, `operator` and `operator_unattended` (the interactive and the unattended Operator commands), `home_country`; `profile_fields` only when not applying in CH | you |
| `field-synonyms.json` | No; grows over time | `map-fields` |
| `photo.jpg` | Recommended Field: warns when missing | `setup-workspace` |

Per Application, created by `jobapply new`:

| File | Needs input? |
|---|---|
| `application.json` | Check `language`, `form_url`, `attachments`; optionally `style`, `letter_style`, `cover_letter: false`, `profile_overrides` |
| `posting.json` | Review: `new`/`fetch` extract only what they can; `extract-posting` completes contact, address and requirements unattended, and `draft-cover-letter` shows the result before the interview |
| `cover-letter.json` | Yes: `draft-cover-letter` writes `intro` (one sentence naming the role, rendered in the same paragraph as the fixed `about_me`) and `body` (the requirements); `[d]` in `run` sets `draft: false` |
| `form-fields.json` | After the Form Check: fields with `value: null` and a `note` are yours to answer in the browser; `"gated": true` means the Form needs your login |
| `snapshot.*`, `email.md`, `out/` | No; outputs |

## How it chains

```
jobapply init ──► setup-workspace ──► import-documents
                   (photo, sources/,     (profile/, cover-letter-fixed.json,
                    attachments/)         manifest.json, config.json)

jobapply run <url> ──► application.json, snapshot.*, posting.json          no questions asked
        │
        ▼
  extract-posting <slug> ──► posting.json complete                   unattended Operator
        │
        ▼
  draft-cover-letter <slug> ──► cover-letter.json                    interactive Operator
        │  [d] marks it done
        │
        ├──────────────────────────────┐
        ▼                              ▼  (background: the Form Check)
  jobapply render ──► out/       web Form: jobapply check ──► form-fields.json
  (CV, letter, Dossier)               │   Open Form:  map-fields <slug> (unattended) ──► values, notes, field-synonyms.json
        │  blocks on Required Fields  │   Gated Form: "gated": true, nothing else
        │  you check the PDFs         │
        ◄──────────────────────────────┘  run waits here
        │
        ├─ Open Form:  jobapply fill      browser opens and fills at once (you press submit)
        │
        ├─ Gated Form: [f] opens the browser: log in, [s] scan, [f] fill, or fill it yourself
        │
        └─ mailto:     jobapply email ──► email.md   (you attach the Dossier and send)
```

`jobapply run` drives the lower chain and pauses only at the interview, the PDF check and the browser; `status` and `back` derive progress from which of these files exist, never from a state file ([data-files.md](data-files.md#how-progress-is-derived)).
