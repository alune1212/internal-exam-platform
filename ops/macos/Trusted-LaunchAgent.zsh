#!/bin/zsh
set -euo pipefail
setopt no_nomatch
umask 077

# This launcher is deliberately standalone until the trusted runtime has
# passed its own file-hash check.  Do not source Common.zsh before that check:
# Common.zsh and the release verifier are both installed beside this file.
runtime_dir="${0:A:h}"
runtime_manifest="$runtime_dir/trusted-runtime.SHA256SUMS"
launcher_path="${0:A}"

runtime_die() {
  print -u2 -- "trusted macOS LaunchAgent failed: $*"
  return 1
}

runtime_secure_path() {
  local target_path="${1:-}" mode owner
  [[ -f "$target_path" && ! -L "$target_path" ]] || runtime_die "trusted runtime file is missing or a symlink: $target_path"
  mode="$(/usr/bin/stat -f '%Lp' -- "$target_path")"
  (( (8#$mode & 8#077) == 0 )) || runtime_die "trusted runtime file is not owner-only: $target_path"
  owner="$(/usr/bin/stat -f '%Su' -- "$target_path")"
  [[ "$owner" == "$(/usr/bin/id -un)" ]] || runtime_die "trusted runtime file is not owned by the current operator: $target_path"
}

runtime_secure_directory() {
  local target_path="${1:-}" mode owner
  [[ -d "$target_path" && ! -L "$target_path" ]] || runtime_die "trusted runtime directory is missing or a symlink: $target_path"
  mode="$(/usr/bin/stat -f '%Lp' -- "$target_path")"
  (( (8#$mode & 8#077) == 0 )) || runtime_die "trusted runtime directory is not owner-only: $target_path"
  owner="$(/usr/bin/stat -f '%Su' -- "$target_path")"
  [[ "$owner" == "$(/usr/bin/id -un)" ]] || runtime_die "trusted runtime directory is not owned by the current operator: $target_path"
}

runtime_sha256() {
  /usr/bin/shasum -a 256 -- "$1" | /usr/bin/awk '{print $1}'
}

runtime_validate() {
  local line digest name actual row_count=0
  typeset -A expected
  runtime_secure_directory "$runtime_dir"
  runtime_secure_path "$launcher_path"
  runtime_secure_path "$runtime_manifest"

  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ "$line" =~ '^([0-9a-f]{64})[[:space:]][[:space:]]([A-Za-z0-9._-]+)$' ]] || runtime_die "trusted runtime manifest row is invalid"
    digest="${match[1]}"
    name="${match[2]}"
    [[ -z "${expected[$name]-}" ]] || runtime_die "trusted runtime manifest contains a duplicate row"
    expected[$name]="$digest"
    (( row_count += 1 ))
  done < "$runtime_manifest"

  (( row_count == 4 )) || runtime_die "trusted runtime manifest must contain exactly four files"
  for name in Trusted-LaunchAgent.zsh LaunchAgent-Dispatcher.zsh Common.zsh Test-ReleaseBundle.zsh; do
    digest="${expected[$name]-}"
    [[ -n "$digest" ]] || runtime_die "trusted runtime manifest is missing: $name"
    runtime_secure_path "$runtime_dir/$name"
    actual="$(runtime_sha256 "$runtime_dir/$name")"
    [[ "$actual" == "$digest" ]] || runtime_die "trusted runtime hash validation failed: $name"
    [[ -x "$runtime_dir/$name" ]] || runtime_die "trusted runtime operation is not executable: $name"
  done

  while IFS= read -r -d '' entry_path; do
    case "${entry_path#$runtime_dir/}" in
      Trusted-LaunchAgent.zsh|LaunchAgent-Dispatcher.zsh|Common.zsh|Test-ReleaseBundle.zsh|trusted-runtime.SHA256SUMS) ;;
      *) runtime_die "trusted runtime contains an unlisted file: ${entry_path#$runtime_dir/}" ;;
    esac
  done < <(/usr/bin/find "$runtime_dir" -mindepth 1 -type f -print0)
  while IFS= read -r -d '' entry_path; do
    runtime_die "trusted runtime contains an unexpected directory: ${entry_path#$runtime_dir/}"
  done < <(/usr/bin/find "$runtime_dir" -mindepth 1 -type d -print0)
  while IFS= read -r -d '' entry_path; do
    runtime_die "trusted runtime contains a symlink: ${entry_path#$runtime_dir/}"
  done < <(/usr/bin/find "$runtime_dir" -type l -print0)
}

runtime_validate

if [[ "${1:-}" == --validate-only && $# -eq 1 ]]; then
  exit 0
fi

action="${1:-}"
shift || true
root="${INTERNAL_EXAM_ROOT:-${HOME:?}/Library/Application Support/InternalExam}"
while (( $# > 0 )); do
  case "$1" in
    --root) (( $# >= 2 )) || runtime_die "--root requires a path"; root="$2"; shift 2 ;;
    *) runtime_die "unknown trusted launcher argument: $1"; exit 1 ;;
  esac
done
[[ "$action" == bootstrap || "$action" == opportunistic-backup ]] || runtime_die "unsupported LaunchAgent action"

# Runtime support is now hash-validated.  All release and state handling below
# is performed by this trusted copy of Common.zsh and Test-ReleaseBundle.zsh.
source "$runtime_dir/Common.zsh"
macos_assert_macos
macos_assert_outside_worktree "$root" >/dev/null
macos_assert_protected_configuration "$root"
macos_layout "$root"

current_state="$MACOS_CURRENT_STATE"
[[ -f "$current_state" && ! -L "$current_state" && -f "$current_state.sha256" && ! -L "$current_state.sha256" ]] || macos_die "formal current release state is missing or incomplete"
macos_secure_path "$current_state"
macos_secure_path "$current_state.sha256"
macos_check_checksum "$current_state"
macos_release_state "$current_state"
selected_release="$MACOS_STATE_PATH"
[[ "$selected_release" == "$MACOS_LAYOUT_RELEASES"/* && ! -L "$selected_release" && -d "$selected_release" ]] || macos_die "formal current state points outside the protected releases directory"

# This is the only verifier used by the LaunchAgent path.  It validates the
# external public key/fingerprint and both release signatures before any
# release-bundled action can be sourced or executed.
trusted_verifier="$runtime_dir/Test-ReleaseBundle.zsh"
"$trusted_verifier" --release-path "$selected_release" --root "$root" >/dev/null

case "$action" in
  bootstrap) action_script="$selected_release/ops/macos/Start-Platform.zsh" ;;
  opportunistic-backup) action_script="$selected_release/ops/macos/Invoke-PairedBackup.zsh" ;;
esac
[[ -f "$action_script" && ! -L "$action_script" && -x "$action_script" ]] || macos_die "selected release LaunchAgent action is missing or not executable"

export INTERNAL_EXAM_TRUSTED_RUNTIME_DIR="$runtime_dir"
export INTERNAL_EXAM_TRUSTED_RELEASE_VERIFIED=1
exec "$runtime_dir/LaunchAgent-Dispatcher.zsh" "$action" --root "$root" --release-path "$selected_release"
