#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
source "$SCRIPT_DIR/Common.zsh"

kind="daily"
opportunistic=0
under_writer_fence=0
lock_held=0
second_copy_path=""
root="${INTERNAL_EXAM_ROOT:-${HOME:?}/Library/Application Support/InternalExam}"
while (( $# > 0 )); do
  case "$1" in
    --kind) (( $# >= 2 )) || macos_die "--kind requires daily, pre-exam, post-exam, pre-upgrade, or cutover"; kind="$2"; shift 2 ;;
    --opportunistic) opportunistic=1; shift ;;
    --under-writer-fence) under_writer_fence=1; shift ;;
    --lock-held) lock_held=1; shift ;;
    --second-copy-path) (( $# >= 2 )) || macos_die "--second-copy-path requires a path"; second_copy_path="$2"; shift 2 ;;
    --root) (( $# >= 2 )) || macos_die "--root requires a path"; root="$2"; shift 2 ;;
    -h|--help) print -r -- "usage: $0 [--kind daily|pre-exam|post-exam|pre-upgrade|cutover] [--opportunistic] [--under-writer-fence] [--second-copy-path PATH] [--root ROOT]"; exit 0 ;;
    *) macos_die "unknown argument: $1"; exit 1 ;;
  esac
done

macos_assert_macos
[[ "$kind" == daily || "$kind" == pre-exam || "$kind" == post-exam || "$kind" == pre-upgrade || "$kind" == cutover ]] || macos_die "invalid backup kind"
macos_assert_outside_worktree "$root" >/dev/null
macos_layout "$root"
macos_assert_protected_configuration "$root"
macos_require_formal_paths
macos_docker_ready
if (( lock_held == 1 )); then
  macos_assert_inherited_lock
else
  macos_acquire_lock "$MACOS_LAYOUT_STATE/.operation.lock"
fi
trap '(( lock_held == 1 )) || macos_release_lock' EXIT
macos_release_state "$MACOS_CURRENT_STATE"
release_path="$MACOS_STATE_PATH"
release_version="$MACOS_STATE_VERSION"
"$SCRIPT_DIR/Test-ReleaseBundle.zsh" --release-path "$release_path" >/dev/null
macos_verify_built_image_identity "$release_path"
macos_cutover_identity
operator="$(macos_active_operator_subject)"
backup_root="$MACOS_LAYOUT_BACKUPS"
mkdir -p -- "$backup_root"
chmod 700 "$backup_root"
second_copy_status="not-run"
second_copy_evidence=""

macos_compose_base "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT"
backup_args=(run --rm --no-deps --volume "$backup_root:/backups" backend \
  uv run --no-sync python -m app.ops.internal_backup container-backup \
  --output-root /backups --media-root /app/learning-media --kind "$kind" \
  --operator-subject "$operator" --app-version "$release_version" \
  --dataset-id "$MACOS_DATASET_ID" --writer-generation "$MACOS_WRITER_GENERATION" \
  --source-host-id "$MACOS_HOST_ID")
(( opportunistic == 1 )) && backup_args+=(--opportunistic)
(( under_writer_fence == 1 )) && backup_args+=(--under-writer-fence)
backup_output="$(macos_run_capture docker "${MACOS_COMPOSE_ARGS[@]}" "${backup_args[@]}")"
result_json="$(print -r -- "$backup_output" | tail -n 1)"
backup_status="$(print -r -- "$result_json" | plutil -extract status raw -o - - 2>/dev/null || true)"
reason="$(print -r -- "$result_json" | plutil -extract reason raw -o - - 2>/dev/null || true)"
backup_id="$(print -r -- "$result_json" | plutil -extract backup_id raw -o - - 2>/dev/null || true)"
[[ "$backup_status" == passed || "$backup_status" == skipped ]] || macos_die "paired backup returned an invalid status"
backup_id_json="$(macos_json_escape "$backup_id")"
reason_json="$(macos_json_escape "$reason")"

if [[ "$backup_status" == passed ]]; then
  [[ -n "$second_copy_path" ]] || second_copy_path="$(macos_formal_value SECOND_COPY_PATH)"
  second_copy_path="$(macos_resolve_path "$second_copy_path")"
  macos_assert_outside_worktree "$second_copy_path" >/dev/null
  [[ "$second_copy_path" != */Docker.raw && "$second_copy_path" != */docker.raw ]] || macos_die "raw Docker Desktop disks are not second-copy storage"
  if [[ ! -d "$second_copy_path" || ! -f "$second_copy_path/.internal-exam-encrypted-storage" ]]; then
    second_copy_status=failed
    if [[ "$kind" == daily && "$opportunistic" == 1 ]]; then
      second_copy_status=degraded
    else
      macos_die "passed $kind backup requires an available encrypted second-copy mount"
    fi
  elif ! macos_assert_second_copy_storage "$second_copy_path"; then
    second_copy_status=failed
    if [[ "$kind" == daily && "$opportunistic" == 1 ]]; then
      second_copy_status=degraded
    else
      macos_die "passed $kind backup requires fresh encrypted second-copy device evidence"
    fi
  fi
  [[ "$backup_id" =~ '^backup-[0-9]{8}T[0-9]{6}Z$' ]] || macos_die "backup id is invalid"
  backup_dir="$backup_root/$backup_id"
  [[ -d "$backup_dir" ]] || macos_die "created backup directory is missing"
  if [[ "$second_copy_status" != failed && "$second_copy_status" != degraded ]]; then
    macos_compose_base "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT"
    if macos_run_checked docker "${MACOS_COMPOSE_ARGS[@]}" run --rm --no-deps \
      --volume "$backup_root:/backups:ro" --volume "$second_copy_path:/second-copy" backend \
      uv run --no-sync python -m app.ops.internal_backup sync-second-copy \
      "/backups/$backup_id" /second-copy; then
      second_copy_status=passed
    else
      second_copy_status=failed
      [[ "$kind" == daily && "$opportunistic" == 1 ]] || macos_die "$kind backup second-copy synchronization failed"
      second_copy_status=degraded
    fi
  fi
  second_copy_evidence="$backup_dir:h/${backup_id}.second-copy.json"
  if [[ "$second_copy_status" == passed && -f "$second_copy_evidence" && -f "$second_copy_evidence.sha256" ]]; then
    macos_check_checksum "$second_copy_evidence"
    [[ "$(macos_json_get "$second_copy_evidence" status 2>/dev/null || true)" == passed ]] || macos_die "second-copy evidence did not pass"
    [[ "$(macos_json_get "$second_copy_evidence" artifact_id 2>/dev/null || true)" == "$backup_id" ]] || macos_die "second-copy evidence identity is invalid"
    if (( under_writer_fence == 0 )); then
      macos_compose_base "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT"
      macos_run_checked docker "${MACOS_COMPOSE_ARGS[@]}" run --rm --no-deps backend \
        uv run --no-sync python -m app.ops.operator_control record-lifecycle \
        --lifecycle-action second_copy_sync_completed --operator-subject "$operator" \
        --target "$backup_id" --artifact "$backup_id.second-copy.json"
    fi
  elif [[ "$kind" == daily && "$opportunistic" == 1 ]]; then
    second_copy_status=degraded
  else
    macos_die "$kind backup second-copy evidence is missing or failed"
  fi
fi

macos_write_evidence "$MACOS_LAYOUT_EVIDENCE" paired-backup \
  "{\"schemaVersion\":1,\"kind\":\"paired-backup\",\"status\":\"$backup_status\",\"backupId\":\"$backup_id_json\",\"reason\":\"$reason_json\",\"kindValue\":\"$kind\",\"opportunistic\":$([[ $opportunistic == 1 ]] && print true || print false),\"localBackupStatus\":\"$backup_status\",\"secondCopyStatus\":\"$second_copy_status\",\"secondCopyEvidence\":\"$(macos_json_escape "${second_copy_evidence:t}")\",\"secrets\":\"redacted\"}" >/dev/null
macos_log "paired_backup status=$backup_status local=$backup_status second_copy=$second_copy_status reason=$reason backup=$backup_id"
