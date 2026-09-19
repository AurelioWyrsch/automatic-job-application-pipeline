# The Cover Letter follows YOU–ME–WE

The specific part of the Cover Letter was `intro` (one sentence naming the role) plus `body` (the requirements, ending with one sentence on why this employer). Every Swiss career service consulted (ETH, UZH, HSG, Uni Bern, ZHAW, Kanton Zürich, BIZ Bern; `docs/research/swiss-cover-letter-body.md`, 2026-09-19) orders the letter YOU – ME – WE: why this role at this employer first, then two to four of the Posting's requirements answered with evidence, then what the applicant wants to contribute, then the closing. The specific part is now three fields — `intro` (the hook: role plus one concrete reason), `body` (the evidence), `outlook` (the contribution, plus Pensum or start date when the Posting asks) — and `draft-cover-letter` caps the requirements at four. The fixed part keeps `about_me` (current studies and job) and `closing` (one indicative sentence); `intro` merges into the first `about_me` paragraph and `outlook` into the first `closing` paragraph, so the letter reads as three to four paragraphs and the seam between fixed and specific text is never a paragraph break.

## Considered Options

- Keep the why-employer sentence at the end of `body`: rejected; the sources put it in the opening, and the ME part then had no place for the contribution sentence UZH, HSG, ZHAW, Uni Bern and BIZ Bern ask for (ETH and Kanton Zürich reduce WE to the closing request; the tool follows the majority, and an applicant who agrees with ETH leaves `outlook` empty).
- WE as the last sentence of `body`, no new field: rejected; the skill and `render` cannot check what is not a field, and the closing paragraph would stay one fixed sentence for every Application.
- `intro` as its own paragraph before `about_me`: rejected; a one-sentence first paragraph, and five paragraphs on a one-page letter.
- Three to five requirements: rejected; UZH says 2–4, ZHAW 3–4, and five plus the fixed halves breaks the one-page limit.

## Consequences

- `cover-letter.json` gains `outlook`; `cover-letter.html` merges it with `closing[0]` the way `intro` merges with `about_me[0]`.
- The English fixed `closing` became indicative ("I look forward to …"); a live Workspace's `cover-letter-fixed.json` should follow.
- `draft-cover-letter` asks for a hook before the requirements and offers the outlook sentence after them; its example opener "Mit grossem Interesse habe ich … gelesen" is gone, since BIZ Bern and jobs.ch name it as the Floskel recruiters discard.
