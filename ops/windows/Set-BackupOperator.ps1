param(
    [Parameter(Mandatory = $true)][ValidateSet('Enabled', 'Disabled')][string]$State,
    [Parameter(Mandatory = $true)][string]$Confirmation,
    [string]$Root = "C:\ProgramData\InternalExam"
)

. "$PSScriptRoot\Common.ps1"
Assert-WindowsHost
Assert-DockerReady
$layout = Get-InternalExamLayout -Root $Root
Assert-ProtectedConfigurationAcl -ConfigurationPath $layout.Configuration
$configuration = Read-DotEnv -Path $layout.FormalEnv
$expectedConfirmation = if ($State -eq 'Enabled') { 'ENABLE BACKUP OPERATOR' } else { 'DISABLE BACKUP OPERATOR' }
if ($Confirmation -cne $expectedConfirmation) { throw "Exact backup-operator confirmation did not match." }
if (-not $configuration.ContainsKey('BACKUP_OPERATOR_USERNAME') -or
    -not $configuration.ContainsKey('BACKUP_OPERATOR_PASSWORD') -or
    -not $configuration.ContainsKey('PRIMARY_OPERATOR_USERNAME') -or
    -not $configuration.ContainsKey('PRIMARY_OPERATOR_PASSWORD') -or
    [string]::IsNullOrWhiteSpace($configuration.BACKUP_OPERATOR_USERNAME) -or
    [string]::IsNullOrWhiteSpace($configuration.BACKUP_OPERATOR_PASSWORD) -or
    [string]::IsNullOrWhiteSpace($configuration.PRIMARY_OPERATOR_USERNAME) -or
    [string]::IsNullOrWhiteSpace($configuration.PRIMARY_OPERATOR_PASSWORD)) {
    throw "Primary and backup operator credentials are not configured."
}

$state = Get-ReleaseState -Path $layout.CurrentRelease
$compose = Get-ComposeBaseArguments -ReleasePath $state.path -EnvPath $layout.FormalEnv -ProjectName 'internal-exam-formal'
$oldValue = $configuration.BACKUP_OPERATOR_ENABLED
$newValue = if ($State -eq 'Enabled') { 'true' } else { 'false' }
$operatorSubject = if ($State -eq 'Enabled') {
    $configuration.PRIMARY_OPERATOR_USERNAME
} else {
    if ($oldValue -notmatch '^(?i:true|1|yes)$') { throw 'Disabling backup operator requires the currently enabled backup operator.' }
    $configuration.BACKUP_OPERATOR_USERNAME
}
$operatorPassword = if ($State -eq 'Enabled') { $configuration.PRIMARY_OPERATOR_PASSWORD } else { $configuration.BACKUP_OPERATOR_PASSWORD }
$savedTag = $env:APP_VERSION_TAG
try {
    $env:APP_VERSION_TAG = $state.gitCommit
    Assert-OperatorLoginState -Username $operatorSubject -Password $operatorPassword -ExpectedSuccess:$true
    Set-DotEnvValueAtomic -Path $layout.FormalEnv -Name 'BACKUP_OPERATOR_ENABLED' -Value $newValue
    Invoke-DockerChecked -Arguments ($compose + @('up', '-d', '--no-deps', '--no-build', '--force-recreate', 'backend'))

    if ($State -eq 'Enabled') {
        # Enabling switches the active audit subject to backup.  Prove both
        # sides of the credential boundary after backend recreation.
        Assert-OperatorLoginState -Username $configuration.BACKUP_OPERATOR_USERNAME -Password $configuration.BACKUP_OPERATOR_PASSWORD -ExpectedSuccess:$true
        Assert-OperatorLoginState -Username $configuration.PRIMARY_OPERATOR_USERNAME -Password $configuration.PRIMARY_OPERATOR_PASSWORD -ExpectedSuccess:$false
    } else {
        # Disabling switches the active audit subject back to primary.  Prove
        # backup is rejected and primary still authenticates.
        Assert-OperatorLoginState -Username $configuration.BACKUP_OPERATOR_USERNAME -Password $configuration.BACKUP_OPERATOR_PASSWORD -ExpectedSuccess:$false
        Assert-OperatorLoginState -Username $configuration.PRIMARY_OPERATOR_USERNAME -Password $configuration.PRIMARY_OPERATOR_PASSWORD -ExpectedSuccess:$true
    }
    Invoke-DockerChecked -Arguments ($compose + @('exec', '-T', 'backend', 'uv', 'run', '--no-sync', 'python', '-m', 'app.ops.operator_control', 'record-backup-operator', '--operator-subject', $operatorSubject, '--target', $configuration.BACKUP_OPERATOR_USERNAME, '--enabled', $newValue))
} catch {
    Set-DotEnvValueAtomic -Path $layout.FormalEnv -Name 'BACKUP_OPERATOR_ENABLED' -Value $oldValue
    try { Invoke-DockerChecked -Arguments ($compose + @('up', '-d', '--no-deps', '--no-build', '--force-recreate', 'backend')) } catch { }
    throw
} finally {
    $env:APP_VERSION_TAG = $savedTag
}

Write-ChecksummedEvidence -Directory $layout.Evidence -Name 'backup-operator' -Data ([ordered]@{
    schemaVersion = 1; status = 'passed'; enabled = ($State -eq 'Enabled')
    changedAt = [DateTimeOffset]::UtcNow.ToString('o'); target = $configuration.BACKUP_OPERATOR_USERNAME
}) | Out-Null
Write-Output "backup_operator_enabled=$newValue backend_recreated=true"
