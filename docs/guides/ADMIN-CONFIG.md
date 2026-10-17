# Admin and configuration guide

This guide explains where OraOne's settings live, how the configuration console works,
how values are masked, when a change takes effect, and how production secrets are
handled. It is for the person who runs the server and the platform administrator.
The full list of settings, with defaults, is in
[CONFIGURATION](../operations/CONFIGURATION.md).

This describes the working tree at the time of writing. The configuration console
and its registry were not yet committed.

## Three places where settings live

| Where                                                                                                   | What is stored there                                                                                  | How it changes                                          | Takes effect                                                                      |
| ------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- | ------------------------------------------------------- | --------------------------------------------------------------------------------- |
| **The server's environment**: the environment files on the server, or the secret store that writes them | Deployment settings and secrets: database, signing keys, provider keys, public addresses, mail server | Edit the file, or change the value in your secret store | After the containers are recreated (`up -d`)                                      |
| **The configuration console** (encrypted rows in the database)                                          | Values for keys the registry marks as console-managed, per environment (`local` or `production`)      | The console at `/admin/config`, or the API              | After the API restarts, or after a reload on the process that handled the request |
| **Platform records** (feature flags, product status, access)                                            | Platform switches that are read on every request                                                      | Platform administration API                             | At once                                                                           |
| **A customer's workspace** (assistants, widgets, channels, integrations, workflows, leads)              | Customer data                                                                                         | The customer, in Studio                                 | At once                                                                           |

A saved console value takes precedence over the environment file for the same key in
the same environment. Removing the saved value restores the value the process had
before the override.

## The configuration console

The console is at `/admin/config`, under **Configuration** in the administration menu.
Its API is `/api/admin/config`.

- **Who can use it.** Only a platform role of `super_admin`. The `admin` platform role
  does not get access to these routes.
- **Environments.** The page has two tabs, **Local** and **Production**. Each tab shows
  the keys that apply to that environment.
- **What the page shows.** For each key: its group, a description, whether it is
  required, whether it is set, where the value comes from (saved in the console, the
  deployment, or not set), and whether it is console-managed.
- **Values for the Local tab.** Plain values are shown in full. Secrets are masked.
- **Values for the Production tab.** Plain values are never shown. Secrets are masked.
  A server only knows its own environment. A production value can be seen as set or not
  set from a different server, and the page says so.

### Changing a value

1. Open the key on the page.
2. Enter the new value. Do not send line breaks or control characters. The limit is 2048 characters.
3. Type the exact key name in **confirm**.
4. Enter a **reason** of 10 to 500 characters. Do not put secrets in the reason.
5. Save. To remove a saved value, send an empty value (the page uses a remove action).

The server refuses a request when:

- the key is unknown, or does not apply to that environment;
- the key is not console-managed (these are read-only in the console);
- the confirm text does not match the key name;
- the reason is too short or too long;
- the value is empty when a value is expected, or contains control characters.

Each refused attempt is recorded in the audit log with the key name, the environment, the
requester and a reason code. Applied changes are recorded with the reason text.

### Reloading

The reload action (`POST /api/admin/config/reload`) re-reads the saved values into the
process that handles the request. It needs the confirm text `RELOAD` and a reason. It
does not change other processes. Each worker keeps the values it had until it restarts.
So a reload is not a substitute for a restart.

## Masking

- **Secrets** (keys marked secret in the registry) are never returned in full.
  - If the value is 12 characters or longer, the response includes the last four
    characters, labelled as "ends in".
  - If it is shorter, only "Set" is shown.
  - If it is not set, "Not set" is shown.
  - The page shows the same rule.
- **Plain values** are shown in full on the Local tab only. On the Production tab they
  are hidden, and the page shows "Hidden for this environment".
- The **audit log** never contains secret values. For plain values it records the old and
  new value, so do not save anything in a plain key that you would not want in the audit log.

## Restarts

Environment settings and saved console values are read when a process starts. A running
process does not see a change.

- **After an environment-file change**, recreate the containers. A plain restart keeps
  the old environment:

  ```bash
  docker compose --env-file .env.production -f docker-compose.prod.yml up -d backend workers
  ```

- **After a console change**, restart the API so that all its workers start again. The
  console values load before the settings are read, so a restart of the API container is
  enough:

  ```bash
  docker compose --env-file .env.production -f docker-compose.prod.yml restart backend workers
  ```

  A restart loads saved values into every worker. A reload does not do that.

