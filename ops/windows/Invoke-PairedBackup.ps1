param(
    [ValidateSet('daily', 'pre-exam', 'post-exam', 'pre-upgrade')][string]$Kind = 'daily',
    [switch]$Opportunistic,
    [switch]$UnderWriterFence,
    [string]$DatasetId,
    [int]$WriterGeneration,
    [string]$SourceHostId,
    [string]$SecondCopyPath,
    [string]$Root = "C:\ProgramData\InternalExam"
)

. "$PSScriptRoot\Common.ps1"
Assert-WindowsHost
Assert-DockerReady
$layout = Initialize-InternalExamLayout -Root $Root
$state = Get-ReleaseState -Path $layout.CurrentRelease
$configuration = Read-DotEnv -Path $layout.FormalEnv
$operatorSubject = Get-ConfiguredOperatorSubject -Configuration $configuration
if ($Kind -in @('post-exam', 'pre-upgrade') -and
    ([string]::IsNullOrWhiteSpace($DatasetId) -or
     $WriterGeneration -lt 1 -or
     [string]::IsNullOrWhiteSpace($SourceHostId))) {
    throw 'Cross-host formal backups require dataset_id, writer_generation, and source_host_id.'
}
if ($UnderWriterFence -and
    ([string]::IsNullOrWhiteSpace($DatasetId) -or $WriterGeneration -lt 1 -or [string]::IsNullOrWhiteSpace($SourceHostId))) {
    throw 'A writer-fenced backup requires exact dataset_id, writer_generation, and source_host_id.'
}
$compose = Get-ComposeBaseArguments -ReleasePath $state.path -EnvPath $layout.FormalEnv -ProjectName 'internal-exam-formal'
$backupMount = "$($layout.Backups):/backups"
$arguments = $compose + @(
    'run', '--rm', '--no-deps', '--volume', $backupMount, 'backend',
    'uv', 'run', '--no-sync', 'python', '-m', 'app.ops.internal_backup',
    'container-backup', '--output-root', '/backups', '--media-root', '/app/learning-media',
    '--kind', $Kind, '--operator-subject', $operatorSubject,
    '--app-version', $state.applicationVersion
)
if ($Opportunistic) { $arguments += '--opportunistic' }
if ($DatasetId) { $arguments += @('--dataset-id', $DatasetId) }
if ($WriterGeneration -gt 0) { $arguments += @('--writer-generation', [string]$WriterGeneration) }
if ($SourceHostId) { $arguments += @('--source-host-id', $SourceHostId) }
if ($UnderWriterFence) { $arguments += '--under-writer-fence' }
$output = Invoke-DockerCaptured -Arguments $arguments
$result = ($output -split "`n" | Select-Object -Last 1) | ConvertFrom-Json

if ($result.status -eq 'passed' -and $Kind -eq 'post-exam') {
    if ([string]::IsNullOrWhiteSpace($SecondCopyPath)) {
        throw 'A post-exam backup requires the configured encrypted second-copy path.'
    }
    $secondFullPath = [System.IO.Path]::GetFullPath($SecondCopyPath)
    $secondMount = "${secondFullPath}:/second-copy"
    Invoke-DockerChecked -Arguments ($compose + @(
        'run', '--rm', '--no-deps', '--volume', $backupMount, '--volume', $secondMount,
        'backend', 'uv', 'run', '--no-sync', 'python', '-m', 'app.ops.internal_backup',
        'sync-second-copy', "/backups/$($result.backup_id)", '/second-copy'
    ))
    Invoke-DockerChecked -Arguments ($compose + @(
        'exec', '-T', 'backend', 'uv', 'run', '--no-sync', 'python', '-m',
        'app.ops.operator_control', 'record-lifecycle', '--lifecycle-action',
        'second_copy_sync_completed', '--operator-subject', $operatorSubject,
        '--target', $result.backup_id, '--artifact', "$($result.backup_id).second-copy.json"
    ))
}

Write-Output "paired_backup status=$($result.status) reason=$($result.reason) backup=$($result.backup_id)"
