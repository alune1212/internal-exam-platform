#!/bin/zsh
# Capture the small browser smoke required while a fresh generation-1 writer is
# still private.  This command never starts/stops Compose, runs staging E2E, or
# performs mobile UAT.  It only probes an already-running target-maintenance
# endpoint and writes a passed artifact after Chromium/Playwright succeeds.
set -euo pipefail
setopt no_nomatch
umask 077

SCRIPT_DIR="${0:A:h}"
source "$SCRIPT_DIR/Common.zsh"

root="${INTERNAL_EXAM_ROOT:-${HOME:?}/Library/Application Support/InternalExam}"
release_arg=""
browser_source=""
output_arg=""
candidate_url="http://127.0.0.1:28080"
operator_url="http://127.0.0.1:28081"

usage() {
  print -r -- "usage: $0 --browser-source CLEAN_EXACT_COMMIT_SOURCE [--release-path INSTALLED_RELEASE] [--output-path EVIDENCE] [--candidate-url http://127.0.0.1:28080] [--operator-url http://127.0.0.1:28081] [--root ABSOLUTE_ROOT]"
  print -r -- "Captures only browser-smoke against the already-running private generation-1 maintenance endpoints; it never claims staging E2E or mobile UAT."
}

while (( $# > 0 )); do
  case "$1" in
    --root) (( $# >= 2 )) || macos_die "--root requires a path"; root="$2"; shift 2 ;;
    --release-path|--release) (( $# >= 2 )) || macos_die "$1 requires a path"; release_arg="$2"; shift 2 ;;
    --browser-source|--source-path|--source) (( $# >= 2 )) || macos_die "$1 requires a path"; browser_source="$2"; shift 2 ;;
    --output-path|--evidence-path|--output) (( $# >= 2 )) || macos_die "$1 requires a path"; output_arg="$2"; shift 2 ;;
    --candidate-url) (( $# >= 2 )) || macos_die "--candidate-url requires the exact loopback URL"; candidate_url="$2"; shift 2 ;;
    --operator-url) (( $# >= 2 )) || macos_die "--operator-url requires the exact loopback URL"; operator_url="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) macos_die "unknown argument: $1"; exit 1 ;;
  esac
done

macos_assert_macos
[[ -n "$browser_source" ]] || macos_die "--browser-source is required"
[[ "$candidate_url" == http://127.0.0.1:28080 ]] || macos_die "candidate URL must be exactly http://127.0.0.1:28080"
[[ "$operator_url" == http://127.0.0.1:28081 ]] || macos_die "operator URL must be exactly http://127.0.0.1:28081"
macos_assert_outside_worktree "$root" >/dev/null
macos_layout "$root"
macos_assert_protected_configuration "$root"
macos_read_cutover_identity
macos_acquire_lock "$MACOS_LAYOUT_STATE/.operation.lock"

temporary_payload=""
cleanup_browser_smoke() {
  local exit_status=$?
  [[ -z "$temporary_payload" ]] || rm -f -- "$temporary_payload"
  macos_release_lock
  return "$exit_status"
}
trap cleanup_browser_smoke EXIT

macos_secure_path "$MACOS_LAYOUT_EVIDENCE"
[[ "$(stat -f '%Lp' -- "$MACOS_LAYOUT_EVIDENCE")" == 700 ]] || macos_die "formal evidence directory must be owner-only mode 0700"

bootstrap_intent="$(macos_formal_writer_bootstrap_intent_path)"
current_state="$MACOS_CURRENT_STATE"
[[ -f "$bootstrap_intent" && -f "$bootstrap_intent.sha256" ]] || macos_die "pending generation-1 bootstrap intent is missing"
[[ -f "$current_state" && -f "$current_state.sha256" ]] || macos_die "pending generation-1 current state is missing"
macos_secure_path "$bootstrap_intent"
macos_secure_path "$current_state"
macos_check_checksum "$bootstrap_intent"
macos_check_checksum "$current_state"
plutil -convert json -o - -- "$bootstrap_intent" >/dev/null 2>&1 || macos_die "bootstrap intent JSON is invalid"
plutil -convert json -o - -- "$current_state" >/dev/null 2>&1 || macos_die "current release state JSON is invalid"

[[ "$(macos_json_get "$bootstrap_intent" kind 2>/dev/null || true)" == formal-writer-bootstrap-intent ]] || macos_die "bootstrap intent kind is invalid"
[[ "$(macos_json_get "$bootstrap_intent" status 2>/dev/null || true)" == prepared ]] || macos_die "bootstrap intent is not pending"
[[ "$(macos_json_get "$bootstrap_intent" emptyDataset 2>/dev/null || true)" == true && "$(macos_json_get "$bootstrap_intent" maintenanceOnly 2>/dev/null || true)" == true && "$(macos_json_get "$bootstrap_intent" maintenanceBindIp 2>/dev/null || true)" == 127.0.0.1 ]] || macos_die "bootstrap intent is not the private empty generation-1 reservation"
[[ "$(macos_json_get "$bootstrap_intent" writerGeneration 2>/dev/null || true)" == 1 ]] || macos_die "browser smoke requires writer generation 1"
[[ "$(macos_json_get "$bootstrap_intent" hostId 2>/dev/null || true)" == "$MACOS_HOST_ID" ]] || macos_die "bootstrap intent hostId does not match the current host identity"

[[ "$(macos_json_get "$current_state" kind 2>/dev/null || true)" == formal-writer-current ]] || macos_die "current state kind is invalid"
[[ "$(macos_json_get "$current_state" bootstrapPending 2>/dev/null || true)" == true ]] || macos_die "browser smoke requires a pending generation-1 writer"
[[ "$(macos_json_get "$current_state" writerGeneration 2>/dev/null || true)" == 1 ]] || macos_die "current writer generation is not 1"
[[ "$(macos_json_get "$current_state" hostId 2>/dev/null || true)" == "$MACOS_HOST_ID" ]] || macos_die "current state hostId does not match the current host identity"

pending_release_path="$(macos_json_get "$current_state" path 2>/dev/null || true)"
pending_commit="$(macos_json_get "$current_state" gitCommit 2>/dev/null || true)"
pending_version="$(macos_json_get "$current_state" applicationVersion 2>/dev/null || true)"
[[ "$pending_commit" =~ '^[0-9a-fA-F]{40}$' ]] || macos_die "pending release commit is invalid"
[[ "$pending_version" =~ '^[0-9]+\.[0-9]+\.[0-9]+([.-][0-9A-Za-z.-]+)?$' ]] || macos_die "pending release version is invalid"
[[ "$(macos_json_get "$bootstrap_intent" releaseCommit 2>/dev/null || true)" == "${pending_commit:l}" ]] || macos_die "bootstrap intent release commit does not match current state"
[[ "$(macos_json_get "$bootstrap_intent" releaseVersion 2>/dev/null || true)" == "$pending_version" ]] || macos_die "bootstrap intent release version does not match current state"
[[ "$(macos_json_get "$bootstrap_intent" releasePath 2>/dev/null || true)" == "$pending_release_path" ]] || macos_die "bootstrap intent release path does not match current state"

if [[ -n "$release_arg" ]]; then
  release_path="$(macos_resolve_path "$release_arg")"
else
  release_path="$(macos_resolve_path "$pending_release_path")"
fi
[[ "$release_path" == "$pending_release_path" ]] || macos_die "selected release path is not the exact pending writer release"
[[ "$release_path" == "$MACOS_LAYOUT_RELEASES"/* && "$release_path" != "$MACOS_LAYOUT_RELEASES"/*/* && -d "$release_path" && ! -L "$release_path" ]] || macos_die "pending release must be an installed direct child of ROOT/releases"
"$SCRIPT_DIR/Test-ReleaseBundle.zsh" --release-path "$release_path" >/dev/null
release_manifest="$release_path/release-manifest.json"
[[ "$(macos_json_get "$release_manifest" gitCommit 2>/dev/null || true)" == "${pending_commit:l}" ]] || macos_die "release manifest commit does not match the pending writer"
[[ "$(macos_json_get "$release_manifest" applicationVersion 2>/dev/null || true)" == "$pending_version" ]] || macos_die "release manifest version does not match the pending writer"

browser_source="$(macos_resolve_path "$browser_source")"
[[ -d "$browser_source" && ! -L "$browser_source" ]] || macos_die "browser source directory is missing or a symlink"
browser_source_root="$(git -C "$browser_source" rev-parse --show-toplevel 2>/dev/null || true)"
[[ "$browser_source_root" == "$browser_source" ]] || macos_die "browser source must be the repository root of a clean exact-commit Git worktree"
source_head="$(git -C "$browser_source" rev-parse --verify HEAD 2>/dev/null || true)"
[[ "${source_head:l}" == "${pending_commit:l}" ]] || macos_die "browser source HEAD is not the exact pending release commit"
git -C "$browser_source" diff-index --quiet HEAD -- >/dev/null 2>&1 || macos_die "browser source has tracked modifications"
[[ -z "$(git -C "$browser_source" status --porcelain --untracked-files=all 2>/dev/null)" ]] || macos_die "browser source has untracked files"

frontend_source="$browser_source/frontend"
[[ -d "$frontend_source" && -f "$frontend_source/package.json" && -f "$frontend_source/package-lock.json" ]] || macos_die "browser source frontend package and lockfile are required"
playwright_bin="$frontend_source/node_modules/.bin/playwright"
playwright_module="$frontend_source/node_modules/playwright"
[[ -x "$playwright_bin" && -d "$playwright_module" && ! -L "$playwright_module" ]] || macos_die "browser source must contain the installed local Playwright runner"
macos_require_command node

temporary_payload="$(macos_mktemp internal-exam-browser-smoke.XXXXXX)"
chmod 600 "$temporary_payload"
browser_payload="$(cd "$frontend_source" && NODE_PATH="$frontend_source/node_modules" BROWSER_SMOKE_SOURCE="$browser_source" BROWSER_SMOKE_RELEASE="$release_path" BROWSER_SMOKE_COMMIT="${pending_commit:l}" BROWSER_SMOKE_VERSION="$pending_version" BROWSER_SMOKE_HOST_ID="$MACOS_HOST_ID" BROWSER_SMOKE_CANDIDATE_URL="$candidate_url" BROWSER_SMOKE_OPERATOR_URL="$operator_url" macos_run_capture node - "$candidate_url" "$operator_url" "${pending_commit:l}" "$pending_version" "$MACOS_HOST_ID" <<'NODE'
const { chromium } = require("playwright");

const [candidateUrl, operatorUrl, expectedCommit, expectedVersion, hostId] = process.argv.slice(2);
const staticTypes = new Set(["script", "stylesheet", "font", "image", "manifest", "media"]);

function originOf(value) {
  return new URL(value).origin;
}

async function smokePage(browser, label, url, pagePath, healthPath) {
  const expectedOrigin = originOf(url);
  const context = await browser.newContext();
  const externalOrigins = new Set();
  const staticFailures = [];
  let staticResourceCount = 0;
  const consoleErrors = [];
  const pageErrors = [];
  const requestFailures = [];
  await context.route("**/*", async (route) => {
    const requestUrl = new URL(route.request().url());
    if ((requestUrl.protocol === "http:" || requestUrl.protocol === "https:") && requestUrl.origin !== expectedOrigin) {
      externalOrigins.add(requestUrl.origin);
      await route.abort("blockedbyclient");
      return;
    }
    await route.continue();
  });
  const page = await context.newPage();
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push("console-error");
  });
  page.on("pageerror", () => pageErrors.push("pageerror"));
  page.on("requestfailed", (request) => {
    if (staticTypes.has(request.resourceType())) requestFailures.push(request.resourceType());
  });
  page.on("response", (response) => {
    if (staticTypes.has(response.request().resourceType())) staticResourceCount += 1;
    if (staticTypes.has(response.request().resourceType()) && response.status() >= 400) {
      staticFailures.push(response.request().resourceType());
    }
  });
  const checks = { health: "failed", page: "failed", console: "failed", pageerror: "failed", offlineStaticResources: "failed" };
  try {
    const pageResponse = await page.goto(`${url}${pagePath}`, { waitUntil: "domcontentloaded", timeout: 30_000 });
    if (!pageResponse || pageResponse.status() >= 400) throw new Error("page");
    await page.waitForTimeout(250);
    const bodyLength = await page.locator("body").innerText().then((value) => value.trim().length).catch(() => 0);
    if (bodyLength === 0) throw new Error("blank-page");
    checks.page = "passed";

    // Run the health probe from the loaded same-origin page so the browser's
    // CORS policy cannot turn a healthy loopback endpoint into a false failure.
    const healthResponse = await page.evaluate(async (target) => {
      const response = await fetch(target, { cache: "no-store" });
      return response.status;
    }, `${url}${healthPath}`);
    if (healthResponse !== 200) throw new Error("health");
    checks.health = "passed";

    if (consoleErrors.length !== 0) throw new Error("console");
    checks.console = "passed";
    if (pageErrors.length !== 0) throw new Error("pageerror");
    checks.pageerror = "passed";

    // Static assets must already be local and loaded before the browser is
    // taken offline.  Any external origin is blocked above and fails this
    // scoped browser-smoke; this is not a claim of offline exam support.
    await context.setOffline(true);
    const offlineBodyLength = await page.locator("body").innerText().then((value) => value.trim().length).catch(() => 0);
    await context.setOffline(false);
    if (offlineBodyLength === 0 || staticResourceCount === 0 || externalOrigins.size !== 0 || staticFailures.length !== 0 || requestFailures.length !== 0) {
      throw new Error("offline-static-resource");
    }
    checks.offlineStaticResources = "passed";
  } finally {
    await context.close();
  }
  return { label, checks, externalOrigins: [...externalOrigins].sort(), staticResourceCount, staticFailureCount: staticFailures.length, requestFailureCount: requestFailures.length };
}

(async () => {
  if (!/^https?:\/\/127\.0\.0\.1:(28080|28081)$/.test(candidateUrl) || !/^https?:\/\/127\.0\.0\.1:(28080|28081)$/.test(operatorUrl)) throw new Error("url");
  const browser = await chromium.launch({ headless: true });
  try {
    const candidate = await smokePage(browser, "candidate", candidateUrl, "/exams", "/api/health");
    const operator = await smokePage(browser, "operator", operatorUrl, "/admin/login", "/api/ready");
    const checkedAt = new Date().toISOString();
    process.stdout.write(JSON.stringify({
      schemaVersion: 1,
      kind: "browser-smoke",
      scope: "browser-smoke",
      status: "passed",
      browser: "chromium",
      runner: "playwright",
      gitCommit: expectedCommit,
      commit: expectedCommit,
      applicationVersion: expectedVersion,
      version: expectedVersion,
      hostId,
      hostOS: "darwin",
      architecture: "arm64",
      writerGeneration: 1,
      candidateUrl,
      operatorUrl,
      url: candidateUrl,
      checkedAt,
      checks: { health: "passed", page: "passed", console: "passed", pageerror: "passed", offlineStaticResources: "passed" },
      pages: [candidate, operator],
      stagingE2e: "not-run",
      mobileUat: "not-run",
      secrets: "redacted",
    }));
  } finally {
    await browser.close();
  }
})().catch((error) => {
  // Keep diagnostics generic: URLs, page content, and response bodies never
  // enter shell output or durable evidence.
  process.stderr.write(`formal browser smoke failed: ${error && error.name ? error.name : "runtime"}\n`);
  process.exitCode = 1;
});
NODE
)"
print -r -- "$browser_payload" > "$temporary_payload"
plutil -convert json -o - -- "$temporary_payload" >/dev/null 2>&1 || macos_die "Playwright browser smoke output is invalid JSON"
[[ "$(macos_json_get "$temporary_payload" kind 2>/dev/null || true)" == browser-smoke && "$(macos_json_get "$temporary_payload" scope 2>/dev/null || true)" == browser-smoke && "$(macos_json_get "$temporary_payload" status 2>/dev/null || true)" == passed ]] || macos_die "browser smoke did not produce a passed browser-smoke result"
[[ "$(macos_json_get "$temporary_payload" gitCommit 2>/dev/null || true)" == "${pending_commit:l}" && "$(macos_json_get "$temporary_payload" applicationVersion 2>/dev/null || true)" == "$pending_version" ]] || macos_die "browser smoke release identity changed"
[[ "$(macos_json_get "$temporary_payload" hostId 2>/dev/null || true)" == "$MACOS_HOST_ID" && "$(macos_json_get "$temporary_payload" hostOS 2>/dev/null || true)" == darwin && "$(macos_json_get "$temporary_payload" architecture 2>/dev/null || true)" == arm64 && "$(macos_json_get "$temporary_payload" writerGeneration 2>/dev/null || true)" == 1 ]] || macos_die "browser smoke host identity is invalid"
[[ "$(macos_json_get "$temporary_payload" candidateUrl 2>/dev/null || true)" == "$candidate_url" && "$(macos_json_get "$temporary_payload" operatorUrl 2>/dev/null || true)" == "$operator_url" && "$(macos_json_get "$temporary_payload" url 2>/dev/null || true)" == "$candidate_url" ]] || macos_die "browser smoke URL binding is invalid"
[[ "$(macos_json_get "$temporary_payload" 'checks.health' 2>/dev/null || true)" == passed && "$(macos_json_get "$temporary_payload" 'checks.page' 2>/dev/null || true)" == passed && "$(macos_json_get "$temporary_payload" 'checks.console' 2>/dev/null || true)" == passed && "$(macos_json_get "$temporary_payload" 'checks.pageerror' 2>/dev/null || true)" == passed && "$(macos_json_get "$temporary_payload" 'checks.offlineStaticResources' 2>/dev/null || true)" == passed ]] || macos_die "browser smoke checks are incomplete"
checked_at="$(macos_json_get "$temporary_payload" checkedAt 2>/dev/null || true)"
macos_assert_fresh_timestamp "$checked_at"
[[ "$(macos_json_get "$temporary_payload" stagingE2e 2>/dev/null || true)" == not-run && "$(macos_json_get "$temporary_payload" mobileUat 2>/dev/null || true)" == not-run ]] || macos_die "browser smoke scope is not explicit"

if [[ -n "$output_arg" ]]; then
  output_path="$(macos_resolve_path "$output_arg")"
  [[ "$output_path:h" == "$MACOS_LAYOUT_EVIDENCE" ]] || macos_die "evidence output must be directly under ROOT/evidence"
  [[ "$output_path" != "$MACOS_LAYOUT_EVIDENCE"/*/* ]] || macos_die "evidence output must not escape the protected evidence directory"
  [[ ! -e "$output_path" && ! -e "$output_path.sha256" ]] || macos_die "refusing to overwrite existing browser evidence"
  macos_write_atomic "$output_path" "$browser_payload"
  macos_checksummed_json "$output_path"
else
  output_path="$(macos_write_evidence "$MACOS_LAYOUT_EVIDENCE" formal-browser-smoke "$browser_payload")"
fi
macos_secure_path "$output_path"
macos_check_checksum "$output_path"
macos_log "formal_browser_smoke status=passed scope=browser-smoke generation=1 evidence=$output_path candidate=$candidate_url operator=$operator_url staging_e2e=not-run mobile_uat=not-run"
