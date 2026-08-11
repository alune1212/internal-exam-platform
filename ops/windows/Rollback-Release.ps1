param(
    [Parameter(Mandatory = $true)][ValidateSet('PreMigration', 'PostMigrationOrWrite')][string]$Mode,
    [Parameter(Mandatory = $true)][string]$Confirmation,
    [switch]$ProvenNoMigrationOrWrites,
    [switch]$AllowDestructiveRestore,
    [string]$DataLossConfirmation,
    [string]$Root = "C:\ProgramData\InternalExam"
)

. "$PSScriptRoot\Common.ps1"
Assert-WindowsHost
Assert-DockerReady
$layout = Get-InternalExamLayout -Root $Root
$current = Get-ReleaseState -Path $layout.CurrentRelease
$previous = Get-ReleaseState -Path $layout.PreviousRelease
& (Join-Path $previous.path 'ops\windows\Test-ReleaseBundle.ps1') -ReleasePath $previous.path | Out-Null
if (-not $?) { throw "Previous release checksum validation failed." }
$currentManifest = Get-Content -Raw -LiteralPath (Join-Path $current.path 'release-manifest.json') -Encoding UTF8 | ConvertFrom-Json
$previousManifest = Get-Content -Raw -LiteralPath (Join-Path $previous.path 'release-manifest.json') -Encoding UTF8 | ConvertFrom-Json
$currentIdentity = Assert-ReleaseImageIdentity -ReleasePath $current.path -Manifest $currentManifest -CheckLocalImages
$previousIdentity = Assert-ReleaseImageIdentity -ReleasePath $previous.path -Manifest $previousManifest -CheckLocalImages
if ($current.stagingEvidence -and (Test-Path -LiteralPath $current.stagingEvidence -PathType Leaf)) {
    $currentStagingEvidence = Assert-PassedEvidence -Path $current.stagingEvidence
    Assert-WindowsEvidenceIdentity -Evidence $currentStagingEvidence -ReleaseIdentity $currentIdentity -Label 'Windows rollback staging evidence'
}

$currentCompose = Get-ComposeBaseArguments -ReleasePath $current.path -EnvPath $layout.FormalEnv -ProjectName 'internal-exam-formal'
$previousCompose = Get-ComposeBaseArguments -ReleasePath $previous.path -EnvPath $layout.FormalEnv -ProjectName 'internal-exam-formal'
$lossBoundary = $null

if ($Mode -eq 'PreMigration') {
    if (-not $ProvenNoMigrationOrWrites -or $Confirmation -cne "ROLLBACK PRE-MIGRATION $($previous.applicationVersion)") {
        throw "Pre-migration rollback requires proof and exact confirmation."
    }
    Invoke-DockerChecked -Arguments ($currentCompose + @('down', '--remove-orphans'))
} else {
    if (-not $AllowDestructiveRestore -or $Confirmation -cne "RESTORE PAIRED BACKUP $($previous.applicationVersion)") {
        throw "Post-migration rollback requires destructive-restore authorization and exact confirmation."
    }
    if ($DataLossConfirmation -cne 'I UNDERSTAND POST-UPGRADE WRITES WILL BE DISCARDED') {
        throw "Post-migration rollback requires an exact typed data-loss confirmation."
    }
    $backupPath = [System.IO.Path]::GetFullPath($current.pairedBackupPath)
    $backupManifestPath = Join-Path $backupPath 'manifest.json'
    if (-not (Test-Path -LiteralPath $backupManifestPath -PathType Leaf)) { throw "Paired backup manifest is missing." }
    $backupManifest = Get-Content -Raw -LiteralPath $backupManifestPath -Encoding UTF8 | ConvertFrom-Json
    $lossBoundary = [string](Get-ObjectPropertyValue -Object $backupManifest -Names @('created_at', 'createdAt'))
    if ([string]::IsNullOrWhiteSpace($lossBoundary)) { throw "Paired backup loss boundary is missing." }
    $savedTag = $env:APP_VERSION_TAG
    try {
        $env:APP_VERSION_TAG = $previous.gitCommit
        Invoke-PortableMigrationValidation -ComposeArguments $previousCompose -BackupPath $backupPath | Out-Null
        Invoke-DockerChecked -Arguments ($currentCompose + @('down', '--remove-orphans'))
        Invoke-DockerChecked -Arguments ($previousCompose + @('up', '-d', 'db'))
        Invoke-DockerChecked -Arguments ($previousCompose + @('cp', (Join-Path $backupPath 'database.dump'), 'db:/tmp/internal-exam-rollback.dump'))
        Invoke-DockerChecked -Arguments ($previousCompose + @('exec', '-T', 'db', 'pg_restore', '--clean', '--if-exists', '--no-owner', '--no-privileges', '-U', 'exam', '-d', 'internal_exam', '/tmp/internal-exam-rollback.dump'))
        Invoke-DockerChecked -Arguments ($previousCompose + @('exec', '-T', 'db', 'rm', '-f', '/tmp/internal-exam-rollback.dump'))

        $mediaVolume = 'internal-exam-formal_learning_media'
        $gatewayImage = $previousIdentity.FinalImageReferences.gateway
        $backupMount = "${backupPath}:/backup:ro"
        Invoke-DockerChecked -Arguments @('run', '--rm', '--volume', "${mediaVolume}:/restore", '--volume', $backupMount, $gatewayImage, 'sh', '-c', 'find /restore -mindepth 1 -delete && tar -C /restore -xzf /backup/learning_media.tar.gz')
    } finally {
        $env:APP_VERSION_TAG = $savedTag
    }
}

