# Operations runbook

For each common problem: the symptom, the likely causes (in order), what to check, and the fix.
Settings are named in [CONFIGURATION](CONFIGURATION.md). Log lines quoted below are
written by the code, so search for them with `docker compose ... logs`.

Commands assume the production Compose file. Set the environment file as in
[DEPLOYMENT](DEPLOYMENT.md):

```bash
DC="docker compose --env-file .env.production -f docker-compose.prod.yml"
$DC logs --tail=200 backend workers
```

**Applying an environment change.** Settings are read when a process starts, and Compose
gives a container its environment when the container is created. After you edit
`.env.production` or `backend/.env`, recreate the containers with `up -d`. `restart`
keeps the old environment:

```bash
$DC up -d backend workers
```

Never paste logs or environment files into a ticket without removing phone numbers,
email addresses, tokens and keys first. The code avoids logging contact details and
provider secrets, but other tools may not.

---

## 1. Webhook signature is failing (HTTP 401, or a handshake returns 403)

**Symptom.** A provider shows failed deliveries. The API answers 401 for a POST, or 403
for the Meta GET handshake. Nothing appears in the inbox.

The code fails closed on purpose. Every inbound webhook is refused when the secret it
needs is missing, so a 401 is the expected answer until the setting is correct.

**Check by provider.**

- **Twilio (SMS, WhatsApp, voice, call status).** The signature is computed from
  `PUBLIC_API_BASE_URL` plus the request path and query string, and the form fields.
  - `PUBLIC_API_BASE_URL` must be exactly the public `https://` origin that Twilio calls. A value
    with `http://`, a different host, or a trailing path is the usual cause. Behind a
    proxy the application cannot infer the public URL, so it must be configured.
  - `TWILIO_AUTH_TOKEN` must belong to the same Twilio account that owns the number.
  - Logs: `call_status_rejected reason=bad_signature` or `reason=not_configured` for calls.
    The messaging path returns 401 without a log line of its own.
  - If `TWILIO_AUTH_TOKEN` or `PUBLIC_API_BASE_URL` is unset, every Twilio webhook is refused.
    The startup check refuses to boot in production if a `TWILIO_*` setting is set without them.
- **Meta (WhatsApp, Instagram POST).** Check `META_WHATSAPP_APP_SECRET`. It must be the
  App Secret of the Meta app that sends the webhook. It is not the access token. The
  signature covers the raw request body, so a proxy or middleware that rewrites the body
  breaks it.
  - Meta GET handshake: `META_WHATSAPP_VERIFY_TOKEN` must equal the token typed in Meta's console. Unset means 403.
- **Inbound email.** The header `X-Email-Inbound-Secret` must equal `EMAIL_INBOUND_SECRET`. Unset refuses every request.
- **Telegram.** The bot token is in the URL path. The header `X-Telegram-Bot-Api-Secret-Token` must equal the `telegram_webhook_secret` stored on the channel binding (database value, not an environment setting). Logs: `inbound rejected: bad or missing secret provider=telegram`.
- **SDK (mobile and desktop).** The header `X-OraOne-Signature` is an HMAC of the raw body with the binding's `sdk_secret`. Logs: `inbound rejected: bad or missing secret provider=sdk`.
- **Stripe.** `STRIPE_WEBHOOK_SECRET` is required when billing is enabled. Missing: 503.

**Fix.** Correct the setting, recreate the backend and workers (`$DC up -d backend workers`, see the note at the top), then resend a test event from the provider's console.

---

## 2. A call was not placed

**Symptom.** A campaign is running, but no call happens, or a lead is marked skipped.

**Check, in this order.**

1. **Campaign status.** Only a `running` campaign places calls. `paused` stops new calls and lets a call in progress finish. A campaign becomes `completed` when no queued attempts remain.
   1a. **Voice binding.** A call that connects but is answered with "this number is not available" has no enabled voice binding (or SMS or WhatsApp binding) on the calling number. Bindings are database records, and no screen or API creates them yet. Engineering must check the `agent_channels` row for the number.
2. **Start response.** `POST /api/calls/campaigns/{id}/start` returns 503 with `Calling is not configured. Set ... on the server.` when a setting is missing. The message names the settings. Set `TWILIO_ACCOUNT_SID` and `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER` and `PUBLIC_API_BASE_URL`, then recreate the containers.
3. **Attempt reasons.** `GET /api/calls/campaigns/{id}/attempts` lists each attempt with its status and reason. A skipped attempt carries the policy reasons. Common reasons:
   - No consent. Leads need consent `given`. An imported `granted` value is self-attested and carries the note "Imported consent, confirm the source".
   - Quiet hours (21:00 to 08:00 local time). The lead's own IANA timezone, stored with the lead, is used when set. Otherwise the campaign timezone is used only when the phone number's country code is recognised. Otherwise the lead cannot be dialled and the reason asks for a timezone.
   - Daily cap of 2 attempts per contact in 24 hours (default policy).
   - Do-not-contact list entry, or opt-out (`STOP` reply).
