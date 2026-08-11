#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
source "$SCRIPT_DIR/Common.zsh"

root="${INTERNAL_EXAM_ROOT:-${HOME:?}/Library/Application Support/InternalExam}"
while (( $# > 0 )); do
  case "$1" in
    --root) (( $# >= 2 )) || macos_die "--root requires a path"; root="$2"; shift 2 ;;
    -h|--help)
      print -r -- "usage: $0 [--root ABSOLUTE_ROOT]"
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

macos_log "initialized root=$MACOS_LAYOUT_ROOT"
macos_log "configuration=$MACOS_LAYOUT_CONFIGURATION"
macos_log "lifecycle_dir=$MACOS_LAYOUT_LIFECYCLE"
macos_log "release_dir=$MACOS_LAYOUT_RELEASES"
macos_log "backup_dir=$MACOS_LAYOUT_BACKUPS"
macos_log "evidence_dir=$MACOS_LAYOUT_EVIDENCE"
macos_log "diagnostics_dir=$MACOS_LAYOUT_DIAGNOSTICS"
macos_log "state_dir=$MACOS_LAYOUT_STATE"
