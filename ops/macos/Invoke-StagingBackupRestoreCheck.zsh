#!/bin/zsh
set -euo pipefail
setopt no_nomatch
umask 077

# Produce the schema-2 backupRestore gate for one live staging run.  This is a
# disposable restore-smoke only: it never points Compose at the formal
# project/volumes and it writes the raw record only after every probe and
# cleanup step passed.  The selected release backend creates and validates the
# portable five-artifact bundle; the host adapter only binds paths, identities,
# and the isolated Compose project.

SCRIPT_DIR="${0:A:h}"
source "$SCRIPT_DIR/Common.zsh"

release_path_arg=""
run_identity_arg=""
second_copy_root_arg=""
output_arg=""
root="${INTERNAL_EXAM_ROOT:-${HOME:?}/Library/Application Support/InternalExam}"

while (( $# > 0 )); do
  case "$1" in
    --release-path|--release) (( $# >= 2 )) || macos_die "$1 requires a path"; release_path_arg="$2"; shift 2 ;;
    --run-identity|--run-evidence) (( $# >= 2 )) || macos_die "$1 requires a path"; run_identity_arg="$2"; shift 2 ;;
    --second-copy-root|--second-copy) (( $# >= 2 )) || macos_die "$1 requires a path"; second_copy_root_arg="$2"; shift 2 ;;
    --output|--backup-restore-evidence) (( $# >= 2 )) || macos_die "$1 requires a path"; output_arg="$2"; shift 2 ;;
    --root) (( $# >= 2 )) || macos_die "--root requires a path"; root="$2"; shift 2 ;;
    -h|--help)
      print -r -- "usage: $0 --release-path INSTALLED_RELEASE --run-identity PATH --second-copy-root ENCRYPTED_SECOND_COPY --output RAW_EVIDENCE [--root ROOT]"
      print -r -- "Creates a real disposable restore-smoke backup bound to the live staging run; no formal project or volume is touched."
      exit 0
      ;;
    *) macos_die "unknown argument: $1"; exit 1 ;;
  esac
done

macos_assert_macos
[[ -n "$release_path_arg" && -n "$run_identity_arg" && -n "$second_copy_root_arg" && -n "$output_arg" ]] || macos_die "release, run identity, second-copy root, and output are required"
macos_assert_outside_worktree "$root" >/dev/null
macos_layout "$root"
macos_assert_protected_configuration "$root"
macos_read_cutover_identity
macos_docker_ready

release_path="$(macos_resolve_path "$release_path_arg")"
[[ -d "$release_path" && "$release_path:h" == "$MACOS_LAYOUT_RELEASES" ]] || macos_die "backup restore check requires an installed release under ROOT/releases/<version>"
version="${release_path:t}"
[[ "$version" =~ '^[0-9]+\.[0-9]+\.[0-9]+([.-][0-9A-Za-z.-]+)?$' ]] || macos_die "installed release version is invalid"
"$SCRIPT_DIR/Test-ReleaseBundle.zsh" --release-path "$release_path" >/dev/null
macos_verify_built_image_identity "$release_path"
manifest="$release_path/release-manifest.json"
git_commit="$(macos_json_get "$manifest" gitCommit)"
application_version="$(macos_json_get "$manifest" applicationVersion)"
migration_head="$(macos_json_get "$manifest" migrationHead 2>/dev/null || macos_json_get "$manifest" migration_head 2>/dev/null || true)"
[[ "$git_commit" =~ '^[0-9a-fA-F]{40}$' && -n "$application_version" && -n "$migration_head" ]] || macos_die "release manifest identity is incomplete"
lower_commit="${git_commit:l}"
short_commit="${lower_commit[1,12]}"
staging_project="internal-exam-staging-${short_commit}"
macos_assert_project_name staging "$staging_project"

staging_host_root="$MACOS_LAYOUT_ROOT/staging/$short_commit"
staging_lifecycle="$staging_host_root/lifecycle"
staging_backup="$staging_host_root/backups"
staging_evidence="$staging_host_root/evidence"
run_identity="$(macos_resolve_path "$run_identity_arg")"
output_path="$(macos_resolve_path "$output_arg")"
second_copy_root="$(macos_resolve_path "$second_copy_root_arg")"
[[ "$run_identity" == "$staging_evidence"/* && -f "$run_identity" ]] || macos_die "run identity must belong to this commit-scoped staging evidence directory"
[[ "$output_path" == "$staging_evidence"/* ]] || macos_die "backupRestore output must remain in the staging evidence directory"
[[ ! -e "$output_path" && ! -e "$output_path.sha256" ]] || macos_die "backupRestore output already exists; refusing to overwrite evidence"
macos_secure_path "$run_identity"
macos_check_checksum "$run_identity"
macos_assert_outside_worktree "$second_copy_root" >/dev/null
macos_assert_second_copy_storage "$second_copy_root"
second_copy_storage_evidence="$MACOS_LAYOUT_EVIDENCE/second-copy-storage.json"
macos_check_checksum "$second_copy_storage_evidence"
second_copy_storage_evidence_sha256="$(macos_sha256 "$second_copy_storage_evidence")"

run_kind="$(macos_json_get "$run_identity" kind 2>/dev/null || true)"
run_status="$(macos_json_get "$run_identity" status 2>/dev/null || true)"
run_id="$(macos_json_get "$run_identity" runId 2>/dev/null || true)"
run_commit="$(macos_json_get "$run_identity" commit 2>/dev/null || true)"
run_project="$(macos_json_get "$run_identity" project 2>/dev/null || true)"
run_host="$(macos_json_get "$run_identity" hostId 2>/dev/null || true)"
run_image_digest="$(macos_json_get "$run_identity" builtImageIdentitySha256 2>/dev/null || true)"
run_started_at="$(macos_json_get "$run_identity" startedAt 2>/dev/null || macos_json_get "$run_identity" started_at 2>/dev/null || true)"
identity_path="$release_path/ops/release/built-image-identity.json"
identity_digest="$(macos_sha256 "$identity_path")"
[[ "$run_kind" == staging-run && "$run_status" == started && "$run_id" =~ '^[A-Za-z0-9][A-Za-z0-9._:-]{7,127}$' ]] || macos_die "staging run identity envelope is invalid"
[[ "$run_commit" == "$lower_commit" && "$run_project" == "$staging_project" && "$run_host" == "$MACOS_HOST_ID" && "$run_image_digest" == "$identity_digest" ]] || macos_die "staging run identity is not bound to this release/project/host/image"
[[ "$(macos_json_get "$run_identity" hostOS 2>/dev/null || true)" == darwin && "$(macos_json_get "$run_identity" architecture 2>/dev/null || true)" == arm64 && "$(macos_json_get "$run_identity" platform 2>/dev/null || true)" == linux/arm64 ]] || macos_die "staging run platform identity is invalid"
macos_assert_fresh_timestamp "$run_started_at"

for service in db backend auto-submit-worker frontend nginx operator-nginx; do
  : "$service"
done
running_services="$(macos_compose_capture "$release_path" "$MACOS_STAGING_ENV" "$staging_project" ps --status running --services)"
for service in db backend auto-submit-worker frontend nginx operator-nginx; do
  print -r -- "$running_services" | grep -Fx -- "$service" >/dev/null || macos_die "staging service is not running: $service"
done

backup_run_root="$staging_backup/restore-smoke-$run_id"
[[ ! -e "$backup_run_root" && ! -L "$backup_run_root" ]] || macos_die "restore-smoke backup root already exists for this run"

macos_save_environment APP_IMAGE_REPOSITORY APP_VERSION_TAG APP_VERSION GIT_COMMIT INTERNAL_EXAM_LIFECYCLE_HOST_DIR INTERNAL_EXAM_BACKUP_HOST_DIR INTERNAL_EXAM_EVIDENCE_HOST_DIR INTERNAL_LAN_BIND_IP CANDIDATE_GATEWAY_PORT CANDIDATE_PUBLIC_BASE_URL OPERATOR_GATEWAY_PORT POSTGRES_LOOPBACK_PORT FRONTEND_LOOPBACK_PORT
restore_project=""
restore_active=0
restore_host_root=""
restore_host_root_created=0
backup_run_root_created=0
second_copy_destination=""
second_copy_partial=""
second_copy_created=0
output_created=0
cleanup_status=failed

restore_compose_base() {
  macos_compose_base "$release_path" "$MACOS_STAGING_ENV" "$restore_project"
  MACOS_COMPOSE_ARGS+=( -f "$restore_compose_override" )
}

restore_compose() {
  restore_compose_base
  macos_run_checked docker "${MACOS_COMPOSE_ARGS[@]}" "$@"
}

restore_compose_capture() {
  restore_compose_base
  macos_run_capture docker "${MACOS_COMPOSE_ARGS[@]}" "$@"
}

cleanup_restore() {
  local exit_status=$?
  if (( restore_active == 1 )) && [[ -n "$restore_project" ]]; then
    if restore_compose down -v --remove-orphans >/dev/null 2>&1; then
      cleanup_status=passed
    else
      cleanup_status=failed
      macos_log "staging_backup_restore cleanup=restore_project_failed project=$restore_project"
    fi
  fi
  if (( restore_host_root_created == 1 )) && [[ -n "$restore_host_root" && -d "$restore_host_root" ]]; then
    rm -R -- "$restore_host_root" >/dev/null 2>&1 || macos_log "staging_backup_restore cleanup=restore_host_root_failed"
  fi
  if (( exit_status != 0 )); then
    if [[ -n "$second_copy_partial" && "$second_copy_partial:h" == "$second_copy_root" && "$second_copy_partial:t" == .backup-*.partial && -d "$second_copy_partial" && ! -L "$second_copy_partial" ]]; then
      rm -R -- "$second_copy_partial" >/dev/null 2>&1 || macos_log "staging_backup_restore cleanup=second_copy_partial_failed"
    fi
    if (( second_copy_created == 1 )) && [[ -n "$second_copy_destination" && "$second_copy_destination" == "$second_copy_root"/backup-* && -d "$second_copy_destination" && ! -L "$second_copy_destination" ]]; then
      rm -R -- "$second_copy_destination" >/dev/null 2>&1 || macos_log "staging_backup_restore cleanup=second_copy_failed"
    fi
    if (( backup_run_root_created == 1 )) && [[ -n "$backup_run_root" && "$backup_run_root" == "$staging_backup/restore-smoke-$run_id" && -d "$backup_run_root" && ! -L "$backup_run_root" ]]; then
      rm -R -- "$backup_run_root" >/dev/null 2>&1 || macos_log "staging_backup_restore cleanup=backup_root_failed"
    fi
    if (( output_created == 1 )) && [[ -n "$output_path" && "$output_path" == "$staging_evidence"/* ]]; then
      rm -f -- "$output_path" "$output_path.sha256" >/dev/null 2>&1 || macos_log "staging_backup_restore cleanup=output_failed"
    fi
  fi
  macos_restore_environment
  macos_release_lock
  return "$exit_status"
}
macos_acquire_lock "$MACOS_LAYOUT_STATE/.operation.lock"
trap cleanup_restore EXIT
mkdir -p -- "$staging_lifecycle" "$staging_backup" "$staging_evidence"
chmod 700 "$staging_host_root" "$staging_lifecycle" "$staging_backup" "$staging_evidence"
backup_run_root_created=1
mkdir -p -- "$backup_run_root"
chmod 700 "$backup_run_root"
export APP_VERSION_TAG="$lower_commit"
export APP_VERSION="$application_version"
export GIT_COMMIT="$lower_commit"
export INTERNAL_EXAM_LIFECYCLE_HOST_DIR="$staging_lifecycle"
export INTERNAL_EXAM_BACKUP_HOST_DIR="$staging_backup"
export INTERNAL_EXAM_EVIDENCE_HOST_DIR="$staging_evidence"
export INTERNAL_LAN_BIND_IP=127.0.0.1
export CANDIDATE_GATEWAY_PORT="$MACOS_STAGE_PORT_CANDIDATE"
export CANDIDATE_PUBLIC_BASE_URL="http://127.0.0.1:${MACOS_STAGE_PORT_CANDIDATE}"
export OPERATOR_GATEWAY_PORT="$MACOS_STAGE_PORT_OPERATOR"
export POSTGRES_LOOPBACK_PORT="$MACOS_STAGE_PORT_DATABASE"
export FRONTEND_LOOPBACK_PORT="$MACOS_STAGE_PORT_FRONTEND"

macos_compose_base "$release_path" "$MACOS_STAGING_ENV" "$staging_project"
backup_json="$(macos_run_capture docker "${MACOS_COMPOSE_ARGS[@]}" run --rm --no-deps \
  --volume "$staging_backup:/staging-backups" backend \
  uv run --no-sync python -m app.ops.internal_backup container-backup \
  --output-root "/staging-backups/restore-smoke-$run_id" \
  --media-root /app/learning-media \
  --kind daily --operator-subject "staging-backup-$run_id" \
  --app-version "$application_version")"
backup_status="$(print -r -- "$backup_json" | plutil -extract status raw -o - -- - 2>/dev/null || true)"
backup_id="$(print -r -- "$backup_json" | plutil -extract backup_id raw -o - -- - 2>/dev/null || true)"
[[ "$backup_status" == passed && "$backup_id" =~ '^backup-[0-9]{8}T[0-9]{6}Z$' ]] || macos_die "staging container backup did not return a passed verified backup"
backup_path="$backup_run_root/$backup_id"
macos_assert_backup "$backup_path" >/dev/null
macos_compose_base "$release_path" "$MACOS_STAGING_ENV" "$staging_project"
macos_run_checked docker "${MACOS_COMPOSE_ARGS[@]}" run --rm --no-deps \
  --volume "$staging_backup:/staging-backups:ro" backend \
  uv run --no-sync python -m app.ops.internal_backup inspect "/staging-backups/restore-smoke-$run_id/$backup_id"

second_copy_destination="$second_copy_root/$backup_id"
second_copy_partial="$second_copy_root/.$backup_id.partial"
[[ ! -e "$second_copy_destination" && ! -L "$second_copy_destination" ]] || macos_die "second-copy destination already exists; refusing to replace independent evidence"
second_copy_created=1
macos_compose_base "$release_path" "$MACOS_STAGING_ENV" "$staging_project"
sync_json="$(macos_run_capture docker "${MACOS_COMPOSE_ARGS[@]}" run --rm --no-deps \
  --volume "$staging_backup:/staging-backups:ro" \
  --volume "$second_copy_root:/second-copy" backend \
  uv run --no-sync python -m app.ops.internal_backup sync-second-copy \
  "/staging-backups/restore-smoke-$run_id/$backup_id" /second-copy)"
sync_status="$(print -r -- "$sync_json" | plutil -extract status raw -o - -- - 2>/dev/null || true)"
sync_artifact="$(print -r -- "$sync_json" | plutil -extract artifact_id raw -o - -- - 2>/dev/null || true)"
[[ "$sync_status" == passed && "$sync_artifact" == "$backup_id" ]] || macos_die "second-copy sync did not return a passed exact artifact identity"
[[ -d "$second_copy_destination" && ! -L "$second_copy_destination" ]] || macos_die "second-copy backup destination is missing"
second_copy_evidence="$backup_run_root/${backup_id}.second-copy.json"
[[ -f "$second_copy_evidence" && -f "$second_copy_evidence.sha256" ]] || macos_die "second-copy sync evidence is missing"
chmod 600 "$second_copy_evidence" "$second_copy_evidence.sha256"
macos_check_checksum "$second_copy_evidence"
[[ "$(macos_json_get "$second_copy_evidence" status 2>/dev/null || true)" == passed && "$(macos_json_get "$second_copy_evidence" artifact_id 2>/dev/null || true)" == "$backup_id" ]] || macos_die "second-copy evidence is not bound to the paired backup basename"
second_copy_evidence_sha256="$(macos_sha256 "$second_copy_evidence")"
macos_compose_base "$release_path" "$MACOS_STAGING_ENV" "$staging_project"
macos_run_checked docker "${MACOS_COMPOSE_ARGS[@]}" run --rm --no-deps \
  --volume "$second_copy_root:/second-copy:ro" backend \
  uv run --no-sync python -m app.ops.internal_backup inspect "/second-copy/$backup_id"

backup_manifest="$backup_path/manifest.json"
migration_value="$(macos_json_get "$backup_manifest" migration_head 2>/dev/null || macos_json_get "$backup_manifest" migrationHead 2>/dev/null || true)"
[[ "$migration_value" == "$migration_head" ]] || macos_die "portable backup migration head does not match the sealed release manifest"
table_counts_json="$(plutil -extract table_counts json -o - -- "$backup_manifest" 2>/dev/null || plutil -extract tableCounts json -o - -- "$backup_manifest" 2>/dev/null || true)"
media_file_count="$(macos_json_get "$backup_manifest" media_file_count 2>/dev/null || macos_json_get "$backup_manifest" mediaFileCount 2>/dev/null || true)"
[[ -n "$table_counts_json" && "$media_file_count" =~ '^[0-9]+$' ]] || macos_die "portable backup manifest counts are invalid"
source_backup_sha256="$(macos_sha256 "$backup_path/SHA256SUMS")"
database_digest="$(macos_sha256 "$backup_path/database.dump")"
media_digest="$(macos_sha256 "$backup_path/learning_media.tar.gz")"
manifest_digest="$(macos_sha256 "$backup_path/manifest.json")"
second_copy_sha256="$(macos_sha256 "$second_copy_destination/SHA256SUMS")"
[[ "$second_copy_sha256" == "$source_backup_sha256" ]] || macos_die "second-copy SHA256SUMS does not match the source backup"

typeset -A image_refs image_ids
for image_name in db backend frontend gateway; do
  image_refs[$image_name]="$(macos_json_get "$identity_path" "images.$image_name.reference")"
  image_ids[$image_name]="$(macos_json_get "$identity_path" "images.$image_name.id")"
done

# The restore target is unique, lower-case, and disposable.  All Compose calls
# below use this project and the staging env; formal env/project/volumes are
# never passed to this producer.
suffix="$(date -u '+%Y%m%d%H%M%S')-$$-$RANDOM"
restore_project="internal-exam-restore-verify-${suffix:l}"
macos_assert_project_name restore "$restore_project"
restore_host_root="$staging_host_root/restore/$suffix"
restore_lifecycle="$restore_host_root/lifecycle"
restore_backup="$restore_host_root/backups"
restore_evidence="$restore_host_root/evidence"
mkdir -p -- "$restore_lifecycle" "$restore_backup" "$restore_evidence"
chmod 700 "$restore_host_root" "$restore_lifecycle" "$restore_backup" "$restore_evidence"
restore_host_root_created=1
# The staging Compose env carries host-published ports (15432/18080/18081/
# 15173).  A restore smoke runs while staging remains live, so reset every
# host-port sequence in a protected, run-scoped override instead of reusing
# those bindings.  Internal container ports remain available on the private
# Compose network for health/restore verification.
restore_compose_override="$restore_host_root/no-host-ports.compose.yml"
restore_override_body=$'services:\n  db:\n    ports: !reset []\n  frontend:\n    ports: !reset []\n  nginx:\n    ports: !reset []\n  operator-nginx:\n    ports: !reset []\n'
macos_write_atomic "$restore_compose_override" "$restore_override_body"
macos_secure_path "$restore_compose_override"
restore_active=1
restore_compose up -d --no-build --wait db
media_volume="${restore_project}_learning_media"
# Create the Compose-labelled media volume through the disposable project so
# its mandatory ``down -v`` cleanup removes it as well; a raw ``docker volume
# create`` would leave an unlabelled volume behind.
restore_compose run --rm --no-deps backend true
restore_compose cp \
  "$second_copy_destination/database.dump" db:/tmp/internal-exam-staging-restore.dump
restore_compose exec -T db \
  pg_restore --clean --if-exists --no-owner --no-privileges -U exam -d internal_exam /tmp/internal-exam-staging-restore.dump
restore_compose exec -T db \
  rm -f /tmp/internal-exam-staging-restore.dump
macos_run_checked docker run --rm --volume "$media_volume:/restore" \
  --volume "$second_copy_destination:/backup:ro" "${image_refs[gateway]}" \
  tar -C /restore -xzf /backup/learning_media.tar.gz
restore_compose up -d --no-build --wait
restore_running="$(restore_compose_capture ps --status running --services)"
for service in db backend auto-submit-worker frontend nginx operator-nginx; do
  print -r -- "$restore_running" | grep -Fx -- "$service" >/dev/null || macos_die "restore service is not running: $service"
done
restore_images="$(restore_compose_capture images --format '{{.Service}}|{{.ID}}')"
typeset -A restore_seen
for row in ${(f)restore_images}; do
  service="${row%%|*}"
  actual_id="${row#*|}"
  case "$service" in
    db) expected_id="${image_ids[db]}" ;;
    backend|auto-submit-worker) expected_id="${image_ids[backend]}" ;;
    frontend) expected_id="${image_ids[frontend]}" ;;
    nginx|operator-nginx) expected_id="${image_ids[gateway]}" ;;
    *) continue ;;
  esac
  restore_seen[$service]=1
  [[ "$actual_id" == "$expected_id" ]] || macos_die "restore service image is not the exact sealed release image: $service"
done
for service in db backend auto-submit-worker frontend nginx operator-nginx; do
  (( ${+restore_seen[$service]} == 1 )) || macos_die "restore image capture is missing service: $service"
done
restore_compose run --rm --no-deps \
  --volume "$second_copy_destination:/portable-backup:ro" backend \
  uv run --no-sync python -m app.ops.internal_backup verify-restored \
  /portable-backup --media-root /app/learning-media
restore_compose down -v --remove-orphans
restore_active=0
cleanup_status=passed
rm -R -- "$restore_host_root"

source_relative="${backup_path#$MACOS_LAYOUT_ROOT/}"
second_copy_evidence_relative="${second_copy_evidence#$MACOS_LAYOUT_ROOT/}"
second_copy_storage_evidence_relative="${second_copy_storage_evidence#$MACOS_LAYOUT_ROOT/}"
checked_at="$(macos_now_iso)"
raw_json="{\"schemaVersion\":2,\"kind\":\"staging-check\",\"status\":\"passed\",\"check\":\"backupRestore\",\"runId\":\"$(macos_json_escape "$run_id")\",\"commit\":\"$lower_commit\",\"project\":\"$staging_project\",\"hostId\":\"$(macos_json_escape "$MACOS_HOST_ID")\",\"hostOS\":\"darwin\",\"architecture\":\"arm64\",\"platform\":\"linux/arm64\",\"builtImageIdentitySha256\":\"$identity_digest\",\"startedAt\":\"$(macos_json_escape "$run_started_at")\",\"checkedAt\":\"$checked_at\",\"mode\":\"restore-smoke\",\"restoreProject\":\"$restore_project\",\"sourceBackupPath\":\"$(macos_json_escape "$source_relative")\",\"sourceBackupSha256\":\"$source_backup_sha256\",\"secondCopySha256\":\"$source_backup_sha256\",\"secondCopyEvidencePath\":\"$(macos_json_escape "$second_copy_evidence_relative")\",\"secondCopyEvidenceSha256\":\"$second_copy_evidence_sha256\",\"secondCopyStorageEvidencePath\":\"$(macos_json_escape "$second_copy_storage_evidence_relative")\",\"secondCopyStorageEvidenceSha256\":\"$second_copy_storage_evidence_sha256\",\"sourceBackupFiles\":[\"SHA256SUMS\",\"SUCCESS\",\"database.dump\",\"learning_media.tar.gz\",\"manifest.json\"],\"sourceBackupDigests\":{\"database.dump\":\"$database_digest\",\"learning_media.tar.gz\":\"$media_digest\",\"manifest.json\":\"$manifest_digest\"},\"restoreMigrationHead\":\"$(macos_json_escape "$migration_value")\",\"cleanupStatus\":\"$cleanup_status\",\"tableCounts\":$table_counts_json,\"mediaFileCount\":$media_file_count,\"restoreImageIds\":{\"db\":\"${image_ids[db]}\",\"backend\":\"${image_ids[backend]}\",\"frontend\":\"${image_ids[frontend]}\",\"gateway\":\"${image_ids[gateway]}\"},\"secrets\":\"redacted\"}"
output_created=1
macos_write_atomic "$output_path" "$raw_json"
macos_checksummed_json "$output_path"
macos_log "staging_backup_restore_passed project=$staging_project runId=$run_id restoreProject=$restore_project backup=${backup_id} output=${output_path:t}"
