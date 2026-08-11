#!/bin/zsh
set -euo pipefail
setopt no_nomatch
umask 077

SCRIPT_DIR="${0:A:h}"
source "$SCRIPT_DIR/Common.zsh"

action=""
release_path=""
root="${INTERNAL_EXAM_ROOT:-${HOME:?}/Library/Application Support/InternalExam}"
run_identity=""
live_image_ids=""
canonical_output=""
health_migration_evidence=""
browser_evidence=""
smtp_evidence=""
capacity_evidence=""
restart_evidence=""
route_evidence=""
backup_restore_evidence=""

while (( $# > 0 )); do
  case "$1" in
    --action) (( $# >= 2 )) || macos_die "--action requires Up, Down, Status, or Accept"; action="$2"; shift 2 ;;
    --release-path|--release) (( $# >= 2 )) || macos_die "$1 requires a path"; release_path="$2"; shift 2 ;;
    --run-identity|--run-evidence) (( $# >= 2 )) || macos_die "$1 requires a path"; run_identity="$2"; shift 2 ;;
    --live-image-ids|--live-images) (( $# >= 2 )) || macos_die "$1 requires a path"; live_image_ids="$2"; shift 2 ;;
    --canonical-output|--acceptance-evidence) (( $# >= 2 )) || macos_die "$1 requires a path"; canonical_output="$2"; shift 2 ;;
    --health-migration-evidence) (( $# >= 2 )) || macos_die "$1 requires a path"; health_migration_evidence="$2"; shift 2 ;;
    --browser-evidence) (( $# >= 2 )) || macos_die "$1 requires a path"; browser_evidence="$2"; shift 2 ;;
    --smtp-evidence) (( $# >= 2 )) || macos_die "$1 requires a path"; smtp_evidence="$2"; shift 2 ;;
    --capacity-evidence) (( $# >= 2 )) || macos_die "$1 requires a path"; capacity_evidence="$2"; shift 2 ;;
    --restart-evidence) (( $# >= 2 )) || macos_die "$1 requires a path"; restart_evidence="$2"; shift 2 ;;
    --route-evidence) (( $# >= 2 )) || macos_die "$1 requires a path"; route_evidence="$2"; shift 2 ;;
    --backup-restore-evidence) (( $# >= 2 )) || macos_die "$1 requires a path"; backup_restore_evidence="$2"; shift 2 ;;
    --root) (( $# >= 2 )) || macos_die "--root requires a path"; root="$2"; shift 2 ;;
    -h|--help)
      print -r -- "usage: $0 --action Up|Down|Status|Accept --release-path INSTALLED_RELEASE [--run-identity PATH --live-image-ids PATH --health-migration-evidence PATH --browser-evidence PATH --smtp-evidence PATH --capacity-evidence PATH --restart-evidence PATH --route-evidence PATH --backup-restore-evidence PATH --canonical-output PATH] [--root ROOT]"
      print -r -- "Accept assembles schemaVersion=2 from all seven checksummed raw artifacts; a hand-written top-level gates JSON is not accepted."
      exit 0
      ;;
    *) macos_die "unknown argument: $1"; exit 1 ;;
  esac
done

macos_assert_macos
[[ "$action" == Up || "$action" == Down || "$action" == Status || "$action" == Accept ]] || macos_die "--action must be Up, Down, Status, or Accept"
[[ -n "$release_path" ]] || macos_die "--release-path is required"
macos_assert_outside_worktree "$root" >/dev/null
macos_layout "$root"
macos_assert_protected_configuration "$root"
macos_read_cutover_identity
macos_docker_ready

release_path="$(macos_resolve_path "$release_path")"
[[ -d "$release_path" ]] || macos_die "release directory is missing"
[[ "$release_path:h" == "$MACOS_LAYOUT_RELEASES" ]] || macos_die "staging requires an installed release under ROOT/releases/<version>"
version="${release_path:t}"
[[ "$version" != *'/'* && -n "$version" ]] || macos_die "installed release version is invalid"
"$SCRIPT_DIR/Test-ReleaseBundle.zsh" --release-path "$release_path" >/dev/null
macos_verify_built_image_identity "$release_path"
manifest="$release_path/release-manifest.json"
git_commit="$(macos_json_get "$manifest" gitCommit)"
[[ "$git_commit" =~ '^[0-9a-fA-F]{40}$' ]] || macos_die "release Git commit is invalid"
lower_commit="${git_commit:l}"
short_commit="${lower_commit[1,12]}"
staging_project="internal-exam-staging-${short_commit}"
macos_assert_project_name staging "$staging_project"
staging_host_root="$MACOS_LAYOUT_ROOT/staging/$short_commit"
staging_lifecycle="$staging_host_root/lifecycle"
staging_backup="$staging_host_root/backups"
staging_evidence="$staging_host_root/evidence"
up_started=0
up_attempted=0
up_created_run_identity=""
up_created_live_images=""
mkdir -p -- "$staging_lifecycle" "$staging_backup" "$staging_evidence"
chmod 700 "$MACOS_LAYOUT_ROOT/staging" "$staging_host_root" "$staging_lifecycle" "$staging_backup" "$staging_evidence"

macos_save_environment APP_VERSION_TAG APP_VERSION GIT_COMMIT INTERNAL_EXAM_LIFECYCLE_HOST_DIR INTERNAL_EXAM_BACKUP_HOST_DIR INTERNAL_EXAM_EVIDENCE_HOST_DIR INTERNAL_LAN_BIND_IP CANDIDATE_GATEWAY_PORT OPERATOR_GATEWAY_PORT POSTGRES_LOOPBACK_PORT FRONTEND_LOOPBACK_PORT
cleanup_staging() {
  local exit_status=$? artifact
  if (( up_attempted == 1 )) && (( exit_status != 0 )); then
    # Up may have started the isolated project before a run identity or live
    # image capture failed.  Tear down only this exact staging project and the
    # two artifacts created by this attempt; accepted durable evidence and all
    # formal state are outside these paths and are never touched here.
    macos_log "staging_up_failed cleanup=project:$staging_project"
    if ! macos_compose "$release_path" "$MACOS_STAGING_ENV" "$staging_project" down -v --remove-orphans >/dev/null 2>&1; then
      macos_log "staging_up_failed cleanup=project_failed"
    fi
    for artifact in "$up_created_run_identity" "$up_created_live_images"; do
      [[ -n "$artifact" && "$artifact" == "$staging_evidence"/* ]] || continue
      rm -f -- "$artifact" "$artifact.sha256"
    done
  fi
  macos_restore_environment
  macos_release_lock
  return "$exit_status"
}
macos_acquire_lock "$MACOS_LAYOUT_STATE/.operation.lock"
trap cleanup_staging EXIT
export APP_VERSION_TAG="$lower_commit"
export APP_VERSION="$(macos_json_get "$manifest" applicationVersion)"
export GIT_COMMIT="$lower_commit"
export INTERNAL_EXAM_LIFECYCLE_HOST_DIR="$staging_lifecycle"
export INTERNAL_EXAM_BACKUP_HOST_DIR="$staging_backup"
export INTERNAL_EXAM_EVIDENCE_HOST_DIR="$staging_evidence"
export INTERNAL_LAN_BIND_IP=127.0.0.1
export CANDIDATE_GATEWAY_PORT="$MACOS_STAGE_PORT_CANDIDATE"
export OPERATOR_GATEWAY_PORT="$MACOS_STAGE_PORT_OPERATOR"
export POSTGRES_LOOPBACK_PORT="$MACOS_STAGE_PORT_DATABASE"
export FRONTEND_LOOPBACK_PORT="$MACOS_STAGE_PORT_FRONTEND"

assert_root_path() {
  local value="$(macos_resolve_path "$1")"
  [[ "$value" == "$MACOS_LAYOUT_ROOT"/* ]] || macos_die "staging evidence path must remain under the protected root: $value"
  print -r -- "$value"
}

container_root_path() {
  local value="$(assert_root_path "$1")"
  print -r -- "/protected/${value#$MACOS_LAYOUT_ROOT/}"
}

assert_staging_running() {
  local running service
  running="$(macos_compose_capture "$release_path" "$MACOS_STAGING_ENV" "$staging_project" ps --status running --services)"
  for service in db backend auto-submit-worker frontend nginx operator-nginx; do
    print -r -- "$running" | grep -Fx -- "$service" >/dev/null || macos_die "staging service is not running: $service"
  done
}

capture_live_images() {
  local destination="$1"
  macos_compose_base "$release_path" "$MACOS_STAGING_ENV" "$staging_project"
  macos_run_to_file "$destination" docker "${MACOS_COMPOSE_ARGS[@]}" images --format json
  macos_write_checksum "$destination"
  macos_check_checksum "$destination"
}

assert_fresh_staging_resources() {
  local existing_containers existing_volumes
  [[ -z "$(find "$staging_evidence" -mindepth 1 -print -quit 2>/dev/null)" ]] || macos_die "staging evidence from an earlier run remains; run Down and preserve/relocate it before a fresh Up"
  existing_containers="$(macos_compose_capture "$release_path" "$MACOS_STAGING_ENV" "$staging_project" ps -aq 2>/dev/null || true)"
  [[ -z "${existing_containers//[[:space:]]/}" ]] || macos_die "staging project already has containers; run Down explicitly before a fresh Up"
  existing_volumes="$(macos_run_capture docker volume ls --filter "label=com.docker.compose.project=$staging_project" --format '{{.Name}}' 2>/dev/null || true)"
  [[ -z "${existing_volumes//[[:space:]]/}" ]] || macos_die "staging project already has volumes; run Down explicitly before a fresh Up"
}

case "$action" in
  Up)
    assert_fresh_staging_resources
    # Compose may create a subset of services before returning non-zero.  Mark
    # the attempt before invoking it so EXIT cleanup removes only this exact
    # staging project even for partial failures.
    up_attempted=1
    macos_compose "$release_path" "$MACOS_STAGING_ENV" "$staging_project" up -d --no-build --remove-orphans
    up_started=1
    run_id="run-${macos_timestamp}-${$}-${RANDOM}"
    started_at="$(macos_now_iso)"
    image_identity_digest="$(macos_sha256 "$release_path/ops/release/built-image-identity.json")"
    run_identity="$staging_evidence/run-${run_id}.json"
    up_created_run_identity="$run_identity"
    run_json="{\"schemaVersion\":2,\"kind\":\"staging-run\",\"status\":\"started\",\"runId\":\"$(macos_json_escape "$run_id")\",\"commit\":\"${lower_commit}\",\"project\":\"${staging_project}\",\"hostId\":\"$(macos_json_escape "$MACOS_HOST_ID")\",\"hostOS\":\"darwin\",\"architecture\":\"arm64\",\"platform\":\"linux/arm64\",\"builtImageIdentitySha256\":\"$image_identity_digest\",\"startedAt\":\"$started_at\",\"secrets\":\"redacted\"}"
    macos_write_atomic "$run_identity" "$run_json"
    macos_checksummed_json "$run_identity"
    live_image_ids="$staging_evidence/live-images-${run_id}.json"
    up_created_live_images="$live_image_ids"
    capture_live_images "$live_image_ids"
    macos_log "staging_started project=$staging_project runId=$run_id runIdentity=${run_identity:t} liveImages=${live_image_ids:t} acceptance=required"
    ;;
  Down)
    # Only this commit-scoped project is removed; formal volumes are never
    # addressed by staging cleanup.
    macos_compose "$release_path" "$MACOS_STAGING_ENV" "$staging_project" down -v --remove-orphans
    accepted_bundle=""
    canonical_candidates=()
    for candidate in "$staging_evidence"/*.json(N); do
      [[ "$(macos_json_get "$candidate" kind 2>/dev/null || true)" == staging-acceptance && "$(macos_json_get "$candidate" status 2>/dev/null || true)" == passed ]] || continue
      canonical_candidates+=("$candidate")
    done
    if (( ${#canonical_candidates[@]} > 0 )); then
      accepted_canonical="${canonical_candidates[-1]}"
      accepted_run_id="$(macos_json_get "$accepted_canonical" runId 2>/dev/null || true)"
      [[ "$accepted_run_id" =~ '^[A-Za-z0-9][A-Za-z0-9._:-]{8,127}$' ]] || macos_die "accepted staging canonical run identity is invalid"
      # Validate the complete canonical/raw bundle while it is still in its
      # live staging location.  Down then relocates the exact files; a
      # malformed or stale bundle is never made durable.  Direct docker run
      # mounts only the protected root and selected backend image, so no
      # formal Compose project or named volume can be created here.
      backend_reference="$(macos_json_get "$release_path/ops/release/built-image-identity.json" images.backend.reference)"
      macos_run_checked docker run --rm \
        --volume "$MACOS_LAYOUT_ROOT:/protected:ro" "$backend_reference" \
        uv run --no-sync python -m app.ops.staging_acceptance validate \
        --root /protected \
        --release "/protected/releases/$version" \
        --canonical "/protected/staging/$short_commit/evidence/${accepted_canonical:t}" \
        --expected-host-id "$MACOS_HOST_ID"
      accepted_bundle="$MACOS_LAYOUT_EVIDENCE/staging-${short_commit}-${accepted_run_id}"
      [[ ! -e "$accepted_bundle" ]] || macos_die "durable staging evidence bundle already exists"
      mv -f -- "$staging_evidence" "$accepted_bundle"
      mkdir -p -- "$staging_evidence"
      chmod 700 "$staging_evidence"
      macos_log "staging_evidence_preserved bundle=$accepted_bundle"
    else
      rm -R -- "$staging_evidence"
      mkdir -p -- "$staging_evidence"
      chmod 700 "$staging_evidence"
    fi
    macos_log "staging_stopped project=$staging_project volumes_removed=true evidence_preserved=${accepted_bundle:-none}"
    ;;
  Status)
    macos_log "staging_status project=$staging_project"
    macos_compose_capture "$release_path" "$MACOS_STAGING_ENV" "$staging_project" ps
    ;;
  Accept)
    [[ -n "$run_identity" && -n "$live_image_ids" && -n "$canonical_output" ]] || macos_die "Accept requires run identity, live image IDs, and canonical output paths"
    [[ -n "$health_migration_evidence" && -n "$browser_evidence" && -n "$smtp_evidence" && -n "$capacity_evidence" && -n "$restart_evidence" && -n "$route_evidence" && -n "$backup_restore_evidence" ]] || macos_die "Accept requires explicit paths for all seven raw evidence artifacts"
    run_identity="$(assert_root_path "$run_identity")"
    live_image_ids="$(assert_root_path "$live_image_ids")"
    canonical_output="$(assert_root_path "$canonical_output")"
    health_migration_evidence="$(assert_root_path "$health_migration_evidence")"
    browser_evidence="$(assert_root_path "$browser_evidence")"
    smtp_evidence="$(assert_root_path "$smtp_evidence")"
    capacity_evidence="$(assert_root_path "$capacity_evidence")"
    restart_evidence="$(assert_root_path "$restart_evidence")"
    route_evidence="$(assert_root_path "$route_evidence")"
    backup_restore_evidence="$(assert_root_path "$backup_restore_evidence")"
    [[ "$canonical_output:h" == "$staging_evidence" ]] || macos_die "canonical output must stay beside its raw run artifacts in the commit-scoped staging evidence directory"
    assert_staging_running
    macos_compose_base "$release_path" "$MACOS_STAGING_ENV" "$staging_project"
    canonical_json="$(macos_run_capture docker "${MACOS_COMPOSE_ARGS[@]}" run --rm --no-deps \
      --volume "$MACOS_LAYOUT_ROOT:/protected:ro" backend \
      uv run --no-sync python -m app.ops.staging_acceptance assemble \
      --root /protected \
      --release "$(container_root_path "$release_path")" \
      --project "$staging_project" \
      --expected-host-id "$MACOS_HOST_ID" \
      --run-identity "$(container_root_path "$run_identity")" \
      --live-image-ids "$(container_root_path "$live_image_ids")" \
      --health-migration-evidence "$(container_root_path "$health_migration_evidence")" \
      --browser-evidence "$(container_root_path "$browser_evidence")" \
      --smtp-evidence "$(container_root_path "$smtp_evidence")" \
      --capacity-evidence "$(container_root_path "$capacity_evidence")" \
      --restart-evidence "$(container_root_path "$restart_evidence")" \
      --route-evidence "$(container_root_path "$route_evidence")" \
      --backup-restore-evidence "$(container_root_path "$backup_restore_evidence")" \
      --output "$(container_root_path "$canonical_output")" \
      --stdout)"
    macos_write_atomic "$canonical_output" "$canonical_json"
    macos_checksummed_json "$canonical_output"
    macos_log "staging_accepted project=$staging_project canonical=${canonical_output:t} raw_bundle=verified security=sealed-release-evidence"
    ;;
esac
