#!/bin/zsh
# Produce real SMTP, Playwright desktop, and measured capacity evidence for a
# running, exact staging run.  This command never writes a passed record when a
# producer is missing or fails.
set -euo pipefail
setopt no_nomatch
umask 077

SCRIPT_DIR="${0:A:h}"
source "$SCRIPT_DIR/Common.zsh"

root="${INTERNAL_EXAM_ROOT:-${HOME:?}/Library/Application Support/InternalExam}"
release_path=""
run_identity=""
live_image_ids=""
output_dir=""
check=""
recipient=""
candidate_url=""
operator_url=""
browser_root=""
browser_report=""
browser_command=""
capacity_report=""
capacity_command=""
capacity_project=""
smtp_output=""
browser_output=""
capacity_output=""

usage() {
  print -r -- "usage: Invoke-StagingExternalChecks.zsh --check smtp|browser|capacity|all --release-path INSTALLED_RELEASE --run-identity PATH --output-dir PATH [options]"
  print -r -- "  smtp: --recipient ADDRESS [--smtp-output PATH]"
  print -r -- "  browser: --candidate-url URL --operator-url URL --browser-report CHECKSUMMED_JSON [--browser-command EXECUTABLE] [--browser-output PATH]"
  print -r -- "  capacity: --capacity-report PATH [--capacity-project PROJECT] [--capacity-command EXECUTABLE] [--capacity-output PATH]"
}

