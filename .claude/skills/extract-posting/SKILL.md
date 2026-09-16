---
name: extract-posting
description: Fill an Application's posting.json from its fetched Snapshot.
disable-model-invocation: true
---

Complete `posting.json` for the Application named in `$ARGUMENTS` from its Snapshot. File formats: [docs/data-files.md](../../../docs/data-files.md).

1. Locate the Application folder (`jobapply list` if the slug is partial). Read `snapshot.md`; fall back to `snapshot.html` only for facts the text version lost (addresses in footers, contact blocks).
2. Read the current `posting.json`. Keep every field the applicant already filled; fill only empty ones.
3. Extract: company (legal name as written on the page), role title exactly as posted, reference number, location, workload/Pensum, the named contact person with salutation (`Herr`/`Frau` for German, `Mr`/`Ms` for English) and their email/phone, the postal address for the letter, and `requirements` as a list of the posting's own requirement lines, verbatim, most important first. Put the readable job text into `description`. Leave a field empty rather than guessing; a wrong contact name is worse than none.
4. Write `posting.json` and show the applicant a short table of what you filled and what stayed empty.

Done when every field in `posting.json` is either filled from the Snapshot or reported as absent from the Posting.
