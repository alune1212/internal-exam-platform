#!/bin/zsh
# Capture the small amount of macOS host state that requires administrator
# privileges.  Run this as the protected formal host account after `sudo -v`;
# do not run the whole formal preflight through sudo.
set -euo pipefail
umask 077

SCRIPT_DIR="${0:A:h}"
source "$SCRIPT_DIR/Common.zsh"

root="${INTERNAL_EXAM_ROOT:-${HOME:?}/Library/Application Support/InternalExam}"
while (( $# > 0 )); do
  case "$1" in
    --root) (( $# >= 2 )) || macos_die "--root requires a path"; root="$2"; shift 2 ;;
    -h|--help)
      print -r -- "usage: $0 [--root ABSOLUTE_ROOT]"
      print -r -- "run /usr/bin/sudo -v first as the designated host account; this script elevates only its fixed read-only probes"
      exit 0
      ;;
    *) macos_die "unknown argument: $1"; exit 1 ;;
  esac
done

macos_assert_macos
(( EUID != 0 )) || macos_die "privileged host evidence must be captured by a non-root designated operator"
macos_assert_outside_worktree "$root" >/dev/null
macos_layout "$root"
macos_assert_protected_configuration "$root"
[[ ! -L "$MACOS_LAYOUT_EVIDENCE" ]] || macos_die "formal evidence directory must not be a symlink"
[[ -d "$MACOS_LAYOUT_EVIDENCE" ]] || mkdir -p -- "$MACOS_LAYOUT_EVIDENCE"
chmod 700 "$MACOS_LAYOUT_EVIDENCE"
macos_privileged_evidence_directory "$MACOS_LAYOUT_EVIDENCE" >/dev/null

# The protected formal root, configuration directory, and evidence directory
# are all checked above through macos_secure_path/macOS evidence helpers.  Their
# common owner is the designated host account for this capture.  This is an OS
# account boundary, intentionally independent from the application operator
# subjects stored in formal.env.
designated_host_account="$(/usr/bin/id -un 2>/dev/null || true)"
[[ -n "$designated_host_account" ]] || macos_die "designated host account cannot be determined"

pf_info_artifact="pf-privileged-info.txt"
pf_rules_artifact="pf-privileged-rules.txt"
network_time_artifact="network-time-privileged-output.txt"
pf_manifest="$MACOS_LAYOUT_EVIDENCE/pf-privileged-host-evidence.json"
network_time_manifest="$MACOS_LAYOUT_EVIDENCE/network-time-privileged-host-evidence.json"

capture_failure=""
capture_ok=1
record_failure() {
  [[ -n "$capture_failure" ]] || capture_failure="$1"
  capture_ok=0
}

json_or_unknown() {
  local value="${1:-}"
  [[ -n "$value" ]] || value=unknown
  macos_json_escape "$value"
}

candidate_ip="unknown"
approved_cidr="unknown"
candidate_port=0
operator_port=0
postgres_port=0
frontend_port=0
backend_port=8000
host_id="unknown"
host_identity_digest="unknown"
boot_marker_digest="unknown"
checked_at="$(macos_now_iso)"

if [[ "$(uname -m)" != arm64 ]]; then
  record_failure "formal macOS host must be arm64"
fi

if ! macos_read_cutover_identity >/dev/null 2>&1; then
  record_failure "current host identity is unavailable"
else
  host_id="$MACOS_HOST_ID"
  identity_path="$MACOS_LAYOUT_STATE/host-identity.json"
  if ! host_identity_digest="$(macos_sha256 "$identity_path")"; then
    host_identity_digest="unknown"
    record_failure "current host identity digest is unavailable"
  fi
fi
if ! boot_marker_digest="$(macos_current_boot_marker_digest 2>/dev/null)"; then
  boot_marker_digest="unknown"
  record_failure "current boot marker is unavailable"
fi

read_formal_value_into() {
  local name="$1" target="$2" value
  if value="$(macos_formal_value "$name" 2>/dev/null)"; then
    typeset -g "$target=$value"
    return 0
  fi
  record_failure "formal configuration field is missing: $name"
  typeset -g "$target=unknown"
  return 0
}

read_formal_value_into INTERNAL_LAN_BIND_IP candidate_ip
read_formal_value_into PF_APPROVED_CIDR approved_cidr
read_formal_value_into CANDIDATE_GATEWAY_PORT candidate_port
read_formal_value_into OPERATOR_GATEWAY_PORT operator_port
read_formal_value_into POSTGRES_LOOPBACK_PORT postgres_port
read_formal_value_into FRONTEND_LOOPBACK_PORT frontend_port

if [[ ! "$candidate_ip" =~ '^[0-9]{1,3}(\.[0-9]{1,3}){3}$' ]]; then
  record_failure "INTERNAL_LAN_BIND_IP is not a fixed IPv4 address"
fi
if [[ ! "$approved_cidr" =~ '^[0-9]{1,3}(\.[0-9]{1,3}){3}/([0-9]|[12][0-9]|3[0-2])$' ]]; then
  record_failure "PF_APPROVED_CIDR is missing or invalid"
elif ! macos_ipv4_in_cidr "$candidate_ip" "$approved_cidr"; then
  record_failure "candidate address is outside the approved PF CIDR"
fi
for port_name in candidate_port operator_port postgres_port frontend_port; do
  port_value="${(P)port_name}"
  if [[ ! "$port_value" =~ '^[0-9]+$' ]] || (( port_value < 1 || port_value > 65535 )); then
    record_failure "formal service port is missing or invalid: $port_name"
    typeset -g "$port_name=0"
  fi
done

# The output files are always replaced atomically.  If configuration or
# operator checks fail, they remain empty and the manifests below are failed;
# no privileged command is attempted by an unauthorized caller.
write_empty_artifact() {
  local artifact="$1"
  macos_write_atomic "$MACOS_LAYOUT_EVIDENCE/$artifact" ""
  macos_write_checksum "$MACOS_LAYOUT_EVIDENCE/$artifact"
}
write_empty_artifact "$pf_info_artifact"
write_empty_artifact "$pf_rules_artifact"
write_empty_artifact "$network_time_artifact"

capture_fixed_command() {
  local destination="$1"; shift
  local temporary code
  temporary="$(mktemp "${destination}.tmp.XXXXXX")"
  chmod 600 "$temporary"
  if "$@" > "$temporary" 2>&1; then
    code=0
  else
    code=$?
  fi
  mv -f -- "$temporary" "$destination"
  chmod 600 "$destination"
  macos_write_checksum "$destination"
  print -r -- "$code"
}

pf_info_exit=-1
pf_rules_exit=-1
network_time_exit=-1
if (( capture_ok == 1 )); then
  # These vectors are intentionally literal.  No command, CIDR, address, or
  # port is accepted from the CLI or environment as an override.
  pf_info_exit="$(capture_fixed_command "$MACOS_LAYOUT_EVIDENCE/$pf_info_artifact" /usr/bin/sudo -n /sbin/pfctl -s info)"
  pf_rules_exit="$(capture_fixed_command "$MACOS_LAYOUT_EVIDENCE/$pf_rules_artifact" /usr/bin/sudo -n /sbin/pfctl -sr)"
  network_time_exit="$(capture_fixed_command "$MACOS_LAYOUT_EVIDENCE/$network_time_artifact" /usr/bin/sudo -n /usr/sbin/systemsetup -getusingnetworktime)"
fi

if (( pf_info_exit != 0 || pf_rules_exit != 0 || network_time_exit != 0 )); then
  record_failure "one or more fixed privileged read-only commands failed"
fi

info_path="$MACOS_LAYOUT_EVIDENCE/$pf_info_artifact"
rules_path="$MACOS_LAYOUT_EVIDENCE/$pf_rules_artifact"
network_time_path="$MACOS_LAYOUT_EVIDENCE/$network_time_artifact"
if (( pf_info_exit == 0 )); then
  [[ "$(< "$info_path")" != *Disabled* && ( "$(< "$info_path")" == *"Status: Enabled"* || "$(< "$info_path")" == *"Status:\ Enabled"* ) ]] || record_failure "packet filter is not enabled"
fi
if (( pf_rules_exit == 0 )); then
  if ! macos_pf_rules_prove_candidate_path "$rules_path" "$approved_cidr" "$candidate_ip" "$candidate_port" >/dev/null 2>&1; then
    record_failure "packet-filter rules do not prove an exact approved candidate path"
  fi
  if ! macos_pf_rules_forbid_ports "$rules_path" "$operator_port" "$postgres_port" "$frontend_port" "$backend_port" >/dev/null 2>&1; then
    record_failure "packet-filter rules expose a forbidden service port"
  fi
fi
if (( network_time_exit == 0 )); then
  network_time_output="$(< "$network_time_path")"
  macos_network_time_output_proves_on "$network_time_output" || record_failure "network time output does not prove On"
fi

pf_info_digest="$(macos_sha256 "$info_path")"
pf_rules_digest="$(macos_sha256 "$rules_path")"
network_time_digest="$(macos_sha256 "$network_time_path")"
if (( capture_ok == 1 )); then
  capture_status=passed
  failure_json=""
else
  capture_status=failed
  failure_json=",\"failureReason\":\"$(json_or_unknown "$capture_failure")\""
fi

write_capture_manifest() {
  local destination="$1" json="$2"
  macos_write_atomic "$destination" "$json"
  macos_checksummed_json "$destination"
}

pf_json="{\"schemaVersion\":1,\"kind\":\"macos-pf-export\",\"provider\":\"pf\",\"status\":\"$capture_status\",\"checkedAt\":\"$(json_or_unknown "$checked_at")\",\"hostOS\":\"darwin\",\"architecture\":\"arm64\",\"hostId\":\"$(json_or_unknown "$host_id")\",\"hostIdentitySha256\":\"$(json_or_unknown "$host_identity_digest")\",\"bootMarkerSha256\":\"$(json_or_unknown "$boot_marker_digest")\",\"designatedHostAccount\":\"$(json_or_unknown "$designated_host_account")\",\"approvedCidr\":\"$(json_or_unknown "$approved_cidr")\",\"candidateAddress\":\"$(json_or_unknown "$candidate_ip")\",\"candidateIp\":\"$(json_or_unknown "$candidate_ip")\",\"candidatePort\":$candidate_port,\"operatorPort\":$operator_port,\"postgresPort\":$postgres_port,\"databasePort\":$postgres_port,\"frontendPort\":$frontend_port,\"backendPort\":$backend_port,\"infoCommand\":\"/usr/bin/sudo -n /sbin/pfctl -s info\",\"infoExitCode\":$pf_info_exit,\"infoArtifact\":\"$pf_info_artifact\",\"infoOutputSha256\":\"$pf_info_digest\",\"rulesCommand\":\"/usr/bin/sudo -n /sbin/pfctl -sr\",\"rulesExitCode\":$pf_rules_exit,\"rulesArtifact\":\"$pf_rules_artifact\",\"rulesOutputSha256\":\"$pf_rules_digest\",\"secrets\":\"redacted\"$failure_json}"
network_json="{\"schemaVersion\":1,\"kind\":\"macos-network-time-export\",\"status\":\"$capture_status\",\"checkedAt\":\"$(json_or_unknown "$checked_at")\",\"hostOS\":\"darwin\",\"architecture\":\"arm64\",\"hostId\":\"$(json_or_unknown "$host_id")\",\"hostIdentitySha256\":\"$(json_or_unknown "$host_identity_digest")\",\"bootMarkerSha256\":\"$(json_or_unknown "$boot_marker_digest")\",\"designatedHostAccount\":\"$(json_or_unknown "$designated_host_account")\",\"command\":\"/usr/bin/sudo -n /usr/sbin/systemsetup -getusingnetworktime\",\"exitCode\":$network_time_exit,\"outputArtifact\":\"$network_time_artifact\",\"outputSha256\":\"$network_time_digest\",\"secrets\":\"redacted\"$failure_json}"
write_capture_manifest "$pf_manifest" "$pf_json"
write_capture_manifest "$network_time_manifest" "$network_json"

macos_log "privileged_host_evidence status=$capture_status pf=$pf_manifest network_time=$network_time_manifest"
[[ "$capture_status" == passed ]] || exit 1
