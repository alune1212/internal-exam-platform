param(
    [Parameter(Mandatory = $true)][string]$ReleasePath,
    [Parameter(Mandatory = $true)][string]$PairedBackupPath,
    [Parameter(Mandatory = $true)][string]$StagingEvidence,
    [Parameter(Mandatory = $true)][string]$Confirmation,
    [string]$Root = "C:\ProgramData\InternalExam"
)

. "$PSScriptRoot\Common.ps1"
Assert-WindowsHost
Assert-DockerReady
$layout = Get-InternalExamLayout -Root $Root
Assert-ProtectedConfigurationAcl -ConfigurationPath $layout.Configuration
& "$PSScriptRoot\Test-ReleaseBundle.ps1" -ReleasePath $ReleasePath | Out-Null
if (-not $?) { throw "Release verification failed." }
$manifest = Get-Content -Raw -LiteralPath (Join-Path $ReleasePath 'release-manifest.json') -Encoding UTF8 | ConvertFrom-Json
if ($Confirmation -cne "PROMOTE $($manifest.applicationVersion)") { throw "Exact promotion confirmation did not match." }
$releaseIdentity = Assert-ReleaseImageIdentity -ReleasePath $ReleasePath -Manifest $manifest -CheckLocalImages
$staging = Assert-PassedEvidence -Path $StagingEvidence
$stagingCommit = [string](Get-ObjectPropertyValue -Object $staging -Names @('git_commit', 'gitCommit', 'commit'))
if ([string]::IsNullOrWhiteSpace($stagingCommit)) {
    $stagingRelease = Get-ObjectPropertyValue -Object $staging -Names @('release', 'releaseIdentity')
    $stagingCommit = [string](Get-ObjectPropertyValue -Object $stagingRelease -Names @('git_commit', 'gitCommit', 'commit'))
}
if ($stagingCommit -cne $manifest.gitCommit) { throw "Staging evidence belongs to another commit." }
Assert-WindowsEvidenceIdentity -Evidence $staging -ReleaseIdentity $releaseIdentity -Label 'Windows staging evidence'

$backupFullPath = [System.IO.Path]::GetFullPath($PairedBackupPath)
$current = if (Test-Path -LiteralPath $layout.CurrentRelease) { Get-ReleaseState -Path $layout.CurrentRelease } else { $null }
$compose = Get-ComposeBaseArguments -ReleasePath $ReleasePath -EnvPath $layout.FormalEnv -ProjectName 'internal-exam-formal'
$backupMount = "${backupFullPath}:/backup:ro"
$previousTag = $env:APP_VERSION_TAG
try {
    $env:APP_VERSION_TAG = $manifest.gitCommit
    Invoke-PortableMigrationValidation -ComposeArguments $compose -BackupPath $backupFullPath | Out-Null
    Assert-WriterFenceClearBeforeExpose -ComposeArguments $compose
    Invoke-DockerChecked -Arguments ($compose + @('up', '-d', '--no-build', '--remove-orphans'))
    Invoke-DockerCaptured -Arguments ($compose + @('exec', '-T', 'backend', 'uv', 'run', '--no-sync', 'alembic', 'current')) | Out-Null
} finally {
    $env:APP_VERSION_TAG = $previousTag
}

if ($current) { $current | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $layout.PreviousRelease -Encoding UTF8 }
$newState = [ordered]@{
    applicationVersion = $manifest.applicationVersion
    gitCommit = $manifest.gitCommit
    path = [System.IO.Path]::GetFullPath($ReleasePath)
    promotedAt = [DateTimeOffset]::UtcNow.ToString('o')
    pairedBackupPath = $backupFullPath
    stagingEvidence = [System.IO.Path]::GetFullPath($StagingEvidence)
}
$newState | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $layout.CurrentRelease -Encoding UTF8
Write-ChecksummedEvidence -Directory $layout.Evidence -Name 'promotion' -Data ([ordered]@{
    schemaVersion = 1; status = 'passed'; kind = 'promotion'; version = $manifest.applicationVersion; commit = $manifest.gitCommit
    hostOS = 'windows'; host_os = 'windows'; architecture = 'amd64'; targetPlatform = 'linux/amd64'; target_platform = 'linux/amd64'
    builtImageIdentitySha256 = $releaseIdentity.IdentityDigest
    imageReferences = $releaseIdentity.FinalImageReferences
    imageIds = [ordered]@{
        db = (Get-ObjectPropertyValue -Object (Get-ReleaseImageEntry -Images $releaseIdentity.Identity.images -Name 'db') -Names @('id', 'image_id', 'imageId'))
        backend = (Get-ObjectPropertyValue -Object (Get-ReleaseImageEntry -Images $releaseIdentity.Identity.images -Name 'backend') -Names @('id', 'image_id', 'imageId'))
        frontend = (Get-ObjectPropertyValue -Object (Get-ReleaseImageEntry -Images $releaseIdentity.Identity.images -Name 'frontend') -Names @('id', 'image_id', 'imageId'))
        gateway = (Get-ObjectPropertyValue -Object (Get-ReleaseImageEntry -Images $releaseIdentity.Identity.images -Name 'gateway') -Names @('id', 'image_id', 'imageId'))
    }
    pairedBackupId = [System.IO.Path]::GetFileName($backupFullPath); stagingEvidenceId = [System.IO.Path]::GetFileName($StagingEvidence)
}) | Out-Null
Write-Output "promoted version=$($manifest.applicationVersion) commit=$($manifest.gitCommit)"
