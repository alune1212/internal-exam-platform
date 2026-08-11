#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
source "$SCRIPT_DIR/Common.zsh"

source_path=""
destination_path=""
application_version=""
git_commit=""
security_evidence=""
while (( $# > 0 )); do
  case "$1" in
    --source-path|--source) (( $# >= 2 )) || macos_die "$1 requires a path"; source_path="$2"; shift 2 ;;
    --destination-path|--destination) (( $# >= 2 )) || macos_die "$1 requires a path"; destination_path="$2"; shift 2 ;;
    --application-version|--version) (( $# >= 2 )) || macos_die "$1 requires a version"; application_version="$2"; shift 2 ;;
    --git-commit|--commit) (( $# >= 2 )) || macos_die "$1 requires a commit"; git_commit="$2"; shift 2 ;;
    --security-evidence) (( $# >= 2 )) || macos_die "$1 requires a path"; security_evidence="$2"; shift 2 ;;
    -h|--help)
      print -r -- "usage: $0 --source-path PATH --destination-path PATH --application-version VERSION --git-commit SHA [--security-evidence PENDING_JSON]"
      exit 0
      ;;
    *) macos_die "unknown argument: $1"; exit 1 ;;
  esac
done

macos_assert_macos
[[ -n "$source_path" && -n "$destination_path" && -n "$application_version" && -n "$git_commit" ]] || macos_die "source, destination, version, and commit are required"
[[ "$application_version" =~ '^[0-9]+\.[0-9]+\.[0-9]+([.-][0-9A-Za-z.-]+)?$' ]] || macos_die "application version is invalid"
[[ "$git_commit" =~ '^[0-9a-fA-F]{40}$' ]] || macos_die "Git commit must be a 40 character SHA-1"
[[ "$(uname -m)" == "arm64" ]] || macos_die "macOS release bundles must be built on ARM64"

source_path="$(macos_resolve_path "$source_path")"
destination_path="$(macos_resolve_path "$destination_path")"
[[ -d "$source_path" ]] || macos_die "source directory is missing"
[[ ! -e "$destination_path" ]] || macos_die "destination already exists"
[[ "$destination_path" != "$source_path"/* && "$source_path" != "$destination_path"/* ]] || macos_die "source and destination must be separate trees"
if [[ -n "$security_evidence" ]]; then
  # Security evidence is bound only after the native ARM64 application images
  # have been built.  A passed report at this stage would necessarily refer to
  # some other image identity, so fail closed instead of accepting it.
  security_evidence="$(macos_resolve_path "$security_evidence")"
  [[ -f "$security_evidence" ]] || macos_die "security evidence is missing"
  macos_check_checksum "$security_evidence"
  [[ "$(macos_json_get "$security_evidence" status 2>/dev/null || true)" != passed ]] || macos_die "passed security evidence must be imported by Seal-Release after native images are built"
fi

# A release label is only meaningful when it names the exact clean checkout
# being copied.  Refuse arbitrary SHA labels, dirty trees, and untracked files
# (which could include a secret that the exclusion list does not know yet).
source_git_root="$(git -C "$source_path" rev-parse --show-toplevel 2>/dev/null || true)"
[[ -n "$source_git_root" && "$source_git_root" == "$source_path" ]] || macos_die "release source must be the repository root of a git worktree"
source_head="$(git -C "$source_path" rev-parse --verify HEAD 2>/dev/null || true)"
[[ "${source_head:l}" == "${git_commit:l}" ]] || macos_die "requested release commit is not the clean source HEAD"
git -C "$source_path" diff-index --quiet HEAD -- >/dev/null 2>&1 || macos_die "release source has tracked modifications"
[[ -z "$(git -C "$source_path" status --porcelain --untracked-files=all --ignored 2>/dev/null)" ]] || macos_die "release source has untracked or ignored files"

image_manifest_source="$source_path/ops/release/image-digests.json"
platform_manifest_source="$source_path/ops/release/platform-support.json"
[[ -f "$image_manifest_source" ]] || macos_die "pinned image digest manifest is missing"
[[ -f "$platform_manifest_source" ]] || macos_die "platform support manifest is missing"
plutil -convert json -o - -- "$image_manifest_source" >/dev/null 2>&1 || macos_die "pinned image digest manifest is invalid"
plutil -convert json -o - -- "$platform_manifest_source" >/dev/null 2>&1 || macos_die "platform support manifest is invalid"
platform_json="$(plutil -convert json -o - -- "$platform_manifest_source")"
grep -F 'linux/arm64' "$platform_manifest_source" >/dev/null || macos_die "platform support manifest does not include linux/arm64"

mkdir -p -- "$destination_path"
chmod 700 "$destination_path"

typeset -a manifest_paths
typeset -a manifest_digests
manifest_paths=()
manifest_digests=()

copy_release_file() {
  local source_file="$1" relative="$2" target
  [[ "$relative" != *'"'* && "$relative" != *$'\n'* && "$relative" != *'\\'* ]] || macos_die "release file name cannot be represented safely: $relative"
  target="$destination_path/$relative"
  mkdir -p -- "${target:h}"
  chmod 700 "${target:h}"
  cp -p -- "$source_file" "$target"
  chmod 600 "$target"
  manifest_paths+=("$relative")
  manifest_digests+=("$(macos_sha256 "$target")")
}

is_excluded_relative() {
  local relative="$1" segment basename
  basename="${relative:t}"
  case "$basename:l" in
    .env.example) ;;
    .env|.env.*|*.env|*.pyc|*.log|*.pem|*.key|*.p12|*.pfx|*.jks|id_rsa*|id_ed25519*|credentials*|credential*|private-key*|private_key*|*secret*) return 0 ;;
  esac
  local -a parts
  parts=("${(@s|/|)relative}")
  for segment in "$parts[@]"; do
    case "$segment" in
      .git|.venv|.runtime|node_modules|dist|backups|diagnostics|evidence|security-evidence|test-results|playwright-report|data|__pycache__|secrets|credentials|private-keys|private_keys)
        return 0
        ;;
      .env.example) ;;
      .env|.env.*|*.env|*.pem|*.key|*.p12|*.pfx|*.jks|id_rsa*|id_ed25519*|credentials*|credential*|private-key*|private_key*|*secret*)
        return 0
        ;;
    esac
  done
  return 1
}

# Inventory only files tracked by the exact clean HEAD.  This is deliberately
# narrower than `find`: ignored runtime artifacts and local credentials cannot
# enter a release even if a future denylist misses their name.
while IFS= read -r -d '' relative; do
  [[ "$relative" != /* && "$relative" != *'..'* ]] || macos_die "tracked release path is unsafe"
  source_file="$source_path/$relative"
  [[ -f "$source_file" && ! -L "$source_file" ]] || macos_die "tracked release input is not a regular file"
  is_excluded_relative "$relative" && continue
  copy_release_file "$source_file" "$relative"
done < <(git -C "$source_path" ls-files -z --cached)

mkdir -p -- "$destination_path/release-evidence"
chmod 700 "$destination_path/release-evidence"
# The initial bundle is deliberately unsealed.  This pending record is not a
# security result and cannot pass any install/start gate; Seal-Release replaces
# it with a checksummed scanner/evaluator report bound to the exact ARM64 IDs.
security_checked_at="$(macos_now_iso)"
security_placeholder='{"schemaVersion":1,"kind":"security-scan-placeholder","status":"pending","phase":"pre-build","checked_at":"'"$security_checked_at"'","secrets":"excluded"}'
security_path="$destination_path/release-evidence/security-scan.json"
macos_write_atomic "$security_path" "$security_placeholder"
macos_write_checksum "$security_path"
manifest_paths+=("release-evidence/security-scan.json")
manifest_digests+=("$(macos_sha256 "$security_path")")

# The bundle is intentionally unbuilt at this stage.  Keep an explicit,
# checksummed placeholder in the release so the normal verifier can require
# Build-ReleaseImages to replace it before installation/start.
identity_path="$destination_path/ops/release/built-image-identity.json"
mkdir -p -- "${identity_path:h}"
chmod 700 "${identity_path:h}"
identity_json='{"schemaVersion":1,"status":"pending","gitCommit":"'"${git_commit:l}"'","applicationVersion":"'"$application_version"'","platform":"linux/arm64","images":{}}'
macos_write_atomic "$identity_path" "$identity_json"
macos_write_checksum "$identity_path"
manifest_paths+=("ops/release/built-image-identity.json")
manifest_digests+=("$(macos_sha256 "$identity_path")")

# Do not infer an Alembic head from filenames: a branch or a future rename can
# make lexical ordering point at a non-head revision.  Parse every tracked
# revision/down_revision declaration and require exactly one unreferenced head.
typeset -a migration_files migration_revisions migration_down_expressions
typeset -A migration_seen migration_referenced
migration_files=()
migration_revisions=()
migration_down_expressions=()
while IFS= read -r -d '' migration_file; do
  [[ "${migration_file:t}" == __init__.py ]] && continue
  revision="$(sed -nE "s/^[[:space:]]*revision[^=]*=[[:space:]]*[\\\"']([^\\\"']+)[\\\"'].*/\\1/p" "$migration_file" | head -n 1)"
  [[ "$revision" =~ '^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$' ]] || macos_die "Alembic revision declaration is missing or invalid"
  [[ -z "${migration_seen[$revision]-}" ]] || macos_die "Alembic revision is duplicated"
  migration_seen[$revision]=1
  migration_files+=("$migration_file")
  migration_revisions+=("$revision")
  migration_down_expressions+=("$(sed -nE "s/^[[:space:]]*down_revision[^=]*=[[:space:]]*(.*)$/\\1/p" "$migration_file" | head -n 1)")
done < <(find "$destination_path/backend/alembic/versions" -type f -name '*.py' -print0)
(( ${#migration_revisions[@]} > 0 )) || macos_die "Alembic migration files are missing"
for (( migration_index = 1; migration_index <= ${#migration_revisions[@]}; migration_index += 1 )); do
  down_expression="${migration_down_expressions[migration_index]}"
  [[ "$down_expression" == *None* ]] && continue
  down_expression="$(print -r -- "$down_expression" | sed -E 's/[^A-Za-z0-9_-]+/ /g')"
  found_parent=0
  for down_token in ${(z)down_expression}; do
    case "$down_token" in
      down_revision|str|Sequence|None) continue ;;
    esac
    [[ -n "${migration_seen[$down_token]-}" ]] || macos_die "Alembic down_revision references an unknown revision"
    migration_referenced[$down_token]=1
    found_parent=1
  done
  (( found_parent == 1 )) || macos_die "Alembic migration has no parseable down_revision"
done
migration_heads=()
for revision in ${(k)migration_seen}; do
  [[ -n "${migration_referenced[$revision]-}" ]] || migration_heads+=("$revision")
done
(( ${#migration_heads[@]} == 1 )) || macos_die "Alembic migration graph must have exactly one head"
migration_head="${migration_heads[1]}"

image_json="$(cat "$destination_path/ops/release/image-digests.json")"
[[ "$image_json" == \{*\} ]] || macos_die "image digest manifest must be a JSON object"
platform_digest="$(macos_sha256 "$destination_path/ops/release/platform-support.json")"
security_digest="$(macos_sha256 "$destination_path/release-evidence/security-scan.json")"
if [[ -n "$security_evidence" ]]; then
  security_checked_at="$(macos_json_get "$security_evidence" checked_at 2>/dev/null || macos_json_get "$security_evidence" checkedAt 2>/dev/null || true)"
fi
[[ "$security_checked_at" != *'"'* && "$security_checked_at" != *$'\n'* && "$security_checked_at" != *$'\r'* ]] || macos_die "security evidence timestamp is invalid"
files_json=""
for (( index = 1; index <= ${#manifest_paths[@]}; index += 1 )); do
  [[ -z "$files_json" ]] || files_json+=","
  files_json+="{\"path\":\"${manifest_paths[index]}\",\"sha256\":\"${manifest_digests[index]}\"}"
done

manifest_json="$(cat <<EOF
{
  "formatVersion": 1,
  "applicationVersion": "${application_version}",
  "gitCommit": "${git_commit:l}",
  "createdAt": "$(macos_now_iso)",
  "imageTag": "${git_commit:l}",
  "hostOS": "darwin",
  "architecture": "arm64",
  "platform": "linux/arm64",
  "migrationHead": "${migration_head}",
  "securityEvidence": {"checkedAt": "${security_checked_at}", "sha256": "${security_digest}", "status": "pending"},
  "platformSupport": {"path": "ops/release/platform-support.json", "sha256": "${platform_digest}"},
  "baseImageReferences": ${image_json},
  "imageDigests": {},
  "builtImageIdentity": {"path": "ops/release/built-image-identity.json", "sha256": "$(macos_sha256 "$identity_path")", "status": "pending"},
  "sealState": "unsealed",
  "files": [${files_json}]
}
EOF
)"
macos_write_atomic "$destination_path/release-manifest.json" "$manifest_json"
macos_write_atomic "$destination_path/SHA256SUMS" "$(for (( index = 1; index <= ${#manifest_paths[@]}; index += 1 )); do print -r -- "${manifest_digests[index]}  ${manifest_paths[index]}"; done)"
chmod 600 "$destination_path/release-manifest.json" "$destination_path/SHA256SUMS"

"$SCRIPT_DIR/Test-ReleaseBundle.zsh" --release-path "$destination_path" --allow-unbuilt >/dev/null
macos_log "release_bundle_created version=$application_version commit=${git_commit:l} path=$destination_path state=unsealed security=pending next=Build-ReleaseImages"
