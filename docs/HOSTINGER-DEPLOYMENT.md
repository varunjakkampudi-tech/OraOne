# Hostinger production deployment (oraone.in)

This page describes the production host that serves `oraone.in`: a Hostinger VPS in the
Mumbai region, the DNS records, the server hardening, the Docker Compose stack, and how to
deploy, check and roll back. The generic stack steps (environment files, startup checks,
provider webhooks) are in [DEPLOYMENT](operations/DEPLOYMENT.md). This page does not repeat
them.

The server's public IP address is deliberately not written here. Use "the VPS IP" and keep
the address in the DNS panel and the owner's records.

## How to read the source column

Every fact has one of three sources:

- **Repo**: checked against a file in this repository. The file is named.
- **Owner**: stated by the owner. It is not in the repository and was not checked on the server.
  Verify it with the commands in section 9 before you rely on it.
- **Not configured**: the repository and the owner's records show that it is missing.

## 1. Summary

| Item                    | Value                                                                          | Source                                                                                                         |
| ----------------------- | ------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------- |
| Host                    | Hostinger VPS, Mumbai (India) region                                           | Owner. `blocker.txt` item 12 also refers to a Mumbai server                                                    |
| Operating system        | Ubuntu 26.04                                                                   | Owner                                                                                                          |
| Public site             | `https://oraone.in`                                                            | Repo: `CADDY_DOMAIN` is required by `docker-compose.prod.yml`; `VITE_SITE_URL` defaults to `https://oraone.in` |
| Public entry point      | Caddy, ports 80 and 443 only                                                   | Repo: `docker-compose.prod.yml` (`proxy`), `Caddyfile`                                                         |
| Application directory   | `/opt/oraone`                                                                  | Owner (`blocker.txt` items 1 and 3)                                                                            |
| Container orchestration | Docker Compose, file `docker-compose.prod.yml`                                 | Repo                                                                                                           |
| Release                 | Build on the server from a checked-out commit; image tag from `ORAONE_VERSION` | Repo: `docker-compose.prod.yml`                                                                                |
| Mail for sign-in codes  | Not configured                                                                 | Owner (`blocker.txt` item 1). See section 8                                                                    |
| Backups                 | Not configured                                                                 | Repo: `docs/operations/BACKUP-RESTORE.md`. See section 8                                                       |
| Deploy workflow         | Not present in the repository                                                  | Repo: `.github/workflows/` holds test, lint and formatting workflows only                                      |

## 2. DNS records

Set these in the DNS zone for `oraone.in`. The registrar and DNS host are owner-managed.

| Name              | Type                       | Value                                            | Purpose and notes                                                                                                                                                                                                                                                                                                   |
| ----------------- | -------------------------- | ------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `@` (`oraone.in`) | A                          | the VPS IP                                       | Points the site at the server. Caddy needs ports 80 and 443 reachable to obtain the certificate for `CADDY_DOMAIN`.                                                                                                                                                                                                 |
| `@`               | CAA                        | `0 issue "letsencrypt.org"` (confirm before use) | Limits which certificate authority may issue for the domain. Caddy's `Caddyfile` does not name an issuer. Caddy's default configuration may fall back to a second authority, and this CAA value would block that fallback. Confirm the authority with the owner, and test a renewal, before you publish the record. |
| `www`             | A or CNAME                 | owner decision                                   | Not served. The `Caddyfile` answers only the host in `CADDY_DOMAIN`, so `www` gets no certificate unless it is added to the configuration. Do not publish `www` until that change is made.                                                                                                                          |
| Mail records      | MX, SPF (TXT), DKIM, DMARC | copy from the Hostinger mail panel               | Managed in Hostinger. Do not edit them by hand from this page. They do not send application mail yet (see section 8).                                                                                                                                                                                               |

DNSSEC: owner-stated as enabled at the registrar. A DNSSEC change must publish the DS record at
the parent zone. Check it with section 9 before you change nameservers.

Registrar lock: owner-stated as enabled. Keep it on, and keep registrar two-factor sign-in
enabled. The owner holds that access. It is not an application setting.

## 3. Network and host hardening

