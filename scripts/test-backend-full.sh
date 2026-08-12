#!/usr/bin/env bash

set -Eeuo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
compose_file="$repo_root/docker-compose.test.yml"
project_name="internal-exam-platform-test"
database_url="postgresql+psycopg://exam:local-dev-postgres-password@127.0.0.1:55432/internal_exam_test"
uv_cache_dir="${UV_CACHE_DIR:-$repo_root/.uv-cache}"

cleanup() {
  docker compose \
    --project-name "$project_name" \
    --file "$compose_file" \
    down --volumes --remove-orphans >/dev/null 2>&1 || true
}

trap cleanup EXIT INT TERM
cleanup

docker compose \
  --project-name "$project_name" \
  --file "$compose_file" \
  up --detach --wait postgres-test

cd "$repo_root/backend"

python3 "$repo_root/scripts/check-legacy-contracts.py"

ENVIRONMENT=development \
DATABASE_URL="$database_url" \
UV_CACHE_DIR="$uv_cache_dir" \
uv run alembic upgrade head

ENVIRONMENT=development \
DATABASE_URL="$database_url" \
POSTGRES_TEST_DATABASE_URL="$database_url" \
UV_CACHE_DIR="$uv_cache_dir" \
uv run pytest "$@"
