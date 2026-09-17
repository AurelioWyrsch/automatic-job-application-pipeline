# jobapply

CLI job-application pipeline; a human always presses submit. Vocabulary in `CONTEXT.md`, decisions in `docs/adr/`, per-application file formats in `docs/data-files.md`.

- Personal data lives only in a Workspace (`workspace/`, git-ignored). Never commit profile data, photos, attachments or applications; the bundled example data is fictional (`src/jobapply/defaults/workspace/`).
- No LLM calls inside the tool (ADR 0001). Judgment steps read/write files; the skills below do the LLM part.
- Application progress is derived from files in the application folder (table in `docs/data-files.md`), never from a state file; `run` and `back` rely on that.
- Run tests with `.venv/bin/python -m pytest`. Chrome-dependent paths (PDF, scan/fill) are exercised manually against a local HTML file, not in the unit tests.

## Skills

Agent-neutral skills live in `.agents/skills/<name>/SKILL.md` (`.claude/skills/` symlinks there for Claude Code). The five that belong to this tool:

- `setup-workspace` — walk the applicant through placing photo, Source Documents and Attachments in a fresh Workspace, then hand over to `import-documents`
- `import-documents` — fill `profile.json`, the fixed cover-letter halves, `manifest.json` and `config.json` from the PDFs in `sources/` and `attachments/`; re-runnable

Each of the following takes an application slug:

- `extract-posting` — complete `posting.json` from the fetched snapshot
- `draft-cover-letter` — offer a sentence per requirement, let the applicant pick and confirm three to five, then draft the specific half of the cover letter into `cover-letter.json`
- `map-fields` — resolve unmatched fields in `form-fields.json` and extend the Synonym Table

Agents without a skill mechanism: read the SKILL.md and follow it as instructions.