All of this section is **Owner** unless marked otherwise. Repository files do not configure
the host firewall, fail2ban or SSH.

| Control                 | Required state                                                                                                                                                                                                                                                                  | Source                                                     |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| Firewall, inbound       | Allow 22/tcp (SSH), 80/tcp and 443/tcp. Deny other inbound traffic.                                                                                                                                                                                                             | Owner                                                      |
| Docker and the firewall | Docker publishes container ports through its own firewall rules. Those rules can bypass host firewall rules. The only ports this repository publishes are 80 and 443 on `proxy`. After any change, check `docker ps` and confirm that nothing else listens on a public address. | Repo (`docker-compose.prod.yml`), general Docker behaviour |
| fail2ban                | Enabled, with the `sshd` jail active.                                                                                                                                                                                                                                           | Owner                                                      |
| SSH                     | Key-only login. Password login disabled. Root login by password disabled.                                                                                                                                                                                                       | Owner                                                      |
| SSH deploy account      | `blocker.txt` item 5 proposes `root` as the deploy user. Owner decision: a dedicated deploy user that is in the `docker` group is the safer choice.                                                                                                                             | Repo (`blocker.txt`)                                       |
| Security updates        | Not stated in any file.                                                                                                                                                                                                                                                         | Not configured (unknown)                                   |

Database and Redis ports are not published. Inside the Compose network they are reachable only
by the services that need them.

## 4. Docker Compose stack

The stack is defined in `docker-compose.prod.yml`. The file is run from `/opt/oraone`.

| Service    | Image or build                                      | Published?            | Role and checks                                                                                                                |
| ---------- | --------------------------------------------------- | --------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| `proxy`    | `caddy:2.11.7-alpine`, with `Caddyfile` read-only   | 80 and 443            | The only public entry point. Terminates TLS for `CADDY_DOMAIN`. Sends `/api/*` to `backend` and everything else to `frontend`. |
| `frontend` | built from `frontend.Dockerfile`                    | No (port 8080 inside) | The web application, a Node server. Starts after `backend`.                                                                    |
| `backend`  | built from `backend/Dockerfile`                     | No (port 8000 inside) | API under Gunicorn as user `oraone`. Health check on `/api/health/ready`. Waits for `migrate`, `postgres` and `redis`.         |
| `workers`  | same image as `backend`, command `python worker.py` | No                    | Workflow scheduler and webhook outbox. `RUN_BACKGROUND_WORKERS=true`. No health check (no HTTP endpoint).                      |
| `migrate`  | same image as `backend`                             | No                    | One-shot `alembic upgrade head`. `backend` and `workers` start only after it exits with code 0.                                |
| `postgres` | `pgvector/pgvector:pg16`                            | No                    | The database. Health check with `pg_isready`.                                                                                  |
| `redis`    | `redis:7.4.11-alpine`                               | No                    | Shared store for rate limits, sign-in codes and other state. Health check with `redis-cli ping`.                               |

Named volumes:

| Volume                 | Mounted in           | Contents                                         |
| ---------------------- | -------------------- | ------------------------------------------------ |
| `oraone_postgres_data` | `postgres`           | Database files                                   |
| `oraone_redis_data`    | `redis`              | Redis data                                       |
| `oraone_uploads`       | `backend`, `workers` | Uploaded documents, at `/var/lib/oraone/uploads` |
| `oraone_caddy_data`    | `proxy`              | Caddy certificates and state                     |

Docker prefixes volume names with the Compose project name, which defaults to the directory name.
Keep the directory name, or set the project name explicitly, so that the stack finds its existing
volumes. Losing `oraone_caddy_data` makes Caddy request new certificates, which Let's Encrypt
rate-limits if this happens repeatedly.

The image tags above are the ones in `docker-compose.prod.yml`, which is the authoritative source.

## 5. Server layout

```text
/opt/oraone/
  docker-compose.prod.yml      from the repository
  Caddyfile                    from the repository
  frontend.Dockerfile          from the repository
  backend/                     from the repository
    .env                       application settings for migrate, backend and workers (Owner)
  .env.production              Compose interpolation values (Owner)
```

