#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
source "$SCRIPT_DIR/Common.zsh"

target_host=""
prepared_state_arg=""
confirmation=""
root="${INTERNAL_EXAM_ROOT:-${HOME:?}/Library/Application Support/InternalExam}"
while (( $# > 0 )); do
  case "$1" in
    --target-host) (( $# >= 2 )) || macos_die "--target-host requires a label"; target_host="$2"; shift 2 ;;
    --state-path|--prepared-state|--prepared-evidence) (( $# >= 2 )) || macos_die "$1 requires a path"; prepared_state_arg="$2"; shift 2 ;;
    --confirmation) (( $# >= 2 )) || macos_die "--confirmation requires exact text"; confirmation="$2"; shift 2 ;;
    --root) (( $# >= 2 )) || macos_die "--root requires a path"; root="$2"; shift 2 ;;
    -h|--help) print -r -- "usage: $0 --target-host LABEL --confirmation 'PREPARE HOST CUTOVER' [--state-path PATH] [--root ROOT]"; exit 0 ;;
    *) macos_die "unknown argument: $1"; exit 1 ;;
  esac
done

macos_assert_macos
[[ -n "$target_host" ]] || macos_die "target host is required"
[[ "$confirmation" == 'PREPARE HOST CUTOVER' ]] || macos_die "exact cutover preparation confirmation did not match"
[[ "$target_host" != *$'\n'* && "$target_host" != *$'\r'* ]] || macos_die "target host label is invalid"
macos_assert_outside_worktree "$root" >/dev/null
macos_layout "$root"
macos_assert_protected_configuration "$root"
macos_require_formal_paths
macos_docker_ready
prepare_status=failed
fence_acquired=0
existing_prepared=0
selected_new_prepared=0
partial_prepared=0
prepared_state=""
prepare_phase_journal=""
prepare_phase="initialized"
cleanup_prepare() {
  local preserve_fence=0
  if [[ -n "${prepared_state:-}" && -f "$prepared_state" && -f "$prepared_state.sha256" ]]; then
    if macos_check_checksum "$prepared_state" >/dev/null 2>&1; then
      case "$(macos_json_get "$prepared_state" state 2>/dev/null || true)" in
        prepared|consumed) preserve_fence=1 ;;
      esac
    fi
  fi
  case "${prepare_phase:-initialized}" in
    backup-passed|source-stopped|prepared) preserve_fence=1 ;;
  esac
  if [[ -n "${prepared_state:-}" ]]; then
    # A backend pair write may have created only a deterministic staging file
    # before the shell phase update.  Preserve the fence in that case too;
    # deleting the phase/inputs would make the exact retry unrecoverable.
    for canonical_prepare_artifact in \
      "$prepared_state:h/.${prepared_state:t}.cutover-write.tmp" \
      "$prepared_state:h/.${prepared_state:t}.sha256.cutover-write.tmp"; do
      if [[ -e "$canonical_prepare_artifact" ]]; then
        preserve_fence=1
        break
      fi
    done
  fi
  if (( preserve_fence == 0 )) && [[ "$prepare_status" != passed ]] && [[ -n "${release_path:-}" ]]; then
    if (( fence_acquired == 1 )); then
      macos_operational_lock_one_shot "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" \
        release-fence --dataset-id "$MACOS_DATASET_ID" --host-id "$MACOS_HOST_ID" \
        --writer-generation "$MACOS_WRITER_GENERATION" >/dev/null 2>&1 || true
    fi
    # A failed pre-canonical attempt may have started only postgres for fence
    # inspection.  Leave the entire formal project stopped after releasing the
    # fence so a retry cannot expose a partially prepared source.
    macos_compose "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" stop >/dev/null 2>&1 || true
  fi
  macos_release_lock
}
trap cleanup_prepare EXIT
macos_release_state "$MACOS_CURRENT_STATE"
release_path="$MACOS_STATE_PATH"
release_commit="$MACOS_STATE_COMMIT"
if [[ -n "$prepared_state_arg" ]]; then
  prepared_state="$(macos_resolve_path "$prepared_state_arg")"
  [[ "${prepared_state:h}" == "$MACOS_LAYOUT_STATE" ]] || macos_die "cutover state must stay in the protected state directory"
  [[ "$prepared_state" != *.consumed.json ]] || macos_die "a consumed cutover state cannot be reused"
  if [[ -e "$prepared_state" || -e "$prepared_state.sha256" ]]; then
    [[ -f "$prepared_state" || ! -f "$prepared_state.sha256" ]] || macos_die "prepared cutover state is incomplete"
    existing_prepared=1
  fi
else
  prepared_state="$MACOS_LAYOUT_STATE/cutover-prepared.json"
  if [[ -e "$prepared_state" || -e "$prepared_state.sha256" ]]; then
    if [[ -f "$prepared_state" && -f "$prepared_state.sha256" && -f "${prepared_state}.consumed.json" && -f "${prepared_state}.consumed.json.sha256" ]]; then
      prepared_state="$MACOS_LAYOUT_STATE/cutover-prepared-$(macos_timestamp)-$$-$RANDOM.json"
      selected_new_prepared=1
    elif [[ -f "$prepared_state" && ! -f "$prepared_state.sha256" ]]; then
      existing_prepared=1
    elif [[ -f "$prepared_state" && -f "$prepared_state.sha256" ]]; then
      existing_prepared=1
    else
      macos_die "prepared cutover state is incomplete"
    fi
  fi
fi
"$SCRIPT_DIR/Test-ReleaseBundle.zsh" --release-path "$release_path" >/dev/null
macos_verify_built_image_identity "$release_path"
macos_cutover_identity
macos_acquire_lock "$MACOS_LAYOUT_STATE/.operation.lock"
prepare_phase_journal="$MACOS_LAYOUT_STATE/cutover-prepare-${prepared_state:t:r}.json"
prepare_phase_update() {
  local next_phase="$1" backup_value="${2:-}" temporary
  if [[ ! -f "$prepare_phase_journal" ]]; then
    macos_write_atomic "$prepare_phase_journal" "{\"schemaVersion\":1,\"kind\":\"formal-cutover-prepare-phase\",\"phase\":\"initialized\",\"preparedState\":\"$(macos_json_escape "$prepared_state")\",\"datasetId\":\"$MACOS_DATASET_ID\",\"sourceHostId\":\"$MACOS_HOST_ID\",\"targetHostId\":\"$(macos_json_escape "$target_host")\",\"writerGeneration\":$MACOS_WRITER_GENERATION,\"createdAt\":\"$(macos_now_iso)\"}"
    macos_checksummed_json "$prepare_phase_journal"
  fi
  temporary="$(mktemp "${prepare_phase_journal}.tmp.XXXXXX")"
  cp -p -- "$prepare_phase_journal" "$temporary"
  chmod 600 "$temporary"
  plutil -replace phase -string "$next_phase" -- "$temporary" >/dev/null 2>&1 || { rm -f -- "$temporary"; macos_die "prepare phase update failed"; return 1; }
  [[ -z "$backup_value" ]] || plutil -replace backupPath -string "$backup_value" -- "$temporary" >/dev/null 2>&1 || { rm -f -- "$temporary"; macos_die "prepare phase backup binding failed"; return 1; }
  plutil -replace updatedAt -string "$(macos_now_iso)" -- "$temporary" >/dev/null 2>&1 || { rm -f -- "$temporary"; macos_die "prepare phase timestamp update failed"; return 1; }
  mv -f -- "$temporary" "$prepare_phase_journal"
  chmod 600 "$prepare_phase_journal"
  macos_write_checksum "$prepare_phase_journal"
  prepare_phase="$next_phase"
}
if [[ -e "$prepare_phase_journal" || -e "$prepare_phase_journal.sha256" ]]; then
  [[ -f "$prepare_phase_journal" ]] || macos_die "prepare phase journal is incomplete"
  if [[ ! -f "$prepare_phase_journal.sha256" ]] || ! macos_check_checksum "$prepare_phase_journal" >/dev/null 2>&1; then
    plutil -convert json -o - -- "$prepare_phase_journal" >/dev/null 2>&1 || macos_die "prepare phase journal is invalid"
    macos_write_checksum "$prepare_phase_journal"
  fi
  [[ "$(macos_json_get "$prepare_phase_journal" preparedState 2>/dev/null || true)" == "$prepared_state" ]] || macos_die "prepare phase journal is bound to another state"
  [[ "$(macos_json_get "$prepare_phase_journal" datasetId 2>/dev/null || true)" == "$MACOS_DATASET_ID" && "$(macos_json_get "$prepare_phase_journal" sourceHostId 2>/dev/null || true)" == "$MACOS_HOST_ID" ]] || macos_die "prepare phase journal identity does not match this source"
  prepare_phase="$(macos_json_get "$prepare_phase_journal" phase 2>/dev/null || true)"
  [[ "$prepare_phase" == initialized || "$prepare_phase" == fence-acquired || "$prepare_phase" == backup-passed || "$prepare_phase" == source-stopped || "$prepare_phase" == prepared ]] || macos_die "prepare phase journal phase is invalid"
  if [[ "$prepare_phase" == prepared ]]; then
    [[ -f "$prepared_state" && -f "$prepared_state.sha256" ]] || macos_die "prepared phase journal has no canonical prepared state"
    existing_prepared=1
  fi
  if (( existing_prepared == 1 )) && [[ ! -f "$prepared_state.sha256" ]]; then
    [[ "$prepare_phase" == source-stopped ]] || macos_die "incomplete prepared state is not covered by a stopped-source phase journal"
    # The canonical backend owns recovery of this exact path.  Keep the
    # partial artifact and its active fence; never delete/recreate it here.
    existing_prepared=0
    partial_prepared=1
  fi
else
  prepare_phase_update initialized
fi
macos_compose "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" up -d --no-build db
if (( selected_new_prepared == 1 )); then
  for consumed_candidate in "$MACOS_LAYOUT_STATE"/cutover-prepared*.json(N); do
    [[ "$consumed_candidate" == "$prepared_state" || "$consumed_candidate" == *.consumed.json ]] && continue
    [[ -f "$consumed_candidate" && -f "$consumed_candidate.sha256" ]] || continue
    macos_check_checksum "$consumed_candidate" >/dev/null 2>&1 || continue
    [[ "$(macos_json_get "$consumed_candidate" state 2>/dev/null || true)" == consumed ]] || continue
    [[ "$(macos_json_get "$consumed_candidate" dataset_id 2>/dev/null || true)" == "$MACOS_DATASET_ID" ]] || continue
    [[ "$(macos_json_get "$consumed_candidate" source_host_id 2>/dev/null || true)" == "$MACOS_HOST_ID" ]] || continue
    consumed_generation="$(macos_json_get "$consumed_candidate" source_writer_generation 2>/dev/null || macos_json_get "$consumed_candidate" writer_generation 2>/dev/null || true)"
    [[ "$consumed_generation" =~ '^[1-9][0-9]*$' ]] || macos_die "consumed prepared state writer generation is invalid"
    (( consumed_generation < MACOS_WRITER_GENERATION )) || macos_die "a consumed cutover already covers the current source writer generation; resume reconciliation before preparing another cutover"
  done
fi
if (( existing_prepared == 1 )); then
  macos_secure_path "$prepared_state"
  macos_check_checksum "$prepared_state"
  [[ "$(macos_json_get "$prepared_state" state 2>/dev/null || true)" == prepared ]] || macos_die "existing prepared cutover state is not reusable"
  [[ "$(macos_json_get "$prepared_state" dataset_id 2>/dev/null || true)" == "$MACOS_DATASET_ID" ]] || macos_die "existing prepared state dataset does not match this source"
  [[ "$(macos_json_get "$prepared_state" source_host_id 2>/dev/null || true)" == "$MACOS_HOST_ID" ]] || macos_die "existing prepared state source host does not match this source"
  [[ "$(macos_json_get "$prepared_state" target_host_id 2>/dev/null || true)" == "$target_host" ]] || macos_die "existing prepared state target host does not match the requested target"
  [[ "$(macos_json_get "$prepared_state" writer_generation 2>/dev/null || true)" == "$MACOS_WRITER_GENERATION" ]] || macos_die "existing prepared state writer generation does not match this source"
  case "$(macos_json_get "$prepared_state" source_gateway_stopped 2>/dev/null || true)" in
    1|true) ;;
    *) macos_die "existing prepared state does not prove source stopped" ;;
  esac
  existing_backup_id="$(macos_json_get "$prepared_state" backup_id 2>/dev/null || true)"
  [[ "$existing_backup_id" =~ '^backup-[0-9]{8}T[0-9]{6}Z$' ]] || macos_die "existing prepared state backup identity is invalid"
  existing_backup_path="$MACOS_LAYOUT_BACKUPS/$existing_backup_id"
  macos_assert_backup "$existing_backup_path" >/dev/null
  macos_compose "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" stop
  existing_running_services="$(macos_compose_capture "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" ps --status running -q)"
  [[ -z "${existing_running_services//[[:space:]]/}" ]] || macos_die "formal source project still has running containers"
  # The DB may be stopped after a crash.  Bring up only DB long enough to
  # inspect the persistent fence, then stop it again before returning the
  # already-committed prepared artifact.
  macos_compose "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" up -d --no-build db
  macos_assert_writer_fence_owner "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" "$MACOS_DATASET_ID" "$MACOS_HOST_ID" "$MACOS_WRITER_GENERATION"
  macos_compose "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" stop
  existing_running_services="$(macos_compose_capture "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" ps --status running -q)"
  [[ -z "${existing_running_services//[[:space:]]/}" ]] || macos_die "formal source project could not be stopped after prepared-state recovery"
  prepare_phase_update prepared
  prepare_status=passed
  macos_log "host_cutover_prepared_existing target=$(macos_json_get "$prepared_state" target_host_id) dataset=$MACOS_DATASET_ID writer_generation=$MACOS_WRITER_GENERATION state=${prepared_state:t}"
  exit 0
