#!/bin/zsh
set -euo pipefail
setopt no_nomatch
umask 077

SCRIPT_DIR="${0:A:h}"
source "$SCRIPT_DIR/Common.zsh"

mode=""
accepted_state_arg=""
post_write_backup_arg=""
confirmation=""
root="${INTERNAL_EXAM_ROOT:-${HOME:?}/Library/Application Support/InternalExam}"

while (( $# > 0 )); do
  case "$1" in
    --mode) (( $# >= 2 )) || macos_die "--mode requires TargetNeverAcceptedWrites or TargetAcceptedWrites"; mode="$2"; shift 2 ;;
    --accepted-state|--state-path) (( $# >= 2 )) || macos_die "$1 requires a checksummed state path"; accepted_state_arg="$2"; shift 2 ;;
    --post-write-backup|--backup) (( $# >= 2 )) || macos_die "$1 requires a paired backup path"; post_write_backup_arg="$2"; shift 2 ;;
    --confirmation) (( $# >= 2 )) || macos_die "--confirmation requires exact text"; confirmation="$2"; shift 2 ;;
    --root) (( $# >= 2 )) || macos_die "--root requires a path"; root="$2"; shift 2 ;;
    -h|--help)
      print -r -- "usage: $0 --mode TargetNeverAcceptedWrites|TargetAcceptedWrites --accepted-state PATH [--post-write-backup PATH] --confirmation 'ROLLBACK HOST CUTOVER PRE-WRITE|POST-WRITE' [--root ROOT]"
      exit 0
      ;;
    *) macos_die "unknown argument: $1"; exit 1 ;;
  esac
done

macos_assert_macos
[[ "$mode" == TargetNeverAcceptedWrites || "$mode" == TargetAcceptedWrites ]] || macos_die "invalid host cutover rollback mode"
[[ -n "$accepted_state_arg" ]] || macos_die "--accepted-state is required"
if [[ "$mode" == TargetNeverAcceptedWrites ]]; then
  [[ "$confirmation" == 'ROLLBACK HOST CUTOVER PRE-WRITE' ]] || macos_die "exact pre-write rollback confirmation did not match"
  [[ -z "$post_write_backup_arg" ]] || macos_die "pre-write rollback must not restore a backup"
else
  [[ "$confirmation" == 'ROLLBACK HOST CUTOVER POST-WRITE' ]] || macos_die "exact post-write rollback confirmation did not match"
fi

macos_assert_outside_worktree "$root" >/dev/null
macos_layout "$root"
macos_assert_protected_configuration "$root"
macos_require_formal_paths
macos_docker_ready
macos_acquire_lock "$MACOS_LAYOUT_STATE/.operation.lock"
rollback_status=failed
rollback_intent_path=""
cleanup_rollback() {
  if [[ -n "${rollback_intent_path:-}" && -f "$rollback_intent_path" && "$rollback_status" != passed ]]; then
    # Once rollback intent is durable, the old Accept path is superseded.  A
    # failed attempt therefore leaves the target stopped rather than silently
    # reopening the stale writer on a retry.
    macos_compose "${release_path:-}" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" stop >/dev/null 2>&1 || true
  fi
  macos_release_lock
}
trap cleanup_rollback EXIT

macos_release_state "$MACOS_CURRENT_STATE"
release_path="$MACOS_STATE_PATH"
release_version="$MACOS_STATE_VERSION"
release_commit="$MACOS_STATE_COMMIT"
"$SCRIPT_DIR/Test-ReleaseBundle.zsh" --release-path "$release_path" >/dev/null
macos_verify_built_image_identity "$release_path"

accepted_state="$(macos_resolve_path "$accepted_state_arg")"
[[ "${accepted_state:h}" == "$MACOS_LAYOUT_STATE" ]] || macos_die "accepted cutover state must stay in the protected state directory"
[[ "$accepted_state" != *.consumed.json ]] || macos_die "a consumed state cannot be used for cutback"
[[ -f "$accepted_state" && -f "$accepted_state.sha256" ]] || macos_die "accepted cutover state is not checksummed"
macos_secure_path "$accepted_state"
macos_check_checksum "$accepted_state"
plutil -convert json -o - -- "$accepted_state" >/dev/null 2>&1 || macos_die "accepted cutover state is invalid JSON"

accepted_phase="$(macos_json_get "$accepted_state" state 2>/dev/null || macos_json_get "$accepted_state" phase 2>/dev/null || true)"
[[ "$accepted_phase" == prepared || "$accepted_phase" == accepted ]] || macos_die "accepted cutover state is not prepared or accepted"
dataset_id="$(macos_json_get "$accepted_state" dataset_id 2>/dev/null || macos_json_get "$accepted_state" datasetId 2>/dev/null || true)"
target_host_id="$(macos_json_get "$accepted_state" target_host_id 2>/dev/null || macos_json_get "$accepted_state" targetHostId 2>/dev/null || true)"
source_host_id="$(macos_json_get "$accepted_state" source_host_id 2>/dev/null || macos_json_get "$accepted_state" sourceHostId 2>/dev/null || true)"
accepted_generation="$(macos_json_get "$accepted_state" target_writer_generation 2>/dev/null || macos_json_get "$accepted_state" targetWriterGeneration 2>/dev/null || macos_json_get "$accepted_state" writer_generation 2>/dev/null || macos_json_get "$accepted_state" writerGeneration 2>/dev/null || true)"
accepted_write="$(macos_json_get "$accepted_state" target_write_accepted 2>/dev/null || macos_json_get "$accepted_state" targetWriteAccepted 2>/dev/null || true)"
accepted_boundary="$(macos_json_get "$accepted_state" last_write_at 2>/dev/null || macos_json_get "$accepted_state" lastWriteAt 2>/dev/null || macos_json_get "$accepted_state" updated_at 2>/dev/null || macos_json_get "$accepted_state" updatedAt 2>/dev/null || macos_json_get "$accepted_state" created_at 2>/dev/null || macos_json_get "$accepted_state" createdAt 2>/dev/null || true)"
[[ "$dataset_id" =~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$' && "$target_host_id" =~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$' && "$source_host_id" =~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$' ]] || macos_die "cutover identity is invalid"
[[ "$source_host_id" != "$target_host_id" ]] || macos_die "source and target host identities must differ"
[[ "$accepted_generation" =~ '^[1-9][0-9]*$' ]] || macos_die "cutover writer generation is invalid"
[[ "$accepted_boundary" =~ '^[0-9]{4}-' ]] || macos_die "cutover state has no write boundary"
macos_epoch_from_iso "$accepted_boundary" >/dev/null

# A rollback is executed on the target.  Never create a new identity here: a
# missing or mismatching protected identity is a hard stop, not an invitation
# to claim the source dataset.
identity_path="$MACOS_LAYOUT_STATE/host-identity.json"
[[ -f "$identity_path" && -f "$identity_path.sha256" ]] || macos_die "target host identity is missing"
macos_secure_path "$identity_path"
macos_check_checksum "$identity_path"
[[ "$(macos_json_get "$identity_path" datasetId 2>/dev/null || true)" == "$dataset_id" ]] || macos_die "target dataset lineage does not match host identity"
[[ "$(macos_json_get "$identity_path" hostId 2>/dev/null || true)" == "$target_host_id" ]] || macos_die "target host identity does not match accepted cutover state"
identity_generation="$(macos_json_get "$identity_path" writerGeneration 2>/dev/null || true)"
[[ "$identity_generation" =~ '^[1-9][0-9]*$' && "$identity_generation" == "$accepted_generation" ]] || macos_die "target host writer generation does not match accepted cutover state"

accepted_digest="$(macos_sha256 "$accepted_state")"
activation_found=0
for activation_candidate in "$MACOS_LAYOUT_EVIDENCE"/cutover-activation-*.json(Nom[1]) "$MACOS_LAYOUT_EVIDENCE"/cutover-activation-intent-*.json(Nom[1]); do
  [[ -f "$activation_candidate" && -f "$activation_candidate.sha256" ]] || continue
  macos_check_checksum "$activation_candidate" || continue
  activation_status="$(macos_json_get "$activation_candidate" status 2>/dev/null || true)"
  [[ "$activation_status" == passed || "$activation_status" == intent ]] || continue
  [[ "$(macos_json_get "$activation_candidate" acceptedStateSha256 2>/dev/null || true)" == "$accepted_digest" ]] || continue
  [[ "$(macos_json_get "$activation_candidate" datasetId 2>/dev/null || true)" == "$dataset_id" ]] || continue
  [[ "$(macos_json_get "$activation_candidate" hostId 2>/dev/null || true)" == "$target_host_id" ]] || continue
  [[ "$(macos_json_get "$activation_candidate" writerGeneration 2>/dev/null || true)" == "$accepted_generation" ]] || continue
  if [[ "$activation_status" == intent ]]; then
    [[ "$(macos_json_get "$activation_candidate" activationIntent 2>/dev/null || true)" == true ]] || continue
  else
    [[ "$(macos_json_get "$activation_candidate" targetExposed 2>/dev/null || true)" == true && "$(macos_json_get "$activation_candidate" targetWriteAccepted 2>/dev/null || true)" == true ]] || continue
  fi
  activation_found=1
  break
done
if (( activation_found == 1 )); then
  [[ "$mode" == TargetAcceptedWrites ]] || macos_die "public target activation requires post-write rollback"
else
  case "$mode:$accepted_write" in
    TargetNeverAcceptedWrites:false|TargetNeverAcceptedWrites:0|TargetAcceptedWrites:true|TargetAcceptedWrites:1) ;;
    *) macos_die "rollback mode does not match target_write_accepted state" ;;
  esac
fi
if [[ "$mode" == TargetAcceptedWrites ]]; then
  [[ "$accepted_phase" == accepted ]] || macos_die "post-write rollback requires an accepted cutover state"
fi

accepted_digest="$(macos_sha256 "$accepted_state")"
source_generation=$(( accepted_generation - 1 ))
if [[ "$mode" == TargetNeverAcceptedWrites ]]; then
  (( source_generation >= 1 )) || macos_die "pre-write cutback source writer generation is invalid"
fi
rollback_intent_path="$MACOS_LAYOUT_STATE/cutover-rollback-intent-${accepted_digest}.json"
rollback_terminal_path="$MACOS_LAYOUT_STATE/cutover-rollback-terminal-${accepted_digest}.json"
rollback_handoff_path=""
rollback_intent_existing=0

rollback_find_handoff() {
  local terminal_path="$1" expected_digest="$2" candidate candidate_digest
  rollback_handoff_path="$(macos_json_get "$terminal_path" handoffStatePath 2>/dev/null || true)"
  if [[ -n "$rollback_handoff_path" ]]; then
    rollback_handoff_path="$(macos_resolve_path "$rollback_handoff_path")"
    [[ "$rollback_handoff_path" == "$MACOS_LAYOUT_STATE"/* ]] || macos_die "rollback terminal handoff is outside protected state" || return 1
  else
    # Older terminal records did not persist the path.  Recover it only by
    # exact checksum match among the two wrapper-owned handoff families.
    for candidate in "$MACOS_LAYOUT_STATE"/cutover-prepared-reverse-*.json(N) "$MACOS_LAYOUT_STATE"/cutback-*.json(N); do
      [[ -f "$candidate" && -f "$candidate.sha256" ]] || continue
      macos_check_checksum "$candidate" >/dev/null 2>&1 || continue
      candidate_digest="$(macos_sha256 "$candidate")"
      if [[ "$candidate_digest" == "$expected_digest" ]]; then
        rollback_handoff_path="$candidate"
        break
      fi
    done
  fi
  [[ -n "$rollback_handoff_path" && -f "$rollback_handoff_path" && -f "$rollback_handoff_path.sha256" ]] || macos_die "rollback terminal handoff is missing" || return 1
  macos_secure_path "$rollback_handoff_path"
  macos_check_checksum "$rollback_handoff_path"
  [[ "$(macos_sha256 "$rollback_handoff_path")" == "$expected_digest" ]] || macos_die "rollback terminal handoff checksum does not match" || return 1
}

rollback_validate_terminal() {
  [[ -f "$rollback_terminal_path" ]] || macos_die "rollback terminal record is incomplete" || return 1
  macos_secure_path "$rollback_terminal_path"
  plutil -convert json -o - -- "$rollback_terminal_path" >/dev/null 2>&1 || macos_die "rollback terminal record is invalid JSON" || return 1
  [[ "$(macos_json_get "$rollback_terminal_path" status 2>/dev/null || true)" == terminal ]] || macos_die "rollback terminal record status is invalid" || return 1
  [[ "$(macos_json_get "$rollback_terminal_path" acceptedStateSha256 2>/dev/null || true)" == "$accepted_digest" ]] || macos_die "rollback terminal identity does not match accepted state" || return 1
  [[ "$(macos_json_get "$rollback_terminal_path" datasetId 2>/dev/null || true)" == "$dataset_id" && "$(macos_json_get "$rollback_terminal_path" targetHostId 2>/dev/null || true)" == "$target_host_id" ]] || macos_die "rollback terminal host lineage does not match accepted state" || return 1
  [[ "$(macos_json_get "$rollback_terminal_path" writerGeneration 2>/dev/null || true)" == "$accepted_generation" && "$(macos_json_get "$rollback_terminal_path" mode 2>/dev/null || true)" == "$mode" ]] || macos_die "rollback terminal mode or generation does not match request" || return 1
  terminal_handoff_digest="$(macos_json_get "$rollback_terminal_path" handoffStateSha256 2>/dev/null || true)"
  [[ "$terminal_handoff_digest" =~ '^[0-9a-fA-F]{64}$' ]] || macos_die "rollback terminal handoff digest is invalid" || return 1
  if [[ ! -f "$rollback_terminal_path.sha256" ]]; then
    # The JSON rename may have committed immediately before its derived
    # checksum.  Repair only this wrapper-owned sidecar after validating the
    # exact identity fields above.
    macos_write_checksum "$rollback_terminal_path"
  fi
  macos_check_checksum "$rollback_terminal_path"
  rollback_find_handoff "$rollback_terminal_path" "$terminal_handoff_digest"
}

if [[ -e "$rollback_terminal_path" || -e "$rollback_terminal_path.sha256" ]]; then
  rollback_validate_terminal
  rollback_status=passed
  macos_log "host_cutback_already_complete mode=$mode state=${rollback_handoff_path:t} approval=manual-required"
  exit 0
fi

if [[ -e "$rollback_intent_path" || -e "$rollback_intent_path.sha256" ]]; then
  [[ -f "$rollback_intent_path" ]] || macos_die "rollback intent is incomplete"
  macos_secure_path "$rollback_intent_path"
  plutil -convert json -o - -- "$rollback_intent_path" >/dev/null 2>&1 || macos_die "rollback intent is invalid JSON"
  [[ "$(macos_json_get "$rollback_intent_path" status 2>/dev/null || true)" == intent ]] || macos_die "rollback intent status is invalid"
  [[ "$(macos_json_get "$rollback_intent_path" acceptedStateSha256 2>/dev/null || true)" == "$accepted_digest" ]] || macos_die "rollback intent identity does not match accepted state"
  [[ "$(macos_json_get "$rollback_intent_path" datasetId 2>/dev/null || true)" == "$dataset_id" && "$(macos_json_get "$rollback_intent_path" targetHostId 2>/dev/null || true)" == "$target_host_id" ]] || macos_die "rollback intent host lineage does not match accepted state"
  [[ "$(macos_json_get "$rollback_intent_path" writerGeneration 2>/dev/null || true)" == "$accepted_generation" && "$(macos_json_get "$rollback_intent_path" mode 2>/dev/null || true)" == "$mode" ]] || macos_die "rollback intent mode or generation does not match request"
  [[ -f "$rollback_intent_path.sha256" ]] || macos_write_checksum "$rollback_intent_path"
  macos_check_checksum "$rollback_intent_path"
  rollback_intent_existing=1
else
  macos_write_atomic "$rollback_intent_path" "{\"schemaVersion\":1,\"kind\":\"formal-cutover-rollback-intent\",\"status\":\"intent\",\"supersedesAcceptedState\":true,\"acceptedStateSha256\":\"$accepted_digest\",\"datasetId\":\"$dataset_id\",\"targetHostId\":\"$target_host_id\",\"writerGeneration\":$accepted_generation,\"mode\":\"$mode\",\"createdAt\":\"$(macos_now_iso)\",\"approval\":\"manual-required\"}"
  macos_checksummed_json "$rollback_intent_path"
fi

# A prior failed accept/rollback may have stopped the whole project.  The
# writer-fence and final-backup one-shots require a live DB connection, so
# start only postgres before inspecting/reacquiring the target fence; the full
# project is stopped and proven below before any handoff is emitted.
macos_compose "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" up -d --no-build db

# Even a target that never accepted formal writes must reacquire its released
# target-generation fence before the cutback stop proof.  This prevents the
# target database from being reopened with stale N+1 identity while the source
# consumes the pre-write cutback state.  The fence intentionally remains held
# after this command; source-side Resume performs the generation reconciliation
# and owns the subsequent reopen decision.
if [[ "$mode" == TargetNeverAcceptedWrites ]]; then
  fence_json="$(macos_operational_lock_one_shot_capture "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" inspect-fence)"
  fence_active="$(print -r -- "$fence_json" | plutil -extract active raw -o - 2>/dev/null || true)"
  fence_dataset="$(print -r -- "$fence_json" | plutil -extract datasetId raw -o - 2>/dev/null || true)"
  fence_host="$(print -r -- "$fence_json" | plutil -extract hostId raw -o - 2>/dev/null || true)"
  fence_generation="$(print -r -- "$fence_json" | plutil -extract writerGeneration raw -o - 2>/dev/null || true)"
  if [[ "$fence_active" == true ]]; then
    [[ "$fence_dataset" == "$dataset_id" && "$fence_host" == "$target_host_id" && "$fence_generation" == "$accepted_generation" ]] || macos_die "active target fence does not match pre-write cutback identity"
  else
    [[ "$fence_dataset" == "$dataset_id" && "$fence_host" == "$target_host_id" && "$fence_generation" == "$accepted_generation" ]] || macos_die "released target fence identity is not the accepted target"
    fence_result="$(macos_operational_lock_one_shot_capture "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" acquire-fence --dataset-id "$dataset_id" --host-id "$target_host_id" --writer-generation "$accepted_generation" --reason host-cutback-prewrite --ttl-seconds 86400)"
    [[ "$(print -r -- "$fence_result" | plutil -extract active raw -o - 2>/dev/null || true)" == true && "$(print -r -- "$fence_result" | plutil -extract datasetId raw -o - 2>/dev/null || true)" == "$dataset_id" && "$(print -r -- "$fence_result" | plutil -extract hostId raw -o - 2>/dev/null || true)" == "$target_host_id" && "$(print -r -- "$fence_result" | plutil -extract writerGeneration raw -o - 2>/dev/null || true)" == "$accepted_generation" ]] || macos_die "target pre-write cutback fence was not acquired"
  fi
fi

backup_path=""
backup_id=""
backup_digest=""
backup_created_at=""
backup_generation=""
second_copy_evidence=""
post_write_phase="$MACOS_LAYOUT_STATE/cutback-postwrite-${accepted_digest}.json"
post_write_phase_reuse=0
validate_post_write_phase_journal() {
  local journal_path="$1" journal_backup journal_manifest journal_evidence journal_backup_id
  macos_secure_path "$journal_path"
  plutil -convert json -o - -- "$journal_path" >/dev/null 2>&1 || macos_die "post-write cutback phase journal is invalid"
  [[ "$(macos_json_get "$journal_path" schemaVersion 2>/dev/null || true)" == 1 ]] || macos_die "post-write cutback phase schema is invalid"
  [[ "$(macos_json_get "$journal_path" kind 2>/dev/null || true)" == host-cutback-postwrite-phase ]] || macos_die "post-write cutback phase kind is invalid"
  [[ "$(macos_json_get "$journal_path" status 2>/dev/null || true)" == final-backup-passed ]] || macos_die "post-write cutback phase is not resumable"
  [[ "$(macos_json_get "$journal_path" acceptedStateSha256 2>/dev/null || true)" == "$accepted_digest" ]] || macos_die "post-write cutback phase does not match accepted state"
  [[ "$(macos_json_get "$journal_path" datasetId 2>/dev/null || true)" == "$dataset_id" ]] || macos_die "post-write cutback phase dataset changed"
  [[ "$(macos_json_get "$journal_path" targetHostId 2>/dev/null || true)" == "$target_host_id" ]] || macos_die "post-write cutback phase target changed"
  [[ "$(macos_json_get "$journal_path" writerGeneration 2>/dev/null || true)" == "$accepted_generation" ]] || macos_die "post-write cutback phase generation changed"
  journal_backup="$(macos_json_get "$journal_path" backupPath 2>/dev/null || true)"
  [[ -n "$journal_backup" ]] || macos_die "post-write cutback phase has no final backup"
  journal_backup="$(macos_assert_backup "$journal_backup")"
  [[ "$journal_backup" == "$MACOS_LAYOUT_BACKUPS"/* ]] || macos_die "post-write phase backup is outside the protected backup root"
  journal_backup_id="$(macos_json_get "$journal_path" backupId 2>/dev/null || true)"
  [[ "$journal_backup_id" == "${journal_backup:t}" ]] || macos_die "post-write phase backup identity changed"
  journal_manifest="$journal_backup/manifest.json"
  [[ "$(macos_sha256 "$journal_manifest")" == "$(macos_json_get "$journal_path" backupManifestSha256 2>/dev/null || true)" ]] || macos_die "post-write phase backup manifest changed"
  journal_evidence="$journal_backup:h/${journal_backup:t}.second-copy.json"
  [[ -f "$journal_evidence" && -f "$journal_evidence.sha256" ]] || macos_die "post-write phase second-copy evidence is missing"
  macos_check_checksum "$journal_evidence"
  [[ "$(macos_sha256 "$journal_evidence")" == "$(macos_json_get "$journal_path" secondCopyEvidenceSha256 2>/dev/null || true)" ]] || macos_die "post-write phase second-copy evidence changed"
  [[ "$(macos_json_get "$journal_evidence" status 2>/dev/null || true)" == passed ]] || macos_die "post-write phase second-copy evidence did not pass"
  typeset -g post_write_backup_arg="$journal_backup"
}
if [[ "$mode" == TargetAcceptedWrites && ( -e "$post_write_phase" || -e "$post_write_phase.sha256" ) ]]; then
  [[ -f "$post_write_phase" ]] || macos_die "post-write cutback phase journal is incomplete"
  if [[ ! -f "$post_write_phase.sha256" ]]; then
    # This is a derived wrapper journal.  A crash after the JSON rename may
    # leave no sidecar; repair it only after the accepted lineage, complete
    # cutover backup and exact second-copy evidence all still match.  A
    # present-but-invalid sidecar is corruption, not a repair opportunity.
    validate_post_write_phase_journal "$post_write_phase"
    macos_write_checksum "$post_write_phase"
  fi
  macos_check_checksum "$post_write_phase"
  validate_post_write_phase_journal "$post_write_phase"
  post_write_phase_reuse=1
fi
if [[ "$mode" == TargetAcceptedWrites ]]; then
  fence_json="$(macos_operational_lock_one_shot_capture "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" inspect-fence)"
  fence_active="$(print -r -- "$fence_json" | plutil -extract active raw -o - 2>/dev/null || true)"
  fence_dataset="$(print -r -- "$fence_json" | plutil -extract datasetId raw -o - 2>/dev/null || true)"
  fence_host="$(print -r -- "$fence_json" | plutil -extract hostId raw -o - 2>/dev/null || true)"
  fence_generation="$(print -r -- "$fence_json" | plutil -extract writerGeneration raw -o - 2>/dev/null || true)"
  if [[ "$fence_active" == true ]]; then
    [[ "$fence_dataset" == "$dataset_id" && "$fence_host" == "$target_host_id" && "$fence_generation" == "$accepted_generation" ]] || macos_die "post-write target fence identity is invalid"
  else
    fence_result="$(macos_operational_lock_one_shot_capture "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" acquire-fence --dataset-id "$dataset_id" --host-id "$target_host_id" --writer-generation "$accepted_generation" --reason host-cutback-prepare --ttl-seconds 86400)"
    [[ "$(print -r -- "$fence_result" | plutil -extract active raw -o - 2>/dev/null || true)" == true && "$(print -r -- "$fence_result" | plutil -extract datasetId raw -o - 2>/dev/null || true)" == "$dataset_id" && "$(print -r -- "$fence_result" | plutil -extract hostId raw -o - 2>/dev/null || true)" == "$target_host_id" && "$(print -r -- "$fence_result" | plutil -extract writerGeneration raw -o - 2>/dev/null || true)" == "$accepted_generation" ]] || macos_die "post-write target fence was not acquired"
  fi
  fence_acquired=1
  if (( post_write_phase_reuse == 0 )); then
    backup_output="$(MACOS_PARENT_LOCK_PID="$$" "$SCRIPT_DIR/Invoke-PairedBackup.zsh" --root "$root" --kind cutover --under-writer-fence --lock-held)"
    [[ "$backup_output" =~ "(backup-[0-9]{8}T[0-9]{6}Z)" ]] || macos_die "fenced reverse cutover backup did not return an id"
    backup_id="${match[1]}"
    [[ "$backup_output" == *"status=passed"* && "$backup_output" == *"second_copy=passed"* ]] || macos_die "fenced reverse cutover backup did not pass local and second-copy verification"
    post_write_backup_arg="$MACOS_LAYOUT_BACKUPS/$backup_id"
  fi
fi
if [[ "$mode" == TargetAcceptedWrites ]]; then
  backup_path="$(macos_assert_backup "$post_write_backup_arg")"
  [[ "$backup_path" == "$MACOS_LAYOUT_BACKUPS"/* ]] || macos_die "post-write backup must be under the protected backup root"
  macos_assert_outside_worktree "$backup_path" >/dev/null
  backup_manifest="$backup_path/manifest.json"
  [[ -f "$backup_manifest" ]] || macos_die "post-write backup manifest is missing"
  plutil -convert json -o - -- "$backup_manifest" >/dev/null 2>&1 || macos_die "post-write backup manifest is invalid"
  backup_id="$(macos_json_get "$backup_manifest" backup_id 2>/dev/null || print -r -- "${backup_path:t}")"
  backup_kind="$(macos_json_get "$backup_manifest" backup_kind 2>/dev/null || true)"
  [[ "$backup_kind" == cutover ]] || macos_die "post-write rollback requires an internally created cutover paired backup"
  [[ "$(macos_json_get "$backup_manifest" dataset_id 2>/dev/null || true)" == "$dataset_id" ]] || macos_die "post-write backup dataset identity does not match"
  [[ "$(macos_json_get "$backup_manifest" source_host_id 2>/dev/null || true)" == "$target_host_id" ]] || macos_die "post-write backup host identity does not match target"
  backup_generation="$(macos_json_get "$backup_manifest" writer_generation 2>/dev/null || true)"
  # Ordinary writes remain in the accepted writer generation; the reverse
  # cutover prepared state advances it exactly once for the source transfer.
  [[ "$backup_generation" =~ '^[1-9][0-9]*$' && "$backup_generation" == "$accepted_generation" ]] || macos_die "post-write backup writer generation does not match accepted writer"
  backup_created_at="$(macos_json_get "$backup_manifest" created_at 2>/dev/null || macos_json_get "$backup_manifest" createdAt 2>/dev/null || true)"
  [[ -n "$backup_created_at" ]] || macos_die "post-write backup creation boundary is missing"
  backup_epoch="$(macos_epoch_from_iso "$backup_created_at")"
  boundary_epoch="$(macos_epoch_from_iso "$accepted_boundary")"
  (( backup_epoch > boundary_epoch )) || macos_die "post-write backup is not newer than the accepted/write boundary"
  backup_digest="$(macos_sha256 "$backup_manifest")"

  # Reject an older target backup when a newer post-write artifact exists.
  # This avoids a plausible but stale paired backup being used to cut back.
  for candidate in "$MACOS_LAYOUT_BACKUPS"/backup-*(N/); do
    [[ "$candidate" == "$backup_path" ]] && continue
    candidate_manifest="$candidate/manifest.json"
    [[ -f "$candidate_manifest" ]] || continue
    candidate_kind="$(macos_json_get "$candidate_manifest" backup_kind 2>/dev/null || true)"
    [[ "$candidate_kind" == cutover ]] || continue
    candidate_dataset="$(macos_json_get "$candidate_manifest" dataset_id 2>/dev/null || true)"
    [[ "$candidate_dataset" == "$dataset_id" ]] || continue
    candidate_created="$(macos_json_get "$candidate_manifest" created_at 2>/dev/null || true)"
    [[ -n "$candidate_created" ]] || continue
    candidate_epoch="$(macos_epoch_from_iso "$candidate_created" 2>/dev/null || print -r -- 0)"
    (( candidate_epoch <= backup_epoch )) || macos_die "supplied post-write backup is not the latest target backup"
  done

  second_copy_root="$(macos_formal_value SECOND_COPY_PATH)"
  macos_assert_outside_worktree "$second_copy_root" >/dev/null
  macos_assert_second_copy_storage "$second_copy_root"
  [[ -d "$second_copy_root/$backup_id" ]] || macos_die "encrypted second-copy backup is missing"
  second_copy_evidence="$backup_path:h/${backup_path:t}.second-copy.json"
  [[ -f "$second_copy_evidence" && -f "$second_copy_evidence.sha256" ]] || macos_die "second-copy evidence is missing"
  macos_check_checksum "$second_copy_evidence"
  [[ "$(macos_json_get "$second_copy_evidence" status 2>/dev/null || true)" == passed ]] || macos_die "second-copy evidence did not pass"
  [[ "$(macos_json_get "$second_copy_evidence" backup_id 2>/dev/null || macos_json_get "$second_copy_evidence" artifact_id 2>/dev/null || true)" == "$backup_id" ]] || macos_die "second-copy evidence backup identity does not match"

  # Validate both copies through the versioned application image.  The host
  # adapter never substitutes a host Python/internal-backup implementation.
  macos_backend_one_shot_with_mounts "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" \
    --volume "$backup_path:/portable-backup:ro" \
    validate-migration-input /portable-backup
  macos_internal_backup_one_shot_with_mounts "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" \
    --volume "$backup_path:/portable-backup:ro" inspect /portable-backup
  macos_backend_one_shot_with_mounts "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" \
    --volume "$second_copy_root:/second-copy:ro" \
    validate-migration-input "/second-copy/$backup_id"
  macos_internal_backup_one_shot_with_mounts "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" \
    --volume "$second_copy_root:/second-copy:ro" inspect "/second-copy/$backup_id"
  if (( post_write_phase_reuse == 0 )); then
    macos_write_atomic "$post_write_phase" "{\"schemaVersion\":1,\"kind\":\"host-cutback-postwrite-phase\",\"status\":\"final-backup-passed\",\"acceptedStateSha256\":\"$accepted_digest\",\"datasetId\":\"$dataset_id\",\"targetHostId\":\"$target_host_id\",\"writerGeneration\":$accepted_generation,\"backupId\":\"$backup_id\",\"backupPath\":\"$(macos_json_escape "$backup_path")\",\"backupManifestSha256\":\"$backup_digest\",\"secondCopyEvidenceSha256\":\"$(macos_sha256 "$second_copy_evidence")\",\"createdAt\":\"$(macos_now_iso)\"}"
    macos_checksummed_json "$post_write_phase"
  fi
fi

# The reverse canonical prepared state is backend-owned.  Keep a durable
# reservation for its exact path before invoking the backend, then bind the
# resulting bytes into a separate immutable, checksummed phase journal.  A
# retry can therefore recover every crash window without choosing a second
# timestamped canonical state.
reverse_state=""
reverse_state_digest=""
reverse_intent_path=""
reverse_phase_path=""
reverse_created_at=""
validate_reverse_prepared_state() {
  local state_path="$1" repair_missing_sidecar="${2:-0}" expected_reverse_generation
  [[ "$state_path" == "$MACOS_LAYOUT_STATE"/* ]] || macos_die "reverse canonical state is outside the protected state directory"
  [[ -f "$state_path" ]] || macos_die "reverse canonical prepared state is missing"
  macos_secure_path "$state_path"
  plutil -convert json -o - -- "$state_path" >/dev/null 2>&1 || macos_die "reverse canonical prepared state is invalid JSON"
  expected_reverse_generation=$(( accepted_generation + 1 ))
  [[ "$(macos_json_get "$state_path" schema_version 2>/dev/null || macos_json_get "$state_path" schemaVersion 2>/dev/null || true)" == 1 ]] || macos_die "reverse canonical prepared state schema is invalid"
  [[ "$(macos_json_get "$state_path" kind 2>/dev/null || true)" == formal-cutover ]] || macos_die "reverse canonical prepared state kind is invalid"
  [[ "$(macos_json_get "$state_path" state 2>/dev/null || true)" == prepared ]] || macos_die "reverse canonical prepared state is not prepared"
  [[ "$(macos_json_get "$state_path" dataset_id 2>/dev/null || macos_json_get "$state_path" datasetId 2>/dev/null || true)" == "$dataset_id" ]] || macos_die "reverse canonical prepared state dataset changed"
  [[ "$(macos_json_get "$state_path" source_host_id 2>/dev/null || macos_json_get "$state_path" sourceHostId 2>/dev/null || true)" == "$target_host_id" ]] || macos_die "reverse canonical prepared state source changed"
  [[ "$(macos_json_get "$state_path" target_host_id 2>/dev/null || macos_json_get "$state_path" targetHostId 2>/dev/null || true)" == "$source_host_id" ]] || macos_die "reverse canonical prepared state target changed"
  [[ "$(macos_json_get "$state_path" writer_generation 2>/dev/null || macos_json_get "$state_path" writerGeneration 2>/dev/null || true)" == "$accepted_generation" ]] || macos_die "reverse canonical prepared state writer generation changed"
  [[ "$(macos_json_get "$state_path" source_writer_generation 2>/dev/null || macos_json_get "$state_path" sourceWriterGeneration 2>/dev/null || true)" == "$accepted_generation" ]] || macos_die "reverse canonical prepared state source generation changed"
  [[ "$(macos_json_get "$state_path" target_writer_generation 2>/dev/null || macos_json_get "$state_path" targetWriterGeneration 2>/dev/null || true)" == "$expected_reverse_generation" ]] || macos_die "reverse canonical prepared state target generation changed"
  [[ "$(macos_json_get "$state_path" backup_id 2>/dev/null || macos_json_get "$state_path" backupId 2>/dev/null || true)" == "$backup_id" ]] || macos_die "reverse canonical prepared state backup identity changed"
  [[ "$(macos_json_get "$state_path" source_project 2>/dev/null || macos_json_get "$state_path" sourceProject 2>/dev/null || true)" == "$MACOS_FORMAL_PROJECT" && "$(macos_json_get "$state_path" target_project 2>/dev/null || macos_json_get "$state_path" targetProject 2>/dev/null || true)" == "$MACOS_FORMAL_PROJECT" ]] || macos_die "reverse canonical prepared state project identity changed"
  [[ "$(macos_json_get "$state_path" source_quiescent 2>/dev/null || macos_json_get "$state_path" sourceQuiescent 2>/dev/null || true)" == true && "$(macos_json_get "$state_path" source_fully_stopped 2>/dev/null || macos_json_get "$state_path" sourceFullyStopped 2>/dev/null || true)" == true ]] || macos_die "reverse canonical prepared state lacks a stopped-source proof"
  [[ "$(macos_json_get "$state_path" target_exposed 2>/dev/null || macos_json_get "$state_path" targetExposed 2>/dev/null || true)" == false && "$(macos_json_get "$state_path" target_write_accepted 2>/dev/null || macos_json_get "$state_path" targetWriteAccepted 2>/dev/null || true)" == false ]] || macos_die "reverse canonical prepared state has an open write boundary"
  if [[ -f "$state_path.sha256" ]]; then
    macos_check_checksum "$state_path"
  elif (( repair_missing_sidecar == 1 )); then
    # The canonical JSON is never recreated.  Repair only its derived sidecar
    # after all immutable semantic bindings above have matched.
    macos_write_checksum "$state_path"
  fi
}

validate_reverse_intent_journal() {
  local journal_path="$1" journal_state journal_digest journal_created_at
  macos_secure_path "$journal_path"
  plutil -convert json -o - -- "$journal_path" >/dev/null 2>&1 || macos_die "reverse cutback intent journal is invalid"
  [[ "$(macos_json_get "$journal_path" schemaVersion 2>/dev/null || true)" == 1 ]] || macos_die "reverse cutback intent journal schema is invalid"
  [[ "$(macos_json_get "$journal_path" kind 2>/dev/null || true)" == formal-cutover-rollback-reverse-intent ]] || macos_die "reverse cutback intent journal kind is invalid"
  [[ "$(macos_json_get "$journal_path" status 2>/dev/null || true)" == intent ]] || macos_die "reverse cutback intent journal status is invalid"
  [[ "$(macos_json_get "$journal_path" acceptedStateSha256 2>/dev/null || true)" == "$accepted_digest" && "$(macos_json_get "$journal_path" datasetId 2>/dev/null || true)" == "$dataset_id" && "$(macos_json_get "$journal_path" sourceHostId 2>/dev/null || true)" == "$target_host_id" && "$(macos_json_get "$journal_path" targetHostId 2>/dev/null || true)" == "$source_host_id" ]] || macos_die "reverse cutback intent journal identity changed"
  [[ "$(macos_json_get "$journal_path" writerGeneration 2>/dev/null || true)" == "$accepted_generation" && "$(macos_json_get "$journal_path" backupId 2>/dev/null || true)" == "$backup_id" && "$(macos_json_get "$journal_path" backupManifestSha256 2>/dev/null || true)" == "$backup_digest" ]] || macos_die "reverse cutback intent journal backup binding changed"
  [[ "$(macos_json_get "$journal_path" secondCopyEvidenceSha256 2>/dev/null || true)" == "$(macos_sha256 "$second_copy_evidence")" ]] || macos_die "reverse cutback intent second-copy binding changed"
  journal_state="$(macos_json_get "$journal_path" reverseStatePath 2>/dev/null || true)"
  [[ -n "$journal_state" && "$journal_state" == "$MACOS_LAYOUT_STATE"/* && "$journal_state" != *.consumed.json ]] || macos_die "reverse cutback intent state path is invalid"
  journal_digest="$(macos_json_get "$journal_path" reverseStateSha256 2>/dev/null || true)"
  [[ -z "$journal_digest" ]] || macos_die "reverse cutback intent unexpectedly contains a state digest"
  journal_created_at="$(macos_json_get "$journal_path" reverseCreatedAt 2>/dev/null || true)"
  [[ "$journal_created_at" =~ '^[0-9]{4}-' ]] || macos_die "reverse cutback intent timestamp is invalid"
  macos_epoch_from_iso "$journal_created_at" >/dev/null
  typeset -g reverse_state="$journal_state" reverse_created_at="$journal_created_at"
}

validate_reverse_phase_journal() {
  local journal_path="$1" journal_state journal_digest actual_digest
  macos_secure_path "$journal_path"
  plutil -convert json -o - -- "$journal_path" >/dev/null 2>&1 || macos_die "reverse cutback phase journal is invalid"
  [[ "$(macos_json_get "$journal_path" schemaVersion 2>/dev/null || true)" == 1 ]] || macos_die "reverse cutback phase journal schema is invalid"
  [[ "$(macos_json_get "$journal_path" kind 2>/dev/null || true)" == formal-cutover-rollback-reverse-phase ]] || macos_die "reverse cutback phase journal kind is invalid"
  [[ "$(macos_json_get "$journal_path" status 2>/dev/null || true)" == prepared ]] || macos_die "reverse cutback phase journal status is invalid"
  [[ "$(macos_json_get "$journal_path" acceptedStateSha256 2>/dev/null || true)" == "$accepted_digest" && "$(macos_json_get "$journal_path" datasetId 2>/dev/null || true)" == "$dataset_id" && "$(macos_json_get "$journal_path" sourceHostId 2>/dev/null || true)" == "$target_host_id" && "$(macos_json_get "$journal_path" targetHostId 2>/dev/null || true)" == "$source_host_id" ]] || macos_die "reverse cutback phase journal identity changed"
  [[ "$(macos_json_get "$journal_path" writerGeneration 2>/dev/null || true)" == "$accepted_generation" && "$(macos_json_get "$journal_path" backupId 2>/dev/null || true)" == "$backup_id" && "$(macos_json_get "$journal_path" backupManifestSha256 2>/dev/null || true)" == "$backup_digest" ]] || macos_die "reverse cutback phase journal backup binding changed"
  [[ "$(macos_json_get "$journal_path" secondCopyEvidenceSha256 2>/dev/null || true)" == "$(macos_sha256 "$second_copy_evidence")" ]] || macos_die "reverse cutback phase second-copy binding changed"
  [[ "$(macos_json_get "$journal_path" reverseCreatedAt 2>/dev/null || true)" == "$reverse_created_at" ]] || macos_die "reverse cutback phase timestamp changed"
  journal_state="$(macos_json_get "$journal_path" reverseStatePath 2>/dev/null || true)"
  [[ -n "$journal_state" && "$journal_state" == "$MACOS_LAYOUT_STATE"/* && "$journal_state" != *.consumed.json ]] || macos_die "reverse cutback phase state path is invalid"
  journal_digest="$(macos_json_get "$journal_path" reverseStateSha256 2>/dev/null || true)"
  [[ "$journal_digest" =~ '^[0-9a-fA-F]{64}$' ]] || macos_die "reverse cutback phase state digest is invalid"
  validate_reverse_prepared_state "$journal_state" 1
  actual_digest="$(macos_sha256 "$journal_state")"
  [[ "$actual_digest" == "$journal_digest" ]] || macos_die "reverse cutback phase state digest changed"
  typeset -g reverse_state="$journal_state" reverse_state_digest="$journal_digest"
}

# Session closure is checked before stopping the target.  A failure leaves the
# target untouched and produces no cutback handoff.
macos_compose_base "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT"
macos_run_checked docker "${MACOS_COMPOSE_ARGS[@]}" run --rm --no-deps backend \
  uv run --no-sync python -m app.ops.operator_control check-session-closure
macos_compose "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" stop
running_services="$(macos_compose_capture "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" ps --status running -q)"
[[ -z "${running_services//[[:space:]]/}" ]] || macos_die "target formal project still has running services"

cutback_mode="pre-write"
output_name="cutback-prewrite"
next_generation="$accepted_generation"
if [[ "$mode" == TargetAcceptedWrites ]]; then
  # Reverse cutback is itself a canonical prepare-cutover operation.  The
  # stopped target is the reverse source and the original source host is the
  # new target, so the resulting checksummed prepared state can be handed to
  # Accept-HostCutover on that source; a custom handoff JSON is insufficient.
  reverse_intent_path="$MACOS_LAYOUT_STATE/cutback-reverse-intent-${accepted_digest}.json"
  reverse_phase_path="$MACOS_LAYOUT_STATE/cutback-reverse-phase-${accepted_digest}.json"
  if [[ ( -e "$reverse_phase_path" || -e "$reverse_phase_path.sha256" ) && ! -e "$reverse_intent_path" && ! -e "$reverse_intent_path.sha256" ]]; then
    macos_die "reverse cutback phase exists without its immutable intent"
  fi

  if [[ -e "$reverse_intent_path" || -e "$reverse_intent_path.sha256" ]]; then
    [[ -f "$reverse_intent_path" ]] || macos_die "reverse cutback intent journal is incomplete"
    if [[ ! -f "$reverse_intent_path.sha256" ]]; then
      validate_reverse_intent_journal "$reverse_intent_path"
      macos_write_checksum "$reverse_intent_path"
    else
      macos_check_checksum "$reverse_intent_path"
    fi
    validate_reverse_intent_journal "$reverse_intent_path"
  else
    reverse_state="$MACOS_LAYOUT_STATE/cutover-prepared-reverse-${accepted_digest}.json"
    reverse_created_at="$(macos_now_iso)"
    macos_write_atomic "$reverse_intent_path" "{\"schemaVersion\":1,\"kind\":\"formal-cutover-rollback-reverse-intent\",\"status\":\"intent\",\"acceptedStateSha256\":\"$accepted_digest\",\"datasetId\":\"$dataset_id\",\"sourceHostId\":\"$target_host_id\",\"targetHostId\":\"$source_host_id\",\"writerGeneration\":$accepted_generation,\"backupId\":\"$backup_id\",\"backupManifestSha256\":\"$backup_digest\",\"secondCopyEvidenceSha256\":\"$(macos_sha256 "$second_copy_evidence")\",\"reverseStatePath\":\"$(macos_json_escape "$reverse_state")\",\"reverseStateSha256\":\"\",\"reverseCreatedAt\":\"$reverse_created_at\",\"createdAt\":\"$reverse_created_at\"}"
    macos_checksummed_json "$reverse_intent_path"
  fi
  [[ -n "$reverse_state" && -n "$reverse_created_at" ]] || macos_die "reverse canonical state binding is incomplete"

  if [[ -e "$reverse_phase_path" || -e "$reverse_phase_path.sha256" ]]; then
    [[ -f "$reverse_phase_path" ]] || macos_die "reverse cutback phase journal is incomplete"
    if [[ ! -f "$reverse_phase_path.sha256" ]]; then
      # Only repair the derived sidecar after the immutable state and all
      # backup/host bindings have been validated.
      validate_reverse_phase_journal "$reverse_phase_path"
      macos_write_checksum "$reverse_phase_path"
    else
      macos_check_checksum "$reverse_phase_path"
    fi
    validate_reverse_phase_journal "$reverse_phase_path"
    [[ "$reverse_state" == "$(macos_json_get "$reverse_phase_path" reverseStatePath)" ]] || macos_die "reverse intent and phase state paths differ"
  else
    if [[ -e "$reverse_state" || -e "$reverse_state.sha256" ]]; then
      [[ -f "$reverse_state" ]] || macos_die "reverse canonical prepared state is incomplete"
      validate_reverse_prepared_state "$reverse_state" 1
    else
      reverse_metadata_path="$MACOS_LAYOUT_STATE/cutover-reverse-release-metadata-${accepted_digest}.json"
      reverse_stop_proof_path="$MACOS_LAYOUT_STATE/cutover-reverse-source-stop-proof-${accepted_digest}.json"
      reverse_image_refs_path="$MACOS_LAYOUT_STATE/cutover-reverse-image-references-${accepted_digest}.json"
      reverse_base_refs_path="$MACOS_LAYOUT_STATE/cutover-reverse-base-image-references-${accepted_digest}.json"
      reverse_checksums_path="$MACOS_LAYOUT_STATE/cutover-reverse-release-checksums-${accepted_digest}.json"

      reverse_image_refs_json="{"
      for image_name in db backend frontend gateway; do
        [[ "$reverse_image_refs_json" == "{" ]] || reverse_image_refs_json+=","
        reverse_image_refs_json+="\"$image_name\":\"$(macos_json_get "$release_path/ops/release/built-image-identity.json" "images.$image_name.id")\""
      done
      reverse_image_refs_json+="}"
      macos_write_atomic "$reverse_image_refs_path" "$reverse_image_refs_json"
      macos_write_checksum "$reverse_image_refs_path"
      reverse_base_refs_json="$(plutil -extract baseImageReferences json -o - -- "$release_path/release-manifest.json")"
      macos_write_atomic "$reverse_base_refs_path" "$reverse_base_refs_json"
      macos_write_checksum "$reverse_base_refs_path"
      reverse_checksums_json="{"
      while IFS= read -r checksum_line || [[ -n "$checksum_line" ]]; do
        [[ "$checksum_line" =~ '^([0-9a-fA-F]{64})[[:space:]][[:space:]](.+)$' ]] || macos_die "reverse release checksum row is invalid"
        [[ "$reverse_checksums_json" == "{" ]] || reverse_checksums_json+=","
        reverse_checksums_json+="\"$(macos_json_escape "${match[2]}")\":\"${match[1]:l}\""
      done < "$release_path/SHA256SUMS"
      reverse_checksums_json+="}"
      macos_write_atomic "$reverse_checksums_path" "$reverse_checksums_json"
      macos_write_checksum "$reverse_checksums_path"
      macos_write_atomic "$reverse_stop_proof_path" "{\"schemaVersion\":1,\"wholeProjectStopped\":true,\"project\":\"$MACOS_FORMAL_PROJECT\",\"observedAt\":\"$reverse_created_at\",\"runningServices\":[],\"method\":\"compose-stop-and-ps\"}"
      macos_checksummed_json "$reverse_stop_proof_path"
      macos_backend_one_shot_with_mounts "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" \
        --volume "$MACOS_LAYOUT_STATE:/cutover-state" \
        release-metadata \
        --application-version "$(macos_json_get "$release_path/release-manifest.json" applicationVersion)" \
        --git-commit "${release_commit:l}" --host-os darwin --architecture arm64 \
        --target-platform linux/arm64 --migration-head "$(macos_json_get "$release_path/release-manifest.json" migrationHead)" \
        --image-references "/cutover-state/${reverse_image_refs_path:t}" \
        --base-image-references "/cutover-state/${reverse_base_refs_path:t}" \
        --release-file-checksums "/cutover-state/${reverse_checksums_path:t}" \
        --created-at "$reverse_created_at" \
        --output "/cutover-state/${reverse_metadata_path:t}"
      [[ -f "$reverse_metadata_path" && -f "$reverse_metadata_path.sha256" ]] || macos_die "reverse release metadata was not written"
      macos_check_checksum "$reverse_metadata_path"
      macos_backend_one_shot_with_mounts "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" \
        --volume "$backup_path:/portable-backup:ro" \
        --volume "$MACOS_LAYOUT_STATE:/cutover-state" \
        prepare-cutover --backup /portable-backup \
        --target-host-id "$source_host_id" \
        --release-metadata "/cutover-state/${reverse_metadata_path:t}" \
        --source-stop-proof "/cutover-state/${reverse_stop_proof_path:t}" \
        --source-project "$MACOS_FORMAL_PROJECT" --target-project "$MACOS_FORMAL_PROJECT" \
        --source-fully-stopped --in-progress-attempts 0 \
        --state-path "/cutover-state/${reverse_state:t}"
      [[ -f "$reverse_state" ]] || macos_die "reverse canonical prepared state was not written"
      validate_reverse_prepared_state "$reverse_state" 1
    fi

    reverse_state_digest="$(macos_sha256 "$reverse_state")"
    macos_write_atomic "$reverse_phase_path" "{\"schemaVersion\":1,\"kind\":\"formal-cutover-rollback-reverse-phase\",\"status\":\"prepared\",\"acceptedStateSha256\":\"$accepted_digest\",\"datasetId\":\"$dataset_id\",\"sourceHostId\":\"$target_host_id\",\"targetHostId\":\"$source_host_id\",\"writerGeneration\":$accepted_generation,\"backupId\":\"$backup_id\",\"backupManifestSha256\":\"$backup_digest\",\"secondCopyEvidenceSha256\":\"$(macos_sha256 "$second_copy_evidence")\",\"reverseStatePath\":\"$(macos_json_escape "$reverse_state")\",\"reverseStateSha256\":\"$reverse_state_digest\",\"reverseCreatedAt\":\"$reverse_created_at\",\"createdAt\":\"$(macos_now_iso)\"}"
    macos_checksummed_json "$reverse_phase_path"
    validate_reverse_phase_journal "$reverse_phase_path"
  fi

  terminal_path="$MACOS_LAYOUT_STATE/cutover-rollback-terminal-${accepted_digest}.json"
  macos_write_atomic "$terminal_path" "{\"schemaVersion\":1,\"kind\":\"formal-cutover-rollback-terminal\",\"status\":\"terminal\",\"acceptedStateSha256\":\"$accepted_digest\",\"handoffStateSha256\":\"$(macos_sha256 "$reverse_state")\",\"handoffStatePath\":\"$(macos_json_escape "$reverse_state")\",\"reversePhaseSha256\":\"$(macos_sha256 "$reverse_phase_path")\",\"datasetId\":\"$dataset_id\",\"targetHostId\":\"$target_host_id\",\"writerGeneration\":$accepted_generation,\"mode\":\"$mode\",\"createdAt\":\"$(macos_now_iso)\",\"approval\":\"manual-required\"}"
  macos_checksummed_json "$terminal_path"
  rollback_status=passed
  macos_log "host_cutback_prepared mode=post-write canonical_state=${reverse_state:t} dataset=$dataset_id target_host=$source_host_id writer_generation=$(macos_json_get "$reverse_state" writer_generation) source_reopen_required=true approval=manual-required"
  exit 0
fi
cutback_state="$MACOS_LAYOUT_STATE/${output_name}-$(macos_timestamp).json"
[[ ! -e "$cutback_state" && ! -e "$cutback_state.sha256" ]] || macos_die "cutback state destination already exists"
accepted_digest="$(macos_sha256 "$accepted_state")"
if [[ "$mode" == TargetNeverAcceptedWrites ]]; then
  cutback_json="{\"schemaVersion\":1,\"kind\":\"formal-cutback\",\"state\":\"prepared-for-source-reopen\",\"mode\":\"pre-write\",\"datasetId\":\"$(macos_json_escape "$dataset_id")\",\"sourceHostId\":\"$(macos_json_escape "$source_host_id")\",\"targetHostId\":\"$(macos_json_escape "$target_host_id")\",\"acceptedStateSha256\":\"$accepted_digest\",\"sourceWriterGeneration\":$source_generation,\"targetWriterGeneration\":$accepted_generation,\"targetWriteAccepted\":false,\"targetFormalProject\":\"$MACOS_FORMAL_PROJECT\",\"targetFormalStopped\":true,\"targetRunningServices\":[],\"sourceReopenRequired\":true,\"dataRestorePerformed\":false,\"dataLossExpected\":false,\"approval\":\"manual-required\",\"createdAt\":\"$(macos_now_iso)\",\"secrets\":\"excluded\"}"
else
  cutback_json="{\"schemaVersion\":1,\"kind\":\"formal-cutback\",\"state\":\"handoff-prepared\",\"mode\":\"post-write\",\"datasetId\":\"$(macos_json_escape "$dataset_id")\",\"sourceHostId\":\"$(macos_json_escape "$source_host_id")\",\"targetHostId\":\"$(macos_json_escape "$target_host_id")\",\"acceptedStateSha256\":\"$accepted_digest\",\"acceptedTargetWriterGeneration\":$accepted_generation,\"postWriteBackupId\":\"$(macos_json_escape "$backup_id")\",\"postWriteBackupManifestSha256\":\"$backup_digest\",\"postWriteBackupCreatedAt\":\"$(macos_json_escape "$backup_created_at")\",\"secondCopyEvidenceSha256\":\"$(macos_sha256 "$second_copy_evidence")\",\"targetWriterGeneration\":$backup_generation,\"handoffWriterGeneration\":$next_generation,\"targetWriteAccepted\":true,\"targetFormalProject\":\"$MACOS_FORMAL_PROJECT\",\"targetFormalStopped\":true,\"targetRunningServices\":[],\"sourceReopenRequired\":true,\"dataRestorePerformed\":false,\"postBackupWritesMayBeLost\":true,\"expectedLoss\":\"writes after post-write backup boundary may be lost\",\"approval\":\"manual-required\",\"createdAt\":\"$(macos_now_iso)\",\"secrets\":\"excluded\"}"
fi
macos_write_atomic "$cutback_state" "$cutback_json"
macos_checksummed_json "$cutback_state"
macos_secure_path "$cutback_state"
terminal_path="$MACOS_LAYOUT_STATE/cutover-rollback-terminal-${accepted_digest}.json"
macos_write_atomic "$terminal_path" "{\"schemaVersion\":1,\"kind\":\"formal-cutover-rollback-terminal\",\"status\":\"terminal\",\"acceptedStateSha256\":\"$accepted_digest\",\"handoffStateSha256\":\"$(macos_sha256 "$cutback_state")\",\"handoffStatePath\":\"$(macos_json_escape "$cutback_state")\",\"datasetId\":\"$dataset_id\",\"targetHostId\":\"$target_host_id\",\"writerGeneration\":$accepted_generation,\"mode\":\"$mode\",\"createdAt\":\"$(macos_now_iso)\",\"approval\":\"manual-required\"}"
macos_checksummed_json "$terminal_path"
rollback_status=passed
macos_log "host_cutback_prepared mode=$cutback_mode dataset=$dataset_id target_host=$target_host_id writer_generation=$next_generation state=${cutback_state:t} source_reopen_required=true approval=manual-required"
