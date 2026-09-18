---
name: draft-cover-letter
description: Draft the specific half of an Application's cover letter into cover-letter.json, after the applicant picks and confirms sentence by sentence which requirements of the Posting it answers. Use when the applicant asks for the letter or when extract-posting hands over.
---

Draft the job-specific half of the cover letter for the Application named in the request (`$ARGUMENTS` in Claude Code). File formats: [docs/data-files.md](../../../docs/data-files.md).

The letter says what the CV cannot: which parts of this Posting the applicant answers, with evidence, and why this employer. Where the applicant lives, which languages they speak and which degrees they hold are already on the CV, so the letter never spends a sentence on them; the Master's is the current credential, so the Bachelor's and its thesis stay on the CV too.

1. Locate the Application folder. If `application.json` has `"cover_letter": false`, the Application waives the letter: tell the applicant and stop. Read `application.json`, `posting.json`, `snapshot.md`, the Workspace `profile.json`, and `cover-letter.<lang>.json` (the fixed half: know what it already says so you write around it, not over it).
2. **Offer a sentence per requirement, then stop.** List every line of `posting.requirements` (plus anything the Posting explicitly asks the letter to address: a choice between entry models, an own project, a start date), numbered, each with the requirement in the Posting's own words and one of:
   - a **candidate sentence**: the one sentence the letter would say, written from a named line of `profile.json` (an experience bullet, a skill, the current studies);
   - a **question**, when nothing in the profile answers it: one line asking what the applicant would say, or whether to leave it out.
   Ask the applicant to pick three to five. Nothing else in that message.
3. **Confirm one at a time.** For each picked item, in the applicant's order, show only the sentence as it will stand in the letter (for a question, written from their answer) and wait: they approve, edit, or drop it. Move on only after the answer. Every confirmed sentence is the applicant's own claim for this letter; a dropped item stays out.
4. Write plain prose: paragraphs of running text, the way a letter is typed, with the applicant's answers folded into sentences. Markdown stays out of the letter (no lists, no bold). Write in the Application's language, addressing the reader formally (Sie/"Dear") whatever tone the Posting uses; German uses Swiss spelling (`ss`, never `ß`). Use only the sentences confirmed in step 3; invent nothing.
5. Produce, in `cover-letter.json`:
   - `subject`: empty; the tool builds "Bewerbung als <role>, Referenz <reference>" from `posting.json`. Set it only when the Posting asks for a specific wording.
   - `salutation`: empty; the tool builds it from `posting.contact` or falls back to the generic form. If `posting.contact` has no name, say so to the applicant: Swiss guides want a named reader, and the applicant may know one.
   - `intro`: a JSON list holding **exactly one sentence** that names the role, e.g. "Mit grossem Interesse habe ich Ihre Ausschreibung als <role> gelesen." The tool renders it and the first fixed `about_me` paragraph as one paragraph, so the sentence must read naturally straight into `about_me`; no requirement goes here.
   - `body`: a JSON list of one or two paragraphs (one string each) that take all confirmed sentences in turn, each tying the Posting's wording to the applicant's evidence. End with one sentence on why this employer.
   - Leave `draft: true`. The applicant edits, then marks it done (`[d]` in `jobapply run`).
6. Show the draft to the applicant in the reply as well, then open the file for them: `jobapply open <slug> letter`.

Done when `cover-letter.json` holds intro and body, every claim in them is a sentence confirmed in step 3, every claim traces to a line in `profile.json`, `posting.json` or the applicant's answer, and the total letter (fixed + specific) stays under one page (about 250 words of specific text). Minimal throughout: one sentence per requirement, one message per confirmation, no summaries between steps.