fi
prior_prepare_phase="$prepare_phase"
if macos_assert_writer_fence_owner "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" "$MACOS_DATASET_ID" "$MACOS_HOST_ID" "$MACOS_WRITER_GENERATION" >/dev/null 2>&1; then
  fence_acquired=1
else
  macos_operational_lock_one_shot "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" \
    acquire-fence --dataset-id "$MACOS_DATASET_ID" --host-id "$MACOS_HOST_ID" \
    --writer-generation "$MACOS_WRITER_GENERATION" --reason host-cutover-prepare --ttl-seconds 86400
  fence_acquired=1
fi
prepare_phase_update fence-acquired
backup_reused=0
if [[ "$prior_prepare_phase" == backup-passed || "$prior_prepare_phase" == source-stopped ]]; then
  backup_path="$(macos_json_get "$prepare_phase_journal" backupPath 2>/dev/null || true)"
  backup_id="${backup_path:t}"
  [[ -n "$backup_path" && "$backup_id" =~ '^backup-[0-9]{8}T[0-9]{6}Z$' ]] || macos_die "prepare phase journal final backup is invalid"
  backup_reused=1
  backup_output="status=passed second_copy=passed backup=$backup_id"
else
  backup_output="$(MACOS_PARENT_LOCK_PID="$$" "$SCRIPT_DIR/Invoke-PairedBackup.zsh" --root "$root" --kind cutover --under-writer-fence --lock-held)"
