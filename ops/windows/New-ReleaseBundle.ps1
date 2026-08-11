param(
    [Parameter(Mandatory = $true)][string]$SourcePath,
    [Parameter(Mandatory = $true)][string]$DestinationPath,
    [Parameter(Mandatory = $true)][ValidatePattern('^[0-9]+\.[0-9]+\.[0-9]+([.-][0-9A-Za-z.-]+)?$')][string]$ApplicationVersion,
    [Parameter(Mandatory = $true)][ValidatePattern('^[0-9a-f]{40}$')][string]$GitCommit,
    [Parameter(Mandatory = $true)][string]$SecurityEvidencePath,
    [ValidateSet('windows')][string]$HostOS = 'windows',
    [ValidateSet('amd64')][string]$Architecture = 'amd64'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
. "$PSScriptRoot\Common.ps1"

$sourceRoot = [System.IO.Path]::GetFullPath($SourcePath)
$destinationRoot = [System.IO.Path]::GetFullPath($DestinationPath)
$securityEvidence = [System.IO.Path]::GetFullPath($SecurityEvidencePath)

$excludedDirectories = @(
    '.git', '.venv', '.runtime', 'node_modules', 'dist', 'backups', 'diagnostics',
    'evidence', 'security-evidence', 'test-results', 'playwright-report', 'data',
    '__pycache__'
)
$excludedFileNames = @(
    '.npmrc', '.pypirc', '.netrc', '.dockerconfigjson', '.git-credentials',
    'credentials', 'credentials.json', 'secrets', 'secrets.json',
    'id_rsa', 'id_dsa', 'id_ecdsa', 'id_ed25519',
    'private.key', 'private.pem', 'server.key', 'server.pem',
    'client.key', 'client.pem', 'ca.key', 'ca.pem'
)
$excludedFileExtensions = @(
    '.pem', '.key', '.pfx', '.p12', '.crt', '.cer', '.der', '.ppk', '.jks',
    '.keystore'
)

function Test-ForbiddenReleaseFile {
    param(
        [Parameter(Mandatory = $true)][string]$RelativePath,
        [Parameter(Mandatory = $true)][string]$Name
    )

    $normalizedRelative = $RelativePath.Replace('\', '/').ToLowerInvariant()
    $lowerName = $Name.ToLowerInvariant()
    # A checked-in example is intentionally safe; all other dotenv variants
    # are excluded before they can enter the release tree.
    if ($lowerName -eq '.env.example') { return $false }
    if ($lowerName -eq '.env' -or
        $lowerName -like '.env.*' -or
        $lowerName -like '*.env' -or
        $lowerName -like '*.env.*') {
        return $true
    }
    if ($excludedFileNames -contains $lowerName) { return $true }
    if ($excludedFileExtensions -contains [System.IO.Path]::GetExtension($lowerName)) {
        return $true
    }
    if ($normalizedRelative -match '(^|/)(credentials?|secrets?|private|certs?|keys?)(/|$)') {
        return $true
    }
    return $lowerName -match '(^|[-_.])(credential|secret|private(?:[-_.]?key)?|access[-_.]?(?:key|token)|password|passwd|token|authorization|cookie|session|service[-_.]?account|oauth)([-_.]|$)'
}

if (-not (Test-Path -LiteralPath $sourceRoot -PathType Container)) {
    throw "Source directory is missing."
}
$relativeDestination = [System.IO.Path]::GetRelativePath($sourceRoot, $destinationRoot)
$relativeSource = [System.IO.Path]::GetRelativePath($destinationRoot, $sourceRoot)
if ($relativeDestination -eq '.' -or
    (-not $relativeDestination.StartsWith('..') -and
        -not [System.IO.Path]::IsPathRooted($relativeDestination)) -or
    ($relativeSource -ne '.' -and
        -not $relativeSource.StartsWith('..') -and
        -not [System.IO.Path]::IsPathRooted($relativeSource))) {
    throw "Source and destination must be separate trees."
}

# The caller supplies the intended identity, but the source checkout is the
# authority.  A bundle from a dirty tree could silently include an untracked
# credential, so require the exact repository root, HEAD, and clean status.
$gitRoot = (& git -C $sourceRoot rev-parse --show-toplevel 2>$null | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($gitRoot)) {
    throw "Source Git metadata is unavailable."
}
try {
    $gitRoot = [System.IO.Path]::GetFullPath($gitRoot)
} catch {
    throw "Source Git metadata is invalid."
}
if (-not [string]::Equals($gitRoot.TrimEnd('\', '/'), $sourceRoot.TrimEnd('\', '/'), [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "SourcePath must be the Git worktree root."
}
$sourceHead = (& git -C $sourceRoot rev-parse --verify HEAD 2>$null | Out-String).Trim().ToLowerInvariant()
if ($LASTEXITCODE -ne 0 -or $sourceHead -notmatch '^[0-9a-f]{40}$' -or $sourceHead -ne $GitCommit.ToLowerInvariant()) {
    throw "Git commit does not match the source HEAD."
}
$gitStatus = @(& git -C $sourceRoot status --porcelain=v1 --untracked-files=all -- . 2>$null)
if ($LASTEXITCODE -ne 0) {
    throw "Source Git status is unavailable."
}
if ($gitStatus.Count -gt 0) {
    throw "Source tree must be clean before release bundling."
}

if (Test-ForbiddenReleaseFile -RelativePath ([System.IO.Path]::GetFileName($securityEvidence)) -Name ([System.IO.Path]::GetFileName($securityEvidence))) {
    throw "Security evidence filename is not allowed in a release bundle."
}
if (-not (Test-Path -LiteralPath $securityEvidence -PathType Leaf) -or
    -not (Test-Path -LiteralPath "$securityEvidence.sha256" -PathType Leaf)) {
    throw "Checksummed security evidence is required."
}
$securityReport = Get-Content -Raw -LiteralPath $securityEvidence -Encoding UTF8 | ConvertFrom-Json
if ($securityReport.status -ne 'passed') { throw "Security scan did not pass release policy." }
$securityCheckedAt = [DateTimeOffset]::Parse([string]$securityReport.checked_at)
if ($securityCheckedAt -gt [DateTimeOffset]::UtcNow.AddMinutes(5)) {
    throw "Security scan evidence timestamp is in the future."
}
if ([DateTimeOffset]::UtcNow - $securityCheckedAt -gt [TimeSpan]::FromDays(8)) {
    throw "Security scan evidence is older than eight days."
}
$securityDigest = (Get-FileHash -Algorithm SHA256 -LiteralPath $securityEvidence).Hash.ToLowerInvariant()
$securityChecksum = (Get-Content -Raw -LiteralPath "$securityEvidence.sha256" -Encoding ASCII).Trim()
if ($securityChecksum -notmatch "^$securityDigest  .+$") { throw "Security evidence checksum failed." }
if (Test-Path -LiteralPath $destinationRoot) { throw "Destination already exists: $destinationRoot" }
New-Item -ItemType Directory -Path $destinationRoot | Out-Null

# Enumerate the exact committed HEAD tree instead of walking the filesystem;
# ignored local files never enter the release inventory. Security evidence is
# intentionally added separately below.
$trackedFiles = @(& git -C $sourceRoot ls-tree -r --name-only HEAD 2>$null)
if ($LASTEXITCODE -ne 0 -or $trackedFiles.Count -eq 0) {
    throw "Source Git tree inventory is unavailable."
}
$sourceFiles = foreach ($trackedRelative in $trackedFiles) {
    $relative = ([string]$trackedRelative).Trim()
    if (-not $relative) { continue }
    $normalizedRelative = $relative.Replace('\', '/')
    if ([System.IO.Path]::IsPathRooted($normalizedRelative) -or
        $normalizedRelative.StartsWith('/') -or
        $normalizedRelative -match '(^|/)\.\.(/|$)' -or
        $normalizedRelative -match '(^|/)\.(/|$)' -or
        $normalizedRelative -match '[\x00-\x1f]') {
        throw "Source Git tree contains an unsafe path entry."
    }
    $segments = $normalizedRelative -split '/'
    if ($segments | Where-Object { $excludedDirectories -contains $_ }) { continue }
    $name = [System.IO.Path]::GetFileName($normalizedRelative)
    if ((Test-ForbiddenReleaseFile -RelativePath $normalizedRelative -Name $name) -or
        $name -like '*.pyc' -or $name -like '*.log') { continue }
    $sourceFile = Get-Item -LiteralPath (Join-Path $sourceRoot $normalizedRelative) -Force
    if (-not $sourceFile.PSIsContainer -and
        ($sourceFile.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -eq 0) {
        $sourceFile
        continue
    }
    throw "Source Git tree contains an unsupported file entry."
}

$manifestFiles = @()
$releaseFileChecksums = [ordered]@{}
foreach ($sourceFile in $sourceFiles) {
    $relative = $sourceFile.FullName.Substring($sourceRoot.Length).TrimStart('\', '/').Replace('\', '/')
    $target = Join-Path $destinationRoot $relative
    New-Item -ItemType Directory -Force -Path ([System.IO.Path]::GetDirectoryName($target)) | Out-Null
    Copy-Item -LiteralPath $sourceFile.FullName -Destination $target
    $digest = (Get-FileHash -Algorithm SHA256 -LiteralPath $target).Hash.ToLowerInvariant()
    $manifestFiles += [ordered]@{ path = $relative; sha256 = $digest; size = $sourceFile.Length }
    $releaseFileChecksums[$relative] = $digest
}

$releaseEvidencePath = Join-Path $destinationRoot 'release-evidence\security-scan.json'
New-Item -ItemType Directory -Force -Path ([System.IO.Path]::GetDirectoryName($releaseEvidencePath)) | Out-Null
Copy-Item -LiteralPath $securityEvidence -Destination $releaseEvidencePath
$manifestFiles += [ordered]@{
    path = 'release-evidence/security-scan.json'
    sha256 = $securityDigest
    size = (Get-Item -LiteralPath $releaseEvidencePath).Length
}
$releaseFileChecksums['release-evidence/security-scan.json'] = $securityDigest

# Reserve a fixed, checksummed final-image identity in every bundle.  The
# pending record prevents a post-build file from being injected without being
# represented in the release manifest; Build-ReleaseImages.ps1 replaces it
# only after it has inspected all four native Linux/AMD64 images.
$builtIdentityPath = Join-Path $destinationRoot 'ops\release\built-image-identity.json'
$pendingImages = [ordered]@{}
foreach ($imageName in @('db', 'backend', 'frontend', 'gateway')) {
    $pendingImages[$imageName] = [ordered]@{
        reference = ''
        id = ''
        os = 'linux'
        architecture = 'amd64'
    }
}
$pendingIdentity = [ordered]@{
    schemaVersion = 1
    schema_version = 1
    kind = 'final-image-identity'
    evidence = 'checksummed'
    status = 'pending'
    gitCommit = $GitCommit
    git_commit = $GitCommit
    applicationVersion = $ApplicationVersion
    application_version = $ApplicationVersion
    hostOS = $HostOS
    host_os = $HostOS
    architecture = $Architecture
    targetPlatform = "linux/$Architecture"
    target_platform = "linux/$Architecture"
    platform = "linux/$Architecture"
    images = $pendingImages
    finalImageReferences = [ordered]@{}
    final_image_references = [ordered]@{}
}
$pendingIdentityDigest = Write-ChecksummedJsonFile -Path $builtIdentityPath -Data $pendingIdentity
$pendingIdentitySidecarPath = "$builtIdentityPath.sha256"
$pendingIdentitySidecarDigest = (Get-FileHash -Algorithm SHA256 -LiteralPath $pendingIdentitySidecarPath).Hash.ToLowerInvariant()
$manifestFiles += [ordered]@{
    path = 'ops/release/built-image-identity.json'
    sha256 = $pendingIdentityDigest
    size = (Get-Item -LiteralPath $builtIdentityPath).Length
}
$manifestFiles += [ordered]@{
    path = 'ops/release/built-image-identity.json.sha256'
    sha256 = $pendingIdentitySidecarDigest
    size = (Get-Item -LiteralPath $pendingIdentitySidecarPath).Length
}
$releaseFileChecksums['ops/release/built-image-identity.json'] = $pendingIdentityDigest
$releaseFileChecksums['ops/release/built-image-identity.json.sha256'] = $pendingIdentitySidecarDigest

# imageDigests.json is retained as the pinned input filename; the manifest
# calls its contents baseImageReferences and never final app image refs.
$baseImageManifestPath = Join-Path $destinationRoot "ops\release\image-digests.json"
if (-not (Test-Path -LiteralPath $baseImageManifestPath -PathType Leaf)) { throw "Pinned image digest manifest is missing." }
$platformSupportPath = Join-Path $destinationRoot "ops\release\platform-support.json"
if (-not (Test-Path -LiteralPath $platformSupportPath -PathType Leaf)) { throw "Base-image platform support manifest is missing." }
$baseImageReferences = Get-Content -Raw -LiteralPath $baseImageManifestPath -Encoding UTF8 | ConvertFrom-Json
$platformSupport = Get-Content -Raw -LiteralPath $platformSupportPath -Encoding UTF8 | ConvertFrom-Json
if ($platformSupport.required_platforms -notcontains "linux/$Architecture") {
    throw "Release inputs do not prove support for linux/$Architecture."
}
foreach ($image in $baseImageReferences.PSObject.Properties) {
    if ([string]$image.Value -notmatch '^([a-z0-9][a-z0-9._/-]{0,254})(:[A-Za-z0-9_][A-Za-z0-9._-]{0,127})?@sha256:[0-9a-f]{64}$') {
        throw "Base image reference is not immutable."
    }
}
$migrationFile = Get-ChildItem -LiteralPath (Join-Path $destinationRoot 'backend\alembic\versions') -File -Filter '*.py' |
    Sort-Object Name | Select-Object -Last 1
if (-not $migrationFile) { throw "Alembic migration files are missing." }
$migrationSource = Get-Content -Raw -LiteralPath $migrationFile.FullName -Encoding UTF8
if ($migrationSource -notmatch 'revision:\s*str\s*=\s*["'']([^"'']+)["'']') { throw "Unable to determine Alembic migration head." }
$migrationHead = $Matches[1]
$manifest = [ordered]@{
    formatVersion = 1
    schema_version = 1
    applicationVersion = $ApplicationVersion
    application_version = $ApplicationVersion
    gitCommit = $GitCommit
    git_commit = $GitCommit
    createdAt = [DateTimeOffset]::UtcNow.ToString('o')
    imageTag = $GitCommit
    hostOS = $HostOS
    host_os = $HostOS
    architecture = $Architecture
    targetPlatform = "linux/$Architecture"
    target_platform = "linux/$Architecture"
    targetLinuxPlatform = "linux/$Architecture"
    migrationHead = $migrationHead
    migration_head = $migrationHead
    releaseFileChecksums = $releaseFileChecksums
    release_file_checksums = $releaseFileChecksums
    securityEvidence = [ordered]@{
        checkedAt = $securityReport.checked_at
        sha256 = $securityDigest
        hostOS = $HostOS
        architecture = $Architecture
        targetPlatform = "linux/$Architecture"
    }
    # These are pinned build inputs, not the application image identities.
    # Native AMD64 app image refs/IDs are recorded only after the image build.
    baseImageReferences = $baseImageReferences
    base_image_references = $baseImageReferences
    imageReferenceKind = 'base-input'
    image_reference_kind = 'base-input'
    imagePlatformSupport = $platformSupport
    builtImageIdentity = [ordered]@{
        path = 'ops/release/built-image-identity.json'
        sha256 = $pendingIdentityDigest
        status = 'pending'
    }
    built_image_identity = [ordered]@{
        path = 'ops/release/built-image-identity.json'
        sha256 = $pendingIdentityDigest
        status = 'pending'
    }
    finalImageReferences = [ordered]@{}
    final_image_references = [ordered]@{}
    imageReferences = [ordered]@{}
    image_references = [ordered]@{}
    files = @($manifestFiles | Sort-Object path)
}
$manifest | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $destinationRoot 'release-manifest.json') -Encoding UTF8

$checksumLines = foreach ($file in ($manifest.files | Sort-Object path)) { "$($file.sha256)  $($file.path)" }
$checksumLines | Set-Content -LiteralPath (Join-Path $destinationRoot 'SHA256SUMS') -Encoding ASCII

& (Join-Path $destinationRoot 'ops\windows\Test-ReleaseBundle.ps1') -ReleasePath $destinationRoot
if (-not $?) { throw "Generated release bundle did not validate." }
Write-Output $destinationRoot
