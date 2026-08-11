param(
    [Parameter(Mandatory = $true)][string]$SecondCopyBackupPath,
    [string]$Root = "C:\ProgramData\InternalExam"
)

. "$PSScriptRoot\Common.ps1"
Assert-WindowsHost
Assert-DockerReady
$layout = Get-InternalExamLayout -Root $Root
$state = Get-ReleaseState -Path $layout.CurrentRelease
$manifest = Get-Content -Raw -LiteralPath (Join-Path $state.path 'release-manifest.json') -Encoding UTF8 | ConvertFrom-Json
$releaseIdentity = Assert-ReleaseImageIdentity -ReleasePath $state.path -Manifest $manifest -CheckLocalImages
$configuration = Read-DotEnv -Path $layout.FormalEnv
$operatorSubject = Get-ConfiguredOperatorSubject -Configuration $configuration
$suffix = [DateTimeOffset]::UtcNow.ToString('yyyyMMddHHmmss').ToLowerInvariant()
$project = "internal-exam-restore-verify-$suffix"
$compose = Get-ComposeBaseArguments -ReleasePath $state.path -EnvPath $layout.FormalEnv -ProjectName $project
$formalCompose = Get-ComposeBaseArguments -ReleasePath $state.path -EnvPath $layout.FormalEnv -ProjectName 'internal-exam-formal'
$backupPath = [System.IO.Path]::GetFullPath($SecondCopyBackupPath)
$backupMount = "${backupPath}:/backup:ro"
$savedTag = $env:APP_VERSION_TAG
$hadTag = Test-Path Env:APP_VERSION_TAG
$status = 'failed'

try {
    $env:APP_VERSION_TAG = $state.gitCommit
    Invoke-DockerChecked -Arguments ($compose + @('up', '-d', '--wait', 'db'))
    Invoke-PortableMigrationValidation -ComposeArguments $compose -BackupPath $backupPath | Out-Null
    Invoke-DockerChecked -Arguments ($compose + @('cp', (Join-Path $backupPath 'database.dump'), 'db:/tmp/restore.dump'))
    Invoke-DockerChecked -Arguments ($compose + @('exec', '-T', 'db', 'pg_restore', '--clean', '--if-exists', '--no-owner', '--no-privileges', '-U', 'exam', '-d', 'internal_exam', '/tmp/restore.dump'))
    $mediaVolume = "${project}_learning_media"
    $gatewayImage = $releaseIdentity.FinalImageReferences.gateway
    Invoke-DockerChecked -Arguments @('run', '--rm', '--volume', "${mediaVolume}:/restore", '--volume', $backupMount, $gatewayImage, 'tar', '-C', '/restore', '-xzf', '/backup/learning_media.tar.gz')
    Invoke-DockerChecked -Arguments ($compose + @(
        'run', '--rm', '--no-deps', '--volume', $backupMount, 'backend',
        'uv', 'run', '--no-sync', 'python', '-m', 'app.ops.internal_backup',
        'verify-restored', '/backup', '--media-root', '/app/learning-media'
    ))
    $status = 'passed'
} finally {
    Invoke-DockerChecked -Arguments ($compose + @('down', '-v', '--remove-orphans'))
    $evidencePath = Write-ChecksummedEvidence -Directory $layout.Evidence -Name 'restore-drill' -Data ([ordered]@{
        schemaVersion = 1; kind = 'second-copy-restore-drill'; status = $status
        checkedAt = [DateTimeOffset]::UtcNow.ToString('o')
        backupId = [System.IO.Path]::GetFileName($backupPath); disposableProject = $project
        formalProjectChanged = $false; secrets = 'excluded'
    })
    if ($status -eq 'passed') {
        Invoke-DockerChecked -Arguments ($formalCompose + @(
            'exec', '-T', 'backend', 'uv', 'run', '--no-sync', 'python', '-m',
            'app.ops.operator_control', 'record-lifecycle', '--lifecycle-action',
            'restore_drill_completed', '--operator-subject', $operatorSubject,
            '--target', [System.IO.Path]::GetFileName($backupPath),
            '--artifact', [System.IO.Path]::GetFileName($evidencePath)
        ))
    }
    if ($hadTag) { $env:APP_VERSION_TAG = $savedTag } else { Remove-Item Env:APP_VERSION_TAG -ErrorAction SilentlyContinue }
}

Write-Output "restore_drill status=$status backup=$([System.IO.Path]::GetFileName($backupPath))"