fi
backup_id="$(print -r -- "$backup_output" | sed -nE 's/.* backup=(backup-[0-9]{8}T[0-9]{6}Z).*/\1/p' | tail -n 1)"
[[ "$backup_output" == *"status=passed"* && "$backup_output" == *"second_copy=passed"* && "$backup_id" =~ '^backup-[0-9]{8}T[0-9]{6}Z$' ]] || macos_die "fenced final paired backup did not pass local and second-copy verification"
backup_path="$MACOS_LAYOUT_BACKUPS/$backup_id"
macos_assert_backup "$backup_path" >/dev/null
macos_assert_outside_worktree "$backup_path" >/dev/null
backup_manifest="$backup_path/manifest.json"
[[ -f "$backup_manifest" ]] || macos_die "final backup manifest is missing"
plutil -convert json -o - -- "$backup_manifest" >/dev/null 2>&1 || macos_die "final backup manifest is invalid"
[[ "$(macos_json_get "$backup_manifest" dataset_id 2>/dev/null || true)" == "$MACOS_DATASET_ID" ]] || macos_die "final backup dataset identity does not match this source"
[[ "$(macos_json_get "$backup_manifest" source_host_id 2>/dev/null || true)" == "$MACOS_HOST_ID" ]] || macos_die "final backup source host identity does not match this source"
[[ "$(macos_json_get "$backup_manifest" writer_generation 2>/dev/null || true)" == "$MACOS_WRITER_GENERATION" ]] || macos_die "final backup writer generation does not match this source"
fence_backup_evidence=""
for candidate in "$backup_path:h/evidence"/backup-opportunity-*.json(N); do
  [[ -f "$candidate" && -f "$candidate.sha256" ]] || continue
  macos_check_checksum "$candidate"
  [[ "$(macos_json_get "$candidate" status 2>/dev/null || true)" == passed ]] || continue
  [[ "$(macos_json_get "$candidate" backup_id 2>/dev/null || true)" == "${backup_path:t}" ]] || continue
  [[ "$(macos_json_get "$candidate" writer_fence_boundary.dataset_id 2>/dev/null || true)" == "$MACOS_DATASET_ID" ]] || continue
  [[ "$(macos_json_get "$candidate" writer_fence_boundary.source_host_id 2>/dev/null || true)" == "$MACOS_HOST_ID" ]] || continue
  [[ "$(macos_json_get "$candidate" writer_fence_boundary.writer_generation 2>/dev/null || true)" == "$MACOS_WRITER_GENERATION" ]] || continue
  fence_backup_evidence="$candidate"
  break
