#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
source "$SCRIPT_DIR/Common.zsh"

state=""
confirmation=""
root="${INTERNAL_EXAM_ROOT:-${HOME:?}/Library/Application Support/InternalExam}"
while (( $# > 0 )); do
  case "$1" in
    --state) (( $# >= 2 )) || macos_die "--state requires Enabled or Disabled"; state="$2"; shift 2 ;;
    --confirmation) (( $# >= 2 )) || macos_die "--confirmation requires exact text"; confirmation="$2"; shift 2 ;;
    --root) (( $# >= 2 )) || macos_die "--root requires a path"; root="$2"; shift 2 ;;
    -h|--help) print -r -- "usage: $0 --state Enabled|Disabled --confirmation TEXT [--root ROOT]"; exit 0 ;;
    *) macos_die "unknown argument: $1"; exit 1 ;;
  esac
done

macos_assert_macos
[[ "$state" == Enabled || "$state" == Disabled ]] || macos_die "invalid backup operator state"
expected_confirmation="ENABLE BACKUP OPERATOR"
[[ "$state" == Disabled ]] && expected_confirmation="DISABLE BACKUP OPERATOR"
[[ "$confirmation" == "$expected_confirmation" ]] || macos_die "exact backup-operator confirmation did not match"
macos_assert_outside_worktree "$root" >/dev/null
macos_layout "$root"
macos_assert_protected_configuration "$root"
macos_docker_ready
macos_acquire_lock "$MACOS_LAYOUT_STATE/.operation.lock"
trap macos_release_lock EXIT
macos_release_state "$MACOS_CURRENT_STATE"
release_path="$MACOS_STATE_PATH"
release_version="$MACOS_STATE_VERSION"
release_commit="$MACOS_STATE_COMMIT"
"$SCRIPT_DIR/Test-ReleaseBundle.zsh" --release-path "$release_path" >/dev/null
macos_verify_built_image_identity "$release_path"
primary_operator="$(macos_formal_value PRIMARY_OPERATOR_USERNAME)"
primary_password="$(macos_formal_value PRIMARY_OPERATOR_PASSWORD)"
backup_operator="$(macos_formal_value BACKUP_OPERATOR_USERNAME)"
backup_password="$(macos_formal_value BACKUP_OPERATOR_PASSWORD)"
old_value="$(macos_formal_value BACKUP_OPERATOR_ENABLED)"
operator_subject="$(macos_active_operator_subject)"
new_value=false
[[ "$state" == Enabled ]] && new_value=true
operator_status=failed
config_changed=0
audit_committed=0

macos_save_environment APP_VERSION_TAG APP_VERSION GIT_COMMIT
cleanup_operator() {
  if [[ "$operator_status" != passed && "$config_changed" == 1 && "$audit_committed" == 0 ]]; then
    macos_dotenv_set_atomic "$MACOS_FORMAL_ENV" BACKUP_OPERATOR_ENABLED "$old_value" || true
    macos_compose "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" up -d --no-deps --no-build --force-recreate backend >/dev/null 2>&1 || true
  fi
  [[ -z "${login_body_file:-}" ]] || rm -f -- "$login_body_file"
  [[ -z "${primary_login_body_file:-}" ]] || rm -f -- "$primary_login_body_file"
  [[ -z "${login_response:-}" ]] || rm -f -- "$login_response"
  macos_restore_environment
  macos_release_lock
}
trap cleanup_operator EXIT
export APP_VERSION_TAG="${release_commit:l}"
export APP_VERSION="$release_version"
export GIT_COMMIT="${release_commit:l}"
macos_compose_base "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT"
macos_assert_writer_fence_clear "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT"

macos_dotenv_set_atomic "$MACOS_FORMAL_ENV" BACKUP_OPERATOR_ENABLED "$new_value"
config_changed=1
if ! macos_compose "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" \
  up -d --no-deps --no-build --force-recreate backend; then
  macos_dotenv_set_atomic "$MACOS_FORMAL_ENV" BACKUP_OPERATOR_ENABLED "$old_value" || true
  macos_compose "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" \
    up -d --no-deps --no-build --force-recreate backend || true
  config_changed=0
  macos_die "backend recreation failed; backup operator configuration was restored"
fi

macos_require_command curl
login_body="{\"username\":\"$(macos_json_escape "$backup_operator")\",\"password\":\"$(macos_json_escape "$backup_password")\"}"
login_body_file="$(macos_mktemp internal-exam-backup-login-body.XXXXXX)"
primary_login_body_file=""
cleanup_login_body() { rm -f -- "$login_body_file"; [[ -z "${primary_login_body_file:-}" ]] || rm -f -- "$primary_login_body_file"; }
macos_write_atomic "$login_body_file" "$login_body"
primary_login_body="{\"username\":\"$(macos_json_escape "$primary_operator")\",\"password\":\"$(macos_json_escape "$primary_password")\"}"
primary_login_body_file="$(macos_mktemp internal-exam-primary-login-body.XXXXXX)"
macos_write_atomic "$primary_login_body_file" "$primary_login_body"
login_response="$(macos_mktemp internal-exam-login.XXXXXX)"
chmod 600 "$login_response"
if [[ "$state" == Enabled ]]; then
  http_code="$(curl -sS -o "$login_response" -w '%{http_code}' --connect-timeout 5 --max-time 10 \
    -H 'Content-Type: application/json' --data-binary "@$login_body_file" http://127.0.0.1:8081/api/admin/login)"
  [[ "$http_code" == 2* ]] || { rm -f -- "$login_response"; macos_die "enabled backup operator could not authenticate"; }
  plutil -extract data.token raw -o - -- "$login_response" >/dev/null 2>&1 || { rm -f -- "$login_response"; macos_die "enabled backup operator token was not issued"; }
  http_code="$(curl -sS -o "$login_response" -w '%{http_code}' --connect-timeout 5 --max-time 10 \
    -H 'Content-Type: application/json' --data-binary "@$primary_login_body_file" http://127.0.0.1:8081/api/admin/login || true)"
  [[ "$http_code" == 401 ]] || { rm -f -- "$login_response"; macos_die "primary operator remained active after backup enablement"; }
else
  http_code="$(curl -sS -o "$login_response" -w '%{http_code}' --connect-timeout 5 --max-time 10 \
    -H 'Content-Type: application/json' --data-binary "@$login_body_file" http://127.0.0.1:8081/api/admin/login || true)"
  [[ "$http_code" == 401 ]] || { rm -f -- "$login_response"; macos_die "disabled backup operator unexpectedly authenticated"; }
  http_code="$(curl -sS -o "$login_response" -w '%{http_code}' --connect-timeout 5 --max-time 10 \
    -H 'Content-Type: application/json' --data-binary "@$primary_login_body_file" http://127.0.0.1:8081/api/admin/login)"
  [[ "$http_code" == 2* ]] || { rm -f -- "$login_response"; macos_die "primary operator did not recover after backup disablement"; }
fi
rm -f -- "$login_response"

macos_compose_base "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT"
macos_run_checked docker "${MACOS_COMPOSE_ARGS[@]}" run --rm --no-deps backend \
  uv run --no-sync python -m app.ops.operator_control record-backup-operator \
  --operator-subject "$operator_subject" --target "$backup_operator" --enabled "$new_value"
audit_committed=1
macos_write_evidence "$MACOS_LAYOUT_EVIDENCE" backup-operator \
  "{\"schemaVersion\":1,\"kind\":\"backup-operator\",\"status\":\"passed\",\"enabled\":$new_value,\"target\":\"$(macos_json_escape "$backup_operator")\",\"secrets\":\"excluded\"}" >/dev/null
macos_log "backup_operator_enabled=$new_value backend_recreated=true"
operator_status=passed
