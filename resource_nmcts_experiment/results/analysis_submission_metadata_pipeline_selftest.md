# Submission Metadata Pipeline Self-Test

This audit uses synthetic, non-private metadata to test the validator and private-preview renderers.

It does not create `submission_metadata.json` and does not write `generated_*.md` private preview files.

## Status counts

- pass: 14

| item | status | evidence | next action |
|---|---|---|---|
| required path fixture coverage | pass | 31/31 required paths present. | Update synthetic fixture when required metadata paths change. |
| placeholder-free fixture | pass | 0 placeholder or empty field(s) remain. | Remove placeholders from the synthetic fixture. |
| validator: Required metadata completeness | pass | 0 required or placeholder field(s) remain incomplete. fields=none | Fill every AUTHOR INPUT REQUIRED field before generating final submission text. |
| validator: Target policy flags | pass | 7/7 policy flag(s) are parseable as checked/yes/no/not-applicable values. fields=none | Use explicit yes/no/checked/not applicable wording for target-venue policy fields. |
| validator: Author list structure | pass | 1 author row(s) checked; corresponding_count=1. fields=none | Use sequential author order values and mark at least one corresponding author. |
| validator: Author contact formats | pass | Email and ORCID-like fields checked without exposing values. fields=none | Use valid email addresses and ORCID format 0000-0000-0000-0000, or an explicit no-ORCID statement if allowed by the venue. |
| validator: Corresponding author consistency | pass | Corresponding-author name/email are checked against the author list without exposing values. fields=none | Ensure corresponding_author.name/email match one author entry. |
| validator: Availability and repository links | pass | 5/5 link-like field(s) are URL/DOI or explicit none; explicit_none_count=1. fields=none | Use https URLs, DOI strings, or explicit none/not-applicable statements for optional links. |
| validator: Code commit hash | pass | Commit hash is checked for hex format and consistency with the current checkout. fields=none | Use the final pushed commit hash for the uploaded code/archive. |
| validator: Submission statements | pass | 8/8 prose statement field(s) have at least three words. fields=none | Use explicit venue-ready prose rather than terse placeholders. |
| preview renderer: author declarations | pass | chars=1923; has_header=True; placeholder_present=False. | Fix renderer output before relying on generated private preview files. |
| preview renderer: availability statements | pass | chars=815; has_header=True; placeholder_present=False. | Fix renderer output before relying on generated private preview files. |
| preview renderer: cover letter | pass | chars=1391; has_header=True; placeholder_present=False. | Fix renderer output before relying on generated private preview files. |
| preview renderer: submission text packet | pass | chars=4308; has_header=True; placeholder_present=False. | Fix renderer output before relying on generated private preview files. |
