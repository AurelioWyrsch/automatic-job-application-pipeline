---
name: extract-posting
description: Fill an Application's posting.json from its fetched Snapshot.
disable-model-invocation: true
---

Complete `posting.json` for the Application named in the request (`$ARGUMENTS` in Claude Code) from its Snapshot. File formats: [docs/data-files.md](../../../docs/data-files.md).

1. Locate the Application folder (`jobapply list` if the slug is partial). Read `snapshot.md`. For facts the text version lost (addresses in footers, contact blocks), grep `snapshot.html` **once** for the contact person's name, `mailto:`, `<footer` and `ld+json`, and read only those hits. A fact that is not in those hits is absent from the Posting: leave the field empty and say so. Never read `snapshot.html` page by page.
2. Read the current `posting.json`. Keep every field the applicant already filled; fill only empty ones.
3. Extract: company (legal name as written on the page), role title exactly as posted, reference number, location, workload/Pensum, the named contact person with salutation (`Herr`/`Frau` for German, `Mr`/`Ms` for English) and their email/phone, the postal address for the letter, and `requirements` as a list of the posting's own requirement lines, verbatim, most important first. Put the readable job text into `description`. Leave a field empty rather than guessing; a wrong contact name is worse than none.
4. Write `posting.json` and show the applicant a short table of what you filled and what stayed empty.
5. Invoke `draft-cover-letter` for the same Application (Claude Code: the Skill tool; other agents: follow its SKILL.md). It stops by itself when the Application waives the letter.

Done when every field in `posting.json` is either filled from the Snapshot or reported as absent from the Posting, and `draft-cover-letter` has taken over.
