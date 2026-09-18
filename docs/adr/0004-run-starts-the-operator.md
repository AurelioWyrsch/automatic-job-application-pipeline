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
