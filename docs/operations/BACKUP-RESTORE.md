# Backup and restore

Production backup evidence is an external release gate.

## Weekly production backup plan

Run `backend/scripts/weekly_backup.py` from a locked-down weekly systemd timer
or cron job on the VPS. Set `DB_NAME`, `DB_PASSWORD`,
`ORAONE_BACKUP_DIR` to a directory outside `/srv/apps/oraone`, and
`ORAONE_BACKUP_PASSPHRASE_FILE` to a root-readable file outside the checkout.
The script creates a `pg_dump` custom-format backup encrypted with GPG AES-256
and mode `0600`. Keep at least four weekly copies on separate encrypted
storage, and monitor the job for failures.

Weekly backup is not a replica: a replica improves recovery time but does not
replace independent backups. Add a managed PostgreSQL replica only after its
cost, retention, failover, and provider support are approved.

Example scheduler command:

```text
DB_NAME=oraone DB_PASSWORD='set-outside-git' \
ORAONE_BACKUP_DIR=/var/backups/oraone \
ORAONE_BACKUP_PASSPHRASE_FILE=/etc/oraone/backup.pass \
python3 /srv/apps/oraone/backend/scripts/weekly_backup.py
```

After each backup, restore one copy into a disposable PostgreSQL instance and
run `backend/scripts/backup_restore_drill.py`. Never store the passphrase in
GitHub Actions logs, the repository, or the application `.env` file.

1. Identify the intended database host and name using a read-only check.
2. Create an encrypted pg_dump outside the application checkout.
3. Restore into a disposable PostgreSQL instance.
4. Run backend/scripts/backup_restore_drill.py against the disposable restore.
5. Verify Alembic revision, critical row counts, email-code mappings, and vector extension.
6. Record timestamp, encryption location, restore duration, and operator.
7. Document retention and ownership.

Do not run alembic upgrade head against production until backup and target identity are independently verified. This checkout contains tooling and instructions, not a production backup result.

## Release and recovery workflow

<!-- diagram: docs/diagrams/release-recovery.mmd -->

```mermaid
flowchart TD
  Source[Verified source revision] --> Gates[Validation gates]
  Gates --> Backup[Verified backup]
  Backup --> Config[Compose configuration check]
  Config --> Migration[Reviewed migration]
  Migration --> Deploy[Controlled deployment]
  Deploy --> Smoke[Health and smoke tests]
  Smoke --> Decision{GO or NO-GO}
  Decision -->|GO| Observe[Monitor and record evidence]
  Decision -->|NO-GO| Rollback[Restore prior image or reviewed schema rollback]
  Rollback --> Verify[Verify recovery]
  Verify --> Observe
```

## Drill evidence

Dated results. Each entry says what was run and what it does not prove.

- **2026-10-18, scratch database (not production).** A throwaway pgvector/pg16 container
  was seeded with two tables and a foreign key (500 and 5,000 rows). It was dumped with
  `pg_dump -Fc` and restored into a second database with `pg_restore`. Row counts,
  an MD5 checksum over the message bodies and the foreign key all matched.
  This proves the dump and restore tooling works on this pg major version.
  It does **not** prove the production backup, its schedule, its passphrase handling,
  or a restore of the real schema. Those remain open until the scheduled drill runs
  against the production backup (see the owner blocker list).
- **Migration rollback is not proven.** The migration chain has one head (0061). No
  down-migration has been exercised against a restored database, so a release that
  includes a migration can only be rolled back by restoring a backup.