while (( $# > 0 )); do
  case "$1" in
    --check) (( $# >= 2 )) || macos_die "--check requires smtp, browser, capacity, or all"; check="$2"; shift 2 ;;
    --root) (( $# >= 2 )) || macos_die "--root requires a path"; root="$2"; shift 2 ;;
    --release-path|--release) (( $# >= 2 )) || macos_die "$1 requires a path"; release_path="$2"; shift 2 ;;
    --run-identity|--run-evidence) (( $# >= 2 )) || macos_die "$1 requires a path"; run_identity="$2"; shift 2 ;;
    --live-image-ids|--live-images) (( $# >= 2 )) || macos_die "$1 requires a path"; live_image_ids="$2"; shift 2 ;;
    --output-dir) (( $# >= 2 )) || macos_die "--output-dir requires a path"; output_dir="$2"; shift 2 ;;
    --recipient) (( $# >= 2 )) || macos_die "--recipient requires an address"; recipient="$2"; shift 2 ;;
    --candidate-url) (( $# >= 2 )) || macos_die "--candidate-url requires a URL"; candidate_url="$2"; shift 2 ;;
    --operator-url) (( $# >= 2 )) || macos_die "--operator-url requires a URL"; operator_url="$2"; shift 2 ;;
    --browser-root) (( $# >= 2 )) || macos_die "--browser-root requires a repository"; browser_root="$2"; shift 2 ;;
    --browser-report) (( $# >= 2 )) || macos_die "--browser-report requires a checksummed report"; browser_report="$2"; shift 2 ;;
    --browser-command) (( $# >= 2 )) || macos_die "--browser-command requires an executable"; browser_command="$2"; shift 2 ;;
    --capacity-report) (( $# >= 2 )) || macos_die "--capacity-report requires a path"; capacity_report="$2"; shift 2 ;;
    --capacity-command) (( $# >= 2 )) || macos_die "--capacity-command requires an executable"; capacity_command="$2"; shift 2 ;;
    --capacity-project) (( $# >= 2 )) || macos_die "--capacity-project requires a project name"; capacity_project="$2"; shift 2 ;;
    --smtp-output) (( $# >= 2 )) || macos_die "--smtp-output requires a path"; smtp_output="$2"; shift 2 ;;
    --browser-output) (( $# >= 2 )) || macos_die "--browser-output requires a path"; browser_output="$2"; shift 2 ;;
    --capacity-output) (( $# >= 2 )) || macos_die "--capacity-output requires a path"; capacity_output="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) macos_die "unknown argument: $1"; exit 1 ;;
  esac
done

macos_assert_macos
[[ "$check" == smtp || "$check" == browser || "$check" == capacity || "$check" == all ]] || macos_die "--check is required"
[[ -n "$release_path" && -n "$run_identity" && -n "$output_dir" ]] || macos_die "release, run identity, and output directory are required"
macos_assert_outside_worktree "$root" >/dev/null
macos_layout "$root"
macos_assert_protected_configuration "$root"
macos_acquire_lock "$MACOS_LAYOUT_STATE/.operation.lock"
macos_save_environment APP_VERSION_TAG APP_VERSION GIT_COMMIT CANDIDATE_PUBLIC_BASE_URL
cleanup_external_checks() {
  macos_restore_environment
  macos_release_lock
}
trap cleanup_external_checks EXIT
macos_read_cutover_identity
macos_docker_ready

release_path="$(macos_resolve_path "$release_path")"
run_identity="$(macos_resolve_path "$run_identity")"
output_dir="$(macos_resolve_path "$output_dir")"
[[ -d "$release_path" && "$release_path:h" == "$MACOS_LAYOUT_RELEASES" ]] || macos_die "release must be installed under ROOT/releases/<version>"
[[ -d "$output_dir" && "$output_dir" == "$MACOS_LAYOUT_ROOT"/staging/*/evidence ]] || macos_die "output directory must be the commit-scoped staging evidence directory"
[[ ! -L "$output_dir" && ! -L "$run_identity" ]] || macos_die "staging evidence paths must not be symlinks"
[[ -f "$run_identity" && -f "$run_identity.sha256" ]] || macos_die "checksummed staging run identity is missing"
macos_check_checksum "$run_identity"
macos_verify_built_image_identity "$release_path"

run_kind="$(macos_json_get "$run_identity" kind 2>/dev/null || true)"
run_status="$(macos_json_get "$run_identity" status 2>/dev/null || true)"
run_id="$(macos_json_get "$run_identity" runId 2>/dev/null || true)"
run_commit="$(macos_json_get "$run_identity" commit 2>/dev/null || true)"
run_project="$(macos_json_get "$run_identity" project 2>/dev/null || true)"
run_host_id="$(macos_json_get "$run_identity" hostId 2>/dev/null || true)"
run_host_os="$(macos_json_get "$run_identity" hostOS 2>/dev/null || true)"
run_architecture="$(macos_json_get "$run_identity" architecture 2>/dev/null || true)"
run_platform="$(macos_json_get "$run_identity" platform 2>/dev/null || true)"
run_identity_digest="$(macos_sha256 "$release_path/ops/release/built-image-identity.json")"
run_built_digest="$(macos_json_get "$run_identity" builtImageIdentitySha256 2>/dev/null || true)"
started_at="$(macos_json_get "$run_identity" startedAt 2>/dev/null || true)"
manifest_commit="$(macos_json_get "$release_path/release-manifest.json" gitCommit)"
[[ "$run_kind" == staging-run && "$run_status" == started ]] || macos_die "staging run identity is not a started schema-2 record"
[[ "$run_id" =~ '^[A-Za-z0-9][A-Za-z0-9._:-]{7,127}$' ]] || macos_die "staging run ID is invalid"
[[ "$run_commit" == "${manifest_commit:l}" && "$run_commit" =~ '^[0-9a-fA-F]{40}$' ]] || macos_die "staging run commit does not match the installed release"
[[ "$run_host_id" == "$MACOS_HOST_ID" && "$run_host_os" == darwin && "$run_architecture" == arm64 && "$run_platform" == linux/arm64 ]] || macos_die "staging run host identity is not this ARM64 macOS host"
[[ "$run_built_digest" == "$run_identity_digest" ]] || macos_die "staging run image identity digest does not match the release"
[[ "$run_project" =~ '^internal-exam-staging-[0-9a-fA-F]{12}$' ]] || macos_die "staging Compose project name is invalid"
macos_assert_fresh_timestamp "$started_at"
macos_secure_path "$output_dir"

# Compose interpolation must resolve to the installed release, never a
# developer's default `dev` tag.
export APP_VERSION_TAG="${run_commit:l}"
export APP_VERSION="$(macos_json_get "$release_path/release-manifest.json" applicationVersion)"
export GIT_COMMIT="${run_commit:l}"
export CANDIDATE_PUBLIC_BASE_URL="http://127.0.0.1:${MACOS_STAGE_PORT_CANDIDATE}"

[[ -n "$smtp_output" ]] || smtp_output="$output_dir/staging-check-smtp-${run_id}.json"
[[ -n "$browser_output" ]] || browser_output="$output_dir/staging-check-browser-${run_id}.json"
[[ -n "$capacity_output" ]] || capacity_output="$output_dir/staging-check-capacity-${run_id}.json"

assert_output_path() {
  local path="$(macos_resolve_path "$1")"
  [[ "$path:h" == "$output_dir" ]] || macos_die "evidence output must be directly beside the run identity"
  [[ ! -e "$path" && ! -e "$path.sha256" ]] || macos_die "evidence output already exists: ${path:t}"
  print -r -- "$path"
}

staging_compose_capture() {
  macos_compose_base "$release_path" "$MACOS_STAGING_ENV" "$run_project"
  macos_run_capture docker "${MACOS_COMPOSE_ARGS[@]}" "$@"
}

assert_staging_running() {
  local running service
  running="$(staging_compose_capture ps --status running --services)"
  for service in db backend auto-submit-worker frontend nginx operator-nginx; do
    print -r -- "$running" | grep -Fx -- "$service" >/dev/null || macos_die "staging service is not running: $service"
  done
}

identity_prefix() {
  local check_name="$1" checked_at="$2"
  printf '%s' "{\"schemaVersion\":2,\"kind\":\"staging-check\",\"status\":\"passed\",\"check\":\"$(macos_json_escape "$check_name")\",\"runId\":\"$(macos_json_escape "$run_id")\",\"commit\":\"$(macos_json_escape "${run_commit:l}")\",\"project\":\"$(macos_json_escape "$run_project")\",\"hostId\":\"$(macos_json_escape "$run_host_id")\",\"hostOS\":\"darwin\",\"architecture\":\"arm64\",\"platform\":\"linux/arm64\",\"builtImageIdentitySha256\":\"$(macos_json_escape "$run_built_digest")\",\"startedAt\":\"$(macos_json_escape "$started_at")\",\"checkedAt\":\"$(macos_json_escape "$checked_at")\",\"secrets\":\"redacted\""
}

write_json_artifact() {
  local destination="$1" payload="$2"
  macos_write_atomic "$destination" "$payload"
  macos_checksummed_json "$destination"
  macos_check_checksum "$destination"
}

run_smtp() {
  [[ -n "$recipient" && "$recipient" == *@* && "$recipient" != *$'\n'* && "$recipient" != *$'\r'* ]] || macos_die "SMTP requires a recipient address"
  local destination checked_at result_file result probe_status recipient_domain sent_at payload
  destination="$(assert_output_path "$smtp_output")"
  assert_staging_running
  result_file="$(mktemp "$output_dir/.smtp-probe.XXXXXX")"
  chmod 600 "$result_file"
  # The selected backend image owns SMTP transport, TLS, and authentication.
  # Host code supplies only the non-secret recipient and records redacted data.
  staging_compose_capture exec -T backend uv run --no-sync python -m app.ops.preflight smtp --recipient "$recipient" > "$result_file"
  result="$(cat "$result_file")"
  rm -f -- "$result_file"
  probe_status="$(print -r -- "$result" | /usr/bin/python3 -c 'import json,sys; x=json.load(sys.stdin); print(x.get("status", ""))')"
  recipient_domain="$(print -r -- "$result" | /usr/bin/python3 -c 'import json,sys; x=json.load(sys.stdin); print(x.get("recipient_domain", ""))')"
  sent_at="$(print -r -- "$result" | /usr/bin/python3 -c 'import json,sys; x=json.load(sys.stdin); print(x.get("sent_at", ""))')"
  [[ "$probe_status" == passed && "$recipient_domain" =~ '^[A-Za-z0-9][A-Za-z0-9.-]{0,252}[A-Za-z0-9]$' && -n "$sent_at" ]] || macos_die "SMTP probe did not return a redacted passed result"
  macos_assert_fresh_timestamp "$sent_at"
  checked_at="$(macos_now_iso)"
  payload="$(identity_prefix smtp "$checked_at"),\"recipientDomain\":\"$(macos_json_escape "${recipient_domain:l}")\",\"sentAt\":\"$(macos_json_escape "$sent_at")\",\"probe\":\"real-smtp\",\"details\":{\"delivery\":\"backend-preflight\",\"recipient\":\"excluded\"}}"
  write_json_artifact "$destination" "$payload"
  macos_log "staging_external_check=passed check=smtp evidence=${destination:t} recipient_domain=${recipient_domain:l}"
}

validate_browser_url() {
  local value="$1" label="$2"
  [[ "$value" =~ '^https?://[^/@[:space:]]+(:[0-9]{1,5})?/?$' ]] || macos_die "$label must be an absolute HTTP(S) URL without credentials"
}

read_browser_report() {
  local report_path="$1" live_path="$2"
  [[ -f "$live_path" && -f "$live_path.sha256" ]] || macos_die "browser requires the exact staging live-image evidence"
  macos_check_checksum "$live_path"
  /usr/bin/python3 - "$report_path" "$live_path" "$run_id" "$run_commit" "$run_project" "$run_host_id" "$run_built_digest" "$started_at" "$candidate_url" "$operator_url" "$output_dir" <<'PY'
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

report_path, live_path, run_id, commit, project, host_id, identity_digest, started_at, candidate_url, operator_url, output_root = sys.argv[1:]
required_markers = {
    "operator-login",
    "exam-publish",
    "candidate-otp-login",
    "exam-start",
    "answer-autosave",
    "offline-draft-recovery",
    "takeover-conflict",
    "submit",
    "answer-release",
    "session-invalidation",
}
def reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise SystemExit("browser JSON contains duplicate keys")
        result[key] = value
    return result
def reject_non_finite(value):
    raise SystemExit("browser JSON contains NaN or Infinity")
def strict_load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=reject_duplicate_keys, parse_constant=reject_non_finite)
report = strict_load(report_path)
live = strict_load(live_path)
if not isinstance(report, dict) or report.get("kind") != "browser-e2e-report" or report.get("status") != "passed":
    raise SystemExit("browser report is not a passed browser-e2e-report")
def pick(data, *names):
    present = [name for name in names if name in data]
    if len(present) != 1:
        raise SystemExit("browser report identity is missing or duplicated")
    return data[present[0]]
if str(pick(report, "runId", "run_id")) != run_id or str(pick(report, "commit", "gitCommit", "git_commit")).lower() != commit.lower() or pick(report, "project", "composeProject", "compose_project") != project or pick(report, "hostId", "host_id") != host_id:
    raise SystemExit("browser report run identity does not match staging")
if pick(report, "builtImageIdentitySha256", "built_image_identity_sha256") != identity_digest:
    raise SystemExit("browser report image identity does not match staging")
report_candidate = pick(report, "candidateUrl", "candidate_url")
report_operator = pick(report, "operatorUrl", "operator_url")
if report_candidate != candidate_url or report_operator != operator_url:
    raise SystemExit("browser report URLs do not match the requested staging URLs")
markers = report.get("scenarioMarkers", report.get("scenario_markers"))
if not isinstance(markers, list) or set(markers) != required_markers or any(not isinstance(value, str) for value in markers):
    raise SystemExit("browser report is missing required business scenario markers")
report_live = report.get("liveImageIds", report.get("live_image_ids"))
if not isinstance(report_live, dict):
    raise SystemExit("browser report live image identity is missing")
if isinstance(live, dict) and isinstance(live.get("images"), dict):
    live_images = live["images"]
elif isinstance(live, list):
    live_images = {}
    for row in live:
        if not isinstance(row, dict):
            continue
        service = str(row.get("service") or row.get("Service") or "")
        if service in {"nginx", "operator-nginx"}:
            service = "gateway"
        elif service == "auto-submit-worker":
            service = "backend"
        image_id = str(row.get("id") or row.get("ID") or "")
        if service and image_id:
            live_images[service] = image_id
else:
    raise SystemExit("staging live image evidence is invalid")
if {str(key): str(value).lower() for key, value in report_live.items()} != {str(key): str(value).lower() for key, value in live_images.items()}:
    raise SystemExit("browser report live image identity does not match staging")
checked = report.get("checkedAt", report.get("checked_at"))
try:
    checked_at = datetime.fromisoformat(str(checked).replace("Z", "+00:00"))
    run_started_at = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
except (TypeError, ValueError) as exc:
    raise SystemExit("browser report timestamp is invalid") from exc
now = datetime.now(timezone.utc)
if checked_at.tzinfo is None or run_started_at.tzinfo is None or checked_at < run_started_at or checked_at > now + timedelta(minutes=5) or now - checked_at > timedelta(days=7):
    raise SystemExit("browser report timestamp is stale or outside this staging run")
report_digest = hashlib.sha256(Path(report_path).read_bytes()).hexdigest()
report_rel = Path(report_path).relative_to(Path(output_root)).as_posix()
print(json.dumps({
    "browser": str(report.get("browser") or report.get("browserName") or "chromium-desktop"),
    "browserName": str(report.get("browserName") or report.get("browser") or "chromium"),
    "url": report_candidate,
    "candidateUrl": report_candidate,
    "operatorUrl": report_operator,
    "browserE2eStatus": "passed",
    "browserReportPath": report_rel,
    "browserReportSha256": report_digest,
    "scenarioMarkers": sorted(required_markers),
    "liveImageIds": {str(key): str(value).lower() for key, value in live_images.items()},
    "details": {"mobileUat": "not-run", "reportKind": "browser-e2e-report"},
}, sort_keys=True, separators=(",", ":")))
PY
}

run_browser() {
  [[ -n "$candidate_url" && -n "$operator_url" && -n "$browser_report" ]] || macos_die "browser requires candidate/operator URLs and a checksummed browser E2E report"
  validate_browser_url "$candidate_url" candidate-url
  validate_browser_url "$operator_url" operator-url
  [[ "$candidate_url" == http://127.0.0.1:18080 && "$operator_url" == http://127.0.0.1:18081 ]] || macos_die "browser gate URLs must be the fixed staging candidate/operator endpoints"
  assert_staging_running
  [[ -n "$live_image_ids" ]] || macos_die "browser requires --live-image-ids from this staging run"
  live_image_ids="$(macos_resolve_path "$live_image_ids")"
  browser_report="$(macos_resolve_path "$browser_report")"
  [[ "$browser_report" == "$output_dir"/* && "$browser_report" != "$output_dir" ]] || macos_die "browser report must stay under the commit-scoped evidence directory"
  if [[ -n "$browser_command" ]]; then
    [[ -x "$browser_command" ]] || macos_die "browser command is not executable"
    "$browser_command" --run-id "$run_id" --commit "$run_commit" --project "$run_project" --host-id "$run_host_id" --candidate-url "$candidate_url" --operator-url "$operator_url" --live-image-ids "$live_image_ids" --report "$browser_report"
  fi
  [[ -f "$browser_report" && -f "$browser_report.sha256" && ! -L "$browser_report" ]] || macos_die "checksummed browser E2E report is missing"
  macos_check_checksum "$browser_report"
  local destination="$(assert_output_path "$browser_output")"
  [[ "$browser_report" != "$destination" ]] || macos_die "browser report and raw evidence must be different files"
  local report_details
  report_details="$(read_browser_report "$browser_report" "$live_image_ids")"
  checked_at="$(macos_now_iso)"
  payload="$(identity_prefix browser "$checked_at"),$(print -r -- "$report_details" | sed 's/^{//')"
  payload="${payload%?}}"
  write_json_artifact "$destination" "$payload"
  macos_log "staging_external_check=passed check=browser evidence=${destination:t} report=${browser_report:t} mobile_uat=not-run"
}

read_capacity_report() {
  local report_path="$1" expected_project="$2" live_path="$3"
  [[ -f "$report_path" && -f "$report_path.sha256" ]] || macos_die "capacity report and checksum are required"
  macos_check_checksum "$report_path"
  [[ -f "$live_path" && -f "$live_path.sha256" ]] || macos_die "capacity requires the exact staging live-image evidence"
  macos_check_checksum "$live_path"
  /usr/bin/python3 - "$report_path" "$live_path" "$run_id" "$run_commit" "$run_host_id" "$run_project" "$expected_project" "$started_at" <<'PY'
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

report_path, live_path, run_id, commit, host_id, staging_project, expected_project, started_at = sys.argv[1:]
def reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise SystemExit("capacity JSON contains duplicate keys")
        result[key] = value
    return result
def reject_non_finite(value):
    raise SystemExit("capacity JSON contains NaN or Infinity")
def strict_load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=reject_duplicate_keys, parse_constant=reject_non_finite)
report = strict_load(report_path)
live = strict_load(live_path)
if report.get("status") != "passed":
    raise SystemExit("capacity report status is not passed")
if report.get("failed_checks") != []:
    raise SystemExit("capacity report failed_checks is not an explicit empty list")
generated = report.get("generated_at") or report.get("generatedAt")
try:
    generated_at = datetime.fromisoformat(str(generated).replace("Z", "+00:00"))
    run_started_at = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
except (TypeError, ValueError) as exc:
    raise SystemExit("capacity report timestamp is invalid") from exc
now = datetime.now(timezone.utc)
if generated_at.tzinfo is None or run_started_at.tzinfo is None or generated_at < run_started_at or generated_at > now + timedelta(minutes=5) or now - generated_at > timedelta(days=7):
    raise SystemExit("capacity report timestamp is stale or outside this staging run")
identity = report.get("identity") if isinstance(report.get("identity"), dict) else report
source_run_id = str(identity.get("run_id") or identity.get("runId") or "")
if (
    not source_run_id
    or str(identity.get("commit", "")).lower() != commit.lower()
    or identity.get("host_os") not in {"darwin", "macos"}
    or identity.get("host_arch") not in {"arm64", "aarch64"}
):
    raise SystemExit("capacity report identity does not match staging run")
report_project = identity.get("compose_project") or report.get("compose_project")
if report_project != expected_project:
    raise SystemExit("capacity report project is not the explicitly approved project")
metrics = report.get("metrics")
if not isinstance(metrics, dict) or "errors" not in metrics or metrics.get("clients") != 100 or metrics.get("errors") != [] or metrics.get("submitted_count") != 100:
    raise SystemExit("capacity metrics did not satisfy 100-client zero-error threshold")
def required_metric(*names):
    present = [name for name in names if name in metrics]
    if len(present) != 1:
        raise SystemExit("capacity report is missing a required measured metric")
    value = metrics[present[0]]
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        raise SystemExit("capacity report contains an invalid measured metric")
    return value
start_p95 = required_metric("start_p95_ms", "startP95Ms")
save_p95 = required_metric("save_p95_ms", "saveP95Ms")
submit_p95 = required_metric("submit_p95_ms", "submitP95Ms")
max_connections = required_metric("max_database_connections", "maxDatabaseConnections")
heartbeat_age = required_metric("worker_heartbeat_age_seconds", "workerHeartbeatAgeSeconds")
images = report.get("final_images") or identity.get("final_images") or []
if isinstance(live, dict) and isinstance(live.get("images"), dict):
    live_images = live["images"]
elif isinstance(live, list):
    live_images = {}
    for row in live:
        if not isinstance(row, dict):
            continue
        service = str(row.get("service") or row.get("Service") or "")
        if service in {"nginx", "operator-nginx"}:
            service = "gateway"
        elif service == "auto-submit-worker":
            service = "backend"
        image_id = str(row.get("id") or row.get("ID") or "")
        if service and image_id:
            live_images[service] = image_id
else:
    live_images = None
if not isinstance(images, list) or not isinstance(live_images, dict):
    raise SystemExit("capacity image evidence is missing")
expected = {str(key): str(value).lower() for key, value in live_images.items()}
seen = {}
for row in images:
    if not isinstance(row, dict):
        raise SystemExit("capacity image row is invalid")
    service = str(row.get("service") or row.get("Service") or "")
    image_id = str(row.get("image_id") or row.get("id") or row.get("ID") or "")
    if service in {"nginx", "operator-nginx"}:
        service = "gateway"
    elif service == "auto-submit-worker":
        service = "backend"
    if service in expected:
        if image_id.lower() != expected[service]:
            raise SystemExit("capacity image ID does not match exact staging image")
        if service in seen and seen[service] != image_id.lower():
            raise SystemExit("capacity aliases resolve to different staging image IDs")
        seen[service] = image_id.lower()
if set(seen) != set(expected):
    raise SystemExit("capacity image evidence does not cover all exact staging images")
report_digest = hashlib.sha256(Path(report_path).read_bytes()).hexdigest()
report_rel = Path(report_path).relative_to(Path(live_path).parent).as_posix()
out = {
    "failed_checks": [],
    "metrics": {
        "run_id": source_run_id,
        "clients": 100,
        "errors": [],
        "submitted_count": metrics["submitted_count"],
        "start_p95_ms": start_p95,
        "save_p95_ms": save_p95,
        "submit_p95_ms": submit_p95,
        "max_database_connections": max_connections,
        "worker_heartbeat_age_seconds": heartbeat_age,
    },
    "thresholds": {
        "clients": 100,
        "error_count": 0,
        "start_p95_ms": 5000,
        "save_p95_ms": 2000,
        "submit_p95_ms": 3000,
        "max_database_connections": 40,
        "worker_heartbeat_age_seconds": 90,
    },
    "imageIds": seen,
    "details": {"capacityProject": report_project},
    "sourceMeasurementRunId": source_run_id,
    "sourceReportPath": report_rel,
    "sourceReportSha256": report_digest,
}
print(json.dumps(out, sort_keys=True, separators=(",", ":")))
PY
}

run_capacity() {
  [[ -n "$capacity_report" ]] || macos_die "capacity requires --capacity-report from a measured gate"
  [[ -n "$live_image_ids" ]] || macos_die "capacity requires --live-image-ids from this staging run"
  capacity_report="$(macos_resolve_path "$capacity_report")"
  [[ "$capacity_report" == "$output_dir"/* && "$capacity_report" != "$output_dir" ]] || macos_die "capacity source report must stay under the commit-scoped evidence directory"
  live_image_ids="$(macos_resolve_path "$live_image_ids")"
  destination="$(assert_output_path "$capacity_output")"
  if [[ -n "$capacity_command" ]]; then
    [[ -x "$capacity_command" ]] || macos_die "capacity command is not executable"
    # This is an argv-safe external producer. Its report is validated below;
    # command success alone is never interpreted as a passed gate.
    "$capacity_command" --run-id "$run_id" --commit "$run_commit" --project "$run_project" --live-image-ids "$live_image_ids" --report "$capacity_report"
  fi
  [[ -n "$capacity_project" ]] || capacity_project="$run_project"
  [[ "$capacity_project" == "$run_project" || "$capacity_project" == internal-exam-capacity || "$capacity_project" == internal-exam-capacity-* ]] || macos_die "capacity project must be staging or an explicitly approved isolated clone"
  details="$(read_capacity_report "$capacity_report" "$capacity_project" "$live_image_ids")"
  checked_at="$(macos_now_iso)"
  # `details` is an object; splice it after the common identity object without
  # allowing arbitrary producer fields into the raw evidence envelope.
  payload="$(identity_prefix capacity "$checked_at"),$(print -r -- "$details" | sed 's/^{//')"
  payload="${payload%?}}"
  write_json_artifact "$destination" "$payload"
  macos_log "staging_external_check=passed check=capacity evidence=${destination:t} clients=100 project=${capacity_project}"
}

case "$check" in
  smtp) run_smtp ;;
  browser) run_browser ;;
  capacity) run_capacity ;;
  all)
    run_smtp
    run_browser
    run_capacity
    ;;
esac
