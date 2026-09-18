---
name: extract-posting
description: Fill an Application's posting.json from its fetched Snapshot, unattended.
disable-model-invocation: true
---

Complete `posting.json` for the Application named in the request (`$ARGUMENTS` in Claude Code) from its Snapshot. File formats: [docs/data-files.md](../../../docs/data-files.md). This normally runs unattended (`jobapply run` starts it with the Operator's unattended command and nobody watches): ask nothing, write the files, print one table.

1. Locate the Application folder (`jobapply list` if the slug is partial). Read `snapshot.md`. For facts the text version lost (addresses in footers, contact blocks), grep `snapshot.html` **once** for the contact person's name, `mailto:`, `<footer`, `ld+json` and the apply link (anchors whose text is "Bewerben", "Apply", "Jetzt bewerben" or similar), and read only those hits. A fact that is not in those hits is absent from the Posting: leave the field empty and say so. Never read `snapshot.html` page by page.
2. Read the current `posting.json`. Keep every field the applicant already filled; fill only empty ones.
3. Extract: company (legal name as written on the page), role title exactly as posted, reference number, location, workload/Pensum, the named contact person with salutation (`Herr`/`Frau` for German, `Mr`/`Ms` for English) and their email/phone, the postal address for the letter, and `requirements` as a list of the posting's own requirement lines, verbatim, most important first. Put the readable job text into `description`. Leave a field empty rather than guessing; a wrong contact name is worse than none. `requirements` must not stay empty when the Posting lists any: the tool takes a filled list as the sign that extraction happened.
4. Correct `application.json` where the tool's guess was poor, and only there: `company` or `role` when empty or a site name rather than the employer; `form_url` when it equals `posting_url` (no apply link was found) or points somewhere other than where the Posting says to apply (an apply page, or `mailto:<address>` when the Posting says to apply by email). Never touch `language`: the applicant applies in the Workspace's default Language whatever language the Posting is written in, and changes it by hand when they want otherwise. Never rename the folder.
5. Write both files and print a short table: each `posting.json` field with what you filled or "absent from the Posting", and each `application.json` key you changed with old and new value. Nothing else.

Done when every field in `posting.json` is either filled from the Snapshot or reported as absent from the Posting, and `application.json` holds the Form URL the Form Check should visit.