- `.env.production` is passed with `--env-file`. It holds `DB_PASSWORD`, `OPENROUTER_API_KEY`,
  `TRUSTED_PROXY_IPS` and `CADDY_DOMAIN`, and optionally `ORAONE_VERSION`.
- `backend/.env` is read through `env_file`. It holds the application settings. Its keys are listed
  in [CONFIGURATION](operations/CONFIGURATION.md).
- Both files are git-ignored (`.gitignore` covers `.env` and `.env.*`, and `backend/.env`).
  Keep them readable only by the deploy account (`chmod 600`). This permission is a recommendation;
  the repository does not enforce it.
- Never paste these files into chat, tickets or logs. Do not run `docker compose config` without
  `--quiet`, because it prints the resolved secrets.

## 6. Deploy manually

Run these on the server as the deploy account. Replace `<release>` with a tag or commit that you
have reviewed.

```bash
cd /opt/oraone
git status --short                      # must print nothing before you deploy
git fetch --tags origin
git checkout <release>
git log -1 --oneline                    # confirm the commit

# Set ORAONE_VERSION in .env.production to a new value for this release (see section 7).

docker compose --env-file .env.production -f docker-compose.prod.yml config --quiet
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build
```

Compose runs the steps in order: `postgres` and `redis` become healthy, then `migrate` runs
`alembic upgrade head`, then `backend` and `workers`, then `frontend`, then `proxy`. If `migrate`
fails, nothing else starts. Read its log:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml logs --tail=200 migrate
```

Then run the checks in section 9.

Before you deploy a release that changes the database schema, check the backup status in section 8.
Without a verified backup, a migration is not reversible in practice (see section 7).

## 7. Rollback

**Status: not verified.** The repository does not contain a tested rollback procedure
(`docs/operations/DEPLOYMENT.md` says so, and the release checklist lists "rollback tested" as an
open gate). The options below are the ones the repository's tooling supports, with their limits.

1. **Application code.** Check out the last known-good commit, set `ORAONE_VERSION` to a tag that
   was not used for the bad release, and run `up -d --build` again. Use a new `ORAONE_VERSION` for
   every release. Re-using a tag such as `v1.0.0` replaces the image that the previous release used.
   Images are built on the server and are not pulled from a registry.
2. **Database schema.** The repository has no tested downgrade procedure for Alembic. The backend
   starts with `alembic upgrade head`. An earlier application image may not run against a newer
   schema, so a release that changes the schema is not reversible by redeploying the old code alone.
3. **Database data.** Restore from a backup. The backup procedure is described in
   [BACKUP-RESTORE](operations/BACKUP-RESTORE.md). It is not yet scheduled on this server (section 8).

Until backups and a restore drill are verified, treat every production release with a migration as
a one-way step.

## 8. Not configured yet

| Area                         | State                                                                                                                                                                                                | Source                                                      | Owner action                                                                                                                           |
| ---------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| Backups                      | `backend/scripts/weekly_backup.py` exists. No schedule, passphrase file, destination or off-site copy is recorded in the repository. The restore drill has not been run against a production backup. | Repo: `BACKUP-RESTORE.md`. Not in `blocker.txt`             | Choose the backup destination and retention. Create the root-only passphrase file. Schedule the job. Run and record one restore drill. |
| Email delivery               | `SMTP_*` not set on the server. Without `SMTP_HOST`, sign-in codes are logged as not sent, so users cannot sign in.                                                                                  | Owner (`blocker.txt` item 1). Repo: `config_registry.py`    | Create `noreply@oraone.in` in Hostinger email. Add the `SMTP_*` settings to `backend/.env`. Restart `backend` and `workers`.           |
| GitHub deploy workflow       | No workflow deploys to the server. `test-suites.yml` runs on pushes to `main`, pull requests and manually, and does not deploy.                                                                      | Repo: `.github/workflows/`. Planned in `blocker.txt` item 5 | Create the private repository and the deploy secrets. Approve the workflow before it is merged.                                        |
| Monitoring and alerts        | No uptime check, alert or log shipping is defined in the repository.                                                                                                                                 | Repo (no configuration found). Owner to confirm             | Choose an uptime monitor for `https://oraone.in/api/health/ready`, and decide who is alerted.                                          |
| Caddy access logs            | Off. The `Caddyfile` does not enable access logging.                                                                                                                                                 | Repo: `Caddyfile`                                           | Decide whether logs are needed. If they are, keep them private and set a retention period.                                             |
| Upload directory ownership   | The backend Dockerfile does not create `/var/lib/oraone/uploads`. A new named volume may be owned by root. Not checked on the running stack.                                                         | Repo: `DEPLOYMENT.md`                                       | Run the check in section 9 before users upload documents.                                                                              |
| Provider webhooks and keys   | Twilio, Meta, ElevenLabs, Google and other provider settings are not set on the server. Each depends on an account owned by the user.                                                                | Owner (`blocker.txt` items 2 to 4 and 6)                    | Follow the owner items in `blocker.txt`.                                                                                               |
| First platform administrator | Not granted. The first sign-in must come from the owner's own email address.                                                                                                                         | Owner (`blocker.txt` item 8)                                | Sign in once, then tell the engineering team the address.                                                                              |
| Billing                      | Off. `ORAONE_FREE_ACCESS_ONLY` is `true` in production.                                                                                                                                              | Owner (`blocker.txt` item 9). Repo: `billing_service.py`    | Keep it on until pricing is ready.                                                                                                     |

