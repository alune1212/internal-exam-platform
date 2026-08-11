#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
source "$SCRIPT_DIR/Common.zsh"

release_path=""
allow_unbuilt=0
allow_unsealed=0
while (( $# > 0 )); do
  case "$1" in
    --release-path) (( $# >= 2 )) || macos_die "--release-path requires a path"; release_path="$2"; shift 2 ;;
    --allow-unbuilt) allow_unbuilt=1; shift ;;
    --allow-unsealed) allow_unsealed=1; shift ;;
    -h|--help)
      print -r -- "usage: $0 --release-path ABSOLUTE_RELEASE"
      exit 0
      ;;
    *) macos_die "unknown argument: $1"; exit 1 ;;
  esac
done

macos_assert_macos
[[ -n "$release_path" ]] || macos_die "--release-path is required"
release_path="$(macos_resolve_path "$release_path")"
[[ -d "$release_path" ]] || macos_die "release directory is missing"
manifest_path="$release_path/release-manifest.json"
checksums_path="$release_path/SHA256SUMS"
[[ -f "$manifest_path" && -f "$checksums_path" ]] || macos_die "release manifest or SHA256SUMS is missing"
plutil -convert json -o - -- "$manifest_path" >/dev/null 2>&1 || macos_die "release manifest is invalid"

format_version="$(macos_json_get "$manifest_path" formatVersion 2>/dev/null || macos_json_get "$manifest_path" format_version 2>/dev/null || true)"
[[ "$format_version" == "1" ]] || macos_die "unsupported release manifest format"
application_version="$(macos_json_get "$manifest_path" applicationVersion 2>/dev/null || macos_json_get "$manifest_path" application_version 2>/dev/null || true)"
git_commit="$(macos_json_get "$manifest_path" gitCommit 2>/dev/null || macos_json_get "$manifest_path" git_commit 2>/dev/null || true)"
[[ "$application_version" =~ '^[0-9]+\.[0-9]+\.[0-9]+([.-][0-9A-Za-z.-]+)?$' ]] || macos_die "release application version is invalid"
[[ "$git_commit" =~ '^[0-9a-fA-F]{40}$' ]] || macos_die "release Git commit is invalid"
[[ "$(macos_json_get "$manifest_path" hostOS 2>/dev/null || true)" == darwin ]] || macos_die "release host OS identity is invalid"
[[ "$(macos_json_get "$manifest_path" architecture 2>/dev/null || true)" == arm64 ]] || macos_die "release architecture identity is invalid"
[[ "$(macos_json_get "$manifest_path" platform 2>/dev/null || macos_json_get "$manifest_path" targetPlatform 2>/dev/null || true)" == linux/arm64 ]] || macos_die "release target platform identity is invalid"

security_path="$release_path/release-evidence/security-scan.json"
[[ -f "$security_path" ]] || macos_die "checksummed security evidence is missing"
macos_check_checksum "$security_path"
security_status="$(macos_json_get "$security_path" status 2>/dev/null || true)"
security_digest="$(macos_sha256 "$security_path")"
manifest_security_digest="$(macos_json_get "$manifest_path" securityEvidence.sha256 2>/dev/null || macos_json_get "$manifest_path" security_evidence.sha256 2>/dev/null || true)"
[[ "$manifest_security_digest" == "$security_digest" ]] || macos_die "security evidence identity does not match the release manifest"
if [[ "$security_status" == pending ]]; then
  (( allow_unbuilt == 1 || allow_unsealed == 1 )) || macos_die "security evidence is pending; import scanner output with Seal-Release"
else
  [[ "$security_status" == passed ]] || macos_die "security evidence did not pass release policy"
  [[ "$(macos_json_get "$security_path" scannerEvidenceSha256 2>/dev/null || true)" =~ '^[0-9a-fA-F]{64}$' ]] || macos_die "sealed security evidence lacks scanner provenance"
  [[ "$(macos_json_get "$security_path" imageRecordSha256 2>/dev/null || true)" =~ '^[0-9a-fA-F]{64}$' ]] || macos_die "sealed security evidence lacks final image record provenance"
  [[ "$(macos_json_get "$security_path" scannerMode 2>/dev/null || true)" == identity-bound ]] || macos_die "sealed security evidence lacks identity-bound evaluator mode"
  security_json="$(plutil -convert json -o - -- "$security_path")"
  [[ "$security_json" =~ '"binding_errors"[[:space:]]*:[[:space:]]*\[[[:space:]]*\]' ]] || macos_die "sealed security evidence contains image binding errors"
  security_checked_at="$(macos_json_get "$security_path" checked_at 2>/dev/null || macos_json_get "$security_path" checkedAt 2>/dev/null || true)"
  manifest_security_checked_at="$(macos_json_get "$manifest_path" securityEvidence.checkedAt 2>/dev/null || macos_json_get "$manifest_path" security_evidence.checked_at 2>/dev/null || true)"
  [[ -n "$security_checked_at" && "$security_checked_at" == "$manifest_security_checked_at" ]] || macos_die "security evidence timestamp does not match the release manifest"
  macos_assert_fresh_timestamp "$security_checked_at"
  security_platform="$(macos_json_get "$security_path" imagePlatform 2>/dev/null || macos_json_get "$security_path" finalImagePlatform 2>/dev/null || macos_json_get "$security_path" targetPlatform 2>/dev/null || true)"
  [[ "$security_platform" == linux/arm64 ]] || macos_die "security evidence is not for native linux/arm64 final images"
