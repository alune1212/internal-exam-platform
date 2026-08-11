#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
source "$SCRIPT_DIR/Common.zsh"

root="${INTERNAL_EXAM_ROOT:-${HOME:?}/Library/Application Support/InternalExam}"
while (( $# > 0 )); do
  case "$1" in
    --root) (( $# >= 2 )) || macos_die "--root requires a path"; root="$2"; shift 2 ;;
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
macos_assert_project_name formal "$MACOS_FORMAL_PROJECT"
macos_log "active_version=$MACOS_STATE_VERSION commit=${MACOS_STATE_COMMIT:l} project=$MACOS_FORMAL_PROJECT"
macos_compose_capture "$MACOS_STATE_PATH" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" ps
