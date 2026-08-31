#!/bin/zsh
set -euo pipefail
umask 077

SCRIPT_DIR="${0:A:h}"

# Direct invocations are routed through the standalone launcher before this
# dispatcher sources any runtime support.  LaunchAgent plists point at that
# launcher, while this fallback keeps the dispatcher fail-closed when called
# manually or from an older installed release.
if [[ "${INTERNAL_EXAM_TRUSTED_RUNTIME_DIR:-}" != "$SCRIPT_DIR" || "${INTERNAL_EXAM_TRUSTED_RELEASE_VERIFIED:-}" != 1 ]]; then
  trusted_launcher="$SCRIPT_DIR/Trusted-LaunchAgent.zsh"
  [[ -f "$trusted_launcher" && ! -L "$trusted_launcher" && -x "$trusted_launcher" ]] || {
    print -u2 -- "trusted macOS LaunchAgent failed: dispatcher requires Trusted-LaunchAgent.zsh"
    exit 1
  }
  exec "$trusted_launcher" "$@"
fi
source "$SCRIPT_DIR/Common.zsh"

action="${1:-}"
shift || true
root="${INTERNAL_EXAM_ROOT:-${HOME:?}/Library/Application Support/InternalExam}"
release_path=""
while (( $# > 0 )); do
  case "$1" in
    --root) (( $# >= 2 )) || macos_die "--root requires a path"; root="$2"; shift 2 ;;
    --release-path) (( $# >= 2 )) || macos_die "--release-path requires a path"; release_path="$2"; shift 2 ;;
    *) macos_die "unknown dispatcher argument: $1"; exit 1 ;;
  esac
done

macos_assert_macos
[[ "$action" == bootstrap || "$action" == opportunistic-backup ]] || macos_die "unsupported LaunchAgent action"
[[ -n "$release_path" ]] || macos_die "trusted release path is required"
macos_assert_outside_worktree "$root" >/dev/null
macos_assert_protected_configuration "$root"
macos_layout "$root"
[[ -f "$MACOS_CURRENT_STATE" && ! -L "$MACOS_CURRENT_STATE" && -f "$MACOS_CURRENT_STATE.sha256" && ! -L "$MACOS_CURRENT_STATE.sha256" ]] || macos_die "formal current release state is missing or incomplete"
macos_secure_path "$MACOS_CURRENT_STATE"
macos_secure_path "$MACOS_CURRENT_STATE.sha256"
macos_check_checksum "$MACOS_CURRENT_STATE"
macos_release_state "$MACOS_CURRENT_STATE"
[[ "$MACOS_STATE_PATH" == "$release_path" ]] || macos_die "formal current release state changed after trusted verification"
[[ "$release_path" == "$MACOS_LAYOUT_RELEASES"/* && ! -L "$release_path" && -d "$release_path" ]] || macos_die "trusted release path is outside the protected releases directory"
"$SCRIPT_DIR/Test-ReleaseBundle.zsh" --release-path "$release_path" --root "$root" >/dev/null
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
    action_script="$release_path/ops/macos/Start-Platform.zsh"
    ;;
  opportunistic-backup)
    action_script="$release_path/ops/macos/Invoke-PairedBackup.zsh"
    ;;
esac
[[ -f "$action_script" && ! -L "$action_script" && -x "$action_script" ]] || macos_die "selected release LaunchAgent action is missing or not executable"
print -r -- "trusted_release_verified path=$release_path action=$action exam_approval=false"
macos_release_lock
trap - EXIT
if [[ "$action" == bootstrap ]]; then
  exec "$action_script" --root "$root"
fi
exec "$action_script" --root "$root" --kind daily --opportunistic