4. **Phone format.** A number that is not E.164 (`+` and country code, 7 to 15 digits) fails with `Phone number is not in E.164 format.` Correct the lead.
5. **Twilio refused the call.** The attempt is marked failed with outcome `dial_error_<http-status>`. Log: `call_dial_failed campaign=... attempt=... http=...`. The reason is in Twilio's account (check the call error in Twilio's console).
6. **Callbacks are not arriving.** The campaign moves forward only when Twilio posts status to `/api/voice/status` (or when someone calls start again). There is no timer. A call still `calling` after 30 minutes is checked with Twilio, then released, the next time the queue advances. If callbacks never arrive, check that `PUBLIC_API_BASE_URL` matches the public origin, because the callback signature depends on it (see section 1).

**Fix.** Fix the cause, then resume the campaign (it may need `start` again, depending on its status).

---

## 3. A message was not sent

Inbound messages are always stored. A reply can fail independently. Find the channel first.

| Channel                                       | Cause                                                                              | What to check or do                                                                                                                                                 |
| --------------------------------------------- | ---------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Twilio SMS or WhatsApp                        | `TWILIO_ACCOUNT_SID` or `TWILIO_AUTH_TOKEN` missing                                | Log: `twilio messaging not configured; reply not sent`. Set both.                                                                                                   |
| Twilio SMS or WhatsApp                        | Twilio returned an error                                                           | Log: `twilio send failed: HTTP <code>`. Check the error in Twilio's console.                                                                                        |
| Meta WhatsApp                                 | `META_WHATSAPP_ACCESS_TOKEN` missing, or no `phone_number_id` on the binding       | Replies are not sent silently. Log: `meta whatsapp send failed: HTTP <code>` if Meta refused.                                                                       |
| Instagram                                     | `META_INSTAGRAM_ACCESS_TOKEN` missing, or no `instagram_account_id` on the binding | Replies are not sent silently. Log: `meta instagram send failed: HTTP <code>` if Meta refused.                                                                      |
| Telegram                                      | Bot token rejected                                                                 | Send returns failure silently. Check the bot token on the binding.                                                                                                  |
| Email                                         | Replies are not sent by the application                                            | Expected. The email adapter stores the answer and does not deliver it (`email reply ready (delivery via provider)`). Deliver replies through your own mail process. |
| Website chat and API                          | Visitor does not see a reply                                                       | Check the widget section (section 5).                                                                                                                               |
| Staff reply in the inbox                      | Staff messages are stored in OraOne only                                           | Expected. Staff replies are not sent to WhatsApp, Instagram, SMS or email.                                                                                          |
| Workflow `send_message` step                  | Consent missing, or no enabled channel binding                                     | The step fails with a plain reason. Open the run in Studio to read it.                                                                                              |
| Email (campaign or workflow)                  | Email delivery is not connected on this server                                     | Expected. The send fails with "Email delivery is not connected on this server yet."                                                                                 |
| Marketing campaign (SMS, WhatsApp, Instagram) | No enabled binding, or the provider is not configured                              | Each affected recipient is recorded as not sent, with the reason. The campaign still completes.                                                                     |
| Spoken reply (AI Voice)                       | ElevenLabs failed or is misconfigured                                              | The turn falls back to the Twilio voice, so the call continues. The log records status codes only.                                                                  |
| Any channel                                   | The assistant is paused                                                            | The visitor receives "Thanks for your message! Our assistant is briefly unavailable". Activate the agent.                                                           |
| Any channel                                   | The contact sent `STOP`                                                            | The contact is recorded as opted out and receives no AI reply. This is by design.                                                                                   |
| Any channel                                   | Webhook redelivered by the provider                                                | Ignored on purpose (log: `duplicate inbound ignored`). The first delivery was answered.                                                                             |
| Any channel                                   | No binding for the number, bot or address                                          | Log: `no agent bound for <provider>/<channel>`. The binding is missing or disabled (section 4 of [PRODUCTS](../guides/PRODUCTS.md)).                                |

---

## 4. Quota is unavailable ("We cannot check this limit yet.")

**Symptom.** A request is refused, with a message about a limit that cannot be checked.
The outcome is `unmeasured` (authorization outcome `quota_unavailable`).

**Cause.** A quota has no usage source in this version of the code. `storage_mb` is
one example. Recordings and exports are not metered. In production an unmeasured quota
fails closed. In development it is allowed.

**What to do.**

1. Confirm the metric in the response or logs. Do not change the production environment to get around the check.
2. Decide whether the limit must be measured (a code change) or whether the feature should stay blocked. This is a product decision, not a configuration change.
3. For local testing only, use `ENVIRONMENT=development`. Never change `ENVIRONMENT` on a production server to bypass a quota.

