# `jobapply run` starts the Operator itself

At the letter step, `run` used to print the two skill commands and wait while the applicant switched to their agent's window. Now it offers `a`, starts the **Operator** — the program named by `operator` in the Workspace's `config.json` — in the same terminal with the Workspace as working directory and `JOBAPPLY_WORKSPACE` exported, and resumes when it exits. The default is Claude Code running the repo's `extract-posting` skill, which hands over to `draft-cover-letter`, so the letter interview happens in that session. ADR 0001 stands: the tool contains no LLM call, the Operator writes the same files the applicant could write by hand, and `d` remains the applicant's review gate.

The command is a template with `{skill}`, `{slug}` and `{tool}` — the checkout holding `.agents/skills`, passed as `--add-dir` so the skills load wherever the Workspace lives (ADR 0002). Permissions (`--allowedTools …`) sit in the template, not in code: they are the applicant's call and specific to the agent. The prompt precedes `--allowedTools` because that flag is variadic and would swallow it.

## Considered Options

- Start the Operator automatically at the letter step: rejected; every re-check would spawn a session, and the applicant may be writing by hand.
- Headless extraction (`claude -p`), then an interactive session for the letter: rejected; two spawns and two configurations for a forty-second gain, and the letter needs a conversation anyway.
- A local model with the letter interview re-implemented as `jobapply` prompts: rejected; it rebuilds the agent harness the skills already run in, with a weaker model. A local model can still become an Operator behind the same key.
- `jobapply` appending the permission flags itself: rejected; breaks the moment the Operator is not Claude Code.

## Consequences

- A missing key means the default; `""` or a program not on `PATH` means the old hint and no `a` key. The tool never fails because the Operator is unavailable.
- Only the letter step has an Operator. Form mapping (`map-fields`) runs inside the browser session and can join later through the same template.
- The real spawn is checked by hand, like the Chrome paths; tests cover the command building against a fake runner.

## Amendment 2026-09-18: `run` is unattended except for the letter interview

Three rejections above are reversed after real applications showed where the time goes. The Operator now has two modes, both templates in the Workspace `config.json`: `operator` (interactive, the letter interview in the applicant's terminal) and `operator_unattended` (`claude -p …`, output only). `run` takes a Posting URL as well as a slug, asks nothing (company, role, Form URL and Language come from the page, the folder falls back to domain plus date), fetches, runs `extract-posting` unattended in the foreground, then forks: the **Form Check** runs in the background while the interactive Operator starts `draft-cover-letter` at once. `run` waits for the Form Check before render and never kills it. An Open Form is filled on opening; a Gated Form is left to the applicant, with today's headed session behind `[f]`.

Why each earlier rejection no longer holds:

- Headless extraction was "two spawns for forty seconds": the Form Check needs an unattended Operator anyway, so the second template exists regardless, and the extraction is now what allows the fork (its `posting.json` feeds `map-fields`, and it may correct `form_url` before the Form Check reads it).
- Auto-start "spawns on every re-check": it fires only while `cover-letter.json` is still the empty file `new` wrote; any content brings the `[a]` menu back, so hand-writing still works.
- Review of `posting.json` happened because the applicant watched the extraction: `draft-cover-letter` now opens by showing company, role, reference and address.

Decisions in the amendment that a reader will wonder about:

- The Form Check visits the Form in a fresh browser context **without** the applicant's stored session, so a Form that only the login reaches counts as Gated (ADR 0001's review gate: the applicant should see a gated page themselves before anything is uploaded through it). Side effect: the check never contends with the `.browser/` profile lock.
- A Gated result is recorded in `form-fields.json` (`"gated": true`, no pages), not in `application.json` or a state file: progress stays derived from files, `back scan` deletes it and re-checks, and a later headed scan adds pages to the same file.
- The Form Check only sees the page the Form URL lands on. ATS flows behind an "Apply" button or account creation come out Gated; clicking through headlessly is out of scope.
- `map-fields` writes a `note` on every field it leaves `null`, because unattended it has no chat to explain in and `run` prints those before fill.
- Only the tool's own field detection runs in the Form Check; the Operator maps leftovers from `form-fields.json` and never browses. ADR 0001 stands: every Operator run is still a file transform.

## Amendment 2026-09-19: the Form Check follows the letter step

The fork above is undone: the Form Check no longer overlaps the letter interview. It starts once the letter step is done — whatever finished it: the Operator, the editor, a hand-written file — and runs in the background while the documents are rendered and the applicant checks the PDFs; `run` waits for it before fill, and a pause during the PDF review still hands the running job back so it is never killed.

Why: two Claude Code sessions in one terminal — the interactive Operator in the foreground, `claude -p map-fields` behind it — left the interview unusable in real applications: mouse reports leaked into the prompt as text and `/exit` stopped working (anthropics/claude-code#76816). Claude Code's documented workaround, `CLAUDE_CODE_DISABLE_MOUSE=1`, was set by the tool and did not cure it; it is gone with the overlap. The rule is now simple and holds by construction: no unattended Operator runs while an interactive one is on the terminal.

What stays from the earlier amendment: the unattended extraction before the interview, the `operator_unattended` template, the visitor-only Form Check, the Gated/Open handling and the `note`s on unmapped fields. What is lost: the check's wall time is no longer hidden behind the interview; render plus the PDF review hides most of it instead.