fi

image_manifest="$release_path/ops/release/image-digests.json"
platform_manifest="$release_path/ops/release/platform-support.json"
[[ -f "$image_manifest" ]] || macos_die "pinned image digest manifest is missing"
[[ -f "$platform_manifest" ]] || macos_die "architecture support manifest is missing"
plutil -convert json -o - -- "$image_manifest" >/dev/null 2>&1 || macos_die "image digest manifest is invalid"
plutil -convert json -o - -- "$platform_manifest" >/dev/null 2>&1 || macos_die "platform support manifest is invalid"
platforms="$(plutil -convert json -o - -- "$platform_manifest" 2>/dev/null || true)"
grep -F 'linux/arm64' "$platform_manifest" >/dev/null || macos_die "release does not prove linux/arm64 support"

for base_name in backend_base backend_postgres_tools frontend_builder frontend_runtime gateway postgres; do
  base_reference="$(macos_json_get "$image_manifest" "$base_name" 2>/dev/null || true)"
  [[ "$base_reference" =~ '^[a-z0-9][a-z0-9._/-]{0,254}(:[A-Za-z0-9_][A-Za-z0-9._-]{0,127})?@sha256:[0-9a-f]{64}$' ]] || macos_die "base image reference is not immutable"
  [[ "$(macos_json_get "$manifest_path" "baseImageReferences.$base_name" 2>/dev/null || true)" == "$base_reference" ]] || macos_die "base image identity does not match the release manifest"
done

built_identity="$release_path/ops/release/built-image-identity.json"
[[ -f "$built_identity" && -f "$built_identity.sha256" ]] || macos_die "built image identity is missing"
macos_check_checksum "$built_identity"
[[ "$(macos_json_get "$manifest_path" builtImageIdentity.path 2>/dev/null || true)" == "ops/release/built-image-identity.json" ]] || macos_die "built image identity path is invalid"
[[ "$(macos_json_get "$manifest_path" builtImageIdentity.sha256 2>/dev/null || true)" == "$(macos_sha256 "$built_identity")" ]] || macos_die "built image identity checksum does not match the release manifest"
identity_status="$(macos_json_get "$built_identity" status 2>/dev/null || true)"
[[ "$identity_status" == passed || "$identity_status" == pending ]] || macos_die "built image identity status is invalid"
[[ "$identity_status" != pending || $allow_unbuilt -eq 1 ]] || macos_die "release images have not been built"
[[ "$(macos_json_get "$built_identity" gitCommit 2>/dev/null || true)" == "${git_commit:l}" ]] || macos_die "built image identity commit does not match the release"
[[ "$(macos_json_get "$built_identity" platform 2>/dev/null || true)" == linux/arm64 ]] || macos_die "built image identity platform is invalid"
security_identity_digest="$(macos_json_get "$security_path" builtImageIdentitySha256 2>/dev/null || macos_json_get "$security_path" imageIdentitySha256 2>/dev/null || true)"
if [[ "$identity_status" == passed && "$security_status" == passed ]]; then
  [[ "$security_identity_digest" == "$(macos_sha256 "$built_identity")" ]] || macos_die "security evidence image identity does not match built images"
  for image_name in db backend frontend gateway; do
    security_image_id="$(macos_json_get "$security_path" "imageIds.$image_name" 2>/dev/null || true)"
    [[ -z "$security_image_id" || "$security_image_id" == "$(macos_json_get "$built_identity" "images.$image_name.id")" ]] || macos_die "security evidence image ID does not match built image identity"
    security_image_reference="$(macos_json_get "$security_path" "imageReferences.$image_name" 2>/dev/null || true)"
    [[ "$security_image_reference" == "$(macos_json_get "$built_identity" "images.$image_name.reference")" ]] || macos_die "security evidence image reference does not match built image identity"
  done
