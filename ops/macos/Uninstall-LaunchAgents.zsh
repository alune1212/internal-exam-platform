#!/bin/zsh
set -euo pipefail
umask 077

SCRIPT_DIR="${0:A:h}"
source "$SCRIPT_DIR/Common.zsh"

confirmation=""
launch_agents_dir="${HOME:?}/Library/LaunchAgents"
while (( $# > 0 )); do
  case "$1" in
    --confirmation) (( $# >= 2 )) || macos_die "--confirmation requires exact text"; confirmation="$2"; shift 2 ;;
    --launch-agents-dir) (( $# >= 2 )) || macos_die "--launch-agents-dir requires a path"; launch_agents_dir="$2"; shift 2 ;;
    -h|--help) print -r -- "usage: $0 --confirmation 'UNINSTALL INTERNAL EXAM LAUNCHAGENTS' [--launch-agents-dir ABSOLUTE_DIR]"; exit 0 ;;
    *) macos_die "unknown argument: $1"; exit 1 ;;
  esac
done

macos_assert_macos
[[ "$confirmation" == 'UNINSTALL INTERNAL EXAM LAUNCHAGENTS' ]] || macos_die "exact uninstall confirmation did not match"
[[ "$launch_agents_dir" == /* ]] || macos_die "LaunchAgents directory must be absolute"
macos_require_command launchctl
uid="$(id -u)"
for label in com.internal-exam.formal-bootstrap com.internal-exam.opportunity-backup; do
  launchctl bootout "gui/$uid/$label" >/dev/null 2>&1 || true
  file="$launch_agents_dir/$label.plist"
  [[ -f "$file" ]] && rm -f -- "$file"
done
macos_log "launchagents_uninstalled agents=$launch_agents_dir"
