#!/usr/bin/env sh
set -eu

repository_root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
compose_file="$repository_root/docker-compose.yml"
e2e_compose_file="$repository_root/ops/e2e/docker-compose.e2e.yml"
env_template="$repository_root/ops/e2e/e2e.env"
runtime_dir="$repository_root/.runtime/e2e"
env_file="$runtime_dir/run.env"
browser_output_dir="$runtime_dir/browser-output"
project_name="internal-exam-e2e"

compose() {
  docker compose --project-name "$project_name" --env-file "$env_file" \
    -f "$compose_file" -f "$e2e_compose_file" "$@"
}

cleanup() {
  status=$?
  trap - EXIT INT TERM
  if [ -f "$env_file" ]; then
    compose down --volumes --remove-orphans || true
  fi
  rm -f -- "$env_file"
  exit "$status"
}
trap cleanup EXIT INT TERM

mkdir -p "$runtime_dir"
# Browser artifacts are evidence for this invocation only.  Remove the
# previous disposable result so a failed build cannot upload a stale pass.
rm -rf -- "$browser_output_dir"
mkdir -p "$browser_output_dir"
cp "$env_template" "$env_file"
{
  printf '%s\n' "E2E_REPOSITORY_ROOT=$repository_root"
  printf '%s\n' "E2E_RUNTIME_DIR=$runtime_dir"
  printf '%s\n' "E2E_BROWSER_OUTPUT_HOST_DIR=$browser_output_dir"
  printf '%s\n' "E2E_COMPOSE_FILE=$compose_file"
  printf '%s\n' "E2E_COMPOSE_OVERRIDE=$e2e_compose_file"
  printf '%s\n' "E2E_ENV_FILE=$env_file"
  printf '%s\n' "E2E_PROJECT_NAME=$project_name"
} >> "$env_file"
chmod 600 "$env_file"
compose down --volumes --remove-orphans
compose --profile browser-gate build db backend frontend nginx browser-e2e
compose up --detach --wait
compose exec -T backend uv run --no-sync python -m app.ops.e2e_seed
compose exec -T backend uv run --no-sync python -m app.ops.internal_backup \
  container-backup \
  --output-root /tmp/e2e-backups \
  --kind pre-exam \
  --operator-subject e2e-gate \
  --app-version e2e

compose --profile browser-gate run --rm --no-deps browser-e2e
