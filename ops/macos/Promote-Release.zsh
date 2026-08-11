#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
source "$SCRIPT_DIR/Common.zsh"

release_path=""
paired_backup_path=""
staging_evidence=""
confirmation=""
root="${INTERNAL_EXAM_ROOT:-${HOME:?}/Library/Application Support/InternalExam}"
while (( $# > 0 )); do
  case "$1" in
    --release-path|--release) (( $# >= 2 )) || macos_die "$1 requires a path"; release_path="$2"; shift 2 ;;
    --paired-backup-path|--backup) (( $# >= 2 )) || macos_die "$1 requires a path"; paired_backup_path="$2"; shift 2 ;;
    --staging-evidence) (( $# >= 2 )) || macos_die "--staging-evidence requires a path"; staging_evidence="$2"; shift 2 ;;
    --confirmation) (( $# >= 2 )) || macos_die "--confirmation requires exact text"; confirmation="$2"; shift 2 ;;
    --root) (( $# >= 2 )) || macos_die "--root requires a path"; root="$2"; shift 2 ;;
    -h|--help) print -r -- "usage: $0 --release-path PATH --paired-backup-path PATH --staging-evidence PATH --confirmation 'PROMOTE VERSION' [--root ROOT]"; exit 0 ;;
    *) macos_die "unknown argument: $1"; exit 1 ;;
  esac
done

macos_assert_macos
[[ -n "$release_path" && -n "$paired_backup_path" && -n "$staging_evidence" && -n "$confirmation" ]] || macos_die "release, backup, staging evidence, and confirmation are required"
macos_assert_outside_worktree "$root" >/dev/null
macos_layout "$root"
macos_assert_protected_configuration "$root"
macos_require_formal_paths
macos_docker_ready
macos_acquire_lock "$MACOS_LAYOUT_STATE/.operation.lock"
trap 'macos_release_lock' EXIT

release_path="$(macos_resolve_path "$release_path")"
paired_backup_path="$(macos_assert_backup "$paired_backup_path")"
staging_evidence="$(macos_resolve_path "$staging_evidence")"
[[ -f "$release_path/release-manifest.json" ]] || macos_die "release manifest is missing"
[[ -f "$staging_evidence" ]] || macos_die "staging evidence is missing"
"$SCRIPT_DIR/Test-ReleaseBundle.zsh" --release-path "$release_path" >/dev/null
macos_verify_built_image_identity "$release_path"
macos_check_checksum "$staging_evidence"
plutil -convert json -o - -- "$staging_evidence" >/dev/null 2>&1 || macos_die "staging evidence is invalid"

manifest="$release_path/release-manifest.json"
version="$(macos_json_get "$manifest" applicationVersion)"
commit="$(macos_json_get "$manifest" gitCommit)"
[[ "$confirmation" == "PROMOTE $version" ]] || macos_die "exact promotion confirmation did not match"
staging_status="$(macos_json_get "$staging_evidence" status 2>/dev/null || true)"
staging_commit="$(macos_json_get "$staging_evidence" commit 2>/dev/null || macos_json_get "$staging_evidence" gitCommit 2>/dev/null || true)"
[[ "$(macos_json_get "$staging_evidence" kind 2>/dev/null || true)" == staging-acceptance && "$staging_status" == passed && "${staging_commit:l}" == "${commit:l}" ]] || macos_die "staging evidence is not a verified acceptance for the release"
[[ "$(macos_json_get "$staging_evidence" hostOS 2>/dev/null || true)" == darwin && "$(macos_json_get "$staging_evidence" architecture 2>/dev/null || true)" == arm64 && "$(macos_json_get "$staging_evidence" platform 2>/dev/null || true)" == linux/arm64 ]] || macos_die "staging evidence platform identity is invalid"
staging_checked_at="$(macos_json_get "$staging_evidence" checkedAt 2>/dev/null || macos_json_get "$staging_evidence" checked_at 2>/dev/null || true)"
macos_assert_fresh_timestamp "$staging_checked_at"
[[ "$(macos_json_get "$staging_evidence" builtImageIdentitySha256 2>/dev/null || true)" == "$(macos_sha256 "$release_path/ops/release/built-image-identity.json")" ]] || macos_die "staging evidence image identity is stale"
for gate in browser smtp capacity restart route security; do
  [[ "$(macos_json_get "$staging_evidence" "gates.$gate" 2>/dev/null || true)" == passed ]] || macos_die "staging acceptance gate is missing or failed"
done
[[ -f "$MACOS_CURRENT_STATE" ]] || macos_die "promotion requires an existing current formal release"
macos_release_state "$MACOS_CURRENT_STATE"
current_release_version="$MACOS_STATE_VERSION"
macos_cutover_identity
if [[ "$(macos_json_get "$MACOS_LAYOUT_STATE/host-identity.json" lineageState 2>/dev/null || true)" == unbound ]]; then
  # An existing formal/current state is the one safe first-writer bootstrap
  # boundary.  Bind it atomically now; an unbound identity is never allowed to
  # be rebound later to an unrelated dataset.
  macos_adopt_cutover_identity "$MACOS_DATASET_ID" "$MACOS_HOST_ID" "$MACOS_WRITER_GENERATION"
fi
# Promotion is a public lifecycle start, not a cutover recovery mechanism.
# Refuse it while this host is retired as an outgoing source or waiting as an
# inbound target; maintenance-only Accept/Resume owns those transitions.
macos_assert_no_pending_cutover_start 0
backup_manifest="$paired_backup_path/manifest.json"
[[ -f "$backup_manifest" ]] || macos_die "paired backup manifest is missing"
plutil -convert json -o - -- "$backup_manifest" >/dev/null 2>&1 || macos_die "paired backup manifest is invalid"
[[ "$(macos_json_get "$backup_manifest" backup_kind 2>/dev/null || true)" == pre-upgrade ]] || macos_die "promotion requires a pre-upgrade backup"
[[ "$(macos_json_get "$backup_manifest" application_version 2>/dev/null || true)" == "$current_release_version" ]] || macos_die "pre-upgrade backup belongs to another release"
[[ "$(macos_json_get "$backup_manifest" dataset_id 2>/dev/null || true)" == "$MACOS_DATASET_ID" ]] || macos_die "pre-upgrade backup dataset identity is invalid"
[[ "$(macos_json_get "$backup_manifest" source_host_id 2>/dev/null || true)" == "$MACOS_HOST_ID" ]] || macos_die "pre-upgrade backup host identity is invalid"
[[ "$(macos_json_get "$backup_manifest" writer_generation 2>/dev/null || true)" == "$MACOS_WRITER_GENERATION" ]] || macos_die "pre-upgrade backup writer generation is invalid"
second_copy_evidence="$paired_backup_path:h/${paired_backup_path:t}.second-copy.json"
[[ -f "$second_copy_evidence" ]] || macos_die "promotion requires verified second-copy evidence"
macos_check_checksum "$second_copy_evidence"
[[ "$(macos_json_get "$second_copy_evidence" status 2>/dev/null || true)" == passed ]] || macos_die "second-copy evidence is not passed"
release_path_json="$(macos_json_escape "$release_path")"
paired_backup_json="$(macos_json_escape "$paired_backup_path")"
staging_evidence_json="$(macos_json_escape "$staging_evidence")"

# Validate the portable input inside the selected backend image before any
# formal Compose command can mutate a volume.
macos_compose_base "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT"
macos_run_checked docker "${MACOS_COMPOSE_ARGS[@]}" run --rm --no-deps \
  --volume "$paired_backup_path:/portable-backup:ro" backend \
  uv run --no-sync python -m app.ops.host_portability validate-migration-input /portable-backup

if [[ -f "$MACOS_CURRENT_STATE" ]]; then
  macos_secure_path "$MACOS_CURRENT_STATE"
  current_state_json="$(cat -- "$MACOS_CURRENT_STATE")"
  macos_write_atomic "$MACOS_PREVIOUS_STATE" "$current_state_json"
fi

macos_save_environment APP_VERSION_TAG APP_VERSION GIT_COMMIT
trap 'macos_restore_environment; macos_release_lock' EXIT
export APP_VERSION_TAG="${commit:l}"
export APP_VERSION="$version"
export GIT_COMMIT="${commit:l}"
state_json="{\"schemaVersion\":1,\"applicationVersion\":\"$version\",\"gitCommit\":\"${commit:l}\",\"path\":\"$release_path_json\",\"promotedAt\":\"$(macos_now_iso)\",\"pairedBackupPath\":\"$paired_backup_json\",\"stagingEvidence\":\"$staging_evidence_json\",\"datasetId\":\"$MACOS_DATASET_ID\",\"hostId\":\"$MACOS_HOST_ID\",\"writerGeneration\":$MACOS_WRITER_GENERATION}"
macos_write_atomic "$MACOS_CURRENT_STATE" "$state_json"
macos_write_checksum "$MACOS_CURRENT_STATE"
MACOS_PARENT_LOCK_PID="$$" "$SCRIPT_DIR/Start-Platform.zsh" --root "$root" --lock-held >/dev/null
migration="$(macos_compose_capture "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" exec -T backend uv run --no-sync alembic current)"
[[ -n "$migration" ]] || macos_die "formal migration identity is unavailable"
macos_write_evidence "$MACOS_LAYOUT_EVIDENCE" promotion \
  "{\"schemaVersion\":1,\"kind\":\"promotion\",\"status\":\"passed\",\"version\":\"$version\",\"commit\":\"${commit:l}\",\"pairedBackup\":\"${paired_backup_path:t}\",\"secrets\":\"redacted\"}" >/dev/null
macos_log "promoted version=$version commit=${commit:l} project=$MACOS_FORMAL_PROJECT"
