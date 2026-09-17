---
name: import-documents
description: Fill profile.json, the fixed halves of the cover letter, attachments/manifest.json and config.json from the PDFs in the Workspace's sources/ and attachments/. Use when Source Documents or Attachments were placed or added, or when setup-workspace hands over. Re-runnable; existing values win.
---

Fill the Workspace's data files from its documents. File formats: the "Your workspace" section of [README.md](../../../README.md); vocabulary: [CONTEXT.md](../../../CONTEXT.md).

1. Read `profile.json`, `config.json`, every `cover-letter.<lang>.json`, `attachments/manifest.json`, and every PDF in `sources/` and `attachments/` (your PDF reader, or `pdftotext`). Also read the tool's example Workspace, `src/jobapply/defaults/workspace/`: a value still equal to its example counts as empty.
2. Decide every write by these rules:
   - Empty values are filled; other values stay. A document that contradicts a kept value is a **disagreement**: reported, never applied.
   - Free-text values are language maps. Write the source's language and `en`; every translated value is **flagged**.
   - Fixed letter paragraphs (`about_me`, `closing`) come from an old cover letter, formal (Sie) throughout.
   - Experience and education from the CV: add entries the profile lacks, newest first.
   - `config.json`: only `default_language` and `home_country`.
   - `manifest.json`: one entry per PDF in `attachments/` — `file`, `kind` (from the PDF, else the filename), `date` (`YYYY-MM` from the PDF, else empty and reported), `title` per language. An entry whose file is gone is reported, not removed.
   - `photo`, `signature`, `field-synonyms.json` and `templates/` stay untouched.
3. Write the files and show one table with four groups: filled, flagged (translated or Du written), disagreements, left empty.

Done when every PDF was read, every empty value is filled or in the table, and nothing outside the rules above changed.