done
[[ -n "$fence_backup_evidence" ]] || macos_die "final backup was not created under the active writer fence; rerun Invoke-PairedBackup with --under-writer-fence"
prepare_phase_update backup-passed "$backup_path"

if (( partial_prepared == 0 )); then
  [[ ! -e "$prepared_state" && ! -e "$prepared_state.sha256" ]] || macos_die "cutover state destination already exists"
fi

macos_compose_base "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT"
macos_backend_one_shot_with_mounts "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" \
  --volume "$backup_path:/portable-backup:ro" \
  validate-migration-input /portable-backup
macos_run_checked docker "${MACOS_COMPOSE_ARGS[@]}" run --rm --no-deps backend \
  uv run --no-sync python -m app.ops.operator_control check-session-closure

# Stop every service in the fixed formal project.  A successful `stop` is not
# enough evidence: prove Compose reports no running container before the
# backend canonical prepare-cutover attestation is emitted.
macos_compose "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" stop
running_services="$(macos_compose_capture "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" ps --status running -q)"
[[ -z "${running_services//[[:space:]]/}" ]] || macos_die "formal source project still has running containers"
prepare_phase_update source-stopped

# The canonical backend now requires two checksummed, non-secret inputs: a
# release identity and a whole-project stop proof.  Generate them only after
# Compose has proved the source is stopped, then mount them read-only/owner-
# only into the selected backend image.
release_metadata_path="$MACOS_LAYOUT_STATE/${prepared_state:t:r}.release-metadata.json"
stop_proof_path="$MACOS_LAYOUT_STATE/${prepared_state:t:r}.source-stop-proof.json"
reuse_prerequisites=0
canonical_prepare_write_evidence=0
for canonical_prepare_artifact in \
  "$prepared_state" "$prepared_state.sha256" \
  "$prepared_state:h/.${prepared_state:t}.cutover-write.tmp" \
  "$prepared_state:h/.${prepared_state:t}.sha256.cutover-write.tmp"; do
  if [[ -e "$canonical_prepare_artifact" ]]; then
    canonical_prepare_write_evidence=1
    break
  fi
