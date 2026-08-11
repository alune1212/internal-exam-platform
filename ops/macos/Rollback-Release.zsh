#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
source "$SCRIPT_DIR/Common.zsh"

mode=""
confirmation=""
proven=0
allow_restore=0
root="${INTERNAL_EXAM_ROOT:-${HOME:?}/Library/Application Support/InternalExam}"
while (( $# > 0 )); do
  case "$1" in
    --mode) (( $# >= 2 )) || macos_die "--mode requires PreMigration or PostMigrationOrWrite"; mode="$2"; shift 2 ;;
    --confirmation) (( $# >= 2 )) || macos_die "--confirmation requires exact text"; confirmation="$2"; shift 2 ;;
    --proven-no-migration-or-writes) proven=1; shift ;;
    --allow-destructive-restore) allow_restore=1; shift ;;
    --root) (( $# >= 2 )) || macos_die "--root requires a path"; root="$2"; shift 2 ;;
    -h|--help) print -r -- "usage: $0 --mode PreMigration|PostMigrationOrWrite --confirmation TEXT [--proven-no-migration-or-writes|--allow-destructive-restore] [--root ROOT]"; exit 0 ;;
    *) macos_die "unknown argument: $1"; exit 1 ;;
  esac
done

macos_assert_macos
[[ "$mode" == PreMigration || "$mode" == PostMigrationOrWrite ]] || macos_die "invalid rollback mode"
[[ -n "$confirmation" ]] || macos_die "--confirmation is required"
macos_assert_outside_worktree "$root" >/dev/null
macos_layout "$root"
macos_assert_protected_configuration "$root"
macos_require_formal_paths
macos_docker_ready
macos_acquire_lock "$MACOS_LAYOUT_STATE/.operation.lock"
trap macos_release_lock EXIT
macos_release_state "$MACOS_CURRENT_STATE"
[[ -f "$MACOS_PREVIOUS_STATE" ]] || macos_die "previous release state is missing"
macos_release_state "$MACOS_PREVIOUS_STATE"
previous_path="$MACOS_STATE_PATH"
previous_version="$MACOS_STATE_VERSION"
previous_commit="$MACOS_STATE_COMMIT"
macos_release_state "$MACOS_CURRENT_STATE"
current_path="$MACOS_STATE_PATH"
current_version="$MACOS_STATE_VERSION"
current_commit="$MACOS_STATE_COMMIT"
current_backup="$MACOS_STATE_BACKUP"
macos_read_cutover_identity
# Same-host version rollback must not double as an escape hatch from a
# cross-host retirement barrier.  Cross-host recovery requires the explicit
# Rollback/Resume state machine and a generation advance.
macos_assert_no_pending_cutover_start 0
"$SCRIPT_DIR/Test-ReleaseBundle.zsh" --release-path "$previous_path" >/dev/null
macos_verify_built_image_identity "$previous_path"
macos_save_environment APP_VERSION_TAG APP_VERSION GIT_COMMIT
trap 'macos_restore_environment; macos_release_lock' EXIT
export APP_VERSION_TAG="${previous_commit:l}"
export APP_VERSION="$previous_version"
export GIT_COMMIT="${previous_commit:l}"

if [[ "$mode" == PreMigration ]]; then
  (( proven == 1 )) || macos_die "pre-migration rollback requires proof of no writes"
  [[ "$confirmation" == "ROLLBACK PRE-MIGRATION $previous_version" ]] || macos_die "exact pre-migration confirmation did not match"
  macos_compose "$current_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" down --remove-orphans
else
  (( allow_restore == 1 )) || macos_die "post-migration rollback requires destructive-restore authorization"
  [[ "$confirmation" == "RESTORE PAIRED BACKUP $previous_version" ]] || macos_die "exact paired-restore confirmation did not match"
  [[ -n "$current_backup" ]] || macos_die "current release has no paired pre-upgrade backup"
  current_backup="$(macos_assert_backup "$current_backup")"
  macos_compose_base "$previous_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT"
  macos_run_checked docker "${MACOS_COMPOSE_ARGS[@]}" run --rm --no-deps \
    --volume "$current_backup:/portable-backup:ro" backend \
    uv run --no-sync python -m app.ops.host_portability validate-migration-input /portable-backup
  macos_compose "$current_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" down --remove-orphans
  macos_compose "$previous_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" up -d --no-build db
  # Check the live pre-restore database with the current release tooling.  A
  # crash after writer-fence acquisition can precede canonical prepared-state
  # creation, so filesystem retirement evidence alone is insufficient here;
  # never let pg_restore erase an active cutover fence.
  export APP_VERSION_TAG="${current_commit:l}"
  export APP_VERSION="$current_version"
  export GIT_COMMIT="${current_commit:l}"
  macos_assert_writer_fence_clear "$current_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT"
  export APP_VERSION_TAG="${previous_commit:l}"
  export APP_VERSION="$previous_version"
  export GIT_COMMIT="${previous_commit:l}"
  macos_compose "$previous_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" cp \
    "$current_backup/database.dump" db:/tmp/internal-exam-rollback.dump
  macos_compose "$previous_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" exec -T db \
    pg_restore --clean --if-exists --no-owner --no-privileges -U exam -d internal_exam /tmp/internal-exam-rollback.dump
  macos_compose "$previous_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" exec -T db rm -f /tmp/internal-exam-rollback.dump
  gateway_image="$(macos_json_get "$previous_path/release-manifest.json" imageDigests.gateway)"
  [[ "$gateway_image" == *":${previous_commit:l}" ]] || macos_die "previous gateway image is not the built release image"
  media_volume="${MACOS_FORMAL_PROJECT}_learning_media"
  volume_override="$MACOS_LAYOUT_STATE/formal-volume-override.yml"
  if [[ -f "$volume_override" ]]; then
    media_volume="$(awk '/^[[:space:]]+learning_media:[[:space:]]*$/ { in_media=1; next } in_media && /^[[:space:]]+name:[[:space:]]*/ { print $2; exit }' "$volume_override")"
    [[ "$media_volume" =~ '^internal-exam-formal-cutover-[A-Za-z0-9-]+-media$' ]] || macos_die "formal media volume override is invalid"
  fi
  macos_run_checked docker run --rm --volume "$media_volume:/restore" \
    --volume "$current_backup:/backup:ro" "$gateway_image" sh -c \
    'find /restore -mindepth 1 -delete && tar -C /restore -xzf /backup/learning_media.tar.gz'
fi

previous_state_json="$(cat -- "$MACOS_PREVIOUS_STATE")"
macos_write_atomic "$MACOS_CURRENT_STATE" "$previous_state_json"
macos_json_replace_atomic "$MACOS_CURRENT_STATE" datasetId "\"$MACOS_DATASET_ID\""
macos_json_replace_atomic "$MACOS_CURRENT_STATE" hostId "\"$MACOS_HOST_ID\""
macos_json_replace_atomic "$MACOS_CURRENT_STATE" writerGeneration "$MACOS_WRITER_GENERATION"
macos_write_checksum "$MACOS_CURRENT_STATE"
MACOS_PARENT_LOCK_PID="$$" "$SCRIPT_DIR/Start-Platform.zsh" --root "$root" --lock-held >/dev/null
macos_compose_capture "$previous_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" exec -T backend uv run --no-sync alembic current >/dev/null
macos_write_evidence "$MACOS_LAYOUT_EVIDENCE" rollback \
  "{\"schemaVersion\":1,\"kind\":\"rollback\",\"status\":\"passed\",\"mode\":\"$mode\",\"restoredVersion\":\"$previous_version\",\"restoredCommit\":\"${previous_commit:l}\",\"pairedBackupRestored\":$([[ "$mode" == PostMigrationOrWrite ]] && print true || print false),\"secrets\":\"redacted\"}" >/dev/null
macos_log "rollback_completed mode=$mode version=$previous_version"
