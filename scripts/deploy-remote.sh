#!/usr/bin/env bash
# Production host side of .github/workflows/deploy.yml. Runs over ssh with the script on stdin:
#   ssh <host> "bash -s -- deploy"   < scripts/deploy-remote.sh
#   ssh <host> "bash -s -- rollback" < scripts/deploy-remote.sh
#
# Layout on the host:
#   /opt/oraone            live copy (docker compose runs from here)
#   /opt/oraone-new        staged copy, extracted from the uploaded git archive
#   /opt/oraone-prev       previous live copy, kept for rollback
#   /opt/oraone-failed     a copy that was rolled back, kept for inspection
#
# The .env files are copied from the live copy into the staged copy. Their contents are never
# printed. Nothing here echoes environment values.

set -euo pipefail

MODE="${1:-}"
LIVE=/opt/oraone
NEW=/opt/oraone-new
PREV=/opt/oraone-prev
FAILED=/opt/oraone-failed
ARCHIVE=/tmp/oraone-release.tar.gz
SWAPPED=0

log() {
  echo "[deploy-remote] $*"
}

compose_up() {
  (cd "$1" && docker compose --env-file .env -f docker-compose.prod.yml up -d --build)
}

rollback() {
  if [ ! -d "$PREV" ]; then
    log "no previous copy at $PREV; nothing to roll back to"
    return 1
  fi
  log "rolling back to the previous copy"
  rm -rf "$FAILED"
  if [ -d "$LIVE" ]; then
    mv "$LIVE" "$FAILED"
  fi
  mv "$PREV" "$LIVE"
  compose_up "$LIVE"
  log "rollback complete"
}

on_error() {
  local status=$?
  log "deploy step failed (exit $status)"
  if [ "$SWAPPED" = "1" ]; then
    rollback || log "rollback also failed; inspect $LIVE and $FAILED on the host"
  fi
  exit "$status"
}

deploy() {
  if [ ! -f "$ARCHIVE" ]; then
    log "release archive $ARCHIVE is missing"
    exit 1
  fi
  if [ ! -f "$LIVE/.env" ] || [ ! -f "$LIVE/backend/.env" ]; then
    log "live .env files are missing; refusing to deploy without them"
    exit 1
  fi

  rm -rf "$NEW"
  mkdir -p "$NEW"
  tar -xzf "$ARCHIVE" -C "$NEW"
  rm -f "$ARCHIVE"

  install -m 600 "$LIVE/.env" "$NEW/.env"
  install -m 600 "$LIVE/backend/.env" "$NEW/backend/.env"

  trap on_error ERR

  rm -rf "$PREV"
  mv "$LIVE" "$PREV"
  mv "$NEW" "$LIVE"
  SWAPPED=1
  log "swapped in the new copy; starting the stack"

  compose_up "$LIVE"
  trap - ERR
  log "stack started; waiting for readiness on the runner"
}

case "$MODE" in
  deploy)
    deploy
    ;;
  rollback)
    rollback
    ;;
  *)
    echo "usage: deploy-remote.sh deploy|rollback" >&2
    exit 2
    ;;
esac
