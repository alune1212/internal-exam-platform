param(
    [Parameter(Mandatory = $true)][string]$Confirmation,
    [string]$Root = "C:\ProgramData\InternalExam"
)

. "$PSScriptRoot\Common.ps1"
Assert-WindowsHost
Assert-DockerReady
if ($Confirmation -cne 'CLOSE ALL SESSIONS') { throw "Exact close-exam confirmation did not match." }
$layout = Get-InternalExamLayout -Root $Root
Assert-ProtectedConfigurationAcl -ConfigurationPath $layout.Configuration
$configuration = Read-DotEnv -Path $layout.FormalEnv
$operatorSubject = Get-ConfiguredOperatorSubject -Configuration $configuration
$operatorPassword = if ($operatorSubject -eq $configuration.BACKUP_OPERATOR_USERNAME) { $configuration.BACKUP_OPERATOR_PASSWORD } else { $configuration.PRIMARY_OPERATOR_PASSWORD }
$state = Get-ReleaseState -Path $layout.CurrentRelease
$compose = Get-ComposeBaseArguments -ReleasePath $state.path -EnvPath $layout.FormalEnv -ProjectName 'internal-exam-formal'

$savedTag = $env:APP_VERSION_TAG
$hadTag = Test-Path Env:APP_VERSION_TAG
$oldSecret = [string]$configuration.TOKEN_SECRET
$lockOwner = "session-closure-$([Guid]::NewGuid().ToString('N'))"
$lockAcquired = $false
$lockReleased = $false
$lockAcquiredAt = $null
$lockReleasedAt = $null
$lockReleaseError = $null
$operationError = $null
$recoveryError = $null
$status = 'failed'
$secretRotationAttempted = $false
$secretRestored = $false
$oldTokensRejected = $false
$readinessRecovered = $false
$newTokenIssued = $false
$auditRecorded = $false
$inProgressAttempts = $null
$randomBytes = New-Object byte[] 64
$newSecret = $null
$oldToken = $null
$headers = $null
$loginBody = @{ username = $operatorSubject; password = $operatorPassword } | ConvertTo-Json

