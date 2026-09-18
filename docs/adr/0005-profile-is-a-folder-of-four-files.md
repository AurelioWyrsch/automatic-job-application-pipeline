# The Profile is a folder of four files with one shape in memory

`profile.json` grew to thirteen top-level keys, and the lists the applicant edits most (experience, education, skills) sat between identity fields that change never. The Profile now lives in `workspace/profile/` as four files: `profile.json` (first_name, last_name, photo, signature, contact, personal, summary, interests), `experience.json`, `education.json` and `skills.json` (skills, languages, certifications). Each file is an object; the loader reads exactly these four names and merges their top-level keys into the one dict the rest of the tool always had. So a dotted path such as `contact.email` or `personal.nationality` means the same thing in Required Fields, the Synonym Table, `profile_overrides` and the Templates as before, and a file name never appears in a path. A key present in two files is an error; a missing file is an error; other files in the folder are ignored.

## Considered Options

- One file per top-level key: rejected; `first_name.json` is noise, and the point is grouping by what the applicant edits together.
- Nesting each file under its name (`profile.experience.experience`): rejected; it would touch every dotted path in the Workspace for nothing.
- Globbing `profile/*.json` so a missing file is an absent key: rejected in favour of a fixed list, whose error names the misspelled file instead of letting `render` report an empty Required Field.
- A compatibility read of the old root `profile.json` or a `migrate` command: rejected; one applicant, one file, moved by hand.

## Consequences

- Error messages name the file that holds a key (`profile/education.json: required field 'education' is empty`), so the loader keeps a key-to-file map.
- `import-documents` and `setup-workspace` write into the folder; the example Workspace ships all four files.
- Per-value language maps (`{"de": …, "en": …}`) are untouched. Adding a Language to every Profile file is a separate, later decision.
