#!/bin/zsh
set -euo pipefail
umask 077

SCRIPT_DIR="${0:A:h}"
source "$SCRIPT_DIR/Common.zsh"

root="${INTERNAL_EXAM_ROOT:-${HOME:?}/Library/Application Support/InternalExam}"
launch_agents_dir="${HOME:?}/Library/LaunchAgents"
while (( $# > 0 )); do
  case "$1" in
    --root) (( $# >= 2 )) || macos_die "--root requires a path"; root="$2"; shift 2 ;;
    --launch-agents-dir) (( $# >= 2 )) || macos_die "--launch-agents-dir requires a path"; launch_agents_dir="$2"; shift 2 ;;
    -h|--help) print -r -- "usage: $0 [--root ROOT] [--launch-agents-dir ABSOLUTE_DIR]"; exit 0 ;;
    *) macos_die "unknown argument: $1"; exit 1 ;;
  esac
done

macos_assert_macos
macos_assert_outside_worktree "$root" >/dev/null
[[ "$launch_agents_dir" == /* ]] || macos_die "LaunchAgents directory must be absolute"
macos_initialize_layout "$root"
macos_assert_protected_configuration "$root"
macos_assert_formal_writer_ready 0
macos_release_state "$MACOS_CURRENT_STATE"
selected_release="$MACOS_STATE_PATH"
macos_assert_outside_worktree "$selected_release" >/dev/null
"$selected_release/ops/macos/Test-ReleaseBundle.zsh" --release-path "$selected_release" >/dev/null
ops_dir="$selected_release/ops/macos"
mkdir -p -- "$launch_agents_dir"
chmod 700 "$launch_agents_dir"
macos_require_command plutil
macos_require_command launchctl

escape_sed_replacement() {
  local value="${1:-}"
  value="${value//\\/\\\\}"
  value="${value//&/\\&}"
  value="${value//|/\\|}"
  print -r -- "$value"
}

escape_xml_text() {
  local value="${1:-}"
  [[ "$value" != *$'\n'* && "$value" != *$'\r'* ]] || macos_die "LaunchAgent path contains a newline"
  value="${value//&/&amp;}"
  value="${value//</&lt;}"
  value="${value//>/&gt;}"
  print -r -- "$value"
}

root_replacement="$(escape_sed_replacement "$(escape_xml_text "$root")")"
ops_replacement="$(escape_sed_replacement "$(escape_xml_text "$ops_dir")")"
uid="$(id -u)"
for template in \
  "$ops_dir/com.internal-exam.formal-bootstrap.plist.template" \
  "$ops_dir/com.internal-exam.opportunity-backup.plist.template"; do
  [[ -f "$template" ]] || macos_die "LaunchAgent template is missing"
  plutil -lint -- "$template" >/dev/null 2>&1 || macos_die "LaunchAgent template is invalid"
  template_name="${template:t}"
  destination="$launch_agents_dir/${template_name%.template}"
  temporary="$(mktemp "${destination}.tmp.XXXXXX")"
  sed -e "s|__INTERNAL_EXAM_ROOT__|$root_replacement|g" \
      -e "s|__MACOS_OPS_DIR__|$ops_replacement|g" "$template" > "$temporary"
  chmod 600 "$temporary"
  plutil -lint -- "$temporary" >/dev/null 2>&1 || { rm -f -- "$temporary"; macos_die "rendered LaunchAgent is invalid"; }
  mv -f -- "$temporary" "$destination"
  chmod 600 "$destination"
  label="$(plutil -extract Label raw -o - -- "$destination")"
  launchctl bootout "gui/$uid/$label" >/dev/null 2>&1 || true
  launchctl bootstrap "gui/$uid" "$destination" >/dev/null 2>&1 || macos_die "unable to bootstrap LaunchAgent: $label"
  launchctl print "gui/$uid/$label" >/dev/null 2>&1 || macos_die "LaunchAgent did not load: $label"
done
macos_log "launchagents_installed root=$root agents=$launch_agents_dir"
