# Documents follow German-speaking Swiss convention

The CV and Cover Letter the tool renders, and what it insists on before rendering, follow the conventions of German-speaking Switzerland as documented in `docs/research/swiss-cv-and-cover-letter-conventions.md` (33 primary sources, read 2026-09-17). Where those sources disagree, one side was chosen; this record says which and why, so nobody later "fixes" the tool towards the German template.

- **Required Fields block `render`; Recommended Fields only warn** (in `status`, at the top of `run` and at `render`). Required: name, postal address, phone, email, nationality, one education entry, one language. Recommended: photo, birth date. Both lists ship as defaults in `config.json` so an applicant targeting another country can change them; the tool is public (ADR 0002) and the lists are convention, not logic. Nationality is required although jobs.ch wants it only for non-Swiss applicants, because ETH, UZH and HSG always list it and it costs one word. `permit` and `marital_status` are plain optional: the sources range from "must" (ETH Welcome Center) to "does not belong" (jobs.ch) on Zivilstand, so the applicant decides.
- **The Dossier is Cover Letter → CV → Attachments.** Every source agrees on this order; the earlier merge put the CV first. `render` still produces the three files (CV, letter, Dossier) because SECO wants one PDF, ETH wants separate files and SBB wants the CV alone; the Field Map picks per Form, which is the right seam. No "everything but the CV" bundle until a real Form asks for it.
- **An Application may waive the Cover Letter** (`"cover_letter": false` in `application.json`): SBB, Swisscom and UBS do not ask for one. The flag is an input; progress stays derived from files.
- **No Beilagen list.** ETH and UZH call it outdated, jobs.ch and SECO still list them. Removed rather than made optional, because when a Form accepts fewer files than the applicant has, a list that promises more than arrived confuses the reader.
- **No comma after the German salutation** ("Sehr geehrte Frau Muster" then a capitalised paragraph), matching the Swiss templates; English keeps its comma.
- **The generic salutation stays as fallback but `render` warns** when `posting.json` has no contact: ETH, UZH and jobs.ch accept "Sehr geehrte Damen und Herren", Uni Bern and BIZ Bern say find a name. A warning at render is the last moment that advice can be acted on; blocking would stall postings that name nobody.
- **The subject line is derived when empty** — "Bewerbung als {role}", plus ", Referenz {reference}" when known — instead of being a required free string. The posting source ("gefunden auf jobs.ch") is not added; the reference number is what HR keys on.
- **`render` warns on ß in German text** (Profile, fixed letter halves, `cover-letter.json`): the Federal Chancellery dropped ß in the 1970s and BIZ Bern names it as the giveaway of a German template. Warning only, since an employer's name may legitimately contain one.
- **Language levels stay free text**; the skills suggest a CEFR code but do not demand one — a native language has none, and studying in a language says more than a certificate.

## Considered Options

- One tier, everything blocks: rejected; the sources call photo and birth date customary, not obligatory, and UZH drops them for UK/US targets.
- Lists hard-coded in the tool: rejected; a non-Swiss applicant would have to fork.
- Beilagen list behind a toggle, default on: rejected for the partial-upload reason above.
- Block `render` until a contact person is known: rejected; some postings name nobody.

## Consequences

- `profile.json` gains `personal.marital_status`; `application.json` gains `cover_letter`; `config.json` gains the two field lists; `cover-letter.<lang>.json` gains `subject_default` and loses `enclosures_label`.
- `import-documents` asks for Required and Recommended Fields; `draft-cover-letter` may leave `subject` empty.
- Anyone changing a default towards German practice (comma, ß, Beilagen, CV first) should read the research file first.
