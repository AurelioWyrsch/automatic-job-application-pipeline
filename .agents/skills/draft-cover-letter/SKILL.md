---
name: draft-cover-letter
description: Draft the specific half of an Application's cover letter into cover-letter.json.
disable-model-invocation: true
---

Draft the job-specific half of the cover letter for the Application named in the request (`$ARGUMENTS` in Claude Code). File formats: [docs/data-files.md](../../../docs/data-files.md).

1. Locate the Application folder. Read `application.json`, `posting.json`, `snapshot.md`, the Workspace `profile.json`, and `cover-letter.<lang>.json` (the fixed half: know what it already says so you write around it, not over it).
2. Write in the Application's language. Match register to the Posting: formal Sie/"Dear" unless the Posting itself is informal. Use the applicant's own facts from `profile.json`; invent nothing.
3. Produce, in `cover-letter.json`:
   - `subject`: "Bewerbung als <role>" / "Application for <role>", with the reference number when there is one.
   - `salutation`: from `posting.contact` when a name exists, otherwise empty (the fixed default applies).
   - `intro`: one paragraph, starting with a capital letter (the salutation ends with a comma), that names the role and the one thing about this Posting that genuinely fits the applicant.
   - `body`: one or two paragraphs mapping the Posting's `requirements` to concrete evidence from `profile.json` (a job, a bullet, a skill). Markdown bullet lists are fine when the requirements are a list. Add one sentence on why this company.
   - Leave `draft: true`. The applicant edits, then sets it to `false` themselves.
4. Show the draft to the applicant in the reply as well.

Done when `cover-letter.json` holds subject, salutation, intro and body, every claim in them traces to a line in `profile.json` or `posting.json`, and the total letter (fixed + specific) stays under one page (about 250 words of specific text).
