#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
source "$SCRIPT_DIR/Common.zsh"

root="${INTERNAL_EXAM_ROOT:-${HOME:?}/Library/Application Support/InternalExam}"
lock_held=0
while (( $# > 0 )); do
  case "$1" in
    --root) (( $# >= 2 )) || macos_die "--root requires a path"; root="$2"; shift 2 ;;
    --lock-held) lock_held=1; shift ;;
    -h|--help) print -r -- "usage: $0 [--root ABSOLUTE_ROOT]"; exit 0 ;;
    *) macos_die "unknown argument: $1"; exit 1 ;;
  esac
done

macos_assert_macos
macos_assert_outside_worktree "$root" >/dev/null
macos_layout "$root"
macos_assert_protected_configuration "$root"
macos_docker_ready
macos_release_state "$MACOS_CURRENT_STATE"
if (( lock_held == 1 )); then
  macos_assert_inherited_lock
else
  macos_acquire_lock "$MACOS_LAYOUT_STATE/.operation.lock"
  trap macos_release_lock EXIT
fi
macos_assert_project_name formal "$MACOS_FORMAL_PROJECT"
# Stop is deliberately not `down` and never removes formal volumes.
macos_compose "$MACOS_STATE_PATH" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" stop
macos_log "formal_stopped version=$MACOS_STATE_VERSION"
