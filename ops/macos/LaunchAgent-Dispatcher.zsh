#!/bin/zsh
set -euo pipefail
umask 077

SCRIPT_DIR="${0:A:h}"
source "$SCRIPT_DIR/Common.zsh"

action="${1:-}"
shift || true
root="${INTERNAL_EXAM_ROOT:-${HOME:?}/Library/Application Support/InternalExam}"
while (( $# > 0 )); do
  case "$1" in
    --root) (( $# >= 2 )) || macos_die "--root requires a path"; root="$2"; shift 2 ;;
    *) macos_die "unknown dispatcher argument: $1"; exit 1 ;;
  esac
done

macos_assert_macos
[[ "$action" == bootstrap || "$action" == opportunistic-backup ]] || macos_die "unsupported LaunchAgent action"
macos_assert_outside_worktree "$root" >/dev/null
macos_assert_protected_configuration "$root"
mkdir -p -- "$MACOS_LAYOUT_DIAGNOSTICS" "$MACOS_LAYOUT_STATE"
chmod 700 "$MACOS_LAYOUT_DIAGNOSTICS" "$MACOS_LAYOUT_STATE"
log_file="$MACOS_LAYOUT_DIAGNOSTICS/launchagent-${action}.log"
macos_rotate_log "$log_file" 1048576
exec >> "$log_file" 2>&1
chmod 600 "$log_file"
print -r -- "dispatcher_started action=$action at=$(macos_now_iso)"

lock="$MACOS_LAYOUT_STATE/.launchagent-${action}.lock"
if ! macos_acquire_lock "$lock"; then
  print -r -- "dispatcher_skipped reason=already_running action=$action"
  exit 0
fi
trap macos_release_lock EXIT

# Docker Desktop may take several minutes after login.  Ten minutes is the
# hard upper bound; no retry after timeout is allowed and no exam is approved.
macos_require_command docker
macos_require_command sleep
waited=0
while (( waited < 600 )); do
  if docker info >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    print -r -- "docker_ready waited_seconds=$waited"
    break
  fi
  sleep 5
  (( waited += 5 ))
done
(( waited < 600 )) || { print -r -- "docker_timeout waited_seconds=600 exam_approval=false"; exit 1; }

case "$action" in
  bootstrap)
    # Start-Platform uses the selected state release and --no-build.  It does
    # not promote, restore, rotate sessions, or authorize an exam.
    if ! "$SCRIPT_DIR/Start-Platform.zsh" --root "$root"; then
      print -r -- "bootstrap_failed exam_approval=false"
      exit 1
    fi
    print -r -- "bootstrap_completed recovery=no-build exam_approval=false"
    ;;
  opportunistic-backup)
    if ! "$SCRIPT_DIR/Invoke-PairedBackup.zsh" --root "$root" --kind daily --opportunistic; then
      print -r -- "opportunistic_backup_failed exam_approval=false"
      exit 1
    fi
    print -r -- "opportunistic_backup_completed exam_approval=false"
    ;;
esac
