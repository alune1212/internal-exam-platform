#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
source "$SCRIPT_DIR/Common.zsh"

second_copy_backup_path=""
release_path_arg=""
lock_held=0
db_audit=1
root="${INTERNAL_EXAM_ROOT:-${HOME:?}/Library/Application Support/InternalExam}"
while (( $# > 0 )); do
  case "$1" in
    --second-copy-backup-path|--backup) (( $# >= 2 )) || macos_die "$1 requires a path"; second_copy_backup_path="$2"; shift 2 ;;
    --release-path|--release) (( $# >= 2 )) || macos_die "$1 requires a sealed release path"; release_path_arg="$2"; shift 2 ;;
    --lock-held) lock_held=1; shift ;;
    --no-db-audit) db_audit=0; shift ;;
    --root) (( $# >= 2 )) || macos_die "--root requires a path"; root="$2"; shift 2 ;;
    -h|--help) print -r -- "usage: $0 --second-copy-backup-path PATH [--release-path SEALED_RELEASE] [--no-db-audit] [--lock-held] [--root ROOT]"; exit 0 ;;
    *) macos_die "unknown argument: $1"; exit 1 ;;
  esac
done

macos_assert_macos
[[ -n "$second_copy_backup_path" ]] || macos_die "--second-copy-backup-path is required"
macos_assert_outside_worktree "$root" >/dev/null
macos_layout "$root"
macos_assert_protected_configuration "$root"
macos_docker_ready
if (( lock_held == 1 )); then
  macos_assert_inherited_lock
else
  macos_acquire_lock "$MACOS_LAYOUT_STATE/.operation.lock"
fi
trap '(( lock_held == 1 )) || macos_release_lock' EXIT
if [[ -n "$release_path_arg" ]]; then
  release_path="$(macos_resolve_path "$release_path_arg")"
  [[ "$release_path" == "$MACOS_LAYOUT_RELEASES"/* ]] || macos_die "restore drill release must be under the protected release directory"
  release_version="$(macos_json_get "$release_path/release-manifest.json" applicationVersion)"
  release_commit="$(macos_json_get "$release_path/release-manifest.json" gitCommit)"
elif [[ -f "$MACOS_CURRENT_STATE" ]]; then
  macos_release_state "$MACOS_CURRENT_STATE"
  release_path="$MACOS_STATE_PATH"
  release_version="$MACOS_STATE_VERSION"
  release_commit="$MACOS_STATE_COMMIT"
else
  [[ -n "$release_path_arg" ]] || macos_die "restore drill requires current release state or --release-path"
  release_path="$(macos_resolve_path "$release_path_arg")"
  [[ "$release_path" == "$MACOS_LAYOUT_RELEASES"/* ]] || macos_die "restore drill release must be under the protected release directory"
  release_version="$(macos_json_get "$release_path/release-manifest.json" applicationVersion)"
  release_commit="$(macos_json_get "$release_path/release-manifest.json" gitCommit)"
fi
operator="$(macos_active_operator_subject)"
backup_path="$(macos_assert_backup "$second_copy_backup_path")"
macos_assert_outside_worktree "$backup_path" >/dev/null
second_copy_root="$(macos_formal_value SECOND_COPY_PATH)"
second_copy_root="$(macos_resolve_path "$second_copy_root")"
[[ "$backup_path" == "$second_copy_root"/backup-* ]] || macos_die "restore drill input must be a direct backup under configured second-copy storage"
macos_assert_second_copy_storage "$second_copy_root"
second_copy_evidence="$MACOS_LAYOUT_BACKUPS/${backup_path:t}.second-copy.json"
[[ -f "$second_copy_evidence" && -f "$second_copy_evidence.sha256" ]] || macos_die "second-copy sync evidence is missing"
macos_check_checksum "$second_copy_evidence"
[[ "$(macos_json_get "$second_copy_evidence" status 2>/dev/null || true)" == passed ]] || macos_die "second-copy sync evidence is not passed"
[[ "$(macos_json_get "$second_copy_evidence" artifact_id 2>/dev/null || true)" == "${backup_path:t}" ]] || macos_die "second-copy sync evidence identity does not match"
"$SCRIPT_DIR/Test-ReleaseBundle.zsh" --release-path "$release_path" >/dev/null
macos_verify_built_image_identity "$release_path"

macos_compose_base "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT"
macos_run_checked docker "${MACOS_COMPOSE_ARGS[@]}" run --rm --no-deps \
  --volume "$backup_path:/portable-backup:ro" backend \
  uv run --no-sync python -m app.ops.host_portability validate-migration-input /portable-backup

suffix="$(date -u '+%Y%m%d%H%M%S')-$$-$RANDOM"
restore_project="internal-exam-restore-verify-${suffix}"
macos_assert_project_name restore "$restore_project"
restore_host_root="$MACOS_LAYOUT_ROOT/restore/$suffix"
restore_lifecycle="$restore_host_root/lifecycle"
restore_backup="$restore_host_root/backups"
restore_evidence="$restore_host_root/evidence"
mkdir -p -- "$restore_lifecycle" "$restore_backup" "$restore_evidence"
chmod 700 "$MACOS_LAYOUT_ROOT/restore" "$restore_host_root" "$restore_lifecycle" "$restore_backup" "$restore_evidence"
restore_status=failed

macos_save_environment APP_IMAGE_REPOSITORY APP_VERSION_TAG APP_VERSION GIT_COMMIT INTERNAL_EXAM_LIFECYCLE_HOST_DIR INTERNAL_EXAM_BACKUP_HOST_DIR INTERNAL_EXAM_EVIDENCE_HOST_DIR INTERNAL_LAN_BIND_IP CANDIDATE_GATEWAY_PORT OPERATOR_GATEWAY_PORT POSTGRES_LOOPBACK_PORT FRONTEND_LOOPBACK_PORT
cleanup_restore() {
  macos_restore_environment
  (( lock_held == 1 )) || macos_release_lock
}
trap cleanup_restore EXIT
export APP_VERSION_TAG="${release_commit:l}"
export APP_VERSION="$release_version"
export GIT_COMMIT="${release_commit:l}"
export INTERNAL_EXAM_LIFECYCLE_HOST_DIR="$restore_lifecycle"
export INTERNAL_EXAM_BACKUP_HOST_DIR="$restore_backup"
export INTERNAL_EXAM_EVIDENCE_HOST_DIR="$restore_evidence"
export INTERNAL_LAN_BIND_IP=127.0.0.1
export CANDIDATE_GATEWAY_PORT=28080
export OPERATOR_GATEWAY_PORT=28081
export POSTGRES_LOOPBACK_PORT=25432
export FRONTEND_LOOPBACK_PORT=25173

macos_restore() {
  setopt local_options err_return
  macos_compose "$release_path" "$MACOS_FORMAL_ENV" "$restore_project" up -d --no-build --wait db
  macos_compose "$release_path" "$MACOS_FORMAL_ENV" "$restore_project" cp \
    "$backup_path/database.dump" db:/tmp/internal-exam-restore.dump
  macos_compose "$release_path" "$MACOS_FORMAL_ENV" "$restore_project" exec -T db \
    pg_restore --clean --if-exists --no-owner --no-privileges -U exam -d internal_exam /tmp/internal-exam-restore.dump
  macos_compose "$release_path" "$MACOS_FORMAL_ENV" "$restore_project" exec -T db rm -f /tmp/internal-exam-restore.dump
  gateway_image="$(macos_json_get "$release_path/release-manifest.json" imageDigests.gateway)"
  [[ "$gateway_image" == *":${release_commit:l}" ]] || macos_die "restore gateway image is not the built release image"
  media_volume="${restore_project}_learning_media"
  macos_run_checked docker run --rm --volume "$media_volume:/restore" \
    --volume "$backup_path:/backup:ro" "$gateway_image" tar -C /restore -xzf /backup/learning_media.tar.gz
  macos_compose_base "$release_path" "$MACOS_FORMAL_ENV" "$restore_project"
  macos_run_checked docker "${MACOS_COMPOSE_ARGS[@]}" run --rm --no-deps \
    --volume "$backup_path:/portable-backup:ro" backend \
    uv run --no-sync python -m app.ops.internal_backup verify-restored \
    /portable-backup --media-root /app/learning-media
}

if macos_restore; then
  restore_status=passed
fi
# Isolated restore resources are always removed.  This is the only operation
# in the macOS adapter allowed to use `down -v`, and the project is unique.
macos_compose "$release_path" "$MACOS_FORMAL_ENV" "$restore_project" down -v --remove-orphans || true
rm -R -- "$restore_host_root"

evidence_path="$(macos_write_evidence "$MACOS_LAYOUT_EVIDENCE" restore-drill \
  "{\"schemaVersion\":1,\"kind\":\"second-copy-restore-drill\",\"status\":\"$restore_status\",\"backupId\":\"${backup_path:t}\",\"disposableProject\":\"$restore_project\",\"formalProjectChanged\":false,\"secrets\":\"excluded\"}")"
if [[ "$restore_status" == passed ]]; then
  # A nested cutover restore runs before the fresh formal database exists and
  # may carry an active source writer fence.  Its filesystem evidence is the
  # authoritative result; writing an audit row to the formal DB here would
  # either fail under the fence or contaminate the DB that is about to be
  # replaced.  Standalone operator-invoked drills retain the normal audit.
  if (( lock_held == 0 && db_audit == 1 )); then
    macos_compose_base "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT"
    macos_run_checked docker "${MACOS_COMPOSE_ARGS[@]}" run --rm --no-deps backend \
      uv run --no-sync python -m app.ops.operator_control record-lifecycle \
      --lifecycle-action restore_drill_completed --operator-subject "$operator" \
      --target "${backup_path:t}" --artifact "${evidence_path:t}"
  fi
  macos_log "restore_drill status=passed backup=${backup_path:t} project=$restore_project"
else
  macos_die "restore drill failed; evidence=${evidence_path:t}"
fi
