# Changelog

## v1.0.8 — Preserve frontend security headers

- Keep frame, permissions, referrer, and MIME-sniffing protections on the SPA entry point and immutable assets despite Nginx `add_header` inheritance rules.
- Verify headers on the deployed HTML and static assets.

## v1.0.7 — Cognito logout build configuration

- Complete Cognito hosted logout after clearing the OraOne session.
- Pass the Cognito sign-out URI explicitly into the production frontend image build.
- Verify production sign-out returns to a fresh email sign-in screen.

## Unreleased — documentation and repository presentation

- Rebuilt the root README around actual product scope, architecture, local setup, security boundaries, and release gates.
- Added structured architecture, guide, operations, security, roadmap, product portfolio, licensing, and documentation-index pages.
- Added Mermaid source diagrams and a reproducible documentation validation script.
- Removed unsupported public metadata claims from frontend HTML.
- Corrected the nested widget package repository URL to this repository.
- Completed the ten-product portfolio, embedded all ten source-backed Mermaid diagrams, and expanded clean-clone Quick Start and environment guidance.
- Added Markdown anchor, code-fence, Mermaid source/embed parity, missing-file, and process-exit validation.
- Documented the canonical GitHub private vulnerability-report URL while leaving feature enablement for owner verification.

No hosting, production database, AWS, DNS, payment, or repository-visibility changes are included.
