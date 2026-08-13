# Target Venue Policy Checklist Audit

Checked date: 2026-07-09

This audit records public policy entry points for the remaining author/venue gate. It does not fill private author metadata.

## Status counts

- pass: 9

| venue | item | metadata paths | public source | status |
|---|---|---|---|---|
| ACM Transactions on Quantum Computing | Submission route and manuscript type | `target_venue.name; target_venue.manuscript_type` | https://dl.acm.org/journal/tqc/author-guidelines | pass |
| ACM Transactions on Quantum Computing | ACM template and TAPS-compatible LaTeX discipline | `target_venue.formatting_policy_checked; target_venue.reference_style_checked; target_venue.supplementary_material_policy_checked` | https://www.acm.org/publications/authors/submissions | pass |
| ACM Transactions on Quantum Computing | Authorship, ORCID, corresponding author, and conflicts | `authors[]; corresponding_author.*; author_contributions.*; competing_interests.statement` | https://www.acm.org/publications/policies/new-acm-policy-on-authorship | pass |
| ACM Transactions on Quantum Computing | AI assistance disclosure | `target_venue.ai_disclosure_policy_checked; ai_assistance.statement` | https://www.acm.org/publications/policies/frequently-asked-questions | pass |
| ACM Transactions on Quantum Computing | Prior publication and preprint status | `preprint_and_prior_submission.*` | https://www.acm.org/publications/policies/new-acm-policy-on-authorship | pass |
| Quantum | ArXiv or quant-ph route | `target_venue.name; target_venue.manuscript_type; preprint_and_prior_submission.preprint_url_or_doi` | https://quantum-journal.org/instructions/authors/ | pass |
| Quantum | Author contribution and AI statement | `author_contributions.*; ai_assistance.statement` | https://quantum-journal.org/instructions/authors/ | pass |
| Quantum | Cover letter, editor, referee, and exclusivity checks | `cover_letter.target_editor; cover_letter.suggested_reviewers; cover_letter.excluded_reviewers; preprint_and_prior_submission.prior_submission_history` | https://quantum-journal.org/instructions/authors/ | pass |
| Any selected venue | Data, code, archive, license, and anonymous-review links | `data_availability.*; code_availability.*; target_venue.anonymous_review_required` | submission_package/dist/resource_nmcts_submission_payload.tar.gz | pass |
