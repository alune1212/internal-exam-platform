#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
source "$SCRIPT_DIR/Common.zsh"

action=""
release_path=""
acceptance_evidence=""
root="${INTERNAL_EXAM_ROOT:-${HOME:?}/Library/Application Support/InternalExam}"
while (( $# > 0 )); do
  case "$1" in
    --action) (( $# >= 2 )) || macos_die "--action requires Up, Down, or Status"; action="$2"; shift 2 ;;
    --release-path|--release) (( $# >= 2 )) || macos_die "$1 requires a path"; release_path="$2"; shift 2 ;;
    --acceptance-evidence) (( $# >= 2 )) || macos_die "--acceptance-evidence requires a path"; acceptance_evidence="$2"; shift 2 ;;
    --root) (( $# >= 2 )) || macos_die "--root requires a path"; root="$2"; shift 2 ;;
    -h|--help) print -r -- "usage: $0 --action Up|Down|Status|Accept --release-path PATH [--acceptance-evidence PATH] [--root ROOT]"; exit 0 ;;
    *) macos_die "unknown argument: $1"; exit 1 ;;
  esac
done

macos_assert_macos
[[ "$action" == Up || "$action" == Down || "$action" == Status || "$action" == Accept ]] || macos_die "--action must be Up, Down, Status, or Accept"
[[ -n "$release_path" ]] || macos_die "--release-path is required"
macos_assert_outside_worktree "$root" >/dev/null
macos_layout "$root"
macos_assert_protected_configuration "$root"
macos_docker_ready
macos_acquire_lock "$MACOS_LAYOUT_STATE/.operation.lock"
cleanup_staging() {
  macos_restore_environment
  macos_release_lock
}
release_path="$(macos_resolve_path "$release_path")"
[[ -d "$release_path" ]] || macos_die "release directory is missing"
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
mkdir -p -- "$staging_lifecycle" "$staging_backup" "$staging_evidence"
chmod 700 "$MACOS_LAYOUT_ROOT/staging" "$staging_host_root" "$staging_lifecycle" "$staging_backup" "$staging_evidence"

macos_save_environment APP_VERSION_TAG APP_VERSION GIT_COMMIT INTERNAL_EXAM_LIFECYCLE_HOST_DIR INTERNAL_EXAM_BACKUP_HOST_DIR INTERNAL_EXAM_EVIDENCE_HOST_DIR INTERNAL_LAN_BIND_IP CANDIDATE_GATEWAY_PORT OPERATOR_GATEWAY_PORT POSTGRES_LOOPBACK_PORT FRONTEND_LOOPBACK_PORT
trap cleanup_staging EXIT
export APP_VERSION_TAG="${git_commit:l}"
export APP_VERSION="$(macos_json_get "$manifest" applicationVersion)"
export GIT_COMMIT="${git_commit:l}"
export INTERNAL_EXAM_LIFECYCLE_HOST_DIR="$staging_lifecycle"
export INTERNAL_EXAM_BACKUP_HOST_DIR="$staging_backup"
export INTERNAL_EXAM_EVIDENCE_HOST_DIR="$staging_evidence"
export INTERNAL_LAN_BIND_IP=127.0.0.1
export CANDIDATE_GATEWAY_PORT="$MACOS_STAGE_PORT_CANDIDATE"
export OPERATOR_GATEWAY_PORT="$MACOS_STAGE_PORT_OPERATOR"
export POSTGRES_LOOPBACK_PORT="$MACOS_STAGE_PORT_DATABASE"
export FRONTEND_LOOPBACK_PORT="$MACOS_STAGE_PORT_FRONTEND"

case "$action" in
  Up)
    macos_compose "$release_path" "$MACOS_STAGING_ENV" "$staging_project" up -d --no-build --remove-orphans
    evidence_json="{\"schemaVersion\":1,\"kind\":\"staging-start\",\"status\":\"started\",\"commit\":\"${git_commit:l}\",\"project\":\"${staging_project}\",\"hostOS\":\"darwin\",\"architecture\":\"arm64\",\"platform\":\"linux/arm64\",\"candidatePort\":${MACOS_STAGE_PORT_CANDIDATE},\"operatorPort\":${MACOS_STAGE_PORT_OPERATOR},\"databasePort\":${MACOS_STAGE_PORT_DATABASE},\"frontendPort\":${MACOS_STAGE_PORT_FRONTEND},\"secrets\":\"redacted\"}"
    evidence_path="$(macos_write_evidence "$MACOS_LAYOUT_EVIDENCE" staging "$evidence_json")"
    macos_log "staging_started project=$staging_project evidence=${evidence_path:t} acceptance=required"
    ;;
  Down)
    # Only this commit-scoped project is removed; formal volumes are never
    # addressed by staging cleanup.
    macos_compose "$release_path" "$MACOS_STAGING_ENV" "$staging_project" down -v --remove-orphans
    rm -R -- "$staging_host_root"
    macos_log "staging_stopped project=$staging_project volumes_removed=true"
    ;;
  Status)
    macos_log "staging_status project=$staging_project"
    macos_compose_capture "$release_path" "$MACOS_STAGING_ENV" "$staging_project" ps
    ;;
  Accept)
    [[ -n "$acceptance_evidence" ]] || macos_die "--acceptance-evidence is required for Accept"
    acceptance_evidence="$(macos_resolve_path "$acceptance_evidence")"
    [[ -f "$acceptance_evidence" ]] || macos_die "staging acceptance evidence is missing"
    macos_check_checksum "$acceptance_evidence"
    plutil -convert json -o - -- "$acceptance_evidence" >/dev/null 2>&1 || macos_die "staging acceptance evidence is invalid"
    [[ "$(macos_json_get "$acceptance_evidence" kind 2>/dev/null || true)" == staging-acceptance ]] || macos_die "staging evidence is not a canonical acceptance"
    [[ "$(macos_json_get "$acceptance_evidence" status 2>/dev/null || true)" == passed ]] || macos_die "staging acceptance has not passed"
    [[ "$(macos_json_get "$acceptance_evidence" commit 2>/dev/null || true)" == "${git_commit:l}" ]] || macos_die "staging acceptance belongs to another release"
    [[ "$(macos_json_get "$acceptance_evidence" project 2>/dev/null || true)" == "$staging_project" ]] || macos_die "staging acceptance project is invalid"
    [[ "$(macos_json_get "$acceptance_evidence" hostOS 2>/dev/null || true)" == darwin && "$(macos_json_get "$acceptance_evidence" architecture 2>/dev/null || true)" == arm64 && "$(macos_json_get "$acceptance_evidence" platform 2>/dev/null || true)" == linux/arm64 ]] || macos_die "staging acceptance platform identity is invalid"
    acceptance_checked_at="$(macos_json_get "$acceptance_evidence" checkedAt 2>/dev/null || macos_json_get "$acceptance_evidence" checked_at 2>/dev/null || true)"
    macos_assert_fresh_timestamp "$acceptance_checked_at"
    [[ "$(macos_json_get "$acceptance_evidence" builtImageIdentitySha256 2>/dev/null || true)" == "$(macos_sha256 "$release_path/ops/release/built-image-identity.json")" ]] || macos_die "staging acceptance image identity is stale"
    for gate in browser smtp capacity restart route security; do
      [[ "$(macos_json_get "$acceptance_evidence" "gates.$gate" 2>/dev/null || true)" == passed ]] || macos_die "staging gate is missing or failed"
    done
    running_services="$(macos_compose_capture "$release_path" "$MACOS_STAGING_ENV" "$staging_project" ps --status running -q)"
    [[ -n "${running_services//[[:space:]]/}" ]] || macos_die "staging project is not running"
    accepted_json="{\"schemaVersion\":1,\"kind\":\"staging-acceptance\",\"status\":\"passed\",\"commit\":\"${git_commit:l}\",\"project\":\"$staging_project\",\"hostOS\":\"darwin\",\"architecture\":\"arm64\",\"platform\":\"linux/arm64\",\"checkedAt\":\"$(macos_json_escape "$acceptance_checked_at")\",\"builtImageIdentitySha256\":\"$(macos_sha256 "$release_path/ops/release/built-image-identity.json")\",\"acceptanceEvidenceSha256\":\"$(macos_sha256 "$acceptance_evidence")\",\"gates\":{\"browser\":\"passed\",\"smtp\":\"passed\",\"capacity\":\"passed\",\"restart\":\"passed\",\"route\":\"passed\",\"security\":\"passed\"},\"secrets\":\"redacted\"}"
    evidence_path="$(macos_write_evidence "$MACOS_LAYOUT_EVIDENCE" staging-accepted "$accepted_json")"
    macos_log "staging_accepted project=$staging_project evidence=${evidence_path:t}"
    ;;
esac
