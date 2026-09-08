#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
self_release_path="${SCRIPT_DIR:h:h}"
if [[ -f "$self_release_path/release-manifest.json" ]]; then
  typeset -a trusted_argv=("$@")
  trusted_root="${INTERNAL_EXAM_ROOT:-${HOME:?}/Library/Application Support/InternalExam}"
  for (( trusted_index = 1; trusted_index <= ${#trusted_argv[@]}; trusted_index += 1 )); do
    if [[ "${trusted_argv[trusted_index]}" == --root ]]; then
      (( trusted_index < ${#trusted_argv[@]} )) || { print -u2 -- "macOS operation failed: bundled installer root is missing"; exit 1; }
      trusted_root="${trusted_argv[trusted_index + 1]}"
      (( trusted_index += 1 ))
    fi
  done
  trusted_state="$trusted_root/state/current-release.json"
  trusted_commit="$(/usr/bin/plutil -extract gitCommit raw -o - -- "$trusted_state" 2>/dev/null || true)"
  [[ "$trusted_commit" =~ '^[0-9a-fA-F]{40}$' ]] || { print -u2 -- "macOS operation failed: bundled installer cannot locate trusted runtime"; exit 1; }
  trusted_runtime="$trusted_root/state/trusted-runtime-${trusted_commit:l}"
  [[ -d "$trusted_runtime" && ! -L "$trusted_runtime" && -x "$trusted_runtime/Trusted-LaunchAgent.zsh" && ! -L "$trusted_runtime/Trusted-LaunchAgent.zsh" ]] || { print -u2 -- "macOS operation failed: bundled installer trusted runtime is missing"; exit 1; }
  "$trusted_runtime/Trusted-LaunchAgent.zsh" --verify-release --release-path "$self_release_path" --root "$trusted_root" >/dev/null || {
    print -u2 -- "macOS operation failed: bundled installer requires external signature verification"
    exit 1
  }
fi
source "$SCRIPT_DIR/Common.zsh"

bundle_path=""
root="${INTERNAL_EXAM_ROOT:-${HOME:?}/Library/Application Support/InternalExam}"
while (( $# > 0 )); do
  case "$1" in
    --bundle-path|--bundle) (( $# >= 2 )) || macos_die "$1 requires a path"; bundle_path="$2"; shift 2 ;;
    --root) (( $# >= 2 )) || macos_die "--root requires a path"; root="$2"; shift 2 ;;
    -h|--help)
      print -r -- "usage: $0 --bundle-path PATH [--root ABSOLUTE_ROOT]"
      exit 0
      ;;
    *) macos_die "unknown argument: $1"; exit 1 ;;
  esac
done

macos_assert_macos
[[ -n "$bundle_path" ]] || macos_die "--bundle-path is required"
bundle_path="$(macos_resolve_path "$bundle_path")"
[[ -d "$bundle_path" ]] || macos_die "release bundle directory is missing"
macos_initialize_layout "$root"
macos_acquire_lock "$MACOS_LAYOUT_STATE/.operation.lock"
temporary_target=""
cleanup_install() {
  [[ -z "$temporary_target" ]] || rm -rf -- "$temporary_target"
  macos_release_lock
}
trap cleanup_install EXIT
while IFS= read -r -d '' link; do
  macos_die "release bundle contains a symlink: ${link#$bundle_path/}"
done < <(find "$bundle_path" -type l -print0)
"$SCRIPT_DIR/Test-ReleaseBundle.zsh" --release-path "$bundle_path" --root "$root" >/dev/null

manifest_path="$bundle_path/release-manifest.json"
version="$(macos_json_get "$manifest_path" applicationVersion)"
commit="$(macos_json_get "$manifest_path" gitCommit)"
target="$MACOS_LAYOUT_RELEASES/$version"
[[ ! -e "$target" ]] || macos_die "release version is already installed: $version"
macos_assert_outside_worktree "$target" >/dev/null

temporary_target="${target}.installing-$$"
[[ ! -e "$temporary_target" ]] || macos_die "release staging destination already exists"
mkdir -p -- "$temporary_target"
chmod 700 "$temporary_target"
cp -pR -- "$bundle_path/." "$temporary_target/"
while IFS= read -r directory; do chmod 700 "$directory"; done < <(find "$temporary_target" -type d -print)
while IFS= read -r file; do chmod 600 "$file"; done < <(find "$temporary_target" -type f -print)
while IFS= read -r file; do chmod 700 "$file"; done < <(find "$temporary_target/ops/macos" -type f -name '*.zsh' -print)
[[ -x "$SCRIPT_DIR/Test-ReleaseBundle.zsh" ]] || macos_die "trusted release verifier is missing"
"$SCRIPT_DIR/Test-ReleaseBundle.zsh" --release-path "$temporary_target" --root "$root" >/dev/null
mv -f -- "$temporary_target" "$target"
temporary_target=""
macos_log "release_installed version=$version commit=$commit path=$target"
