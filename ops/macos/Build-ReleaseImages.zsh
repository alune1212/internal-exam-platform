#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
source "$SCRIPT_DIR/Common.zsh"

release_path=""
while (( $# > 0 )); do
  case "$1" in
    --release-path|--release) (( $# >= 2 )) || macos_die "$1 requires a path"; release_path="$2"; shift 2 ;;
    -h|--help) print -r -- "usage: $0 --release-path ABSOLUTE_RELEASE"; exit 0 ;;
    *) macos_die "unknown argument: $1"; exit 1 ;;
  esac
done

macos_assert_macos
[[ -n "$release_path" ]] || macos_die "--release-path is required"
[[ "$(uname -m)" == "arm64" ]] || macos_die "macOS release images must be built on ARM64"
release_path="$(macos_resolve_path "$release_path")"
[[ -d "$release_path" ]] || macos_die "release directory is missing"
"$SCRIPT_DIR/Test-ReleaseBundle.zsh" --release-path "$release_path" --allow-unbuilt >/dev/null
macos_docker_ready

manifest="$release_path/release-manifest.json"
git_commit="$(macos_json_get "$manifest" gitCommit)"
[[ "$git_commit" =~ '^[0-9a-fA-F]{40}$' ]] || macos_die "release Git commit is invalid"
identity_path="$release_path/ops/release/built-image-identity.json"
identity_status="$(macos_json_get "$identity_path" status 2>/dev/null || true)"
[[ "$identity_status" == pending ]] || macos_die "release image identity is not pending; refusing a tag rebuild"

macos_save_environment APP_IMAGE_REPOSITORY APP_VERSION_TAG DOCKER_DEFAULT_PLATFORM
build_env=""
cleanup_build_env() { [[ -z "$build_env" ]] || rm -f -- "$build_env"; macos_restore_environment; }
trap cleanup_build_env EXIT
export APP_IMAGE_REPOSITORY="${APP_IMAGE_REPOSITORY:-internal-exam-platform}"
export APP_VERSION_TAG="${git_commit:l}"
export DOCKER_DEFAULT_PLATFORM=linux/arm64
[[ "$APP_IMAGE_REPOSITORY" =~ '^[a-z0-9][a-z0-9._/-]{0,254}$' ]] || macos_die "image repository is invalid"
 # Compose requires an env-file.  Use a private transient build-only file;
 # formal credentials are never loaded by this command.
build_env="$(mktemp /tmp/internal-exam-build-env.XXXXXX)"
chmod 600 "$build_env"
print -r -- "APP_IMAGE_REPOSITORY=$APP_IMAGE_REPOSITORY" > "$build_env"
print -r -- "APP_VERSION_TAG=$APP_VERSION_TAG" >> "$build_env"
print -r -- "DOCKER_DEFAULT_PLATFORM=$DOCKER_DEFAULT_PLATFORM" >> "$build_env"
print -r -- "POSTGRES_PASSWORD=build-only-placeholder" >> "$build_env"
print -r -- "DATABASE_URL=postgresql+psycopg://exam:build-only-placeholder@db:5432/internal_exam" >> "$build_env"
print -r -- "ADMIN_PASSWORD=build-only-placeholder" >> "$build_env"
print -r -- "TOKEN_SECRET=build-only-placeholder" >> "$build_env"
macos_compose_base "$release_path" "$build_env" "$MACOS_FORMAL_PROJECT"
for image_reference in \
  "$APP_IMAGE_REPOSITORY-database:${git_commit:l}" \
  "$APP_IMAGE_REPOSITORY-backend:${git_commit:l}" \
  "$APP_IMAGE_REPOSITORY-frontend:${git_commit:l}" \
  "$APP_IMAGE_REPOSITORY-gateway:${git_commit:l}"; do
  if docker image inspect "$image_reference" >/dev/null 2>&1; then
    macos_die "release image tag already exists; refusing a mutable rebuild"
  fi
done
macos_run_checked docker "${MACOS_COMPOSE_ARGS[@]}" build --pull=false db backend frontend nginx

db_reference="$APP_IMAGE_REPOSITORY-database:${git_commit:l}"
backend_reference="$APP_IMAGE_REPOSITORY-backend:${git_commit:l}"
frontend_reference="$APP_IMAGE_REPOSITORY-frontend:${git_commit:l}"
gateway_reference="$APP_IMAGE_REPOSITORY-gateway:${git_commit:l}"
inspect_image() {
  local reference="$1" image_id image_os image_arch repo_tags
  image_id="$(macos_run_capture docker image inspect --format '{{.Id}}' "$reference")"
  image_os="$(macos_run_capture docker image inspect --format '{{.Os}}' "$reference")"
  image_arch="$(macos_run_capture docker image inspect --format '{{.Architecture}}' "$reference")"
  repo_tags="$(macos_run_capture docker image inspect --format '{{json .RepoTags}}' "$reference")"
  [[ "$image_id" =~ '^sha256:[0-9a-fA-F]{64}$' ]] || macos_die "built image ID is invalid"
  [[ "$image_os" == linux && "$image_arch" == arm64 ]] || macos_die "built image platform is not linux/arm64"
  [[ "$repo_tags" == *"\"$reference\""* ]] || macos_die "built image tag identity is missing"
  print -r -- "$image_id|$image_os|$image_arch"
}
db_identity="$(inspect_image "$db_reference")"
backend_identity="$(inspect_image "$backend_reference")"
frontend_identity="$(inspect_image "$frontend_reference")"
gateway_identity="$(inspect_image "$gateway_reference")"
db_id="${db_identity%%|*}"; db_tail="${db_identity#*|}"; db_os="${db_tail%%|*}"; db_arch="${db_tail#*|}"
backend_id="${backend_identity%%|*}"; backend_tail="${backend_identity#*|}"; backend_os="${backend_tail%%|*}"; backend_arch="${backend_tail#*|}"
frontend_id="${frontend_identity%%|*}"; frontend_tail="${frontend_identity#*|}"; frontend_os="${frontend_tail%%|*}"; frontend_arch="${frontend_tail#*|}"
gateway_id="${gateway_identity%%|*}"; gateway_tail="${gateway_identity#*|}"; gateway_os="${gateway_tail%%|*}"; gateway_arch="${gateway_tail#*|}"
identity_json="{\"schemaVersion\":1,\"status\":\"passed\",\"gitCommit\":\"${git_commit:l}\",\"applicationVersion\":\"$(macos_json_escape "$(macos_json_get "$manifest" applicationVersion)")\",\"platform\":\"linux/arm64\",\"images\":{\"db\":{\"reference\":\"$db_reference\",\"id\":\"$db_id\",\"os\":\"$db_os\",\"architecture\":\"$db_arch\"},\"backend\":{\"reference\":\"$backend_reference\",\"id\":\"$backend_id\",\"os\":\"$backend_os\",\"architecture\":\"$backend_arch\"},\"frontend\":{\"reference\":\"$frontend_reference\",\"id\":\"$frontend_id\",\"os\":\"$frontend_os\",\"architecture\":\"$frontend_arch\"},\"gateway\":{\"reference\":\"$gateway_reference\",\"id\":\"$gateway_id\",\"os\":\"$gateway_os\",\"architecture\":\"$gateway_arch\"}}}"
macos_write_atomic "$identity_path" "$identity_json"
macos_write_checksum "$identity_path"
identity_digest="$(macos_sha256 "$identity_path")"
built_refs_json="{\"db\":\"$db_reference\",\"backend\":\"$backend_reference\",\"frontend\":\"$frontend_reference\",\"gateway\":\"$gateway_reference\"}"
identity_meta_json="{\"path\":\"ops/release/built-image-identity.json\",\"sha256\":\"$identity_digest\",\"status\":\"passed\"}"
macos_json_replace_atomic "$manifest" imageDigests "$built_refs_json"
macos_json_replace_atomic "$manifest" builtImageIdentity "$identity_meta_json"
macos_replace_checksum_row "$release_path/SHA256SUMS" ops/release/built-image-identity.json "$identity_digest"
"$SCRIPT_DIR/Test-ReleaseBundle.zsh" --release-path "$release_path" --allow-unsealed >/dev/null
macos_log "images_built tag=${git_commit:l} platform=linux/arm64 identity=$identity_path next=Seal-Release"
