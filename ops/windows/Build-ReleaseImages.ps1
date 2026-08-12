param(
    [Parameter(Mandatory = $true)][string]$ReleasePath,
    [string]$ImageRepository = "internal-exam-platform"
)

. "$PSScriptRoot\Common.ps1"
Assert-WindowsHost
Assert-DockerReady
$resolvedRelease = [System.IO.Path]::GetFullPath($ReleasePath)
& (Join-Path $resolvedRelease 'ops\windows\Test-ReleaseBundle.ps1') -ReleasePath $resolvedRelease
if (-not $?) { throw "Release verification failed." }
$manifestPath = Join-Path $resolvedRelease 'release-manifest.json'
$manifest = Get-Content -Raw -LiteralPath $manifestPath -Encoding UTF8 | ConvertFrom-Json
$releaseIdentity = Assert-ReleaseImageIdentity -ReleasePath $resolvedRelease -Manifest $manifest -AllowPending
if ($releaseIdentity.Identity.status -ne 'pending') {
    throw "Release image identity is already passed; refusing a mutable tag rebuild."
}
if ($ImageRepository -notmatch '^[a-z0-9][a-z0-9._/-]{0,254}$') {
    throw "Image repository is invalid."
}

$previousRepository = $env:APP_IMAGE_REPOSITORY
$previousTag = $env:APP_VERSION_TAG
$gitCommit = [string](Get-ObjectPropertyValue -Object $manifest -Names @('git_commit', 'gitCommit'))
$applicationVersion = [string](Get-ObjectPropertyValue -Object $manifest -Names @('application_version', 'applicationVersion'))
$references = [ordered]@{
    db = "$ImageRepository-database:$gitCommit"
    backend = "$ImageRepository-backend:$gitCommit"
    frontend = "$ImageRepository-frontend:$gitCommit"
    gateway = "$ImageRepository-gateway:$gitCommit"
}
try {
    $env:APP_IMAGE_REPOSITORY = $ImageRepository
    $env:APP_VERSION_TAG = $gitCommit
    foreach ($reference in $references.Values) {
        & docker image inspect $reference *> $null
        if ($LASTEXITCODE -eq 0) {
            throw "Release image tag already exists; refusing a mutable rebuild: $reference"
        }
    }
    $arguments = @(
        'compose', '-f', (Join-Path $resolvedRelease 'docker-compose.yml'),
        'build', '--pull=false', '--platform', 'linux/amd64',
        'db', 'backend', 'frontend', 'nginx'
    )
    Invoke-DockerChecked -Arguments $arguments

    $images = [ordered]@{}
    foreach ($name in @('db', 'backend', 'frontend', 'gateway')) {
        $reference = [string]$references[$name]
        $raw = Invoke-DockerCaptured -Arguments @('image', 'inspect', '--format', '{{json .}}', $reference)
        $record = $raw | ConvertFrom-Json
        if ($record -is [array]) { $record = $record[0] }
        $imageID = [string](Get-ObjectPropertyValue -Object $record -Names @('Id', 'ID', 'id'))
        $imageOS = [string](Get-ObjectPropertyValue -Object $record -Names @('Os', 'OS', 'os'))
        $imageArchitecture = [string](Get-ObjectPropertyValue -Object $record -Names @('Architecture', 'architecture', 'arch'))
        if ($imageID -notmatch '^sha256:[0-9a-f]{64}$' -or
            $imageOS -cne 'linux' -or $imageArchitecture -cne 'amd64' -or
            @($record.RepoTags) -notcontains $reference) {
            throw "Built final image identity is not linux/amd64 or tag-bound: $name"
        }
        $images[$name] = [ordered]@{
            reference = $reference
            id = $imageID
            os = $imageOS
            architecture = $imageArchitecture
        }
    }

    $identity = [ordered]@{
        schemaVersion = 1
        schema_version = 1
        kind = 'final-image-identity'
        evidence = 'checksummed'
        status = 'passed'
        gitCommit = $gitCommit
        git_commit = $gitCommit
        applicationVersion = $applicationVersion
        application_version = $applicationVersion
        hostOS = 'windows'
        host_os = 'windows'
        architecture = 'amd64'
        targetPlatform = 'linux/amd64'
        target_platform = 'linux/amd64'
        platform = 'linux/amd64'
        images = $images
        finalImageReferences = [ordered]@{
            db = $references.db
            backend = $references.backend
            frontend = $references.frontend
            gateway = $references.gateway
        }
        final_image_references = [ordered]@{
            db = $references.db
            backend = $references.backend
            frontend = $references.frontend
            gateway = $references.gateway
        }
    }
    $identityDigest = Write-ChecksummedJsonFile -Path $releaseIdentity.IdentityPath -Data $identity
    $identitySidecarPath = "$($releaseIdentity.IdentityPath).sha256"
    $identitySidecarDigest = (Get-FileHash -Algorithm SHA256 -LiteralPath $identitySidecarPath).Hash.ToLowerInvariant()

    # Bind the exact final refs and identity checksum into the manifest.  The
    # input image-digests.json remains base-image provenance; it is never used
    # as a substitute for these four application image identities.
    $manifestIdentity = Get-ObjectPropertyValue -Object $manifest -Names @('builtImageIdentity', 'built_image_identity')
    Set-ObjectPropertyValue -Object $manifestIdentity -Name 'path' -Value 'ops/release/built-image-identity.json'
    Set-ObjectPropertyValue -Object $manifestIdentity -Name 'sha256' -Value $identityDigest
    Set-ObjectPropertyValue -Object $manifestIdentity -Name 'status' -Value 'passed'
    Set-ObjectPropertyValue -Object $manifest -Name 'builtImageIdentity' -Value $manifestIdentity
    Set-ObjectPropertyValue -Object $manifest -Name 'built_image_identity' -Value $manifestIdentity
    Set-ObjectPropertyValue -Object $manifest -Name 'finalImageReferences' -Value $identity.finalImageReferences
    Set-ObjectPropertyValue -Object $manifest -Name 'final_image_references' -Value $identity.final_image_references
    Set-ObjectPropertyValue -Object $manifest -Name 'imageReferences' -Value $identity.finalImageReferences
    Set-ObjectPropertyValue -Object $manifest -Name 'image_references' -Value $identity.final_image_references
    Set-ObjectPropertyValue -Object $manifest -Name 'imageDigests' -Value $identity.finalImageReferences
    Set-ObjectPropertyValue -Object $manifest -Name 'imageReferenceKind' -Value 'final-image-bound'
    Set-ObjectPropertyValue -Object $manifest -Name 'image_reference_kind' -Value 'final-image-bound'

    foreach ($file in @($manifest.files)) {
        if ($file.path -eq 'ops/release/built-image-identity.json') {
            $file.sha256 = $identityDigest
            $file.size = (Get-Item -LiteralPath $releaseIdentity.IdentityPath).Length
        } elseif ($file.path -eq 'ops/release/built-image-identity.json.sha256') {
            $file.sha256 = $identitySidecarDigest
            $file.size = (Get-Item -LiteralPath $identitySidecarPath).Length
        }
    }
    foreach ($checksumProperty in @(
        @{ Name = 'releaseFileChecksums'; Value = $manifest.releaseFileChecksums },
        @{ Name = 'release_file_checksums'; Value = $manifest.release_file_checksums }
    )) {
        $checksums = $checksumProperty.Value
        Set-ObjectPropertyValue -Object $checksums -Name 'ops/release/built-image-identity.json' -Value $identityDigest
        Set-ObjectPropertyValue -Object $checksums -Name 'ops/release/built-image-identity.json.sha256' -Value $identitySidecarDigest
        Set-ObjectPropertyValue -Object $manifest -Name $checksumProperty.Name -Value $checksums
    }
    $manifest | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $manifestPath -Encoding UTF8

    $checksumPath = Join-Path $resolvedRelease 'SHA256SUMS'
    $checksumLines = foreach ($file in ($manifest.files | Sort-Object path)) {
        "$($file.sha256)  $($file.path)"
    }
    $checksumLines | Set-Content -LiteralPath $checksumPath -Encoding UTF8
} finally {
    $env:APP_IMAGE_REPOSITORY = $previousRepository
    $env:APP_VERSION_TAG = $previousTag
}

& (Join-Path $resolvedRelease 'ops\windows\Test-ReleaseBundle.ps1') -ReleasePath $resolvedRelease
if (-not $?) { throw "Final image identity binding failed release verification." }
$bound = Assert-ReleaseImageIdentity -ReleasePath $resolvedRelease -Manifest (
    Get-Content -Raw -LiteralPath $manifestPath -Encoding UTF8 | ConvertFrom-Json
) -CheckLocalImages
Write-Output "images_built tag=$gitCommit platform=linux/amd64 identity=$($bound.IdentityPath) final_images=db,backend,frontend,gateway"
