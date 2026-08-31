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
[[ -f "$MACOS_CURRENT_STATE" && ! -L "$MACOS_CURRENT_STATE" && -f "$MACOS_CURRENT_STATE.sha256" && ! -L "$MACOS_CURRENT_STATE.sha256" ]] || macos_die "formal current release state is missing or incomplete"
macos_secure_path "$MACOS_CURRENT_STATE"
macos_secure_path "$MACOS_CURRENT_STATE.sha256"
macos_check_checksum "$MACOS_CURRENT_STATE"
macos_release_state "$MACOS_CURRENT_STATE"
selected_release="$MACOS_STATE_PATH"
macos_assert_outside_worktree "$selected_release" >/dev/null
[[ -x "$SCRIPT_DIR/Test-ReleaseBundle.zsh" ]] || macos_die "trusted release verifier is missing"
"$SCRIPT_DIR/Test-ReleaseBundle.zsh" --release-path "$selected_release" --root "$root" >/dev/null
trusted_runtime="$MACOS_LAYOUT_STATE/trusted-runtime-${MACOS_STATE_COMMIT:l}"
[[ "$trusted_runtime" != "$MACOS_LAYOUT_RELEASES"/* && "$trusted_runtime" != "$selected_release"/* ]] || macos_die "trusted runtime must stay outside release paths"
macos_assert_outside_worktree "$trusted_runtime" >/dev/null
trusted_runtime_staging=""
cleanup_trusted_runtime() {
  [[ -z "$trusted_runtime_staging" ]] || rm -R -- "$trusted_runtime_staging"
}
trap cleanup_trusted_runtime EXIT
typeset -a trusted_runtime_files
trusted_runtime_files=(Trusted-LaunchAgent.zsh LaunchAgent-Dispatcher.zsh Common.zsh Test-ReleaseBundle.zsh evaluate_scans.py)
if [[ -e "$trusted_runtime" ]]; then
  [[ -d "$trusted_runtime" && ! -L "$trusted_runtime" ]] || macos_die "trusted runtime is not a directory"
  for runtime_file in "${trusted_runtime_files[@]}"; do
    source_file="$SCRIPT_DIR/$runtime_file"
    [[ "$runtime_file" == evaluate_scans.py ]] && source_file="$SCRIPT_DIR/../security/evaluate_scans.py"
    [[ -f "$source_file" && ! -L "$source_file" && -f "$trusted_runtime/$runtime_file" && ! -L "$trusted_runtime/$runtime_file" ]] || macos_die "trusted runtime does not match the trusted checkout: $runtime_file"
    [[ "$(macos_sha256 "$trusted_runtime/$runtime_file")" == "$(macos_sha256 "$source_file")" ]] || macos_die "trusted runtime does not match the trusted checkout: $runtime_file"
  done
  "$trusted_runtime/Trusted-LaunchAgent.zsh" --validate-only >/dev/null
else
  trusted_runtime_staging="${trusted_runtime}.installing-$$"
  [[ ! -e "$trusted_runtime_staging" ]] || macos_die "trusted runtime staging path already exists"
  mkdir -p -- "$trusted_runtime_staging"
  chmod 700 "$trusted_runtime_staging"
  for runtime_file in "${trusted_runtime_files[@]}"; do
    source_file="$SCRIPT_DIR/$runtime_file"
    [[ "$runtime_file" == evaluate_scans.py ]] && source_file="$SCRIPT_DIR/../security/evaluate_scans.py"
    [[ -f "$source_file" && ! -L "$source_file" ]] || macos_die "trusted runtime source is missing or a symlink: $runtime_file"
    cp -p -- "$source_file" "$trusted_runtime_staging/$runtime_file"
    chmod 700 "$trusted_runtime_staging/$runtime_file"
  done
  trusted_runtime_manifest="$trusted_runtime_staging/trusted-runtime.SHA256SUMS"
  : > "$trusted_runtime_manifest"
  chmod 600 "$trusted_runtime_manifest"
  for runtime_file in "${trusted_runtime_files[@]}"; do
    print -r -- "$(macos_sha256 "$trusted_runtime_staging/$runtime_file")  $runtime_file" >> "$trusted_runtime_manifest"
  done
  "$trusted_runtime_staging/Trusted-LaunchAgent.zsh" --validate-only >/dev/null
  mv -- "$trusted_runtime_staging" "$trusted_runtime"
  trusted_runtime_staging=""
fi
[[ -x "$trusted_runtime/Trusted-LaunchAgent.zsh" ]] || macos_die "trusted host LaunchAgent is missing"
macos_secure_path "$trusted_runtime"
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
runtime_replacement="$(escape_sed_replacement "$(escape_xml_text "$trusted_runtime")")"
uid="$(id -u)"
for template in \
  "$SCRIPT_DIR/com.internal-exam.formal-bootstrap.plist.template" \
  "$SCRIPT_DIR/com.internal-exam.opportunity-backup.plist.template"; do
  [[ -f "$template" ]] || macos_die "LaunchAgent template is missing"
  plutil -lint -- "$template" >/dev/null 2>&1 || macos_die "LaunchAgent template is invalid"
  template_name="${template:t}"
  destination="$launch_agents_dir/${template_name%.template}"
  temporary="$(mktemp "${destination}.tmp.XXXXXX")"
  sed -e "s|__INTERNAL_EXAM_ROOT__|$root_replacement|g" \
      -e "s|__TRUSTED_RUNTIME_DIR__|$runtime_replacement|g" "$template" > "$temporary"
  chmod 600 "$temporary"
  plutil -lint -- "$temporary" >/dev/null 2>&1 || { rm -f -- "$temporary"; macos_die "rendered LaunchAgent is invalid"; }
  mv -f -- "$temporary" "$destination"
  chmod 600 "$destination"
  label="$(plutil -extract Label raw -o - -- "$destination")"
  launchctl bootout "gui/$uid/$label" >/dev/null 2>&1 || true
  launchctl bootstrap "gui/$uid" "$destination" >/dev/null 2>&1 || macos_die "unable to bootstrap LaunchAgent: $label"
  launchctl print "gui/$uid/$label" >/dev/null 2>&1 || macos_die "LaunchAgent did not load: $label"
done
macos_log "launchagents_installed root=$root agents=$launch_agents_dir trusted_runtime=$trusted_runtime"
