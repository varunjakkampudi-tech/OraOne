# Legal documents (drafts)

Status: **DRAFT. Not approved. Not published.**

These drafts describe the data flows and providers that the code in this repository actually uses, as of 20 October 2026. They are written for review by the owner and by qualified counsel. They are not legal advice and they do not state that OraOne complies with any law.

Files:

- `TERMS-OF-SERVICE.DRAFT.md`: draft Terms of Service shown at signup.
- `PRIVACY-POLICY.DRAFT.md`: draft Privacy Policy linked at signup.
- `LEGAL-REVIEW-ITEMS.md`: every provision that needs an owner or counsel decision before publication.

Publication rules (see `blocker.txt`, round 17):

1. The owner approves each document, and counsel reviews the privacy policy for India DPDP applicability and any other market the owner chooses.
2. The approved version identifiers are set on the server with `LEGAL_TERMS_VERSION`, `LEGAL_PRIVACY_VERSION` and `LEGAL_MARKETING_VERSION`. Any value beginning with `draft` keeps signup closed in production.
3. Only then are the documents published at `/terms` and `/privacy`.
