#!/bin/zsh
set -euo pipefail
setopt no_nomatch
umask 077

SCRIPT_DIR="${0:A:h}"
source "$SCRIPT_DIR/Common.zsh"

# Seal-Release is the only transition from the unsealed native-image bundle to
# an installable formal release.

release_path=""
security_evidence=""
image_record=""
scanner_evidence_dir=""
confirmation=""
root="${INTERNAL_EXAM_ROOT:-${HOME:?}/Library/Application Support/InternalExam}"
while (( $# > 0 )); do
  case "$1" in
    --release-path|--release) (( $# >= 2 )) || macos_die "$1 requires a path"; release_path="$2"; shift 2 ;;
    --security-evidence|--scanner-evidence) (( $# >= 2 )) || macos_die "$1 requires a path"; security_evidence="$2"; shift 2 ;;
    --image-record|--final-image-record) (( $# >= 2 )) || macos_die "$1 requires a path"; image_record="$2"; shift 2 ;;
    --scanner-evidence-dir|--evidence-dir) (( $# >= 2 )) || macos_die "$1 requires a path"; scanner_evidence_dir="$2"; shift 2 ;;
    --confirmation) (( $# >= 2 )) || macos_die "--confirmation requires exact text"; confirmation="$2"; shift 2 ;;
    --root) (( $# >= 2 )) || macos_die "--root requires a path"; root="$2"; shift 2 ;;
    -h|--help)
      print -r -- "usage: $0 --release-path PATH --security-evidence CHECKSUMMED_SCANNER_JSON --image-record CHECKSUMMED_FINAL_IMAGES_JSON --scanner-evidence-dir CHECKSUMMED_RAW_EVIDENCE_DIR --confirmation 'SEAL RELEASE VERSION' [--root ROOT]"
      exit 0
      ;;
    *) macos_die "unknown argument: $1"; exit 1 ;;
  esac
done

macos_assert_macos
[[ -n "$release_path" && -n "$security_evidence" && -n "$image_record" && -n "$confirmation" ]] || macos_die "release, scanner evidence, image record, and confirmation are required"
macos_assert_outside_worktree "$root" >/dev/null
macos_initialize_layout "$root"
macos_acquire_lock "$MACOS_LAYOUT_STATE/.operation.lock"
trap macos_release_lock EXIT

release_path="$(macos_resolve_path "$release_path")"
security_evidence="$(macos_resolve_path "$security_evidence")"
image_record="$(macos_resolve_path "$image_record")"
if [[ -z "$scanner_evidence_dir" ]]; then
  scanner_evidence_relative="$(macos_json_get "$security_evidence" scannerEvidence.path 2>/dev/null || true)"
  [[ -n "$scanner_evidence_relative" && "$scanner_evidence_relative" != /* && "$scanner_evidence_relative" != *'..'* && "$scanner_evidence_relative" != *$'\n'* ]] || macos_die "raw scanner evidence directory is required"
  scanner_evidence_dir="${security_evidence:h}/$scanner_evidence_relative"
fi
scanner_evidence_dir="$(macos_resolve_path "$scanner_evidence_dir")"
[[ -d "$release_path" ]] || macos_die "release directory is missing"
[[ "$security_evidence" != "$release_path"/* && "$image_record" != "$release_path"/* && "$scanner_evidence_dir" != "$release_path"/* ]] || macos_die "scanner inputs must be outside the release being sealed"
"$SCRIPT_DIR/Test-ReleaseBundle.zsh" --release-path "$release_path" --allow-unbuilt --allow-unsealed >/dev/null
macos_verify_built_image_identity "$release_path"

manifest="$release_path/release-manifest.json"
version="$(macos_json_get "$manifest" applicationVersion)"
commit="$(macos_json_get "$manifest" gitCommit)"
[[ "$confirmation" == "SEAL RELEASE $version" ]] || macos_die "exact release seal confirmation did not match"
identity="$release_path/ops/release/built-image-identity.json"
identity_digest="$(macos_sha256 "$identity")"

[[ -f "$security_evidence" ]] || macos_die "scanner security evidence is missing"
macos_check_checksum "$security_evidence"
plutil -convert json -o - -- "$security_evidence" >/dev/null 2>&1 || macos_die "scanner security evidence is invalid JSON"
[[ "$(macos_json_get "$security_evidence" schema_version 2>/dev/null || macos_json_get "$security_evidence" schemaVersion 2>/dev/null || true)" == 1 ]] || macos_die "scanner security evidence schema is unsupported"
[[ "$(macos_json_get "$security_evidence" status 2>/dev/null || true)" == passed ]] || macos_die "scanner security evidence did not pass policy"
[[ "$(macos_json_get "$security_evidence" policy 2>/dev/null || true)" == 'critical-blocks; high-blocks-until-reviewed-not-exploitable' ]] || macos_die "security evidence was not produced by the release policy evaluator"
[[ "$(macos_json_get "$security_evidence" finding_count 2>/dev/null || true)" =~ '^[0-9]+$' ]] || macos_die "security evidence finding count is invalid"
scanner_json="$(plutil -convert json -o - -- "$security_evidence")"
[[ "$scanner_json" =~ '"blocking_keys"[[:space:]]*:[[:space:]]*\[[[:space:]]*\]' ]] || macos_die "security evidence contains blocking findings"
scanner_checked_at="$(macos_json_get "$security_evidence" checked_at 2>/dev/null || macos_json_get "$security_evidence" checkedAt 2>/dev/null || true)"
[[ -n "$scanner_checked_at" ]] || macos_die "scanner security evidence timestamp is missing"
macos_assert_fresh_timestamp "$scanner_checked_at"

[[ -f "$image_record" ]] || macos_die "final image record is missing"
if [[ -f "$image_record.sha256" ]]; then
  macos_check_checksum "$image_record"
fi
plutil -convert json -o - -- "$image_record" >/dev/null 2>&1 || macos_die "final image record is invalid JSON"
image_record_digest="$(macos_sha256 "$image_record")"

typeset -A image_ids
typeset -A image_refs
for image_name in db backend frontend gateway; do
  image_ids[$image_name]="$(macos_json_get "$identity" "images.$image_name.id")"
  image_refs[$image_name]="$(macos_json_get "$identity" "images.$image_name.reference")"
  [[ "${image_ids[$image_name]}" =~ '^sha256:[0-9a-fA-F]{64}$' ]] || macos_die "built image identity is invalid"
done
# Provenance must already be present in the scanner/evaluator payload.  Seal
# never fills in missing image bindings, because doing so would turn an older
# generic passing report into a claim about these exact release images.
[[ "$(macos_json_get "$security_evidence" builtImageIdentitySha256 2>/dev/null || true)" == "$identity_digest" ]] || macos_die "scanner evidence is not identity-bound to this built image set"
[[ "$(macos_json_get "$security_evidence" imagePlatform 2>/dev/null || true)" == linux/arm64 ]] || macos_die "scanner evidence platform binding is invalid"
[[ "$(macos_json_get "$security_evidence" hostOS 2>/dev/null || true)" == darwin && "$(macos_json_get "$security_evidence" architecture 2>/dev/null || true)" == arm64 ]] || macos_die "scanner evidence host binding is invalid"
[[ "$(macos_json_get "$security_evidence" scannerMode 2>/dev/null || true)" == identity-bound ]] || macos_die "scanner evidence was not produced by identity-bound evaluation"
binding_json="$(plutil -convert json -o - -- "$security_evidence")"
[[ "$binding_json" =~ '"binding_errors"[[:space:]]*:[[:space:]]*\[[[:space:]]*\]' ]] || macos_die "scanner evidence contains image binding errors"
[[ "$(macos_json_get "$security_evidence" scannerEvidenceSha256 2>/dev/null || true)" =~ '^[0-9a-fA-F]{64}$' ]] || macos_die "scanner evidence lacks evaluator provenance"
[[ "$(macos_json_get "$security_evidence" imageRecordSha256 2>/dev/null || true)" == "$image_record_digest" ]] || macos_die "scanner evidence image record binding is stale"
for image_name in db backend frontend gateway; do
  [[ "$(macos_json_get "$security_evidence" "imageIds.$image_name" 2>/dev/null || true)" == "${image_ids[$image_name]}" ]] || macos_die "scanner evidence image ID binding is stale"
  [[ "$(macos_json_get "$security_evidence" "imageReferences.$image_name" 2>/dev/null || true)" == "${image_refs[$image_name]}" ]] || macos_die "scanner evidence image reference binding is stale"
done

# The image record is the scanner's final-image input.  Require all four
# records to match the immutable native image IDs from Build-ReleaseImages;
# tags or a different architecture cannot satisfy this seal.
for image_name in db backend frontend gateway; do
  found=0
  for index in 0 1 2 3 4 5 6 7; do
    record_id="$(macos_json_get "$image_record" "images.$index.id" 2>/dev/null || macos_json_get "$image_record" "$index.Id" 2>/dev/null || true)"
    [[ -n "$record_id" ]] || continue
    record_os="$(macos_json_get "$image_record" "images.$index.os" 2>/dev/null || macos_json_get "$image_record" "$index.Os" 2>/dev/null || true)"
    record_arch="$(macos_json_get "$image_record" "images.$index.architecture" 2>/dev/null || macos_json_get "$image_record" "$index.Architecture" 2>/dev/null || true)"
    record_reference="$(macos_json_get "$image_record" "images.$index.reference" 2>/dev/null || true)"
    record_tags="$(plutil -extract "$index.RepoTags" json -o - -- "$image_record" 2>/dev/null || true)"
    if [[ "$record_id" == "${image_ids[$image_name]}" && "$record_os" == linux && "$record_arch" == arm64 && ( "$record_reference" == "${image_refs[$image_name]}" || "$record_tags" == *"\"${image_refs[$image_name]}\""* ) ]]; then
      found=1
      break
    fi
  done
  (( found == 1 )) || macos_die "final scanner image record does not match built ${image_name} linux/arm64 image"
done

# Recompute the evaluator result from the retained raw evidence.  A caller
# supplied report and a self-generated .sha256 sidecar are not evidence of
# scanner authenticity; the trusted evaluator must bind every raw input to
# this exact release before any raw member is copied into it.
macos_verify_scanner_evidence \
  "$release_path" "$scanner_evidence_dir" "$security_evidence" "$identity" "$image_record" \
  "$SCRIPT_DIR/../security/evaluate_scans.py"
raw_manifest="$scanner_evidence_dir/scanner-evidence-manifest.json"
raw_manifest_digest="$(macos_sha256 "$raw_manifest")"
raw_scanner_digest="$(macos_json_get "$security_evidence" scannerEvidenceSha256)"
raw_image_manifest_digest="$(macos_sha256 "$scanner_evidence_dir/image-digests.json")"
raw_platform_support_digest="$(macos_sha256 "$scanner_evidence_dir/platform-support.json")"

security_path="$release_path/release-evidence/security-scan.json"
sealed_scanner_evidence_dir="$release_path/release-evidence/scanner-evidence"
[[ ! -e "$sealed_scanner_evidence_dir" ]] || macos_die "release already contains retained scanner evidence"
mkdir -p -- "$sealed_scanner_evidence_dir"
chmod 700 "$sealed_scanner_evidence_dir"
for scanner_member in \
  pip-audit.json npm-audit.json trivy-db.json trivy-backend.json \
  trivy-frontend.json trivy-gateway.json dispositions.json image-record.json \
  image-digests.json platform-support.json scanner-evidence-manifest.json \
  scanner-evidence-manifest.json.sha256; do
  [[ -f "$scanner_evidence_dir/$scanner_member" && ! -L "$scanner_evidence_dir/$scanner_member" ]] || macos_die "raw scanner evidence member is missing: $scanner_member"
  cp -p -- "$scanner_evidence_dir/$scanner_member" "$sealed_scanner_evidence_dir/$scanner_member"
  chmod 600 "$sealed_scanner_evidence_dir/$scanner_member"
done
temporary_security="${security_path}.sealing-$$"
cp -p -- "$security_evidence" "$temporary_security"
chmod 600 "$temporary_security"
cleanup_seal() { [[ -z "${temporary_security:-}" ]] || rm -f -- "$temporary_security"; }
trap 'cleanup_seal; macos_release_lock' EXIT
for field in sealedAt sealState; do
  plutil -remove "$field" -- "$temporary_security" >/dev/null 2>&1 || true
done
plutil -insert sealedAt -string "$(macos_now_iso)" -- "$temporary_security"
plutil -insert sealState -string sealed -- "$temporary_security"
scanner_binding="{\"path\":\"release-evidence/scanner-evidence\",\"manifestSha256\":\"$raw_manifest_digest\",\"scannerEvidenceSha256\":\"$raw_scanner_digest\",\"imageRecordSha256\":\"$image_record_digest\",\"imageManifestSha256\":\"$raw_image_manifest_digest\",\"platformSupportSha256\":\"$raw_platform_support_digest\"}"
plutil -remove scannerEvidence -- "$temporary_security" >/dev/null 2>&1 || true
plutil -insert scannerEvidence -json "$scanner_binding" -- "$temporary_security" >/dev/null 2>&1 || macos_die "unable to bind retained scanner evidence"
plutil -convert json -o - -- "$temporary_security" >/dev/null 2>&1 || macos_die "sealed security evidence is invalid JSON"
mv -f -- "$temporary_security" "$security_path"
temporary_security=""
chmod 600 "$security_path"
macos_write_checksum "$security_path"
security_digest="$(macos_sha256 "$security_path")"

# Update only the mutable release metadata fields.  The source scanner report
# digest is retained in the sealed evidence, while the manifest binds the
# resulting evidence and exact built identity to this release.
temporary_manifest="${manifest}.sealing-$$"
cleanup_seal() {
  [[ -z "${temporary_security:-}" ]] || rm -f -- "$temporary_security"
  [[ -z "${temporary_manifest:-}" ]] || rm -f -- "$temporary_manifest"
}
trap 'cleanup_seal; macos_release_lock' EXIT
cp -p -- "$manifest" "$temporary_manifest"
chmod 600 "$temporary_manifest"
plutil -replace sealState -string sealed -- "$temporary_manifest" 2>/dev/null || plutil -insert sealState -string sealed -- "$temporary_manifest"
plutil -replace sealedAt -string "$(macos_now_iso)" -- "$temporary_manifest" 2>/dev/null || plutil -insert sealedAt -string "$(macos_now_iso)" -- "$temporary_manifest"
plutil -replace securityEvidence.sha256 -string "$security_digest" -- "$temporary_manifest"
plutil -replace securityEvidence.checkedAt -string "$scanner_checked_at" -- "$temporary_manifest"
plutil -replace securityEvidence.status -string passed -- "$temporary_manifest" 2>/dev/null || plutil -insert securityEvidence.status -string passed -- "$temporary_manifest"
scanner_manifest_binding="{\"path\":\"release-evidence/scanner-evidence/scanner-evidence-manifest.json\",\"sha256\":\"$raw_manifest_digest\",\"scannerEvidenceSha256\":\"$raw_scanner_digest\",\"imageRecordSha256\":\"$image_record_digest\",\"imageManifestSha256\":\"$raw_image_manifest_digest\",\"platformSupportSha256\":\"$raw_platform_support_digest\"}"
plutil -remove scannerEvidence -- "$temporary_manifest" >/dev/null 2>&1 || true
plutil -insert scannerEvidence -json "$scanner_manifest_binding" -- "$temporary_manifest" >/dev/null 2>&1 || macos_die "unable to bind scanner evidence to release manifest"
manifest_index=0
while :; do
  relative="$(macos_json_get "$temporary_manifest" "files.$manifest_index.path" 2>/dev/null || true)"
  [[ -n "$relative" ]] || break
  (( manifest_index += 1 ))
done
for scanner_member in \
  pip-audit.json npm-audit.json trivy-db.json trivy-backend.json \
  trivy-frontend.json trivy-gateway.json dispositions.json image-record.json \
  image-digests.json platform-support.json scanner-evidence-manifest.json; do
  scanner_relative="release-evidence/scanner-evidence/$scanner_member"
  scanner_digest="$(macos_sha256 "$sealed_scanner_evidence_dir/$scanner_member")"
  scanner_row="{\"path\":\"$scanner_relative\",\"sha256\":\"$scanner_digest\"}"
  plutil -insert "files.$manifest_index" -json "$scanner_row" -- "$temporary_manifest" >/dev/null 2>&1 || macos_die "unable to add scanner evidence to release manifest"
  (( manifest_index += 1 ))
done
index=0
while :; do
  relative="$(macos_json_get "$temporary_manifest" "files.$index.path" 2>/dev/null || true)"
  [[ -n "$relative" ]] || break
  if [[ "$relative" == release-evidence/security-scan.json ]]; then
    plutil -replace "files.$index.sha256" -string "$security_digest" -- "$temporary_manifest"
    break
  fi
  (( index += 1 ))
done
plutil -convert json -o - -- "$temporary_manifest" >/dev/null 2>&1 || macos_die "sealed release manifest is invalid JSON"
mv -f -- "$temporary_manifest" "$manifest"
chmod 600 "$manifest"
macos_replace_checksum_row "$release_path/SHA256SUMS" release-evidence/security-scan.json "$security_digest"
for scanner_member in \
  pip-audit.json npm-audit.json trivy-db.json trivy-backend.json \
  trivy-frontend.json trivy-gateway.json dispositions.json image-record.json \
  image-digests.json platform-support.json scanner-evidence-manifest.json; do
  scanner_relative="release-evidence/scanner-evidence/$scanner_member"
  macos_append_checksum_row "$release_path/SHA256SUMS" "$scanner_relative" "$(macos_sha256 "$sealed_scanner_evidence_dir/$scanner_member")"
done

"$SCRIPT_DIR/Test-ReleaseBundle.zsh" --release-path "$release_path" --root "$root" --allow-signature-missing >/dev/null
macos_log "release_sealed version=$version commit=${commit:l} security=passed platform=linux/arm64 identity=$identity_digest next=Sign-ReleaseBundle"
