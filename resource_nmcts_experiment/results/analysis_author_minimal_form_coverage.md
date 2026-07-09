# Author Minimal Response Form Coverage Audit

This audit checks that the short Chinese author response form covers every required private author/venue metadata field through explicit paths or grouped wildcard prompts.

## Status counts

- pass: 6

| item | status | evidence | next action |
|---|---|---|---|
| Minimal form file and private workflow | pass | minimal_form_exists=True; missing_tokens=none. | Keep the minimal form as a public intake checklist; store real values only in ignored private metadata files. |
| Required metadata path coverage | pass | required_paths=50; missing_paths=none. | Add exact path prompts or grouped wildcard prompts to AUTHOR_MINIMAL_RESPONSE_FORM_zh.md. |
| Template path parity | pass | required_paths=50; missing_in_template=none. | Keep REQUIRED_METADATA_PATHS aligned with submission_metadata_template.json. |
| One-pass answerability cues | pass | missing_tokens=none. | Keep explicit placeholder wording so the author can answer every field without guessing how to mark absent values. |
| Claim-boundary reminders | pass | missing_tokens=none. | Keep comparison and overclaim boundaries visible in the short author-intake path. |
| Anonymous-review prompts | pass | missing_tokens=none. | Keep double-blind data/code-link prompts visible until the target venue is selected. |