`AUTHZ_ENFORCE_QUOTAS` and `AUTHZ_ENFORCE_SUBSCRIPTION` do not change this fail-closed
behaviour. They control whether other quota and subscription denials are enforced.

---

## 5. The website widget is not showing

Work through the list in order. The first match is the usual cause.

1. **Published?** In Studio, open the assistant's **Add to website** page. The widget must be published. A paused widget is hidden. Publishing an agent that has no system prompt does not activate it.
2. **Script on the page?** View the page source. The `<script src=".../widget.js" data-widget-id="...">` tag must be present on the live page, not only in a test page. Open `https://<your-domain>/widget.js` directly. It must return the script, not an error page.
3. **Snippet origin.** The snippet uses `WIDGET_CDN_BASE` (default `FRONTEND_URL`) and `WIDGET_API_BASE` (default the CDN origin). If `FRONTEND_URL` is unset in production, the snippet points to `http://localhost:3000`. Fix the setting and reinstall the snippet.
4. **Allowed websites.** In production an empty allow-list denies every host. The API answers `403 This widget is not authorized for this domain.` Add the domain on its own line (for example `example.com`). The check compares the host from the `Origin` header.
5. **Widget not live.** The API answers `403 Widget is not live.` when the widget is paused, or has not been published.
6. **Rate limit.** `Too many messages — please slow down.` means the per-IP limit (`WIDGET_IP_RATE_LIMIT_PER_MIN`, default 60) was reached. This is expected for automated traffic.
7. **Browser blocks it.** Check the browser console for Content-Security-Policy messages. The site's policy must allow the CDN origin and the API origin.
8. **Wrong widget key.** The `data-widget-id` is the widget's public key. If it was regenerated, the old key stops working. Use the current snippet.

---

## 6. Integration not configured

**Symptom.** Studio shows "Not configured yet" or "requires account setup", or the connect call returns 503.

**Cause and fix.**

- Google Drive needs `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` on the server. Without them the connect call returns 503 and nothing is connected. Set both, then recreate the containers.
- `GOOGLE_REDIRECT_URI` must match the redirect URI registered in Google's console, which is `https://<your-domain>/api/integrations/google/callback`. The default value is a localhost address.
- "Planned. This connector is not available yet." means the provider is catalogue-only. Gmail and Salesforce are in this state, and connecting them returns 409. This is expected.
- Slack, Notion, HubSpot, Google Calendar and Google Sheets connect through OAuth but do not sync data yet. Only Google Drive syncs. A connected provider with no data is expected.
- Each provider has its own redirect setting. Google Drive uses `GOOGLE_REDIRECT_URI` and the path `/api/integrations/google/callback`. The others use `<PREFIX>_REDIRECT_URI` and `/api/integrations/oauth/callback`. A mismatch fails the callback.
- A callback that reports an expired or consumed state: OAuth state lasts 10 minutes and is single-use. Start the connection again.
- A callback that cannot find the nonce cookie: the cookie is set on `/api/integrations` with the `Secure` flag outside development. The flow must run over HTTPS through the public origin.
- After rotating `JWT_SECRET_KEY` or `SECRET_KEY`, previously stored integration tokens cannot be decrypted. Connect the integration again. Setting `INTEGRATIONS_ENCRYPTION_KEY` to a fixed value avoids this in future.

---

## 7. Sign-in codes do not arrive

**Symptom.** A user asks for a sign-in code and gets an error ("Sign-in codes cannot be sent right now") or never receives a code.

**Cause.** When `SMTP_HOST` is unset, the log says `email (SMTP_HOST not configured) ... [not sent]`. When SMTP fails, the log says `SMTP send failed` with the error type. In both cases the server removes the stored code and the sign-in request returns HTTP 503, so no code is issued. The log line `email_code_not_delivered` marks the failed request.

**Fix.** Set `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` and `SMTP_USE_SSL` (`true` for port 465, `false` for STARTTLS). Restart the backend. Send yourself a code to test. Codes last 10 minutes.

---

## 8. Readiness is failing (`/api/health/ready` returns 503)

The response body lists each check. Look at the first one that is not `connected`.

- `database: unreachable` means `DATABASE_URL` is wrong, the database is down, or the password changed. Check the `postgres` container and its health.
- `redis: not_configured` in production means `REDIS_URL` is unset. Set it, then recreate the containers.
- `redis: unreachable` means the Redis container is down or the URL is wrong.

The backend container's health check uses `/api/health/ready`. The `restart: unless-stopped`
setting restarts a container that exits. It does not restart a container that is only
reported unhealthy. A restart loop usually means the startup check refused to boot, so
read the log for the named settings.

---

