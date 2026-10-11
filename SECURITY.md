# Security policy

## Scope

This policy covers the OraOne source repository and the local application code. A local test result is not evidence that a hosted deployment is secure.

## Reporting

Do not open a public issue for a suspected vulnerability. Send a private report to the repository owner using an authorized private channel and include a sanitized reproduction, affected revision, impact, and suggested mitigation.

Never include passwords, OTPs, bearer tokens, provider keys, database credentials, or private customer data.

## Release boundaries

High-risk areas include Cognito token handling, RBAC and tenant isolation, webhook SSRF and retries, file uploads and crawling, prompt injection, provider and billing integrations, secret history, and backup/restore. Production claims require current test and runtime evidence for the relevant boundary.

## Response expectations

Reports are triaged, reproduced, fixed, tested, and documented according to impact. Coordinated disclosure timing is agreed with the reporter.
