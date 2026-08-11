#!/bin/zsh
# Shared, fail-closed helpers for the macOS formal host adapter.
#
# This file intentionally contains no application logic.  Application-specific
# checks and data operations stay inside the versioned backend image.

set -euo pipefail
setopt no_nomatch
umask 077

typeset -g MACOS_OPS_SCRIPT_DIR="${${(%):-%N}:A:h}"
typeset -g MACOS_FORMAL_PROJECT="internal-exam-formal"
typeset -g MACOS_DEV_PROJECT="internal-exam-dev"
typeset -g MACOS_STAGE_PORT_CANDIDATE="18080"
typeset -g MACOS_STAGE_PORT_OPERATOR="18081"
typeset -g MACOS_STAGE_PORT_DATABASE="15432"
typeset -g MACOS_STAGE_PORT_FRONTEND="15173"

macos_die() {
  print -u2 -- "macOS operation failed: $*"
  return 1
}

macos_log() {
  print -r -- "$*"
}

macos_require_command() {
  (( $# == 1 )) || macos_die "internal command check error" || return 1
  command -v "$1" >/dev/null 2>&1 || macos_die "required command is unavailable: $1"
}

macos_assert_macos() {
  [[ "$(uname -s)" == "Darwin" ]] || macos_die "this operation requires macOS" || return 1
}

macos_resolve_path() {
  local value="${1:-}"
  [[ -n "$value" ]] || macos_die "path is empty" || return 1
  [[ "$value" == /* ]] || macos_die "path must be absolute: $value" || return 1
  if [[ -e "$value" ]]; then
    print -r -- "${value:A}"
    return 0
  fi
  local parent="${value:h}"
  local name="${value:t}"
  [[ -d "$parent" ]] || macos_die "path parent does not exist: $parent" || return 1
  print -r -- "${parent:A}/$name"
}

macos_timestamp() {
  date -u '+%Y%m%dT%H%M%SZ'
}

macos_now_iso() {
  date -u '+%Y-%m-%dT%H:%M:%SZ'
}

macos_epoch_from_iso() {
  local timestamp="${1:-}" main zone zone_arg
  [[ "$timestamp" =~ '^([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2})(\.[0-9]+)?(Z|[+-][0-9]{2}:[0-9]{2})$' ]] || macos_die "timestamp format is invalid" || return 1
  main="${match[1]}"
  zone="${match[3]}"
  if [[ "$zone" == Z ]]; then
    zone_arg="+0000"
  else
    zone_arg="${zone//:/}"
  fi
  date -u -j -f '%Y-%m-%dT%H:%M:%S%z' "${main}${zone_arg}" '+%s' 2>/dev/null || macos_die "timestamp cannot be parsed" || return 1
}

macos_assert_fresh_timestamp() {
  local timestamp="${1:-}" maximum_age_seconds="${2:-604800}" timestamp_epoch now_epoch
  timestamp_epoch="$(macos_epoch_from_iso "$timestamp")"
  now_epoch="$(date -u '+%s')"
  (( timestamp_epoch <= now_epoch + 300 )) || macos_die "timestamp is too far in the future" || return 1
  (( now_epoch - timestamp_epoch <= maximum_age_seconds )) || macos_die "timestamp is stale" || return 1
}

macos_mktemp() {
  local template="${1:-internal-exam.XXXXXX}"
  mktemp -t "$template"
}

macos_secure_mode() {
  local target_path="${1:-}"
  [[ -e "$target_path" ]] || macos_die "required path is missing: $target_path" || return 1
  local mode
  mode="$(stat -f '%Lp' -- "$target_path")"
  (( (8#$mode & 8#077) == 0 )) || macos_die "path is not owner-only: $target_path" || return 1
}

macos_assert_owner() {
  local target_path="${1:-}"
  [[ -e "$target_path" ]] || macos_die "required path is missing: $target_path" || return 1
  local owner
  owner="$(stat -f '%Su' -- "$target_path")"
  [[ "$owner" == "$(id -un)" ]] || macos_die "path is not owned by the current operator: $target_path" || return 1
}

macos_secure_path() {
  macos_assert_owner "$1"
  macos_secure_mode "$1"
}

macos_layout() {
  local root_input="${1:-${INTERNAL_EXAM_ROOT:-${HOME:?}/Library/Application Support/InternalExam}}"
  typeset -g MACOS_LAYOUT_ROOT="$(macos_resolve_path "$root_input")"
  typeset -g MACOS_LAYOUT_CONFIGURATION="$MACOS_LAYOUT_ROOT/configuration"
  typeset -g MACOS_LAYOUT_LIFECYCLE="$MACOS_LAYOUT_ROOT/lifecycle"
  typeset -g MACOS_LAYOUT_RELEASES="$MACOS_LAYOUT_ROOT/releases"
  typeset -g MACOS_LAYOUT_BACKUPS="$MACOS_LAYOUT_ROOT/backups"
  typeset -g MACOS_LAYOUT_EVIDENCE="$MACOS_LAYOUT_ROOT/evidence"
  typeset -g MACOS_LAYOUT_DIAGNOSTICS="$MACOS_LAYOUT_ROOT/diagnostics"
  typeset -g MACOS_LAYOUT_STATE="$MACOS_LAYOUT_ROOT/state"
  typeset -g MACOS_FORMAL_ENV="$MACOS_LAYOUT_CONFIGURATION/formal.env"
  typeset -g MACOS_STAGING_ENV="$MACOS_LAYOUT_CONFIGURATION/staging.env"
  typeset -g MACOS_HOST_EVIDENCE="$MACOS_LAYOUT_CONFIGURATION/host-evidence.env"
  typeset -g MACOS_CURRENT_STATE="$MACOS_LAYOUT_STATE/current-release.json"
  typeset -g MACOS_PREVIOUS_STATE="$MACOS_LAYOUT_STATE/previous-release.json"
}

macos_assert_outside_worktree() {
  local value="$(macos_resolve_path "$1")"
  local worktree=""
  if worktree="$(git -C "$MACOS_OPS_SCRIPT_DIR/../.." rev-parse --show-toplevel 2>/dev/null)"; then
    worktree="${worktree:A}"
    [[ "$value" != "$worktree" && "$value" != "$worktree"/* ]] || {
      macos_die "formal host path must be outside the development worktree: $value"
      return 1
    }
  fi
  print -r -- "$value"
}

macos_initialize_layout() {
  local root_input="${1:-}"
  [[ -n "$root_input" ]] || root_input="${INTERNAL_EXAM_ROOT:-${HOME:?}/Library/Application Support/InternalExam}"
  # A formal root must never resolve into the development checkout.  Resolve
  # before creating anything so a symlink cannot bypass this boundary.
  macos_assert_outside_worktree "$root_input" >/dev/null
  macos_layout "$root_input"
  local directory
  for directory in \
    "$MACOS_LAYOUT_ROOT" "$MACOS_LAYOUT_CONFIGURATION" "$MACOS_LAYOUT_LIFECYCLE" "$MACOS_LAYOUT_RELEASES" \
    "$MACOS_LAYOUT_BACKUPS" "$MACOS_LAYOUT_EVIDENCE" "$MACOS_LAYOUT_DIAGNOSTICS" \
    "$MACOS_LAYOUT_STATE"; do
    mkdir -p -- "$directory"
    chmod 700 "$directory"
  done
  for file in "$MACOS_FORMAL_ENV" "$MACOS_STAGING_ENV" "$MACOS_HOST_EVIDENCE"; do
    if [[ ! -e "$file" ]]; then
      : > "$file"
    fi
    chmod 600 "$file"
  done
  macos_secure_path "$MACOS_LAYOUT_ROOT"
  macos_secure_path "$MACOS_LAYOUT_CONFIGURATION"
  macos_secure_path "$MACOS_FORMAL_ENV"
}

macos_assert_protected_configuration() {
  local root_input="${1:-}"
  [[ -n "$root_input" ]] || root_input="${INTERNAL_EXAM_ROOT:-${HOME:?}/Library/Application Support/InternalExam}"
  macos_assert_outside_worktree "$root_input" >/dev/null
  macos_layout "$root_input"
  macos_secure_path "$MACOS_LAYOUT_ROOT"
  macos_secure_path "$MACOS_LAYOUT_CONFIGURATION"
  macos_secure_path "$MACOS_FORMAL_ENV"
}

macos_assert_formal_paths() {
  macos_layout "${1:-}"
  macos_assert_protected_configuration "$MACOS_LAYOUT_ROOT"
  local name value
  for name in INTERNAL_EXAM_LIFECYCLE_HOST_DIR INTERNAL_EXAM_BACKUP_HOST_DIR INTERNAL_EXAM_EVIDENCE_HOST_DIR SECOND_COPY_PATH; do
    if value="$(macos_dotenv_get "$MACOS_FORMAL_ENV" "$name" 2>/dev/null)"; then
      [[ -n "$value" ]] || macos_die "$name must not be empty when configured" || return 1
      macos_assert_outside_worktree "$value" >/dev/null
    fi
  done
}

macos_run_checked() {
  (( $# > 0 )) || macos_die "no command supplied" || return 1
  local error_file
  error_file="$(macos_mktemp internal-exam-error.XXXXXX)"
  if ! "$@" > /dev/null 2> "$error_file"; then
    rm -f -- "$error_file"
    macos_die "operation failed; review local non-secret diagnostics"
    return 1
  fi
  rm -f -- "$error_file"
}

macos_run_capture() {
  (( $# > 0 )) || macos_die "no command supplied" || return 1
  local error_file output
  error_file="$(macos_mktemp internal-exam-error.XXXXXX)"
  # Keep the argument vector intact.  An unquoted $@ turns a path or compose
  # argument containing whitespace into a different command (and permits
  # command-string interpretation by the shell).
  if ! output="$("$@" 2> "$error_file")"; then
    rm -f -- "$error_file"
    macos_die "validation command failed"
    return 1
  fi
  rm -f -- "$error_file"
  print -r -- "$output"
}

macos_run_to_file() {
  (( $# >= 2 )) || macos_die "invalid output command" || return 1
  local destination="${1}"; shift
  [[ "$destination" == /* ]] || macos_die "output path must be absolute" || return 1
  [[ -d "${destination:h}" ]] || macos_die "output parent is missing" || return 1
  local temporary
  temporary="$(mktemp "${destination}.tmp.XXXXXX")"
  chmod 600 "$temporary"
  local error_file
  error_file="$(macos_mktemp internal-exam-error.XXXXXX)"
  if ! "$@" > "$temporary" 2> "$error_file"; then
    rm -f -- "$error_file"
    rm -f -- "$temporary"
    macos_die "operation failed; output was not retained"
    return 1
  fi
  rm -f -- "$error_file"
  mv -f -- "$temporary" "$destination"
  chmod 600 "$destination"
}

macos_docker_ready() {
  macos_require_command docker
  docker info >/dev/null 2>&1 || macos_die "Docker Desktop is not ready" || return 1
  docker compose version >/dev/null 2>&1 || macos_die "Docker Compose is unavailable" || return 1
}

typeset -ga MACOS_COMPOSE_ARGS
macos_compose_base() {
  local release="$(macos_resolve_path "$1")"
  local env_file="$(macos_resolve_path "$2")"
  local project="$3"
  [[ -f "$release/docker-compose.yml" ]] || macos_die "release Compose file is missing" || return 1
  macos_secure_path "$env_file"
  case "$project" in
    "$MACOS_FORMAL_PROJECT"|"$MACOS_DEV_PROJECT") ;;
    internal-exam-staging-*) macos_assert_project_name staging "$project" ;;
    internal-exam-restore-verify-*) macos_assert_project_name restore "$project" ;;
    *) macos_die "unsafe or ambiguous Compose project name: $project"; return 1 ;;
  esac
  typeset -ga MACOS_COMPOSE_ARGS
  MACOS_COMPOSE_ARGS=(compose --project-name "$project" --env-file "$env_file" -f "$release/docker-compose.yml")
  # A cutover restore must never merge data into the previous formal named
  # volumes.  Accept-HostCutover writes this owner-only, checksummed override
  # before touching the formal project; every subsequent formal one-shot and
  # lifecycle command then resolves the same fresh volume names here.
  if [[ "$project" == "$MACOS_FORMAL_PROJECT" && -n "${MACOS_LAYOUT_STATE:-}" ]]; then
    local volume_override="$MACOS_LAYOUT_STATE/formal-volume-override.yml"
    if [[ -e "$volume_override" || -e "$volume_override.sha256" ]]; then
      [[ -f "$volume_override" && -f "$volume_override.sha256" ]] || macos_die "formal volume override is incomplete" || return 1
      macos_secure_path "$volume_override"
      macos_check_checksum "$volume_override"
      MACOS_COMPOSE_ARGS+=( -f "$volume_override" )
    fi
  fi
}

macos_compose() {
  local release="$1" env_file="$2" project="$3"
  shift 3
  macos_compose_base "$release" "$env_file" "$project"
  macos_run_checked docker "${MACOS_COMPOSE_ARGS[@]}" "$@"
}

macos_compose_capture() {
  local release="$1" env_file="$2" project="$3"
  shift 3
  macos_compose_base "$release" "$env_file" "$project"
  macos_run_capture docker "${MACOS_COMPOSE_ARGS[@]}" "$@"
}

macos_backend_one_shot() {
  # Application and portability logic belongs to the selected image.  The
  # host adapter supplies only the Compose project and command arguments.
  local release="$1" env_file="$2" project="$3"
  shift 3
  (( $# > 0 )) || macos_die "backend one-shot command is missing" || return 1
  macos_compose_base "$release" "$env_file" "$project"
  macos_run_checked docker "${MACOS_COMPOSE_ARGS[@]}" run --rm --no-deps backend \
    uv run --no-sync python -m app.ops.host_portability "$@"
}

macos_backend_one_shot_capture() {
  local release="$1" env_file="$2" project="$3"
  shift 3
  (( $# > 0 )) || macos_die "backend one-shot command is missing" || return 1
  macos_compose_base "$release" "$env_file" "$project"
  macos_run_capture docker "${MACOS_COMPOSE_ARGS[@]}" run --rm --no-deps backend \
    uv run --no-sync python -m app.ops.host_portability "$@"
}

macos_backend_one_shot_with_mounts() {
  # Keep portability calls in the selected backend image while allowing a
  # host adapter to pass only explicitly-scoped, read-only or state mounts.
  # Mount declarations must precede the backend CLI vector; this prevents a
  # user-supplied value from being interpreted as a Docker option.
  local release="$1" env_file="$2" project="$3"
  shift 3
  local -a mount_args=()
  while (( $# >= 2 )) && [[ "$1" == --volume ]]; do
    mount_args+=(--volume "$2")
    shift 2
  done
  (( $# > 0 )) || macos_die "backend one-shot command is missing" || return 1
  macos_compose_base "$release" "$env_file" "$project"
  macos_run_checked docker "${MACOS_COMPOSE_ARGS[@]}" run --rm --no-deps \
    "${mount_args[@]}" backend \
    uv run --no-sync python -m app.ops.host_portability "$@"
}

macos_recover_cutover_state() {
  # Canonical cutover JSON/sidecar claim recovery belongs to the selected
  # backend image.  The host adapter may only detect an interrupted
  # transaction and invoke that narrow repair command; it must never rewrite
  # the canonical state or checksum itself.
  local release_input="$1" source_input="$2" accepted_input="$3"
  [[ ! -L "$source_input" && ! -L "$accepted_input" ]] || macos_die "cutover recovery paths must be ordinary files" || return 1
  local release="$(macos_resolve_path "$release_input")" source_path="$(macos_resolve_path "$source_input")" accepted_path="$(macos_resolve_path "$accepted_input")"
  local source_name="${source_path:t}" accepted_name="${accepted_path:t}"
  local marker_path="${source_path}.consumed.json" marker_checksum_path="${source_path}.consumed.json.sha256"
  local source_write_temp="${source_path:h}/.${source_name}.cutover-write.tmp" source_checksum_write_temp="${source_path:h}/.${source_name}.sha256.cutover-write.tmp" source_claim_temp="${source_path:h}/.${source_name}.cutover-claim.tmp" source_checksum_claim_temp="${source_path:h}/.${source_name}.sha256.cutover-claim.tmp"
  local accepted_write_temp="${accepted_path:h}/.${accepted_name}.cutover-write.tmp" accepted_claim_temp="${accepted_path:h}/.${accepted_name}.cutover-claim.tmp"
  local marker_write_temp="${marker_path:h}/.${marker_path:t}.cutover-write.tmp" marker_claim_temp="${marker_path:h}/.${marker_path:t}.cutover-claim.tmp"
  local marker_checksum_write_temp="${marker_checksum_path:h}/.${marker_checksum_path:t}.cutover-write.tmp" marker_checksum_claim_temp="${marker_checksum_path:h}/.${marker_checksum_path:t}.cutover-claim.tmp"
  local accepted_checksum_write_temp="${accepted_path:h}/.${accepted_name}.sha256.cutover-write.tmp" accepted_checksum_claim_temp="${accepted_path:h}/.${accepted_name}.sha256.cutover-claim.tmp"
  local recovery_evidence=0 backend_image commit artifact
  [[ "${source_path:h}" == "$MACOS_LAYOUT_STATE" && "${accepted_path:h}" == "$MACOS_LAYOUT_STATE" ]] || macos_die "cutover recovery paths must stay in the protected state directory" || return 1
  [[ "$source_path" != "$accepted_path" && ! -L "$source_path" && ! -L "$accepted_path" ]] || macos_die "cutover recovery paths must be distinct ordinary files" || return 1
  # Existing canonical JSON is not by itself an interrupted claim.  Marker,
  # accepted output, or deterministic backend staging is the evidence that
  # permits the backend recovery command to run.
  for artifact in \
    "$marker_path" "$marker_checksum_path" "$source_write_temp" "$source_checksum_write_temp" "$source_claim_temp" "$source_checksum_claim_temp" \
    "$accepted_path" "$accepted_path.sha256" "$accepted_write_temp" "$accepted_claim_temp" \
    "$accepted_checksum_write_temp" "$accepted_checksum_claim_temp" \
    "$marker_write_temp" "$marker_claim_temp" "$marker_checksum_write_temp" "$marker_checksum_claim_temp"; do
    if [[ -e "$artifact" ]]; then
      recovery_evidence=1
      break
    fi
  done
  (( recovery_evidence == 1 )) || return 0
  [[ -f "$release/release-manifest.json" && -f "$release/ops/release/built-image-identity.json" ]] || macos_die "selected release image identity is missing for cutover recovery" || return 1
  macos_check_checksum "$release/ops/release/built-image-identity.json"
  commit="$(macos_json_get "$release/release-manifest.json" gitCommit 2>/dev/null || true)"
  backend_image="$(macos_json_get "$release/ops/release/built-image-identity.json" images.backend.reference 2>/dev/null || true)"
  [[ "$commit" =~ '^[0-9a-fA-F]{40}$' && "$backend_image" == *":${commit:l}" ]] || macos_die "cutover recovery image is not the selected release backend" || return 1
  # This is deliberately a plain selected-image one-shot: no formal Compose
  # service, env file, database, or named volume is involved.
  macos_run_checked docker run --rm --volume "$MACOS_LAYOUT_STATE:/cutover-state:rw" "$backend_image" \
    uv run --no-sync python -m app.ops.host_portability recover-cutover-state \
    "/cutover-state/$source_name" --accepted-state "/cutover-state/$accepted_name"
}

macos_internal_backup_one_shot_with_mounts() {
  # The versioned backend image is also the authority for paired-backup
  # checksum/manifest validation.  Keep this vector separate from the
  # host-portability CLI so callers cannot accidentally validate a directory
  # with host Python or a development checkout.
  local release="$1" env_file="$2" project="$3"
  shift 3
  local -a mount_args=()
  while (( $# >= 2 )) && [[ "$1" == --volume ]]; do
    mount_args+=(--volume "$2")
    shift 2
  done
  (( $# > 0 )) || macos_die "internal backup command is missing" || return 1
  macos_compose_base "$release" "$env_file" "$project"
  macos_run_checked docker "${MACOS_COMPOSE_ARGS[@]}" run --rm --no-deps \
    "${mount_args[@]}" backend \
    uv run --no-sync python -m app.ops.internal_backup "$@"
}

macos_operational_lock_one_shot() {
  # Persistent writer-fence transitions are backend-owned.  Keep this vector
  # centralized so a backend CLI rename changes one adapter surface only.
  local release="$1" env_file="$2" project="$3"
  shift 3
  (( $# > 0 )) || macos_die "operational-lock command is missing" || return 1
  macos_compose_base "$release" "$env_file" "$project"
  macos_run_checked docker "${MACOS_COMPOSE_ARGS[@]}" run --rm --no-deps backend \
    uv run --no-sync python -m app.ops.operational_lock "$@"
}

macos_operational_lock_one_shot_capture() {
  local release="$1" env_file="$2" project="$3"
  shift 3
  (( $# > 0 )) || macos_die "operational-lock command is missing" || return 1
  macos_compose_base "$release" "$env_file" "$project"
  macos_run_capture docker "${MACOS_COMPOSE_ARGS[@]}" run --rm --no-deps backend \
    uv run --no-sync python -m app.ops.operational_lock "$@"
}

macos_operational_lock_one_shot_with_mounts_capture() {
  local release="$1" env_file="$2" project="$3"
  shift 3
  local -a mount_args=()
  while (( $# >= 2 )) && [[ "$1" == --volume ]]; do
    mount_args+=(--volume "$2")
    shift 2
  done
  (( $# > 0 )) || macos_die "operational-lock command is missing" || return 1
  macos_compose_base "$release" "$env_file" "$project"
  macos_run_capture docker "${MACOS_COMPOSE_ARGS[@]}" run --rm --no-deps \
    "${mount_args[@]}" backend \
    uv run --no-sync python -m app.ops.operational_lock "$@"
}

macos_operational_lock_one_shot_with_mounts() {
  local release="$1" env_file="$2" project="$3"
  shift 3
  local -a mount_args=()
  while (( $# >= 2 )) && [[ "$1" == --volume ]]; do
    mount_args+=(--volume "$2")
    shift 2
  done
  (( $# > 0 )) || macos_die "operational-lock command is missing" || return 1
  macos_compose_base "$release" "$env_file" "$project"
  macos_run_checked docker "${MACOS_COMPOSE_ARGS[@]}" run --rm --no-deps \
    "${mount_args[@]}" backend \
    uv run --no-sync python -m app.ops.operational_lock "$@"
}

macos_assert_writer_fence_clear() {
  local release="$1" env_file="$2" project="$3" fence_json fence_active fence_dataset fence_host fence_generation
  fence_json="$(macos_operational_lock_one_shot_capture "$release" "$env_file" "$project" inspect-fence)"
  fence_active="$(print -r -- "$fence_json" | plutil -extract active raw -o - - 2>/dev/null || true)"
  [[ "$fence_active" != true ]] || macos_die "formal writer fence is active; lifecycle start is fenced"
  fence_dataset="$(print -r -- "$fence_json" | plutil -extract datasetId raw -o - - 2>/dev/null || true)"
  fence_host="$(print -r -- "$fence_json" | plutil -extract hostId raw -o - - 2>/dev/null || true)"
  fence_generation="$(print -r -- "$fence_json" | plutil -extract writerGeneration raw -o - - 2>/dev/null || true)"
  if [[ -n "$fence_host" && "$fence_host" != null ]]; then
    local expected_dataset expected_host expected_generation
    [[ -f "$MACOS_CURRENT_STATE" && -f "$MACOS_CURRENT_STATE.sha256" ]] || macos_die "released writer fence exists but current formal state is missing"
    macos_check_checksum "$MACOS_CURRENT_STATE"
    expected_dataset="$(macos_json_get "$MACOS_CURRENT_STATE" datasetId 2>/dev/null || true)"
    expected_host="$(macos_json_get "$MACOS_CURRENT_STATE" hostId 2>/dev/null || true)"
    expected_generation="$(macos_json_get "$MACOS_CURRENT_STATE" writerGeneration 2>/dev/null || true)"
    [[ "$fence_dataset" == "$expected_dataset" && "$fence_host" == "$expected_host" && "$fence_generation" == "$expected_generation" ]] || macos_die "released writer fence identity does not match protected current state"
  fi
}

macos_assert_no_pending_cutover_start() {
  # A source fence lives in the source database while the target transfers a
  # restored clone.  Releasing that old source row cannot by itself prove a
  # cutback, so the protected prepared state is also a local retirement
  # barrier.  Only a later, valid Resume generation makes it historical.
  local maintenance="${1:-0}" candidate state_path state_value dataset source_host target_host source_generation
  local rollback_kind rollback_status rollback_target rollback_generation rollback_digest
  local resume_target resume_source_generation resume_target_generation resume_generation resume_accepted resume_cutback
  local resume_terminal resume_preflight resume_activation expected actual
  local current_dataset="$MACOS_DATASET_ID" current_host="$MACOS_HOST_ID" current_generation="$MACOS_WRITER_GENERATION"
  local -a candidates staging rollback_candidates resume_candidates
  local -A seen rollback_seen resume_seen
  macos_assert_formal_writer_ready "$maintenance"
  staging=( "$MACOS_LAYOUT_STATE"/.cutover-prepared*.cutover-*.tmp(N) )
  (( ${#staging[@]} == 0 )) || macos_die "partial canonical cutover state exists; lifecycle start is retired" || return 1
  candidates=( "$MACOS_LAYOUT_STATE"/cutover-prepared*.json(N) "$MACOS_LAYOUT_STATE"/cutover-prepared*.json.sha256(N) )
  for candidate in "${candidates[@]}"; do
    state_path="$candidate"
    [[ "$state_path" == *.sha256 ]] && state_path="${state_path%.sha256}"
    case "${state_path:t}" in
      *.consumed.json|*.target-release-metadata.json) continue ;;
    esac
    [[ -z "${seen[$state_path]:-}" ]] || continue
    seen[$state_path]=1
    [[ -f "$state_path" && -f "$state_path.sha256" ]] || macos_die "canonical prepared cutover state is incomplete; lifecycle start is retired" || return 1
    macos_secure_path "$state_path"
    macos_check_checksum "$state_path"
    state_value="$(macos_json_get "$state_path" state 2>/dev/null || true)"
    if [[ "$state_value" == consumed ]]; then
      continue
    fi
    [[ "$state_value" == prepared ]] || macos_die "canonical prepared cutover state phase is invalid; lifecycle start is retired" || return 1
    dataset="$(macos_json_get "$state_path" dataset_id 2>/dev/null || true)"
    source_host="$(macos_json_get "$state_path" source_host_id 2>/dev/null || true)"
    target_host="$(macos_json_get "$state_path" target_host_id 2>/dev/null || true)"
    source_generation="$(macos_json_get "$state_path" source_writer_generation 2>/dev/null || true)"
    [[ "$dataset" =~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$' && "$source_host" =~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$' && "$target_host" =~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$' && "$source_generation" =~ '^[1-9][0-9]*$' ]] || macos_die "canonical prepared cutover identity is invalid; lifecycle start is retired" || return 1
    if [[ "$dataset" == "$current_dataset" && "$source_host" == "$current_host" ]] && (( source_generation >= current_generation )); then
      macos_die "this source host is retired by a pending cutover; only a valid cutback Resume may reopen it" || return 1
    fi
    if [[ "$target_host" == "$current_host" && "$maintenance" != 1 ]]; then
      macos_die "this target host has a pending inbound cutover; public start is forbidden before canonical acceptance" || return 1
    fi
  done

  # A rollback intent permanently supersedes the old target's Accept path.
  # The target must remain retired even if its exact owner later releases the
  # DB fence; only a newer accepted writer generation makes this tombstone
  # historical.  Recovery scripts use DB-only startup and do not need a broad
  # maintenance escape hatch here.
  rollback_candidates=(
    "$MACOS_LAYOUT_STATE"/cutover-rollback-intent-*.json(N)
    "$MACOS_LAYOUT_STATE"/cutover-rollback-intent-*.json.sha256(N)
    "$MACOS_LAYOUT_STATE"/cutover-rollback-terminal-*.json(N)
    "$MACOS_LAYOUT_STATE"/cutover-rollback-terminal-*.json.sha256(N)
  )
  for candidate in "${rollback_candidates[@]}"; do
    state_path="$candidate"
    [[ "$state_path" == *.sha256 ]] && state_path="${state_path%.sha256}"
    [[ -z "${rollback_seen[$state_path]:-}" ]] || continue
    rollback_seen[$state_path]=1
    [[ -f "$state_path" && -f "$state_path.sha256" ]] || macos_die "cutover rollback tombstone is incomplete; lifecycle start is retired" || return 1
    macos_secure_path "$state_path"
    macos_check_checksum "$state_path"
    rollback_kind="$(macos_json_get "$state_path" kind 2>/dev/null || true)"
    rollback_status="$(macos_json_get "$state_path" status 2>/dev/null || true)"
    case "$rollback_kind:$rollback_status" in
      formal-cutover-rollback-intent:intent|formal-cutover-rollback-terminal:terminal) ;;
      *) macos_die "cutover rollback tombstone phase is invalid; lifecycle start is retired" || return 1 ;;
    esac
    dataset="$(macos_json_get "$state_path" datasetId 2>/dev/null || true)"
    rollback_target="$(macos_json_get "$state_path" targetHostId 2>/dev/null || true)"
    rollback_generation="$(macos_json_get "$state_path" writerGeneration 2>/dev/null || true)"
    rollback_digest="$(macos_json_get "$state_path" acceptedStateSha256 2>/dev/null || true)"
    [[ "$dataset" =~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$' && "$rollback_target" =~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$' && "$rollback_generation" =~ '^[1-9][0-9]*$' && "$rollback_digest" =~ '^[0-9a-fA-F]{64}$' ]] || macos_die "cutover rollback tombstone identity is invalid; lifecycle start is retired" || return 1
    if [[ "$dataset" == "$current_dataset" && "$rollback_target" == "$current_host" ]] && (( rollback_generation >= current_generation )); then
      macos_die "this target host is retired by a cutover rollback; only a newer canonical cutover may reopen it" || return 1
    fi
  done

  # Resume advances the old source to N+2 before its private readiness check.
  # Keep public startup retired across that crash window.  Maintenance remains
  # loopback-only so Resume can run preflight; public start requires an exact,
  # checksummed terminal that binds both preflight and activation intent.
  resume_candidates=(
    "$MACOS_LAYOUT_STATE"/source-cutback-resume-intent-*.json(N)
    "$MACOS_LAYOUT_STATE"/source-cutback-resume-intent-*.json.sha256(N)
  )
  for candidate in "${resume_candidates[@]}"; do
    state_path="$candidate"
    [[ "$state_path" == *.sha256 ]] && state_path="${state_path%.sha256}"
    [[ -z "${resume_seen[$state_path]:-}" ]] || continue
    resume_seen[$state_path]=1
    [[ -f "$state_path" && -f "$state_path.sha256" ]] || macos_die "source cutback resume intent is incomplete; public start is retired" || return 1
    macos_secure_path "$state_path"
    macos_check_checksum "$state_path"
    [[ "$(macos_json_get "$state_path" kind 2>/dev/null || true)" == source-cutback-resume-intent && "$(macos_json_get "$state_path" status 2>/dev/null || true)" == pending ]] || macos_die "source cutback resume intent phase is invalid; public start is retired" || return 1
    dataset="$(macos_json_get "$state_path" datasetId 2>/dev/null || true)"
    source_host="$(macos_json_get "$state_path" sourceHostId 2>/dev/null || true)"
    resume_target="$(macos_json_get "$state_path" targetHostId 2>/dev/null || true)"
    resume_source_generation="$(macos_json_get "$state_path" sourceWriterGeneration 2>/dev/null || true)"
    resume_target_generation="$(macos_json_get "$state_path" targetWriterGeneration 2>/dev/null || true)"
    resume_generation="$(macos_json_get "$state_path" reconciledWriterGeneration 2>/dev/null || true)"
    resume_accepted="$(macos_json_get "$state_path" acceptedStateSha256 2>/dev/null || true)"
    resume_cutback="$(macos_json_get "$state_path" cutbackStateSha256 2>/dev/null || true)"
    [[ "$dataset" =~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$' && "$source_host" =~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$' && "$resume_target" =~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$' && "$resume_source_generation" =~ '^[1-9][0-9]*$' && "$resume_target_generation" =~ '^[1-9][0-9]*$' && "$resume_generation" =~ '^[1-9][0-9]*$' && "$resume_accepted" =~ '^[0-9a-fA-F]{64}$' && "$resume_cutback" =~ '^[0-9a-fA-F]{64}$' ]] || macos_die "source cutback resume intent identity is invalid; public start is retired" || return 1
    [[ "$resume_target_generation" == $(( resume_source_generation + 1 )) && "$resume_generation" == $(( resume_source_generation + 2 )) ]] || macos_die "source cutback resume generations are invalid; public start is retired" || return 1
    if [[ "$dataset" != "$current_dataset" || "$source_host" != "$current_host" ]] || (( resume_generation < current_generation )); then
      continue
    fi

    resume_terminal="$MACOS_LAYOUT_STATE/source-cutback-resume-terminal-${resume_accepted}.json"
    if [[ ! -e "$resume_terminal" && ! -e "$resume_terminal.sha256" ]]; then
      [[ "$maintenance" == 1 ]] && continue
      macos_die "source cutback resume readiness is pending; public start is retired" || return 1
    fi
    [[ -f "$resume_terminal" && -f "$resume_terminal.sha256" ]] || macos_die "source cutback resume terminal is incomplete; public start is retired" || return 1
    macos_secure_path "$resume_terminal"
    macos_check_checksum "$resume_terminal"
    [[ "$(macos_json_get "$resume_terminal" kind 2>/dev/null || true)" == source-cutback-resume-terminal && "$(macos_json_get "$resume_terminal" status 2>/dev/null || true)" == readiness-passed ]] || macos_die "source cutback resume terminal phase is invalid; public start is retired" || return 1
    [[ "$(macos_json_get "$resume_terminal" resumeIntentSha256 2>/dev/null || true)" == "$(macos_sha256 "$state_path")" && "$(macos_json_get "$resume_terminal" acceptedStateSha256 2>/dev/null || true)" == "$resume_accepted" && "$(macos_json_get "$resume_terminal" cutbackStateSha256 2>/dev/null || true)" == "$resume_cutback" ]] || macos_die "source cutback resume terminal state binding is invalid; public start is retired" || return 1
    [[ "$(macos_json_get "$resume_terminal" datasetId 2>/dev/null || true)" == "$dataset" && "$(macos_json_get "$resume_terminal" sourceHostId 2>/dev/null || true)" == "$source_host" && "$(macos_json_get "$resume_terminal" targetHostId 2>/dev/null || true)" == "$resume_target" && "$(macos_json_get "$resume_terminal" reconciledWriterGeneration 2>/dev/null || true)" == "$resume_generation" ]] || macos_die "source cutback resume terminal lineage is invalid; public start is retired" || return 1
    resume_preflight="$(macos_json_get "$resume_terminal" preflightPath 2>/dev/null || true)"
    resume_activation="$(macos_json_get "$resume_terminal" activationIntentPath 2>/dev/null || true)"
    [[ "$resume_preflight" == "$MACOS_LAYOUT_EVIDENCE"/* && "$resume_activation" == "$MACOS_LAYOUT_EVIDENCE"/* ]] || macos_die "source cutback resume evidence path is invalid; public start is retired" || return 1
    for expected in "$resume_preflight" "$resume_activation"; do
      [[ -f "$expected" && -f "$expected.sha256" ]] || macos_die "source cutback resume evidence is incomplete; public start is retired" || return 1
      macos_secure_path "$expected"
      macos_check_checksum "$expected"
    done
    actual="$(macos_sha256 "$resume_preflight")"
    [[ "$actual" == "$(macos_json_get "$resume_terminal" preflightSha256 2>/dev/null || true)" && "$(macos_json_get "$resume_preflight" status 2>/dev/null || true)" == passed ]] || macos_die "source cutback resume preflight binding is invalid; public start is retired" || return 1
    actual="$(macos_sha256 "$resume_activation")"
    [[ "$actual" == "$(macos_json_get "$resume_terminal" activationIntentSha256 2>/dev/null || true)" && "$(macos_json_get "$resume_activation" status 2>/dev/null || true)" == intent && "$(macos_json_get "$resume_activation" acceptedStateSha256 2>/dev/null || true)" == "$resume_accepted" && "$(macos_json_get "$resume_activation" cutbackStateSha256 2>/dev/null || true)" == "$resume_cutback" ]] || macos_die "source cutback resume activation binding is invalid; public start is retired" || return 1
  done
}

macos_assert_writer_fence_owner() {
  local release="$1" env_file="$2" project="$3" dataset_id="$4" host_id="$5" writer_generation="$6"
  local fence_json fence_active fence_dataset fence_host fence_generation
  fence_json="$(macos_operational_lock_one_shot_capture "$release" "$env_file" "$project" inspect-fence)"
  fence_active="$(print -r -- "$fence_json" | plutil -extract active raw -o - - 2>/dev/null || true)"
  fence_dataset="$(print -r -- "$fence_json" | plutil -extract datasetId raw -o - - 2>/dev/null || true)"
  fence_host="$(print -r -- "$fence_json" | plutil -extract hostId raw -o - - 2>/dev/null || true)"
  fence_generation="$(print -r -- "$fence_json" | plutil -extract writerGeneration raw -o - - 2>/dev/null || true)"
  [[ "$fence_active" == true && "$fence_dataset" == "$dataset_id" && "$fence_host" == "$host_id" && "$fence_generation" == "$writer_generation" ]] || macos_die "formal writer fence owner does not match the transferred target identity"
}

macos_claim_cutover_state() {
  # The backend portability contract owns this state transition.  Verify that
  # its canonical consumed marker and rewritten source state are both
  # checksummed before reporting acceptance; the host never fabricates a
  # cutover identity or bypasses the backend's single-use claim.
  local source_path="${1:-}" accepted_path="${2:-}" marker_path checksum_path
  local source_digest accepted_digest consumed_source_digest consumed_state_digest
  [[ -f "$source_path" && -f "$accepted_path" ]] || macos_die "cutover state is incomplete" || return 1
  macos_secure_path "$source_path"
  macos_secure_path "$accepted_path"
  [[ "$(macos_json_get "$source_path" state)" == consumed ]] || macos_die "canonical backend did not consume prepared cutover state" || return 1
  source_digest="$(macos_sha256 "$source_path")"
  accepted_digest="$(macos_sha256 "$accepted_path")"
  marker_path="${source_path}.consumed.json"
  checksum_path="${marker_path}.sha256"
  [[ -f "$marker_path" && -f "$checksum_path" ]] || macos_die "cutover consumed marker is incomplete" || return 1
  macos_check_checksum "$source_path"
  macos_check_checksum "$marker_path"
  consumed_source_digest="$(macos_json_get "$source_path" consumed_source_sha256)"
  consumed_state_digest="$(macos_json_get "$marker_path" source_sha256)"
  [[ "$consumed_source_digest" == "$consumed_state_digest" ]] || macos_die "cutover consumed marker does not match source state" || return 1
  [[ "$(macos_json_get "$marker_path" consumed_state_sha256)" == "$source_digest" ]] || macos_die "cutover consumed marker state checksum is invalid" || return 1
  [[ "$(macos_json_get "$marker_path" accepted_sha256)" == "$accepted_digest" ]] || macos_die "cutover consumed marker does not match accepted state" || return 1
  macos_secure_path "$marker_path"
  macos_secure_path "$checksum_path"
}

macos_dotenv_get() {
  local env_path="${1:-}" name="${2:-}" line key value
  [[ -f "$env_path" ]] || return 1
  [[ "$name" =~ '^[A-Z][A-Z0-9_]*$' ]] || return 1
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line%$'\r'}"
    [[ -n "${line//[[:space:]]/}" ]] || continue
    [[ "${line##[[:space:]]}" == \#* ]] && continue
    [[ "$line" == *=* ]] || continue
    key="${line%%=*}"
    key="${key##[[:space:]]}"
    key="${key%%[[:space:]]}"
    [[ "$key" == "$name" ]] || continue
    value="${line#*=}"
    print -r -- "$value"
    return 0
  done < "$env_path"
  return 1
}

macos_dotenv_set_atomic() {
  local env_path="${1:-}" name="${2:-}" value="${3:-}" line key temporary found=0
  [[ -f "$env_path" ]] || macos_die "environment file is missing" || return 1
  [[ "$name" =~ '^[A-Z][A-Z0-9_]*$' ]] || macos_die "invalid environment field" || return 1
  [[ "$value" != *$'\n'* && "$value" != *$'\r'* ]] || macos_die "environment value contains a newline" || return 1
  macos_secure_path "$env_path"
  temporary="$(mktemp "${env_path}.tmp.XXXXXX")"
  chmod 600 "$temporary"
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line%$'\r'}"
    key="${line%%=*}"
    key="${key##[[:space:]]}"
    key="${key%%[[:space:]]}"
    if [[ "$key" == "$name" ]]; then
      print -r -- "$name=$value" >> "$temporary"
      found=1
    else
      print -r -- "$line" >> "$temporary"
    fi
  done < "$env_path"
  (( found == 1 )) || {
    rm -f -- "$temporary"
    macos_die "environment field is missing: $name"
    return 1
  }
  mv -f -- "$temporary" "$env_path"
  chmod 600 "$env_path"
}

macos_json_get() {
  local json_path="${1:-}" key="${2:-}"
  macos_require_command plutil
  plutil -extract "$key" raw -o - -- "$json_path" 2>/dev/null
}

macos_json_object_get() {
  # plutil key paths treat dots as nested separators.  Backup artifact names
  # intentionally contain dots, so extract the object as XML and read its
  # exact child key instead of allowing a dotted path to select another value.
  local json_path="${1:-}" object_key="${2:-}" field_key="${3:-}" xml value
  [[ -f "$json_path" && "$json_path" == /* ]] || return 1
  [[ "$object_key" != *.* && "$object_key" != *$'\n'* && "$field_key" != *$'\n'* ]] || return 1
  xml="$(plutil -extract "$object_key" xml -o - -- "$json_path" 2>/dev/null)" || return 1
  value="$(print -r -- "$xml" | awk -v wanted="$field_key" '
    {
      line = $0
      gsub(/^[[:space:]]+|[[:space:]]+$/, "", line)
      if (line == "<key>" wanted "</key>") {
        while (getline line > 0) {
          gsub(/^[[:space:]]+|[[:space:]]+$/, "", line)
          if (line ~ /^<string>/) {
            sub(/^<string>/, "", line)
            sub(/<\\/string>$/, "", line)
            print line
            exit
          }
        }
      }
    }')"
  [[ -n "$value" ]] || return 1
  print -r -- "$value"
}

macos_write_atomic() {
  local destination="${1:-}" content="${2:-}" temporary
  [[ -n "$destination" ]] || macos_die "destination is empty" || return 1
  [[ "$destination" == /* ]] || macos_die "destination must be absolute" || return 1
  [[ -d "${destination:h}" ]] || macos_die "destination parent is missing" || return 1
  temporary="$(mktemp "${destination}.tmp.XXXXXX")"
  print -r -- "$content" > "$temporary"
  chmod 600 "$temporary"
  mv -f -- "$temporary" "$destination"
}

macos_json_replace_atomic() {
  local json_path="${1:-}" key="${2:-}" value="${3:-}" temporary
  [[ -f "$json_path" && "$json_path" == /* ]] || macos_die "JSON target is missing" || return 1
  [[ -n "$key" && "$key" != *.* && "$key" != *$'\n'* ]] || macos_die "JSON key is invalid" || return 1
  temporary="$(mktemp "${json_path}.tmp.XXXXXX")"
  cp -p -- "$json_path" "$temporary"
  chmod 600 "$temporary"
  plutil -replace "$key" -json "$value" -- "$temporary" >/dev/null 2>&1 || {
    rm -f -- "$temporary"
    macos_die "JSON replacement failed"
    return 1
  }
  mv -f -- "$temporary" "$json_path"
  chmod 600 "$json_path"
}

macos_replace_checksum_row() {
  local sums_path="${1:-}" relative="${2:-}" digest="${3:-}" temporary
  [[ -f "$sums_path" && "$sums_path" == /* ]] || macos_die "checksum manifest is missing" || return 1
  [[ "$relative" != /* && "$relative" != *$'\n'* && "$relative" != *$'\r'* ]] || macos_die "checksum path is invalid" || return 1
  [[ "$digest" =~ '^[0-9a-fA-F]{64}$' ]] || macos_die "checksum digest is invalid" || return 1
  temporary="$(mktemp "${sums_path}.tmp.XXXXXX")"
  awk -v digest="$digest" -v relative="$relative" '
    BEGIN { replaced = 0 }
    $0 ~ "  " relative "$" { print digest "  " relative; replaced = 1; next }
    { print }
    END { if (!replaced) print digest "  " relative }
  ' "$sums_path" > "$temporary"
  chmod 600 "$temporary"
  mv -f -- "$temporary" "$sums_path"
  chmod 600 "$sums_path"
}

macos_sha256() {
  [[ -x /usr/bin/shasum ]] || macos_die "required command is unavailable: shasum" || return 1
  /usr/bin/shasum -a 256 -- "$1" | /usr/bin/awk '{print $1}'
}

macos_write_checksum() {
  local file="${1:-}" checksum_file="${1:-}.sha256" digest
  digest="$(macos_sha256 "$file")"
  [[ "$digest" =~ '^[0-9a-fA-F]{64}$' ]] || macos_die "SHA-256 calculation failed" || return 1
  macos_write_atomic "$checksum_file" "$digest  ${file:t}"
  chmod 600 "$checksum_file"
}

macos_check_checksum() {
  local file="${1:-}" checksum_file="${1:-}.sha256" expected actual name
  [[ -f "$file" && -f "$checksum_file" ]] || macos_die "checksummed artifact is missing" || return 1
  read -r expected name < "$checksum_file" || macos_die "checksum file is invalid" || return 1
  actual="$(macos_sha256 "$file")"
  [[ "$expected" == "$actual" && "$name" == "${file:t}" ]] || macos_die "checksum validation failed" || return 1
}

macos_checksummed_json() {
  local json_path="${1:-}"
  macos_require_command plutil
  plutil -convert json -o - -- "$json_path" >/dev/null 2>&1 || macos_die "evidence JSON is invalid" || return 1
  macos_write_checksum "$json_path"
}

macos_write_evidence() {
  local directory="${1:-}" name="${2:-}" json="${3:-}" evidence_path attempt=0
  [[ -d "$directory" ]] || mkdir -p -- "$directory"
  chmod 700 "$directory"
  # Seconds-only names made two same-second operations overwrite evidence.
  # Include the process and a random suffix, and refuse an existing pair so a
  # retry cannot silently replace a previous checksummed artifact.
  while :; do
    evidence_path="$directory/${name}-$(macos_timestamp)-$$-$RANDOM.json"
    [[ ! -e "$evidence_path" && ! -e "$evidence_path.sha256" ]] && break
    (( attempt += 1 ))
    (( attempt < 20 )) || macos_die "unable to allocate a unique evidence path"
  done
  macos_write_atomic "$evidence_path" "$json"
  macos_checksummed_json "$evidence_path"
  print -r -- "$evidence_path"
}

macos_json_escape() {
  # Values passed to the small shell-generated evidence records are restricted
  # to identity/path fields.  Escape the two JSON metacharacters and reject
  # control characters instead of allowing malformed or injected JSON.
  local value="${1:-}"
  [[ "$value" != *$'\n'* && "$value" != *$'\r'* && "$value" != *$'\t'* ]] || {
    macos_die "JSON value contains a control character"
    return 1
  }
  value="${value//\\/\\\\}"
  value="${value//\"/\\\"}"
  print -r -- "$value"
}

macos_redact_file() {
  local source="${1:-}" destination="${2:-}"
  sed -E \
    -e 's/(authorization|x-admin-token|token|password|passwd|secret|otp|smtp_password)([[:space:]]*[:=][[:space:]]*)(Bearer[[:space:]]+)?[^,[:space:]}]+/\1\2[REDACTED]/Ig' \
    -e 's/(Bearer[[:space:]]+)[^[:space:]]+/\1[REDACTED]/Ig' \
    -e 's#(postgres(ql)?://)[^[:space:]]+#\1[REDACTED]#Ig' \
    -e 's/[[:alnum:]._%+-]+@[[:alnum:].-]+\.[A-Za-z]{2,}/[REDACTED_EMAIL]/g' \
    -e 's/(phone|mobile|telephone)([[:space:]]*[:=][[:space:]]*)[0-9+() -]{7,}/\1\2[REDACTED_PHONE]/Ig' \
    -e 's/(sql|query|params)([[:space:]]*[:=][[:space:]]*).*/\1\2[REDACTED]/Ig' \
    -e 's/(name|employee[_-]?no|phone[_-]?suffix|sql|query|params|traceback|stacktrace)([[:space:]]*[:=][[:space:]]*)("[^"]*"|[^,}[:space:]]*)/\1\2[REDACTED]/Ig' \
    -- "$source" > "$destination"
  chmod 600 "$destination"
}

macos_release_state() {
  local state_path="${1:-}"
  [[ -f "$state_path" ]] || macos_die "release state is missing" || return 1
  macos_secure_path "$state_path"
  typeset -g MACOS_STATE_VERSION="$(macos_json_get "$state_path" applicationVersion)"
  typeset -g MACOS_STATE_COMMIT="$(macos_json_get "$state_path" gitCommit)"
  typeset -g MACOS_STATE_PATH="$(macos_json_get "$state_path" path)"
  typeset -g MACOS_STATE_BACKUP=""
  if MACOS_STATE_BACKUP="$(macos_json_get "$state_path" pairedBackupPath 2>/dev/null)"; then :; else MACOS_STATE_BACKUP=""; fi
  [[ "$MACOS_STATE_PATH" == /* && -d "$MACOS_STATE_PATH" ]] || macos_die "release state path is invalid" || return 1
  [[ "$MACOS_STATE_COMMIT" =~ '^[0-9a-fA-F]{40}$' ]] || macos_die "release state commit is invalid" || return 1
}

macos_formal_writer_bootstrap_intent_path() {
  print -r -- "$MACOS_LAYOUT_STATE/formal-writer-bootstrap-intent.json"
}

macos_formal_writer_activation_intent_path() {
  print -r -- "$MACOS_LAYOUT_STATE/formal-writer-activation-intent.json"
}

macos_formal_writer_activation_terminal_path() {
  print -r -- "$MACOS_LAYOUT_STATE/formal-writer-activation-terminal.json"
}

macos_formal_writer_lineage_path() {
  # The generation-1 activation terminal is a permanent commissioning proof.
  # Keep its immutable binding separate from current-release.json so ordinary
  # Promote/Rollback may move the running release without re-signing the
  # original activation evidence.
  print -r -- "$MACOS_LAYOUT_STATE/formal-writer-lineage.json"
}

macos_assert_formal_writer_ready() {
  # A prepared generation-1 writer is a private maintenance target until a
  # checksummed activation terminal binds the exact intent/current state.  No
  # public lifecycle, LaunchAgent, promotion, or backup path may infer
  # readiness from bootstrapPending=false alone.
  local maintenance="${1:-0}" current_path="$MACOS_CURRENT_STATE"
  local intent_path activation_intent terminal_path phase_path lineage_path pending activation_status
  local intent_digest current_digest dataset_id host_id generation lineage_generation lineage_terminal_sha
  [[ "$maintenance" == 0 || "$maintenance" == 1 ]] || macos_die "writer readiness mode is invalid" || return 1
  intent_path="$(macos_formal_writer_bootstrap_intent_path)"
  activation_intent="$(macos_formal_writer_activation_intent_path)"
  terminal_path="$(macos_formal_writer_activation_terminal_path)"
  lineage_path="$(macos_formal_writer_lineage_path)"
  phase_path="$MACOS_LAYOUT_STATE/formal-writer-activation-phase.json"

  # A half current sidecar is never repaired by a public start.  The
  # commissioning command owns derived-sidecar repair after exact intent
  # validation; ordinary lifecycle paths stop before Docker is touched.
  if [[ -e "$current_path" || -e "$current_path.sha256" ]]; then
    [[ -f "$current_path" && -f "$current_path.sha256" ]] || macos_die "formal writer current state is incomplete; public start is blocked" || return 1
    macos_secure_path "$current_path"
    macos_check_checksum "$current_path"
    pending="$(macos_json_get "$current_path" bootstrapPending 2>/dev/null || true)"
    if [[ "$pending" == true && "$maintenance" != 1 ]]; then
      macos_die "formal writer bootstrap is pending; public start is blocked until activation terminal evidence"
      return 1
    fi
    if [[ -n "$pending" && "$pending" != true && "$pending" != false ]]; then
      macos_die "formal writer bootstrapPending value is invalid"
      return 1
    fi
  fi

  # An activation intent is durable before ownership changes.  If a process
  # dies after changing the release/current state but before writing its
  # terminal record, ordinary startup remains retired.  Maintenance may
  # inspect/resume the intent, but it cannot silently expose the target.
  if [[ -e "$activation_intent" || -e "$activation_intent.sha256" ]]; then
    [[ -f "$activation_intent" && -f "$activation_intent.sha256" ]] || macos_die "formal writer activation intent is incomplete; public start is blocked" || return 1
    macos_secure_path "$activation_intent"
    macos_check_checksum "$activation_intent"
    [[ "$(macos_json_get "$activation_intent" kind 2>/dev/null || true)" == formal-writer-activation-intent && "$(macos_json_get "$activation_intent" status 2>/dev/null || true)" == intent ]] || macos_die "formal writer activation intent phase is invalid; public start is blocked" || return 1
    if [[ "$maintenance" != 1 ]]; then
      [[ -f "$terminal_path" && -f "$terminal_path.sha256" ]] || macos_die "formal writer activation terminal evidence is missing; public start is blocked" || return 1
    fi
  fi

  if [[ -e "$terminal_path" || -e "$terminal_path.sha256" ]]; then
    [[ -f "$activation_intent" && -f "$activation_intent.sha256" && -f "$terminal_path" && -f "$terminal_path.sha256" && -f "$phase_path" && -f "$phase_path.sha256" && -f "$lineage_path" && -f "$lineage_path.sha256" ]] || macos_die "formal writer activation terminal binding is incomplete; public start is blocked" || return 1
    macos_secure_path "$terminal_path"
    macos_check_checksum "$terminal_path"
    macos_secure_path "$phase_path"
    macos_check_checksum "$phase_path"
    macos_secure_path "$lineage_path"
    macos_check_checksum "$lineage_path"
    [[ "$(macos_json_get "$phase_path" kind 2>/dev/null || true)" == formal-writer-activation-phase && "$(macos_json_get "$phase_path" phase 2>/dev/null || true)" == terminal && "$(macos_json_get "$terminal_path" phaseSha256 2>/dev/null || true)" == "$(macos_sha256 "$phase_path")" ]] || macos_die "formal writer activation terminal phase binding is stale; public start is blocked" || return 1
    [[ "$(macos_json_get "$terminal_path" kind 2>/dev/null || true)" == formal-writer-activation-terminal && "$(macos_json_get "$terminal_path" status 2>/dev/null || true)" == passed ]] || macos_die "formal writer activation terminal is not passed; public start is blocked" || return 1
    intent_digest="$(macos_sha256 "$activation_intent")"
    [[ "$(macos_json_get "$terminal_path" activationIntentSha256 2>/dev/null || true)" == "$intent_digest" ]] || macos_die "formal writer activation terminal is not bound to the exact intent; public start is blocked" || return 1
    bootstrap_intent_path="$(macos_formal_writer_bootstrap_intent_path)"
    [[ -f "$bootstrap_intent_path" && -f "$bootstrap_intent_path.sha256" ]] || macos_die "formal writer bootstrap intent is missing; public start is blocked" || return 1
    macos_check_checksum "$bootstrap_intent_path"
    [[ "$(macos_json_get "$activation_intent" bootstrapIntentSha256 2>/dev/null || true)" == "$(macos_sha256 "$bootstrap_intent_path")" ]] || macos_die "formal writer activation intent is not bound to the bootstrap reservation; public start is blocked" || return 1
    [[ "$(macos_json_get "$activation_intent" releasePath 2>/dev/null || true)" == "$(macos_json_get "$terminal_path" releasePath 2>/dev/null || true)" ]] || macos_die "formal writer activation release is not bound to the immutable terminal proof; public start is blocked" || return 1
    [[ "$(macos_json_get "$lineage_path" kind 2>/dev/null || true)" == formal-writer-lineage && "$(macos_json_get "$lineage_path" status 2>/dev/null || true)" == commissioned ]] || macos_die "formal writer lineage record is invalid; public start is blocked" || return 1
    lineage_terminal_sha="$(macos_json_get "$lineage_path" activationTerminalSha256 2>/dev/null || true)"
    [[ "$lineage_terminal_sha" == "$(macos_sha256 "$terminal_path")" ]] || macos_die "formal writer lineage terminal binding is stale; public start is blocked" || return 1
    [[ "$(macos_json_get "$lineage_path" activationIntentSha256 2>/dev/null || true)" == "$intent_digest" && "$(macos_json_get "$lineage_path" activationPhaseSha256 2>/dev/null || true)" == "$(macos_sha256 "$phase_path")" && "$(macos_json_get "$lineage_path" bootstrapIntentSha256 2>/dev/null || true)" == "$(macos_sha256 "$bootstrap_intent_path")" ]] || macos_die "formal writer lineage evidence binding is stale; public start is blocked" || return 1
    [[ "$(macos_json_get "$lineage_path" datasetId 2>/dev/null || true)" == "$(macos_json_get "$terminal_path" datasetId 2>/dev/null || true)" && "$(macos_json_get "$lineage_path" hostId 2>/dev/null || true)" == "$(macos_json_get "$terminal_path" hostId 2>/dev/null || true)" && "$(macos_json_get "$lineage_path" writerGeneration 2>/dev/null || true)" == "$(macos_json_get "$terminal_path" writerGeneration 2>/dev/null || true)" ]] || macos_die "formal writer lineage commissioning identity is invalid; public start is blocked" || return 1
    [[ "$(macos_json_get "$lineage_path" initialCurrentStateSha256 2>/dev/null || true)" == "$(macos_json_get "$terminal_path" currentStateSha256 2>/dev/null || true)" && "$(macos_json_get "$lineage_path" initialReleasePath 2>/dev/null || true)" == "$(macos_json_get "$terminal_path" releasePath 2>/dev/null || true)" ]] || macos_die "formal writer lineage initial release binding is invalid; public start is blocked" || return 1
    if [[ -f "$current_path" ]]; then
      dataset_id="$(macos_json_get "$current_path" datasetId 2>/dev/null || true)"
      host_id="$(macos_json_get "$current_path" hostId 2>/dev/null || true)"
      generation="$(macos_json_get "$current_path" writerGeneration 2>/dev/null || true)"
      [[ "$dataset_id" =~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$' && "$host_id" =~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$' && "$generation" =~ '^[1-9][0-9]*$' ]] || macos_die "formal writer current state identity is invalid; public start is blocked" || return 1
      lineage_generation="$(macos_json_get "$lineage_path" writerGeneration 2>/dev/null || true)"
      [[ "$lineage_generation" =~ '^[1-9][0-9]*$' ]] && (( generation >= lineage_generation )) || macos_die "formal writer current generation regressed behind the immutable commissioning lineage; public start is blocked" || return 1
      # If the protected host identity is available, bind the current
      # release to it.  The immutable generation-1 lineage remains the
      # commissioning proof; a later legal cutover may advance generation (or
      # host) without rewriting that proof.
      if [[ -f "$MACOS_LAYOUT_STATE/host-identity.json" && -f "$MACOS_LAYOUT_STATE/host-identity.json.sha256" ]]; then
        macos_read_cutover_identity
        [[ "$dataset_id" == "$MACOS_DATASET_ID" && "$host_id" == "$MACOS_HOST_ID" && "$generation" == "$MACOS_WRITER_GENERATION" ]] || macos_die "formal writer current state identity does not match the protected host identity; public start is blocked" || return 1
      fi
      [[ "$(macos_json_get "$current_path" bootstrapPending 2>/dev/null || true)" == false && "$(macos_json_get "$current_path" activationReady 2>/dev/null || true)" == true ]] || macos_die "formal writer current state is not public-ready; public start is blocked" || return 1
      [[ "$generation" == 1 || "$generation" =~ '^[2-9][0-9]*$' ]] || macos_die "formal writer activation terminal generation is invalid" || return 1
    fi
  fi
}

macos_assert_project_name() {
  local kind="${1:-}" project="${2:-}"
  case "$kind" in
    formal) [[ "$project" == "$MACOS_FORMAL_PROJECT" ]] ;;
    development) [[ "$project" == "$MACOS_DEV_PROJECT" ]] ;;
    staging) [[ "$project" =~ '^internal-exam-staging-[0-9a-fA-F]{12}$' ]] ;;
    restore) [[ "$project" =~ '^internal-exam-restore-verify-[a-z0-9][a-z0-9-]{2,62}$' ]] ;;
    *) false ;;
  esac || macos_die "unsafe or ambiguous Compose project name: $project"
}

macos_assert_backup() {
  local backup_path="$(macos_resolve_path "$1")"
  [[ "$backup_path" != */Docker.raw && "$backup_path" != */docker.raw ]] || macos_die "raw Docker Desktop disks are not migration artifacts" || return 1
  [[ -d "$backup_path" ]] || macos_die "backup directory is missing" || return 1
  macos_docker_ready
  print -r -- "$backup_path"
}

macos_assert_cutover_backup_binding() {
  # Bind the bytes restored by Accept-HostCutover to the exact five-artifact
  # identity emitted by canonical host portability.  A basename, manifest
  # self-check, or second-copy location alone is insufficient: every byte and
  # every expected artifact must match the prepared state before restore.
  local backup_path="$(macos_resolve_path "$1")" prepared_path="$(macos_resolve_path "$2")"
  local artifact expected actual entry
  typeset -a expected_artifacts entries
  expected_artifacts=(database.dump learning_media.tar.gz manifest.json SHA256SUMS SUCCESS)
  [[ -d "$backup_path" && ! -L "$backup_path" ]] || macos_die "portable backup directory is invalid" || return 1
  macos_secure_path "$prepared_path"
  macos_check_checksum "$prepared_path"
  for artifact in "${expected_artifacts[@]}"; do
    entry="$backup_path/$artifact"
    [[ -f "$entry" && ! -L "$entry" ]] || macos_die "portable backup artifact is missing or not a regular file" || return 1
    expected="$(macos_json_object_get "$prepared_path" backup_artifact_sha256 "$artifact" 2>/dev/null || true)"
    [[ "$expected" =~ '^[0-9a-fA-F]{64}$' ]] || macos_die "prepared portable backup identity is incomplete" || return 1
    actual="$(macos_sha256 "$entry")"
    [[ "$actual" == "${expected:l}" ]] || macos_die "portable backup artifact does not match prepared identity" || return 1
  done
  entries=( "$backup_path"/*(N) "$backup_path"/.[!.]*(N) )
  for entry in "${entries[@]}"; do
    [[ -e "$entry" || -L "$entry" ]] || continue
    artifact="${entry:t}"
    case "$artifact" in
      database.dump|learning_media.tar.gz|manifest.json|SHA256SUMS|SUCCESS) ;;
      *) macos_die "portable backup contains an unexpected artifact"; return 1 ;;
    esac
  done
}

macos_formal_value() {
  local name="${1:-}" value
  [[ "$name" =~ '^[A-Z][A-Z0-9_]*$' ]] || macos_die "invalid formal configuration field" || return 1
  value="$(macos_dotenv_get "$MACOS_FORMAL_ENV" "$name" 2>/dev/null || true)"
  [[ -n "$value" ]] || macos_die "formal configuration field is missing: $name" || return 1
  print -r -- "$value"
}

macos_active_operator_subject() {
  # Exactly one operator may perform a mutable audit action.  The enabled
  # backup operator replaces the primary for backups, restore drills, and
  # session closure; callers record this value in the backend evidence.
  local enabled
  enabled="$(macos_formal_value BACKUP_OPERATOR_ENABLED)"
  if [[ "$enabled" == true ]]; then
    macos_formal_value BACKUP_OPERATOR_USERNAME
  elif [[ "$enabled" == false ]]; then
    macos_formal_value PRIMARY_OPERATOR_USERNAME
  else
    macos_die "backup operator enablement is invalid"
  fi
}

macos_active_operator_password() {
  local enabled
  enabled="$(macos_formal_value BACKUP_OPERATOR_ENABLED)"
  if [[ "$enabled" == true ]]; then
    macos_formal_value BACKUP_OPERATOR_PASSWORD
  elif [[ "$enabled" == false ]]; then
    macos_formal_value PRIMARY_OPERATOR_PASSWORD
  else
    macos_die "backup operator enablement is invalid"
  fi
}

macos_assert_second_copy_storage() {
  local storage_path="$(macos_resolve_path "${1:-}")" evidence_path checked_at evidence_path_value mount_point mounted encrypted writable device_id whole_device_id formal_whole_device_id live_device disk_info formal_disk_info diskutil_whole diskutil_formal_whole
  [[ -d "$storage_path" ]] || macos_die "encrypted second-copy mount is missing" || return 1
  [[ -f "$storage_path/.internal-exam-encrypted-storage" ]] || macos_die "encrypted second-copy marker is missing" || return 1
  evidence_path="$MACOS_LAYOUT_EVIDENCE/second-copy-storage.json"
  [[ -f "$evidence_path" && -f "$evidence_path.sha256" ]] || macos_die "checksummed second-copy storage evidence is missing" || return 1
  macos_check_checksum "$evidence_path"
  [[ "$(macos_json_get "$evidence_path" status 2>/dev/null || true)" == passed ]] || macos_die "second-copy storage evidence is not passed" || return 1
  evidence_path_value="$(macos_json_get "$evidence_path" path 2>/dev/null || macos_json_get "$evidence_path" mountPoint 2>/dev/null || true)"
  [[ "$evidence_path_value" == "$storage_path" ]] || macos_die "second-copy evidence path does not match configured storage" || return 1
  mount_point="$(macos_json_get "$evidence_path" mountPoint 2>/dev/null || true)"
  mounted="$(macos_json_get "$evidence_path" mounted 2>/dev/null || true)"
  encrypted="$(macos_json_get "$evidence_path" encrypted 2>/dev/null || true)"
  writable="$(macos_json_get "$evidence_path" writable 2>/dev/null || true)"
  device_id="$(macos_json_get "$evidence_path" deviceId 2>/dev/null || macos_json_get "$evidence_path" device_id 2>/dev/null || true)"
  whole_device_id="$(macos_json_get "$evidence_path" wholeDeviceId 2>/dev/null || true)"
  formal_whole_device_id="$(macos_json_get "$evidence_path" formalWholeDeviceId 2>/dev/null || true)"
  [[ "$mount_point" == "$storage_path" && "$mounted" == true && "$encrypted" == true && "$writable" == true && -n "$device_id" && -n "$whole_device_id" && -n "$formal_whole_device_id" && "$whole_device_id" != "$formal_whole_device_id" ]] || macos_die "second-copy evidence lacks mounted encrypted writable distinct-device proof" || return 1
  checked_at="$(macos_json_get "$evidence_path" checkedAt 2>/dev/null || macos_json_get "$evidence_path" checked_at 2>/dev/null || true)"
  macos_assert_fresh_timestamp "$checked_at"
  live_device="$(df -P "$storage_path" | tail -n 1 | awk '{print $1}')"
  [[ -n "$live_device" && "$live_device" == "$device_id" ]] || macos_die "second-copy live device does not match checksummed evidence" || return 1
  if command -v diskutil >/dev/null 2>&1; then
    disk_info="$(macos_mktemp internal-exam-disk-info.XXXXXX)"
    formal_disk_info="$(macos_mktemp internal-exam-formal-disk-info.XXXXXX)"
    if ! diskutil info -plist "$storage_path" > "$disk_info" 2>/dev/null || ! diskutil info -plist "$MACOS_LAYOUT_ROOT" > "$formal_disk_info" 2>/dev/null; then
      rm -f -- "$disk_info" "$formal_disk_info"
      macos_die "diskutil cannot verify the second-copy mount" || return 1
    fi
    [[ "$(plutil -extract MountPoint raw -o - -- "$disk_info" 2>/dev/null || true)" == "$storage_path" ]] || { rm -f -- "$disk_info" "$formal_disk_info"; macos_die "diskutil mount point does not match second-copy evidence"; return 1; }
    diskutil_encrypted="$(plutil -extract Encryption raw -o - -- "$disk_info" 2>/dev/null || true)"
    diskutil_filevault="$(plutil -extract FileVault raw -o - -- "$disk_info" 2>/dev/null || true)"
    diskutil_writable="$(plutil -extract WritableVolume raw -o - -- "$disk_info" 2>/dev/null || true)"
    diskutil_whole="$(plutil -extract ParentWholeDisk raw -o - -- "$disk_info" 2>/dev/null || true)"
    diskutil_formal_whole="$(plutil -extract ParentWholeDisk raw -o - -- "$formal_disk_info" 2>/dev/null || true)"
    [[ "$diskutil_encrypted" == true || "$diskutil_encrypted" == 1 || "$diskutil_filevault" == true || "$diskutil_filevault" == 1 ]] || { rm -f -- "$disk_info" "$formal_disk_info"; macos_die "diskutil does not prove encrypted second-copy storage"; return 1; }
    [[ "$diskutil_writable" == true || "$diskutil_writable" == 1 ]] || { rm -f -- "$disk_info" "$formal_disk_info"; macos_die "diskutil does not prove writable second-copy storage"; return 1; }
    [[ "/dev/$diskutil_whole" == "$whole_device_id" && "/dev/$diskutil_formal_whole" == "$formal_whole_device_id" && "$diskutil_whole" != "$diskutil_formal_whole" ]] || { rm -f -- "$disk_info" "$formal_disk_info"; macos_die "live diskutil identities do not match distinct second-copy evidence"; return 1; }
    rm -f -- "$disk_info" "$formal_disk_info"
  fi
}

macos_require_formal_paths() {
  # The backend host-portability CLI is the canonical policy check.  The
  # shell performs only the protected-root boundary before delegating the
  # complete, distinct-path contract to the selected release image.
  local lifecycle backup evidence second_copy release_path
  lifecycle="$(macos_formal_value INTERNAL_EXAM_LIFECYCLE_HOST_DIR)"
  backup="$(macos_formal_value INTERNAL_EXAM_BACKUP_HOST_DIR)"
  evidence="$(macos_formal_value INTERNAL_EXAM_EVIDENCE_HOST_DIR)"
  second_copy="$(macos_formal_value SECOND_COPY_PATH)"
  local -a path_values
  path_values=("$lifecycle" "$backup" "$evidence" "$second_copy")
  for value in "$lifecycle" "$backup" "$evidence" "$second_copy"; do
    [[ "$value" == /* ]] || macos_die "formal host paths must be absolute" || return 1
    macos_assert_outside_worktree "$value" >/dev/null
  done
  [[ "$lifecycle" == "$MACOS_LAYOUT_LIFECYCLE" ]] || macos_die "formal lifecycle path must be the canonical protected lifecycle directory" || return 1
  [[ "$backup" == "$MACOS_LAYOUT_BACKUPS" ]] || macos_die "formal backup path must be the canonical protected backup directory" || return 1
  [[ "$evidence" == "$MACOS_LAYOUT_EVIDENCE" ]] || macos_die "formal evidence path must be the canonical protected evidence directory" || return 1
  [[ "$second_copy" != "$MACOS_LAYOUT_ROOT" && "$second_copy" != "$MACOS_LAYOUT_ROOT"/* && "$MACOS_LAYOUT_ROOT" != "$second_copy"/* ]] || macos_die "encrypted second-copy path must be outside the protected formal root" || return 1
  [[ "$second_copy" != "$lifecycle" && "$second_copy" != "$backup" && "$second_copy" != "$evidence" ]] || macos_die "encrypted second-copy path must be distinct" || return 1
  [[ "${path_values[1]}" != "${path_values[2]}" && "${path_values[1]}" != "${path_values[3]}" && "${path_values[1]}" != "${path_values[4]}" && "${path_values[2]}" != "${path_values[3]}" && "${path_values[2]}" != "${path_values[4]}" && "${path_values[3]}" != "${path_values[4]}" ]] || macos_die "formal host paths must be distinct" || return 1
  if [[ -n "${1:-}" ]]; then
    release_path="$(macos_resolve_path "$1")"
  else
    [[ -f "$MACOS_CURRENT_STATE" ]] || macos_die "release state is required for canonical formal path validation" || return 1
    release_path="$(macos_json_get "$MACOS_CURRENT_STATE" path 2>/dev/null || true)"
  fi
  [[ "$release_path" == /* && -d "$release_path" ]] || macos_die "release state path is invalid" || return 1
  macos_docker_ready
  [[ -x "$MACOS_OPS_SCRIPT_DIR/Test-ReleaseBundle.zsh" ]] || macos_die "release verifier is missing"
  "$MACOS_OPS_SCRIPT_DIR/Test-ReleaseBundle.zsh" --release-path "$release_path" >/dev/null
  path_backend_image="$(macos_json_get "$release_path/ops/release/built-image-identity.json" images.backend.reference 2>/dev/null || true)"
  [[ "$path_backend_image" == *":$(macos_json_get "$release_path/release-manifest.json" gitCommit | tr '[:upper:]' '[:lower:]')" ]] || macos_die "path validation backend image is not the selected release image"
  # Path validation is a host-portability policy check, not an application
  # service operation.  Use a plain selected backend-image one-shot so a
  # pre-cutover validation cannot create or touch formal Compose named
  # volumes before the fresh-volume override is installed.
  macos_run_checked docker run --rm "$path_backend_image" \
    uv run --no-sync python -m app.ops.host_portability validate-paths \
    --development-root "${MACOS_OPS_SCRIPT_DIR:h:h}" \
    --formal-root "$MACOS_LAYOUT_ROOT" \
    --lifecycle "$lifecycle" --backup "$backup" --evidence "$evidence" --second-copy "$second_copy"
}

macos_release_manifest() {
  local release="$(macos_resolve_path "$1")"
  local manifest="$release/release-manifest.json"
  [[ -f "$manifest" ]] || macos_die "release manifest is missing" || return 1
  macos_json_get "$manifest" "$2"
}

macos_verify_built_image_identity() {
  local release="$(macos_resolve_path "$1")" manifest identity identity_status commit image_name reference expected_id actual_id image_os image_arch repo_tags
  manifest="$release/release-manifest.json"
  identity="$release/ops/release/built-image-identity.json"
  [[ -f "$manifest" && -f "$identity" ]] || macos_die "built image identity is missing" || return 1
  macos_check_checksum "$identity"
  identity_status="$(macos_json_get "$identity" status 2>/dev/null || true)"
  [[ "$identity_status" == passed ]] || macos_die "release built image identity is not passed" || return 1
  commit="$(macos_json_get "$manifest" gitCommit)"
  [[ "$(macos_json_get "$identity" gitCommit)" == "${commit:l}" ]] || macos_die "built image identity commit does not match release" || return 1
  [[ "$(macos_json_get "$identity" platform)" == linux/arm64 ]] || macos_die "built image identity platform is invalid" || return 1
  backend_reference="$(macos_json_get "$identity" images.backend.reference)"
  [[ "$backend_reference" == *-backend:* ]] || macos_die "built backend image repository is invalid" || return 1
  typeset -gx APP_IMAGE_REPOSITORY="${backend_reference%:*}"
  typeset -g APP_IMAGE_REPOSITORY="${APP_IMAGE_REPOSITORY%-backend}"
  for image_name in db backend frontend gateway; do
    reference="$(macos_json_get "$identity" "images.$image_name.reference")"
    expected_id="$(macos_json_get "$identity" "images.$image_name.id")"
    [[ "$reference" == *":${commit:l}" && "$expected_id" =~ '^sha256:[0-9a-fA-F]{64}$' ]] || macos_die "built image identity is invalid" || return 1
    actual_id="$(macos_run_capture docker image inspect --format '{{.Id}}' "$reference")"
    image_os="$(macos_run_capture docker image inspect --format '{{.Os}}' "$reference")"
    image_arch="$(macos_run_capture docker image inspect --format '{{.Architecture}}' "$reference")"
    repo_tags="$(macos_run_capture docker image inspect --format '{{json .RepoTags}}' "$reference")"
    [[ "$actual_id" == "$expected_id" && "$image_os" == linux && "$image_arch" == arm64 && "$repo_tags" == *"\"$reference\""* ]] || macos_die "built image identity does not match the local image" || return 1
    [[ "$(macos_json_get "$manifest" "imageDigests.$image_name" 2>/dev/null || true)" == "$reference" ]] || macos_die "release image manifest does not match built image identity" || return 1
  done
}

macos_cutover_identity() {
  local identity_path dataset_id host_id writer_generation host_name identity_json
  identity_path="$MACOS_LAYOUT_STATE/host-identity.json"
  if [[ -f "$identity_path" && -f "$identity_path.sha256" ]]; then
    macos_check_checksum "$identity_path"
  else
    macos_require_command openssl
    host_name="$(scutil --get LocalHostName 2>/dev/null || hostname -s 2>/dev/null || print -r -- macos-host)"
    host_name="${host_name:l}"
    host_name="${host_name//[^a-z0-9._-]/-}"
    [[ -n "$host_name" ]] || host_name=macos-host
    dataset_id="dataset-$(openssl rand -hex 16)"
    host_id="host-${host_name}-$(openssl rand -hex 4)"
    writer_generation=1
    identity_json="{\"schemaVersion\":1,\"datasetId\":\"$dataset_id\",\"hostId\":\"$host_id\",\"writerGeneration\":$writer_generation,\"lineageState\":\"unbound\"}"
    macos_write_atomic "$identity_path" "$identity_json"
    macos_write_checksum "$identity_path"
  fi
  macos_secure_path "$identity_path"
  typeset -g MACOS_DATASET_ID="$(macos_json_get "$identity_path" datasetId)"
  typeset -g MACOS_HOST_ID="$(macos_json_get "$identity_path" hostId)"
  typeset -g MACOS_WRITER_GENERATION="$(macos_json_get "$identity_path" writerGeneration)"
  [[ "$MACOS_DATASET_ID" =~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$' ]] || macos_die "dataset identity is invalid" || return 1
  [[ "$MACOS_HOST_ID" =~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$' ]] || macos_die "host identity is invalid" || return 1
  [[ "$MACOS_WRITER_GENERATION" =~ '^[1-9][0-9]*$' ]] || macos_die "writer generation is invalid" || return 1
}

macos_read_cutover_identity() {
  local identity_path="$MACOS_LAYOUT_STATE/host-identity.json"
  [[ -f "$identity_path" && -f "$identity_path.sha256" ]] || macos_die "host identity is missing" || return 1
  [[ ! -L "$identity_path" && ! -L "$identity_path.sha256" ]] || macos_die "host identity must not be a symlink" || return 1
  macos_secure_path "$identity_path"
  macos_check_checksum "$identity_path"
  typeset -g MACOS_DATASET_ID="$(macos_json_get "$identity_path" datasetId)"
  typeset -g MACOS_HOST_ID="$(macos_json_get "$identity_path" hostId)"
  typeset -g MACOS_WRITER_GENERATION="$(macos_json_get "$identity_path" writerGeneration)"
  [[ "$MACOS_DATASET_ID" =~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$' ]] || macos_die "dataset identity is invalid" || return 1
  [[ "$MACOS_HOST_ID" =~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$' ]] || macos_die "host identity is invalid" || return 1
  [[ "$MACOS_WRITER_GENERATION" =~ '^[1-9][0-9]*$' ]] || macos_die "writer generation is invalid" || return 1
}

macos_adopt_cutover_identity() {
  local dataset_id="$1" host_id="$2" writer_generation="$3" identity_path="$MACOS_LAYOUT_STATE/host-identity.json" identity_json lineage_state
  [[ "$dataset_id" =~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$' && "$host_id" =~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$' && "$writer_generation" =~ '^[1-9][0-9]*$' ]] || macos_die "cutover identity adoption values are invalid" || return 1
  macos_read_cutover_identity
  [[ "$MACOS_HOST_ID" == "$host_id" ]] || macos_die "target host identity does not match accepted cutover target" || return 1
  lineage_state="$(macos_json_get "$identity_path" lineageState 2>/dev/null || true)"
  [[ "$MACOS_DATASET_ID" == "$dataset_id" || "$lineage_state" == unbound ]] || macos_die "target host already belongs to an unrelated dataset" || return 1
  identity_json="{\"schemaVersion\":1,\"datasetId\":\"$dataset_id\",\"hostId\":\"$host_id\",\"writerGeneration\":$writer_generation,\"lineageState\":\"bound\"}"
  macos_write_atomic "$identity_path" "$identity_json"
  macos_write_checksum "$identity_path"
  macos_read_cutover_identity
}

macos_recover_derived_sidecars() {
  # A power loss can leave a valid identity/current JSON immediately before
  # its checksum sidecar is renamed.  Never infer state from a stale sidecar:
  # repair only the derived sidecar after a checksummed canonical cutover
  # binding and an exact database fence identity have both been verified.
  local release_path="${1:-}" binding_path_arg="${2:-}" expected_host_arg="${3:-}" expected_generation_arg="${4:-}" canonical_path_arg="${5:-}"
  local identity_path="$MACOS_LAYOUT_STATE/host-identity.json" current_path="$MACOS_CURRENT_STATE" binding_path="" canonical_path=""
  local identity_needs=0 current_needs=0 binding_state dataset_id expected_host expected_generation
  local identity_dataset identity_host identity_generation current_dataset current_host current_generation current_release current_version current_commit current_bootstrap
  local fence_json fence_active fence_dataset fence_host fence_generation
  [[ -n "$release_path" && -d "$release_path" ]] || macos_die "sidecar recovery release path is invalid" || return 1
  [[ -f "$identity_path" ]] || macos_die "sidecar recovery cannot verify a missing host identity" || return 1
  if ! macos_check_checksum "$identity_path" >/dev/null 2>&1; then
    identity_needs=1
  fi
  if [[ -f "$current_path" ]] && ! macos_check_checksum "$current_path" >/dev/null 2>&1; then
    current_needs=1
  fi
  (( identity_needs == 1 || current_needs == 1 )) || return 0
  macos_secure_path "$identity_path"
  plutil -convert json -o - -- "$identity_path" >/dev/null 2>&1 || macos_die "host identity JSON is invalid; sidecar recovery is refused" || return 1
  if [[ -f "$current_path" ]]; then
    macos_secure_path "$current_path"
    plutil -convert json -o - -- "$current_path" >/dev/null 2>&1 || macos_die "current release JSON is invalid; sidecar recovery is refused" || return 1
  fi
  identity_dataset="$(macos_json_get "$identity_path" datasetId 2>/dev/null || true)"
  identity_host="$(macos_json_get "$identity_path" hostId 2>/dev/null || true)"
  identity_generation="$(macos_json_get "$identity_path" writerGeneration 2>/dev/null || true)"
  [[ "$identity_dataset" =~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$' && "$identity_host" =~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$' && "$identity_generation" =~ '^[1-9][0-9]*$' ]] || macos_die "host identity fields are invalid; sidecar recovery is refused" || return 1
  if [[ -f "$current_path" ]]; then
    current_dataset="$(macos_json_get "$current_path" datasetId 2>/dev/null || true)"
    current_host="$(macos_json_get "$current_path" hostId 2>/dev/null || true)"
    current_generation="$(macos_json_get "$current_path" writerGeneration 2>/dev/null || true)"
    current_release="$(macos_json_get "$current_path" path 2>/dev/null || true)"
    current_bootstrap="$(macos_json_get "$current_path" bootstrapPending 2>/dev/null || true)"
    [[ "$current_dataset" =~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$' && "$current_host" =~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$' && "$current_generation" =~ '^[1-9][0-9]*$' && "$current_release" == "$MACOS_LAYOUT_RELEASES"/* && -d "$current_release" ]] || macos_die "current release identity is invalid; sidecar recovery is refused" || return 1
    current_commit="$(macos_json_get "$current_path" gitCommit 2>/dev/null || true)"
    current_version="$(macos_json_get "$current_path" applicationVersion 2>/dev/null || true)"
    [[ "$(macos_json_get "$current_release/release-manifest.json" gitCommit 2>/dev/null || true)" == "$current_commit" && "$(macos_json_get "$current_release/release-manifest.json" applicationVersion 2>/dev/null || true)" == "$current_version" ]] || macos_die "current release identity is not bound to its selected release" || return 1
  fi
  if [[ -n "$binding_path_arg" ]]; then
    binding_path="$(macos_resolve_path "$binding_path_arg")"
  else
    typeset -a binding_candidates
    binding_candidates=( "$MACOS_LAYOUT_STATE"/cutover-accepted-*.json(Nom[1]) )
    for candidate in "${binding_candidates[@]}"; do
      [[ -f "$candidate" && -f "$candidate.sha256" ]] || continue
      macos_check_checksum "$candidate" >/dev/null 2>&1 || continue
      [[ "$(macos_json_get "$candidate" state 2>/dev/null || true)" == accepted ]] || continue
      binding_path="$candidate"
      break
    done
  fi
  [[ -n "$binding_path" && -f "$binding_path" ]] || macos_die "no checksummed canonical cutover binding is available for sidecar recovery" || return 1
  macos_secure_path "$binding_path"
  macos_check_checksum "$binding_path"
  binding_state="$(macos_json_get "$binding_path" state 2>/dev/null || true)"
  if [[ "$binding_state" == accepted ]]; then
    dataset_id="$(macos_json_get "$binding_path" dataset_id 2>/dev/null || true)"
    expected_host="$(macos_json_get "$binding_path" target_host_id 2>/dev/null || true)"
    expected_generation="$(macos_json_get "$binding_path" target_writer_generation 2>/dev/null || true)"
    [[ "$(macos_json_get "$binding_path" target_write_accepted 2>/dev/null || true)" == false && "$(macos_json_get "$binding_path" target_exposed 2>/dev/null || true)" == false ]] || macos_die "accepted cutover binding is already exposed; sidecar repair is refused" || return 1
  elif [[ "$binding_state" == prepared-for-source-reopen ]]; then
    local cutback_source_generation cutback_target_generation
    dataset_id="$(macos_json_get "$binding_path" datasetId 2>/dev/null || true)"
    expected_host="$(macos_json_get "$binding_path" sourceHostId 2>/dev/null || true)"
    cutback_source_generation="$(macos_json_get "$binding_path" sourceWriterGeneration 2>/dev/null || true)"
    cutback_target_generation="$(macos_json_get "$binding_path" targetWriterGeneration 2>/dev/null || true)"
    expected_generation="$cutback_source_generation"
    [[ "$cutback_source_generation" =~ '^[1-9][0-9]*$' && "$cutback_target_generation" =~ '^[1-9][0-9]*$' ]] || macos_die "cutback binding generations are invalid" || return 1
    [[ "$(macos_json_get "$binding_path" targetWriteAccepted 2>/dev/null || true)" == false ]] || macos_die "pre-write cutback binding claims target writes; sidecar recovery is refused" || return 1
    [[ -n "$canonical_path_arg" ]] || macos_die "pre-write sidecar recovery requires its canonical accepted state" || return 1
    canonical_path="$(macos_resolve_path "$canonical_path_arg")"
    [[ -f "$canonical_path" ]] || macos_die "canonical accepted state for sidecar recovery is missing" || return 1
    macos_secure_path "$canonical_path"
    macos_check_checksum "$canonical_path"
    [[ "$(macos_json_get "$canonical_path" state 2>/dev/null || true)" == accepted && "$(macos_json_get "$binding_path" acceptedStateSha256 2>/dev/null || true)" == "$(macos_sha256 "$canonical_path")" ]] || macos_die "cutback binding is not tied to its canonical accepted state" || return 1
    if [[ -n "$expected_generation_arg" ]]; then
      [[ "$expected_generation_arg" == "$cutback_source_generation" || "$expected_generation_arg" == $(( cutback_target_generation + 1 )) ]] || macos_die "cutback sidecar recovery generation is not an original or reconciled generation" || return 1
      expected_generation="$expected_generation_arg"
    fi
  else
    macos_die "unsupported canonical binding for sidecar recovery" || return 1
  fi
  [[ "$dataset_id" == "$identity_dataset" && "$expected_host" == "$identity_host" && "$expected_generation" == "$identity_generation" ]] || macos_die "host identity does not match canonical cutover binding; sidecar recovery is refused" || return 1
  if [[ -f "$current_path" ]]; then
    if (( current_needs == 1 )); then
      [[ "$current_dataset" == "$dataset_id" && "$current_host" == "$expected_host" && "$current_generation" == "$expected_generation" ]] || macos_die "current release identity does not match canonical cutover binding; sidecar recovery is refused" || return 1
    elif (( identity_needs == 1 )); then
      # Identity adoption is written before current-release.  During that
      # narrow crash window the checksummed current state may still be the
      # older, same-host bootstrap release.  It is safe to preserve it for
      # the resumable caller, but never to accept a newer/different binding.
      [[ "$current_host" == "$expected_host" && ( "$current_dataset" == "$dataset_id" || "$current_bootstrap" == true ) && "$current_generation" -lt "$expected_generation" && "$current_release" == "$release_path" ]] || macos_die "older current release is not a safe derived sidecar recovery candidate" || return 1
    fi
  fi
  if [[ -n "$expected_host_arg" ]]; then
    [[ "$expected_host_arg" == "$expected_host" ]] || macos_die "requested sidecar recovery host does not match canonical binding" || return 1
  fi
  if [[ -n "$expected_generation_arg" && "$binding_state" != prepared-for-source-reopen ]]; then
    [[ "$expected_generation_arg" == "$expected_generation" ]] || macos_die "requested sidecar recovery generation does not match canonical binding" || return 1
  fi
  macos_compose "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" up -d --no-build db
  fence_json="$(macos_operational_lock_one_shot_capture "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" inspect-fence)"
  fence_active="$(print -r -- "$fence_json" | plutil -extract active raw -o - -- - 2>/dev/null || true)"
  fence_dataset="$(print -r -- "$fence_json" | plutil -extract datasetId raw -o - -- - 2>/dev/null || true)"
  fence_host="$(print -r -- "$fence_json" | plutil -extract hostId raw -o - -- - 2>/dev/null || true)"
  fence_generation="$(print -r -- "$fence_json" | plutil -extract writerGeneration raw -o - -- - 2>/dev/null || true)"
  [[ "$fence_active" == true || "$fence_active" == false ]] || macos_die "database fence state is unavailable; sidecar recovery is refused" || return 1
  [[ "$fence_dataset" == "$dataset_id" && "$fence_host" == "$expected_host" && "$fence_generation" == "$expected_generation" ]] || macos_die "database fence identity does not match canonical cutover binding; sidecar recovery is refused" || return 1
  if (( current_needs == 1 )); then
    macos_write_checksum "$current_path"
  fi
  if (( identity_needs == 1 )); then
    macos_write_checksum "$identity_path"
  fi
  macos_check_checksum "$identity_path"
  (( current_needs == 0 )) || macos_check_checksum "$current_path"
}

macos_save_environment() {
  local name value
  typeset -ga MACOS_SAVED_ENV_NAMES MACOS_SAVED_ENV_VALUES MACOS_SAVED_ENV_SET
  MACOS_SAVED_ENV_NAMES=(); MACOS_SAVED_ENV_VALUES=(); MACOS_SAVED_ENV_SET=()
  for name in "$@"; do
    if [[ -v "${name}" ]]; then
      MACOS_SAVED_ENV_SET+=(1)
      MACOS_SAVED_ENV_VALUES+=("${(P)name}")
    else
      MACOS_SAVED_ENV_SET+=(0)
      MACOS_SAVED_ENV_VALUES+=("")
    fi
    MACOS_SAVED_ENV_NAMES+=("$name")
  done
}

macos_restore_environment() {
  local index name
  for (( index = 1; index <= ${#MACOS_SAVED_ENV_NAMES[@]}; index += 1 )); do
    name="${MACOS_SAVED_ENV_NAMES[index]}"
    if (( MACOS_SAVED_ENV_SET[index] == 1 )); then
      export "$name=${MACOS_SAVED_ENV_VALUES[index]}"
    else
      unset "$name"
    fi
  done
}

macos_rotate_log() {
  local log_path="${1:-}" max_bytes="${2:-1048576}" size
  [[ -f "$log_path" ]] || return 0
  size="$(stat -f '%z' -- "$log_path")"
  if (( size > max_bytes )); then
    mv -f -- "$log_path" "$log_path.1"
    : > "$log_path"
    chmod 600 "$log_path" "$log_path.1"
  fi
}

macos_acquire_lock() {
  local directory="${1:-}"
  [[ "$directory" == /* ]] || macos_die "lock path must be absolute" || return 1
  [[ -d "${directory:h}" ]] || macos_die "lock parent is missing" || return 1
  [[ -z "${MACOS_LOCK_PATH:-}" ]] || macos_die "operation lock is already held" || return 1
  local boot_marker current_pid current_boot stale_path
  boot_marker="$(sysctl -n kern.boottime 2>/dev/null | tr -d '[:space:]' || true)"
  if ! mkdir -- "$directory" 2>/dev/null; then
    current_pid=""
    current_boot=""
    if [[ -f "$directory/pid" ]]; then
      read -r current_pid current_boot < "$directory/pid" || true
    fi
    # A live PID from the same boot is an active operation.  If the boot
    # marker differs, or the PID is gone, quarantine only the exact lock
    # directory and retry; no recursive deletion or process termination.
    if [[ -n "$current_pid" && "$current_pid" == <-> && ( -z "$current_boot" || "$current_boot" == "$boot_marker" ) ]] && kill -0 "$current_pid" 2>/dev/null; then
      macos_die "another macOS operation is already running"
      return 1
    fi
    stale_path="${directory}.stale-$(macos_timestamp)-$$"
    if ! mv -- "$directory" "$stale_path" 2>/dev/null; then
      macos_die "another macOS operation is already running"
      return 1
    fi
    rm -f -- "$stale_path/pid"
    rmdir -- "$stale_path" 2>/dev/null || {
      macos_die "stale lock contains unexpected files"
      return 1
    }
    mkdir -- "$directory" 2>/dev/null || {
      macos_die "another macOS operation is already running"
      return 1
    }
  fi
  chmod 700 "$directory"
  print -r -- "$$ $boot_marker" > "$directory/pid"
  chmod 600 "$directory/pid"
  typeset -g MACOS_LOCK_PATH="$directory"
}

macos_release_lock() {
  local directory="${MACOS_LOCK_PATH:-}"
  [[ -n "$directory" ]] || return 0
  rm -f -- "$directory/pid"
  rmdir -- "$directory" 2>/dev/null || true
  unset MACOS_LOCK_PATH
}

macos_assert_inherited_lock() {
  local lock_path="${MACOS_LAYOUT_STATE:-}/.operation.lock" parent_pid actual_pid
  parent_pid="${MACOS_PARENT_LOCK_PID:-}"
  [[ "$parent_pid" == <-> && -f "$lock_path/pid" ]] || macos_die "inherited operation lock is missing" || return 1
  read -r actual_pid _ < "$lock_path/pid" || macos_die "inherited operation lock is invalid" || return 1
  [[ "$actual_pid" == "$parent_pid" ]] || macos_die "inherited operation lock owner changed" || return 1
  kill -0 "$parent_pid" 2>/dev/null || macos_die "inherited operation lock owner is not active" || return 1
}

# Privileged host evidence is deliberately handled as a small, immutable
# envelope.  The capture script runs as the designated (non-root) host account and
# writes ordinary owner-only files; only the three fixed read-only commands in
# Capture-PrivilegedHostEvidence.zsh are elevated.  Preflight uses the helpers
# below to re-check every byte and every host/configuration binding instead of
# trusting a caller-supplied status field.
macos_privileged_evidence_directory() {
  local directory="${1:-}"
  [[ -n "$directory" && "$directory" == /* ]] || macos_die "privileged evidence directory must be absolute" || return 1
  [[ -d "$directory" && ! -L "$directory" ]] || macos_die "privileged evidence directory is missing or a symlink" || return 1
  local resolved="${directory:A}" mode
  [[ "$resolved" == "$directory" ]] || macos_die "privileged evidence directory must be canonical" || return 1
  mode="$(/usr/bin/stat -f '%Lp' -- "$directory")"
  (( (8#$mode & 8#0777) == 8#0700 )) || macos_die "privileged evidence directory must be mode 0700" || return 1
  [[ "$(/usr/bin/stat -f '%Su' -- "$directory")" == "$(/usr/bin/id -un)" ]] || macos_die "privileged evidence directory is not owned by the current operator" || return 1
  print -r -- "$directory"
}

macos_privileged_evidence_artifact_path() {
  local directory="${1:-}" artifact="${2:-}" resolved_directory
  resolved_directory="$(macos_privileged_evidence_directory "$directory")"
  [[ "$artifact" =~ '^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$' ]] || macos_die "privileged evidence artifact name is invalid" || return 1
  print -r -- "$resolved_directory/$artifact"
}

macos_assert_privileged_evidence_artifact() {
  local directory="${1:-}" artifact="${2:-}" path sidecar mode
  path="$(macos_privileged_evidence_artifact_path "$directory" "$artifact")"
  [[ -f "$path" && ! -L "$path" ]] || macos_die "privileged evidence artifact is missing or not a regular file: $artifact" || return 1
  [[ "${path:h}" == "${directory:A}" ]] || macos_die "privileged evidence artifact escaped its protected directory" || return 1
  mode="$(/usr/bin/stat -f '%Lp' -- "$path")"
  (( (8#$mode & 8#0777) == 8#0600 )) || macos_die "privileged evidence artifact must be mode 0600: $artifact" || return 1
  [[ "$(/usr/bin/stat -f '%Su' -- "$path")" == "$(/usr/bin/id -un)" ]] || macos_die "privileged evidence artifact is not owned by the current operator" || return 1
  sidecar="$path.sha256"
  [[ -f "$sidecar" && ! -L "$sidecar" ]] || macos_die "privileged evidence artifact checksum is missing: $artifact" || return 1
  mode="$(/usr/bin/stat -f '%Lp' -- "$sidecar")"
  (( (8#$mode & 8#0777) == 8#0600 )) || macos_die "privileged evidence checksum must be mode 0600: $artifact" || return 1
  [[ "$(/usr/bin/stat -f '%Su' -- "$sidecar")" == "$(/usr/bin/id -un)" ]] || macos_die "privileged evidence checksum is not owned by the current operator" || return 1
  macos_check_checksum "$path"
  print -r -- "$path"
}

macos_privileged_evidence_fresh() {
  local timestamp="${1:-}" timestamp_epoch now_epoch
  timestamp_epoch="$(macos_epoch_from_iso "$timestamp")" || return 1
  now_epoch="$(date -u '+%s')"
  (( timestamp_epoch <= now_epoch + 300 )) || macos_die "privileged host evidence is too far in the future" || return 1
  (( now_epoch - timestamp_epoch <= 3600 )) || macos_die "privileged host evidence is stale" || return 1
}

macos_current_boot_marker_digest() {
  local marker digest
  marker="$(sysctl -n kern.boottime 2>/dev/null || sysctl kern.boottime 2>/dev/null || true)"
  [[ -n "$marker" ]] || macos_die "current boot marker is unavailable" || return 1
  digest="$(print -rn -- "$marker" | /usr/bin/shasum -a 256 | /usr/bin/awk '{print $1}')"
  [[ "$digest" =~ '^[0-9a-fA-F]{64}$' ]] || macos_die "current boot marker digest is invalid" || return 1
  print -r -- "${digest:l}"
}

macos_ipv4_in_cidr() {
  local address="${1:-}" cidr="${2:-}" base prefix
  local -a address_octets base_octets
  integer address_value base_value mask
  [[ "$address" =~ '^[0-9]{1,3}(\.[0-9]{1,3}){3}$' && "$cidr" =~ '^[0-9]{1,3}(\.[0-9]{1,3}){3}/([0-9]|[12][0-9]|3[0-2])$' ]] || return 1
  address_octets=( ${(s:.:)address} )
  base="${cidr%%/*}"
  prefix="${cidr##*/}"
  (( prefix >= 8 )) || return 1
  base_octets=( ${(s:.:)base} )
  (( ${#address_octets} == 4 && ${#base_octets} == 4 )) || return 1
  local octet
  for octet in "${address_octets[@]}" "${base_octets[@]}"; do
    [[ "$octet" =~ '^[0-9]{1,3}$' && "$octet" -le 255 ]] || return 1
  done
  address_value=$(( address_octets[1] * 16777216 + address_octets[2] * 65536 + address_octets[3] * 256 + address_octets[4] ))
  base_value=$(( base_octets[1] * 16777216 + base_octets[2] * 65536 + base_octets[3] * 256 + base_octets[4] ))
  if (( prefix == 0 )); then
    mask=0
  else
    mask=$(( (0xffffffff << (32 - prefix)) & 0xffffffff ))
  fi
  (( (address_value & mask) == (base_value & mask) ))
}

macos_privileged_manifest_common() {
  local manifest="${1:-}" expected_kind="${2:-}" expected_host="${3:-}" expected_identity_digest="${4:-}" expected_boot_digest="${5:-}" evidence_directory="${6:-$MACOS_LAYOUT_EVIDENCE}"
  local directory schema kind manifest_status checked_at host_os architecture host_id identity_digest boot_digest designated_host_account current_host_account
  [[ -f "$manifest" && ! -L "$manifest" && "$manifest" == /* ]] || macos_die "privileged host evidence manifest is missing or unsafe" || return 1
  directory="$(macos_privileged_evidence_directory "$evidence_directory")"
  [[ "${manifest:h}" == "$directory" ]] || macos_die "privileged host evidence manifest is outside the protected evidence directory" || return 1
  macos_assert_privileged_evidence_artifact "$directory" "${manifest:t}" >/dev/null
  schema="$(macos_json_get "$manifest" schemaVersion 2>/dev/null || true)"
  kind="$(macos_json_get "$manifest" kind 2>/dev/null || true)"
  manifest_status="$(macos_json_get "$manifest" status 2>/dev/null || true)"
  [[ "$schema" == 1 && "$kind" == "$expected_kind" && "$manifest_status" == passed ]] || macos_die "privileged host evidence manifest envelope is invalid" || return 1
  checked_at="$(macos_json_get "$manifest" checkedAt 2>/dev/null || macos_json_get "$manifest" checked_at 2>/dev/null || true)"
  macos_privileged_evidence_fresh "$checked_at"
  host_os="$(macos_json_get "$manifest" hostOS 2>/dev/null || macos_json_get "$manifest" host_os 2>/dev/null || true)"
  architecture="$(macos_json_get "$manifest" architecture 2>/dev/null || true)"
  host_id="$(macos_json_get "$manifest" hostId 2>/dev/null || macos_json_get "$manifest" host_id 2>/dev/null || true)"
  identity_digest="$(macos_json_get "$manifest" hostIdentitySha256 2>/dev/null || macos_json_get "$manifest" host_identity_sha256 2>/dev/null || true)"
  boot_digest="$(macos_json_get "$manifest" bootMarkerSha256 2>/dev/null || macos_json_get "$manifest" boot_marker_sha256 2>/dev/null || true)"
  [[ "$host_os" == darwin && "$architecture" == arm64 && "$host_id" == "$expected_host" && "${identity_digest:l}" == "${expected_identity_digest:l}" && "${boot_digest:l}" == "${expected_boot_digest:l}" ]] || macos_die "privileged host evidence host binding is invalid" || return 1
  designated_host_account="$(macos_json_get "$manifest" designatedHostAccount 2>/dev/null || true)"
  current_host_account="$(/usr/bin/id -un 2>/dev/null || true)"
  [[ -n "$current_host_account" && "$designated_host_account" == "$current_host_account" ]] || macos_die "privileged host evidence designated account binding is invalid" || return 1
}

macos_privileged_manifest_artifact() {
  local manifest="${1:-}" field="${2:-}" artifact directory
  artifact="$(macos_json_get "$manifest" "$field" 2>/dev/null || true)"
  [[ -n "$artifact" ]] || macos_die "privileged host evidence output artifact is missing: $field" || return 1
  directory="${manifest:h}"
  macos_assert_privileged_evidence_artifact "$directory" "$artifact"
}

macos_privileged_manifest_port() {
  local manifest="${1:-}" field="${2:-}" expected="${3:-}" value
  value="$(macos_json_get "$manifest" "$field" 2>/dev/null || true)"
  if [[ -z "$value" && "$field" == postgresPort ]]; then
    value="$(macos_json_get "$manifest" databasePort 2>/dev/null || macos_json_get "$manifest" dbPort 2>/dev/null || true)"
  fi
  [[ "$value" =~ '^[0-9]+$' && "$value" == "$expected" ]] || macos_die "privileged host evidence port binding is invalid: $field" || return 1
  (( value >= 1 && value <= 65535 )) || macos_die "privileged host evidence port is out of range: $field" || return 1
}

macos_privileged_manifest_command() {
  local manifest="${1:-}" command_field="${2:-}" exit_field="${3:-}" expected_command="${4:-}" artifact_field="${5:-}" digest_field="${6:-}" raw_path raw_digest exit_code actual_digest
  [[ "$(macos_json_get "$manifest" "$command_field" 2>/dev/null || true)" == "$expected_command" ]] || macos_die "privileged host evidence command binding is invalid: $command_field" || return 1
  exit_code="$(macos_json_get "$manifest" "$exit_field" 2>/dev/null || true)"
  [[ "$exit_code" == 0 ]] || macos_die "privileged host evidence command did not succeed: $command_field" || return 1
  raw_path="$(macos_privileged_manifest_artifact "$manifest" "$artifact_field")"
  raw_digest="$(macos_json_get "$manifest" "$digest_field" 2>/dev/null || true)"
  [[ "$raw_digest" =~ '^[0-9a-fA-F]{64}$' ]] || macos_die "privileged host evidence output digest is invalid: $digest_field" || return 1
  actual_digest="$(macos_sha256 "$raw_path")"
  [[ "${actual_digest:l}" == "${raw_digest:l}" ]] || macos_die "privileged host evidence output digest does not match: $artifact_field" || return 1
  print -r -- "$raw_path"
}

macos_pf_rule_is_pass() {
  local line="${1:-}"
  # pfctl -sr emits the action first (or after an optional @N rule index).
  # Restricting this check to the action token keeps block rules from being
  # mistaken for an allow path or a forbidden exposed service.
  print -r -- "$line" | grep -Eqi -- '^[[:space:]]*(@[0-9]+[[:space:]]+)?pass([[:space:]]|$)'
}

macos_pf_rules_prove_candidate_path() {
  local rules_path="${1:-}" approved_cidr="${2:-}" candidate_ip="${3:-}" candidate_port="${4:-}" rules line candidate_lines=0 exact_lines=0
  rules="$(< "$rules_path")"
  [[ -n "$rules" ]] || macos_die "packet-filter rules output is empty" || return 1
  while IFS= read -r line || [[ -n "$line" ]]; do
    macos_pf_rule_is_pass "$line" || continue
    # Every pass rule for the candidate port is part of the exposure set.  Do
    # not first narrow by destination: a pass-to-any rule must fail even when
    # an exact candidate rule is also present.
    if print -r -- "$line" | grep -Eq -- "(^|[^[:alnum:]_])port[^0-9]*${candidate_port}([^0-9]|$)"; then
      (( candidate_lines += 1 ))
      if print -r -- "$line" | grep -Eqi -- "(^|[^[:alnum:]_])from[[:space:]]+${approved_cidr}[[:space:]]+to[[:space:]]+${candidate_ip}([^0-9]|$)" && print -r -- "$line" | grep -Eqi -- '(^|[^[:alnum:]_])proto[[:space:]]+tcp([^[:alnum:]_]|$)'; then
        (( exact_lines += 1 ))
      fi
    fi
  done <<< "$rules"
  (( candidate_lines > 0 && candidate_lines == exact_lines )) || macos_die "packet-filter rules do not prove an exact approved candidate path" || return 1
}

macos_pf_rules_forbid_ports() {
  local rules_path="${1:-}"; shift
  local rules="$(< "$rules_path")" line port
  for port in "$@"; do
    while IFS= read -r line || [[ -n "$line" ]]; do
      macos_pf_rule_is_pass "$line" || continue
      if print -r -- "$line" | grep -Eqi -- "(^|[^[:alnum:]_])port[^0-9]*${port}([^0-9]|$)"; then
        macos_die "packet-filter rules expose a forbidden service port: $port"
        return 1
      fi
    done <<< "$rules"
  done
}

macos_network_time_output_proves_on() {
  local output="${1:-}" line
  while IFS= read -r line || [[ -n "$line" ]]; do
    if print -r -- "$line" | grep -Eqi -- '^[[:space:]]*Network[[:space:]]+Time[[:space:]]*:[[:space:]]*On[[:space:]]*$'; then
      return 0
    fi
  done <<< "$output"
  return 1
}

macos_assert_pf_evidence() {
  local manifest="${1:-}" expected_host="${2:-}" expected_identity_digest="${3:-}" expected_boot_digest="${4:-}" approved_cidr="${5:-}" candidate_ip="${6:-}" candidate_port="${7:-}" operator_port="${8:-}" postgres_port="${9:-}" frontend_port="${10:-}" backend_port="${11:-}" evidence_directory="${12:-${MACOS_LAYOUT_EVIDENCE:-${1:h}}}"
  local info_path rules_path
  macos_privileged_manifest_common "$manifest" macos-pf-export "$expected_host" "$expected_identity_digest" "$expected_boot_digest" "$evidence_directory"
  [[ "$(macos_json_get "$manifest" provider 2>/dev/null || true)" == pf ]] || macos_die "PF evidence provider binding is invalid" || return 1
  [[ "$(macos_json_get "$manifest" approvedCidr 2>/dev/null || true)" == "$approved_cidr" ]] || macos_die "PF approved CIDR binding is invalid" || return 1
  [[ "$(macos_json_get "$manifest" candidateAddress 2>/dev/null || macos_json_get "$manifest" candidateIp 2>/dev/null || true)" == "$candidate_ip" ]] || macos_die "PF candidate address binding is invalid" || return 1
  macos_ipv4_in_cidr "$candidate_ip" "$approved_cidr" || macos_die "PF candidate address is outside the approved CIDR" || return 1
  macos_privileged_manifest_port "$manifest" candidatePort "$candidate_port"
  macos_privileged_manifest_port "$manifest" operatorPort "$operator_port"
  macos_privileged_manifest_port "$manifest" postgresPort "$postgres_port"
  macos_privileged_manifest_port "$manifest" frontendPort "$frontend_port"
  macos_privileged_manifest_port "$manifest" backendPort "$backend_port"
  info_path="$(macos_privileged_manifest_command "$manifest" infoCommand infoExitCode '/usr/bin/sudo -n /sbin/pfctl -s info' infoArtifact infoOutputSha256)"
  rules_path="$(macos_privileged_manifest_command "$manifest" rulesCommand rulesExitCode '/usr/bin/sudo -n /sbin/pfctl -sr' rulesArtifact rulesOutputSha256)"
  [[ "$(< "$info_path")" != *Disabled* && ( "$(< "$info_path")" == *"Status: Enabled"* || "$(< "$info_path")" == *"Status:\ Enabled"* ) ]] || macos_die "packet filter is not enabled" || return 1
  macos_pf_rules_prove_candidate_path "$rules_path" "$approved_cidr" "$candidate_ip" "$candidate_port"
  macos_pf_rules_forbid_ports "$rules_path" "$operator_port" "$postgres_port" "$frontend_port" "$backend_port"
}

macos_assert_network_time_evidence() {
  local manifest="${1:-}" expected_host="${2:-}" expected_identity_digest="${3:-}" expected_boot_digest="${4:-}" evidence_directory="${5:-${MACOS_LAYOUT_EVIDENCE:-${1:h}}}" output_path output
  macos_privileged_manifest_common "$manifest" macos-network-time-export "$expected_host" "$expected_identity_digest" "$expected_boot_digest" "$evidence_directory"
  output_path="$(macos_privileged_manifest_command "$manifest" command exitCode '/usr/bin/sudo -n /usr/sbin/systemsetup -getusingnetworktime' outputArtifact outputSha256)"
  output="$(< "$output_path")"
  macos_network_time_output_proves_on "$output" || macos_die "network time evidence does not prove On" || return 1
}
