#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
source "$SCRIPT_DIR/Common.zsh"

final_backup_path=""
browser_evidence=""
pf_evidence=""
network_time_evidence=""
prepared_state_arg=""
confirmation=""
source_stopped=0
target_release_arg=""
root="${INTERNAL_EXAM_ROOT:-${HOME:?}/Library/Application Support/InternalExam}"
while (( $# > 0 )); do
  case "$1" in
    --final-backup-path|--backup) (( $# >= 2 )) || macos_die "$1 requires a path"; final_backup_path="$2"; shift 2 ;;
    --browser-smoke-evidence|--browser-evidence) (( $# >= 2 )) || macos_die "$1 requires a path"; browser_evidence="$2"; shift 2 ;;
    --pf-evidence) (( $# >= 2 )) || macos_die "$1 requires a path"; pf_evidence="$2"; shift 2 ;;
    --network-time-evidence) (( $# >= 2 )) || macos_die "$1 requires a path"; network_time_evidence="$2"; shift 2 ;;
    --prepared-state|--prepared-evidence|--state-path) (( $# >= 2 )) || macos_die "$1 requires a path"; prepared_state_arg="$2"; shift 2 ;;
    --source-stopped) source_stopped=1; shift ;;
    --release-path|--release) (( $# >= 2 )) || macos_die "$1 requires a sealed target release path"; target_release_arg="$2"; shift 2 ;;
    --confirmation) (( $# >= 2 )) || macos_die "--confirmation requires exact text"; confirmation="$2"; shift 2 ;;
    --root) (( $# >= 2 )) || macos_die "--root requires a path"; root="$2"; shift 2 ;;
   -h|--help) print -r -- "usage: $0 [--final-backup-path PATH] --browser-smoke-evidence PATH --pf-evidence PATH --network-time-evidence PATH --source-stopped --confirmation 'ACCEPT HOST CUTOVER' [--prepared-state PATH] [--release-path SEALED_RELEASE] [--root ROOT]"; exit 0 ;;
    *) macos_die "unknown argument: $1"; exit 1 ;;
  esac
done

macos_assert_macos
[[ -n "$browser_evidence" && -n "$pf_evidence" && -n "$network_time_evidence" ]] || macos_die "browser, PF, and network-time evidence are required"
(( source_stopped == 1 )) || macos_die "source gateway shutdown must be explicitly confirmed"
[[ "$confirmation" == 'ACCEPT HOST CUTOVER' ]] || macos_die "exact cutover acceptance confirmation did not match"
macos_assert_outside_worktree "$root" >/dev/null
macos_layout "$root"
macos_assert_protected_configuration "$root"
if [[ -f "$MACOS_CURRENT_STATE" ]]; then
  if [[ -n "$target_release_arg" ]]; then
    target_release_arg="$(macos_resolve_path "$target_release_arg")"
    [[ "$target_release_arg" == "$MACOS_LAYOUT_RELEASES"/* ]] || macos_die "target release must be an installed release under the protected release directory"
    macos_require_formal_paths "$target_release_arg"
  else
    macos_require_formal_paths
  fi
else
  [[ -n "$target_release_arg" ]] || macos_die "first target acceptance requires --release-path because no current formal release exists"
  target_release_arg="$(macos_resolve_path "$target_release_arg")"
  [[ "$target_release_arg" == "$MACOS_LAYOUT_RELEASES"/* ]] || macos_die "target release must be an installed release under the protected release directory"
  macos_require_formal_paths "$target_release_arg"
fi
macos_docker_ready
macos_acquire_lock "$MACOS_LAYOUT_STATE/.operation.lock"
trap macos_release_lock EXIT
bootstrap_current=0
bootstrap_initial=0
resuming_accept=0
resuming_pre_accept=0
if [[ -f "$MACOS_CURRENT_STATE" ]]; then
  macos_secure_path "$MACOS_CURRENT_STATE"
  plutil -convert json -o - -- "$MACOS_CURRENT_STATE" >/dev/null 2>&1 || macos_die "current release JSON is invalid"
  if [[ -n "$target_release_arg" ]]; then
    release_path="$target_release_arg"
    release_version="$(macos_json_get "$release_path/release-manifest.json" applicationVersion)"
    release_commit="$(macos_json_get "$release_path/release-manifest.json" gitCommit)"
  else
    recovery_release_path="$(macos_json_get "$MACOS_CURRENT_STATE" path 2>/dev/null || true)"
    [[ "$recovery_release_path" == "$MACOS_LAYOUT_RELEASES"/* && -d "$recovery_release_path" ]] || macos_die "current release path is invalid"
    release_path="$recovery_release_path"
    release_version="$(macos_json_get "$release_path/release-manifest.json" applicationVersion)"
    release_commit="$(macos_json_get "$release_path/release-manifest.json" gitCommit)"
  fi
else
  release_path="$target_release_arg"
  release_version="$(macos_json_get "$release_path/release-manifest.json" applicationVersion)"
  release_commit="$(macos_json_get "$release_path/release-manifest.json" gitCommit)"
  bootstrap_current=1
  bootstrap_initial=1
fi
if [[ -n "$prepared_state_arg" ]]; then
  prepared_state="$(macos_resolve_path "$prepared_state_arg")"
  [[ "${prepared_state:h}" == "$MACOS_LAYOUT_STATE" ]] || macos_die "prepared cutover state must stay in the protected state directory"
else
  # Resolve the newest canonical prepared state, excluding consumed markers.
  # A caller may always pass --prepared-state to remove any ambiguity.
  typeset -a prepared_candidates
  prepared_candidates=( "$MACOS_LAYOUT_STATE"/cutover-prepared*.json(Nom[1]) )
  prepared_state=""
  for candidate in "${prepared_candidates[@]}"; do
    [[ "$candidate" == *.consumed.json ]] && continue
    [[ -f "$candidate" ]] || continue
    candidate_suffix="${candidate:t#cutover-prepared-}"
    candidate_accepted="$MACOS_LAYOUT_STATE/cutover-accepted-$candidate_suffix"
    candidate_marker="${candidate}.consumed.json"
    candidate_recovery_evidence=0
    for candidate_artifact in \
      "$candidate_marker" "$candidate_marker.sha256" \
      "$candidate_accepted" "$candidate_accepted.sha256" \
      "$candidate_accepted:h/.${candidate_accepted:t}.cutover-write.tmp" \
      "$candidate_marker:h/.${candidate_marker:t}.cutover-write.tmp" \
      "$candidate:h/.${candidate:t}.cutover-write.tmp" \
      "$candidate:h/.${candidate:t}.cutover-claim.tmp"; do
      if [[ -e "$candidate_artifact" ]]; then
        candidate_recovery_evidence=1
        break
      fi
    done
    if [[ ! -f "$candidate.sha256" && "$candidate_recovery_evidence" != 1 ]]; then
      continue
    fi
    candidate_state="$(macos_json_get "$candidate" state 2>/dev/null || true)"
    if [[ "$candidate_state" == prepared ]]; then
      prepared_state="$candidate"
      break
    fi
    if [[ "$candidate_state" == consumed ]]; then
      [[ -f "$candidate_accepted" && -f "$MACOS_LAYOUT_STATE/cutover-phase-$candidate_suffix" ]] || continue
      prepared_state="$candidate"
      break
    fi
  done
  [[ -n "$prepared_state" ]] || macos_die "no unconsumed canonical prepared cutover state was found"
fi
[[ "$prepared_state" != *.consumed.json ]] || macos_die "a consumed cutover state cannot be accepted"
macos_secure_path "$prepared_state"
prepared_name="${prepared_state:t}"
accepted_state="$MACOS_LAYOUT_STATE/cutover-accepted-${prepared_name#cutover-prepared-}"
# Derive the accepted filename before strict checksum gates.  The backend
# recovery CLI can finish an exact claim/accept half-commit whose JSON or
# sidecar is incomplete; shell code must not repair canonical bytes itself.
macos_recover_cutover_state "$release_path" "$prepared_state" "$accepted_state"
macos_check_checksum "$prepared_state"
prepared_state_phase="$(macos_json_get "$prepared_state" state)"
[[ "$prepared_state_phase" == prepared || "$prepared_state_phase" == consumed ]] || macos_die "prepared cutover state is stale or already accepted"
[[ "$(macos_json_get "$prepared_state" source_project)" == "$MACOS_FORMAL_PROJECT" ]] || macos_die "prepared source project is not formal"
[[ "$(macos_json_get "$prepared_state" target_project)" == "$MACOS_FORMAL_PROJECT" ]] || macos_die "prepared target project is not formal"
case "$(macos_json_get "$prepared_state" source_gateway_stopped)" in
  1|true) ;;
  *) macos_die "prepared state does not prove source project stopped" ;;
esac
prepared_backup_id="$(macos_json_get "$prepared_state" backup_id)"
[[ "$prepared_backup_id" =~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$' ]] || macos_die "prepared backup identity is invalid"
if [[ -n "$final_backup_path" ]]; then
  backup_path="$(macos_assert_backup "$final_backup_path")"
else
  backup_path="$(macos_assert_backup "$MACOS_LAYOUT_BACKUPS/$prepared_backup_id")"
fi
macos_assert_outside_worktree "$backup_path" >/dev/null
[[ "${backup_path:t}" == "$prepared_backup_id" ]] || macos_die "final backup does not match prepared cutover state"
identity_path="$MACOS_LAYOUT_STATE/host-identity.json"
macos_secure_path "$identity_path"
plutil -convert json -o - -- "$identity_path" >/dev/null 2>&1 || macos_die "host identity JSON is invalid"
MACOS_DATASET_ID="$(macos_json_get "$identity_path" datasetId 2>/dev/null || true)"
MACOS_HOST_ID="$(macos_json_get "$identity_path" hostId 2>/dev/null || true)"
MACOS_WRITER_GENERATION="$(macos_json_get "$identity_path" writerGeneration 2>/dev/null || true)"
[[ "$MACOS_DATASET_ID" =~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$' && "$MACOS_HOST_ID" =~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$' && "$MACOS_WRITER_GENERATION" =~ '^[1-9][0-9]*$' ]] || macos_die "host identity fields are invalid"
[[ "$(macos_json_get "$prepared_state" target_host_id 2>/dev/null || true)" == "$MACOS_HOST_ID" ]] || macos_die "prepared cutover target host does not match this target identity"
source_writer_generation="$(macos_json_get "$prepared_state" writer_generation)"
[[ "$source_writer_generation" =~ '^[0-9]+$' ]] || macos_die "prepared writer generation is invalid"
target_writer_generation=$(( source_writer_generation + 1 ))
lineage_state="$(macos_json_get "$MACOS_LAYOUT_STATE/host-identity.json" lineageState 2>/dev/null || true)"
if [[ "$prepared_state_phase" == prepared && ( "$lineage_state" == bound || "$bootstrap_current" == 0 ) ]]; then
  (( target_writer_generation > MACOS_WRITER_GENERATION )) || macos_die "new canonical cutover must advance the bound target writer generation"
fi
phase_journal="$MACOS_LAYOUT_STATE/cutover-phase-${prepared_name#cutover-prepared-}"
target_metadata_path="$MACOS_LAYOUT_STATE/${prepared_state:t:r}.target-release-metadata.json"
# Rollback uses a deterministic filename derived from the accepted-state
# digest.  Any matching JSON or sidecar is a supersession signal, including a
# half-written sidecar; an invalid/tampered tombstone must never be ignored.
accepted_digest_for_tombstone=""
if [[ -f "$accepted_state" ]]; then
  accepted_digest_for_tombstone="$(macos_sha256 "$accepted_state")"
elif [[ -f "$accepted_state:h/.${accepted_state:t}.cutover-write.tmp" ]]; then
  accepted_digest_for_tombstone="$(macos_sha256 "$accepted_state:h/.${accepted_state:t}.cutover-write.tmp")"
fi
if [[ -n "$accepted_digest_for_tombstone" ]]; then
  for rollback_tombstone in \
    "$MACOS_LAYOUT_STATE/cutover-rollback-intent-${accepted_digest_for_tombstone}.json" \
    "$MACOS_LAYOUT_STATE/cutover-rollback-intent-${accepted_digest_for_tombstone}.json.sha256" \
    "$MACOS_LAYOUT_STATE/cutover-rollback-terminal-${accepted_digest_for_tombstone}.json" \
    "$MACOS_LAYOUT_STATE/cutover-rollback-terminal-${accepted_digest_for_tombstone}.json.sha256"; do
    [[ -e "$rollback_tombstone" ]] && macos_die "accepted cutover is superseded by a rollback record; automatic resume is forbidden"
  done
fi
if [[ -f "$accepted_state" && -f "$accepted_state.sha256" ]]; then
  macos_recover_derived_sidecars "$release_path" "$accepted_state" "$MACOS_HOST_ID" "$target_writer_generation"
fi
if [[ -f "$MACOS_CURRENT_STATE" ]]; then
  macos_release_state "$MACOS_CURRENT_STATE"
fi
macos_read_cutover_identity
volume_override="$MACOS_LAYOUT_STATE/formal-volume-override.yml"
validate_cutover_volume_override() {
  local override_path="$1" expected_digest="${2:-}" pg media worker actual
  [[ -f "$override_path" ]] || macos_die "cutover volume override is missing"
  pg="$(awk '/^[[:space:]]+postgres_data:[[:space:]]*$/ { in_postgres=1; next } in_postgres && /^[[:space:]]+name:[[:space:]]*/ { print $2; exit }' "$override_path")"
  media="$(awk '/^[[:space:]]+learning_media:[[:space:]]*$/ { in_media=1; next } in_media && /^[[:space:]]+name:[[:space:]]*/ { print $2; exit }' "$override_path")"
  worker="$(awk '/^[[:space:]]+worker_state:[[:space:]]*$/ { in_worker=1; next } in_worker && /^[[:space:]]+name:[[:space:]]*/ { print $2; exit }' "$override_path")"
  [[ "$pg" =~ '^internal-exam-formal-cutover-[A-Za-z0-9-]+-postgres$' && "$media" =~ '^internal-exam-formal-cutover-[A-Za-z0-9-]+-media$' && "$worker" =~ '^internal-exam-formal-cutover-[A-Za-z0-9-]+-worker$' ]] || macos_die "cutover volume override contains unsafe names"
  actual="$(macos_sha256 "$override_path")"
  if [[ -n "$expected_digest" ]]; then
    [[ "$actual" == "$expected_digest" ]] || macos_die "cutover volume override changed after its phase journal"
  fi
  print -r -- "$actual"
}
validate_pre_accept_phase_journal() {
  local journal_path="$1" journal_phase journal_override_digest
  macos_secure_path "$journal_path"
  plutil -convert json -o - -- "$journal_path" >/dev/null 2>&1 || macos_die "pre-accept cutover phase journal is invalid"
  [[ "$(macos_json_get "$journal_path" schemaVersion 2>/dev/null || true)" == 1 ]] || macos_die "pre-accept phase journal schema is invalid"
  [[ "$(macos_json_get "$journal_path" kind 2>/dev/null || true)" == formal-cutover-phase ]] || macos_die "pre-accept phase journal kind is invalid"
  journal_phase="$(macos_json_get "$journal_path" phase 2>/dev/null || true)"
  [[ "$journal_phase" == restore-pending || "$journal_phase" == preflight-passed ]] || macos_die "pre-accept cutover phase cannot be replayed"
  [[ "$(macos_json_get "$journal_path" preparedState 2>/dev/null || true)" == "$prepared_state" ]] || macos_die "pre-accept phase journal prepared path changed"
  [[ "$(macos_json_get "$journal_path" preparedStateSha256 2>/dev/null || true)" == "$(macos_sha256 "$prepared_state")" ]] || macos_die "pre-accept phase journal is not bound to prepared state"
  [[ "$(macos_json_get "$journal_path" acceptedState 2>/dev/null || true)" == "$accepted_state" ]] || macos_die "pre-accept phase journal accepted path changed"
  [[ "$(macos_json_get "$journal_path" backupPath 2>/dev/null || true)" == "$backup_path" ]] || macos_die "pre-accept phase journal backup path changed"
  [[ "$(macos_json_get "$journal_path" releasePath 2>/dev/null || true)" == "$release_path" ]] || macos_die "pre-accept phase journal release path changed"
  [[ "$(macos_json_get "$journal_path" volumeOverride 2>/dev/null || true)" == "$volume_override" ]] || macos_die "pre-accept phase journal volume override changed"
  [[ "$(macos_json_get "$journal_path" datasetId 2>/dev/null || true)" == "$(macos_json_get "$prepared_state" dataset_id)" ]] || macos_die "pre-accept phase journal dataset changed"
  [[ "$(macos_json_get "$journal_path" targetHostId 2>/dev/null || true)" == "$MACOS_HOST_ID" ]] || macos_die "pre-accept phase journal target host changed"
  [[ "$(macos_json_get "$journal_path" sourceWriterGeneration 2>/dev/null || true)" == "$source_writer_generation" ]] || macos_die "pre-accept phase journal source generation changed"
  [[ "$(macos_json_get "$journal_path" targetWriterGeneration 2>/dev/null || true)" == "$target_writer_generation" ]] || macos_die "pre-accept phase journal target generation changed"
  [[ -f "$volume_override" ]] || macos_die "pre-accept phase journal volume override is missing"
  journal_override_digest="$(macos_json_get "$journal_path" volumeOverrideSha256 2>/dev/null || true)"
  [[ "$journal_override_digest" == "$(macos_sha256 "$volume_override")" ]] || macos_die "pre-accept phase journal volume override checksum changed"
}
validate_cutover_external_bindings() {
  local state_path="$1" require_target_release="${2:-0}" binding_backup="${3:-$backup_path}"
  if (( require_target_release == 1 )); then
    [[ -f "$target_metadata_path" && -f "$target_metadata_path.sha256" ]] || macos_die "accepted cutover target release metadata is missing"
    macos_check_checksum "$target_metadata_path"
    macos_backend_one_shot_with_mounts "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" \
      --volume "$MACOS_LAYOUT_STATE:/cutover-state:ro" \
      --volume "$binding_backup:/portable-backup:ro" \
      validate-cutover-bindings "/cutover-state/${state_path:t}" \
      --backup /portable-backup \
      --target-release-metadata "/cutover-state/${target_metadata_path:t}"
  else
    macos_backend_one_shot_with_mounts "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" \
      --volume "$MACOS_LAYOUT_STATE:/cutover-state:ro" \
      --volume "$binding_backup:/portable-backup:ro" \
      validate-cutover-bindings "/cutover-state/${state_path:t}" \
      --backup /portable-backup
  fi
}
validate_accepted_phase_journal() {
  local journal_path="$1" expected_prepared_digest="$2" expected_accepted_digest="$3" allow_missing_accepted="${4:-0}"
  local journal_phase journal_accepted journal_override_digest
  macos_secure_path "$journal_path"
  plutil -convert json -o - -- "$journal_path" >/dev/null 2>&1 || macos_die "accepted cutover phase journal is invalid"
  [[ "$(macos_json_get "$journal_path" schemaVersion 2>/dev/null || true)" == 1 ]] || macos_die "accepted phase journal schema is invalid"
  [[ "$(macos_json_get "$journal_path" kind 2>/dev/null || true)" == formal-cutover-phase ]] || macos_die "accepted phase journal kind is invalid"
  journal_phase="$(macos_json_get "$journal_path" phase 2>/dev/null || true)"
  [[ "$journal_phase" == restore-pending || "$journal_phase" == preflight-passed || "$journal_phase" == accepted || "$journal_phase" == fence-transferred || "$journal_phase" == state-bound || "$journal_phase" == fence-released || "$journal_phase" == activation-intent || "$journal_phase" == activated ]] || macos_die "accepted cutover phase journal cannot be resumed"
  [[ "$(macos_json_get "$journal_path" preparedState 2>/dev/null || true)" == "$prepared_state" ]] || macos_die "accepted phase journal prepared path changed"
  [[ "$(macos_json_get "$journal_path" preparedStateSha256 2>/dev/null || true)" == "$expected_prepared_digest" ]] || macos_die "accepted phase journal prepared digest changed"
  [[ "$(macos_json_get "$journal_path" acceptedState 2>/dev/null || true)" == "$accepted_state" ]] || macos_die "accepted phase journal accepted path changed"
  journal_accepted="$(macos_json_get "$journal_path" acceptedStateSha256 2>/dev/null || true)"
  if [[ -z "$journal_accepted" && "$allow_missing_accepted" == 1 && ( "$journal_phase" == restore-pending || "$journal_phase" == preflight-passed ) ]]; then
    :
  else
    [[ "$journal_accepted" == "$expected_accepted_digest" ]] || macos_die "accepted phase journal accepted digest changed"
  fi
  [[ "$(macos_json_get "$journal_path" backupPath 2>/dev/null || true)" == "$backup_path" ]] || macos_die "accepted phase journal backup path changed"
  [[ "$(macos_json_get "$journal_path" releasePath 2>/dev/null || true)" == "$release_path" ]] || macos_die "accepted phase journal release path changed"
  [[ "$(macos_json_get "$journal_path" volumeOverride 2>/dev/null || true)" == "$volume_override" ]] || macos_die "accepted phase journal volume override changed"
  [[ "$(macos_json_get "$journal_path" datasetId 2>/dev/null || true)" == "$(macos_json_get "$accepted_state" dataset_id)" ]] || macos_die "accepted phase journal dataset changed"
  [[ "$(macos_json_get "$journal_path" targetHostId 2>/dev/null || true)" == "$MACOS_HOST_ID" ]] || macos_die "accepted phase journal target host changed"
  [[ "$(macos_json_get "$journal_path" sourceWriterGeneration 2>/dev/null || true)" == "$source_writer_generation" ]] || macos_die "accepted phase journal source generation changed"
  [[ "$(macos_json_get "$journal_path" targetWriterGeneration 2>/dev/null || true)" == "$target_writer_generation" ]] || macos_die "accepted phase journal target generation changed"
  [[ -f "$volume_override" ]] || macos_die "accepted phase journal volume override is missing"
  journal_override_digest="$(macos_json_get "$journal_path" volumeOverrideSha256 2>/dev/null || true)"
  [[ "$journal_override_digest" == "$(macos_sha256 "$volume_override")" ]] || macos_die "accepted phase journal volume override checksum changed"
}
if [[ -e "$accepted_state" || -e "$accepted_state.sha256" ]]; then
  [[ -f "$accepted_state" && -f "$accepted_state.sha256" ]] || macos_die "accepted cutover state is incomplete"
  macos_secure_path "$accepted_state"
  macos_check_checksum "$accepted_state"
  [[ "$(macos_json_get "$prepared_state" state 2>/dev/null || true)" == consumed ]] || macos_die "accepted state exists before its prepared state was consumed"
  consumed_marker="${prepared_state}.consumed.json"
  [[ -f "$consumed_marker" && -f "$consumed_marker.sha256" ]] || macos_die "accepted state is missing the consumed-state marker"
  macos_check_checksum "$consumed_marker"
  [[ "$(macos_json_get "$consumed_marker" accepted_sha256 2>/dev/null || true)" == "$(macos_sha256 "$accepted_state")" ]] || macos_die "accepted state is not bound to the consumed prepared state"
  canonical_prepared_digest="$(macos_json_get "$consumed_marker" source_sha256 2>/dev/null || true)"
  [[ "$canonical_prepared_digest" =~ '^[0-9a-f]{64}$' ]] || macos_die "consumed state source digest is invalid"
  accepted_state_digest="$(macos_sha256 "$accepted_state")"
  # Before repairing any derived shell journal, bind the caller-selected
  # backup and release to the immutable canonical accepted state.  A retry
  # may not substitute another same-named backup or installed release.
  validate_cutover_external_bindings "$accepted_state" 1
  if [[ ! -f "$phase_journal" ]]; then
    # Canonical accepted/consumed state is authoritative if the host died
    # before the shell journal write.  Recreate only this derived journal;
    # never recreate or mutate canonical backend state.
    phase_json="{\"schemaVersion\":1,\"kind\":\"formal-cutover-phase\",\"phase\":\"accepted\",\"preparedState\":\"$(macos_json_escape "$prepared_state")\",\"preparedStateSha256\":\"$canonical_prepared_digest\",\"acceptedState\":\"$(macos_json_escape "$accepted_state")\",\"acceptedStateSha256\":\"$accepted_state_digest\",\"backupPath\":\"$(macos_json_escape "$backup_path")\",\"releasePath\":\"$(macos_json_escape "$release_path")\",\"volumeOverride\":\"$(macos_json_escape "$volume_override")\",\"volumeOverrideSha256\":\"$(macos_sha256 "$volume_override")\",\"datasetId\":\"$(macos_json_escape "$(macos_json_get "$accepted_state" dataset_id)")\",\"targetHostId\":\"$(macos_json_escape "$MACOS_HOST_ID")\",\"sourceWriterGeneration\":$source_writer_generation,\"targetWriterGeneration\":$target_writer_generation,\"updatedAt\":\"$(macos_now_iso)\"}"
    macos_write_atomic "$phase_journal" "$phase_json"
    macos_checksummed_json "$phase_journal"
  elif [[ ! -f "$phase_journal.sha256" ]] || ! macos_check_checksum "$phase_journal"; then
    validate_accepted_phase_journal "$phase_journal" "$canonical_prepared_digest" "$accepted_state_digest" 1
    macos_write_checksum "$phase_journal"
  fi
  validate_accepted_phase_journal "$phase_journal" "$canonical_prepared_digest" "$accepted_state_digest" 1
  journal_accepted_digest="$(macos_json_get "$phase_journal" acceptedStateSha256 2>/dev/null || true)"
  if [[ -z "$journal_accepted_digest" ]]; then
    # The canonical consumed marker and accepted sidecar are authoritative if
    # the process died in the tiny accept-commit/journal-update window.
    macos_json_replace_atomic "$phase_journal" acceptedStateSha256 "\"$accepted_state_digest\""
    macos_write_checksum "$phase_journal"
  else
    [[ "$journal_accepted_digest" == "$accepted_state_digest" ]] || macos_die "cutover phase journal is not bound to accepted state"
  fi
  validate_accepted_phase_journal "$phase_journal" "$canonical_prepared_digest" "$accepted_state_digest" 0
  [[ "$(macos_json_get "$phase_journal" volumeOverride 2>/dev/null || true)" == "$volume_override" ]] || macos_die "cutover phase journal volume override does not match"
  resuming_accept=1
else
  if [[ -e "$phase_journal" || -e "$phase_journal.sha256" ]]; then
    [[ -f "$phase_journal" ]] || macos_die "pre-accept cutover phase journal is incomplete"
    if [[ ! -f "$phase_journal.sha256" ]] || ! macos_check_checksum "$phase_journal"; then
      # The restore-pending JSON is a wrapper-owned derived journal.  If a
      # power loss happens after its atomic rename but before its sidecar,
      # repair only the checksum after every immutable binding matches the
      # canonical prepared state, selected release, backup and volume map.
      validate_pre_accept_phase_journal "$phase_journal"
      macos_write_checksum "$phase_journal"
    fi
    validate_pre_accept_phase_journal "$phase_journal"
    journal_phase="$(macos_json_get "$phase_journal" phase 2>/dev/null || true)"
    resuming_pre_accept=1
  fi
fi
previous_volume_override=""
if (( resuming_accept == 1 || resuming_pre_accept == 1 )); then
  phase_override_digest="$(macos_json_get "$phase_journal" volumeOverrideSha256 2>/dev/null || true)"
  [[ -f "$volume_override" ]] || macos_die "cutover resume is missing its volume override"
  override_digest="$(validate_cutover_volume_override "$volume_override" "$phase_override_digest")"
  if [[ ! -f "$volume_override.sha256" ]] || ! macos_check_checksum "$volume_override"; then
    macos_write_checksum "$volume_override"
  fi
else
  if [[ -e "$volume_override" || -e "$volume_override.sha256" ]]; then
    [[ -f "$volume_override" ]] || macos_die "existing formal volume override is incomplete"
    validate_cutover_volume_override "$volume_override" >/dev/null
    if [[ ! -f "$volume_override.sha256" ]] || ! macos_check_checksum "$volume_override"; then
      macos_write_checksum "$volume_override"
    fi
    if (( bootstrap_initial == 1 )); then
      # A crash between writing the unique override and its phase journal has
      # no canonical accepted state to preserve.  Remove only the validated
      # journal-shaped volume names, then regenerate the pair.
      stale_postgres_volume="$(awk '/^[[:space:]]+postgres_data:[[:space:]]*$/ { in_postgres=1; next } in_postgres && /^[[:space:]]+name:[[:space:]]*/ { print $2; exit }' "$volume_override")"
      stale_media_volume="$(awk '/^[[:space:]]+learning_media:[[:space:]]*$/ { in_media=1; next } in_media && /^[[:space:]]+name:[[:space:]]*/ { print $2; exit }' "$volume_override")"
      stale_worker_volume="$(awk '/^[[:space:]]+worker_state:[[:space:]]*$/ { in_worker=1; next } in_worker && /^[[:space:]]+name:[[:space:]]*/ { print $2; exit }' "$volume_override")"
      [[ "$stale_postgres_volume" =~ '^internal-exam-formal-cutover-[A-Za-z0-9-]+-postgres$' && "$stale_media_volume" =~ '^internal-exam-formal-cutover-[A-Za-z0-9-]+-media$' && "$stale_worker_volume" =~ '^internal-exam-formal-cutover-[A-Za-z0-9-]+-worker$' ]] || macos_die "existing cutover volume override contains unsafe names"
      for stale_volume in "$stale_postgres_volume" "$stale_media_volume" "$stale_worker_volume"; do
        if docker volume inspect "$stale_volume" >/dev/null 2>&1; then
          macos_run_checked docker volume rm "$stale_volume"
        fi
      done
      rm -f -- "$volume_override" "$volume_override.sha256"
    else
      previous_volume_override="$MACOS_LAYOUT_STATE/formal-volume-override.previous-$$.yml"
      cp -p -- "$volume_override" "$previous_volume_override"
      cp -p -- "$volume_override.sha256" "$previous_volume_override.sha256"
      chmod 600 "$previous_volume_override" "$previous_volume_override.sha256"
    fi
  fi
  volume_suffix="cutover-$(macos_timestamp)-$$-$RANDOM"
  cutover_postgres_volume="internal-exam-formal-${volume_suffix}-postgres"
  cutover_media_volume="internal-exam-formal-${volume_suffix}-media"
  cutover_worker_volume="internal-exam-formal-${volume_suffix}-worker"
  volume_override_content=$'volumes:\n  postgres_data:\n    name: '"$cutover_postgres_volume"$'\n  learning_media:\n    name: '"$cutover_media_volume"$'\n  worker_state:\n    name: '"$cutover_worker_volume"
  macos_write_atomic "$volume_override" "$volume_override_content"
  macos_write_checksum "$volume_override"
  if (( resuming_pre_accept == 0 )); then
    phase_json="{\"schemaVersion\":1,\"kind\":\"formal-cutover-phase\",\"phase\":\"restore-pending\",\"preparedState\":\"$(macos_json_escape "$prepared_state")\",\"preparedStateSha256\":\"$(macos_sha256 "$prepared_state")\",\"acceptedState\":\"$(macos_json_escape "$accepted_state")\",\"backupPath\":\"$(macos_json_escape "$backup_path")\",\"releasePath\":\"$(macos_json_escape "$release_path")\",\"volumeOverride\":\"$(macos_json_escape "$volume_override")\",\"volumeOverrideSha256\":\"$(macos_sha256 "$volume_override")\",\"datasetId\":\"$(macos_json_escape "$(macos_json_get "$prepared_state" dataset_id)")\",\"targetHostId\":\"$(macos_json_escape "$MACOS_HOST_ID")\",\"sourceWriterGeneration\":$source_writer_generation,\"targetWriterGeneration\":$target_writer_generation,\"updatedAt\":\"$(macos_now_iso)\"}"
    macos_write_atomic "$phase_journal" "$phase_json"
    macos_checksummed_json "$phase_journal"
  fi
fi
macos_phase_update() {
  local phase="$1" accepted_digest="${2:-}"
  macos_json_replace_atomic "$phase_journal" phase "\"$phase\""
  [[ -z "$accepted_digest" ]] || macos_json_replace_atomic "$phase_journal" acceptedStateSha256 "\"$accepted_digest\""
  macos_json_replace_atomic "$phase_journal" updatedAt "\"$(macos_now_iso)\""
  macos_write_checksum "$phase_journal"
}
"$SCRIPT_DIR/Test-ReleaseBundle.zsh" --release-path "$release_path" >/dev/null

cutover_status=failed
accepted_committed=0
accept_cutover_resume() {
  setopt local_options err_return
  [[ "$(macos_json_get "$accepted_state" state)" == accepted ]] || macos_die "resume accepted state is not canonical"
  [[ "$(macos_json_get "$accepted_state" target_write_accepted)" == false && "$(macos_json_get "$accepted_state" target_exposed)" == false ]] || macos_die "resume accepted state has an open write boundary"
  accepted_digest="$(macos_sha256 "$accepted_state")"
  # A crash after preflight/accept commonly leaves the formal project fully
  # stopped.  Bring up only the DB needed by the backend one-shot inspection;
  # public services stay down until the final activation step below.
  macos_compose "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" up -d --no-build db
  journal_phase="$(macos_json_get "$phase_journal" phase 2>/dev/null || true)"
  [[ "$journal_phase" == restore-pending || "$journal_phase" == preflight-passed || "$journal_phase" == accepted || "$journal_phase" == fence-transferred || "$journal_phase" == state-bound || "$journal_phase" == fence-released || "$journal_phase" == activation-intent || "$journal_phase" == activated ]] || macos_die "cutover phase journal cannot be resumed"
  fence_json="$(macos_operational_lock_one_shot_capture "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" inspect-fence)"
  fence_active="$(print -r -- "$fence_json" | plutil -extract active raw -o - 2>/dev/null || true)"
  fence_host="$(print -r -- "$fence_json" | plutil -extract hostId raw -o - 2>/dev/null || true)"
  fence_generation="$(print -r -- "$fence_json" | plutil -extract writerGeneration raw -o - 2>/dev/null || true)"
  fence_released_at="$(print -r -- "$fence_json" | plutil -extract releasedAt raw -o - 2>/dev/null || true)"
  if [[ "$fence_active" == true && "$fence_host" == "$(macos_json_get "$accepted_state" source_host_id)" && "$fence_generation" == "$source_writer_generation" ]]; then
    [[ "$journal_phase" == restore-pending || "$journal_phase" == preflight-passed || "$journal_phase" == accepted ]] || macos_die "resume found a source fence after a later cutover phase"
    transfer_result="$(macos_operational_lock_one_shot_with_mounts_capture "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" \
      --volume "$backup_path:/restored-cutover-backup:ro" \
      transfer-fence --dataset-id "$(macos_json_get "$accepted_state" dataset_id)" \
      --source-host-id "$(macos_json_get "$accepted_state" source_host_id)" \
      --source-writer-generation "$source_writer_generation" \
      --target-host-id "$MACOS_HOST_ID" --target-writer-generation "$target_writer_generation" \
      --restored-cutover-backup /restored-cutover-backup \
      --reason host-cutover-accept-resume --ttl-seconds 86400)"
    [[ "$(print -r -- "$transfer_result" | plutil -extract active raw -o - 2>/dev/null || true)" == true && "$(print -r -- "$transfer_result" | plutil -extract hostId raw -o - 2>/dev/null || true)" == "$MACOS_HOST_ID" ]] || macos_die "resume writer fence transfer was not verified"
    macos_phase_update fence-transferred "$accepted_digest"
  elif [[ "$fence_host" == "$MACOS_HOST_ID" && "$fence_generation" == "$target_writer_generation" ]]; then
    # The DB is already target-active (or target-released) after a prior
    # commit.  Never repeat source->target transfer; continue from observed
    # database identity rather than trusting the journal phase alone.
    [[ "$fence_active" == true || ( "$fence_active" == false && "$fence_released_at" != "" && "$fence_released_at" != null ) ]] || macos_die "resume target fence identity is incomplete"
    [[ "$journal_phase" != restore-pending && "$journal_phase" != preflight-passed ]] || macos_phase_update fence-transferred "$accepted_digest"
  else
    macos_die "resume writer fence is neither source-active, target-active, nor target-released"
  fi
  macos_adopt_cutover_identity "$(macos_json_get "$accepted_state" dataset_id)" "$MACOS_HOST_ID" "$target_writer_generation"
  bootstrap_release_json="$(macos_json_escape "$release_path")"
  bootstrap_backup_json="$(macos_json_escape "$backup_path")"
  macos_write_atomic "$MACOS_CURRENT_STATE" "{\"schemaVersion\":1,\"applicationVersion\":\"$(macos_json_escape "$release_version")\",\"gitCommit\":\"$(macos_json_escape "$release_commit")\",\"path\":\"$bootstrap_release_json\",\"promotedAt\":\"$(macos_now_iso)\",\"pairedBackupPath\":\"$bootstrap_backup_json\",\"datasetId\":\"$(macos_json_get "$accepted_state" dataset_id)\",\"hostId\":\"$MACOS_HOST_ID\",\"writerGeneration\":$target_writer_generation,\"bootstrap\":$bootstrap_current}"
  macos_write_checksum "$MACOS_CURRENT_STATE"
  bootstrap_current=0
  macos_phase_update state-bound "$accepted_digest"
  macos_claim_cutover_state "$prepared_state" "$accepted_state"
  activation_intent_path="$MACOS_LAYOUT_EVIDENCE/cutover-activation-intent-$(macos_timestamp)-$$.json"
  macos_write_atomic "$activation_intent_path" "{\"schemaVersion\":1,\"kind\":\"formal-cutover-activation-intent\",\"status\":\"intent\",\"activationIntent\":true,\"acceptedStateSha256\":\"$accepted_digest\",\"datasetId\":\"$(macos_json_get "$accepted_state" dataset_id)\",\"hostId\":\"$MACOS_HOST_ID\",\"writerGeneration\":$target_writer_generation,\"targetExposed\":false,\"targetWriteAccepted\":false,\"activationAttemptedAt\":\"$(macos_now_iso)\",\"approval\":\"manual-required\"}"
  macos_checksummed_json "$activation_intent_path"
  macos_phase_update activation-intent "$accepted_digest"
  if [[ "$fence_active" == true ]]; then
    release_result="$(macos_operational_lock_one_shot_capture "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" \
      release-fence --dataset-id "$(macos_json_get "$accepted_state" dataset_id)" --host-id "$MACOS_HOST_ID" --writer-generation "$target_writer_generation")"
    [[ "$(print -r -- "$release_result" | plutil -extract active raw -o - 2>/dev/null || true)" == false ]] || macos_die "resume target writer fence was not released"
  fi
  macos_phase_update fence-released "$accepted_digest"
  MACOS_PARENT_LOCK_PID="$$" "$SCRIPT_DIR/Start-Platform.zsh" --root "$root" --lock-held >/dev/null
  activation_path="$MACOS_LAYOUT_EVIDENCE/cutover-activation-$(macos_timestamp)-$$.json"
  macos_write_atomic "$activation_path" "{\"schemaVersion\":1,\"kind\":\"formal-cutover-activation\",\"status\":\"passed\",\"acceptedStateSha256\":\"$accepted_digest\",\"datasetId\":\"$(macos_json_get "$accepted_state" dataset_id)\",\"hostId\":\"$MACOS_HOST_ID\",\"writerGeneration\":$target_writer_generation,\"targetExposed\":true,\"targetWriteAccepted\":true,\"activatedAt\":\"$(macos_now_iso)\",\"releasePath\":\"$bootstrap_release_json\",\"approval\":\"manual-required\"}"
  macos_checksummed_json "$activation_path"
  macos_phase_update activated "$accepted_digest"
  cutover_status=passed
}

accept_cutover() {
  setopt local_options err_return
  cutover_media_volume="$(awk '/^[[:space:]]+learning_media:[[:space:]]*$/ { in_media=1; next } in_media && /^[[:space:]]+name:[[:space:]]*/ { print $2; exit }' "$volume_override")"
  [[ "$cutover_media_volume" =~ '^internal-exam-formal-cutover-[A-Za-z0-9-]+-media$' ]] || macos_die "cutover media volume override is invalid"
  # Validate and restore into an isolated project before touching formal data.
  second_copy_root="$(macos_formal_value SECOND_COPY_PATH)"
  second_copy_backup="$second_copy_root/${backup_path:t}"
  validate_cutover_external_bindings "$prepared_state" 0 "$backup_path"
  validate_cutover_external_bindings "$prepared_state" 0 "$second_copy_backup"
  MACOS_PARENT_LOCK_PID="$$" "$SCRIPT_DIR/Invoke-RestoreDrill.zsh" --second-copy-backup-path "$second_copy_backup" --release-path "$release_path" --no-db-audit --root "$root" --lock-held >/dev/null
  macos_compose_base "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT"
  macos_backend_one_shot_with_mounts "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" \
    --volume "$backup_path:/portable-backup:ro" \
    validate-migration-input /portable-backup
  macos_compose "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" down --remove-orphans
  if (( resuming_pre_accept == 1 )); then
    # Only the three names generated and checksummed by this journal may be
    # removed.  This resets an interrupted, never-accepted restore to truly
    # empty volumes without ever deleting an accepted formal dataset.
    cutover_postgres_volume="$(awk '/^[[:space:]]+postgres_data:[[:space:]]*$/ { in_postgres=1; next } in_postgres && /^[[:space:]]+name:[[:space:]]*/ { print $2; exit }' "$volume_override")"
    cutover_worker_volume="$(awk '/^[[:space:]]+worker_state:[[:space:]]*$/ { in_worker=1; next } in_worker && /^[[:space:]]+name:[[:space:]]*/ { print $2; exit }' "$volume_override")"
    [[ "$cutover_postgres_volume" =~ '^internal-exam-formal-cutover-[A-Za-z0-9-]+-postgres$' && "$cutover_media_volume" =~ '^internal-exam-formal-cutover-[A-Za-z0-9-]+-media$' && "$cutover_worker_volume" =~ '^internal-exam-formal-cutover-[A-Za-z0-9-]+-worker$' ]] || macos_die "pre-accept volume journal contains unsafe names"
    for cutover_volume in "$cutover_postgres_volume" "$cutover_media_volume" "$cutover_worker_volume"; do
      if docker volume inspect "$cutover_volume" >/dev/null 2>&1; then
        macos_run_checked docker volume rm "$cutover_volume"
      fi
    done
  fi
  macos_compose "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" up -d --no-build db
  macos_compose "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" cp \
    "$backup_path/database.dump" db:/tmp/internal-exam-cutover.dump
  macos_compose "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" exec -T db \
    pg_restore --clean --if-exists --no-owner --no-privileges -U exam -d internal_exam /tmp/internal-exam-cutover.dump
  macos_compose "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" exec -T db rm -f /tmp/internal-exam-cutover.dump
  gateway_image="$(macos_json_get "$release_path/release-manifest.json" imageDigests.gateway)"
  [[ "$gateway_image" == *":${release_commit:l}" ]] || macos_die "cutover gateway image is not the built release image"
  macos_run_checked docker run --rm --volume "$cutover_media_volume:/restore" \
    --volume "$backup_path:/backup:ro" "$gateway_image" tar -C /restore -xzf /backup/learning_media.tar.gz
  # Restore and preflight stay in the private maintenance project.  The
  # target must not expose candidate traffic before canonical accept and the
  # database fence transfer have completed.
  if (( bootstrap_current == 1 )); then
    bootstrap_release_json="$(macos_json_escape "$release_path")"
    bootstrap_backup_json="$(macos_json_escape "$backup_path")"
    macos_write_atomic "$MACOS_CURRENT_STATE" "{\"schemaVersion\":1,\"applicationVersion\":\"$(macos_json_escape "$release_version")\",\"gitCommit\":\"$(macos_json_escape "$release_commit")\",\"path\":\"$bootstrap_release_json\",\"promotedAt\":\"$(macos_now_iso)\",\"pairedBackupPath\":\"$bootstrap_backup_json\",\"datasetId\":\"$MACOS_DATASET_ID\",\"hostId\":\"$MACOS_HOST_ID\",\"writerGeneration\":$MACOS_WRITER_GENERATION,\"bootstrapPending\":true}"
    macos_write_checksum "$MACOS_CURRENT_STATE"
  fi
  MACOS_PARENT_LOCK_PID="$$" "$SCRIPT_DIR/Start-Platform.zsh" --root "$root" --maintenance --lock-held >/dev/null
  target_preflight_path="$MACOS_LAYOUT_EVIDENCE/target-preflight-$(macos_timestamp)-$$.json"
  MACOS_PARENT_LOCK_PID="$$" "$SCRIPT_DIR/Test-FormalPreflight.zsh" --root "$root" --lock-held \
    --target-maintenance \
    --backup-path "$backup_path" --browser-smoke-evidence "$browser_evidence" \
    --pf-evidence "$pf_evidence" --network-time-evidence "$network_time_evidence" \
    --evidence-path "$target_preflight_path" >/dev/null
  macos_check_checksum "$target_preflight_path"
  [[ "$(macos_json_get "$target_preflight_path" status 2>/dev/null || true)" == passed ]] || macos_die "target preflight evidence did not pass"
  MACOS_PARENT_LOCK_PID="$$" "$SCRIPT_DIR/Stop-Platform.zsh" --root "$root" --lock-held >/dev/null
  # The canonical fence transfer is a backend one-shot that must connect to
  # the restored DB.  Keep only the DB service up for this private transition;
  # public/backend/worker services remain stopped until activation is approved.
  macos_compose "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" up -d --no-build db
  macos_phase_update preflight-passed

  # Rebuild the release metadata on this target from the selected installed
  # release.  The source prepared state's metadata is not reused as target
  # evidence, which keeps architecture/host-specific image identity explicit.
  target_metadata_path="$MACOS_LAYOUT_STATE/${prepared_state:t:r}.target-release-metadata.json"
  target_image_refs_json="{"
  for image_name in db backend frontend gateway; do
    [[ "$target_image_refs_json" == "{" ]] || target_image_refs_json+=","
    target_image_refs_json+="\"$image_name\":\"$(macos_json_get "$release_path/ops/release/built-image-identity.json" "images.$image_name.id")\""
  done
  target_image_refs_json+="}"
  macos_write_atomic "$MACOS_LAYOUT_STATE/target-cutover-image-references.json" "$target_image_refs_json"
  macos_write_checksum "$MACOS_LAYOUT_STATE/target-cutover-image-references.json"
  target_base_refs_json="$(plutil -extract baseImageReferences json -o - -- "$release_path/release-manifest.json")"
  macos_write_atomic "$MACOS_LAYOUT_STATE/target-cutover-base-image-references.json" "$target_base_refs_json"
  macos_write_checksum "$MACOS_LAYOUT_STATE/target-cutover-base-image-references.json"
  target_checksums_json="{"
  while IFS= read -r checksum_line || [[ -n "$checksum_line" ]]; do
    [[ "$checksum_line" =~ '^([0-9a-fA-F]{64})[[:space:]][[:space:]](.+)$' ]] || macos_die "target release checksum row is invalid"
    [[ "$target_checksums_json" == "{" ]] || target_checksums_json+=","
    target_checksums_json+="\"$(macos_json_escape "${match[2]}")\":\"${match[1]:l}\""
  done < "$release_path/SHA256SUMS"
  target_checksums_json+="}"
  macos_write_atomic "$MACOS_LAYOUT_STATE/target-cutover-release-checksums.json" "$target_checksums_json"
  macos_write_checksum "$MACOS_LAYOUT_STATE/target-cutover-release-checksums.json"
  macos_backend_one_shot_with_mounts "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" \
    --volume "$MACOS_LAYOUT_STATE:/cutover-state" \
    release-metadata \
    --application-version "$(macos_json_get "$release_path/release-manifest.json" applicationVersion)" \
    --git-commit "${release_commit:l}" --host-os darwin --architecture arm64 \
    --target-platform linux/arm64 --migration-head "$(macos_json_get "$release_path/release-manifest.json" migrationHead)" \
    --image-references /cutover-state/target-cutover-image-references.json \
    --base-image-references /cutover-state/target-cutover-base-image-references.json \
    --release-file-checksums /cutover-state/target-cutover-release-checksums.json \
    --output "/cutover-state/${target_metadata_path:t}"
  [[ -f "$target_metadata_path" && -f "$target_metadata_path.sha256" ]] || macos_die "target release metadata was not written"
  macos_check_checksum "$target_metadata_path"
  target_release_metadata_json="$(plutil -convert json -o - -- "$target_metadata_path")"
  target_preflight_checked_at="$(macos_json_get "$target_preflight_path" checkedAt 2>/dev/null || macos_json_get "$target_preflight_path" checked_at 2>/dev/null || true)"
  target_evidence_path="$MACOS_LAYOUT_EVIDENCE/target-preflight-bound-$(macos_timestamp)-$$.json"
  target_evidence_json="{\"schema_version\":1,\"kind\":\"target-preflight\",\"status\":\"passed\",\"checked_at\":\"$(macos_json_escape "$target_preflight_checked_at")\",\"dataset_id\":\"$(macos_json_get "$prepared_state" dataset_id)\",\"target_host_id\":\"$(macos_json_escape "$MACOS_HOST_ID")\",\"target_writer_generation\":$target_writer_generation,\"release_metadata\":$target_release_metadata_json,\"checks\":{\"hostOS\":\"darwin\",\"architecture\":\"arm64\",\"candidatePort\":28080,\"operatorPort\":28081,\"targetMaintenance\":true}}"
  macos_write_atomic "$target_evidence_path" "$target_evidence_json"
  macos_checksummed_json "$target_evidence_path"

  # The backend image is the sole authority for dataset/host identity and
  # writer-generation transitions.  It consumes the checksummed prepared
  # state only after the target preflight has passed and records the explicit
  # write-acceptance boundary in the canonical accepted state.
  macos_backend_one_shot_with_mounts "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" \
    --volume "$MACOS_LAYOUT_STATE:/cutover-state" \
    --volume "$MACOS_LAYOUT_EVIDENCE:/preflight-evidence:ro" \
    accept-cutover "/cutover-state/${prepared_state:t}" \
    --target-host-id "$MACOS_HOST_ID" \
    --target-preflight-evidence "/preflight-evidence/${target_evidence_path:t}" \
    --state-path "/cutover-state/${accepted_state:t}" \
    --target-writer-generation "$target_writer_generation" \
    --target-not-exposed --target-write-not-accepted --source-fully-stopped
  [[ -f "$accepted_state" && -f "$accepted_state.sha256" ]] || macos_die "canonical accepted cutover state was not written"
  chmod 600 "$accepted_state" "$accepted_state.sha256"
  macos_secure_path "$accepted_state"
  macos_secure_path "$accepted_state.sha256"
  macos_check_checksum "$accepted_state"
  [[ "$(macos_json_get "$accepted_state" state)" == accepted ]] || macos_die "canonical cutover state is not accepted"
  [[ "$(macos_json_get "$accepted_state" dataset_id)" == "$(macos_json_get "$prepared_state" dataset_id)" ]] || macos_die "accepted dataset identity changed"
  [[ "$(macos_json_get "$accepted_state" target_writer_generation)" == "$target_writer_generation" ]] || macos_die "accepted writer generation is invalid"
  [[ "$(macos_json_get "$accepted_state" target_preflight_status)" == passed ]] || macos_die "accepted state does not contain passed preflight"
  [[ "$(macos_json_get "$accepted_state" target_write_accepted)" == false ]] || macos_die "canonical cutover target write boundary is not closed"
  [[ "$(macos_json_get "$accepted_state" target_exposed)" == false ]] || macos_die "canonical cutover target exposure boundary is not closed"
  [[ "$(macos_json_get "$accepted_state" target_write_authorized)" == true ]] || macos_die "canonical cutover did not authorize the target transition"
  validate_cutover_external_bindings "$accepted_state" 1 "$backup_path"
  accepted_digest="$(macos_sha256 "$accepted_state")"
  accepted_committed=1
  macos_phase_update accepted "$accepted_digest"
  # The restored database contains the source fence. Transfer it atomically
  # to this target, then release it before any public Compose start.
  transfer_result="$(macos_operational_lock_one_shot_with_mounts_capture "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" \
    --volume "$backup_path:/restored-cutover-backup:ro" \
    transfer-fence --dataset-id "$(macos_json_get "$prepared_state" dataset_id)" \
    --source-host-id "$(macos_json_get "$prepared_state" source_host_id)" \
    --source-writer-generation "$source_writer_generation" \
    --target-host-id "$MACOS_HOST_ID" --target-writer-generation "$target_writer_generation" \
    --restored-cutover-backup /restored-cutover-backup \
    --reason host-cutover-accept --ttl-seconds 86400)"
  [[ "$(print -r -- "$transfer_result" | plutil -extract active raw -o - 2>/dev/null || true)" == true ]] || macos_die "canonical writer fence transfer did not become active"
  [[ "$(print -r -- "$transfer_result" | plutil -extract hostId raw -o - 2>/dev/null || true)" == "$MACOS_HOST_ID" ]] || macos_die "canonical writer fence transfer target is invalid"
  macos_phase_update fence-transferred "$accepted_digest"
  macos_adopt_cutover_identity "$(macos_json_get "$accepted_state" dataset_id)" "$(macos_json_get "$accepted_state" target_host_id)" "$target_writer_generation"
  bootstrap_release_json="$(macos_json_escape "$release_path")"
  bootstrap_backup_json="$(macos_json_escape "$backup_path")"
  macos_write_atomic "$MACOS_CURRENT_STATE" "{\"schemaVersion\":1,\"applicationVersion\":\"$(macos_json_escape "$release_version")\",\"gitCommit\":\"$(macos_json_escape "$release_commit")\",\"path\":\"$bootstrap_release_json\",\"promotedAt\":\"$(macos_now_iso)\",\"pairedBackupPath\":\"$bootstrap_backup_json\",\"datasetId\":\"$(macos_json_get "$accepted_state" dataset_id)\",\"hostId\":\"$(macos_json_get "$accepted_state" target_host_id)\",\"writerGeneration\":$target_writer_generation,\"bootstrap\":$bootstrap_current}"
  macos_write_checksum "$MACOS_CURRENT_STATE"
  bootstrap_current=0
  macos_claim_cutover_state "$prepared_state" "$accepted_state"
  macos_phase_update state-bound "$accepted_digest"
  # Persist a conservative activation intent before public Compose start.  If
  # the process dies after the gateway is opened but before the passed record
  # is written, rollback must still assume that target writes may have landed.
  accepted_digest="$(macos_sha256 "$accepted_state")"
  activation_intent_path="$MACOS_LAYOUT_EVIDENCE/cutover-activation-intent-$(macos_timestamp)-$$.json"
  macos_write_atomic "$activation_intent_path" "{\"schemaVersion\":1,\"kind\":\"formal-cutover-activation-intent\",\"status\":\"intent\",\"activationIntent\":true,\"acceptedStateSha256\":\"$accepted_digest\",\"datasetId\":\"$(macos_json_get "$accepted_state" dataset_id)\",\"hostId\":\"$(macos_json_get "$accepted_state" target_host_id)\",\"writerGeneration\":$target_writer_generation,\"targetExposed\":false,\"targetWriteAccepted\":false,\"activationAttemptedAt\":\"$(macos_now_iso)\",\"approval\":\"manual-required\"}"
  macos_checksummed_json "$activation_intent_path"
  macos_phase_update activation-intent "$accepted_digest"
  # Keep the target fence active until both the local identity/current state
  # and the conservative activation intent are durable.  A crash before this
  # release therefore cannot reopen the target from stale local state.
  release_result="$(macos_operational_lock_one_shot_capture "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" \
    release-fence --dataset-id "$(macos_json_get "$prepared_state" dataset_id)" \
    --host-id "$MACOS_HOST_ID" --writer-generation "$target_writer_generation")"
  [[ "$(print -r -- "$release_result" | plutil -extract active raw -o - 2>/dev/null || true)" == false ]] || macos_die "target writer fence was not released"
  macos_phase_update fence-released "$accepted_digest"
  # Public exposure is deliberately last. The passed activation record binds
  # the accepted digest and records the now-public boundary for rollback.
  MACOS_PARENT_LOCK_PID="$$" "$SCRIPT_DIR/Start-Platform.zsh" --root "$root" --lock-held >/dev/null
  activation_path="$MACOS_LAYOUT_EVIDENCE/cutover-activation-$(macos_timestamp)-$$.json"
  macos_write_atomic "$activation_path" "{\"schemaVersion\":1,\"kind\":\"formal-cutover-activation\",\"status\":\"passed\",\"acceptedStateSha256\":\"$accepted_digest\",\"datasetId\":\"$(macos_json_get "$accepted_state" dataset_id)\",\"hostId\":\"$(macos_json_get "$accepted_state" target_host_id)\",\"writerGeneration\":$target_writer_generation,\"targetExposed\":true,\"targetWriteAccepted\":true,\"activatedAt\":\"$(macos_now_iso)\",\"releasePath\":\"$bootstrap_release_json\",\"approval\":\"manual-required\"}"
  macos_checksummed_json "$activation_path"
  macos_phase_update activated "$accepted_digest"
  cutover_status=passed
}

run_accept() {
  if (( resuming_accept == 1 )); then
    accept_cutover_resume
  else
    accept_cutover
  fi
}

if ! run_accept; then
  MACOS_PARENT_LOCK_PID="$$" "$SCRIPT_DIR/Stop-Platform.zsh" --root "$root" --lock-held >/dev/null 2>&1 || true
  # The backend accept is the canonical commit point.  Re-read its durable
  # consumed marker and all deterministic backend staging files before any
  # cleanup: a crash/error after reservation, accepted output, or claim
  # staging must preserve the exact phase/override/volumes for recovery.
  canonical_transaction_evidence=0
  for canonical_artifact in \
    "${prepared_state}.consumed.json" "${prepared_state}.consumed.json.sha256" \
    "${prepared_state:h}/.${prepared_state:t}.consumed.json.cutover-write.tmp" \
    "${prepared_state:h}/.${prepared_state:t}.consumed.json.sha256.cutover-write.tmp" \
    "${prepared_state:h}/.${prepared_state:t}.consumed.json.cutover-claim.tmp" \
    "${prepared_state:h}/.${prepared_state:t}.consumed.json.sha256.cutover-claim.tmp" \
    "${prepared_state:h}/.${prepared_state:t}.cutover-claim.tmp" \
    "${prepared_state:h}/.${prepared_state:t}.sha256.cutover-claim.tmp" \
    "$accepted_state" "$accepted_state.sha256" \
    "$accepted_state:h/.${accepted_state:t}.cutover-write.tmp" \
    "$accepted_state:h/.${accepted_state:t}.sha256.cutover-write.tmp" \
    "$accepted_state:h/.${accepted_state:t}.cutover-claim.tmp" \
    "$accepted_state:h/.${accepted_state:t}.sha256.cutover-claim.tmp"; do
    if [[ -e "$canonical_artifact" ]]; then
      canonical_transaction_evidence=1
      break
    fi
  done
  if (( canonical_transaction_evidence == 1 )); then
    accepted_committed=1
  fi
  if (( bootstrap_initial == 1 && accepted_committed == 0 && resuming_accept == 0 && canonical_transaction_evidence == 0 )); then
    rm -f -- "$MACOS_CURRENT_STATE" "$MACOS_CURRENT_STATE.sha256"
    rm -f -- "$volume_override" "$volume_override.sha256" "$phase_journal" "$phase_journal.sha256"
  elif (( accepted_committed == 0 && resuming_accept == 0 && canonical_transaction_evidence == 0 )) && [[ -n "$previous_volume_override" ]]; then
    mv -f -- "$previous_volume_override" "$volume_override"
    mv -f -- "$previous_volume_override.sha256" "$volume_override.sha256"
    rm -f -- "$phase_journal" "$phase_journal.sha256"
  fi
fi

if [[ "$cutover_status" == passed ]]; then
  macos_log "host_cutover_accepted version=$release_version commit=$release_commit dataset=$(macos_json_get "$accepted_state" dataset_id) target_host=$(macos_json_get "$accepted_state" target_host_id) writer_generation=$(macos_json_get "$accepted_state" target_writer_generation) state=${accepted_state:t} approval=manual-required"
else
  macos_die "target cutover acceptance failed; target formal project was stopped"
fi
