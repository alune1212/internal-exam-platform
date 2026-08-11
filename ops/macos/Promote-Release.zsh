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
macos_read_cutover_identity
macos_require_formal_paths
macos_docker_ready
macos_acquire_lock "$MACOS_LAYOUT_STATE/.operation.lock"
macos_save_environment APP_IMAGE_REPOSITORY APP_VERSION_TAG APP_VERSION GIT_COMMIT
cleanup_promotion() {
  local exit_status=$?
  macos_restore_environment
  macos_release_lock
  return "$exit_status"
}
trap cleanup_promotion EXIT

release_path="$(macos_resolve_path "$release_path")"
paired_backup_path="$(macos_assert_backup "$paired_backup_path")"
staging_evidence="$(macos_resolve_path "$staging_evidence")"
second_copy_root="$(macos_formal_value SECOND_COPY_PATH)"
second_copy_root="$(macos_resolve_path "$second_copy_root")"
macos_assert_second_copy_storage "$second_copy_root"
[[ "$paired_backup_path:h" == "$MACOS_LAYOUT_BACKUPS" ]] || macos_die "paired backup must be a direct child of the protected local backup directory"
[[ "$paired_backup_path:t" == backup-* ]] || macos_die "paired backup basename is invalid"
second_copy_backup_path="$second_copy_root/${paired_backup_path:t}"
[[ "$second_copy_backup_path:h" == "$second_copy_root" ]] || macos_die "second-copy backup path must be a direct child of verified second-copy storage"
[[ -d "$second_copy_backup_path" && ! -L "$second_copy_backup_path" ]] || macos_die "paired backup is missing from verified second-copy storage"
[[ -f "$release_path/release-manifest.json" ]] || macos_die "release manifest is missing"
[[ -f "$staging_evidence" ]] || macos_die "staging evidence is missing"
[[ "$release_path:h" == "$MACOS_LAYOUT_RELEASES" ]] || macos_die "promotion requires an installed release under ROOT/releases/<version>"
[[ "$staging_evidence" == "$MACOS_LAYOUT_ROOT"/* ]] || macos_die "staging evidence must remain under the protected root"
"$SCRIPT_DIR/Test-ReleaseBundle.zsh" --release-path "$release_path" >/dev/null
macos_verify_built_image_identity "$release_path"

manifest="$release_path/release-manifest.json"
version="$(macos_json_get "$manifest" applicationVersion)"
commit="$(macos_json_get "$manifest" gitCommit)"
[[ "$confirmation" == "PROMOTE $version" ]] || macos_die "exact promotion confirmation did not match"
lower_commit="${commit:l}"
short_commit="${lower_commit[1,12]}"
export APP_VERSION_TAG="$lower_commit"
export APP_VERSION="$version"
export GIT_COMMIT="$lower_commit"
backend_reference="$(macos_json_get "$release_path/ops/release/built-image-identity.json" images.backend.reference)"
local_backup_sums_sha256="$(macos_sha256 "$paired_backup_path/SHA256SUMS")"
second_copy_sums_sha256="$(macos_sha256 "$second_copy_backup_path/SHA256SUMS")"
[[ "$local_backup_sums_sha256" == "$second_copy_sums_sha256" ]] || macos_die "second-copy backup checksum manifest does not match local paired backup"
macos_run_checked docker run --rm \
  --volume "$second_copy_backup_path:/portable-backup:ro" "$backend_reference" \
  uv run --no-sync python -m app.ops.internal_backup inspect /portable-backup
staging_project="internal-exam-staging-${short_commit}"
staging_host_root="$MACOS_LAYOUT_ROOT/staging/$short_commit"
staging_evidence_dir="$staging_host_root/evidence"
staging_live_image_ids=""
if [[ -d "$staging_evidence_dir" ]]; then
  running_services="$(macos_compose_capture "$release_path" "$MACOS_STAGING_ENV" "$staging_project" ps --status running --services 2>/dev/null || true)"
  staging_running=1
  for service in db backend auto-submit-worker frontend nginx operator-nginx; do
    print -r -- "$running_services" | grep -Fx -- "$service" >/dev/null || staging_running=0
  done
  if (( staging_running == 1 )); then
    staging_live_image_ids="$staging_evidence_dir/live-images-promote-${$}-${RANDOM}.json"
    macos_compose_base "$release_path" "$MACOS_STAGING_ENV" "$staging_project"
    macos_run_to_file "$staging_live_image_ids" docker "${MACOS_COMPOSE_ARGS[@]}" images --format json
    macos_write_checksum "$staging_live_image_ids"
    macos_check_checksum "$staging_live_image_ids"
  fi
fi

# The canonical kind is staging-acceptance (schemaVersion 2); promotion never
# trusts its top-level flags. Re-run the selected
# backend image's validator against the canonical record, all relative raw
# artifact references/digests, the sealed release security record, and a fresh
# live Compose image capture when the staging project is still running.  After
# an explicit Down, the validator instead rechecks the durable checksummed
# live-image artifact preserved beside the canonical bundle; promotion does
# not restart staging implicitly.
container_root_path() {
  local value="$1"
  [[ "$value" == "$MACOS_LAYOUT_ROOT"/* ]] || macos_die "promotion evidence path is outside the protected root"
  print -r -- "/protected/${value#$MACOS_LAYOUT_ROOT/}"
}
typeset -a validator_args
validator_args=(
  run --rm
  --volume "$MACOS_LAYOUT_ROOT:/protected:ro"
  "$backend_reference"
  uv run --no-sync python -m app.ops.staging_acceptance validate
  --root /protected
  --release "$(container_root_path "$release_path")"
  --canonical "$(container_root_path "$staging_evidence")"
  --expected-host-id "$MACOS_HOST_ID"
)
if [[ -n "$staging_live_image_ids" ]]; then
  validator_args+=(--live-image-ids "$(container_root_path "$staging_live_image_ids")")
fi
macos_run_checked docker "${validator_args[@]}"
macos_check_checksum "$staging_evidence"
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
[[ "$(macos_json_get "$second_copy_evidence" artifact_id 2>/dev/null || macos_json_get "$second_copy_evidence" artifactId 2>/dev/null || true)" == "${paired_backup_path:t}" ]] || macos_die "second-copy evidence artifact identity does not match the paired backup basename"
[[ "$(macos_json_get "$second_copy_evidence" backup_id 2>/dev/null || macos_json_get "$second_copy_evidence" backupId 2>/dev/null || true)" == "${paired_backup_path:t}" ]] || macos_die "second-copy evidence backup identity does not match the paired backup basename"
paired_migration_head="$(macos_json_get "$backup_manifest" migration_head 2>/dev/null || macos_json_get "$backup_manifest" migrationHead 2>/dev/null || true)"
release_migration_head="$(macos_json_get "$manifest" migrationHead 2>/dev/null || macos_json_get "$manifest" migration_head 2>/dev/null || true)"
[[ -n "$paired_migration_head" && "$paired_migration_head" == "$release_migration_head" ]] || macos_die "paired backup migration head is not bound to the release manifest"
release_path_json="$(macos_json_escape "$release_path")"
paired_backup_json="$(macos_json_escape "$paired_backup_path")"
staging_evidence_json="$(macos_json_escape "$staging_evidence")"

# Validate the portable input inside the exact selected backend image before
# any formal Compose command can mutate a volume.  A direct ``docker run``
# intentionally mounts only the backup, so this check cannot create or open a
# formal named volume.
macos_run_checked docker run --rm \
  --volume "$paired_backup_path:/portable-backup:ro" "$backend_reference" \
  uv run --no-sync python -m app.ops.host_portability validate-migration-input /portable-backup

if [[ -f "$MACOS_CURRENT_STATE" ]]; then
  macos_secure_path "$MACOS_CURRENT_STATE"
  current_state_json="$(cat -- "$MACOS_CURRENT_STATE")"
  macos_write_atomic "$MACOS_PREVIOUS_STATE" "$current_state_json"
fi

state_json="{\"schemaVersion\":1,\"kind\":\"formal-writer-current\",\"applicationVersion\":\"$version\",\"gitCommit\":\"${commit:l}\",\"path\":\"$release_path_json\",\"promotedAt\":\"$(macos_now_iso)\",\"pairedBackupPath\":\"$paired_backup_json\",\"stagingEvidence\":\"$staging_evidence_json\",\"datasetId\":\"$MACOS_DATASET_ID\",\"hostId\":\"$MACOS_HOST_ID\",\"writerGeneration\":$MACOS_WRITER_GENERATION,\"bootstrapPending\":false,\"activationReady\":true}"
macos_write_atomic "$MACOS_CURRENT_STATE" "$state_json"
macos_write_checksum "$MACOS_CURRENT_STATE"
MACOS_PARENT_LOCK_PID="$$" "$SCRIPT_DIR/Start-Platform.zsh" --root "$root" --lock-held >/dev/null
migration="$(macos_compose_capture "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" exec -T backend uv run --no-sync alembic current)"
[[ -n "$migration" ]] || macos_die "formal migration identity is unavailable"
macos_write_evidence "$MACOS_LAYOUT_EVIDENCE" promotion \
  "{\"schemaVersion\":1,\"kind\":\"promotion\",\"status\":\"passed\",\"version\":\"$version\",\"commit\":\"${commit:l}\",\"pairedBackup\":\"${paired_backup_path:t}\",\"secrets\":\"redacted\"}" >/dev/null
macos_log "promoted version=$version commit=${commit:l} project=$MACOS_FORMAL_PROJECT"
