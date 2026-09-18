---
name: map-fields
description: Resolve unmatched fields in an Application's form-fields.json and teach the Synonym Table.
disable-model-invocation: true
---

Complete the Field Map for the Application named in the request (`$ARGUMENTS` in Claude Code). Target syntax and file formats: [docs/data-files.md](../../../docs/data-files.md). This normally runs unattended, inside the Form Check that `jobapply run` starts in the background: ask nothing; whatever you would tell the applicant goes into the file as a `note`.

1. Locate the Application folder. Read `form-fields.json`, the Workspace's Profile files (`profile/*.json`; `profile:<path>` targets use the merged keys, never a file name), `posting.json`, `application.json` and `field-synonyms.json`.
2. For every field whose `value` is `null`, decide from its `label`, `hints`, `placeholder`, `name`, `id`, `type` and `options`:
   - A Profile or Posting value exists → `profile:<path>` / `posting:<path>`.
   - A document slot → `document:cv`, `document:cover_letter`, `document:merged` (single-file inputs) or `attachments:all` (multi-file).
   - A select/radio whose answer follows from Profile (salutation, country, nationality) → `literal:<option label>` chosen from `options`.
   - Consent checkboxes, salary, start date, notice period, "how did you hear about us", free-text motivation → leave `null` and set `note` on the field to a few words saying why it is the applicant's (e.g. `"salary: yours to answer"`); `jobapply run` prints these notes before it opens the Form. A motivation textarea stays `null` too, with the note that the letter text (`intro` + `body` of `cover-letter.json`) can be pasted there.
   Keep every `value` the applicant already set.
3. For each field you resolved via a label the Synonym Table lacked, add that label (lower-case, as displayed) under the right target in `field-synonyms.json` (`any` for language-neutral labels such as "linkedin", the `<lang>` section otherwise), so `jobapply scan` catches it next time.
4. Write both files and print one short report: fields resolved, fields left for the applicant with their notes, synonyms added.

Done when every field in `form-fields.json` has either a `value` or a `note` saying why it is the applicant's to fill.
