#!/bin/zsh
# Reserve and activate the first macOS formal writer (generation 1).
#
# Prepare is a reservation only.  It binds an installed sealed ARM64 release,
# immutable dataset/host identity, and fresh named volumes without starting,
# restoring, or deleting a formal service.  Staging is deliberately performed
# after this reservation so its acceptance can bind the pending host identity.
# Activate validates every supplied evidence artifact, persists a durable
# phase journal, and owns the fresh generation-1 database boundary under an
# exact writer fence.  Any incomplete phase remains private and resumable.

set -euo pipefail
umask 077

SCRIPT_DIR="${0:A:h}"
source "$SCRIPT_DIR/Common.zsh"

action=""
root="${INTERNAL_EXAM_ROOT:-${HOME:?}/Library/Application Support/InternalExam}"
release_arg=""
staging_arg=""
paired_backup_arg=""
preflight_arg=""
restore_drill_arg=""
browser_arg=""
pf_evidence_arg=""
network_time_evidence_arg=""
docker_settings_evidence_arg=""
confirmation=""
empty_dataset=0
seed_input=""

while (( $# > 0 )); do
  case "$1" in
    Prepare|prepare) [[ -z "$action" ]] || macos_die "an action was supplied more than once"; action=prepare; shift ;;
    Activate|activate) [[ -z "$action" ]] || macos_die "an action was supplied more than once"; action=activate; shift ;;
    Status|status) [[ -z "$action" ]] || macos_die "an action was supplied more than once"; action=status; shift ;;
    --action) (( $# >= 2 )) || macos_die "--action requires Prepare, Activate, or Status"; action="${2:l}"; shift 2 ;;
    --root) (( $# >= 2 )) || macos_die "--root requires a path"; root="$2"; shift 2 ;;
    --release-path|--release) (( $# >= 2 )) || macos_die "$1 requires an installed release path"; release_arg="$2"; shift 2 ;;
    --staging-evidence|--staging-acceptance) (( $# >= 2 )) || macos_die "$1 requires a checksummed staging acceptance"; staging_arg="$2"; shift 2 ;;
    --paired-backup-path|--paired-backup|--backup) (( $# >= 2 )) || macos_die "$1 requires a paired backup directory"; paired_backup_arg="$2"; shift 2 ;;
    --preflight-evidence|--preflight) (( $# >= 2 )) || macos_die "$1 requires checksummed maintenance preflight evidence"; preflight_arg="$2"; shift 2 ;;
    --restore-drill-evidence|--restore-drill) (( $# >= 2 )) || macos_die "$1 requires checksummed restore-drill evidence"; restore_drill_arg="$2"; shift 2 ;;
    --browser-smoke-evidence|--browser-evidence) (( $# >= 2 )) || macos_die "$1 requires checksummed browser evidence"; browser_arg="$2"; shift 2 ;;
    --pf-evidence) (( $# >= 2 )) || macos_die "--pf-evidence requires checksummed PF evidence"; pf_evidence_arg="$2"; shift 2 ;;
    --network-time-evidence) (( $# >= 2 )) || macos_die "--network-time-evidence requires checksummed network-time evidence"; network_time_evidence_arg="$2"; shift 2 ;;
    --docker-settings-evidence) (( $# >= 2 )) || macos_die "--docker-settings-evidence requires checksummed Docker settings evidence"; docker_settings_evidence_arg="$2"; shift 2 ;;
    --confirmation) (( $# >= 2 )) || macos_die "--confirmation requires exact text"; confirmation="$2"; shift 2 ;;
    --empty-dataset) empty_dataset=1; shift ;;
    --seed|--seed-input|--seed-path|--dataset-seed) (( $# >= 2 )) || macos_die "$1 requires a seed input"; seed_input="$2"; shift 2 ;;
    -h|--help)
      print -r -- "usage: $0 --action Prepare|Activate|Status [--root ABSOLUTE_ROOT] [--release-path INSTALLED_RELEASE] [--staging-evidence CHECKSUMMED_ACCEPTANCE] [--empty-dataset] [--paired-backup-path BACKUP] [--preflight-evidence PREFLIGHT] [--restore-drill-evidence DRILL] [--browser-smoke-evidence BROWSER] [--pf-evidence PF] [--network-time-evidence NETWORK_TIME] [--docker-settings-evidence DOCKER_SETTINGS] [--confirmation 'ACTIVATE FORMAL WRITER VERSION']"
      print -r -- "Prepare reserves an empty dataset only; staging is run afterwards and Activate owns generation-1 under an exact writer fence before public Start."
      exit 0
      ;;
    *) macos_die "unknown argument: $1"; exit 1 ;;
  esac
done

[[ "$action" == prepare || "$action" == activate || "$action" == status ]] || macos_die "--action must be Prepare, Activate, or Status"
[[ -z "$seed_input" ]] || macos_die "seed inputs are not supported; only explicit --empty-dataset commissioning is allowed"
if [[ "$action" == prepare ]]; then
  (( empty_dataset == 1 )) || macos_die "Prepare requires explicit --empty-dataset"
fi

macos_assert_macos
macos_assert_outside_worktree "$root" >/dev/null
if [[ "$action" == prepare ]]; then
  macos_initialize_layout "$root"
else
  macos_layout "$root"
fi
macos_assert_protected_configuration "$root"

intent_path="$(macos_formal_writer_bootstrap_intent_path)"
activation_intent_path="$(macos_formal_writer_activation_intent_path)"
activation_terminal_path="$(macos_formal_writer_activation_terminal_path)"
lineage_path="$(macos_formal_writer_lineage_path)"
phase_path="$MACOS_LAYOUT_STATE/formal-writer-activation-phase.json"
volume_override="$MACOS_LAYOUT_STATE/formal-volume-override.yml"
identity_path="$MACOS_LAYOUT_STATE/host-identity.json"

bootstrap_validate_formal_paths() {
  local lifecycle backup evidence second_copy value
  lifecycle="$(macos_formal_value INTERNAL_EXAM_LIFECYCLE_HOST_DIR)"
  backup="$(macos_formal_value INTERNAL_EXAM_BACKUP_HOST_DIR)"
  evidence="$(macos_formal_value INTERNAL_EXAM_EVIDENCE_HOST_DIR)"
  second_copy="$(macos_formal_value SECOND_COPY_PATH)"
  [[ "$lifecycle" == "$MACOS_LAYOUT_LIFECYCLE" ]] || macos_die "formal lifecycle path must be canonical before writer commissioning"
  [[ "$backup" == "$MACOS_LAYOUT_BACKUPS" ]] || macos_die "formal backup path must be canonical before writer commissioning"
  [[ "$evidence" == "$MACOS_LAYOUT_EVIDENCE" ]] || macos_die "formal evidence path must be canonical before writer commissioning"
  for value in "$lifecycle" "$backup" "$evidence" "$second_copy"; do
    [[ "$value" == /* ]] || macos_die "formal host paths must be absolute before writer commissioning"
    macos_assert_outside_worktree "$value" >/dev/null
  done
  [[ "$second_copy" != "$MACOS_LAYOUT_ROOT" && "$second_copy" != "$MACOS_LAYOUT_ROOT"/* ]] || macos_die "second-copy storage must be outside the fresh formal root"
  [[ "$second_copy" != "$lifecycle" && "$second_copy" != "$backup" && "$second_copy" != "$evidence" ]] || macos_die "formal host paths must be distinct"
  typeset -g BOOTSTRAP_LIFECYCLE_PATH="$lifecycle"
  typeset -g BOOTSTRAP_BACKUP_ROOT="$backup"
  typeset -g BOOTSTRAP_EVIDENCE_ROOT="$evidence"
  typeset -g BOOTSTRAP_SECOND_COPY_ROOT="$second_copy"
}

bootstrap_assert_fresh_state() {
  local path artifact
  if [[ ! -e "$intent_path" && ! -e "$intent_path.sha256" ]]; then
    for path in "$MACOS_CURRENT_STATE" "$MACOS_PREVIOUS_STATE" "$identity_path" "$lineage_path" "$volume_override" "$volume_override.sha256"; do
      [[ ! -e "$path" ]] || macos_die "fresh writer root already contains prior state: ${path:t}"
    done
  else
    [[ -f "$intent_path" ]] || macos_die "bootstrap intent sidecar exists without canonical intent"
    [[ ! -e "$MACOS_PREVIOUS_STATE" ]] || macos_die "fresh writer root contains a previous release state"
  fi
  for artifact in "$MACOS_LAYOUT_STATE"/cutover-*.json(N) "$MACOS_LAYOUT_STATE"/cutover-*.yml(N) "$MACOS_LAYOUT_STATE"/rollback-*.json(N) "$MACOS_LAYOUT_STATE"/source-cutback-*.json(N) "$MACOS_LAYOUT_STATE"/formal-writer-activation-*.json(N) "$MACOS_LAYOUT_STATE"/formal-writer-activation-*.json.sha256(N) "$lineage_path" "$lineage_path.sha256"; do
    [[ ! -e "$artifact" ]] || macos_die "fresh writer root contains an unrelated lifecycle artifact: ${artifact:t}"
  done
}

bootstrap_resolve_release() {
  local manifest release_commit release_version
  if [[ -n "$release_arg" ]]; then
    release_path="$(macos_resolve_path "$release_arg")"
  else
    release_path="$(macos_json_get "$intent_path" releasePath 2>/dev/null || true)"
    [[ -n "$release_path" ]] || macos_die "--release-path is required for the first Prepare"
    release_path="$(macos_resolve_path "$release_path")"
  fi
  [[ "$release_path" == "$MACOS_LAYOUT_RELEASES"/* && -d "$release_path" && ! -L "$release_path" ]] || macos_die "writer release must be an installed non-link release under the protected release directory"
  "$SCRIPT_DIR/Test-ReleaseBundle.zsh" --release-path "$release_path" >/dev/null
  macos_verify_built_image_identity "$release_path"
  manifest="$release_path/release-manifest.json"
  release_commit="$(macos_json_get "$manifest" gitCommit)"
  release_version="$(macos_json_get "$manifest" applicationVersion)"
  [[ "$(macos_json_get "$manifest" hostOS 2>/dev/null || true)" == darwin && "$(macos_json_get "$manifest" architecture 2>/dev/null || true)" == arm64 ]] || macos_die "writer release must be sealed for a Darwin ARM64 host"
  typeset -g BOOTSTRAP_RELEASE_PATH="$release_path"
  typeset -g BOOTSTRAP_RELEASE_VERSION="$release_version"
  typeset -g BOOTSTRAP_RELEASE_COMMIT="${release_commit:l}"
  typeset -g BOOTSTRAP_RELEASE_MANIFEST_SHA256="$(macos_sha256 "$manifest")"
  typeset -g BOOTSTRAP_RELEASE_CHECKSUMS_SHA256="$(macos_sha256 "$release_path/SHA256SUMS")"
  typeset -g BOOTSTRAP_IMAGE_IDENTITY_SHA256="$(macos_sha256 "$release_path/ops/release/built-image-identity.json")"
}

bootstrap_validate_intent() {
  local expected_release="$1" dataset_id host_id generation
  [[ -f "$intent_path" ]] || macos_die "bootstrap intent is missing"
  plutil -convert json -o - -- "$intent_path" >/dev/null 2>&1 || macos_die "bootstrap intent JSON is invalid"
  [[ ! -f "$intent_path.sha256" ]] || { macos_secure_path "$intent_path"; macos_check_checksum "$intent_path"; }
  [[ "$(macos_json_get "$intent_path" kind 2>/dev/null || true)" == formal-writer-bootstrap-intent && "$(macos_json_get "$intent_path" status 2>/dev/null || true)" == prepared ]] || macos_die "bootstrap intent kind or phase is invalid"
  [[ "$(macos_json_get "$intent_path" emptyDataset 2>/dev/null || true)" == true && "$(macos_json_get "$intent_path" maintenanceOnly 2>/dev/null || true)" == true && "$(macos_json_get "$intent_path" maintenanceBindIp 2>/dev/null || true)" == 127.0.0.1 ]] || macos_die "bootstrap intent is not an empty loopback-only reservation"
  dataset_id="$(macos_json_get "$intent_path" datasetId 2>/dev/null || true)"
  host_id="$(macos_json_get "$intent_path" hostId 2>/dev/null || true)"
  generation="$(macos_json_get "$intent_path" writerGeneration 2>/dev/null || true)"
  [[ "$dataset_id" =~ '^dataset-[0-9a-f]{32}$' && "$host_id" =~ '^host-[a-z0-9._-]+-[0-9a-f]{8}$' && "$generation" == 1 ]] || macos_die "bootstrap intent identity or generation is invalid"
  [[ "$(macos_json_get "$intent_path" releasePath 2>/dev/null || true)" == "$expected_release" ]] || macos_die "bootstrap intent release path changed; exact rerun is required"
  [[ "$(macos_json_get "$intent_path" releaseManifestSha256 2>/dev/null || true)" == "$BOOTSTRAP_RELEASE_MANIFEST_SHA256" && "$(macos_json_get "$intent_path" releaseChecksumsSha256 2>/dev/null || true)" == "$BOOTSTRAP_RELEASE_CHECKSUMS_SHA256" && "$(macos_json_get "$intent_path" builtImageIdentitySha256 2>/dev/null || true)" == "$BOOTSTRAP_IMAGE_IDENTITY_SHA256" ]] || macos_die "bootstrap intent release digest changed"
  [[ "$(macos_json_get "$intent_path" lifecyclePath 2>/dev/null || true)" == "$BOOTSTRAP_LIFECYCLE_PATH" && "$(macos_json_get "$intent_path" backupPath 2>/dev/null || true)" == "$BOOTSTRAP_BACKUP_ROOT" && "$(macos_json_get "$intent_path" evidencePath 2>/dev/null || true)" == "$BOOTSTRAP_EVIDENCE_ROOT" && "$(macos_json_get "$intent_path" secondCopyPath 2>/dev/null || true)" == "$BOOTSTRAP_SECOND_COPY_ROOT" ]] || macos_die "bootstrap intent formal host paths changed"
  [[ "$(macos_json_get "$intent_path" volumeOverridePath 2>/dev/null || true)" == "$volume_override" ]] || macos_die "bootstrap intent volume override path changed"
  [[ "$(macos_json_get "$intent_path" volumeOverrideSha256 2>/dev/null || true)" =~ '^[0-9a-f]{64}$' ]] || macos_die "bootstrap intent volume override digest is invalid"
  [[ -z "$(macos_json_get "$intent_path" seedInputs 2>/dev/null || true)" || "$(macos_json_get "$intent_path" seedInputs 2>/dev/null || true)" == null ]] || macos_die "bootstrap intent contains an unsupported seed input"
  typeset -g BOOTSTRAP_DATASET_ID="$dataset_id"
  typeset -g BOOTSTRAP_HOST_ID="$host_id"
  typeset -g BOOTSTRAP_WRITER_GENERATION="$generation"
  typeset -g BOOTSTRAP_POSTGRES_VOLUME="$(macos_json_get "$intent_path" postgresVolume)"
  typeset -g BOOTSTRAP_MEDIA_VOLUME="$(macos_json_get "$intent_path" mediaVolume)"
  typeset -g BOOTSTRAP_WORKER_VOLUME="$(macos_json_get "$intent_path" workerVolume)"
  [[ "$BOOTSTRAP_POSTGRES_VOLUME" =~ '^internal-exam-formal-bootstrap-[0-9a-f]{32}-postgres$' && "$BOOTSTRAP_MEDIA_VOLUME" =~ '^internal-exam-formal-bootstrap-[0-9a-f]{32}-media$' && "$BOOTSTRAP_WORKER_VOLUME" =~ '^internal-exam-formal-bootstrap-[0-9a-f]{32}-worker$' ]] || macos_die "bootstrap intent volume identity is invalid"
}

bootstrap_validate_current_shape() {
  local pending current_dataset current_host current_generation current_release activation_digest
  [[ -f "$MACOS_CURRENT_STATE" ]] || macos_die "formal writer current state is missing"
  plutil -convert json -o - -- "$MACOS_CURRENT_STATE" >/dev/null 2>&1 || macos_die "formal writer current state JSON is invalid"
  current_dataset="$(macos_json_get "$MACOS_CURRENT_STATE" datasetId 2>/dev/null || true)"
  current_host="$(macos_json_get "$MACOS_CURRENT_STATE" hostId 2>/dev/null || true)"
  current_generation="$(macos_json_get "$MACOS_CURRENT_STATE" writerGeneration 2>/dev/null || true)"
  current_release="$(macos_json_get "$MACOS_CURRENT_STATE" path 2>/dev/null || true)"
  pending="$(macos_json_get "$MACOS_CURRENT_STATE" bootstrapPending 2>/dev/null || true)"
  [[ "$current_dataset" == "$BOOTSTRAP_DATASET_ID" && "$current_host" == "$BOOTSTRAP_HOST_ID" && "$current_generation" == 1 && "$current_release" == "$BOOTSTRAP_RELEASE_PATH" ]] || macos_die "formal writer current state is not bound to the exact generation-1 reservation"
  [[ "$pending" == true || "$pending" == false ]] || macos_die "formal writer current state bootstrapPending value is invalid"
  if [[ -f "$activation_intent_path" ]]; then
    activation_digest="$(macos_sha256 "$activation_intent_path")"
    [[ "$(macos_json_get "$MACOS_CURRENT_STATE" activationIntentSha256 2>/dev/null || true)" == "$activation_digest" || -z "$(macos_json_get "$MACOS_CURRENT_STATE" activationIntentSha256 2>/dev/null || true)" ]] || macos_die "formal writer current state activation intent binding changed"
  fi
}

bootstrap_repair_derived_sidecars() {
  local identity_path_local="$identity_path" identity_lineage identity_dataset identity_host identity_generation identity_pending
  local current_needs=0 identity_needs=0
  if [[ ! -f "$intent_path.sha256" ]]; then
    macos_checksummed_json "$intent_path"
  else
    macos_check_checksum "$intent_path"
  fi
  if [[ -f "$identity_path_local" ]]; then
    if ! macos_check_checksum "$identity_path_local" >/dev/null 2>&1; then identity_needs=1; fi
    plutil -convert json -o - -- "$identity_path_local" >/dev/null 2>&1 || macos_die "host identity JSON is invalid; sidecar recovery is refused"
    identity_dataset="$(macos_json_get "$identity_path_local" datasetId 2>/dev/null || true)"
    identity_host="$(macos_json_get "$identity_path_local" hostId 2>/dev/null || true)"
    identity_generation="$(macos_json_get "$identity_path_local" writerGeneration 2>/dev/null || true)"
    identity_lineage="$(macos_json_get "$identity_path_local" lineageState 2>/dev/null || true)"
    identity_pending="$(macos_json_get "$identity_path_local" bootstrapPending 2>/dev/null || true)"
    [[ "$identity_dataset" == "$BOOTSTRAP_DATASET_ID" && "$identity_host" == "$BOOTSTRAP_HOST_ID" && "$identity_generation" == 1 && ( "$identity_lineage" == bootstrap-pending || "$identity_lineage" == bound ) ]] || macos_die "host identity is not bound to the exact reservation; sidecar recovery is refused"
    if [[ "$identity_lineage" == bootstrap-pending ]]; then
      [[ "$identity_pending" == true && "$(macos_json_get "$identity_path_local" bootstrapIntentSha256 2>/dev/null || true)" == "$(macos_sha256 "$intent_path")" ]] || macos_die "pending host identity binding is invalid; sidecar recovery is refused"
    fi
    (( identity_needs == 1 )) && macos_write_checksum "$identity_path_local"
  fi
  if [[ -f "$MACOS_CURRENT_STATE" ]]; then
    if ! macos_check_checksum "$MACOS_CURRENT_STATE" >/dev/null 2>&1; then current_needs=1; fi
    # A terminal means commissioning already completed; current-release may
    # now point at a later promoted/rolled-back release.  Defer its exact
    # public-ready identity validation to bootstrap_validate_terminal_semantics
    # below instead of applying the initial generation-1 path shape here.
    if [[ ! -f "$activation_terminal_path" ]]; then
      bootstrap_validate_current_shape
    else
      plutil -convert json -o - -- "$MACOS_CURRENT_STATE" >/dev/null 2>&1 || macos_die "current release state JSON is invalid; sidecar recovery was refused"
    fi
    (( current_needs == 1 )) && macos_write_checksum "$MACOS_CURRENT_STATE"
  fi
}

bootstrap_validate_volume_override() {
  local expected_digest="$(macos_json_get "$intent_path" volumeOverrideSha256)" actual pg media worker
  [[ -f "$volume_override" ]] || macos_die "bootstrap volume override is missing"
  pg="$(awk '/^[[:space:]]+postgres_data:[[:space:]]*$/ { in_pg=1; next } in_pg && /^[[:space:]]+name:[[:space:]]*/ { print $2; exit }' "$volume_override")"
  media="$(awk '/^[[:space:]]+learning_media:[[:space:]]*$/ { in_media=1; next } in_media && /^[[:space:]]+name:[[:space:]]*/ { print $2; exit }' "$volume_override")"
  worker="$(awk '/^[[:space:]]+worker_state:[[:space:]]*$/ { in_worker=1; next } in_worker && /^[[:space:]]+name:[[:space:]]*/ { print $2; exit }' "$volume_override")"
  [[ "$pg" == "$BOOTSTRAP_POSTGRES_VOLUME" && "$media" == "$BOOTSTRAP_MEDIA_VOLUME" && "$worker" == "$BOOTSTRAP_WORKER_VOLUME" ]] || macos_die "bootstrap volume override names are not bound to the exact intent"
  actual="$(macos_sha256 "$volume_override")"
  [[ "$actual" == "$expected_digest" ]] || macos_die "bootstrap volume override changed after intent preparation"
  [[ ! -f "$volume_override.sha256" ]] || { macos_secure_path "$volume_override"; macos_check_checksum "$volume_override"; }
}

bootstrap_write_derived_state() {
  local digest="$(macos_sha256 "$intent_path")" release_json identity_json current_json path
  release_json="$(macos_json_escape "$BOOTSTRAP_RELEASE_PATH")"
  identity_json="{\"schemaVersion\":1,\"kind\":\"formal-writer-identity\",\"datasetId\":\"$BOOTSTRAP_DATASET_ID\",\"hostId\":\"$BOOTSTRAP_HOST_ID\",\"writerGeneration\":1,\"lineageState\":\"bootstrap-pending\",\"bootstrapPending\":true,\"bootstrapIntentSha256\":\"$digest\"}"
  current_json="{\"schemaVersion\":1,\"kind\":\"formal-writer-current\",\"applicationVersion\":\"$(macos_json_escape "$BOOTSTRAP_RELEASE_VERSION")\",\"gitCommit\":\"$BOOTSTRAP_RELEASE_COMMIT\",\"path\":\"$release_json\",\"datasetId\":\"$BOOTSTRAP_DATASET_ID\",\"hostId\":\"$BOOTSTRAP_HOST_ID\",\"writerGeneration\":1,\"bootstrapPending\":true,\"bootstrapIntentSha256\":\"$digest\"}"
  for path in "$identity_path" "$MACOS_CURRENT_STATE"; do
    if [[ -f "$path" ]]; then
      plutil -convert json -o - -- "$path" >/dev/null 2>&1 || macos_die "derived writer state is invalid"
      [[ "$(macos_json_get "$path" datasetId 2>/dev/null || true)" == "$BOOTSTRAP_DATASET_ID" && "$(macos_json_get "$path" hostId 2>/dev/null || true)" == "$BOOTSTRAP_HOST_ID" && "$(macos_json_get "$path" writerGeneration 2>/dev/null || true)" == 1 && "$(macos_json_get "$path" bootstrapPending 2>/dev/null || true)" == true && "$(macos_json_get "$path" bootstrapIntentSha256 2>/dev/null || true)" == "$digest" ]] || macos_die "derived writer state changed outside the exact bootstrap intent"
      [[ -f "$path.sha256" ]] || macos_write_checksum "$path"
      [[ -f "$path.sha256" ]] && macos_check_checksum "$path"
    elif [[ "$path" == "$identity_path" ]]; then
      macos_write_atomic "$path" "$identity_json"
      macos_write_checksum "$path"
    else
      macos_write_atomic "$path" "$current_json"
      macos_write_checksum "$path"
    fi
  done
}

bootstrap_write_prepare() {
  local content temporary volume_digest intent_json
  if [[ -e "$intent_path" || -e "$intent_path.sha256" ]]; then
    [[ -f "$intent_path" ]] || macos_die "bootstrap intent sidecar exists without canonical intent"
    bootstrap_validate_intent "$BOOTSTRAP_RELEASE_PATH"
    [[ -f "$intent_path.sha256" ]] || macos_write_checksum "$intent_path"
  else
    macos_require_command openssl
    dataset_id="dataset-$(openssl rand -hex 16)"
    host_name="$(scutil --get LocalHostName 2>/dev/null || hostname -s 2>/dev/null || print -r -- macos-host)"
    host_name="${host_name:l}"
    host_name="${host_name//[^a-z0-9._-]/-}"
    [[ -n "$host_name" ]] || host_name=macos-host
    host_id="host-$host_name-$(openssl rand -hex 4)"
    postgres_volume="internal-exam-formal-bootstrap-${dataset_id#dataset-}-postgres"
    media_volume="internal-exam-formal-bootstrap-${dataset_id#dataset-}-media"
    worker_volume="internal-exam-formal-bootstrap-${dataset_id#dataset-}-worker"
    content=$'volumes:\n  postgres_data:\n    name: '
    content+="$postgres_volume"
    content+=$'\n  learning_media:\n    name: '
    content+="$media_volume"
    content+=$'\n  worker_state:\n    name: '
    content+="$worker_volume"
    temporary="$(macos_mktemp internal-exam-formal-volume.XXXXXX)"
    print -r -- "$content" > "$temporary"
    volume_digest="$(macos_sha256 "$temporary")"
    rm -f -- "$temporary"
    intent_json="{\"schemaVersion\":1,\"kind\":\"formal-writer-bootstrap-intent\",\"status\":\"prepared\",\"emptyDataset\":true,\"maintenanceOnly\":true,\"maintenanceBindIp\":\"127.0.0.1\",\"datasetId\":\"$dataset_id\",\"hostId\":\"$host_id\",\"writerGeneration\":1,\"releasePath\":\"$(macos_json_escape "$BOOTSTRAP_RELEASE_PATH")\",\"releaseVersion\":\"$(macos_json_escape "$BOOTSTRAP_RELEASE_VERSION")\",\"releaseCommit\":\"$BOOTSTRAP_RELEASE_COMMIT\",\"releaseManifestSha256\":\"$BOOTSTRAP_RELEASE_MANIFEST_SHA256\",\"releaseChecksumsSha256\":\"$BOOTSTRAP_RELEASE_CHECKSUMS_SHA256\",\"builtImageIdentitySha256\":\"$BOOTSTRAP_IMAGE_IDENTITY_SHA256\",\"stagingAcceptancePath\":null,\"stagingAcceptanceSha256\":null,\"lifecyclePath\":\"$(macos_json_escape "$BOOTSTRAP_LIFECYCLE_PATH")\",\"backupPath\":\"$(macos_json_escape "$BOOTSTRAP_BACKUP_ROOT")\",\"evidencePath\":\"$(macos_json_escape "$BOOTSTRAP_EVIDENCE_ROOT")\",\"secondCopyPath\":\"$(macos_json_escape "$BOOTSTRAP_SECOND_COPY_ROOT")\",\"volumeOverridePath\":\"$(macos_json_escape "$volume_override")\",\"volumeOverrideSha256\":\"$volume_digest\",\"postgresVolume\":\"$postgres_volume\",\"mediaVolume\":\"$media_volume\",\"workerVolume\":\"$worker_volume\",\"seedInputs\":null,\"createdAt\":\"$(macos_now_iso)\",\"approval\":\"manual-required\"}"
    macos_write_atomic "$intent_path" "$intent_json"
    macos_checksummed_json "$intent_path"
    BOOTSTRAP_DATASET_ID="$dataset_id"
    BOOTSTRAP_HOST_ID="$host_id"
    BOOTSTRAP_WRITER_GENERATION=1
    BOOTSTRAP_POSTGRES_VOLUME="$postgres_volume"
    BOOTSTRAP_MEDIA_VOLUME="$media_volume"
    BOOTSTRAP_WORKER_VOLUME="$worker_volume"
  fi
  bootstrap_validate_intent "$BOOTSTRAP_RELEASE_PATH"
  if [[ -f "$volume_override" ]]; then
    bootstrap_validate_volume_override
    [[ -f "$volume_override.sha256" ]] || macos_write_checksum "$volume_override"
  else
    content=$'volumes:\n  postgres_data:\n    name: '
    content+="$BOOTSTRAP_POSTGRES_VOLUME"
    content+=$'\n  learning_media:\n    name: '
    content+="$BOOTSTRAP_MEDIA_VOLUME"
    content+=$'\n  worker_state:\n    name: '
    content+="$BOOTSTRAP_WORKER_VOLUME"
    macos_write_atomic "$volume_override" "$content"
    macos_write_checksum "$volume_override"
    bootstrap_validate_volume_override
  fi
  bootstrap_write_derived_state
}

bootstrap_validate_staging() {
  local path="$1" commit checked_at relative_path validation_output
  [[ -n "$path" ]] || macos_die "--staging-evidence is required for Activate"
  path="$(macos_resolve_path "$path")"
  [[ "$path" == "$MACOS_LAYOUT_ROOT"/* && -f "$path" && ! -L "$path" ]] || macos_die "staging acceptance must be a canonical artifact inside the protected formal root"
  macos_secure_path "$path"
  macos_check_checksum "$path"
  plutil -convert json -o - -- "$path" >/dev/null 2>&1 || macos_die "staging acceptance evidence is invalid"
  # Schema-2 canonical evidence owns the raw run bundle and its relative
  # references.  Revalidate it inside the selected sealed backend image so a
  # copied top-level gates object or a stale artifact cannot satisfy Activate.
  relative_path="/protected/${path#$MACOS_LAYOUT_ROOT/}"
  backend_image="$(macos_json_get "$BOOTSTRAP_RELEASE_PATH/release-manifest.json" imageDigests.backend 2>/dev/null || true)"
  [[ -n "$backend_image" ]] || macos_die "sealed release backend image identity is missing"
  validation_output="$(macos_run_capture docker run --rm --platform linux/arm64 --volume "$MACOS_LAYOUT_ROOT:/protected:ro" "$backend_image" uv run --no-sync python -m app.ops.staging_acceptance validate --root /protected --release "/protected/releases/${BOOTSTRAP_RELEASE_PATH:t}" --canonical "$relative_path")"
  [[ "$validation_output" == *'"status": "passed"'* || "$validation_output" == *'"status":"passed"'* ]] || macos_die "schema-2 staging acceptance validator did not pass"
  commit="$(macos_json_get "$path" commit 2>/dev/null || macos_json_get "$path" gitCommit 2>/dev/null || true)"
  checked_at="$(macos_json_get "$path" checkedAt 2>/dev/null || macos_json_get "$path" checked_at 2>/dev/null || true)"
  [[ "$(macos_json_get "$path" schemaVersion 2>/dev/null || true)" == 2 && "$(macos_json_get "$path" kind 2>/dev/null || true)" == staging-acceptance && "$(macos_json_get "$path" status 2>/dev/null || true)" == passed && "${commit:l}" == "$BOOTSTRAP_RELEASE_COMMIT" && "$(macos_json_get "$path" hostOS 2>/dev/null || true)" == darwin && "$(macos_json_get "$path" architecture 2>/dev/null || true)" == arm64 && "$(macos_json_get "$path" platform 2>/dev/null || true)" == linux/arm64 ]] || macos_die "staging acceptance is not a passed schema-2 ARM64 acceptance for this release"
  [[ "$(macos_json_get "$path" hostId 2>/dev/null || true)" == "$BOOTSTRAP_HOST_ID" ]] || macos_die "staging acceptance hostId does not match the pending writer"
  macos_assert_fresh_timestamp "$checked_at"
  [[ "$(macos_json_get "$path" builtImageIdentitySha256 2>/dev/null || true)" == "$BOOTSTRAP_IMAGE_IDENTITY_SHA256" ]] || macos_die "staging acceptance image identity is stale"
  for gate in browser smtp capacity restart route security; do
    [[ "$(macos_json_get "$path" "gates.$gate" 2>/dev/null || true)" == passed ]] || macos_die "staging acceptance gate is missing or failed: $gate"
  done
  typeset -g BOOTSTRAP_STAGING_PATH="$path"
  typeset -g BOOTSTRAP_STAGING_SHA256="$(macos_sha256 "$path")"
}

bootstrap_validate_activation_evidence() {
  local preflight_path checked_at
  bootstrap_validate_staging "$staging_arg"
  [[ -n "$browser_arg" ]] || macos_die "Activate requires browser evidence"
  bootstrap_validate_browser_evidence "$browser_arg"
  [[ -z "$preflight_arg" ]] || preflight_path="$(macos_resolve_path "$preflight_arg")"
  [[ -z "$preflight_arg" || "$preflight_path" == "$MACOS_LAYOUT_ROOT"/* ]] || macos_die "activation evidence must remain in the protected formal root"
  if [[ -n "$preflight_arg" ]]; then
    [[ -f "$preflight_path" && -f "$preflight_path.sha256" ]] || macos_die "maintenance preflight evidence is incomplete"
    macos_secure_path "$preflight_path"
    macos_check_checksum "$preflight_path"
    plutil -convert json -o - -- "$preflight_path" >/dev/null 2>&1 || macos_die "maintenance preflight evidence JSON is invalid"
    [[ "$(macos_json_get "$preflight_path" kind 2>/dev/null || true)" == formal-preflight && "$(macos_json_get "$preflight_path" status 2>/dev/null || true)" == passed && "$(macos_json_get "$preflight_path" targetMaintenance 2>/dev/null || true)" == true && "$(macos_json_get "$preflight_path" commit 2>/dev/null || true)" == "$BOOTSTRAP_RELEASE_COMMIT" && "$(macos_json_get "$preflight_path" hostId 2>/dev/null || true)" == "$BOOTSTRAP_HOST_ID" ]] || macos_die "maintenance preflight evidence is not bound to the pending writer"
    checked_at="$(macos_json_get "$preflight_path" checkedAt 2>/dev/null || macos_json_get "$preflight_path" checked_at 2>/dev/null || true)"
    macos_assert_fresh_timestamp "$checked_at"
    typeset -g BOOTSTRAP_PREFLIGHT_PATH="$preflight_path"
  fi
}

bootstrap_validate_backup() {
  local backup_path="$1" backup_manifest second_copy_evidence second_copy_root backend_image expected actual artifact
  backup_path="$(macos_assert_backup "$backup_path")"
  [[ "$backup_path" == "$MACOS_LAYOUT_BACKUPS"/backup-* && "$backup_path" != "$MACOS_LAYOUT_BACKUPS"/*/* ]] || macos_die "activation paired backup must be a direct canonical backup child"
  [[ "${backup_path:t}" =~ '^backup-[0-9]{8}T[0-9]{6}Z$' ]] || macos_die "activation paired backup identity is invalid"
  for artifact in SUCCESS SHA256SUMS manifest.json database.dump learning_media.tar.gz; do
    [[ -f "$backup_path/$artifact" && ! -L "$backup_path/$artifact" ]] || macos_die "activation paired backup is missing required artifact: $artifact"
    macos_secure_path "$backup_path/$artifact"
  done
  [[ "$(find "$backup_path" -mindepth 1 -maxdepth 1 -print | wc -l | tr -d '[:space:]')" == 5 ]] || macos_die "activation paired backup contains extra or missing artifacts"
  [[ "$(cat "$backup_path/SUCCESS")" == "ok" ]] || macos_die "activation paired backup SUCCESS marker is invalid"
  for artifact in database.dump learning_media.tar.gz manifest.json; do
    expected="$(awk -v name="$artifact" '$2 == name { print $1; count += 1 } END { if (count != 1) exit 1 }' "$backup_path/SHA256SUMS" 2>/dev/null || true)"
    [[ "$expected" =~ '^[0-9a-fA-F]{64}$' ]] || macos_die "activation paired backup checksum row is missing: $artifact"
    actual="$(macos_sha256 "$backup_path/$artifact")"
    [[ "$actual" == "$expected" ]] || macos_die "activation paired backup checksum mismatch: $artifact"
  done
  backend_image="$(macos_json_get "$BOOTSTRAP_RELEASE_PATH/release-manifest.json" imageDigests.backend 2>/dev/null || true)"
  [[ -n "$backend_image" ]] || macos_die "sealed release backend image identity is missing"
  macos_run_checked docker run --rm --platform linux/arm64 --volume "$backup_path:/portable-backup:ro" "$backend_image" uv run --no-sync python -m app.ops.host_portability validate-migration-input /portable-backup
  backup_manifest="$backup_path/manifest.json"
  [[ -f "$backup_manifest" ]] || macos_die "activation paired backup manifest is missing"
  plutil -convert json -o - -- "$backup_manifest" >/dev/null 2>&1 || macos_die "activation paired backup manifest is invalid"
  [[ "$(macos_json_get "$backup_manifest" backup_kind 2>/dev/null || true)" == cutover && "$(macos_json_get "$backup_manifest" dataset_id 2>/dev/null || true)" == "$BOOTSTRAP_DATASET_ID" && "$(macos_json_get "$backup_manifest" source_host_id 2>/dev/null || true)" == "$BOOTSTRAP_HOST_ID" && "$(macos_json_get "$backup_manifest" writer_generation 2>/dev/null || true)" == 1 ]] || macos_die "activation paired backup is not an exact generation-1 writer backup"
  [[ "$(macos_json_get "$backup_manifest" writer_fence_boundary.dataset_id 2>/dev/null || true)" == "$BOOTSTRAP_DATASET_ID" && "$(macos_json_get "$backup_manifest" writer_fence_boundary.source_host_id 2>/dev/null || true)" == "$BOOTSTRAP_HOST_ID" && "$(macos_json_get "$backup_manifest" writer_fence_boundary.writer_generation 2>/dev/null || true)" == 1 ]] || macos_die "activation backup does not prove the exact writer-fence boundary"
  second_copy_root="$(macos_formal_value SECOND_COPY_PATH)"
  macos_assert_second_copy_storage "$second_copy_root"
  second_copy_evidence="$backup_path:h/${backup_path:t}.second-copy.json"
  [[ -f "$second_copy_evidence" && -f "$second_copy_evidence.sha256" ]] || macos_die "activation paired backup lacks exact second-copy evidence"
  macos_check_checksum "$second_copy_evidence"
  [[ "$(macos_json_get "$second_copy_evidence" status 2>/dev/null || true)" == passed && "$(macos_json_get "$second_copy_evidence" artifact_id 2>/dev/null || true)" == "${backup_path:t}" ]] || macos_die "activation second-copy evidence is not bound to the exact backup"
  typeset -g BOOTSTRAP_BACKUP_PATH="$backup_path"
  typeset -g BOOTSTRAP_BACKUP_MANIFEST="$backup_manifest"
  typeset -g BOOTSTRAP_SECOND_COPY_EVIDENCE="$second_copy_evidence"
}

bootstrap_validate_restore_drill() {
  local restore_path="$1" checked_at
  restore_path="$(macos_resolve_path "$restore_path")"
  [[ "$restore_path" == "$MACOS_LAYOUT_ROOT"/* && -f "$restore_path" && -f "$restore_path.sha256" ]] || macos_die "restore-drill evidence must remain a checksummed artifact in the protected formal root"
  macos_check_checksum "$restore_path"
  checked_at="$(macos_json_get "$restore_path" checkedAt 2>/dev/null || true)"
  [[ "$(macos_json_get "$restore_path" kind 2>/dev/null || true)" == second-copy-restore-drill && "$(macos_json_get "$restore_path" status 2>/dev/null || true)" == passed && "$(macos_json_get "$restore_path" backupId 2>/dev/null || true)" == "${BOOTSTRAP_BACKUP_PATH:t}" && "$(macos_json_get "$restore_path" formalProjectChanged 2>/dev/null || true)" == false && "$(macos_json_get "$restore_path" hostId 2>/dev/null || true)" == "$BOOTSTRAP_HOST_ID" && "$(macos_json_get "$restore_path" hostOS 2>/dev/null || true)" == darwin && "$(macos_json_get "$restore_path" architecture 2>/dev/null || true)" == arm64 && "$(macos_json_get "$restore_path" releaseCommit 2>/dev/null || true)" == "$BOOTSTRAP_RELEASE_COMMIT" && "$(macos_json_get "$restore_path" releaseVersion 2>/dev/null || true)" == "$BOOTSTRAP_RELEASE_VERSION" && "$(macos_json_get "$restore_path" datasetId 2>/dev/null || true)" == "$BOOTSTRAP_DATASET_ID" && "$(macos_json_get "$restore_path" writerGeneration 2>/dev/null || true)" == 1 && "$(macos_json_get "$restore_path" sourceBackupManifestSha256 2>/dev/null || true)" == "$(macos_sha256 "$BOOTSTRAP_BACKUP_MANIFEST")" ]] || macos_die "restore-drill evidence is not bound to the exact paired backup, host, or release"
  macos_assert_fresh_timestamp "$checked_at"
  typeset -g BOOTSTRAP_RESTORE_DRILL_PATH="$restore_path"
}

bootstrap_phase_write() {
  local phase="$1" json
  json="{\"schemaVersion\":1,\"kind\":\"formal-writer-activation-phase\",\"phase\":\"$phase\",\"activationIntentSha256\":\"$(macos_sha256 "$activation_intent_path")\",\"bootstrapIntentSha256\":\"$(macos_sha256 "$intent_path")\",\"datasetId\":\"$BOOTSTRAP_DATASET_ID\",\"hostId\":\"$BOOTSTRAP_HOST_ID\",\"writerGeneration\":1,\"releasePath\":\"$(macos_json_escape "$BOOTSTRAP_RELEASE_PATH")\",\"releaseManifestSha256\":\"$BOOTSTRAP_RELEASE_MANIFEST_SHA256\",\"stagingAcceptancePath\":\"$(macos_json_escape "$BOOTSTRAP_STAGING_PATH")\",\"stagingAcceptanceSha256\":\"$BOOTSTRAP_STAGING_SHA256\",\"browserEvidencePath\":\"$(macos_json_escape "${BOOTSTRAP_BROWSER_PATH:-}")\",\"browserEvidenceSha256\":\"$(macos_sha256 "${BOOTSTRAP_BROWSER_PATH:-/dev/null}")\",\"confirmation\":\"$(macos_json_escape "$confirmation")\",\"updatedAt\":\"$(macos_now_iso)\"}"
  [[ -z "${BOOTSTRAP_BACKUP_PATH:-}" ]] || json="${json%\}} ,\"pairedBackupPath\":\"$(macos_json_escape "$BOOTSTRAP_BACKUP_PATH")\",\"pairedBackupManifestSha256\":\"$(macos_sha256 "$BOOTSTRAP_BACKUP_MANIFEST")\",\"secondCopyEvidencePath\":\"$(macos_json_escape "$BOOTSTRAP_SECOND_COPY_EVIDENCE")\",\"secondCopyEvidenceSha256\":\"$(macos_sha256 "$BOOTSTRAP_SECOND_COPY_EVIDENCE")\"}"
  [[ -z "${BOOTSTRAP_RESTORE_DRILL_PATH:-}" ]] || json="${json%\}} ,\"restoreDrillPath\":\"$(macos_json_escape "$BOOTSTRAP_RESTORE_DRILL_PATH")\",\"restoreDrillSha256\":\"$(macos_sha256 "$BOOTSTRAP_RESTORE_DRILL_PATH")\"}"
  [[ -z "${BOOTSTRAP_PREFLIGHT_PATH:-}" ]] || json="${json%\}} ,\"preflightPath\":\"$(macos_json_escape "$BOOTSTRAP_PREFLIGHT_PATH")\",\"preflightSha256\":\"$(macos_sha256 "$BOOTSTRAP_PREFLIGHT_PATH")\"}"
  macos_write_atomic "$phase_path" "$json"
  macos_checksummed_json "$phase_path"
}

bootstrap_phase_read() {
  [[ -f "$phase_path" && -f "$phase_path.sha256" ]] || return 1
  macos_check_checksum "$phase_path"
  [[ "$(macos_json_get "$phase_path" kind 2>/dev/null || true)" == formal-writer-activation-phase ]] || macos_die "activation phase journal kind is invalid"
  case "$(macos_json_get "$phase_path" phase 2>/dev/null || true)" in
    intent|maintenance-started|fence-acquired|backup-passed|restore-passed|preflight-passed|state-bound|fence-released|terminal) ;;
    *) macos_die "activation phase journal phase is invalid" ;;
  esac
  [[ "$(macos_json_get "$phase_path" activationIntentSha256 2>/dev/null || true)" == "$(macos_sha256 "$activation_intent_path")" && "$(macos_json_get "$phase_path" bootstrapIntentSha256 2>/dev/null || true)" == "$(macos_sha256 "$intent_path")" && "$(macos_json_get "$phase_path" datasetId 2>/dev/null || true)" == "$BOOTSTRAP_DATASET_ID" && "$(macos_json_get "$phase_path" hostId 2>/dev/null || true)" == "$BOOTSTRAP_HOST_ID" && "$(macos_json_get "$phase_path" releasePath 2>/dev/null || true)" == "$BOOTSTRAP_RELEASE_PATH" && "$(macos_json_get "$phase_path" releaseManifestSha256 2>/dev/null || true)" == "$BOOTSTRAP_RELEASE_MANIFEST_SHA256" ]] || macos_die "activation phase journal identity changed"
  return 0
}

bootstrap_repair_phase_sidecar() {
  local phase_value phase_staging phase_staging_sha phase_browser phase_browser_sha phase_backup phase_backup_manifest_sha
  local phase_second_copy phase_second_copy_sha phase_restore phase_restore_sha phase_preflight phase_preflight_sha
  [[ -f "$phase_path" ]] || macos_die "activation phase journal is missing; manual recovery is required"
  plutil -convert json -o - -- "$phase_path" >/dev/null 2>&1 || macos_die "activation phase journal JSON is invalid; manual recovery is required"
  [[ "$(macos_json_get "$phase_path" kind 2>/dev/null || true)" == formal-writer-activation-phase ]] || macos_die "activation phase journal kind is invalid; sidecar recovery is refused"
  phase_value="$(macos_json_get "$phase_path" phase 2>/dev/null || true)"
  case "$phase_value" in
    intent|maintenance-started|fence-acquired|backup-passed|restore-passed|preflight-passed|state-bound|fence-released|terminal) ;;
    *) macos_die "activation phase journal phase is invalid; sidecar recovery is refused" ;;
  esac
  [[ "$(macos_json_get "$phase_path" activationIntentSha256 2>/dev/null || true)" == "$(macos_sha256 "$activation_intent_path")" && "$(macos_json_get "$phase_path" bootstrapIntentSha256 2>/dev/null || true)" == "$(macos_sha256 "$intent_path")" && "$(macos_json_get "$phase_path" datasetId 2>/dev/null || true)" == "$BOOTSTRAP_DATASET_ID" && "$(macos_json_get "$phase_path" hostId 2>/dev/null || true)" == "$BOOTSTRAP_HOST_ID" && "$(macos_json_get "$phase_path" releasePath 2>/dev/null || true)" == "$BOOTSTRAP_RELEASE_PATH" && "$(macos_json_get "$phase_path" releaseManifestSha256 2>/dev/null || true)" == "$BOOTSTRAP_RELEASE_MANIFEST_SHA256" ]] || macos_die "activation phase journal binding changed; sidecar recovery is refused"
  phase_staging="$(macos_json_get "$phase_path" stagingAcceptancePath 2>/dev/null || true)"
  phase_staging_sha="$(macos_json_get "$phase_path" stagingAcceptanceSha256 2>/dev/null || true)"
  phase_browser="$(macos_json_get "$phase_path" browserEvidencePath 2>/dev/null || true)"
  phase_browser_sha="$(macos_json_get "$phase_path" browserEvidenceSha256 2>/dev/null || true)"
  [[ "$phase_staging" == "$MACOS_LAYOUT_ROOT"/* && "$phase_browser" == "$MACOS_LAYOUT_ROOT"/* && -f "$phase_staging" && "$(macos_sha256 "$phase_staging")" == "$phase_staging_sha" && -f "$phase_browser" && "$(macos_sha256 "$phase_browser")" == "$phase_browser_sha" ]] || macos_die "activation phase evidence binding is incomplete; sidecar recovery is refused"
  phase_backup="$(macos_json_get "$phase_path" pairedBackupPath 2>/dev/null || true)"
  phase_backup_manifest_sha="$(macos_json_get "$phase_path" pairedBackupManifestSha256 2>/dev/null || true)"
  phase_second_copy="$(macos_json_get "$phase_path" secondCopyEvidencePath 2>/dev/null || true)"
  phase_second_copy_sha="$(macos_json_get "$phase_path" secondCopyEvidenceSha256 2>/dev/null || true)"
  if [[ -n "$phase_backup" ]]; then
    [[ "$phase_backup" == "$MACOS_LAYOUT_BACKUPS"/* && "$phase_second_copy" == "$MACOS_LAYOUT_BACKUPS"/* && -f "$phase_backup/manifest.json" && "$(macos_sha256 "$phase_backup/manifest.json")" == "$phase_backup_manifest_sha" && -f "$phase_second_copy" && "$(macos_sha256 "$phase_second_copy")" == "$phase_second_copy_sha" ]] || macos_die "activation phase backup binding is incomplete; sidecar recovery is refused"
  fi
  phase_restore="$(macos_json_get "$phase_path" restoreDrillPath 2>/dev/null || true)"
  phase_restore_sha="$(macos_json_get "$phase_path" restoreDrillSha256 2>/dev/null || true)"
  [[ -z "$phase_restore" || ( "$phase_restore" == "$MACOS_LAYOUT_ROOT"/* && -f "$phase_restore" && "$(macos_sha256 "$phase_restore")" == "$phase_restore_sha" ) ]] || macos_die "activation phase restore binding is incomplete; sidecar recovery is refused"
  phase_preflight="$(macos_json_get "$phase_path" preflightPath 2>/dev/null || true)"
  phase_preflight_sha="$(macos_json_get "$phase_path" preflightSha256 2>/dev/null || true)"
  [[ -z "$phase_preflight" || ( "$phase_preflight" == "$MACOS_LAYOUT_ROOT"/* && -f "$phase_preflight" && "$(macos_sha256 "$phase_preflight")" == "$phase_preflight_sha" ) ]] || macos_die "activation phase preflight binding is incomplete; sidecar recovery is refused"
  macos_write_checksum "$phase_path"
}

bootstrap_validate_browser_evidence() {
  local browser_input="$1" browser_path checked_at browser_kind browser_scope browser_status
  local browser_host browser_generation browser_candidate_url browser_operator_url browser_url
  local browser_commit browser_commit_alias browser_version browser_version_alias browser_host_os browser_architecture
  local browser_health browser_page browser_console browser_pageerror browser_offline_static
  local browser_staging_e2e browser_mobile_uat
  [[ "$browser_input" == /* && ! -L "$browser_input" ]] || macos_die "browser evidence path must be an absolute non-symlink path"
  browser_path="$(macos_resolve_path "$browser_input")"
  [[ "$browser_path" == "$MACOS_LAYOUT_ROOT"/* && -f "$browser_path" && ! -L "$browser_path" ]] || macos_die "browser evidence must be a canonical artifact inside the protected formal root"
  macos_secure_path "$browser_path"
  macos_check_checksum "$browser_path"
  plutil -convert json -o - -- "$browser_path" >/dev/null 2>&1 || macos_die "browser evidence JSON is invalid"
  # Validate the exact Capture-FormalBrowserSmokeEvidence schema.  Do not
  # accept legacy aliases or a candidate URL with a path: Activate binds this
  # artifact to the private target-maintenance endpoints only.
  browser_kind="$(macos_json_get "$browser_path" kind 2>/dev/null || true)"
  browser_scope="$(macos_json_get "$browser_path" scope 2>/dev/null || true)"
  browser_status="$(macos_json_get "$browser_path" status 2>/dev/null || true)"
  [[ "$browser_kind" == browser-smoke && "$browser_scope" == browser-smoke && "$browser_status" == passed ]] || macos_die "browser evidence schema or status is invalid"

  browser_host="$(macos_json_get "$browser_path" hostId 2>/dev/null || true)"
  browser_generation="$(macos_json_get "$browser_path" writerGeneration 2>/dev/null || true)"
  [[ "$browser_host" == "$BOOTSTRAP_HOST_ID" && "$browser_generation" == 1 ]] || macos_die "browser evidence host identity is not bound to pending generation 1"

  browser_candidate_url="$(macos_json_get "$browser_path" candidateUrl 2>/dev/null || true)"
  browser_operator_url="$(macos_json_get "$browser_path" operatorUrl 2>/dev/null || true)"
  browser_url="$(macos_json_get "$browser_path" url 2>/dev/null || true)"
  [[ "$browser_candidate_url" == http://127.0.0.1:28080 && "$browser_url" == http://127.0.0.1:28080 && "$browser_operator_url" == http://127.0.0.1:28081 ]] || macos_die "browser evidence URLs are not the exact loopback target-maintenance endpoints"

  browser_commit="$(macos_json_get "$browser_path" gitCommit 2>/dev/null || true)"
  browser_commit_alias="$(macos_json_get "$browser_path" commit 2>/dev/null || true)"
  browser_version="$(macos_json_get "$browser_path" applicationVersion 2>/dev/null || true)"
  browser_version_alias="$(macos_json_get "$browser_path" version 2>/dev/null || true)"
  browser_host_os="$(macos_json_get "$browser_path" hostOS 2>/dev/null || true)"
  browser_architecture="$(macos_json_get "$browser_path" architecture 2>/dev/null || true)"
  [[ "$browser_commit" == "$BOOTSTRAP_RELEASE_COMMIT" && "$browser_commit_alias" == "$BOOTSTRAP_RELEASE_COMMIT" && "$browser_version" == "$BOOTSTRAP_RELEASE_VERSION" && "$browser_version_alias" == "$BOOTSTRAP_RELEASE_VERSION" && "$browser_host_os" == darwin && "$browser_architecture" == arm64 ]] || macos_die "browser evidence release identity is not the exact Darwin ARM64 sealed release"

  browser_health="$(macos_json_get "$browser_path" 'checks.health' 2>/dev/null || true)"
  browser_page="$(macos_json_get "$browser_path" 'checks.page' 2>/dev/null || true)"
  browser_console="$(macos_json_get "$browser_path" 'checks.console' 2>/dev/null || true)"
  browser_pageerror="$(macos_json_get "$browser_path" 'checks.pageerror' 2>/dev/null || true)"
  browser_offline_static="$(macos_json_get "$browser_path" 'checks.offlineStaticResources' 2>/dev/null || true)"
  [[ "$browser_health" == passed && "$browser_page" == passed && "$browser_console" == passed && "$browser_pageerror" == passed && "$browser_offline_static" == passed ]] || macos_die "browser evidence checks are incomplete or failed"

  browser_staging_e2e="$(macos_json_get "$browser_path" stagingE2e 2>/dev/null || true)"
  browser_mobile_uat="$(macos_json_get "$browser_path" mobileUat 2>/dev/null || true)"
  [[ "$browser_staging_e2e" == not-run && "$browser_mobile_uat" == not-run ]] || macos_die "browser evidence scope must mark staging E2E and mobile UAT not-run"

  checked_at="$(macos_json_get "$browser_path" checkedAt 2>/dev/null || true)"
  macos_assert_fresh_timestamp "$checked_at"
  typeset -g BOOTSTRAP_BROWSER_PATH="$browser_path"
  typeset -g BOOTSTRAP_BROWSER_SHA256="$(macos_sha256 "$browser_path")"
}

bootstrap_load_phase_artifacts() {
  local phase_staging phase_staging_sha phase_browser phase_browser_sha phase_backup phase_backup_manifest_sha
  local phase_second_copy phase_second_copy_sha phase_restore phase_restore_sha phase_preflight phase_preflight_sha
  phase_staging="$(macos_json_get "$phase_path" stagingAcceptancePath 2>/dev/null || true)"
  phase_staging_sha="$(macos_json_get "$phase_path" stagingAcceptanceSha256 2>/dev/null || true)"
  phase_browser="$(macos_json_get "$phase_path" browserEvidencePath 2>/dev/null || true)"
  phase_browser_sha="$(macos_json_get "$phase_path" browserEvidenceSha256 2>/dev/null || true)"
  [[ -n "$phase_staging" && "$phase_staging" == "$MACOS_LAYOUT_ROOT"/* && -n "$phase_staging_sha" ]] || macos_die "activation phase lacks an exact staging acceptance binding"
  [[ "$(macos_sha256 "$phase_staging")" == "$phase_staging_sha" ]] || macos_die "activation phase staging acceptance digest changed"
  [[ -n "$phase_browser" && "$phase_browser" == "$MACOS_LAYOUT_ROOT"/* && -n "$phase_browser_sha" ]] || macos_die "activation phase lacks an exact browser evidence binding"
  [[ "$(macos_sha256 "$phase_browser")" == "$phase_browser_sha" ]] || macos_die "activation phase browser evidence digest changed"
  staging_arg="$phase_staging"
  browser_arg="$phase_browser"
  preflight_arg="$(macos_json_get "$phase_path" preflightPath 2>/dev/null || true)"
  bootstrap_validate_activation_evidence
  [[ "$BOOTSTRAP_STAGING_SHA256" == "$phase_staging_sha" && "$BOOTSTRAP_BROWSER_SHA256" == "$phase_browser_sha" ]] || macos_die "activation phase evidence validation is not exact"
  phase_backup="$(macos_json_get "$phase_path" pairedBackupPath 2>/dev/null || true)"
  phase_backup_manifest_sha="$(macos_json_get "$phase_path" pairedBackupManifestSha256 2>/dev/null || true)"
  phase_second_copy="$(macos_json_get "$phase_path" secondCopyEvidencePath 2>/dev/null || true)"
  phase_second_copy_sha="$(macos_json_get "$phase_path" secondCopyEvidenceSha256 2>/dev/null || true)"
  if [[ -n "$phase_backup" ]]; then
    bootstrap_validate_backup "$phase_backup"
    [[ "$(macos_sha256 "$BOOTSTRAP_BACKUP_MANIFEST")" == "$phase_backup_manifest_sha" && "$(macos_sha256 "$BOOTSTRAP_SECOND_COPY_EVIDENCE")" == "$phase_second_copy_sha" && "$BOOTSTRAP_SECOND_COPY_EVIDENCE" == "$phase_second_copy" ]] || macos_die "activation phase backup binding changed"
  fi
  phase_restore="$(macos_json_get "$phase_path" restoreDrillPath 2>/dev/null || true)"
  phase_restore_sha="$(macos_json_get "$phase_path" restoreDrillSha256 2>/dev/null || true)"
  if [[ -n "$phase_restore" ]]; then
    [[ -n "${BOOTSTRAP_BACKUP_PATH:-}" ]] || macos_die "activation phase restore drill has no paired backup"
    bootstrap_validate_restore_drill "$phase_restore"
    [[ "$(macos_sha256 "$BOOTSTRAP_RESTORE_DRILL_PATH")" == "$phase_restore_sha" ]] || macos_die "activation phase restore-drill binding changed"
  fi
  phase_preflight="$(macos_json_get "$phase_path" preflightPath 2>/dev/null || true)"
  phase_preflight_sha="$(macos_json_get "$phase_path" preflightSha256 2>/dev/null || true)"
  if [[ -n "$phase_preflight" ]]; then
    [[ -n "${BOOTSTRAP_PREFLIGHT_PATH:-}" && "$BOOTSTRAP_PREFLIGHT_PATH" == "$phase_preflight" && "$(macos_sha256 "$BOOTSTRAP_PREFLIGHT_PATH")" == "$phase_preflight_sha" ]] || macos_die "activation phase preflight binding changed"
  fi
}

bootstrap_load_terminal_artifacts() {
  typeset -g BOOTSTRAP_STAGING_PATH="$(macos_json_get "$activation_intent_path" stagingAcceptancePath 2>/dev/null || true)"
  typeset -g BOOTSTRAP_STAGING_SHA256="$(macos_json_get "$activation_intent_path" stagingAcceptanceSha256 2>/dev/null || true)"
  typeset -g BOOTSTRAP_BROWSER_PATH="$(macos_json_get "$activation_intent_path" browserEvidencePath 2>/dev/null || true)"
  typeset -g BOOTSTRAP_BROWSER_SHA256="$(macos_json_get "$activation_intent_path" browserEvidenceSha256 2>/dev/null || true)"
  typeset -g BOOTSTRAP_BACKUP_PATH="$(macos_json_get "$activation_terminal_path" pairedBackupPath 2>/dev/null || true)"
  typeset -g BOOTSTRAP_PREFLIGHT_PATH="$(macos_json_get "$activation_terminal_path" preflightPath 2>/dev/null || true)"
  typeset -g BOOTSTRAP_RESTORE_DRILL_PATH="$(macos_json_get "$activation_terminal_path" restoreDrillPath 2>/dev/null || true)"
  [[ -n "$BOOTSTRAP_STAGING_PATH" && -n "$BOOTSTRAP_BACKUP_PATH" && -n "$BOOTSTRAP_PREFLIGHT_PATH" && -n "$BOOTSTRAP_RESTORE_DRILL_PATH" ]] || macos_die "activation terminal artifact references are incomplete"
}

bootstrap_validate_terminal_semantics() {
  local terminal_phase_sha terminal_current_sha terminal_intent_sha identity_dataset identity_host identity_generation identity_lineage current_dataset current_host current_generation
  [[ -f "$activation_terminal_path" ]] || macos_die "activation terminal is missing"
  plutil -convert json -o - -- "$activation_terminal_path" >/dev/null 2>&1 || macos_die "activation terminal JSON is invalid"
  [[ "$(macos_json_get "$activation_terminal_path" kind 2>/dev/null || true)" == formal-writer-activation-terminal && "$(macos_json_get "$activation_terminal_path" status 2>/dev/null || true)" == passed && "$(macos_json_get "$activation_terminal_path" datasetId 2>/dev/null || true)" == "$BOOTSTRAP_DATASET_ID" && "$(macos_json_get "$activation_terminal_path" hostId 2>/dev/null || true)" == "$BOOTSTRAP_HOST_ID" && "$(macos_json_get "$activation_terminal_path" writerGeneration 2>/dev/null || true)" == 1 && "$(macos_json_get "$activation_terminal_path" releasePath 2>/dev/null || true)" == "$BOOTSTRAP_RELEASE_PATH" && "$(macos_json_get "$activation_terminal_path" stagingAcceptancePath 2>/dev/null || true)" == "$BOOTSTRAP_STAGING_PATH" && "$(macos_json_get "$activation_terminal_path" pairedBackupPath 2>/dev/null || true)" == "$BOOTSTRAP_BACKUP_PATH" && "$(macos_json_get "$activation_terminal_path" preflightPath 2>/dev/null || true)" == "$BOOTSTRAP_PREFLIGHT_PATH" && "$(macos_json_get "$activation_terminal_path" restoreDrillPath 2>/dev/null || true)" == "$BOOTSTRAP_RESTORE_DRILL_PATH" && "$(macos_json_get "$activation_terminal_path" targetExposed 2>/dev/null || true)" == false && "$(macos_json_get "$activation_terminal_path" targetWriteAccepted 2>/dev/null || true)" == false ]] || macos_die "activation terminal semantic binding is invalid"
  terminal_intent_sha="$(macos_json_get "$activation_terminal_path" activationIntentSha256 2>/dev/null || true)"
  terminal_phase_sha="$(macos_json_get "$activation_terminal_path" phaseSha256 2>/dev/null || true)"
  terminal_current_sha="$(macos_json_get "$activation_terminal_path" currentStateSha256 2>/dev/null || true)"
  [[ "$terminal_intent_sha" == "$(macos_sha256 "$activation_intent_path")" && "$terminal_phase_sha" == "$(macos_sha256 "$phase_path")" && "$terminal_current_sha" =~ '^[0-9a-fA-F]{64}$' ]] || macos_die "activation terminal digest binding is stale"
  [[ "$(macos_json_get "$MACOS_CURRENT_STATE" bootstrapPending 2>/dev/null || true)" == false && "$(macos_json_get "$MACOS_CURRENT_STATE" activationReady 2>/dev/null || true)" == true ]] || macos_die "activation terminal current state is not public-ready"
  [[ -f "$identity_path" ]] || macos_die "activation terminal host identity is missing"
  macos_check_checksum "$identity_path"
  identity_dataset="$(macos_json_get "$identity_path" datasetId 2>/dev/null || true)"
  identity_host="$(macos_json_get "$identity_path" hostId 2>/dev/null || true)"
  identity_generation="$(macos_json_get "$identity_path" writerGeneration 2>/dev/null || true)"
  identity_lineage="$(macos_json_get "$identity_path" lineageState 2>/dev/null || true)"
  [[ "$identity_dataset" == "$BOOTSTRAP_DATASET_ID" && "$identity_host" == "$BOOTSTRAP_HOST_ID" && "$identity_generation" =~ '^[1-9][0-9]*$' && "$identity_lineage" == bound ]] || macos_die "activation terminal host identity binding is invalid"
  current_dataset="$(macos_json_get "$MACOS_CURRENT_STATE" datasetId 2>/dev/null || true)"
  current_host="$(macos_json_get "$MACOS_CURRENT_STATE" hostId 2>/dev/null || true)"
  current_generation="$(macos_json_get "$MACOS_CURRENT_STATE" writerGeneration 2>/dev/null || true)"
  [[ "$current_dataset" == "$identity_dataset" && "$current_host" == "$identity_host" && "$current_generation" == "$identity_generation" ]] || macos_die "activation terminal current state identity is invalid"
}

bootstrap_repair_terminal_sidecar() {
  bootstrap_validate_terminal_semantics
  if [[ ! -f "$activation_terminal_path.sha256" ]] || ! macos_check_checksum "$activation_terminal_path" >/dev/null 2>&1; then
    macos_write_checksum "$activation_terminal_path"
  fi
  bootstrap_write_lineage
}

bootstrap_write_lineage() {
  local terminal_sha activation_sha phase_sha bootstrap_sha current_sha release_path_value lineage_json
  [[ -f "$activation_terminal_path" && -f "$activation_intent_path" && -f "$phase_path" && -f "$intent_path" && -f "$MACOS_CURRENT_STATE" ]] || macos_die "activation lineage inputs are incomplete"
  macos_check_checksum "$activation_terminal_path"
  macos_check_checksum "$activation_intent_path"
  macos_check_checksum "$phase_path"
  macos_check_checksum "$intent_path"
  macos_check_checksum "$MACOS_CURRENT_STATE"
  terminal_sha="$(macos_sha256 "$activation_terminal_path")"
  activation_sha="$(macos_sha256 "$activation_intent_path")"
  phase_sha="$(macos_sha256 "$phase_path")"
  bootstrap_sha="$(macos_sha256 "$intent_path")"
  current_sha="$(macos_json_get "$activation_terminal_path" currentStateSha256 2>/dev/null || true)"
  release_path_value="$(macos_json_get "$activation_terminal_path" releasePath 2>/dev/null || true)"
  [[ "$current_sha" =~ '^[0-9a-fA-F]{64}$' && "$release_path_value" == "$BOOTSTRAP_RELEASE_PATH" ]] || macos_die "activation terminal initial release binding is invalid"
  if [[ -e "$lineage_path" || -e "$lineage_path.sha256" ]]; then
    [[ -f "$lineage_path" ]] || macos_die "formal writer lineage canonical record is missing"
    plutil -convert json -o - -- "$lineage_path" >/dev/null 2>&1 || macos_die "formal writer lineage JSON is invalid"
    if [[ -f "$lineage_path.sha256" ]]; then
      macos_check_checksum "$lineage_path"
    fi
    [[ "$(macos_json_get "$lineage_path" kind 2>/dev/null || true)" == formal-writer-lineage && "$(macos_json_get "$lineage_path" status 2>/dev/null || true)" == commissioned && "$(macos_json_get "$lineage_path" datasetId 2>/dev/null || true)" == "$BOOTSTRAP_DATASET_ID" && "$(macos_json_get "$lineage_path" hostId 2>/dev/null || true)" == "$BOOTSTRAP_HOST_ID" && "$(macos_json_get "$lineage_path" writerGeneration 2>/dev/null || true)" == 1 && "$(macos_json_get "$lineage_path" bootstrapIntentSha256 2>/dev/null || true)" == "$bootstrap_sha" && "$(macos_json_get "$lineage_path" activationIntentSha256 2>/dev/null || true)" == "$activation_sha" && "$(macos_json_get "$lineage_path" activationPhaseSha256 2>/dev/null || true)" == "$phase_sha" && "$(macos_json_get "$lineage_path" activationTerminalSha256 2>/dev/null || true)" == "$terminal_sha" && "$(macos_json_get "$lineage_path" initialCurrentStateSha256 2>/dev/null || true)" == "$current_sha" && "$(macos_json_get "$lineage_path" initialReleasePath 2>/dev/null || true)" == "$release_path_value" ]] || macos_die "formal writer lineage sidecar binding changed"
    [[ -f "$lineage_path.sha256" ]] || macos_write_checksum "$lineage_path"
    return 0
  fi
  lineage_json="{\"schemaVersion\":1,\"kind\":\"formal-writer-lineage\",\"status\":\"commissioned\",\"datasetId\":\"$BOOTSTRAP_DATASET_ID\",\"hostId\":\"$BOOTSTRAP_HOST_ID\",\"writerGeneration\":1,\"bootstrapIntentSha256\":\"$bootstrap_sha\",\"activationIntentSha256\":\"$activation_sha\",\"activationPhaseSha256\":\"$phase_sha\",\"activationTerminalSha256\":\"$terminal_sha\",\"initialCurrentStateSha256\":\"$current_sha\",\"initialReleasePath\":\"$(macos_json_escape "$release_path_value")\",\"initialReleaseVersion\":\"$(macos_json_escape "$BOOTSTRAP_RELEASE_VERSION")\",\"initialReleaseCommit\":\"$BOOTSTRAP_RELEASE_COMMIT\",\"commissionedAt\":\"$(macos_now_iso)\",\"approval\":\"manual-required\"}"
  macos_write_atomic "$lineage_path" "$lineage_json"
  macos_checksummed_json "$lineage_path"
}

bootstrap_write_activation_intent() {
  local expected="ACTIVATE FORMAL WRITER $BOOTSTRAP_RELEASE_VERSION"
  [[ "$confirmation" == "$expected" ]] || macos_die "exact activation confirmation did not match"
  if [[ -e "$activation_intent_path" || -e "$activation_intent_path.sha256" ]]; then
    [[ -f "$activation_intent_path" ]] || macos_die "activation intent is incomplete; manual recovery is required"
    if [[ -f "$activation_intent_path.sha256" ]]; then
      macos_check_checksum "$activation_intent_path"
    fi
    [[ "$(macos_json_get "$activation_intent_path" kind 2>/dev/null || true)" == formal-writer-activation-intent && "$(macos_json_get "$activation_intent_path" status 2>/dev/null || true)" == intent && "$(macos_json_get "$activation_intent_path" datasetId 2>/dev/null || true)" == "$BOOTSTRAP_DATASET_ID" && "$(macos_json_get "$activation_intent_path" hostId 2>/dev/null || true)" == "$BOOTSTRAP_HOST_ID" && "$(macos_json_get "$activation_intent_path" releasePath 2>/dev/null || true)" == "$BOOTSTRAP_RELEASE_PATH" && "$(macos_json_get "$activation_intent_path" stagingAcceptancePath 2>/dev/null || true)" == "$BOOTSTRAP_STAGING_PATH" && "$(macos_json_get "$activation_intent_path" confirmation 2>/dev/null || true)" == "$confirmation" ]] || macos_die "activation intent does not match the exact reservation"
    [[ "$(macos_json_get "$activation_intent_path" lifecyclePath 2>/dev/null || true)" == "$BOOTSTRAP_LIFECYCLE_PATH" && "$(macos_json_get "$activation_intent_path" backupPath 2>/dev/null || true)" == "$BOOTSTRAP_BACKUP_ROOT" && "$(macos_json_get "$activation_intent_path" evidencePath 2>/dev/null || true)" == "$BOOTSTRAP_EVIDENCE_ROOT" && "$(macos_json_get "$activation_intent_path" secondCopyPath 2>/dev/null || true)" == "$BOOTSTRAP_SECOND_COPY_ROOT" ]] || macos_die "activation intent formal host paths changed"
    [[ "$(macos_json_get "$activation_intent_path" browserEvidencePath 2>/dev/null || true)" == "$BOOTSTRAP_BROWSER_PATH" && "$(macos_json_get "$activation_intent_path" browserEvidenceSha256 2>/dev/null || true)" == "$BOOTSTRAP_BROWSER_SHA256" ]] || macos_die "activation intent browser evidence binding changed"
    [[ -f "$activation_intent_path.sha256" ]] || macos_checksummed_json "$activation_intent_path"
    return 0
  fi
  intent_json="{\"schemaVersion\":1,\"kind\":\"formal-writer-activation-intent\",\"status\":\"intent\",\"datasetId\":\"$BOOTSTRAP_DATASET_ID\",\"hostId\":\"$BOOTSTRAP_HOST_ID\",\"writerGeneration\":1,\"bootstrapIntentSha256\":\"$(macos_sha256 "$intent_path")\",\"releasePath\":\"$(macos_json_escape "$BOOTSTRAP_RELEASE_PATH")\",\"releaseManifestSha256\":\"$BOOTSTRAP_RELEASE_MANIFEST_SHA256\",\"stagingAcceptancePath\":\"$(macos_json_escape "$BOOTSTRAP_STAGING_PATH")\",\"stagingAcceptanceSha256\":\"$BOOTSTRAP_STAGING_SHA256\",\"volumeOverrideSha256\":\"$(macos_sha256 "$volume_override")\",\"confirmation\":\"$(macos_json_escape "$confirmation")\",\"maintenanceLoopback\":true,\"targetExposed\":false,\"targetWriteAccepted\":false,\"ownershipChange\":\"blocked\",\"createdAt\":\"$(macos_now_iso)\",\"approval\":\"manual-required\"}"
  intent_json="${intent_json%\}},\"lifecyclePath\":\"$(macos_json_escape "$BOOTSTRAP_LIFECYCLE_PATH")\",\"backupPath\":\"$(macos_json_escape "$BOOTSTRAP_BACKUP_ROOT")\",\"evidencePath\":\"$(macos_json_escape "$BOOTSTRAP_EVIDENCE_ROOT")\",\"secondCopyPath\":\"$(macos_json_escape "$BOOTSTRAP_SECOND_COPY_ROOT")\",\"browserEvidencePath\":\"$(macos_json_escape "$BOOTSTRAP_BROWSER_PATH")\",\"browserEvidenceSha256\":\"$BOOTSTRAP_BROWSER_SHA256\"}"
  macos_write_atomic "$activation_intent_path" "$intent_json"
  macos_checksummed_json "$activation_intent_path"
}

run_prepare() {
  bootstrap_validate_formal_paths
  bootstrap_assert_fresh_state
  macos_acquire_lock "$MACOS_LAYOUT_STATE/.operation.lock"
  trap macos_release_lock EXIT
  bootstrap_resolve_release
  bootstrap_write_prepare
  macos_log "formal_writer_prepare status=prepared dataset=$BOOTSTRAP_DATASET_ID host=$BOOTSTRAP_HOST_ID writer_generation=1 maintenance=loopback-only empty_dataset=true volume_override=${volume_override:t}"
}

run_activate() {
  [[ -f "$intent_path" ]] || macos_die "Activate requires a completed Prepare intent"
  bootstrap_validate_formal_paths
  macos_acquire_lock "$MACOS_LAYOUT_STATE/.operation.lock"
  activation_failed=1
  fence_acquired=0
  maintenance_started=0
  db_started_for_resume=0
  cleanup_activate() {
    local exit_code=$?
    # A fence acquired for a failed activation is deliberately retained.  It
    # is the exact DB boundary that makes a retry/resume safe; releasing it
    # here could reopen a writer after a crash window.  Stop only services
    # started by this operation; no volume is deleted or recreated.
    if (( activation_failed == 1 && ( maintenance_started == 1 || db_started_for_resume == 1 ) )); then
      MACOS_PARENT_LOCK_PID="$$" "$SCRIPT_DIR/Stop-Platform.zsh" --root "$root" --lock-held >/dev/null 2>&1 || true
    fi
    macos_release_lock
    exit "$exit_code"
  }
  trap cleanup_activate EXIT

  bootstrap_resolve_release
  bootstrap_validate_intent "$BOOTSTRAP_RELEASE_PATH"
  bootstrap_repair_derived_sidecars
  [[ -f "$MACOS_CURRENT_STATE" ]] || macos_die "Activate requires the pending current state"
  pending_state="$(macos_json_get "$MACOS_CURRENT_STATE" bootstrapPending 2>/dev/null || true)"
  if [[ -f "$activation_terminal_path" ]]; then
    # A completed terminal is immutable commissioning evidence.  Validate its
    # exact intent/phase/identity semantics first, then create or repair the
    # separate persistent lineage record before asking the public readiness
    # guard to start the newer current release.
    bootstrap_load_terminal_artifacts
    bootstrap_validate_terminal_semantics
    if [[ ! -f "$activation_terminal_path.sha256" ]] || ! macos_check_checksum "$activation_terminal_path" >/dev/null 2>&1; then
      macos_write_checksum "$activation_terminal_path"
    fi
    bootstrap_write_lineage
  else
    bootstrap_validate_current_shape
  fi
  if [[ "$pending_state" != true && -f "$activation_terminal_path" && -f "$activation_terminal_path.sha256" ]]; then
    macos_assert_formal_writer_ready 0
    MACOS_PARENT_LOCK_PID="$$" "$SCRIPT_DIR/Start-Platform.zsh" --root "$root" --lock-held >/dev/null
    activation_failed=0
    macos_log "formal_writer_activate status=already-activated dataset=$BOOTSTRAP_DATASET_ID host=$BOOTSTRAP_HOST_ID writer_generation=1 public_start=resumed"
    return 0
  fi
  [[ "$pending_state" == true || -f "$activation_intent_path" ]] || macos_die "Activate found a non-pending current state without a resumable activation intent"
  bootstrap_validate_volume_override
  phase=""
  if [[ -f "$phase_path" ]]; then
    if ! bootstrap_phase_read >/dev/null 2>&1; then
      bootstrap_repair_phase_sidecar
      bootstrap_phase_read
    fi
    phase="$(macos_json_get "$phase_path" phase 2>/dev/null || true)"
  elif [[ -e "$phase_path.sha256" ]]; then
    macos_die "activation phase sidecar exists without its canonical journal"
  fi
  if [[ -z "$phase" || "$phase" == intent ]]; then
    # Schema-2 staging and browser evidence are validated before any formal
    # database/volume/migration side effect, then bound by the initial intent.
    bootstrap_validate_activation_evidence
    bootstrap_write_activation_intent
    if [[ -z "$phase" ]]; then
      bootstrap_phase_write intent
      phase=intent
    else
      phase_staging="$(macos_json_get "$phase_path" stagingAcceptancePath 2>/dev/null || true)"
      phase_browser="$(macos_json_get "$phase_path" browserEvidencePath 2>/dev/null || true)"
      [[ "$phase_staging" == "$BOOTSTRAP_STAGING_PATH" && "$phase_browser" == "$BOOTSTRAP_BROWSER_PATH" ]] || macos_die "activation intent rerun changed its immutable evidence binding"
    fi
  else
    bootstrap_load_phase_artifacts
  fi
  if [[ "$phase" == terminal ]]; then
    if [[ -f "$activation_terminal_path" ]]; then
      bootstrap_load_terminal_artifacts
      bootstrap_validate_terminal_semantics
      if [[ ! -f "$activation_terminal_path.sha256" ]] || ! macos_check_checksum "$activation_terminal_path" >/dev/null 2>&1; then
        macos_write_checksum "$activation_terminal_path"
      fi
      bootstrap_write_lineage
      macos_assert_formal_writer_ready 0
      MACOS_PARENT_LOCK_PID="$$" "$SCRIPT_DIR/Start-Platform.zsh" --root "$root" --lock-held >/dev/null
      activation_failed=0
      macos_log "formal_writer_activate status=already-activated dataset=$BOOTSTRAP_DATASET_ID host=$BOOTSTRAP_HOST_ID writer_generation=1 public_start=resumed"
      return 0
    fi
    db_started_for_resume=1
    macos_compose "$BOOTSTRAP_RELEASE_PATH" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" up -d --no-build --wait db
    fence_json="$(macos_operational_lock_one_shot_capture "$BOOTSTRAP_RELEASE_PATH" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" inspect-fence)"
    [[ "$(print -r -- "$fence_json" | plutil -extract active raw -o - 2>/dev/null || true)" == false ]] || macos_die "terminal phase without terminal evidence has an active writer fence"
    phase=fence-released
  fi

  if [[ "$phase" == intent ]]; then
    MACOS_PARENT_LOCK_PID="$$" "$SCRIPT_DIR/Start-Platform.zsh" --root "$root" --maintenance --lock-held >/dev/null
    maintenance_started=1
    bootstrap_phase_write maintenance-started
    phase=maintenance-started
  elif [[ "$phase" == maintenance-started || "$phase" == fence-acquired || "$phase" == backup-passed || "$phase" == restore-passed || "$phase" == preflight-passed ]]; then
    # A retry may have inherited a stopped Compose project after a crash.  The
    # exact phase keeps the target private, so starting maintenance again is
    # safe and makes the DB available for fence/backup/drill inspection.
    MACOS_PARENT_LOCK_PID="$$" "$SCRIPT_DIR/Start-Platform.zsh" --root "$root" --maintenance --lock-held >/dev/null
    maintenance_started=1
  elif [[ "$phase" == state-bound || "$phase" == fence-released ]]; then
    maintenance_started=0
    # These phases are reached after public services have been stopped.  A
    # host/DB restart can therefore leave the exact fence inaccessible until
    # the private DB is brought back; never start the public stack here.
    db_started_for_resume=1
    macos_compose "$BOOTSTRAP_RELEASE_PATH" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" up -d --no-build --wait db
  fi

  # The first writer DB is now initialized/migrated privately.  Reuse an
  # exact active fence on retry; otherwise acquire generation 1 atomically.
  if [[ "$phase" == maintenance-started || "$phase" == fence-acquired ]]; then
    db_started_for_resume=1
    macos_compose "$BOOTSTRAP_RELEASE_PATH" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" up -d --no-build --wait db
    fence_json="$(macos_operational_lock_one_shot_capture "$BOOTSTRAP_RELEASE_PATH" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" inspect-fence)"
    fence_active="$(print -r -- "$fence_json" | plutil -extract active raw -o - 2>/dev/null || true)"
    fence_dataset="$(print -r -- "$fence_json" | plutil -extract datasetId raw -o - 2>/dev/null || true)"
    fence_host="$(print -r -- "$fence_json" | plutil -extract hostId raw -o - 2>/dev/null || true)"
    fence_generation="$(print -r -- "$fence_json" | plutil -extract writerGeneration raw -o - 2>/dev/null || true)"
    if [[ "$fence_active" == true ]]; then
      [[ "$fence_dataset" == "$BOOTSTRAP_DATASET_ID" && "$fence_host" == "$BOOTSTRAP_HOST_ID" && "$fence_generation" == 1 ]] || macos_die "an unrelated writer fence blocks generation-1 activation"
    else
      fence_result="$(macos_operational_lock_one_shot_capture "$BOOTSTRAP_RELEASE_PATH" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" acquire-fence --dataset-id "$BOOTSTRAP_DATASET_ID" --host-id "$BOOTSTRAP_HOST_ID" --writer-generation 1 --reason formal-writer-bootstrap-activate --ttl-seconds 86400)"
      [[ "$(print -r -- "$fence_result" | plutil -extract active raw -o - 2>/dev/null || true)" == true && "$(print -r -- "$fence_result" | plutil -extract datasetId raw -o - 2>/dev/null || true)" == "$BOOTSTRAP_DATASET_ID" && "$(print -r -- "$fence_result" | plutil -extract hostId raw -o - 2>/dev/null || true)" == "$BOOTSTRAP_HOST_ID" && "$(print -r -- "$fence_result" | plutil -extract writerGeneration raw -o - 2>/dev/null || true)" == 1 ]] || macos_die "generation-1 writer fence was not acquired exactly"
    fi
    fence_acquired=1
    if [[ "$phase" == maintenance-started ]]; then
      bootstrap_phase_write fence-acquired
      phase=fence-acquired
    fi
  elif [[ "$phase" == backup-passed || "$phase" == restore-passed || "$phase" == preflight-passed ]]; then
    fence_json="$(macos_operational_lock_one_shot_capture "$BOOTSTRAP_RELEASE_PATH" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" inspect-fence)"
    [[ "$(print -r -- "$fence_json" | plutil -extract active raw -o - 2>/dev/null || true)" == true && "$(print -r -- "$fence_json" | plutil -extract datasetId raw -o - 2>/dev/null || true)" == "$BOOTSTRAP_DATASET_ID" && "$(print -r -- "$fence_json" | plutil -extract hostId raw -o - 2>/dev/null || true)" == "$BOOTSTRAP_HOST_ID" && "$(print -r -- "$fence_json" | plutil -extract writerGeneration raw -o - 2>/dev/null || true)" == 1 ]] || macos_die "activation phase requires the exact active generation-1 writer fence"
    fence_acquired=1
  elif [[ "$phase" == state-bound ]]; then
    fence_json="$(macos_operational_lock_one_shot_capture "$BOOTSTRAP_RELEASE_PATH" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" inspect-fence)"
    fence_active="$(print -r -- "$fence_json" | plutil -extract active raw -o - 2>/dev/null || true)"
    if [[ "$fence_active" == true ]]; then
      [[ "$(print -r -- "$fence_json" | plutil -extract datasetId raw -o - 2>/dev/null || true)" == "$BOOTSTRAP_DATASET_ID" && "$(print -r -- "$fence_json" | plutil -extract hostId raw -o - 2>/dev/null || true)" == "$BOOTSTRAP_HOST_ID" && "$(print -r -- "$fence_json" | plutil -extract writerGeneration raw -o - 2>/dev/null || true)" == 1 ]] || macos_die "state-bound phase has an unrelated active writer fence"
      fence_acquired=1
    else
      bootstrap_validate_current_shape
      [[ "$(macos_json_get "$MACOS_CURRENT_STATE" bootstrapPending 2>/dev/null || true)" == true && "$(macos_json_get "$MACOS_CURRENT_STATE" activationReady 2>/dev/null || true)" == true ]] || macos_die "state-bound phase lost its pending activation barrier"
      phase=fence-released
      bootstrap_phase_write fence-released
      fence_acquired=0
    fi
  elif [[ "$phase" == fence-released ]]; then
    fence_json="$(macos_operational_lock_one_shot_capture "$BOOTSTRAP_RELEASE_PATH" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" inspect-fence)"
    [[ "$(print -r -- "$fence_json" | plutil -extract active raw -o - 2>/dev/null || true)" == false ]] || macos_die "fence-released phase has an active writer fence"
    fence_acquired=0
  fi

  if [[ "$phase" == fence-acquired || "$phase" == backup-passed ]]; then
    if [[ "$phase" != backup-passed ]]; then
      if [[ -n "$paired_backup_arg" ]]; then
        bootstrap_validate_backup "$paired_backup_arg"
      else
        backup_output="$(MACOS_PARENT_LOCK_PID="$$" "$SCRIPT_DIR/Invoke-PairedBackup.zsh" --root "$root" --kind cutover --under-writer-fence --lock-held)"
        backup_id="$(print -r -- "$backup_output" | sed -n 's/.*backup=//p' | tail -n 1)"
        [[ "$backup_id" =~ '^backup-[0-9]{8}T[0-9]{6}Z$' ]] || macos_die "fenced paired backup did not return an exact backup identity"
        bootstrap_validate_backup "$MACOS_LAYOUT_BACKUPS/$backup_id"
      fi
      bootstrap_phase_write backup-passed
      phase=backup-passed
    else
      [[ -n "${BOOTSTRAP_BACKUP_PATH:-}" ]] || {
        phase_backup_path="$(macos_json_get "$phase_path" pairedBackupPath 2>/dev/null || true)"
        [[ -n "$phase_backup_path" ]] || macos_die "backup-passed phase lacks its exact backup path"
        bootstrap_validate_backup "$phase_backup_path"
      }
    fi
  fi

  if [[ "$phase" == backup-passed || "$phase" == restore-passed ]]; then
    if [[ "$phase" != restore-passed ]]; then
      if [[ -n "$restore_drill_arg" ]]; then
        bootstrap_validate_restore_drill "$restore_drill_arg"
      else
        second_copy_root="$(macos_formal_value SECOND_COPY_PATH)"
        MACOS_PARENT_LOCK_PID="$$" "$SCRIPT_DIR/Invoke-RestoreDrill.zsh" --second-copy-backup-path "$second_copy_root/${BOOTSTRAP_BACKUP_PATH:t}" --release-path "$BOOTSTRAP_RELEASE_PATH" --no-db-audit --bootstrap --lock-held --root "$root" >/dev/null
        restore_candidate=""
        for candidate in "$MACOS_LAYOUT_EVIDENCE"/restore-drill-*.json(Nom[1]); do
          [[ "$(macos_json_get "$candidate" backupId 2>/dev/null || true)" == "${BOOTSTRAP_BACKUP_PATH:t}" ]] && restore_candidate="$candidate"
        done
        [[ -n "$restore_candidate" ]] || macos_die "restore drill did not leave a checksummed exact evidence record"
        bootstrap_validate_restore_drill "$restore_candidate"
      fi
      bootstrap_phase_write restore-passed
      phase=restore-passed
    fi
  fi

  if [[ "$phase" == restore-passed || "$phase" == preflight-passed ]]; then
    if [[ "$phase" != preflight-passed ]]; then
      if [[ -n "$preflight_arg" ]]; then
        bootstrap_validate_activation_evidence
      else
        [[ -n "$pf_evidence_arg" && -n "$network_time_evidence_arg" ]] || macos_die "automatic target-maintenance preflight requires --pf-evidence and --network-time-evidence"
        target_preflight_path="$MACOS_LAYOUT_EVIDENCE/formal-writer-preflight-$(macos_timestamp)-$$.json"
        preflight_command=( "$SCRIPT_DIR/Test-FormalPreflight.zsh" --root "$root" --lock-held --target-maintenance --backup-path "$BOOTSTRAP_BACKUP_PATH" --browser-smoke-evidence "$BOOTSTRAP_BROWSER_PATH" --pf-evidence "$pf_evidence_arg" --network-time-evidence "$network_time_evidence_arg" --evidence-path "$target_preflight_path" )
        [[ -z "$docker_settings_evidence_arg" ]] || preflight_command+=( --docker-settings-evidence "$docker_settings_evidence_arg" )
        MACOS_PARENT_LOCK_PID="$$" "${preflight_command[@]}" >/dev/null
        preflight_arg="$target_preflight_path"
        bootstrap_validate_activation_evidence
      fi
      bootstrap_phase_write preflight-passed
      phase=preflight-passed
    fi
  fi

  if [[ "$phase" == preflight-passed ]]; then
  # Public services are stopped before the ownership state is changed.  Keep
  # only DB up for the final fence/state transition and preserve the pending
  # barrier until release and terminal evidence are both durable.
  MACOS_PARENT_LOCK_PID="$$" "$SCRIPT_DIR/Stop-Platform.zsh" --root "$root" --lock-held >/dev/null
  maintenance_started=0
  db_started_for_resume=1
  macos_compose "$BOOTSTRAP_RELEASE_PATH" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" up -d --no-build --wait db
  macos_assert_writer_fence_owner "$BOOTSTRAP_RELEASE_PATH" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" "$BOOTSTRAP_DATASET_ID" "$BOOTSTRAP_HOST_ID" 1
  macos_adopt_cutover_identity "$BOOTSTRAP_DATASET_ID" "$BOOTSTRAP_HOST_ID" 1
  activation_digest="$(macos_sha256 "$activation_intent_path")"
  macos_write_atomic "$MACOS_CURRENT_STATE" "{\"schemaVersion\":1,\"kind\":\"formal-writer-current\",\"applicationVersion\":\"$(macos_json_escape "$BOOTSTRAP_RELEASE_VERSION")\",\"gitCommit\":\"$BOOTSTRAP_RELEASE_COMMIT\",\"path\":\"$(macos_json_escape "$BOOTSTRAP_RELEASE_PATH")\",\"promotedAt\":\"$(macos_now_iso)\",\"pairedBackupPath\":\"$(macos_json_escape "$BOOTSTRAP_BACKUP_PATH")\",\"stagingAcceptancePath\":\"$(macos_json_escape "$BOOTSTRAP_STAGING_PATH")\",\"datasetId\":\"$BOOTSTRAP_DATASET_ID\",\"hostId\":\"$BOOTSTRAP_HOST_ID\",\"writerGeneration\":1,\"bootstrapPending\":true,\"activationReady\":true,\"activationIntentSha256\":\"$activation_digest\"}"
  macos_write_checksum "$MACOS_CURRENT_STATE"
  bootstrap_phase_write state-bound
  phase=state-bound
  fi
  if [[ "$phase" == state-bound && "$fence_acquired" == 1 ]]; then
  release_result="$(macos_operational_lock_one_shot_capture "$BOOTSTRAP_RELEASE_PATH" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" release-fence --dataset-id "$BOOTSTRAP_DATASET_ID" --host-id "$BOOTSTRAP_HOST_ID" --writer-generation 1)"
  [[ "$(print -r -- "$release_result" | plutil -extract active raw -o - 2>/dev/null || true)" == false ]] || macos_die "generation-1 writer fence was not released exactly"
  fence_acquired=0
  bootstrap_phase_write fence-released
  phase=fence-released
  fi
  if [[ "$phase" == fence-released ]]; then
    activation_digest="$(macos_sha256 "$activation_intent_path")"
    if [[ "$(macos_json_get "$MACOS_CURRENT_STATE" bootstrapPending 2>/dev/null || true)" == true ]]; then
      macos_json_replace_atomic "$MACOS_CURRENT_STATE" bootstrapPending false
      macos_json_replace_atomic "$MACOS_CURRENT_STATE" activationReady true
      macos_write_checksum "$MACOS_CURRENT_STATE"
    else
      bootstrap_validate_current_shape
      [[ "$(macos_json_get "$MACOS_CURRENT_STATE" activationReady 2>/dev/null || true)" == true ]] || macos_die "fence-released phase lost activation readiness"
    fi
    current_digest="$(macos_sha256 "$MACOS_CURRENT_STATE")"
    bootstrap_phase_write terminal
    phase_digest="$(macos_sha256 "$phase_path")"
    if [[ ! -f "$activation_terminal_path" ]]; then
      macos_write_atomic "$activation_terminal_path" "{\"schemaVersion\":1,\"kind\":\"formal-writer-activation-terminal\",\"status\":\"passed\",\"activationIntentSha256\":\"$activation_digest\",\"phaseSha256\":\"$phase_digest\",\"currentStateSha256\":\"$current_digest\",\"datasetId\":\"$BOOTSTRAP_DATASET_ID\",\"hostId\":\"$BOOTSTRAP_HOST_ID\",\"writerGeneration\":1,\"releasePath\":\"$(macos_json_escape "$BOOTSTRAP_RELEASE_PATH")\",\"pairedBackupPath\":\"$(macos_json_escape "$BOOTSTRAP_BACKUP_PATH")\",\"stagingAcceptancePath\":\"$(macos_json_escape "$BOOTSTRAP_STAGING_PATH")\",\"preflightPath\":\"$(macos_json_escape "$BOOTSTRAP_PREFLIGHT_PATH")\",\"restoreDrillPath\":\"$(macos_json_escape "$BOOTSTRAP_RESTORE_DRILL_PATH")\",\"targetExposed\":false,\"targetWriteAccepted\":false,\"createdAt\":\"$(macos_now_iso)\",\"approval\":\"manual-required\"}"
      macos_checksummed_json "$activation_terminal_path"
    else
      macos_check_checksum "$activation_terminal_path"
    fi
    bootstrap_write_lineage
  fi
  [[ "$phase" == fence-released ]] || macos_die "activation cannot complete from an unknown phase: $phase"
  MACOS_PARENT_LOCK_PID="$$" "$SCRIPT_DIR/Start-Platform.zsh" --root "$root" --lock-held >/dev/null
  activation_failed=0
  macos_log "formal_writer_activate status=activated dataset=$BOOTSTRAP_DATASET_ID host=$BOOTSTRAP_HOST_ID writer_generation=1 release=${BOOTSTRAP_RELEASE_PATH:t}"
}

run_status() {
  if [[ ! -e "$intent_path" && ! -e "$intent_path.sha256" ]]; then
    macos_log "formal_writer_status status=unprepared"
    return 0
  fi
  [[ -f "$intent_path" && -f "$intent_path.sha256" ]] || macos_die "bootstrap intent sidecar is incomplete"
  macos_check_checksum "$intent_path"
  if [[ -e "$activation_terminal_path" || -e "$activation_terminal_path.sha256" ]]; then
    macos_assert_formal_writer_ready 0
    macos_log "formal_writer_status status=activated dataset=$(macos_json_get "$intent_path" datasetId) host=$(macos_json_get "$intent_path" hostId) writer_generation=1"
  elif [[ -e "$activation_intent_path" || -e "$activation_intent_path.sha256" ]]; then
    macos_log "formal_writer_status status=activation-pending dataset=$(macos_json_get "$intent_path" datasetId) host=$(macos_json_get "$intent_path" hostId) writer_generation=1"
  else
    macos_log "formal_writer_status status=prepared dataset=$(macos_json_get "$intent_path" datasetId) host=$(macos_json_get "$intent_path" hostId) writer_generation=1 maintenance=loopback-only"
  fi
}

case "$action" in
  prepare) run_prepare ;;
  activate) run_activate ;;
  status) run_status ;;
esac
