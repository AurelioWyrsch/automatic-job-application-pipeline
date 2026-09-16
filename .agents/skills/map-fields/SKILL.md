---
name: map-fields
description: Resolve unmatched fields in an Application's form-fields.json and teach the Synonym Table.
disable-model-invocation: true
---

Complete the Field Map for the Application named in the request (`$ARGUMENTS` in Claude Code). Target syntax and file formats: [docs/data-files.md](../../../docs/data-files.md).

1. Locate the Application folder. Read `form-fields.json`, the Workspace `profile.json`, `posting.json`, `application.json` and `field-synonyms.json`.
2. For every field whose `value` is `null`, decide from its `label`, `hints`, `placeholder`, `name`, `id`, `type` and `options`:
   - A Profile or Posting value exists → `profile:<path>` / `posting:<path>`.
   - A document slot → `document:cv`, `document:cover_letter`, `document:merged` (single-file inputs) or `attachments:all` (multi-file).
   - A select/radio whose answer follows from Profile (salutation, country, nationality) → `literal:<option label>` chosen from `options`.
   - Consent checkboxes, salary, start date, notice period, "how did you hear about us", free-text motivation → leave `null` and list them for the applicant; those are theirs to answer. Exception: a motivation textarea may take `literal:` with the `intro` + `body` text from `cover-letter.json` as plain text, if the applicant agrees.
   Keep every `value` the applicant already set.
3. For each field you resolved via a label the Synonym Table lacked, add that label (lower-case, as displayed) under the right target in `field-synonyms.json` (`any` for language-neutral labels such as "linkedin", the `<lang>` section otherwise), so `jobapply scan` catches it next time.
4. Write both files and report: fields resolved, fields left for the applicant with the reason, synonyms added.

Done when every field in `form-fields.json` has either a `value` or a stated reason it is the applicant's to fill.