## 9. Verify after a deploy

Replace `oraone.in` if the domain changes. These commands are read-only.

```bash
# DNS
dig +short A oraone.in
dig +short CAA oraone.in
dig +short DNSKEY oraone.in                        # DNSSEC: at least one DNSKEY is returned
dig +short DS oraone.in                            # DS record published at the parent zone

# Application health (through Caddy)
curl -fsS https://oraone.in/api/health
curl -fsS https://oraone.in/api/health/ready

# Containers
cd /opt/oraone
docker compose --env-file .env.production -f docker-compose.prod.yml ps
docker compose --env-file .env.production -f docker-compose.prod.yml logs --tail=100 backend workers

# Settings that must hold in production
docker compose --env-file .env.production -f docker-compose.prod.yml exec backend sh -c 'echo "$ENVIRONMENT"'   # expect: production
docker compose --env-file .env.production -f docker-compose.prod.yml exec backend ls -ld /var/lib/oraone/uploads  # expect UID 1000

# Host hardening (on the server)
sudo ufw status verbose
sudo fail2ban-client status sshd
sudo sshd -T | grep -E 'passwordauthentication|permitrootlogin'   # expect: passwordauthentication no
```

Do not paste the output of `docker compose config` or `env` into a ticket or chat. The commands above
print only the values they name.

After the first deploy, record which `Content-Security-Policy` header a browser receives for
`https://oraone.in/` and for `https://oraone.in/api/health`. `Caddyfile` sets one policy for the
web application, and `backend/server.py` sets a stricter one for JSON responses. The repository does
not show which one is returned for each path on the running stack. Record the answer in
[SECURITY](operations/SECURITY.md).

## 10. Facts this page could not verify from the repository

- Mumbai region, Ubuntu 26.04, the VPS plan and its IP address.
- The DNS records in section 2 as they exist in Hostinger, the CAA contents, DNSSEC and the registrar lock.
- Firewall rules, fail2ban, SSH configuration and the deploy account.
- The `/opt/oraone` directory contents, file permissions and the git checkout on the server.
- Whether the server has security updates enabled.
- Whether `oraone_uploads` is owned by UID 1000 on the running stack.
- Any monitoring, backup or log shipping on the server.

## Related

- [DEPLOYMENT](operations/DEPLOYMENT.md): the generic Compose deployment steps and startup checks
- [CONFIGURATION](operations/CONFIGURATION.md): every environment setting
- [BACKUP-RESTORE](operations/BACKUP-RESTORE.md): backup plan and restore drill
- [RUNBOOK](operations/RUNBOOK.md): common problems and fixes
- [RELEASE-CHECKLIST](operations/RELEASE-CHECKLIST.md): gates before routing live traffic
- [SECURITY](operations/SECURITY.md): controls in the code and accepted risks
