# jobapply

CLI job-application pipeline; a human always presses submit. Vocabulary in `CONTEXT.md`, decisions in `docs/adr/`, per-application file formats in `docs/data-files.md`.

- Personal data lives only in a Workspace (`workspace/`, git-ignored). Never commit profile data, photos, attachments or applications; the bundled example data is fictional (`src/jobapply/defaults/workspace/`).
- No LLM calls inside the tool (ADR 0001). Judgment steps read/write files; the skills in `.claude/skills/` do the LLM part.
- Application progress is derived from files in the application folder (table in `docs/data-files.md`), never from a state file; `run` and `back` rely on that.
- Run tests with `.venv/bin/python -m pytest`. Chrome-dependent paths (PDF, scan/fill) are exercised manually against a local HTML file, not in the unit tests.
