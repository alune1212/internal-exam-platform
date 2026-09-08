#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
source "$SCRIPT_DIR/Common.zsh"

root="${INTERNAL_EXAM_ROOT:-${HOME:?}/Library/Application Support/InternalExam}"
sync_staging_env=0
while (( $# > 0 )); do
  case "$1" in
    --root) (( $# >= 2 )) || macos_die "--root requires a path"; root="$2"; shift 2 ;;
    --sync-staging-env) sync_staging_env=1; shift ;;
    -h|--help)
      print -r -- "usage: $0 [--root ABSOLUTE_ROOT] [--sync-staging-env]"
      print -r -- "--sync-staging-env copies the owner-only formal config, then applies fixed disposable staging values; it never prints secrets."
      exit 0
      ;;
    *) macos_die "unknown argument: $1"; exit 1 ;;
  esac
done

macos_assert_macos
macos_initialize_layout "$root"

# Keep Compose's writable host binds and the adapter's evidence paths on one
# canonical layout.  An existing non-canonical value is rejected rather than
# silently copied or split across another runtime tree.  The encrypted
# second-copy default is intentionally outside this root and is still gated by
# its live marker/mount at every operation.
ensure_canonical_path() {
  local name="$1" expected="$2" existing
  existing="$(macos_dotenv_get "$MACOS_FORMAL_ENV" "$name" 2>/dev/null || true)"
  if [[ -z "$existing" ]]; then
    print -r -- "$name=$expected" >> "$MACOS_FORMAL_ENV"
    chmod 600 "$MACOS_FORMAL_ENV"
  else
    [[ "$existing" == "$expected" ]] || macos_die "$name must use the canonical formal host path"
  fi
}
ensure_canonical_path INTERNAL_EXAM_LIFECYCLE_HOST_DIR "$MACOS_LAYOUT_LIFECYCLE"
ensure_canonical_path INTERNAL_EXAM_BACKUP_HOST_DIR "$MACOS_LAYOUT_BACKUPS"
ensure_canonical_path INTERNAL_EXAM_EVIDENCE_HOST_DIR "$MACOS_LAYOUT_EVIDENCE"
second_copy_existing="$(macos_dotenv_get "$MACOS_FORMAL_ENV" SECOND_COPY_PATH 2>/dev/null || true)"
if [[ -z "$second_copy_existing" ]]; then
  print -r -- "SECOND_COPY_PATH=/Volumes/InternalExamSecondCopy" >> "$MACOS_FORMAL_ENV"
  chmod 600 "$MACOS_FORMAL_ENV"
fi

set_staging_value() {
  local name="$1" value="$2"
  if macos_dotenv_get "$MACOS_STAGING_ENV" "$name" >/dev/null 2>&1; then
    macos_dotenv_set_atomic "$MACOS_STAGING_ENV" "$name" "$value"
  else
    print -r -- "$name=$value" >> "$MACOS_STAGING_ENV"
    chmod 600 "$MACOS_STAGING_ENV"
  fi
}

if (( sync_staging_env == 1 )); then
  [[ -s "$MACOS_FORMAL_ENV" ]] || macos_die "formal.env must be populated before staging sync"
  [[ ! -L "$MACOS_FORMAL_ENV" && ! -L "$MACOS_STAGING_ENV" ]] || macos_die "formal/staging environment files must not be symlinks"
  macos_assert_dotenv_canonical "$MACOS_FORMAL_ENV"
  macos_assert_dotenv_canonical "$MACOS_STAGING_ENV"
  temporary="$(mktemp "${MACOS_STAGING_ENV}.tmp.XXXXXX")"
  chmod 600 "$temporary"
  cp -p -- "$MACOS_FORMAL_ENV" "$temporary"
  mv -f -- "$temporary" "$MACOS_STAGING_ENV"
  chmod 600 "$MACOS_STAGING_ENV"

  formal_token_secret="$(macos_dotenv_get "$MACOS_FORMAL_ENV" TOKEN_SECRET 2>/dev/null || true)"
  [[ -n "$formal_token_secret" ]] || macos_die "formal TOKEN_SECRET must be populated before staging sync"
  [[ "$formal_token_secret" =~ '^[A-Za-z0-9_-]{43}$' ]] || macos_die "formal TOKEN_SECRET must be canonical before staging sync"
  macos_require_command openssl
  staging_token_secret=""
  for secret_attempt in {1..3}; do
    staging_token_secret="$(openssl rand -base64 32 | tr '+/' '-_' | tr -d '=[:space:]')" || macos_die "unable to generate staging TOKEN_SECRET"
    [[ "$staging_token_secret" =~ '^[A-Za-z0-9_-]{43}$' ]] || continue
    [[ "$staging_token_secret" != "$formal_token_secret" ]] && break
    staging_token_secret=""
  done
  [[ "$staging_token_secret" =~ '^[A-Za-z0-9_-]{43}$' && "$staging_token_secret" != "$formal_token_secret" ]] || macos_die "unable to generate an independent staging TOKEN_SECRET"

  # Keep the disposable runtime explicit and loopback-only.  Credentials and
  # SMTP settings remain copied from formal.env without ever entering output.
  set_staging_value TOKEN_SECRET "$staging_token_secret"
  set_staging_value ENVIRONMENT development
  set_staging_value ACCOUNT_MIGRATION_ALLOW_UNGATED_DEVELOPMENT true
  set_staging_value ACCOUNT_MIGRATION_DISPOSABLE_DATABASE true
  set_staging_value CANDIDATE_LOGIN_TEST_OTP ""
  set_staging_value CANDIDATE_LOGIN_EMAIL_DELIVERY_MODE smtp
  set_staging_value CORS_ORIGINS "http://127.0.0.1:${MACOS_STAGE_PORT_CANDIDATE}"
  set_staging_value CANDIDATE_PUBLIC_BASE_URL "http://127.0.0.1:${MACOS_STAGE_PORT_CANDIDATE}"
  set_staging_value INTERNAL_LAN_BIND_IP 127.0.0.1
  set_staging_value CANDIDATE_GATEWAY_PORT "$MACOS_STAGE_PORT_CANDIDATE"
  set_staging_value OPERATOR_GATEWAY_PORT "$MACOS_STAGE_PORT_OPERATOR"
  set_staging_value POSTGRES_LOOPBACK_PORT "$MACOS_STAGE_PORT_DATABASE"
  set_staging_value FRONTEND_LOOPBACK_PORT "$MACOS_STAGE_PORT_FRONTEND"
  set_staging_value GATEWAY_SUBNET 172.31.0.0/24
  set_staging_value GATEWAY_IP_RANGE 172.31.0.128/25
  set_staging_value CANDIDATE_GATEWAY_IP 172.31.0.2
  set_staging_value OPERATOR_GATEWAY_IP 172.31.0.3
  macos_assert_staging_env "$MACOS_STAGING_ENV"
fi

macos_log "initialized root=$MACOS_LAYOUT_ROOT"
macos_log "configuration=$MACOS_LAYOUT_CONFIGURATION"
macos_log "lifecycle_dir=$MACOS_LAYOUT_LIFECYCLE"
macos_log "release_dir=$MACOS_LAYOUT_RELEASES"
macos_log "backup_dir=$MACOS_LAYOUT_BACKUPS"
macos_log "evidence_dir=$MACOS_LAYOUT_EVIDENCE"
macos_log "diagnostics_dir=$MACOS_LAYOUT_DIAGNOSTICS"
macos_log "state_dir=$MACOS_LAYOUT_STATE"
if (( sync_staging_env == 1 )); then
  macos_log "staging_env=$MACOS_STAGING_ENV"
fi
