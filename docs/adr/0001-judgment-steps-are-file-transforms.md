# Judgment steps are file transforms; the LLM is a pluggable operator

The pipeline has three steps that need judgment rather than rules: extracting facts from a Posting, writing the specific part of a Cover Letter, and mapping unrecognised Form fields. Instead of calling an LLM API from inside the tool, each of these steps reads and writes a plain file (`posting.json`, `cover-letter.json`, `form-fields.json`) and the tool itself stays deterministic. Whoever edits the file — the applicant by hand, any coding agent via the repo's skills in `.agents/skills/`, or later an optional API call behind a flag — is interchangeable, and the applicant always reviews the file before the next step consumes it.

## Considered Options

- Anthropic SDK inside the CLI: works, but needs an API key, costs per call, and sends personal data to a provider by default. Kept as a possible opt-in later.
- No LLM anywhere: rejected; drafting letters and mapping odd forms is exactly where an LLM saves the most time.

## Consequences

- The tool never fails because an LLM is unavailable; it just leaves a file for a human to complete.
- Every judgment file must be readable and editable by hand, which constrains their formats to JSON/Markdown.
