#!/usr/bin/env sh
set -eu
umask 077

repository_root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
compose_file="$repository_root/docker-compose.yml"
e2e_compose_file="$repository_root/ops/e2e/docker-compose.e2e.yml"
env_template="$repository_root/ops/e2e/e2e.env"
runtime_dir="$repository_root/.runtime/e2e"
run_root="$runtime_dir/capacity-runs"
project_name="internal-exam-capacity"

mkdir -p "$run_root"
run_dir=$(mktemp -d "$run_root/run-XXXXXXXXXXXX")
run_id=$(basename "$run_dir")
evidence_dir="$run_dir/evidence"
env_file="$run_dir/capacity.env"
report_name="capacity-report-$run_id.json"
report_path="$evidence_dir/$report_name"
checksum_path="$report_path.sha256"
container_report="/tmp/$report_name"

git_commit=$(git -C "$repository_root" rev-parse HEAD 2>/dev/null || printf '%s' unknown)
host_os=$(uname -s | tr '[:upper:]' '[:lower:]')
host_arch=$(uname -m)
commit_state=clean
if [ "$git_commit" = unknown ] || [ -n "$(git -C "$repository_root" status --porcelain --untracked-files=all)" ]; then
  commit_state=dirty
fi

# The target is unique, but clear it before every attempt as a second guard
# against an interrupted prior process or an accidentally reused path.
mkdir -p "$evidence_dir"
rm -f "$report_path" "$checksum_path"
cp "$env_template" "$env_file"
chmod 600 "$env_file"
{
  # The browser service remains in the shared E2E override.  These exact,
  # non-secret values satisfy its required interpolation even though the
  # capacity run never enables the browser profile.
  printf '%s\n' "E2E_REPOSITORY_ROOT=$repository_root"
  printf '%s\n' "E2E_RUNTIME_DIR=$runtime_dir"
  printf '%s\n' "E2E_BROWSER_OUTPUT_HOST_DIR=$evidence_dir"
  printf '%s\n' "E2E_COMPOSE_FILE=$compose_file"
  printf '%s\n' "E2E_COMPOSE_OVERRIDE=$e2e_compose_file"
  printf '%s\n' "E2E_ENV_FILE=$env_file"
  printf '%s\n' "E2E_PROJECT_NAME=$project_name"
  printf '%s\n' "CAPACITY_RUN_ID=$run_id"
  printf '%s\n' "CAPACITY_PROJECT_NAME=$project_name"
  printf '%s\n' "CAPACITY_GIT_COMMIT=$git_commit"
  printf '%s\n' "CAPACITY_COMMIT_STATE=$commit_state"
  printf '%s\n' "CAPACITY_HOST_OS=$host_os"
  printf '%s\n' "CAPACITY_HOST_ARCH=$host_arch"
} >> "$env_file"

compose() {
  docker compose --project-name "$project_name" --env-file "$env_file" \
    -f "$compose_file" -f "$e2e_compose_file" "$@"
}

checksum_file() {
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$1" | awk '{print $1}'
  elif command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  else
    return 1
  fi
}

write_failure_evidence() {
  if [ -s "$report_path" ] && [ -s "$checksum_path" ]; then
    expected=$(awk 'NR == 1 {print $1}' "$checksum_path")
    actual=$(checksum_file "$report_path" 2>/dev/null || true)
    if [ -n "$expected" ] && [ "$actual" = "$expected" ]; then
      chmod 600 "$report_path" "$checksum_path"
      return 0
    fi
  fi
  rm -f "$report_path" "$checksum_path"
  {
    printf '{\n'
    printf '  "schema_version": 2,\n'
    printf '  "status": "failed",\n'
    printf '  "commit": "%s",\n' "$git_commit"
    printf '  "commit_state": "%s",\n' "$commit_state"
    printf '  "host_os": "%s",\n' "$host_os"
    printf '  "host_arch": "%s",\n' "$host_arch"
    printf '  "run_directory": "%s",\n' "$run_id"
    printf '  "compose_project": "%s",\n' "$project_name"
    printf '  "docker_platform": "unknown",\n'
    printf '  "final_images": [],\n'
    printf '  "base_url": "http://nginx",\n'
    printf '  "identity": {"run_id": "%s", "commit": "%s", "commit_state": "%s", "host_os": "%s", "host_arch": "%s", "run_directory": "%s", "compose_project": "%s", "docker_platform": "unknown", "final_images": []},\n' "$run_id" "$git_commit" "$commit_state" "$host_os" "$host_arch" "$run_id" "$project_name"
    printf '  "warmup": {"performed": false, "measured": false, "cold_start_recovery": "separate-gate", "errors": []},\n'
    printf '  "failed_checks": ["capacity-command"],\n'
    printf '  "error": "capacity command did not produce a report"\n'
    printf '}\n'
  } > "$report_path"
  digest=$(checksum_file "$report_path") || return 1
  printf '%s  %s\n' "$digest" "$(basename "$report_path")" > "$checksum_path"
  chmod 600 "$report_path" "$checksum_path"
}

cleanup() {
  status=$?
  trap - EXIT INT TERM
  set +e
  write_failure_evidence
  compose down --volumes --remove-orphans >/dev/null 2>&1
  rm -f "$env_file"
  exit "$status"
}
trap cleanup EXIT INT TERM

# A measured capacity result is only useful when it can be tied to an exact
# reproducible source revision.  Refuse before spending time building the
# disposable stack; the trap still emits checksummed failure evidence.
if [ "$commit_state" != clean ]; then
  printf '%s\n' 'capacity gate requires a clean, known Git revision' >&2
  exit 1
fi

# This down is scoped to the disposable project and clears any stale
# containers/volumes before the measured run starts.
compose down --volumes --remove-orphans
compose build db backend frontend nginx
compose up --detach --wait

docker_platform=$(docker info --format '{{.OSType}}/{{.Architecture}}' 2>/dev/null || printf '%s' unknown)
case "$docker_platform" in
  linux/aarch64) docker_platform=linux/arm64 ;;
  linux/x86_64) docker_platform=linux/amd64 ;;
esac
image_evidence=$(compose images --format json 2>/dev/null || printf '%s' '[]')
[ "$image_evidence" = null ] && image_evidence='[]'

capacity_status=0
compose exec -T backend uv run --no-sync python -m app.ops.capacity_gate \
  --base-url http://nginx --clients 100 \
  --run-id "$run_id" \
  --commit "$git_commit" \
  --commit-state "$commit_state" \
  --host-os "$host_os" \
  --host-arch "$host_arch" \
  --run-directory "$run_id" \
  --compose-project "$project_name" \
  --docker-platform "$docker_platform" \
  --image-evidence "$image_evidence" \
  --output "$container_report" || capacity_status=$?

# Copy both passing and failed reports.  The Python gate writes a report on
# runtime exceptions; the trap above creates a non-sensitive fallback if the
# container itself fails before Python can run.
compose cp "backend:$container_report" "$report_path" >/dev/null 2>&1 || true
compose cp "backend:$container_report.sha256" "$checksum_path" >/dev/null 2>&1 || true
if ! write_failure_evidence; then
  capacity_status=1
fi
if [ ! -s "$report_path" ] || [ ! -s "$checksum_path" ]; then
  capacity_status=1
fi

exit "$capacity_status"
