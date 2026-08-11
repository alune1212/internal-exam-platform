#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
source "$SCRIPT_DIR/Common.zsh"

admin_token_file=""
root="${INTERNAL_EXAM_ROOT:-${HOME:?}/Library/Application Support/InternalExam}"
while (( $# > 0 )); do
  case "$1" in
    --admin-token-file|--token-file) (( $# >= 2 )) || macos_die "$1 requires a path"; admin_token_file="$2"; shift 2 ;;
    --root) (( $# >= 2 )) || macos_die "--root requires a path"; root="$2"; shift 2 ;;
    -h|--help) print -r -- "usage: $0 [--admin-token-file PATH] [--root ROOT]"; exit 0 ;;
    *) macos_die "unknown argument: $1"; exit 1 ;;
  esac
done

macos_assert_macos
[[ -n "$admin_token_file" ]] || macos_die "a secure --admin-token-file is required"
macos_assert_outside_worktree "$root" >/dev/null
macos_layout "$root"
macos_assert_protected_configuration "$root"
macos_docker_ready
macos_release_state "$MACOS_CURRENT_STATE"
release_path="$MACOS_STATE_PATH"
timestamp="$(macos_timestamp)"
working="$MACOS_LAYOUT_DIAGNOSTICS/.diagnostic-${timestamp}-$$"
archive="$MACOS_LAYOUT_DIAGNOSTICS/diagnostic-${timestamp}.tar.gz"
mkdir -p -- "$working"
chmod 700 "$working"
cleanup_diagnostics() {
  [[ -z "${header_file:-}" ]] || rm -f -- "$header_file"
  [[ -d "$working" ]] && rm -R -- "$working"
}
trap cleanup_diagnostics EXIT

macos_require_command curl
token=""
header_file=""
admin_token_file="$(macos_resolve_path "$admin_token_file")"
macos_secure_path "$admin_token_file"
token="$(tr -d '\r\n' < "$admin_token_file")"
[[ -n "$token" ]] || macos_die "diagnostic admin token is missing"
header_file="$(macos_mktemp internal-exam-diagnostics-header.XXXXXX)"
chmod 600 "$header_file"
print -r -- "header = \"X-Admin-Token: $token\"" > "$header_file"

operations_json="$working/operations.json"
operations_raw="$working/.operations.raw"
curl -sS --fail --connect-timeout 5 --max-time 20 -o "$operations_raw" \
  --config "$header_file" http://127.0.0.1:8081/api/admin/operations/snapshot
macos_redact_file "$operations_raw" "$operations_json"
rm -f -- "$operations_raw"

services_json="$working/services.jsonl"
macos_run_to_file "$services_json" docker compose --project-name "$MACOS_FORMAL_PROJECT" \
  --env-file "$MACOS_FORMAL_ENV" -f "$release_path/docker-compose.yml" ps --format json
cp -p -- "$release_path/release-manifest.json" "$working/release-manifest.json"
chmod 600 "$working/release-manifest.json"

raw_logs="$working/.logs.raw"
bounded_logs="$working/bounded-logs.txt"
macos_run_to_file "$raw_logs" docker compose --project-name "$MACOS_FORMAL_PROJECT" \
  --env-file "$MACOS_FORMAL_ENV" -f "$release_path/docker-compose.yml" logs --no-color --tail 500
macos_redact_file "$raw_logs" "$bounded_logs"
rm -f -- "$raw_logs"
head -c 1048576 -- "$bounded_logs" > "$bounded_logs.tmp"
mv -f -- "$bounded_logs.tmp" "$bounded_logs"
chmod 600 "$bounded_logs"

disk="$working/disk.txt"
disk_free_kib="$(df -Pk "$MACOS_LAYOUT_ROOT" | tail -n 1 | awk '{print $4}')"
[[ "$disk_free_kib" =~ '^[0-9]+$' ]] || macos_die "disk evidence is unavailable"
macos_write_atomic "$disk" "free_kib=$disk_free_kib"
chmod 600 "$disk"

manifest="$working/manifest.json"
manifest_files=""
while IFS= read -r -d '' file; do
  relative="${file#$working/}"
  [[ "$relative" == manifest.json ]] && continue
  digest="$(macos_sha256 "$file")"
  [[ -z "$manifest_files" ]] || manifest_files+=","
  manifest_files+="{\"name\":\"$(macos_json_escape "$relative")\",\"sha256\":\"$digest\"}"
done < <(find "$working" -type f -print0 | sort -z)
macos_write_atomic "$manifest" "{\"schemaVersion\":1,\"kind\":\"diagnostic-export\",\"createdAt\":\"$(macos_now_iso)\",\"releaseVersion\":\"$MACOS_STATE_VERSION\",\"gitCommit\":\"$MACOS_STATE_COMMIT\",\"project\":\"$MACOS_FORMAL_PROJECT\",\"logTailLinesPerService\":500,\"maxLogBytes\":1048576,\"secrets\":\"redacted\",\"files\":[$manifest_files]}"

macos_run_checked tar -C "${MACOS_LAYOUT_DIAGNOSTICS}" -czf "$archive" "$working:t"
chmod 600 "$archive"
macos_write_checksum "$archive"
rm -f -- "$header_file"
header_file=""
macos_log "diagnostic_export=$archive checksum=${archive}.sha256"
