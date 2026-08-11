#!/bin/zsh
set -euo pipefail
setopt no_nomatch
umask 077

SCRIPT_DIR="${0:A:h}"
source "$SCRIPT_DIR/Common.zsh"

release_path=""
output_dir=""
trivy_image=""
node_image=""
typeset -r MACOS_TRIVY_IMAGE="aquasec/trivy@sha256:be1190afcb28352bfddc4ddeb71470835d16462af68d310f9f4bca710961a41e"
root="${INTERNAL_EXAM_ROOT:-${HOME:?}/Library/Application Support/InternalExam}"
while (( $# > 0 )); do
  case "$1" in
    --release-path|--release) (( $# >= 2 )) || macos_die "$1 requires a path"; release_path="$2"; shift 2 ;;
    --output-dir|--output) (( $# >= 2 )) || macos_die "$1 requires a path"; output_dir="$2"; shift 2 ;;
    --trivy-image) (( $# >= 2 )) || macos_die "$1 requires the versioned scanner image"; trivy_image="$2"; shift 2 ;;
    --node-image) (( $# >= 2 )) || macos_die "$1 requires the release-pinned builder image"; node_image="$2"; shift 2 ;;
    --root) (( $# >= 2 )) || macos_die "$1 requires a path"; root="$2"; shift 2 ;;
    -h|--help)
      print -r -- "usage: $0 --release-path BUILT_RELEASE --output-dir EVIDENCE_DIR [--trivy-image $MACOS_TRIVY_IMAGE] [--node-image RELEASE_FRONTEND_BUILDER] [--root ROOT]"
      exit 0
      ;;
    *) macos_die "unknown argument: $1"; exit 1 ;;
  esac
done

macos_assert_macos
[[ -n "$release_path" && -n "$output_dir" ]] || macos_die "release and output are required"
[[ -n "$trivy_image" ]] || trivy_image="$MACOS_TRIVY_IMAGE"
[[ "$trivy_image" == "$MACOS_TRIVY_IMAGE" ]] || macos_die "Trivy scanner image is not on the versioned allowlist"
[[ "$(uname -m)" == arm64 ]] || macos_die "native ARM64 security scan is required"
macos_assert_outside_worktree "$root" >/dev/null
macos_layout "$root"
macos_assert_protected_configuration "$root"
macos_docker_ready
release_path="$(macos_resolve_path "$release_path")"
output_dir="$(macos_resolve_path "$output_dir")"
[[ -d "$release_path" ]] || macos_die "release directory is missing"
[[ -n "$node_image" ]] || node_image="$(macos_json_get "$release_path/ops/release/image-digests.json" frontend_builder 2>/dev/null || true)"
[[ -n "$node_image" && "$node_image" == "$(macos_json_get "$release_path/ops/release/image-digests.json" frontend_builder 2>/dev/null || true)" ]] || macos_die "Node scanner image must be the release-pinned frontend builder"
[[ "$node_image" =~ '^[a-z0-9][a-z0-9._/-]{0,254}(:[A-Za-z0-9_][A-Za-z0-9._-]{0,127})?@sha256:[0-9a-fA-F]{64}$' ]] || macos_die "Node scanner image must be immutable"
[[ "$output_dir" != "$release_path"/* ]] || macos_die "security output cannot be inside the release bundle"
mkdir -p -- "$output_dir"
chmod 700 "$output_dir"
"$SCRIPT_DIR/Test-ReleaseBundle.zsh" --release-path "$release_path" --allow-unsealed >/dev/null
macos_verify_built_image_identity "$release_path"

manifest="$release_path/release-manifest.json"
commit="$(macos_json_get "$manifest" gitCommit)"
identity="$release_path/ops/release/built-image-identity.json"
backend_ref="$(macos_json_get "$identity" images.backend.reference)"
[[ "$backend_ref" == *":${commit:l}" ]] || macos_die "security scan backend image does not match release commit"
work="$(mktemp -d /private/tmp/internal-exam-security-scan.XXXXXX)"
chmod 700 "$work"
trivy_cache="$work/trivy-cache"
mkdir -p -- "$trivy_cache"
chmod 700 "$trivy_cache"
cleanup_scan() { [[ -z "${work:-}" ]] || rm -R -- "$work"; }
trap cleanup_scan EXIT

typeset -A image_refs
for image_name in db backend frontend gateway; do
  image_refs[$image_name]="$(macos_json_get "$identity" "images.$image_name.reference")"
  [[ "${image_refs[$image_name]}" == *":${commit:l}" ]] || macos_die "security scan image reference is not commit-bound"
done
# Keep the complete Docker inspect output private to the temporary directory.
# Formal evidence contains only the identity allowlist consumed by the
# evaluator (reference, immutable ID, OS, and architecture).
canonical_images=""
for image_name in db backend frontend gateway; do
  image_ref="${image_refs[$image_name]}"
  expected_id="$(macos_json_get "$identity" "images.$image_name.id")"
  inspect_line="$(macos_run_capture docker image inspect --format '{{.Id}}|{{.Os}}|{{.Architecture}}' "$image_ref")"
  [[ "$inspect_line" != *$'\n'* && "$inspect_line" != *$'\r'* ]] || macos_die "built image inspect output contains multiple lines"
  separator_count="${inspect_line//[^|]/}"
  [[ "${#separator_count}" -eq 2 ]] || macos_die "built image inspect output is malformed"
  IFS='|' read -r actual_id actual_os actual_architecture extra <<< "$inspect_line"
  [[ -n "$actual_id" && -n "$actual_os" && -n "$actual_architecture" && -z "${extra:-}" ]] || macos_die "built image inspect output is malformed"
  [[ "$actual_id" == "$expected_id" && "$actual_os" == linux && "$actual_architecture" == arm64 ]] || macos_die "built image inspect identity is not native ARM64"
  escaped_ref="$(macos_json_escape "$image_ref")"
  escaped_id="$(macos_json_escape "$actual_id")"
  canonical_row="{\"reference\":\"$escaped_ref\",\"id\":\"$escaped_id\",\"os\":\"linux\",\"architecture\":\"arm64\"}"
  if [[ -n "$canonical_images" ]]; then canonical_images+=","; fi
  canonical_images+="$canonical_row"
done
canonical_json="{\"schemaVersion\":1,\"images\":[$canonical_images]}"
macos_write_atomic "$work/canonical-images.json" "$canonical_json"
macos_checksummed_json "$work/canonical-images.json"
macos_run_to_file "$work/final-images.json" docker image inspect \
  "${image_refs[db]}" "${image_refs[backend]}" "${image_refs[frontend]}" "${image_refs[gateway]}"
macos_write_checksum "$work/final-images.json"

# Trivy reads the exact local image IDs through the Docker socket; it does not
# rebuild a mutable tag.  The scanner reference itself must be digest pinned.
for image_name in db backend frontend gateway; do
  macos_run_checked docker run --rm --platform linux/arm64 \
    --volume /var/run/docker.sock:/var/run/docker.sock \
    --volume "$work:/evidence" "$trivy_image" image --exit-code 0 --format json \
    --cache-dir /evidence/trivy-cache \
    --output "/evidence/trivy-${image_name}.json" "${image_refs[$image_name]}"
done

# Dependency scans run inside pinned/containerized runtimes; the macOS host
# never needs Python, Node, npm, or PostgreSQL for release security evidence.
macos_run_checked docker run --rm --platform linux/arm64 \
  --volume "$release_path:/workspace:ro" --volume "$work:/evidence" "$backend_ref" \
  sh -c 'uv export --project /workspace/backend --frozen --no-dev --format requirements-txt --output-file /evidence/python-requirements.txt && uvx --from pip-audit==2.9.0 pip-audit --disable-pip --require-hashes --requirement /evidence/python-requirements.txt --format json --output /evidence/pip-audit.json || test -s /evidence/pip-audit.json'
macos_run_checked docker run --rm --platform linux/arm64 \
  --volume "$release_path/frontend:/workspace:ro" --volume "$work:/evidence" "$node_image" \
  sh -c 'cd /workspace && npm audit --omit=dev --json > /evidence/npm-audit.json || test -s /evidence/npm-audit.json'

# Run the checked-in evaluator inside the selected release backend image in
# identity mode.  It must emit the binding fields itself; this adapter never
# adds image IDs or a false empty binding-error list after the fact.
evaluator_output="$work/evaluator-output.json"
evaluator_error="$work/evaluator-error.txt"
if docker run --rm --platform linux/arm64 \
  --volume "$release_path:/workspace:ro" --volume "$work:/evidence" "$backend_ref" \
  uv run --no-sync python /workspace/ops/security/evaluate_scans.py \
  --repository /workspace \
  --pip-audit /evidence/pip-audit.json --npm-audit /evidence/npm-audit.json \
  --trivy /evidence/trivy-db.json --trivy /evidence/trivy-backend.json \
  --trivy /evidence/trivy-frontend.json --trivy /evidence/trivy-gateway.json \
  --dispositions /workspace/ops/security/dispositions.json \
  --image-record /evidence/canonical-images.json \
  --built-image-identity /workspace/ops/release/built-image-identity.json \
  --host-os darwin --host-architecture arm64 \
  --output-dir /evidence > "$evaluator_output" 2> "$evaluator_error"; then
  evaluator_status=0
else
  evaluator_status=$?
fi
chmod 600 "$evaluator_output" "$evaluator_error"

preserve_failed_scan() {
  local failure_dir="$output_dir/security-failed-$(macos_timestamp)-$$"
  mkdir -p -- "$failure_dir"
  chmod 700 "$failure_dir"
  local failed_report
  for failed_report in "$work"/security-scan-*.json(N); do
    cp -p -- "$failed_report" "$failure_dir/${failed_report:t}"
    [[ -f "$failed_report.sha256" ]] && cp -p -- "$failed_report.sha256" "$failure_dir/${failed_report:t}.sha256"
  done
  if [[ -f "$evaluator_error" ]]; then
    macos_redact_file "$evaluator_error" "$failure_dir/evaluator-error.txt"
  else
    macos_write_atomic "$failure_dir/evaluator-error.txt" "scanner did not reach the evaluator"
  fi
  failure_json="{\"schemaVersion\":1,\"kind\":\"release-security-scan-failure\",\"status\":\"failed\",\"exitCode\":${evaluator_status:-1},\"commit\":\"$(macos_json_escape "${commit:l}")\",\"platform\":\"linux/arm64\",\"secrets\":\"redacted\"}"
  macos_write_atomic "$failure_dir/failure.json" "$failure_json"
  macos_checksummed_json "$failure_dir/failure.json"
  chmod 600 "$failure_dir"/*
  print -r -- "$failure_dir"
}
if (( evaluator_status != 0 )); then
  failure_dir="$(preserve_failed_scan)"
  macos_die "security evaluator failed; checksummed failure evidence retained at ${failure_dir:t}"
fi

security_report=""
for candidate in "$work"/security-scan-*.json(N); do security_report="$candidate"; break; done
[[ -n "$security_report" && -f "$security_report" ]] || macos_die "security evaluator did not produce a report"
macos_check_checksum "$security_report"
[[ "$(macos_json_get "$security_report" status 2>/dev/null || true)" == passed ]] || { failure_dir="$(preserve_failed_scan)"; macos_die "security evaluator did not pass release policy; failure evidence retained at ${failure_dir:t}"; }
[[ "$(macos_json_get "$security_report" builtImageIdentitySha256 2>/dev/null || true)" == "$(macos_sha256 "$identity")" ]] || macos_die "security evaluator did not bind the built image identity"
[[ "$(macos_json_get "$security_report" imagePlatform 2>/dev/null || true)" == linux/arm64 && "$(macos_json_get "$security_report" scannerMode 2>/dev/null || true)" == identity-bound ]] || macos_die "security evaluator did not emit native identity mode"
security_json="$(plutil -convert json -o - -- "$security_report")"
[[ "$security_json" =~ '"binding_errors"[[:space:]]*:[[:space:]]*\[[[:space:]]*\]' ]] || macos_die "security evaluator emitted image binding errors"
image_record_digest="$(macos_sha256 "$work/canonical-images.json")"
[[ "$(macos_json_get "$security_report" imageRecordSha256 2>/dev/null || true)" == "$image_record_digest" ]] || macos_die "security evaluator image record binding is stale"
for image_name in db backend frontend gateway; do
  image_id="$(macos_json_get "$identity" "images.$image_name.id")"
  image_ref="${image_refs[$image_name]}"
  [[ "$(macos_json_get "$security_report" "imageIds.$image_name" 2>/dev/null || true)" == "$image_id" ]] || macos_die "security evaluator image ID binding is stale"
  [[ "$(macos_json_get "$security_report" "imageReferences.$image_name" 2>/dev/null || true)" == "$image_ref" ]] || macos_die "security evaluator image reference binding is stale"
done

timestamp="$(macos_timestamp)"
final_report="$output_dir/security-scan-${timestamp}.json"
cp -p -- "$security_report" "$final_report"
chmod 600 "$final_report"
macos_write_checksum "$final_report"
final_record="$output_dir/canonical-images-${timestamp}.json"
cp -p -- "$work/canonical-images.json" "$final_record"
chmod 600 "$final_record"
macos_write_checksum "$final_record"
macos_log "release_security_scan status=passed commit=${commit:l} platform=linux/arm64 report=${final_report:t} image_record=${final_record:t} next=Seal-Release"
