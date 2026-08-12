#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
source "$SCRIPT_DIR/Common.zsh"

backup_path=""
browser_evidence=""
docker_settings_evidence=""
pf_evidence=""
network_time_evidence=""
evidence_path=""
lock_held=0
target_maintenance=0
root="${INTERNAL_EXAM_ROOT:-${HOME:?}/Library/Application Support/InternalExam}"
while (( $# > 0 )); do
  case "$1" in
    --backup-path|--backup) (( $# >= 2 )) || macos_die "$1 requires a path"; backup_path="$2"; shift 2 ;;
    --browser-smoke-evidence|--browser-evidence) (( $# >= 2 )) || macos_die "$1 requires a path"; browser_evidence="$2"; shift 2 ;;
    --docker-settings-evidence) (( $# >= 2 )) || macos_die "$1 requires a path"; docker_settings_evidence="$2"; shift 2 ;;
    --pf-evidence) (( $# >= 2 )) || macos_die "$1 requires a path"; pf_evidence="$2"; shift 2 ;;
    --network-time-evidence) (( $# >= 2 )) || macos_die "$1 requires a path"; network_time_evidence="$2"; shift 2 ;;
    --evidence-path) (( $# >= 2 )) || macos_die "$1 requires a path"; evidence_path="$2"; shift 2 ;;
    --lock-held) lock_held=1; shift ;;
    --target-maintenance) target_maintenance=1; shift ;;
    --root) (( $# >= 2 )) || macos_die "--root requires a path"; root="$2"; shift 2 ;;
    -h|--help) print -r -- "usage: $0 --backup-path PATH --browser-smoke-evidence PATH --pf-evidence PATH --network-time-evidence PATH [--docker-settings-evidence PATH] [--evidence-path PATH] [--target-maintenance] [--root ROOT]"; exit 0 ;;
    *) macos_die "unknown argument: $1"; exit 1 ;;
  esac
done

preflight_status=failed
current_check=initialization
release_version="unknown"
release_commit="unknown"
evidence_written=0
environment_saved=0
candidate_port=8080
operator_port=8081
candidate_public_base_url="unknown"
pf_evidence_digest="unknown"
network_time_evidence_digest="unknown"

write_preflight_evidence() {
  local status_value="$1" destination json
  json="{\"schemaVersion\":1,\"kind\":\"formal-preflight\",\"status\":\"$status_value\",\"checkedAt\":\"$(macos_now_iso)\",\"check\":\"$current_check\",\"version\":\"$(macos_json_escape "$release_version")\",\"commit\":\"$(macos_json_escape "$release_commit")\",\"hostId\":\"$(macos_json_escape "${MACOS_HOST_ID:-unknown}")\",\"architecture\":\"arm64\",\"candidatePort\":$candidate_port,\"candidatePublicBaseUrl\":\"$(macos_json_escape "$candidate_public_base_url")\",\"operatorPort\":$operator_port,\"targetMaintenance\":$target_maintenance,\"pfEvidenceSha256\":\"$(macos_json_escape "$pf_evidence_digest")\",\"networkTimeEvidenceSha256\":\"$(macos_json_escape "$network_time_evidence_digest")\",\"secrets\":\"redacted\",\"approval\":\"manual-required\"}"
  if [[ -n "$evidence_path" ]]; then
    destination="$(macos_resolve_path "$evidence_path")"
    [[ "$destination" == "$MACOS_LAYOUT_EVIDENCE"/* ]] || macos_die "preflight evidence must remain in the protected evidence directory"
    macos_write_atomic "$destination" "$json"
    macos_checksummed_json "$destination"
  else
    destination="$(macos_write_evidence "$MACOS_LAYOUT_EVIDENCE" formal-preflight "$json")"
  fi
  evidence_written=1
  print -r -- "$destination"
}

finish_preflight() {
  local exit_code=$?
  if (( evidence_written == 0 )) && [[ -d "${MACOS_LAYOUT_EVIDENCE:-}" ]]; then
    write_preflight_evidence "$preflight_status" >/dev/null 2>&1 || true
  fi
  (( environment_saved == 1 )) && macos_restore_environment
  (( lock_held == 1 )) || macos_release_lock
  if [[ "$preflight_status" != passed ]]; then exit 1; fi
  exit "$exit_code"
}
trap finish_preflight EXIT

macos_assert_macos
[[ -n "$backup_path" && -n "$browser_evidence" && -n "$pf_evidence" && -n "$network_time_evidence" ]] || macos_die "backup, browser, PF, and network-time evidence are required"
macos_assert_outside_worktree "$root" >/dev/null
macos_layout "$root"
macos_assert_protected_configuration "$root"
[[ -n "$docker_settings_evidence" ]] || docker_settings_evidence="$MACOS_LAYOUT_CONFIGURATION/docker-settings-evidence.json"
docker_settings_evidence="$(macos_resolve_path "$docker_settings_evidence")"
[[ ! -L "$pf_evidence" && ! -L "$network_time_evidence" ]] || macos_die "privileged host evidence paths must not be symlinks"
pf_evidence="$(macos_resolve_path "$pf_evidence")"
network_time_evidence="$(macos_resolve_path "$network_time_evidence")"
if [[ -n "$evidence_path" ]]; then evidence_path="$(macos_resolve_path "$evidence_path")"; fi
if (( lock_held == 1 )); then
  macos_assert_inherited_lock
else
  macos_acquire_lock "$MACOS_LAYOUT_STATE/.operation.lock"
fi
macos_save_environment INTERNAL_LAN_BIND_IP CANDIDATE_GATEWAY_PORT OPERATOR_GATEWAY_PORT \
  POSTGRES_LOOPBACK_PORT FRONTEND_LOOPBACK_PORT CORS_ORIGINS CANDIDATE_PUBLIC_BASE_URL
environment_saved=1
if (( target_maintenance == 1 )); then
  candidate_port=28080
  operator_port=28081
  export INTERNAL_LAN_BIND_IP=127.0.0.1
  export CANDIDATE_GATEWAY_PORT="$candidate_port"
  export OPERATOR_GATEWAY_PORT="$operator_port"
  export POSTGRES_LOOPBACK_PORT=25432
  export FRONTEND_LOOPBACK_PORT=25173
  export CORS_ORIGINS="http://127.0.0.1:${candidate_port}"
  export CANDIDATE_PUBLIC_BASE_URL="http://127.0.0.1:${candidate_port}"
fi
macos_require_formal_paths
macos_read_cutover_identity
formal_lan_ip="$(macos_formal_value INTERNAL_LAN_BIND_IP)"
formal_approved_cidr="$(macos_formal_value PF_APPROVED_CIDR)"
formal_candidate_port="$(macos_formal_value CANDIDATE_GATEWAY_PORT)"
formal_candidate_public_base_url="$(macos_formal_value CANDIDATE_PUBLIC_BASE_URL)"
formal_operator_port="$(macos_formal_value OPERATOR_GATEWAY_PORT)"
formal_postgres_port="$(macos_formal_value POSTGRES_LOOPBACK_PORT)"
formal_frontend_port="$(macos_formal_value FRONTEND_LOOPBACK_PORT)"
formal_backend_port=8000
[[ "$formal_candidate_port" =~ '^[0-9]+$' && "$formal_operator_port" =~ '^[0-9]+$' && "$formal_postgres_port" =~ '^[0-9]+$' && "$formal_frontend_port" =~ '^[0-9]+$' ]] || macos_die "formal service ports are missing or invalid"
[[ "$formal_backend_port" =~ '^[0-9]+$' ]] || macos_die "formal backend port is invalid"
[[ "$formal_candidate_public_base_url" == "http://${formal_lan_ip}:${formal_candidate_port}" ]] || macos_die "CANDIDATE_PUBLIC_BASE_URL must exactly match the fixed formal candidate address"

current_check=privileged_host_evidence
host_identity_digest="$(macos_sha256 "$MACOS_LAYOUT_STATE/host-identity.json")"
boot_marker_digest="$(macos_current_boot_marker_digest)"
macos_assert_pf_evidence "$pf_evidence" "$MACOS_HOST_ID" "$host_identity_digest" "$boot_marker_digest" \
  "$formal_approved_cidr" "$formal_lan_ip" "$formal_candidate_port" "$formal_operator_port" \
  "$formal_postgres_port" "$formal_frontend_port" "$formal_backend_port" "$MACOS_LAYOUT_EVIDENCE"
macos_assert_network_time_evidence "$network_time_evidence" "$MACOS_HOST_ID" "$host_identity_digest" "$boot_marker_digest" "$MACOS_LAYOUT_EVIDENCE"
pf_evidence_digest="$(macos_sha256 "$pf_evidence")"
network_time_evidence_digest="$(macos_sha256 "$network_time_evidence")"

current_check=docker
macos_docker_ready
docker_arch="$(docker info --format '{{.Architecture}}' 2>/dev/null || true)"
case "$docker_arch" in
  arm64|aarch64) ;;
  *) macos_die "Docker Desktop architecture is not ARM64" ;;
esac
docker_os="$(docker info --format '{{.OSType}}' 2>/dev/null || true)"
[[ "$docker_os" == linux ]] || macos_die "Docker Desktop operating system is not Linux"
docker_memory="$(docker info --format '{{.MemTotal}}' 2>/dev/null || true)"
[[ "$docker_memory" =~ '^[0-9]+$' && "$docker_memory" -ge 8000000000 ]] || macos_die "Docker Desktop memory is below the approved 8 GB threshold"
docker_ncpu="$(docker info --format '{{.NCPU}}' 2>/dev/null || true)"
[[ "$docker_ncpu" =~ '^[0-9]+$' && "$docker_ncpu" -ge 8 ]] || macos_die "Docker Desktop CPU allocation is below the approved 8 CPU threshold"
macos_require_command curl
macos_require_command df
macos_require_command pmset
macos_require_command fdesetup
macos_require_command awk
macos_require_command grep

current_check=release_checksums
macos_release_state "$MACOS_CURRENT_STATE"
release_path="$MACOS_STATE_PATH"
release_version="$MACOS_STATE_VERSION"
release_commit="$MACOS_STATE_COMMIT"
"$SCRIPT_DIR/Test-ReleaseBundle.zsh" --release-path "$release_path" >/dev/null
macos_verify_built_image_identity "$release_path"
[[ "$(uname -m)" == arm64 ]] || macos_die "formal macOS host must be arm64"
manifest="$release_path/release-manifest.json"
[[ "$(macos_json_get "$manifest" hostOS 2>/dev/null || true)" == darwin ]] || macos_die "release host OS identity is not darwin"
[[ "$(macos_json_get "$manifest" architecture 2>/dev/null || true)" == arm64 ]] || macos_die "release architecture identity is not arm64"

current_check=configuration_acl
macos_assert_project_name formal "$MACOS_FORMAL_PROJECT"
lan_ip="$formal_lan_ip"
cors_origins="$(macos_formal_value CORS_ORIGINS)"
if (( target_maintenance == 1 )); then
  lan_ip=127.0.0.1
  # Maintenance Compose uses an isolated loopback port pair, while the
  # privileged PF evidence remains bound to the production values read above.
  cors_origins="http://127.0.0.1:${candidate_port}"
  candidate_public_base_url="http://127.0.0.1:${candidate_port}"
else
  candidate_port="$formal_candidate_port"
  operator_port="$formal_operator_port"
  case "$lan_ip" in
    10.*|192.168.*|172.16.*|172.17.*|172.18.*|172.19.*|172.2[0-9].*|172.3[0-1].*) ;;
    *) macos_die "INTERNAL_LAN_BIND_IP must be one fixed private IPv4 address" ;;
  esac
  [[ "$cors_origins" == "http://${lan_ip}:${candidate_port}" ]] || macos_die "CORS_ORIGINS must exactly match the fixed candidate address"
  candidate_public_base_url="$formal_candidate_public_base_url"
  [[ "$candidate_public_base_url" == "http://${lan_ip}:${candidate_port}" ]] || macos_die "CANDIDATE_PUBLIC_BASE_URL must exactly match the fixed candidate address"
fi

current_check=docker_desktop_settings
docker_settings_file=""
for candidate in \
  "$HOME/Library/Group Containers/group.com.docker/settings.json" \
  "$HOME/Library/Group Containers/group.com.docker/settings-store.json" \
  "$HOME/Library/Containers/com.docker.docker/Data/settings.json"; do
  if [[ -f "$candidate" ]]; then docker_settings_file="$candidate"; break; fi
done
[[ -n "$docker_settings_file" ]] || macos_die "Docker Desktop settings file is unavailable"
plutil -convert json -o - -- "$docker_settings_file" >/dev/null 2>&1 || macos_die "Docker Desktop settings file is invalid"
docker_autostart="$(macos_json_get "$docker_settings_file" AutoStart 2>/dev/null || macos_json_get "$docker_settings_file" autoStart 2>/dev/null || macos_json_get "$docker_settings_file" startOnLogin 2>/dev/null || true)"
docker_resource_saver="$(macos_json_get "$docker_settings_file" UseResourceSaver 2>/dev/null || macos_json_get "$docker_settings_file" useResourceSaver 2>/dev/null || macos_json_get "$docker_settings_file" resourceSaver 2>/dev/null || true)"
[[ "$docker_autostart" == true ]] || macos_die "Docker Desktop auto-start setting is not enabled"
if [[ -n "$docker_resource_saver" ]]; then
  [[ "$docker_resource_saver" == false ]] || macos_die "Docker Desktop Resource Saver is enabled"
else
  # Older settings-store files may omit UseResourceSaver.  In that narrow
  # compatibility case require a protected operator capture for the boolean;
  # memory is independently verified above from live `docker info` output.
  [[ -f "$docker_settings_evidence" && -f "$docker_settings_evidence.sha256" ]] || macos_die "Docker Desktop Resource Saver setting requires checksummed operator evidence"
  macos_secure_path "$docker_settings_evidence"
  macos_check_checksum "$docker_settings_evidence"
  [[ "$(macos_json_get "$docker_settings_evidence" status 2>/dev/null || true)" == passed ]] || macos_die "Docker Desktop settings evidence did not pass"
  settings_checked_at="$(macos_json_get "$docker_settings_evidence" checkedAt 2>/dev/null || macos_json_get "$docker_settings_evidence" checked_at 2>/dev/null || true)"
  macos_assert_fresh_timestamp "$settings_checked_at"
  [[ "$(macos_json_get "$docker_settings_evidence" hostId 2>/dev/null || true)" == "$MACOS_HOST_ID" ]] || macos_die "Docker Desktop settings evidence belongs to another host"
  [[ "$(macos_json_get "$docker_settings_evidence" hostOS 2>/dev/null || true)" == darwin && "$(macos_json_get "$docker_settings_evidence" architecture 2>/dev/null || true)" == arm64 ]] || macos_die "Docker Desktop settings evidence host identity is invalid"
  capture_digest="$(macos_json_get "$docker_settings_evidence" captureSha256 2>/dev/null || macos_json_get "$docker_settings_evidence" exportSha256 2>/dev/null || macos_json_get "$docker_settings_evidence" summarySha256 2>/dev/null || true)"
  [[ "$capture_digest" =~ '^[0-9a-fA-F]{64}$' ]] || macos_die "Docker Desktop settings evidence lacks a capture digest"
  [[ "$(macos_json_get "$docker_settings_evidence" resourceSaverDisabled 2>/dev/null || true)" == true ]] || macos_die "Docker Desktop Resource Saver is enabled or unverified"
fi

current_check=power_and_sleep
pmset_custom="$(pmset -g custom 2>/dev/null || true)"
[[ -n "$pmset_custom" ]] || macos_die "power-management evidence is unavailable"
power_source="$(pmset -g batt 2>/dev/null || true)"
[[ "$power_source" == *"AC Power"* ]] || macos_die "formal host is not connected to AC power"
ac_settings="$(print -r -- "$pmset_custom" | awk '/AC Power:/{active=1; next} /^[[:alpha:]][[:alnum:] _-]* Power:/{active=0} active {print}')"
[[ -n "$ac_settings" ]] || macos_die "AC power settings are unavailable"
sleep_value="$(print -r -- "$ac_settings" | awk '$1 == "sleep" {print $2; exit}')"
disksleep_value="$(print -r -- "$ac_settings" | awk '$1 == "disksleep" {print $2; exit}')"
[[ "$sleep_value" == 0 && "$disksleep_value" == 0 ]] || macos_die "AC sleep/disksleep must both be disabled"

current_check=time_sync
date -u '+%Y-%m-%dT%H:%M:%SZ' >/dev/null

current_check=filevault_firewall
filevault_output="$(fdesetup status 2>/dev/null || true)"
[[ "$filevault_output" == *"FileVault is On"* ]] || macos_die "FileVault is not enabled"
firewall_output="$(/usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate 2>/dev/null || true)"
[[ "$firewall_output" == *enabled* || "$firewall_output" == *Enabled* ]] || macos_die "firewall is not enabled"

current_check=services_and_split_exposure
macos_compose_base "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT"
running="$(macos_compose_capture "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" ps --status running --services)"
for service in db backend auto-submit-worker frontend nginx operator-nginx; do
  [[ "$running" == *$'\n'"$service"$'\n'* || "$running" == "$service" || "$running" == "$service"$'\n'* || "$running" == *$'\n'"$service" ]] || macos_die "required service is not running: $service"
done
compose_config="$(macos_compose_capture "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" config)"
[[ "$compose_config" == *"${lan_ip}:${candidate_port}"* && "$compose_config" == *"127.0.0.1:${operator_port}"* ]] || macos_die "formal split ingress is not rendered"

current_check=health_and_migration
candidate_code="$(curl -sS -o /dev/null -w '%{http_code}' --connect-timeout 5 --max-time 10 "http://${lan_ip}:${candidate_port}/api/health")"
operator_code="$(curl -sS -o /dev/null -w '%{http_code}' --connect-timeout 5 --max-time 10 "http://127.0.0.1:${operator_port}/api/ready")"
[[ "$candidate_code" == 200 && "$operator_code" == 200 ]] || macos_die "candidate or operator health check failed"
migration_head="$(macos_json_get "$manifest" migrationHead)"
migration="$(macos_compose_capture "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT" exec -T backend uv run --no-sync alembic current)"
[[ "$migration" == *"$migration_head"* ]] || macos_die "database is not at the release migration head"

current_check=route_isolation
candidate_admin="$(curl -sS -o /dev/null -w '%{http_code}' --connect-timeout 5 --max-time 10 "http://${lan_ip}:${candidate_port}/admin" || true)"
operator_admin="$(curl -sS -o /dev/null -w '%{http_code}' --connect-timeout 5 --max-time 10 "http://127.0.0.1:${operator_port}/admin" || true)"
[[ "$candidate_admin" == 404 && "$operator_admin" == 200 ]] || macos_die "candidate/operator route isolation failed"

current_check=disk_reserve
free_kib="$(df -Pk "$root" | tail -n 1 | awk '{print $4}')"
[[ "$free_kib" =~ '^[0-9]+$' ]] || macos_die "disk reserve evidence is unavailable"
(( free_kib * 1024 >= 21474836480 )) || macos_die "disk reserve is below 20 GiB"

current_check=backup
backup_path="$(macos_assert_backup "$backup_path")"
macos_assert_outside_worktree "$backup_path" >/dev/null
macos_compose_base "$release_path" "$MACOS_FORMAL_ENV" "$MACOS_FORMAL_PROJECT"
macos_run_checked docker "${MACOS_COMPOSE_ARGS[@]}" run --rm --no-deps \
  --volume "$backup_path:/portable-backup:ro" backend \
  uv run --no-sync python -m app.ops.host_portability validate-migration-input /portable-backup
backup_footprint_kib="$(du -k "$backup_path/database.dump" "$backup_path/learning_media.tar.gz" | awk '{total += $1} END {print total}')"
[[ "$backup_footprint_kib" =~ '^[0-9]+$' ]] || macos_die "backup footprint evidence is unavailable"
required_kib=$((20 * 1024 * 1024))
(( backup_footprint_kib * 3 > required_kib )) && required_kib=$(( backup_footprint_kib * 3 ))
(( free_kib >= required_kib )) || macos_die "disk reserve is below max(20 GiB, 3x backup footprint)"

current_check=smtp
macos_run_checked docker "${MACOS_COMPOSE_ARGS[@]}" run --rm --no-deps backend \
  uv run --no-sync python -m app.ops.preflight smtp

current_check=browser_smoke
browser_evidence="$(macos_resolve_path "$browser_evidence")"
[[ -f "$browser_evidence" ]] || macos_die "browser smoke evidence is missing"
macos_check_checksum "$browser_evidence"
plutil -convert json -o - -- "$browser_evidence" >/dev/null 2>&1 || macos_die "browser smoke evidence is invalid"
[[ "$(macos_json_get "$browser_evidence" status 2>/dev/null || true)" == passed ]] || macos_die "browser smoke evidence did not pass"
[[ "$(macos_json_get "$browser_evidence" gitCommit 2>/dev/null || macos_json_get "$browser_evidence" commit 2>/dev/null || true)" == "${release_commit:l}" ]] || macos_die "browser smoke evidence belongs to another release"
[[ "$(macos_json_get "$browser_evidence" applicationVersion 2>/dev/null || macos_json_get "$browser_evidence" version 2>/dev/null || true)" == "$release_version" ]] || macos_die "browser smoke evidence version is invalid"
[[ "$(macos_json_get "$browser_evidence" hostOS 2>/dev/null || true)" == darwin && "$(macos_json_get "$browser_evidence" architecture 2>/dev/null || true)" == arm64 ]] || macos_die "browser smoke evidence host identity is invalid"
browser_checked_at="$(macos_json_get "$browser_evidence" checkedAt 2>/dev/null || macos_json_get "$browser_evidence" checked_at 2>/dev/null || true)"
macos_assert_fresh_timestamp "$browser_checked_at"
browser_url="$(macos_json_get "$browser_evidence" candidateUrl 2>/dev/null || macos_json_get "$browser_evidence" url 2>/dev/null || true)"
[[ "$browser_url" == "http://${lan_ip}:${candidate_port}" || "$browser_url" == "http://${lan_ip}:${candidate_port}"/* ]] || macos_die "browser smoke evidence URL is not the formal candidate endpoint"

preflight_status=passed
write_preflight_evidence passed >/dev/null
macos_log "formal_preflight status=passed version=$release_version commit=$release_commit approval=manual-required"
