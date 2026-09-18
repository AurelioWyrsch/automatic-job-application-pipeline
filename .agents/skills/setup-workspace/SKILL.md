---
name: setup-workspace
description: Walk the applicant through filling a fresh Workspace with their own photo, Source Documents, Attachments and languages, then import them.
disable-model-invocation: true
---

Fill the Workspace (`workspace/` by default, `$ARGUMENTS` in Claude Code when given) with the applicant's own data. Layout: the "Your workspace" section of [README.md](../../../README.md); vocabulary: [CONTEXT.md](../../../CONTEXT.md). The applicant may start with no documents or many; whatever they lack is simply left out.

1. Find the Workspace. When it has no `config.json`, run `jobapply init <dir>`. Create `sources/` if it is missing.
2. **Ask for everything in one message, then stop.** Four items, each with its destination, and nothing else:
   - a photo for the CV → `<workspace>/photo.jpg`
   - current CV and any old cover letters (Source Documents) → `sources/`
   - reference letters, diplomas, transcripts, certificates (Attachments) → `attachments/`
   - the languages they apply in (`de`, `en`, …)
3. **Check placement.** List `<workspace>/`, `sources/` and `attachments/`. A PDF that is a reference letter, diploma, transcript or certificate (from its name or first page) belongs in `attachments/`; a CV or letter belongs in `sources/`. Move misplaced files and report every move. Set `photo` in `profile/profile.json` to the placed file. Make every language map in `cover-letter-fixed.json` carry the named languages (a new language starts as a translation of the `en` values; `default_language` in `config.json` is the first language named). Then re-ask only for what the applicant said they have and is still absent, and stop. Repeat until nothing they named is absent.
4. Invoke `import-documents` (Claude Code: the Skill tool; other agents: follow its SKILL.md).

Done when every file the applicant said they placed sits in its folder, `photo` points at the placed photo, every language map in `cover-letter-fixed.json` carries exactly the named languages, and `import-documents` has shown its table.