$previous | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $layout.CurrentRelease -Encoding UTF8
$savedTag = $env:APP_VERSION_TAG
try {
    $env:APP_VERSION_TAG = $previous.gitCommit
    Assert-WriterFenceClearBeforeExpose -ComposeArguments $previousCompose
    Invoke-DockerChecked -Arguments ($previousCompose + @('up', '-d', '--no-build', '--remove-orphans'))
    Invoke-DockerCaptured -Arguments ($previousCompose + @('exec', '-T', 'backend', 'uv', 'run', '--no-sync', 'alembic', 'current')) | Out-Null
} finally {
    $env:APP_VERSION_TAG = $savedTag
}

Write-ChecksummedEvidence -Directory $layout.Evidence -Name 'rollback' -Data ([ordered]@{
    schemaVersion = 1; status = 'passed'; mode = $Mode
    kind = 'rollback'; version = $previous.applicationVersion; commit = $previous.gitCommit; gitCommit = $previous.gitCommit
    hostOS = 'windows'; host_os = 'windows'; architecture = 'amd64'; targetPlatform = 'linux/amd64'; target_platform = 'linux/amd64'
    builtImageIdentitySha256 = $previousIdentity.IdentityDigest
    imageReferences = $previousIdentity.FinalImageReferences
    imageIds = [ordered]@{
        db = (Get-ObjectPropertyValue -Object (Get-ReleaseImageEntry -Images $previousIdentity.Identity.images -Name 'db') -Names @('id', 'image_id', 'imageId'))
        backend = (Get-ObjectPropertyValue -Object (Get-ReleaseImageEntry -Images $previousIdentity.Identity.images -Name 'backend') -Names @('id', 'image_id', 'imageId'))
        frontend = (Get-ObjectPropertyValue -Object (Get-ReleaseImageEntry -Images $previousIdentity.Identity.images -Name 'frontend') -Names @('id', 'image_id', 'imageId'))
        gateway = (Get-ObjectPropertyValue -Object (Get-ReleaseImageEntry -Images $previousIdentity.Identity.images -Name 'gateway') -Names @('id', 'image_id', 'imageId'))
    }
    expectedLoss = if ($Mode -eq 'PostMigrationOrWrite') { 'post-upgrade-writes-after-paired-backup-boundary-discarded' } else { 'none' }
    lossBoundary = if ($Mode -eq 'PostMigrationOrWrite') { $lossBoundary } else { $null }
    dataLossConfirmation = if ($Mode -eq 'PostMigrationOrWrite') { 'I UNDERSTAND POST-UPGRADE WRITES WILL BE DISCARDED' } else { $null }
    restoredVersion = $previous.applicationVersion; restoredCommit = $previous.gitCommit
    pairedBackupRestored = ($Mode -eq 'PostMigrationOrWrite')
}) | Out-Null
Write-Output "rollback_completed mode=$Mode version=$($previous.applicationVersion)"