done
if [[ "$prior_prepare_phase" == source-stopped && "$canonical_prepare_write_evidence" == 1 ]]; then
  # Once the backend has started its exact state transaction, all prerequisite
  # inputs must be reused byte-for-byte.  If no canonical/hidden state write
  # exists yet, the derived metadata/proof files can safely be regenerated.
  for prerequisite in "$release_metadata_path" "$stop_proof_path" \
    "$MACOS_LAYOUT_STATE/cutover-image-references.json" \
    "$MACOS_LAYOUT_STATE/cutover-base-image-references.json" \
    "$MACOS_LAYOUT_STATE/cutover-release-checksums.json"; do
    [[ -f "$prerequisite" && -f "$prerequisite.sha256" ]] || macos_die "source-stopped prepare phase is missing a checksummed prerequisite"
    macos_check_checksum "$prerequisite"
  done
  reuse_prerequisites=1
fi
if (( reuse_prerequisites == 0 )); then
  image_refs_json="{"
  for image_name in db backend frontend gateway; do
    [[ "$image_refs_json" == "{" ]] || image_refs_json+="," 
    image_refs_json+="\"$image_name\":\"$(macos_json_get "$release_path/ops/release/built-image-identity.json" "images.$image_name.id")\""
  done
  image_refs_json+="}"
  macos_write_atomic "$MACOS_LAYOUT_STATE/cutover-image-references.json" "$image_refs_json"
  macos_write_checksum "$MACOS_LAYOUT_STATE/cutover-image-references.json"
  base_refs_json="$(plutil -extract baseImageReferences json -o - -- "$release_path/release-manifest.json")"
  macos_write_atomic "$MACOS_LAYOUT_STATE/cutover-base-image-references.json" "$base_refs_json"
  macos_write_checksum "$MACOS_LAYOUT_STATE/cutover-base-image-references.json"
  checksums_json="{"
  while IFS= read -r checksum_line || [[ -n "$checksum_line" ]]; do
    [[ "$checksum_line" =~ '^([0-9a-fA-F]{64})[[:space:]][[:space:]](.+)$' ]] || macos_die "release checksum row is invalid"
    [[ "$checksums_json" == "{" ]] || checksums_json+="," 
    checksums_json+="\"$(macos_json_escape "${match[2]}")\":\"${match[1]:l}\""
  done < "$release_path/SHA256SUMS"
  checksums_json+="}"
  macos_write_atomic "$MACOS_LAYOUT_STATE/cutover-release-checksums.json" "$checksums_json"
  macos_write_checksum "$MACOS_LAYOUT_STATE/cutover-release-checksums.json"
  macos_write_atomic "$stop_proof_path" "{\"schemaVersion\":1,\"wholeProjectStopped\":true,\"project\":\"$MACOS_FORMAL_PROJECT\",\"observedAt\":\"$(macos_now_iso)\",\"runningServices\":[],\"method\":\"compose-stop-and-ps\"}"
  macos_checksummed_json "$stop_proof_path"
  macos_backend_one_shot_with_mounts "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" \
    --volume "$MACOS_LAYOUT_STATE:/cutover-state" \
    release-metadata \
    --application-version "$(macos_json_get "$release_path/release-manifest.json" applicationVersion)" \
    --git-commit "${release_commit:l}" --host-os darwin --architecture arm64 \
    --target-platform linux/arm64 --migration-head "$(macos_json_get "$release_path/release-manifest.json" migrationHead)" \
    --image-references /cutover-state/cutover-image-references.json \
    --base-image-references /cutover-state/cutover-base-image-references.json \
    --release-file-checksums /cutover-state/cutover-release-checksums.json \
    --output "/cutover-state/${release_metadata_path:t}"
  [[ -f "$release_metadata_path" && -f "$release_metadata_path.sha256" ]] || macos_die "canonical release metadata was not written"
  chmod 600 "$release_metadata_path" "$release_metadata_path.sha256"
  macos_check_checksum "$release_metadata_path"
