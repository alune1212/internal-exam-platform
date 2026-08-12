#!/bin/zsh
set -euo pipefail
umask 077

SCRIPT_DIR="${0:A:h}"
source "$SCRIPT_DIR/Common.zsh"

release_path=""
run_identity=""
health_migration_evidence=""
restart_evidence=""
route_evidence=""
root="${INTERNAL_EXAM_ROOT:-${HOME:?}/Library/Application Support/InternalExam}"
while (( $# > 0 )); do
  case "$1" in
    --release-path|--release) (( $# >= 2 )) || macos_die "$1 requires a path"; release_path="$2"; shift 2 ;;
    --run-identity|--run-evidence) (( $# >= 2 )) || macos_die "$1 requires a path"; run_identity="$2"; shift 2 ;;
    --health-migration-evidence) (( $# >= 2 )) || macos_die "$1 requires a path"; health_migration_evidence="$2"; shift 2 ;;
    --restart-evidence) (( $# >= 2 )) || macos_die "$1 requires a path"; restart_evidence="$2"; shift 2 ;;
    --route-evidence) (( $# >= 2 )) || macos_die "$1 requires a path"; route_evidence="$2"; shift 2 ;;
    --root) (( $# >= 2 )) || macos_die "--root requires a path"; root="$2"; shift 2 ;;
    -h|--help)
      print -r -- "usage: $0 --release-path INSTALLED_RELEASE --run-identity PATH --health-migration-evidence PATH --restart-evidence PATH --route-evidence PATH [--root ROOT]"
      print -r -- "This helper emits only health/migration, exact six-service Compose restart recovery, and route facts it probes. It never emits browser, SMTP, or capacity passed evidence, and it does not claim a Docker Desktop or full-host restart."
      exit 0
      ;;
    *) macos_die "unknown argument: $1"; exit 1 ;;
  esac
done

macos_assert_macos
[[ -n "$release_path" && -n "$run_identity" && -n "$health_migration_evidence" && -n "$restart_evidence" && -n "$route_evidence" ]] || macos_die "release, run identity, and three output paths are required"
macos_assert_outside_worktree "$root" >/dev/null
macos_layout "$root"
macos_assert_protected_configuration "$root"
macos_read_cutover_identity
macos_docker_ready
macos_acquire_lock "$MACOS_LAYOUT_STATE/.operation.lock"
trap 'macos_release_lock' EXIT

release_path="$(macos_resolve_path "$release_path")"
[[ "$release_path:h" == "$MACOS_LAYOUT_RELEASES" ]] || macos_die "runtime checks require an installed release under ROOT/releases/<version>"
manifest="$release_path/release-manifest.json"
git_commit="$(macos_json_get "$manifest" gitCommit)"
lower_commit="${git_commit:l}"
staging_project="internal-exam-staging-${lower_commit[1,12]}"
macos_assert_project_name staging "$staging_project"
staging_root="$MACOS_LAYOUT_ROOT/staging/${lower_commit[1,12]}"
staging_evidence="$staging_root/evidence"
mkdir -p -- "$staging_evidence"
chmod 700 "$staging_root" "$staging_evidence"

assert_protected_output() {
  local candidate="$1" relative current part resolved existing
  [[ "$candidate" == /* ]] || macos_die "runtime evidence output must be absolute"
  [[ "$candidate" == "$MACOS_LAYOUT_ROOT"/* ]] || macos_die "runtime evidence output must remain under the protected root"
  relative="${candidate#$MACOS_LAYOUT_ROOT/}"
  [[ -n "$relative" ]] || macos_die "runtime evidence output cannot be the protected root"
  current="$MACOS_LAYOUT_ROOT"
  local -a components
  components=("${(@s:/:)relative}")
  for part in "${components[@]}"; do
    [[ -n "$part" && "$part" != "." && "$part" != ".." ]] || macos_die "runtime evidence output path is invalid"
    current="$current/$part"
    [[ ! -L "$current" ]] || macos_die "runtime evidence output path contains a symlink"
  done
  [[ -d "$candidate:h" ]] || macos_die "runtime evidence output parent is missing"
  macos_secure_path "$candidate:h"
  for existing in "$candidate" "$candidate.sha256"; do
    [[ ! -L "$existing" ]] || macos_die "runtime evidence output must not be a symlink"
    if [[ -e "$existing" ]]; then
      macos_secure_path "$existing"
    fi
  done
  resolved="$(macos_resolve_path "$candidate")"
  [[ "$resolved" == "$MACOS_LAYOUT_ROOT"/* ]] || macos_die "runtime evidence output resolved outside the protected root"
  print -r -- "$resolved"
}

run_identity="$(assert_protected_output "$run_identity")"
health_migration_evidence="$(assert_protected_output "$health_migration_evidence")"
restart_evidence="$(assert_protected_output "$restart_evidence")"
route_evidence="$(assert_protected_output "$route_evidence")"
[[ -f "$run_identity" ]] || macos_die "staging run identity is missing"
run_id="$(macos_json_get "$run_identity" runId 2>/dev/null || macos_json_get "$run_identity" run_id)"
run_host_id="$(macos_json_get "$run_identity" hostId 2>/dev/null || macos_json_get "$run_identity" host_id)"
[[ "$run_host_id" == "$MACOS_HOST_ID" ]] || macos_die "staging run belongs to another commissioning host"
image_identity_digest="$(macos_sha256 "$release_path/ops/release/built-image-identity.json")"
started_at="$(macos_json_get "$run_identity" startedAt 2>/dev/null || macos_json_get "$run_identity" started_at)"

macos_save_environment APP_VERSION_TAG APP_VERSION GIT_COMMIT INTERNAL_EXAM_LIFECYCLE_HOST_DIR INTERNAL_EXAM_BACKUP_HOST_DIR INTERNAL_EXAM_EVIDENCE_HOST_DIR INTERNAL_LAN_BIND_IP CANDIDATE_GATEWAY_PORT CANDIDATE_PUBLIC_BASE_URL OPERATOR_GATEWAY_PORT POSTGRES_LOOPBACK_PORT FRONTEND_LOOPBACK_PORT
export APP_VERSION_TAG="$lower_commit"
export APP_VERSION="$(macos_json_get "$manifest" applicationVersion)"
export GIT_COMMIT="$lower_commit"
export INTERNAL_EXAM_LIFECYCLE_HOST_DIR="$staging_root/lifecycle"
export INTERNAL_EXAM_BACKUP_HOST_DIR="$staging_root/backups"
export INTERNAL_EXAM_EVIDENCE_HOST_DIR="$staging_evidence"
export INTERNAL_LAN_BIND_IP=127.0.0.1
export CANDIDATE_GATEWAY_PORT="$MACOS_STAGE_PORT_CANDIDATE"
export CANDIDATE_PUBLIC_BASE_URL="http://127.0.0.1:${MACOS_STAGE_PORT_CANDIDATE}"
export OPERATOR_GATEWAY_PORT="$MACOS_STAGE_PORT_OPERATOR"
export POSTGRES_LOOPBACK_PORT="$MACOS_STAGE_PORT_DATABASE"
export FRONTEND_LOOPBACK_PORT="$MACOS_STAGE_PORT_FRONTEND"
trap 'macos_restore_environment; macos_release_lock' EXIT

running="$(macos_compose_capture "$release_path" "$MACOS_STAGING_ENV" "$staging_project" ps --status running --services)"
for service in db backend auto-submit-worker frontend nginx operator-nginx; do
  print -r -- "$running" | grep -Fx -- "$service" >/dev/null || macos_die "staging service is not running: $service"
done
macos_compose_base "$release_path" "$MACOS_STAGING_ENV" "$staging_project"
restart_services=(db backend auto-submit-worker frontend nginx operator-nginx)

write_raw() {
  local check="$1" destination="$2" facts="$3" checked_at
  checked_at="$(macos_now_iso)"
  local json="{\"schemaVersion\":2,\"kind\":\"staging-check\",\"status\":\"passed\",\"check\":\"$check\",\"runId\":\"$(macos_json_escape "$run_id")\",\"commit\":\"$lower_commit\",\"project\":\"$staging_project\",\"hostId\":\"$(macos_json_escape "$MACOS_HOST_ID")\",\"hostOS\":\"darwin\",\"architecture\":\"arm64\",\"platform\":\"linux/arm64\",\"builtImageIdentitySha256\":\"$image_identity_digest\",\"startedAt\":\"$(macos_json_escape "$started_at")\",\"checkedAt\":\"$checked_at\",$facts\"secrets\":\"redacted\"}"
  macos_write_atomic "$destination" "$json"
  macos_checksummed_json "$destination"
}

health_code="$(macos_run_capture curl -sS -o /dev/null -w '%{http_code}' --connect-timeout 5 --max-time 10 http://127.0.0.1:${MACOS_STAGE_PORT_CANDIDATE}/api/health)"
ready_code="$(macos_run_capture curl -sS -o /dev/null -w '%{http_code}' --connect-timeout 5 --max-time 10 http://127.0.0.1:${MACOS_STAGE_PORT_OPERATOR}/api/ready)"
[[ "$health_code" == 200 && "$ready_code" == 200 ]] || macos_die "staging health/readiness probe failed"
migration_head="$(macos_json_get "$manifest" migrationHead)"
migration_current="$(macos_compose_capture "$release_path" "$MACOS_STAGING_ENV" "$staging_project" exec -T backend uv run --no-sync alembic current)"
[[ "$migration_current" == *"$migration_head"* ]] || macos_die "staging database migration head probe failed"
write_raw healthMigration "$health_migration_evidence" "\"migrationHead\":\"$(macos_json_escape "$migration_head")\",\"healthHttpStatus\":$health_code,\"readyHttpStatus\":$ready_code,"

macos_compose "$release_path" "$MACOS_STAGING_ENV" "$staging_project" restart "${restart_services[@]}"
macos_compose "$release_path" "$MACOS_STAGING_ENV" "$staging_project" up -d --no-build --wait "${restart_services[@]}"
running_after="$(macos_compose_capture "$release_path" "$MACOS_STAGING_ENV" "$staging_project" ps --status running --services)"
for service in "${restart_services[@]}"; do
  print -r -- "$running_after" | grep -Fx -- "$service" >/dev/null || macos_die "staging service did not recover after Compose restart: $service"
done
recovered_health_code="$(macos_run_capture curl -sS -o /dev/null -w '%{http_code}' --connect-timeout 5 --max-time 20 http://127.0.0.1:${MACOS_STAGE_PORT_CANDIDATE}/api/health)"
recovered_code="$(macos_run_capture curl -sS -o /dev/null -w '%{http_code}' --connect-timeout 5 --max-time 20 http://127.0.0.1:${MACOS_STAGE_PORT_OPERATOR}/api/ready)"
[[ "$recovered_health_code" == 200 && "$recovered_code" == 200 ]] || macos_die "staging Compose service restart recovery probe failed"
recovered_migration_current="$(macos_compose_capture "$release_path" "$MACOS_STAGING_ENV" "$staging_project" exec -T backend uv run --no-sync alembic current)"
[[ "$recovered_migration_current" == *"$migration_head"* ]] || macos_die "staging migration head did not recover after Compose restart"
worker_heartbeat_age="$(macos_compose_capture "$release_path" "$MACOS_STAGING_ENV" "$staging_project" exec -T auto-submit-worker uv run --no-sync python -c 'import pathlib,time; print(max(0.0, time.time() - pathlib.Path("/var/run/internal-exam/auto-submit.heartbeat").stat().st_mtime))')"
[[ "$worker_heartbeat_age" =~ '^[0-9]+([.][0-9]+)?$' ]] || macos_die "staging worker heartbeat age is invalid"
awk -v age="$worker_heartbeat_age" 'BEGIN { exit !(age <= 90) }' || macos_die "staging worker heartbeat is stale after Compose restart"
write_raw restart "$restart_evidence" "\"restartedServices\":[\"db\",\"backend\",\"auto-submit-worker\",\"frontend\",\"nginx\",\"operator-nginx\"],\"recoveredAt\":\"$(macos_now_iso)\",\"healthHttpStatus\":$recovered_health_code,\"readyHttpStatus\":$recovered_code,\"migrationHead\":\"$(macos_json_escape "$migration_head")\",\"workerHeartbeatAgeSeconds\":$worker_heartbeat_age,"

candidate_admin="$(macos_run_capture curl -sS -o /dev/null -w '%{http_code}' --connect-timeout 5 --max-time 10 http://127.0.0.1:${MACOS_STAGE_PORT_CANDIDATE}/admin || true)"
operator_admin="$(macos_run_capture curl -sS -o /dev/null -w '%{http_code}' --connect-timeout 5 --max-time 10 http://127.0.0.1:${MACOS_STAGE_PORT_OPERATOR}/admin || true)"
[[ "$candidate_admin" == 404 && "$operator_admin" == 200 ]] || macos_die "staging route isolation probe failed"
write_raw route "$route_evidence" "\"candidatePort\":${MACOS_STAGE_PORT_CANDIDATE},\"operatorPort\":${MACOS_STAGE_PORT_OPERATOR},\"candidateAdminHttpStatus\":$candidate_admin,\"operatorAdminHttpStatus\":$operator_admin,"
macos_log "staging_runtime_checks status=passed runId=$run_id checks=healthMigration,restart,route browser=supplied-external smtp=supplied-external capacity=supplied-external"