## 9. The API refuses to start

Read the first error in `docker compose ... logs backend`.

| Log text                                                                                                  | Meaning                                            | Fix                                                                                                                                                                             |
| --------------------------------------------------------------------------------------------------------- | -------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Refusing to start: incomplete configuration ... Missing or invalid settings (values not shown): <names>` | A production startup check failed                  | Set the named settings. Read the list in [DEPLOYMENT](DEPLOYMENT.md).                                                                                                           |
| `JWT_SECRET_KEY must be at least 32 characters`                                                           | The secret is missing or short                     | Generate a new one. Changing it invalidates existing access tokens. If the encryption key is derived from it, stored integration tokens and console values become unreadable.   |
| `CORS_ORIGINS requires exact frontend origins in deployment environments.`                                | Production without `CORS_ORIGINS`                  | Set the public origin.                                                                                                                                                          |
| `CORS_ORIGINS accepts only exact HTTP(S) origins...`                                                      | A wildcard, path, query or credential was included | Use `https://<your-domain>` only.                                                                                                                                               |
| `alembic` migration error during `migrate`                                                                | The schema cannot be upgraded                      | Read the migration error. Do not start the API until `migrate` exits with 0. Restore from backup if the database is inconsistent (see [backup and restore](BACKUP-RESTORE.md)). |

---

## 10. Rate limits affect all users at once

**Symptom.** Many users get `429` responses at the same time, from the same network.

**Cause.** `TRUSTED_PROXY_IPS` does not include the proxy's current address, so every request is counted against the proxy's own address. The proxy address can change when its container is recreated.

**Fix.** Find the current proxy address (see [DEPLOYMENT](DEPLOYMENT.md), step 5), update `TRUSTED_PROXY_IPS` in `.env.production`, and recreate the backend:

```bash
$DC up -d backend workers
```

---

## 11. Uploads fail

**Symptom.** Document upload returns an error, or the logs mention the upload directory.

**Cause.** `UPLOAD_DIR` is not writable by the `oraone` user (UID 1000), or it is a symbolic link, or it is owned by another user. The storage code refuses those directories. The default `/tmp/oraone-uploads` is used only when `UPLOAD_DIR` is unset.

**Fix.** Check ownership with `docker compose ... exec backend ls -ld /var/lib/oraone/uploads`. The owner must be UID 1000. Correct it, then retry the upload.

---

## 12. Workflow runs do not start

- Scheduled workflows run only in the `workers` process (or in an API process where `RUN_BACKGROUND_WORKERS=true`). Check that `oraone-prod-workers` is running.
- Event workflows need an event the engine supports: `lead.created` or `message.received`. Other names are rejected when the workflow is saved.
- The workflow must be active. A draft workflow never runs. Marketplace installs of workflows always start as drafts.

---

## 13. A value saved in the configuration console is wrong, or does not apply

**Symptom.** A saved value does not take effect, the page shows "Restart required", or the
page shows a key as set without a masked tail.

**Check, in this order.**

1. **Restart.** Saved values load when the API starts. Restart the backend and workers
   containers with `restart` (or with `up -d` if the environment file also changed). A reload
   from the page only changes the process that handled the request. Other workers keep their
   values until they restart.
2. **Environment.** A value is saved for either `local` or `production`. Make sure the tab you
   changed matches the server you are checking.
3. **Encryption key.** Saved values are encrypted. If `INTEGRATIONS_ENCRYPTION_KEY` (or the
   `SECRET_KEY` or `JWT_SECRET_KEY` it is derived from) changed, a saved value cannot be read.
   It is then skipped, and the environment file value applies. The page shows "Set" with no tail.
   Re-save the value, or restore the old key.
4. **Key scope.** Keys that are not console-managed cannot be saved there, including
   `DATABASE_URL`, `JWT_SECRET_KEY`, `SECRET_KEY` and `INTEGRATIONS_ENCRYPTION_KEY`. Change those in
   the environment file and recreate the containers.

**Fix.** Re-save the value with a reason of 10 to 500 characters and the exact key name in the
confirm field. To remove a saved value, remove it on the page, then restart. The audit log records
each change, the requester and the reason.

---

## Where to look first

| Question                    | Look at                                                                         |
| --------------------------- | ------------------------------------------------------------------------------- |
| Is the stack up?            | `$DC ps`                                                                        |
| Is the API healthy?         | `/api/health`, then `/api/health/ready`                                         |
| Why did a webhook fail?     | `backend` log, search for `rejected`, `bad or missing secret`, `not_configured` |
| Why did a call fail?        | Campaign attempts (API), then `workers` and `backend` logs for `call_` lines    |
| Why did a message not send? | The table in section 3, then `send failed` lines                                |
| Restore the database        | [BACKUP-RESTORE](BACKUP-RESTORE.md)                                             |