- **Check the page.** When a saved change is newer than the process that serves the
  request, the page shows a **Restart required** banner.
- **Check the service.** Run `curl -fsS https://<your-domain>/api/health/ready` after the
  restart, then check the logs. The startup check may refuse a value that is missing or
  invalid (see [DEPLOYMENT](../operations/DEPLOYMENT.md)).

## Keys the console cannot change

These keys are marked not console-managed. They are bootstrap or process settings, and
changing them from a web request could lock the platform out or break decryption. They
stay in the environment file or the secret store:

- `ENVIRONMENT`, `RUN_BACKGROUND_WORKERS`, and the `GUNICORN_*` settings;
- `DATABASE_URL`, `ALEMBIC_DATABASE_URL` and the `DB_*` parts;
- `JWT_SECRET_KEY`, `SECRET_KEY` and `INTEGRATIONS_ENCRYPTION_KEY`;
- `EMBED_DIM`.

Keys that are not in the registry at all (for example the ElevenLabs settings and the
OAuth settings for Slack, Notion, HubSpot, Google Calendar and Google Sheets) are also
outside the console. See [CONFIGURATION](../operations/CONFIGURATION.md), section 13.

## How saved values are stored

- Each saved value is stored encrypted, one row per environment and key, with the user
  who saved it and the time. The encryption uses the integration encryption key, which is
  derived from `INTEGRATIONS_ENCRYPTION_KEY`, or from `SECRET_KEY` or `JWT_SECRET_KEY`
  when that is unset.
- **If the encryption key changes**, saved values cannot be decrypted. Each unreadable
  value is skipped, and the environment file value for that key applies. The page still
  shows the key as set, without a masked tail. Re-save the value, or restore the old key.
- A saved row is applied at startup only for the environment the process runs in.
  A local instance does not apply production rows, and the reverse.

## Production secrets

- **Secrets are kept on the server or in a secret store, not in the repository.** The
  repository ignores `.env`, `.env.*` and `backend/.env`. Only the `.example` templates are
  tracked. Both Docker build contexts exclude these files, so they are not copied into images.
- **Use the server's secret store.** Keep the environment files readable only by the
  deployment user, or use a managed secret store that writes them at deploy time. Do not
  paste values into chat, tickets, email, documents or commit messages.
- **Generate strong values.** `JWT_SECRET_KEY` must be at least 32 characters. Generate it
  with a cryptographic generator, for example
  `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
- **Set `INTEGRATIONS_ENCRYPTION_KEY` explicitly** in production. Otherwise rotating the
  JWT secret also makes stored integration tokens and console-saved values unreadable.
- **Rotation.**
  - Rotating `JWT_SECRET_KEY` makes access tokens issued with the old key invalid, so users
    sign in again. It also invalidates marketing unsubscribe links, which are signed with
    that key.
  - To rotate a provider credential, create the new one at the provider, save it (in the
    console or the environment file), restart the API, test, then revoke the old one.
- **Limit access.** Only people who run the deployment should read the environment files.
  Only people who need it should hold a `super_admin` platform role, because that role can
  write production values.

## Who can change what

| Change                                                                     | Who                            | Where                                                                                                                                              |
| -------------------------------------------------------------------------- | ------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| Console-managed settings, per environment                                  | A `super_admin` platform user  | `/admin/config`, or `PUT /api/admin/config/{name}`                                                                                                 |
| Environment-only settings, for example database and signing keys           | The person who runs the server | Environment file or secret store, then `up -d`                                                                                                     |
| Feature flags and product status                                           | A platform administrator       | `PATCH /api/super-admin/feature-flags/{key}` and `PATCH /api/super-admin/products/{key}`. The administration pages do not yet offer these controls |
| Customer settings (assistants, widgets, channels, integrations, workflows) | The customer                   | Studio                                                                                                                                             |

## Other administration pages

The other administration pages in this build are previews. Their footer reads
"Frontend preview · No privileged access", and their editing controls are disabled.
They do not change production. Use the API or the server for those changes.

## Checks after any change

1. `GET /api/health/ready` returns 200.
2. The backend and workers logs show no new startup error. A missing or invalid setting is
   named there, without its value.
3. The changed flow works: sign-in for an email change, a test widget message for a widget
   change, a test webhook for a provider change, or a test call for a Twilio change.
4. Record the change with the setting **name**, the environment, the date and the reason.
   Do not record the value.
