# jobapply

CLI job-application pipeline; a human always presses submit. Vocabulary in `CONTEXT.md`, decisions in `docs/adr/`, per-application file formats in `docs/data-files.md`, one-page map of commands, skills and files in `docs/overview.md`.

- Personal data lives only in a Workspace (`workspace/`, git-ignored). Never commit profile data, photos, attachments or applications; the bundled example data is fictional (`src/jobapply/defaults/workspace/`).
- No LLM calls inside the tool (ADR 0001). Judgment steps read/write files; the skills below do the LLM part. `run` starts the Operator — the programs named by `operator` (interactive) and `operator_unattended` in the Workspace `config.json`, by default Claude Code — itself: `extract-posting` unattended after the fetch, then `draft-cover-letter` interactively while the Form Check runs `map-fields` unattended in the background (ADR 0004 and its amendment).
- The Profile is four files in the Workspace's `profile/` folder, merged into one dict by the loader (ADR 0005); dotted paths (`contact.email`) never contain a file name.
- Application progress is derived from files in the application folder (table in `docs/data-files.md`), never from a state file; `run` and `back` rely on that.
- Document defaults follow German-speaking Swiss convention (ADR 0003, sources in `docs/research/`): Required Fields block `render`, Recommended Fields warn; both lists live in the Workspace's `config.json`, not in code. Styles are CSS files in `templates/styles/`.
- Run tests with `.venv/bin/python -m pytest`. Chrome-dependent paths (PDF, scan/fill) are exercised manually against a local HTML file, not in the unit tests.

## Skills

Agent-neutral skills live in `.agents/skills/<name>/SKILL.md` (`.claude/skills/` symlinks there for Claude Code). The five that belong to this tool:

- `setup-workspace` — walk the applicant through placing photo, Source Documents and Attachments in a fresh Workspace, then hand over to `import-documents`
- `import-documents` — fill the Profile files in `profile/`, the fixed cover-letter halves, `manifest.json` and `config.json` from the PDFs in `sources/` and `attachments/`; re-runnable

Each of the following takes an application slug:

- `extract-posting` — complete `posting.json` from the fetched snapshot and correct `application.json` where the tool guessed poorly; unattended
- `draft-cover-letter` — offer a sentence per requirement, let the applicant pick and confirm three to five, then draft the specific half of the cover letter into `cover-letter.json`
- `map-fields` — resolve unmatched fields in `form-fields.json` and extend the Synonym Table; unattended, inside the Form Check

Agents without a skill mechanism: read the SKILL.md and follow it as instructions.
