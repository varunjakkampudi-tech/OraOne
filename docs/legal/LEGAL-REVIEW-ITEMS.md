# Items that need owner or counsel decisions before publication

Each item blocks publication until answered. Reply in `blocker.txt` (round 17) with the decision.

## Owner decisions

1. Legal entity name, registered address and contact details for legal notices (both documents).
2. Terms version and privacy version identifiers to set on the server (`LEGAL_TERMS_VERSION`, `LEGAL_PRIVACY_VERSION`, `LEGAL_MARKETING_VERSION`).
3. Retention periods for every category of personal data, including call audio and transcripts, conversation history, uploaded files and backups.
4. Whether call audio is stored, or only transcripts, and for how long.
5. Whether paid billing will be enabled, and if so pricing, taxes and currency.
6. Service-level commitment (the application currently promises no uptime).
7. The data-request process (access, correction, export, deletion): who receives requests, identity checks, timelines. The product workflow for this is not yet built.
8. Minimum age for users.
9. Backup location, encryption and off-host copies.
10. Whether existing accounts must re-accept new terms when a version changes.
11. Whether the optional marketing choice covers email only, or also messages on connected channels (WhatsApp, Instagram, SMS).

## Counsel decisions

12. India: applicability of the Digital Personal Data Protection Act 2023 and the Rules; notice wording; consent wording; grievance officer; processor contracts; cross-border transfers.
13. Consumer-law limits on the warranty disclaimer and liability cap, for India and for each market the owner targets.
14. Governing law, venue and dispute process.
15. Whether the AI-output disclaimer is adequate for regulated sectors (health, legal, finance) the customers may serve.
16. Telecom rules for voice and SMS campaigns (TRAI and TCCCPR in India), and what the terms must require from customers.
17. The lawful basis for each processing purpose, and whether consent or legitimate interest applies to security logging.
18. Whether each AI and messaging provider's no-training and retention settings meet the commitments written in the policy.

## Facts verified in the code (for reviewers)

- Sign-in: one-time email code, five-minute expiry, single use, hashed storage.
- Signup: an account is created only after a correct code and the required acceptances (see `backend/app/services/auth_service.py`).
- Consent records: `signup_consents` table, one row per document per account, with version and UTC time.
- Providers named in the code: Resend, OpenRouter, Meta WhatsApp and Instagram, Telegram, Twilio, ElevenLabs, Google, Stripe (disabled in the current deployment), Cohere, Jina, PostgreSQL with pgvector, Redis.
- Not verified: each provider's real retention and training terms, the production hosting location, and the backup setup.
