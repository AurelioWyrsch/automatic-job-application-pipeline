---
name: draft-cover-letter
description: Draft the specific half of an Application's cover letter into cover-letter.json, after agreeing with the applicant which parts of the Posting it answers.
disable-model-invocation: true
---

Draft the job-specific half of the cover letter for the Application named in the request (`$ARGUMENTS` in Claude Code). File formats: [docs/data-files.md](../../../docs/data-files.md).

The letter says what the CV cannot: which parts of this Posting the applicant answers, with evidence, and why this employer. Where the applicant lives, which languages they speak and which degrees they hold are already on the CV, so the letter never spends a sentence on them; the Master's is the current credential, so the Bachelor's and its thesis stay on the CV too.

1. Locate the Application folder. Read `application.json`, `posting.json`, `snapshot.md`, the Workspace `profile.json`, and `cover-letter.<lang>.json` (the fixed half: know what it already says so you write around it, not over it).
2. **Propose the angles, then stop.** List, numbered, every part of the Posting the letter could pick up: each requirement or task that a line of `profile.json` (an experience bullet, a skill, the current studies) answers, named with that evidence in one line; plus anything the Posting explicitly asks the letter to address (a choice between entry models, an own project, a start date). Mark the requirements no profile line answers as gaps. Ask which angles to include and wait for the answer before writing a word of the letter; the applicant may also add facts or an angle of their own, and those count as profile lines for this letter.
3. Write in the Application's language. Set `register` to match the Posting: `formal` (Sie/"Dear") unless the Posting itself addresses the reader informally (Du), then `informal`; the fixed half switches its own wording accordingly, so keep the specific half consistent with that choice. Use only the agreed angles and the applicant's own facts; invent nothing.
4. Produce, in `cover-letter.json`:
   - `subject`: "Bewerbung als <role>" / "Application for <role>", with the reference number when there is one.
   - `salutation`: from `posting.contact` when a name exists, otherwise empty (the fixed default applies).
   - `intro`: one paragraph, starting with a capital letter (the salutation ends with a comma), that names the role and the one agreed angle that fits best.
   - `body`: one or two paragraphs, one agreed angle each or a markdown bullet list when there are several, each mapping the Posting's wording to the evidence. Add one sentence on why this employer.
   - Leave `draft: true`. The applicant edits, then marks it done (`[d]` in `jobapply run`).
5. Show the draft to the applicant in the reply as well, then open the file for them: `jobapply open <slug> letter`.

Done when `cover-letter.json` holds subject, salutation, intro and body, every angle in them was agreed in step 2, every claim traces to a line in `profile.json`, `posting.json` or the applicant's answer, and the total letter (fixed + specific) stays under one page (about 250 words of specific text).
