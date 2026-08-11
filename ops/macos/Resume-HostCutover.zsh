#!/bin/zsh
set -euo pipefail
umask 077

SCRIPT_DIR="${0:A:h}"
source "$SCRIPT_DIR/Common.zsh"

cutback_state_arg=""
accepted_state_arg=""
browser_evidence=""
pf_evidence=""
network_time_evidence=""
backup_path_arg=""
confirmation=""
root="${INTERNAL_EXAM_ROOT:-${HOME:?}/Library/Application Support/InternalExam}"
while (( $# > 0 )); do
  case "$1" in
    --cutback-state) (( $# >= 2 )) || macos_die "--cutback-state requires a checksummed path"; cutback_state_arg="$2"; shift 2 ;;
    --accepted-state) (( $# >= 2 )) || macos_die "--accepted-state requires a checksummed path"; accepted_state_arg="$2"; shift 2 ;;
    --browser-smoke-evidence|--browser-evidence) (( $# >= 2 )) || macos_die "$1 requires a path"; browser_evidence="$2"; shift 2 ;;
    --pf-evidence) (( $# >= 2 )) || macos_die "$1 requires a path"; pf_evidence="$2"; shift 2 ;;
    --network-time-evidence) (( $# >= 2 )) || macos_die "$1 requires a path"; network_time_evidence="$2"; shift 2 ;;
    --backup-path|--backup) (( $# >= 2 )) || macos_die "$1 requires a paired backup path"; backup_path_arg="$2"; shift 2 ;;
    --confirmation) (( $# >= 2 )) || macos_die "--confirmation requires exact text"; confirmation="$2"; shift 2 ;;
    --root) (( $# >= 2 )) || macos_die "--root requires a path"; root="$2"; shift 2 ;;
    -h|--help) print -r -- "usage: $0 --cutback-state PATH --accepted-state PATH --browser-smoke-evidence PATH --pf-evidence PATH --network-time-evidence PATH --confirmation RESUME-SOURCE [--backup-path PATH] [--root ROOT]"; exit 0 ;;
    *) macos_die "unknown argument: $1"; exit 1 ;;
  esac
done

macos_assert_macos
[[ "$confirmation" == "RESUME SOURCE AFTER PRE-WRITE CUTBACK" ]] || macos_die "exact source resume confirmation did not match"
[[ -n "$cutback_state_arg" && -n "$accepted_state_arg" && -n "$browser_evidence" && -n "$pf_evidence" && -n "$network_time_evidence" ]] || macos_die "cutback, accepted, browser, PF, and network-time evidence are required"
macos_assert_outside_worktree "$root" >/dev/null
macos_layout "$root"
macos_assert_protected_configuration "$root"
macos_require_formal_paths
macos_docker_ready
macos_acquire_lock "$MACOS_LAYOUT_STATE/.operation.lock"
resume_status=failed
cleanup_resume() {
  if [[ "$resume_status" != passed ]]; then
    macos_compose "$MACOS_STATE_PATH" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" stop >/dev/null 2>&1 || true
  fi
  macos_release_lock
}
trap cleanup_resume EXIT
if [[ -f "$MACOS_CURRENT_STATE" ]]; then
  pre_recovery_release_path="$(macos_json_get "$MACOS_CURRENT_STATE" path 2>/dev/null || true)"
  if [[ -n "$pre_recovery_release_path" && -n "$cutback_state_arg" && -n "$accepted_state_arg" ]]; then
    pre_recovery_cutback="$(macos_resolve_path "$cutback_state_arg")"
    pre_recovery_accepted="$(macos_resolve_path "$accepted_state_arg")"
    [[ "${pre_recovery_cutback:h}" == "$MACOS_LAYOUT_STATE" && "${pre_recovery_accepted:h}" == "$MACOS_LAYOUT_STATE" ]] || macos_die "pre-recovery cutover states must stay in the protected state directory"
    [[ -f "$pre_recovery_cutback" && -f "$pre_recovery_accepted" ]] || macos_die "pre-recovery cutover states are missing"
    macos_secure_path "$pre_recovery_cutback"
    macos_secure_path "$pre_recovery_accepted"
    macos_check_checksum "$pre_recovery_cutback"
    macos_check_checksum "$pre_recovery_accepted"
    pre_recovery_host="$(macos_json_get "$pre_recovery_cutback" sourceHostId 2>/dev/null || true)"
    pre_recovery_dataset="$(macos_json_get "$pre_recovery_cutback" datasetId 2>/dev/null || true)"
    pre_recovery_target="$(macos_json_get "$pre_recovery_cutback" targetHostId 2>/dev/null || true)"
    pre_recovery_source_generation="$(macos_json_get "$pre_recovery_cutback" sourceWriterGeneration 2>/dev/null || true)"
    pre_recovery_target_generation="$(macos_json_get "$pre_recovery_cutback" targetWriterGeneration 2>/dev/null || true)"
    pre_recovery_accepted_dataset="$(macos_json_get "$pre_recovery_accepted" dataset_id 2>/dev/null || true)"
    pre_recovery_accepted_source="$(macos_json_get "$pre_recovery_accepted" source_host_id 2>/dev/null || true)"
    pre_recovery_accepted_target="$(macos_json_get "$pre_recovery_accepted" target_host_id 2>/dev/null || true)"
    pre_recovery_accepted_source_generation="$(macos_json_get "$pre_recovery_accepted" source_writer_generation 2>/dev/null || true)"
    pre_recovery_accepted_target_generation="$(macos_json_get "$pre_recovery_accepted" target_writer_generation 2>/dev/null || true)"
    pre_recovery_identity_dataset="$(macos_json_get "$MACOS_LAYOUT_STATE/host-identity.json" datasetId 2>/dev/null || true)"
    pre_recovery_identity_host="$(macos_json_get "$MACOS_LAYOUT_STATE/host-identity.json" hostId 2>/dev/null || true)"
    pre_recovery_generation="$(macos_json_get "$MACOS_LAYOUT_STATE/host-identity.json" writerGeneration 2>/dev/null || true)"
    [[ "$(macos_json_get "$pre_recovery_cutback" state 2>/dev/null || true)" == prepared-for-source-reopen && "$(macos_json_get "$pre_recovery_cutback" mode 2>/dev/null || true)" == pre-write ]] || macos_die "pre-recovery cutback state is not a pre-write proof"
    [[ "$(macos_json_get "$pre_recovery_accepted" state 2>/dev/null || true)" == accepted ]] || macos_die "pre-recovery accepted state is not canonical"
    [[ "$pre_recovery_dataset" == "$pre_recovery_accepted_dataset" && "$pre_recovery_host" == "$pre_recovery_accepted_source" && "$pre_recovery_target" == "$pre_recovery_accepted_target" ]] || macos_die "pre-recovery cutover identity does not match accepted lineage"
    [[ "$pre_recovery_source_generation" == "$pre_recovery_accepted_source_generation" && "$pre_recovery_target_generation" == "$pre_recovery_accepted_target_generation" ]] || macos_die "pre-recovery cutback generations do not match accepted lineage"
    [[ "$pre_recovery_identity_dataset" == "$pre_recovery_dataset" && "$pre_recovery_identity_host" == "$pre_recovery_host" ]] || macos_die "local identity does not match accepted source lineage before sidecar recovery"
    [[ "$pre_recovery_generation" =~ '^[1-9][0-9]*$' && ( "$pre_recovery_generation" == "$pre_recovery_accepted_source_generation" || "$pre_recovery_generation" == $(( pre_recovery_accepted_target_generation + 1 )) ) ]] || macos_die "local source identity generation does not match accepted source or reconciled generation"
    if [[ -n "$pre_recovery_host" && "$pre_recovery_generation" =~ '^[1-9][0-9]*$' ]]; then
      macos_recover_derived_sidecars "$pre_recovery_release_path" "$pre_recovery_cutback" "$pre_recovery_host" "$pre_recovery_generation" "$pre_recovery_accepted"
    fi
  fi
fi
macos_release_state "$MACOS_CURRENT_STATE"
release_path="$MACOS_STATE_PATH"
backup_path="$MACOS_STATE_BACKUP"
[[ -n "$backup_path_arg" ]] && backup_path="$backup_path_arg"
backup_path="$(macos_assert_backup "$backup_path")"
macos_assert_outside_worktree "$backup_path" >/dev/null
cutback_state="$(macos_resolve_path "$cutback_state_arg")"
accepted_state="$(macos_resolve_path "$accepted_state_arg")"
[[ "${cutback_state:h}" == "$MACOS_LAYOUT_STATE" ]] || macos_die "cutback state must stay in the protected state directory"
[[ "${accepted_state:h}" == "$MACOS_LAYOUT_STATE" ]] || macos_die "accepted state must stay in the protected state directory"
macos_secure_path "$cutback_state"; macos_check_checksum "$cutback_state"
macos_secure_path "$accepted_state"; macos_check_checksum "$accepted_state"
[[ "$(macos_json_get "$cutback_state" state 2>/dev/null || true)" == "prepared-for-source-reopen" ]] || macos_die "cutback state is not a pre-write source-reopen proof"
[[ "$(macos_json_get "$cutback_state" mode 2>/dev/null || true)" == "pre-write" ]] || macos_die "cutback state mode is not pre-write"
[[ "$(macos_json_get "$cutback_state" targetWriteAccepted 2>/dev/null || true)" == false ]] || macos_die "pre-write cutback claims target writes"
[[ "$(macos_json_get "$cutback_state" targetFormalStopped 2>/dev/null || true)" == true ]] || macos_die "pre-write cutback lacks target stop proof"
[[ "$(macos_json_get "$cutback_state" targetRunningServices 2>/dev/null || true)" == "[]" ]] || macos_die "pre-write cutback has running target services"
[[ "$(macos_json_get "$cutback_state" dataRestorePerformed 2>/dev/null || true)" == false ]] || macos_die "pre-write cutback unexpectedly restored data"
[[ "$(macos_json_get "$cutback_state" sourceReopenRequired 2>/dev/null || true)" == true ]] || macos_die "pre-write cutback does not authorize source resume"
[[ "$(macos_json_get "$accepted_state" state 2>/dev/null || true)" == accepted ]] || macos_die "accepted state is not canonical"
[[ "$(macos_json_get "$accepted_state" target_write_accepted 2>/dev/null || true)" == false ]] || macos_die "accepted state target write boundary is not closed"
[[ "$(macos_json_get "$accepted_state" target_exposed 2>/dev/null || true)" == false ]] || macos_die "accepted state target exposure boundary is not closed"
accepted_digest="$(macos_sha256 "$accepted_state")"
[[ "$(macos_json_get "$cutback_state" acceptedStateSha256 2>/dev/null || true)" == "$accepted_digest" ]] || macos_die "cutback proof does not bind the accepted state"
dataset_id="$(macos_json_get "$cutback_state" datasetId 2>/dev/null || true)"
source_host_id="$(macos_json_get "$cutback_state" sourceHostId 2>/dev/null || true)"
target_host_id="$(macos_json_get "$cutback_state" targetHostId 2>/dev/null || true)"
[[ "$dataset_id" == "$(macos_json_get "$accepted_state" dataset_id 2>/dev/null || true)" ]] || macos_die "cutback dataset lineage does not match accepted state"
[[ "$target_host_id" == "$(macos_json_get "$accepted_state" target_host_id 2>/dev/null || true)" ]] || macos_die "cutback target identity does not match accepted state"
[[ "$source_host_id" == "$(macos_json_get "$accepted_state" source_host_id 2>/dev/null || true)" ]] || macos_die "cutback source identity does not match accepted state"
target_generation="$(macos_json_get "$accepted_state" target_writer_generation 2>/dev/null || true)"
source_generation="$(macos_json_get "$accepted_state" source_writer_generation 2>/dev/null || true)"
[[ "$target_generation" =~ '^[1-9][0-9]*$' && "$source_generation" =~ '^[1-9][0-9]*$' && "$target_generation" == $(( source_generation + 1 )) ]] || macos_die "accepted cutover generations are invalid"
[[ "$(macos_json_get "$cutback_state" sourceWriterGeneration 2>/dev/null || true)" == "$source_generation" && "$(macos_json_get "$cutback_state" targetWriterGeneration 2>/dev/null || true)" == "$target_generation" ]] || macos_die "cutback generations do not match accepted state"
recovery_generation="$(macos_json_get "$MACOS_LAYOUT_STATE/host-identity.json" writerGeneration 2>/dev/null || true)"
identity_dataset="$(macos_json_get "$MACOS_LAYOUT_STATE/host-identity.json" datasetId 2>/dev/null || true)"
identity_host="$(macos_json_get "$MACOS_LAYOUT_STATE/host-identity.json" hostId 2>/dev/null || true)"
[[ "$identity_dataset" == "$dataset_id" && "$identity_host" == "$source_host_id" ]] || macos_die "source host identity does not match cutback lineage before sidecar recovery"
[[ "$recovery_generation" =~ '^[1-9][0-9]*$' && ( "$recovery_generation" == "$source_generation" || "$recovery_generation" == $(( target_generation + 1 )) ) ]] || macos_die "source identity generation is neither the accepted source nor reconciled generation before sidecar recovery"
cutback_digest="$(macos_sha256 "$cutback_state")"
reconciled_generation=$(( source_generation + 2 ))
resume_intent_path="$MACOS_LAYOUT_STATE/source-cutback-resume-intent-${accepted_digest}.json"
resume_terminal_path="$MACOS_LAYOUT_STATE/source-cutback-resume-terminal-${accepted_digest}.json"
resume_terminal_committed=0
preflight_path=""
activation_intent_path=""

validate_resume_intent() {
  local path="$1"
  macos_secure_path "$path"
  plutil -convert json -o - -- "$path" >/dev/null 2>&1 || macos_die "source resume intent is invalid JSON"
  [[ "$(macos_json_get "$path" kind 2>/dev/null || true)" == source-cutback-resume-intent && "$(macos_json_get "$path" status 2>/dev/null || true)" == pending ]] || macos_die "source resume intent phase is invalid"
  [[ "$(macos_json_get "$path" acceptedStateSha256 2>/dev/null || true)" == "$accepted_digest" && "$(macos_json_get "$path" cutbackStateSha256 2>/dev/null || true)" == "$cutback_digest" ]] || macos_die "source resume intent state binding changed"
  [[ "$(macos_json_get "$path" datasetId 2>/dev/null || true)" == "$dataset_id" && "$(macos_json_get "$path" sourceHostId 2>/dev/null || true)" == "$source_host_id" && "$(macos_json_get "$path" targetHostId 2>/dev/null || true)" == "$target_host_id" ]] || macos_die "source resume intent host lineage changed"
  [[ "$(macos_json_get "$path" sourceWriterGeneration 2>/dev/null || true)" == "$source_generation" && "$(macos_json_get "$path" targetWriterGeneration 2>/dev/null || true)" == "$target_generation" && "$(macos_json_get "$path" reconciledWriterGeneration 2>/dev/null || true)" == "$reconciled_generation" ]] || macos_die "source resume intent generation changed"
}

validate_resume_terminal() {
  local path="$1" terminal_preflight terminal_activation expected actual
  macos_secure_path "$path"
  plutil -convert json -o - -- "$path" >/dev/null 2>&1 || macos_die "source resume terminal is invalid JSON"
  [[ "$(macos_json_get "$path" kind 2>/dev/null || true)" == source-cutback-resume-terminal && "$(macos_json_get "$path" status 2>/dev/null || true)" == readiness-passed ]] || macos_die "source resume terminal phase is invalid"
  [[ "$(macos_json_get "$path" resumeIntentSha256 2>/dev/null || true)" == "$(macos_sha256 "$resume_intent_path")" && "$(macos_json_get "$path" acceptedStateSha256 2>/dev/null || true)" == "$accepted_digest" && "$(macos_json_get "$path" cutbackStateSha256 2>/dev/null || true)" == "$cutback_digest" ]] || macos_die "source resume terminal state binding changed"
  [[ "$(macos_json_get "$path" datasetId 2>/dev/null || true)" == "$dataset_id" && "$(macos_json_get "$path" sourceHostId 2>/dev/null || true)" == "$source_host_id" && "$(macos_json_get "$path" targetHostId 2>/dev/null || true)" == "$target_host_id" && "$(macos_json_get "$path" reconciledWriterGeneration 2>/dev/null || true)" == "$reconciled_generation" ]] || macos_die "source resume terminal lineage changed"
  terminal_preflight="$(macos_json_get "$path" preflightPath 2>/dev/null || true)"
  terminal_activation="$(macos_json_get "$path" activationIntentPath 2>/dev/null || true)"
  [[ "$terminal_preflight" == "$MACOS_LAYOUT_EVIDENCE"/* && "$terminal_activation" == "$MACOS_LAYOUT_EVIDENCE"/* ]] || macos_die "source resume terminal evidence path is invalid"
  for expected in "$terminal_preflight" "$terminal_activation"; do
    [[ -f "$expected" && -f "$expected.sha256" ]] || macos_die "source resume terminal evidence is incomplete"
    macos_secure_path "$expected"
    macos_check_checksum "$expected"
  done
  actual="$(macos_sha256 "$terminal_preflight")"
  [[ "$actual" == "$(macos_json_get "$path" preflightSha256 2>/dev/null || true)" && "$(macos_json_get "$terminal_preflight" status 2>/dev/null || true)" == passed ]] || macos_die "source resume terminal preflight binding changed"
  actual="$(macos_sha256 "$terminal_activation")"
  [[ "$actual" == "$(macos_json_get "$path" activationIntentSha256 2>/dev/null || true)" && "$(macos_json_get "$terminal_activation" status 2>/dev/null || true)" == intent && "$(macos_json_get "$terminal_activation" acceptedStateSha256 2>/dev/null || true)" == "$accepted_digest" && "$(macos_json_get "$terminal_activation" cutbackStateSha256 2>/dev/null || true)" == "$cutback_digest" ]] || macos_die "source resume terminal activation binding changed"
  typeset -g preflight_path="$terminal_preflight" activation_intent_path="$terminal_activation" resume_terminal_committed=1
}

if [[ -e "$resume_intent_path" || -e "$resume_intent_path.sha256" ]]; then
  [[ -f "$resume_intent_path" ]] || macos_die "source resume intent is incomplete"
  validate_resume_intent "$resume_intent_path"
  [[ -f "$resume_intent_path.sha256" ]] || macos_write_checksum "$resume_intent_path"
  macos_check_checksum "$resume_intent_path"
else
  macos_write_atomic "$resume_intent_path" "{\"schemaVersion\":1,\"kind\":\"source-cutback-resume-intent\",\"status\":\"pending\",\"acceptedStateSha256\":\"$accepted_digest\",\"cutbackStateSha256\":\"$cutback_digest\",\"datasetId\":\"$dataset_id\",\"sourceHostId\":\"$source_host_id\",\"targetHostId\":\"$target_host_id\",\"sourceWriterGeneration\":$source_generation,\"targetWriterGeneration\":$target_generation,\"reconciledWriterGeneration\":$reconciled_generation,\"createdAt\":\"$(macos_now_iso)\",\"approval\":\"manual-required\"}"
  macos_checksummed_json "$resume_intent_path"
fi
if [[ -e "$resume_terminal_path" || -e "$resume_terminal_path.sha256" ]]; then
  [[ -f "$resume_terminal_path" ]] || macos_die "source resume terminal is incomplete"
  validate_resume_terminal "$resume_terminal_path"
  [[ -f "$resume_terminal_path.sha256" ]] || macos_write_checksum "$resume_terminal_path"
  macos_check_checksum "$resume_terminal_path"
fi
macos_recover_derived_sidecars "$release_path" "$cutback_state" "$source_host_id" "$recovery_generation" "$accepted_state"
macos_read_cutover_identity
[[ "$MACOS_DATASET_ID" == "$dataset_id" && "$MACOS_HOST_ID" == "$source_host_id" ]] || macos_die "source host identity does not match cutback lineage"
current_generation="$MACOS_WRITER_GENERATION"
[[ "$current_generation" == "$source_generation" || "$current_generation" == $(( target_generation + 1 )) ]] || macos_die "source identity is neither the original nor reconciled generation"
"$SCRIPT_DIR/Test-ReleaseBundle.zsh" --release-path "$release_path" >/dev/null
macos_verify_built_image_identity "$release_path"
# The outgoing source is intentionally retired while the pending cutover still
# names its original generation.  Do not grant a generic maintenance bypass to
# Start-Platform: only the database is needed to reconcile the DB-backed fence,
# and every public/application service must remain stopped until N+2 is durable.
macos_compose "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" up -d --no-build db
fence_json="$(macos_operational_lock_one_shot_capture "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" inspect-fence)"
fence_active="$(print -r -- "$fence_json" | plutil -extract active raw -o - 2>/dev/null || true)"
fence_dataset="$(print -r -- "$fence_json" | plutil -extract datasetId raw -o - 2>/dev/null || true)"
fence_host="$(print -r -- "$fence_json" | plutil -extract hostId raw -o - 2>/dev/null || true)"
fence_generation="$(print -r -- "$fence_json" | plutil -extract writerGeneration raw -o - 2>/dev/null || true)"
if [[ "$fence_active" == true && "$fence_dataset" == "$dataset_id" && "$fence_host" == "$source_host_id" && "$fence_generation" == "$source_generation" ]]; then
  transfer_result="$(macos_operational_lock_one_shot_capture "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" transfer-fence --dataset-id "$dataset_id" --source-host-id "$source_host_id" --source-writer-generation "$source_generation" --target-host-id "$target_host_id" --target-writer-generation "$target_generation" --reason host-cutback-prewrite-forward --ttl-seconds 86400)"
  [[ "$(print -r -- "$transfer_result" | plutil -extract active raw -o - 2>/dev/null || true)" == true && "$(print -r -- "$transfer_result" | plutil -extract datasetId raw -o - 2>/dev/null || true)" == "$dataset_id" && "$(print -r -- "$transfer_result" | plutil -extract hostId raw -o - 2>/dev/null || true)" == "$target_host_id" && "$(print -r -- "$transfer_result" | plutil -extract writerGeneration raw -o - 2>/dev/null || true)" == "$target_generation" ]] || macos_die "pre-write forward fence transfer was not verified"
elif [[ "$fence_active" == true && "$fence_dataset" == "$dataset_id" && "$fence_host" == "$target_host_id" && "$fence_generation" == "$target_generation" ]]; then
  : # Forward transfer already committed before a crash; continue idempotently.
elif [[ "$fence_active" == true && "$fence_dataset" == "$dataset_id" && "$fence_host" == "$source_host_id" && "$fence_generation" == "$reconciled_generation" ]]; then
  : # Both transfers already committed before a crash; reconcile/release only.
elif [[ "$fence_active" == false && "$fence_dataset" == "$dataset_id" && "$fence_host" == "$source_host_id" && "$fence_generation" == "$reconciled_generation" ]]; then
  fence_reconciled_released=1
else
  macos_die "pre-write resume fence is neither source-active nor target-active"
fi
fence_json="$(macos_operational_lock_one_shot_capture "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" inspect-fence)"
fence_active="$(print -r -- "$fence_json" | plutil -extract active raw -o - 2>/dev/null || true)"
fence_dataset="$(print -r -- "$fence_json" | plutil -extract datasetId raw -o - 2>/dev/null || true)"
fence_host="$(print -r -- "$fence_json" | plutil -extract hostId raw -o - 2>/dev/null || true)"
fence_generation="$(print -r -- "$fence_json" | plutil -extract writerGeneration raw -o - 2>/dev/null || true)"
if [[ "$fence_active" == true && "$fence_dataset" == "$dataset_id" && "$fence_host" == "$target_host_id" && "$fence_generation" == "$target_generation" ]]; then
  reverse_transfer_result="$(macos_operational_lock_one_shot_capture "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" transfer-fence --dataset-id "$dataset_id" --source-host-id "$target_host_id" --source-writer-generation "$target_generation" --target-host-id "$source_host_id" --target-writer-generation "$reconciled_generation" --reason host-cutback-prewrite-reverse --ttl-seconds 86400)"
  [[ "$(print -r -- "$reverse_transfer_result" | plutil -extract active raw -o - 2>/dev/null || true)" == true && "$(print -r -- "$reverse_transfer_result" | plutil -extract datasetId raw -o - 2>/dev/null || true)" == "$dataset_id" && "$(print -r -- "$reverse_transfer_result" | plutil -extract hostId raw -o - 2>/dev/null || true)" == "$source_host_id" && "$(print -r -- "$reverse_transfer_result" | plutil -extract writerGeneration raw -o - 2>/dev/null || true)" == "$reconciled_generation" ]] || macos_die "pre-write reverse fence transfer was not verified"
elif [[ "$fence_active" == true && "$fence_dataset" == "$dataset_id" && "$fence_host" == "$source_host_id" && "$fence_generation" == "$reconciled_generation" ]]; then
  : # Reverse transfer already committed before a crash; reconcile locally.
elif [[ "$fence_active" == false && "$fence_dataset" == "$dataset_id" && "$fence_host" == "$source_host_id" && "$fence_generation" == "$reconciled_generation" ]]; then
  fence_reconciled_released=1
else
  macos_die "pre-write resume fence is neither target-active nor reconciled source-active"
fi
macos_adopt_cutover_identity "$dataset_id" "$source_host_id" "$reconciled_generation"
macos_json_replace_atomic "$MACOS_CURRENT_STATE" writerGeneration "$reconciled_generation"
macos_write_checksum "$MACOS_CURRENT_STATE"
if [[ "${fence_reconciled_released:-0}" != 1 ]]; then
  release_result="$(macos_operational_lock_one_shot_capture "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" release-fence --dataset-id "$dataset_id" --host-id "$source_host_id" --writer-generation "$reconciled_generation")"
  [[ "$(print -r -- "$release_result" | plutil -extract active raw -o - 2>/dev/null || true)" == false && "$(print -r -- "$release_result" | plutil -extract datasetId raw -o - 2>/dev/null || true)" == "$dataset_id" && "$(print -r -- "$release_result" | plutil -extract hostId raw -o - 2>/dev/null || true)" == "$source_host_id" && "$(print -r -- "$release_result" | plutil -extract writerGeneration raw -o - 2>/dev/null || true)" == "$reconciled_generation" ]] || macos_die "source reconciled writer fence was not released"
fi
if (( resume_terminal_committed == 0 )); then
  MACOS_PARENT_LOCK_PID="$$" "$SCRIPT_DIR/Start-Platform.zsh" --root "$root" --maintenance --lock-held >/dev/null
  preflight_path="$MACOS_LAYOUT_EVIDENCE/source-resume-preflight-$(macos_timestamp)-$$.json"
  MACOS_PARENT_LOCK_PID="$$" "$SCRIPT_DIR/Test-FormalPreflight.zsh" --root "$root" --lock-held --target-maintenance --backup-path "$backup_path" --browser-smoke-evidence "$browser_evidence" --pf-evidence "$pf_evidence" --network-time-evidence "$network_time_evidence" --evidence-path "$preflight_path" >/dev/null
  macos_check_checksum "$preflight_path"
  [[ "$(macos_json_get "$preflight_path" status 2>/dev/null || true)" == passed ]] || macos_die "source resume preflight did not pass"
  MACOS_PARENT_LOCK_PID="$$" "$SCRIPT_DIR/Stop-Platform.zsh" --root "$root" --lock-held >/dev/null
  # The activation intent and readiness terminal are durable before public
  # exposure.  A crash after N+2 release but before this boundary leaves the
  # resume-pending barrier in place; a crash after it may be safely recovered.
  activation_intent_path="$MACOS_LAYOUT_EVIDENCE/source-cutback-activation-intent-$(macos_timestamp)-$$.json"
  macos_write_atomic "$activation_intent_path" "{\"schemaVersion\":1,\"kind\":\"source-cutback-activation-intent\",\"status\":\"intent\",\"activationIntent\":true,\"mode\":\"pre-write\",\"datasetId\":\"$dataset_id\",\"sourceHostId\":\"$source_host_id\",\"targetHostId\":\"$target_host_id\",\"acceptedStateSha256\":\"$accepted_digest\",\"cutbackStateSha256\":\"$cutback_digest\",\"sourceWriterGeneration\":$reconciled_generation,\"targetExposed\":false,\"targetWriteAccepted\":false,\"activationAttemptedAt\":\"$(macos_now_iso)\",\"approval\":\"manual-required\"}"
  macos_checksummed_json "$activation_intent_path"
  macos_write_atomic "$resume_terminal_path" "{\"schemaVersion\":1,\"kind\":\"source-cutback-resume-terminal\",\"status\":\"readiness-passed\",\"resumeIntentSha256\":\"$(macos_sha256 "$resume_intent_path")\",\"acceptedStateSha256\":\"$accepted_digest\",\"cutbackStateSha256\":\"$cutback_digest\",\"datasetId\":\"$dataset_id\",\"sourceHostId\":\"$source_host_id\",\"targetHostId\":\"$target_host_id\",\"reconciledWriterGeneration\":$reconciled_generation,\"preflightPath\":\"$(macos_json_escape "$preflight_path")\",\"preflightSha256\":\"$(macos_sha256 "$preflight_path")\",\"activationIntentPath\":\"$(macos_json_escape "$activation_intent_path")\",\"activationIntentSha256\":\"$(macos_sha256 "$activation_intent_path")\",\"createdAt\":\"$(macos_now_iso)\",\"approval\":\"manual-required\"}"
  macos_checksummed_json "$resume_terminal_path"
  validate_resume_terminal "$resume_terminal_path"
fi
MACOS_PARENT_LOCK_PID="$$" "$SCRIPT_DIR/Start-Platform.zsh" --root "$root" --lock-held >/dev/null
resume_path="$MACOS_LAYOUT_EVIDENCE/source-cutback-resume-$(macos_timestamp)-$$.json"
macos_write_atomic "$resume_path" "{\"schemaVersion\":1,\"kind\":\"source-cutback-resume\",\"status\":\"passed\",\"mode\":\"pre-write\",\"datasetId\":\"$dataset_id\",\"sourceHostId\":\"$source_host_id\",\"targetHostId\":\"$target_host_id\",\"acceptedStateSha256\":\"$accepted_digest\",\"cutbackStateSha256\":\"$(macos_sha256 "$cutback_state")\",\"preflightSha256\":\"$(macos_sha256 "$preflight_path")\",\"activationIntentSha256\":\"$(macos_sha256 "$activation_intent_path")\",\"sourceWriterGenerationBefore\":$source_generation,\"sourceWriterGeneration\":$reconciled_generation,\"targetWriterGeneration\":$target_generation,\"forwardTransferVerified\":true,\"reverseTransferVerified\":true,\"targetWriteAccepted\":false,\"dataRestorePerformed\":false,\"sourceReopened\":true,\"createdAt\":\"$(macos_now_iso)\",\"approval\":\"manual-required\"}"
macos_checksummed_json "$resume_path"
resume_status=passed
macos_log "source_cutback_resumed mode=pre-write dataset=$dataset_id writer_generation=$source_generation evidence=${resume_path:t} approval=manual-required"
