#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
source "$SCRIPT_DIR/Common.zsh"

root="${INTERNAL_EXAM_ROOT:-${HOME:?}/Library/Application Support/InternalExam}"
lock_held=0
maintenance=0
start_status=failed
while (( $# > 0 )); do
  case "$1" in
    --root) (( $# >= 2 )) || macos_die "--root requires a path"; root="$2"; shift 2 ;;
    --lock-held) lock_held=1; shift ;;
    --maintenance) maintenance=1; shift ;;
    -h|--help) print -r -- "usage: $0 [--root ABSOLUTE_ROOT] [--maintenance] [--lock-held]"; exit 0 ;;
    *) macos_die "unknown argument: $1"; exit 1 ;;
  esac
done

macos_assert_macos
macos_assert_outside_worktree "$root" >/dev/null
macos_layout "$root"
macos_assert_protected_configuration "$root"
macos_require_formal_paths
macos_docker_ready
macos_release_state "$MACOS_CURRENT_STATE"
macos_read_cutover_identity
macos_assert_formal_writer_ready "$maintenance"
state_dataset_id="$(macos_json_get "$MACOS_CURRENT_STATE" datasetId 2>/dev/null || true)"
state_host_id="$(macos_json_get "$MACOS_CURRENT_STATE" hostId 2>/dev/null || true)"
state_writer_generation="$(macos_json_get "$MACOS_CURRENT_STATE" writerGeneration 2>/dev/null || true)"
[[ "$state_dataset_id" == "$MACOS_DATASET_ID" && "$state_host_id" == "$MACOS_HOST_ID" && "$state_writer_generation" == "$MACOS_WRITER_GENERATION" ]] || macos_die "current release identity is not bound to the active host writer generation"
if (( lock_held == 1 )); then
  macos_assert_inherited_lock
else
  macos_acquire_lock "$MACOS_LAYOUT_STATE/.operation.lock"
fi
macos_assert_no_pending_cutover_start "$maintenance"
"$SCRIPT_DIR/Test-ReleaseBundle.zsh" --release-path "$MACOS_STATE_PATH" >/dev/null
macos_verify_built_image_identity "$MACOS_STATE_PATH"
macos_assert_project_name formal "$MACOS_FORMAL_PROJECT"

macos_save_environment APP_VERSION_TAG APP_VERSION GIT_COMMIT \
  INTERNAL_LAN_BIND_IP CANDIDATE_GATEWAY_PORT OPERATOR_GATEWAY_PORT \
  POSTGRES_LOOPBACK_PORT FRONTEND_LOOPBACK_PORT CORS_ORIGINS
cleanup_start() {
  if [[ "$start_status" != passed ]]; then
    macos_compose "$MACOS_STATE_PATH" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" stop >/dev/null 2>&1 || true
    cleanup_running_services="$(macos_compose_capture "$MACOS_STATE_PATH" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" ps --status running -q 2>/dev/null || true)"
    [[ -z "${cleanup_running_services//[[:space:]]/}" ]] || print -u2 -- "macOS operation failed; formal services remain running"
  fi
  macos_restore_environment
  (( lock_held == 1 )) || macos_release_lock
}
trap cleanup_start EXIT
export APP_VERSION_TAG="${MACOS_STATE_COMMIT:l}"
export APP_VERSION="$MACOS_STATE_VERSION"
export GIT_COMMIT="${MACOS_STATE_COMMIT:l}"
if (( maintenance == 1 )); then
  # Cutover validation is private maintenance traffic.  These values are
  # restored by cleanup_start before the operation exits; no public candidate
  # or operator listener is opened while the target is being evaluated.
  export INTERNAL_LAN_BIND_IP=127.0.0.1
  export CANDIDATE_GATEWAY_PORT=28080
  export OPERATOR_GATEWAY_PORT=28081
  export POSTGRES_LOOPBACK_PORT=25432
  export FRONTEND_LOOPBACK_PORT=25173
  export CORS_ORIGINS=http://127.0.0.1:28080
fi
macos_compose "$MACOS_STATE_PATH" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" up -d --no-build db
if (( maintenance == 0 )); then
  if ! macos_assert_writer_fence_clear "$MACOS_STATE_PATH" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT"; then
    macos_compose "$MACOS_STATE_PATH" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" stop >/dev/null 2>&1 || true
    fence_failure_running="$(macos_compose_capture "$MACOS_STATE_PATH" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" ps --status running -q 2>/dev/null || true)"
    [[ -z "${fence_failure_running//[[:space:]]/}" ]] || print -u2 -- "macOS operation failed; formal services remain running after fence rejection"
    macos_die "formal writer fence is active; lifecycle start is fenced"
  fi
fi
macos_compose "$MACOS_STATE_PATH" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" \
  up -d --no-build --remove-orphans
if (( maintenance == 1 )); then
  macos_log "formal_started maintenance=true version=$MACOS_STATE_VERSION commit=${MACOS_STATE_COMMIT:l} recovery=no-build"
else
  macos_log "formal_started version=$MACOS_STATE_VERSION commit=${MACOS_STATE_COMMIT:l} recovery=no-build"
fi
start_status=passed