try {
    # Compose commands must use the active release while the lock is held.
    $env:APP_VERSION_TAG = $state.gitCommit

    try {
        # Login writes an audit event and therefore must happen before the
        # backup-write freeze.  No readiness or mutable operation is checked
        # until the atomic acquire-backup command has succeeded below.
        $login = Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8081/api/admin/login' -ContentType 'application/json' -Body $loginBody
        $oldToken = $login.data.token
        if (-not $oldToken) { throw "Active operator authentication failed." }
        $headers = @{ 'X-Admin-Token' = $oldToken }

        $lockResult = Invoke-BackupWriteFreezeAcquire -ComposeArguments $compose -Owner $lockOwner
        $lockAcquired = $true
        $lockAcquiredAt = [DateTimeOffset]::UtcNow.ToString('o')

        # acquire-backup atomically checked zero in-progress attempts.  Keep
        # this second readiness check under the same freeze for an auditable
        # boundary and to detect an unhealthy service before rotation.
        $readiness = Invoke-RestMethod -Method Get -Uri 'http://127.0.0.1:8081/api/admin/operations/session-closure-readiness' -Headers $headers
        $inProgressAttempts = $readiness.data.in_progress_attempt_count
        if (-not $readiness.data.ready -or $readiness.data.in_progress_attempt_count -ne 0) {
            throw "Session closure refused because a formal attempt is still in progress."
        }
        Invoke-DockerChecked -Arguments ($compose + @('exec', '-T', 'backend', 'uv', 'run', '--no-sync', 'python', '-m', 'app.ops.operator_control', 'check-session-closure'))

        [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($randomBytes)
        $newSecret = [Convert]::ToBase64String($randomBytes)
        if ([string]::IsNullOrWhiteSpace($newSecret)) { throw "Unable to generate a new session secret." }
        $secretRotationAttempted = $true
        Set-DotEnvValueAtomic -Path $layout.FormalEnv -Name 'TOKEN_SECRET' -Value $newSecret
        Invoke-DockerChecked -Arguments ($compose + @('up', '-d', '--no-deps', '--no-build', '--force-recreate', 'backend'))

        $ready = $false
        for ($attempt = 0; $attempt -lt 30; $attempt++) {
            try {
                $response = Invoke-WebRequest -UseBasicParsing -TimeoutSec 3 -Uri 'http://127.0.0.1:8081/api/ready'
                if ($response.StatusCode -eq 200) { $ready = $true; break }
            } catch { }
            Start-Sleep -Seconds 2
        }
        if (-not $ready) { throw "Backend readiness did not recover after secret rotation." }
        $readinessRecovered = $true

        try {
            Invoke-RestMethod -Method Get -Uri 'http://127.0.0.1:8081/api/admin/exams' -Headers $headers | Out-Null
            throw "A token issued before session closure was still accepted."
        } catch {
            if (-not $_.Exception.Response -or [int]$_.Exception.Response.StatusCode -ne 401) { throw }
        }
        $oldTokensRejected = $true
    } catch {
        $operationError = $_
        if ($secretRotationAttempted) {
            try {
                Set-DotEnvValueAtomic -Path $layout.FormalEnv -Name 'TOKEN_SECRET' -Value $oldSecret
                Invoke-DockerChecked -Arguments ($compose + @('up', '-d', '--no-deps', '--no-build', '--force-recreate', 'backend'))
                $secretRestored = $true
            } catch {
                $recoveryError = $_
            }
        }
    } finally {
        # Release only after rotation, backend recovery, and old-token
        # rejection (or their guarded failure restoration) have finished.
        if ($lockAcquired) {
            try {
                Invoke-BackupWriteFreezeRelease -ComposeArguments $compose -Owner $lockOwner | Out-Null
                $lockReleased = $true
                $lockReleasedAt = [DateTimeOffset]::UtcNow.ToString('o')
            } catch {
                $lockReleaseError = $_
                if ($null -eq $operationError) { $operationError = $_ }
            }
        }
    }

    # Login and DB audit both write audit rows; they intentionally happen only
    # after the freeze has been released.  The old-token check above remains
    # inside the freeze boundary.
    if ($null -eq $operationError -and $lockReleased -and $oldTokensRejected) {
        try {
            $newLogin = Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8081/api/admin/login' -ContentType 'application/json' -Body $loginBody
            if (-not $newLogin.data.token) { throw "Active operator could not authenticate after session closure." }
            $newTokenIssued = $true
            Invoke-DockerChecked -Arguments ($compose + @(
                'exec', '-T', 'backend', 'uv', 'run', '--no-sync', 'python', '-m',
                'app.ops.operator_control', 'record-session-closure', '--operator-subject', $operatorSubject
            ))
            $auditRecorded = $true
            $status = 'passed'
        } catch {
            $operationError = $_
        }
    }
    if ($null -eq $operationError -and -not $auditRecorded) {
        $operationError = [System.InvalidOperationException]::new('Session-closure audit was not recorded after lock release.')
    }
    if ($null -ne $operationError) { $status = 'failed' }

    $evidencePath = Write-ChecksummedEvidence -Directory $layout.Evidence -Name 'session-closure' -Data ([ordered]@{
        schemaVersion = 1; kind = 'session-closure'; status = $status
        closedAt = [DateTimeOffset]::UtcNow.ToString('o')
        inProgressAttempts = $inProgressAttempts; oldTokensRejected = $oldTokensRejected
        readinessRecovered = $readinessRecovered; newTokenIssued = $newTokenIssued
        auditRecorded = $auditRecorded; secretRotationAttempted = $secretRotationAttempted
        commitPoint = if ($oldTokensRejected) { 'old-token-401' } else { 'not-reached' }
        partial = ($oldTokensRejected -and $status -ne 'passed')
        secretRestored = $secretRestored; recoveryError = if ($recoveryError) { $recoveryError.Exception.GetType().Name } else { $null }
        lock = [ordered]@{
            owner = $lockOwner; scope = 'session-closure-token-rotation'
            acquired = $lockAcquired; acquiredAt = $lockAcquiredAt
            released = $lockReleased; releasedAt = $lockReleasedAt
            releaseError = if ($lockReleaseError) { $lockReleaseError.Exception.GetType().Name } else { $null }
        }
    })
    Write-Output "session_closure_evidence=$evidencePath status=$status lock_acquired=$lockAcquired lock_released=$lockReleased"
    if ($status -eq 'passed') { Write-Output 'all_sessions_closed old_tokens_rejected=true readiness=ready' }
    if ($null -ne $operationError) {
        if ($operationError -is [System.Management.Automation.ErrorRecord]) { throw $operationError.Exception }
        throw $operationError
    }
} finally {
    if ($null -ne $randomBytes) { [Array]::Clear($randomBytes, 0, $randomBytes.Length) }
    $randomBytes = $null
    $newSecret = $null
    $oldSecret = $null
    $oldToken = $null
    $headers = $null
    $loginBody = $null
    $operatorPassword = $null
    if ($hadTag) { $env:APP_VERSION_TAG = $savedTag } else { Remove-Item Env:APP_VERSION_TAG -ErrorAction SilentlyContinue }
}