fi
for image_name in db backend frontend gateway; do
  image_reference="$(macos_json_get "$built_identity" "images.$image_name.reference" 2>/dev/null || true)"
  image_id="$(macos_json_get "$built_identity" "images.$image_name.id" 2>/dev/null || true)"
  [[ "$identity_status" == pending && -z "$image_reference" && -z "$image_id" ]] && continue
  [[ "$image_reference" == *":${git_commit:l}" ]] || macos_die "built image tag does not match the release commit"
  [[ "$image_id" =~ '^sha256:[0-9a-f]{64}$' ]] || macos_die "built image ID is invalid"
  [[ "$(macos_json_get "$built_identity" "images.$image_name.os" 2>/dev/null || true)" == linux ]] || macos_die "built image OS is invalid"
  [[ "$(macos_json_get "$built_identity" "images.$image_name.architecture" 2>/dev/null || true)" == arm64 ]] || macos_die "built image architecture is invalid"
  if [[ "$identity_status" == passed ]]; then
    [[ "$(macos_json_get "$manifest_path" "imageDigests.$image_name" 2>/dev/null || true)" == "$image_reference" ]] || macos_die "final image identity does not match built image identity"
  fi
done

seal_state="$(macos_json_get "$manifest_path" sealState 2>/dev/null || true)"
[[ "$seal_state" == sealed || $allow_unsealed -eq 1 || $allow_unbuilt -eq 1 ]] || macos_die "release bundle is unsealed; run Seal-Release after native security evaluation"

typeset -A checksum_rows
typeset -A manifest_rows
checksum_count=0
while IFS= read -r checksum_line || [[ -n "$checksum_line" ]]; do
  [[ "$checksum_line" =~ '^([0-9a-fA-F]{64})[[:space:]][[:space:]](.+)$' ]] || macos_die "invalid SHA256SUMS row"
  digest="${match[1]}"
  relative="${match[2]}"
  [[ "$relative" != /* && "$relative" != *'..'* ]] || macos_die "unsafe release path in checksum manifest"
  [[ -z "${checksum_rows[$relative]-}" ]] || macos_die "duplicate release checksum row"
  checksum_rows[$relative]="$digest"
  (( checksum_count += 1 ))
done < "$checksums_path"

manifest_count=0
while :; do
  relative="$(macos_json_get "$manifest_path" "files.$manifest_count.path" 2>/dev/null || true)"
  [[ -n "$relative" ]] || break
  [[ "$relative" != /* && "$relative" != *'..'* ]] || macos_die "unsafe release path in manifest"
  [[ -z "${manifest_rows[$relative]-}" ]] || macos_die "duplicate release manifest row"
  manifest_rows[$relative]=1
  case "$relative" in
    .env.example|*/.env.example) ;;
    .env|*/.env|.env.*|*/.env.*|*.env|*/*.env|*.pem|*/*.pem|*.key|*/*.key|*.p12|*/*.p12|*.pfx|*/*.pfx|*.jks|*/*.jks|id_rsa*|*/id_rsa*|id_ed25519*|*/id_ed25519*|credentials*|*/credentials*|credential*|*/credential*|private-key*|*/private-key*|private_key*|*/private_key*|*secret*|*/*secret*|*/backups/*|*/diagnostics/*|*/evidence/*|*/data/*|*/token*|*/otp*)
      macos_die "release bundle contains a forbidden runtime or secret file"
      ;;
  esac
  full_path="$release_path/$relative"
  [[ -f "$full_path" ]] || macos_die "release file is missing: $relative"
  expected="${checksum_rows[$relative]-}"
  [[ -n "$expected" ]] || macos_die "release file is absent from SHA256SUMS: $relative"
  actual="$(macos_sha256 "$full_path")"
  [[ "$expected" == "$actual" ]] || macos_die "release checksum failed: $relative"
  (( manifest_count += 1 ))
done
(( manifest_count > 0 && manifest_count == checksum_count )) || macos_die "manifest and checksum file counts differ"

# No post-build injection is allowed: every regular file must be named by the
# manifest/checksum set.  Manifest/SHA files and their explicit checksum
# sidecars are the only metadata exceptions; symlinks are never accepted.
while IFS= read -r -d '' extra_path; do
  relative="${extra_path#$release_path/}"
  case "$relative" in
    release-manifest.json|SHA256SUMS) continue ;;
    *.sha256)
      sidecar_target="${relative%.sha256}"
      [[ -f "$release_path/$sidecar_target" && -n "${checksum_rows[$sidecar_target]-}" ]] || macos_die "release contains an unpaired checksum sidecar"
      continue
      ;;
  esac
  [[ -n "${checksum_rows[$relative]-}" ]] || macos_die "release contains an unlisted file"
done < <(find "$release_path" -type f -print0)
while IFS= read -r -d '' link_path; do
  macos_die "release bundle contains a symlink"
done < <(find "$release_path" -type l -print0)

macos_log "release_bundle_valid version=$application_version commit=$git_commit architecture=arm64"
