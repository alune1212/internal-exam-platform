#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
source "$SCRIPT_DIR/Common.zsh"

confirmation=""
root="${INTERNAL_EXAM_ROOT:-${HOME:?}/Library/Application Support/InternalExam}"
while (( $# > 0 )); do
  case "$1" in
    --confirmation) (( $# >= 2 )) || macos_die "--confirmation requires exact text"; confirmation="$2"; shift 2 ;;
    --root) (( $# >= 2 )) || macos_die "--root requires a path"; root="$2"; shift 2 ;;
    -h|--help) print -r -- "usage: $0 --confirmation 'CLOSE ALL SESSIONS' [--root ROOT]"; exit 0 ;;
    *) macos_die "unknown argument: $1"; exit 1 ;;
  esac
done

macos_assert_macos
[[ "$confirmation" == 'CLOSE ALL SESSIONS' ]] || macos_die "exact close-exam confirmation did not match"
macos_assert_outside_worktree "$root" >/dev/null
macos_layout "$root"
macos_assert_protected_configuration "$root"
macos_docker_ready
macos_acquire_lock "$MACOS_LAYOUT_STATE/.operation.lock"
freeze_owner="session-closure-$$"
freeze_acquired=0
cleanup_closure_lock() {
  if (( freeze_acquired == 1 )); then
    macos_operational_lock_one_shot "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" release-backup --owner "$freeze_owner" >/dev/null 2>&1 || true
    freeze_acquired=0
  fi
  macos_release_lock
}
trap cleanup_closure_lock EXIT
macos_release_state "$MACOS_CURRENT_STATE"
release_path="$MACOS_STATE_PATH"
release_version="$MACOS_STATE_VERSION"
release_commit="$MACOS_STATE_COMMIT"
"$SCRIPT_DIR/Test-ReleaseBundle.zsh" --release-path "$release_path" >/dev/null
macos_verify_built_image_identity "$release_path"
primary_operator="$(macos_active_operator_subject)"
primary_password="$(macos_active_operator_password)"
old_secret="$(macos_formal_value TOKEN_SECRET)"
admin_header_file=""

macos_require_command curl
login_body="{\"username\":\"$(macos_json_escape "$primary_operator")\",\"password\":\"$(macos_json_escape "$primary_password")\"}"
login_body_file="$(macos_mktemp internal-exam-close-login-body.XXXXXX)"
macos_write_atomic "$login_body_file" "$login_body"
cleanup_login_body() { rm -f -- "$login_body_file"; [[ -z "${admin_header_file:-}" ]] || rm -f -- "$admin_header_file"; }
login_response="$(macos_mktemp internal-exam-close-login.XXXXXX)"
chmod 600 "$login_response"
http_code="$(curl -sS -o "$login_response" -w '%{http_code}' --connect-timeout 5 --max-time 10 \
  -H 'Content-Type: application/json' --data-binary "@$login_body_file" http://127.0.0.1:8081/api/admin/login)"
[[ "$http_code" == 2* ]] || { rm -f -- "$login_response"; macos_die "primary operator authentication failed"; }
old_token="$(plutil -extract data.token raw -o - -- "$login_response" 2>/dev/null || true)"
rm -f -- "$login_response"
[[ -n "$old_token" ]] || macos_die "primary operator token was not issued"
macos_operational_lock_one_shot "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" acquire-backup --owner "$freeze_owner" --ttl-seconds 1800 >/dev/null
freeze_acquired=1
admin_header_file="$(macos_mktemp internal-exam-close-admin-header.XXXXXX)"
chmod 600 "$admin_header_file"
print -r -- "header = \"X-Admin-Token: $old_token\"" > "$admin_header_file"

# Readiness and the container-side gate happen before changing TOKEN_SECRET.
readiness_file="$(macos_mktemp internal-exam-close-readiness.XXXXXX)"
chmod 600 "$readiness_file"
http_code="$(curl -sS -o "$readiness_file" -w '%{http_code}' --connect-timeout 5 --max-time 10 \
  --config "$admin_header_file" http://127.0.0.1:8081/api/admin/operations/session-closure-readiness)"
[[ "$http_code" == 2* ]] || { rm -f -- "$readiness_file"; macos_die "session closure readiness request failed"; }
ready="$(plutil -extract data.ready raw -o - -- "$readiness_file" 2>/dev/null || true)"
in_progress="$(plutil -extract data.in_progress_attempt_count raw -o - -- "$readiness_file" 2>/dev/null || true)"
rm -f -- "$readiness_file"
[[ "$ready" == true && "$in_progress" == 0 ]] || macos_die "session closure refused while an attempt is in progress"
macos_compose_base "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT"
macos_run_checked docker "${MACOS_COMPOSE_ARGS[@]}" run --rm --no-deps backend \
  uv run --no-sync python -m app.ops.operator_control check-session-closure

macos_require_command openssl
new_secret="$(openssl rand -base64 48 | tr -d '\n')"
[[ -n "$new_secret" ]] || macos_die "unable to generate session secret"
macos_dotenv_set_atomic "$MACOS_FORMAL_ENV" TOKEN_SECRET "$new_secret"
macos_save_environment APP_VERSION_TAG APP_VERSION GIT_COMMIT
session_closed=0
cleanup_session_closure() {
  if (( session_closed == 0 )); then
    macos_dotenv_set_atomic "$MACOS_FORMAL_ENV" TOKEN_SECRET "$old_secret" || true
    macos_compose "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" \
      up -d --no-deps --no-build --force-recreate backend || true
  fi
  cleanup_login_body
  macos_restore_environment
  cleanup_closure_lock
}
trap cleanup_session_closure EXIT
export APP_VERSION_TAG="${release_commit:l}"
export APP_VERSION="$release_version"
export GIT_COMMIT="${release_commit:l}"
if ! macos_compose "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" \
  up -d --no-deps --no-build --force-recreate backend; then
  macos_dotenv_set_atomic "$MACOS_FORMAL_ENV" TOKEN_SECRET "$old_secret" || true
  macos_compose "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" \
    up -d --no-deps --no-build --force-recreate backend || true
  macos_die "backend recreation failed; TOKEN_SECRET was restored"
fi

ready_after=0
for (( attempt = 1; attempt <= 30; attempt += 1 )); do
  status_code="$(curl -sS -o /dev/null -w '%{http_code}' --connect-timeout 2 --max-time 3 \
    http://127.0.0.1:8081/api/ready || true)"
  if [[ "$status_code" == 200 ]]; then ready_after=1; break; fi
  sleep 2
done
(( ready_after == 1 )) || macos_die "backend readiness did not recover after session closure"

old_status="$(curl -sS -o /dev/null -w '%{http_code}' --connect-timeout 5 --max-time 10 \
  --config "$admin_header_file" http://127.0.0.1:8081/api/admin/exams || true)"
[[ "$old_status" == 401 ]] || macos_die "a token issued before session closure was still accepted"
# This is the irreversible security boundary.  From this point onward a
# later evidence/audit failure must not restore TOKEN_SECRET and resurrect the
# old token; the operator must keep the new secret and repair evidence.
session_closed=1
macos_operational_lock_one_shot "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" release-backup --owner "$freeze_owner" >/dev/null
freeze_acquired=0
new_login_response="$(macos_mktemp internal-exam-close-new-login.XXXXXX)"
chmod 600 "$new_login_response"
new_status="$(curl -sS -o "$new_login_response" -w '%{http_code}' --connect-timeout 5 --max-time 10 \
  -H 'Content-Type: application/json' --data-binary "@$login_body_file" http://127.0.0.1:8081/api/admin/login)"
new_token="$(plutil -extract data.token raw -o - -- "$new_login_response" 2>/dev/null || true)"
rm -f -- "$new_login_response"
[[ "$new_status" == 2* && -n "$new_token" ]] || macos_die "primary operator could not authenticate after session closure"

macos_compose_base "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT"
macos_run_checked docker "${MACOS_COMPOSE_ARGS[@]}" run --rm --no-deps backend \
  uv run --no-sync python -m app.ops.operator_control record-session-closure \
  --operator-subject "$primary_operator"
macos_write_evidence "$MACOS_LAYOUT_EVIDENCE" session-closure \
  "{\"schemaVersion\":1,\"kind\":\"session-closure\",\"status\":\"passed\",\"inProgressAttempts\":0,\"oldTokensRejected\":true,\"readinessRecovered\":true,\"secrets\":\"excluded\"}" >/dev/null
macos_log "all_sessions_closed old_tokens_rejected=true readiness=ready"
