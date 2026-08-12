param(
    [Parameter(Mandatory = $true)][string]$ReleasePath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
. "$PSScriptRoot\Common.ps1"

$releaseRoot = [System.IO.Path]::GetFullPath($ReleasePath)
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

function Get-OptionalManifestProperty {
    param(
        [Parameter(Mandatory = $true)][object]$ManifestObject,
        [Parameter(Mandatory = $true)][string]$Name
    )

    $property = $ManifestObject.PSObject.Properties[$Name]
    if ($null -eq $property) { return $null }
    return $property.Value
}

$manifestPath = Join-Path $releaseRoot "release-manifest.json"
$checksumsPath = Join-Path $releaseRoot "SHA256SUMS"
if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf) -or
    -not (Test-Path -LiteralPath $checksumsPath -PathType Leaf)) {
    throw "Release manifest or SHA256SUMS is missing."
}

$manifestFiles = @{}
$metadataFiles = @('release-manifest.json', 'SHA256SUMS')
foreach ($entry in Get-ChildItem -LiteralPath $releaseRoot -Force -Recurse) {
    $entryRelative = $entry.FullName.Substring($releaseRoot.Length).TrimStart('\', '/')
    if (($entry.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw "Release bundle contains a link or reparse point."
    }
    if ($entryRelative -match '[\x00-\x1f]' -or
        $entryRelative -match '(^|[\\/])\.\.([\\/]|$)' -or
        $entryRelative -match '(^|[\\/])\.([\\/]|$)') {
        throw "Release bundle contains an unsafe path entry."
    }
}

$manifest = Get-Content -Raw -LiteralPath $manifestPath -Encoding UTF8 | ConvertFrom-Json
if ($manifest.formatVersion -ne 1 -or
    $manifest.gitCommit -notmatch '^[0-9a-f]{40}$' -or
    [string]::IsNullOrWhiteSpace($manifest.applicationVersion) -or
    $manifest.hostOS -ne 'windows' -or
    $manifest.architecture -ne 'amd64' -or
    $manifest.targetPlatform -ne 'linux/amd64' -or
    $manifest.targetLinuxPlatform -ne 'linux/amd64' -or
    $manifest.host_os -ne 'windows' -or
    $manifest.target_platform -ne 'linux/amd64' -or
    $manifest.migration_head -ne $manifest.migrationHead -or
    [string]::IsNullOrWhiteSpace($manifest.migrationHead)) {
    throw "Release manifest identity is invalid."
}
$releaseIdentity = Assert-ReleaseImageIdentity -ReleasePath $releaseRoot -Manifest $manifest -AllowPending
# Architecture-specific final image references, IDs, OS, and architecture are
# validated by the shared helper; pending bundles contain no final references.
$builtIdentityPath = $releaseIdentity.IdentityPath
$builtIdentityRelative = 'ops/release/built-image-identity.json'
$builtIdentitySidecarRelative = 'ops/release/built-image-identity.json.sha256'
if (-not $manifest.files -or
    @($manifest.files | ForEach-Object { $_.path }) -notcontains $builtIdentityRelative -or
    @($manifest.files | ForEach-Object { $_.path }) -notcontains $builtIdentitySidecarRelative) {
    throw "Checksummed final image identity is not part of the release manifest."
}
$manifestIdentityStatus = [string](Get-ObjectPropertyValue -Object $manifest.builtImageIdentity -Names @('status'))
if ($manifestIdentityStatus -ne [string]$releaseIdentity.Identity.status) {
    throw "Release manifest final image identity status is inconsistent."
}
$baseImageReferences = Get-OptionalManifestProperty -ManifestObject $manifest -Name 'baseImageReferences'
if (-not $baseImageReferences) {
    $baseImageReferences = Get-OptionalManifestProperty -ManifestObject $manifest -Name 'base_image_references'
}
# Read the old field only as a compatibility alias; New-ReleaseBundle never
# emits it because image-digests.json contains base-image inputs.
if (-not $baseImageReferences) {
    $baseImageReferences = Get-OptionalManifestProperty -ManifestObject $manifest -Name 'imageDigests'
}
if (-not $baseImageReferences) { throw "Pinned base image references are missing." }
foreach ($image in $baseImageReferences.PSObject.Properties) {
    if ([string]$image.Value -notmatch '^([a-z0-9][a-z0-9._/-]{0,254})(:[A-Za-z0-9_][A-Za-z0-9._-]{0,127})?@sha256:[0-9a-f]{64}$') {
        throw "Pinned base image reference is not immutable."
    }
}
if (-not $manifest.imagePlatformSupport -or
    $manifest.imagePlatformSupport.schema_version -ne 1 -or
    @($manifest.imagePlatformSupport.required_platforms) -notcontains 'linux/arm64' -or
    @($manifest.imagePlatformSupport.required_platforms) -notcontains 'linux/amd64') {
    throw "Release manifest does not prove required ARM64 and AMD64 base-image support."
}
$bundledSecurityPath = Join-Path $releaseRoot 'release-evidence\security-scan.json'
if (-not $manifest.securityEvidence -or
    $manifest.securityEvidence.sha256 -notmatch '^[0-9a-f]{64}$' -or
    -not (Test-Path -LiteralPath $bundledSecurityPath -PathType Leaf)) {
    throw "Passed security evidence is missing from release bundle."
}
$bundledSecurityDigest = (Get-FileHash -Algorithm SHA256 -LiteralPath $bundledSecurityPath).Hash.ToLowerInvariant()
if ($bundledSecurityDigest -ne $manifest.securityEvidence.sha256) {
    throw "Bundled security evidence identity does not match the release manifest."
}
$bundledSecurityReport = Get-Content -Raw -LiteralPath $bundledSecurityPath -Encoding UTF8 | ConvertFrom-Json
if ($bundledSecurityReport.status -ne 'passed') { throw "Bundled security evidence did not pass release policy." }
$bundledSecurityCheckedAt = [DateTimeOffset]::Parse([string]$bundledSecurityReport.checked_at)
if ($bundledSecurityCheckedAt -gt [DateTimeOffset]::UtcNow.AddMinutes(5) -or
    [DateTimeOffset]::UtcNow - $bundledSecurityCheckedAt -gt [TimeSpan]::FromDays(8)) {
    throw "Bundled security evidence is outside the allowed release window."
}
if ($bundledSecurityCheckedAt.ToString('o') -ne ([DateTimeOffset]::Parse([string]$manifest.securityEvidence.checkedAt)).ToString('o')) {
    throw "Bundled security evidence timestamp does not match the release manifest."
}

$checksumRows = @{}
foreach ($line in Get-Content -LiteralPath $checksumsPath -Encoding UTF8) {
    if ($line -notmatch '^([0-9a-f]{64})  (.+)$') { throw "Invalid SHA256SUMS row." }
    $checksumRelative = [string]$Matches[2]
    $normalizedChecksumRelative = $checksumRelative.Replace('\', '/')
    if ([string]::IsNullOrWhiteSpace($checksumRelative) -or
        [System.IO.Path]::IsPathRooted($checksumRelative) -or
        $normalizedChecksumRelative.StartsWith('/') -or
        $normalizedChecksumRelative -match '[\x00-\x1f]' -or
        $normalizedChecksumRelative -match '(^|/)\.\.(/|$)' -or
        $normalizedChecksumRelative -match '(^|/)\.(/|$)') {
        throw "Unsafe release path in SHA256SUMS."
    }
    if ($checksumRows.ContainsKey($normalizedChecksumRelative)) {
        throw "Duplicate release path in SHA256SUMS."
    }
    $checksumRows[$normalizedChecksumRelative] = $Matches[1]
}

$expectedPaths = @($manifest.files | ForEach-Object { $_.path })
if ($checksumRows.Count -ne $expectedPaths.Count) { throw "Checksum file count does not match manifest." }
if (-not $manifest.releaseFileChecksums) { throw "Release file checksum metadata is missing." }
if (@($manifest.releaseFileChecksums.PSObject.Properties).Count -ne $expectedPaths.Count) {
    throw "Release file checksum metadata count does not match manifest."
}
foreach ($file in $manifest.files) {
    $relative = [string]$file.path
    $normalizedRelative = $relative.Replace('\', '/')
    if ([string]::IsNullOrWhiteSpace($relative) -or
        [System.IO.Path]::IsPathRooted($relative) -or
        $normalizedRelative.StartsWith('/') -or
        $normalizedRelative -match '[\x00-\x1f]' -or
        $normalizedRelative -match '(^|/)\.\.(/|$)' -or
        $normalizedRelative -match '(^|/)\.(/|$)') {
        throw "Unsafe release path in manifest."
    }
    if ($manifestFiles.ContainsKey($normalizedRelative)) {
        throw "Release manifest contains a duplicate path."
    }
    $manifestFiles[$normalizedRelative] = $true
    $fileName = [System.IO.Path]::GetFileName($normalizedRelative)
    if ((Test-ForbiddenReleaseFile -RelativePath $normalizedRelative -Name $fileName) -or
        $normalizedRelative -match '(^|/)(backups|diagnostics|evidence|data)(/|$)') {
        throw "Release bundle contains a forbidden runtime file."
    }
    $fullPath = Join-Path $releaseRoot $normalizedRelative
    if (-not (Test-Path -LiteralPath $fullPath -PathType Leaf)) { throw "Release file is missing." }
    $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $fullPath).Hash.ToLowerInvariant()
    if ($actual -ne $file.sha256 -or $actual -ne $checksumRows[$normalizedRelative]) {
        throw "Release checksum failed."
    }
    $metadataProperty = $manifest.releaseFileChecksums.PSObject.Properties[$normalizedRelative]
    if (-not $metadataProperty) { throw "Release file checksum metadata is missing." }
    $metadataDigest = [string]$metadataProperty.Value
    if ($actual -ne $metadataDigest) { throw "Release file metadata checksum failed." }
}
foreach ($metadata in $manifest.releaseFileChecksums.PSObject.Properties) {
    $metadataRelative = ([string]$metadata.Name).Replace('\', '/')
    if ([string]::IsNullOrWhiteSpace($metadataRelative) -or
        [System.IO.Path]::IsPathRooted($metadataRelative) -or
        $metadataRelative.StartsWith('/') -or
        $metadataRelative -match '[\x00-\x1f]' -or
        $metadataRelative -match '(^|/)\.\.(/|$)' -or
        $metadataRelative -match '(^|/)\.(/|$)' -or
        -not $manifestFiles.ContainsKey($metadataRelative)) {
        throw "Unsafe release checksum metadata path."
    }
}

# Also inspect files not listed by the manifest. A hand-edited bundle must not
# smuggle a credential or arbitrary payload through an unchecksummed path.
foreach ($candidate in Get-ChildItem -LiteralPath $releaseRoot -Force -File -Recurse) {
    $candidateRelative = $candidate.FullName.Substring($releaseRoot.Length).TrimStart('\', '/')
    if (Test-ForbiddenReleaseFile -RelativePath $candidateRelative -Name $candidate.Name) {
        throw "Release bundle contains a forbidden runtime file."
    }
    $normalizedCandidate = $candidateRelative.Replace('\', '/')
    if (-not $manifestFiles.ContainsKey($normalizedCandidate) -and
        $metadataFiles -notcontains $normalizedCandidate) {
        throw "Release bundle contains an unmanifested file."
    }
}

Write-Output "release_bundle_valid version=$($manifest.applicationVersion) commit=$($manifest.gitCommit)"
