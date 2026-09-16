---
name: draft-cover-letter
description: Draft the specific half of an Application's cover letter into cover-letter.json, after agreeing with the applicant which parts of the Posting it answers.
disable-model-invocation: true
---

Draft the job-specific half of the cover letter for the Application named in the request (`$ARGUMENTS` in Claude Code). File formats: [docs/data-files.md](../../../docs/data-files.md).

The letter says what the CV cannot: which parts of this Posting the applicant answers, with evidence, and why this employer. Where the applicant lives, which languages they speak and which degrees they hold are already on the CV, so the letter never spends a sentence on them; the Master's is the current credential, so the Bachelor's and its thesis stay on the CV too.

1. Locate the Application folder. Read `application.json`, `posting.json`, `snapshot.md`, the Workspace `profile.json`, and `cover-letter.<lang>.json` (the fixed half: know what it already says so you write around it, not over it).
2. **Ask about the key skills, then stop.** Judge which three to five skills the Posting really hinges on (the ones the role is built around, not every line of the requirements list) and put them to the applicant as numbered questions: for each, name the skill in the Posting's own words, say which line of `profile.json` (an experience bullet, a skill, the current studies) answers it or that nothing in the profile does, and ask what they would say to it. Add a question for anything the Posting explicitly asks the letter to address (a choice between entry models, an own project, a start date). Wait for the answers before writing a word of the letter; what the applicant answers counts as a profile line for this letter, and a skill they wave off is left out.
3. Write plain prose: paragraphs of running text, the way a letter is typed, with the applicant's answers folded into sentences. Markdown stays out of the letter (no lists, no bold). Write in the Application's language. Set `register` to match the Posting: `formal` (Sie/"Dear") unless the Posting itself addresses the reader informally (Du), then `informal`; the fixed half switches its own wording accordingly, so keep the specific half consistent with that choice. Use only the skills agreed in step 2 and the applicant's own facts; invent nothing.
4. Produce, in `cover-letter.json`:
   - `subject`: "Bewerbung als <role>" / "Application for <role>", with the reference number when there is one.
   - `salutation`: from `posting.contact` when a name exists, otherwise empty (the fixed default applies).
   - `intro`: one paragraph, starting with a capital letter (the salutation ends with a comma), that names the role and the one skill from step 2 that fits best.
   - `body`: one or two paragraphs that take the remaining skills from step 2 in turn, each in a sentence or two that ties the Posting's wording to the applicant's evidence. End with one sentence on why this employer.
   - Leave `draft: true`. The applicant edits, then marks it done (`[d]` in `jobapply run`).
5. Show the draft to the applicant in the reply as well, then open the file for them: `jobapply open <slug> letter`.

Done when `cover-letter.json` holds subject, salutation, intro and body, every skill in them was put to the applicant in step 2, every claim traces to a line in `profile.json`, `posting.json` or the applicant's answer, and the total letter (fixed + specific) stays under one page (about 250 words of specific text).