fi

macos_backend_one_shot_with_mounts "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" \
  --volume "$backup_path:/portable-backup:ro" \
  --volume "$MACOS_LAYOUT_STATE:/cutover-state" \
  prepare-cutover --backup /portable-backup \
  --target-host-id "$target_host" \
  --release-metadata "/cutover-state/${release_metadata_path:t}" \
  --source-stop-proof "/cutover-state/${stop_proof_path:t}" \
  --source-project "$MACOS_FORMAL_PROJECT" \
  --target-project "$MACOS_FORMAL_PROJECT" \
  --source-gateway-stopped --in-progress-attempts 0 \
  --state-path "/cutover-state/${prepared_state:t}"

[[ -f "$prepared_state" && -f "$prepared_state.sha256" ]] || macos_die "canonical prepared cutover state was not written"
chmod 600 "$prepared_state" "$prepared_state.sha256"
macos_secure_path "$prepared_state"
macos_secure_path "$prepared_state.sha256"
macos_check_checksum "$prepared_state"
[[ "$(macos_json_get "$prepared_state" state)" == prepared ]] || macos_die "canonical cutover state is not prepared"
[[ "$(macos_json_get "$prepared_state" source_project)" == "$MACOS_FORMAL_PROJECT" ]] || macos_die "canonical cutover source project is not formal"
[[ "$(macos_json_get "$prepared_state" target_project)" == "$MACOS_FORMAL_PROJECT" ]] || macos_die "canonical cutover target project is not formal"
case "$(macos_json_get "$prepared_state" source_gateway_stopped)" in
  1|true) ;;
  *) macos_die "canonical cutover state does not prove source stopped" ;;
esac
prepare_phase_update prepared "$backup_path"
prepare_status=passed
macos_log "host_cutover_prepared target=$(macos_json_get "$prepared_state" target_host_id) dataset=$(macos_json_get "$prepared_state" dataset_id) writer_generation=$(macos_json_get "$prepared_state" writer_generation) state=${prepared_state:t}"
