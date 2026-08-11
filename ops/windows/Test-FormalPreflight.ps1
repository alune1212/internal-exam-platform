param(
    [Parameter(Mandatory = $true)][string]$BackupPath,
    [Parameter(Mandatory = $true)][string]$BrowserSmokeEvidence,
    [string]$Root = "C:\ProgramData\InternalExam"
)

. "$PSScriptRoot\Common.ps1"
Assert-WindowsHost
$layout = Get-InternalExamLayout -Root $Root
$checks = [System.Collections.Generic.List[object]]::new()
$currentCheck = 'initialization'
$state = $null
$releaseIdentity = $null
$savedTag = $env:APP_VERSION_TAG
$hadTag = Test-Path Env:APP_VERSION_TAG
$status = 'failed'

try {
    $currentCheck = 'docker'
    Assert-DockerReady
    $checks.Add([ordered]@{ name = $currentCheck; status = 'passed' })

    $currentCheck = 'configuration_acl'
    Assert-ProtectedConfigurationAcl -ConfigurationPath $layout.Configuration
    $configuration = Read-DotEnv -Path $layout.FormalEnv
    $required = @(
        'ENVIRONMENT', 'INTERNAL_LAN_BIND_IP', 'CORS_ORIGINS', 'DATABASE_URL',
        'PRIMARY_OPERATOR_USERNAME', 'PRIMARY_OPERATOR_PASSWORD',
        'BACKUP_OPERATOR_USERNAME', 'BACKUP_OPERATOR_PASSWORD', 'TOKEN_SECRET',
        'ADMIN_TOKEN_TTL_SECONDS', 'CANDIDATE_TOKEN_TTL_SECONDS',
        'CANDIDATE_LOGIN_EMAIL_DELIVERY_MODE', 'CANDIDATE_LOGIN_EMAIL_FROM',
        'CANDIDATE_LOGIN_SMTP_HOST', 'PREFLIGHT_SMTP_RECIPIENT'
    )
    foreach ($name in $required) {
        if (-not $configuration.ContainsKey($name) -or [string]::IsNullOrWhiteSpace($configuration[$name])) {
            throw "Required formal configuration field is missing: $name"
        }
    }
    if ($configuration.ENVIRONMENT -ne 'internal' -or
        $configuration.ADMIN_TOKEN_TTL_SECONDS -ne '14400' -or
        $configuration.CANDIDATE_TOKEN_TTL_SECONDS -ne '14400' -or
        $configuration.CANDIDATE_LOGIN_EMAIL_DELIVERY_MODE -ne 'smtp') {
        throw "Formal internal profile values are invalid."
    }
    if (-not (Test-PrivateIpv4 -Address $configuration.INTERNAL_LAN_BIND_IP)) {
        throw "INTERNAL_LAN_BIND_IP must be one fixed private IPv4 address."
    }
    $checks.Add([ordered]@{ name = $currentCheck; status = 'passed'; bind = 'private-fixed-ip'; secrets = 'redacted' })

    $currentCheck = 'release_checksums'
    $state = Get-ReleaseState -Path $layout.CurrentRelease
    & (Join-Path $state.path 'ops\windows\Test-ReleaseBundle.ps1') -ReleasePath $state.path | Out-Null
    if (-not $?) { throw "Active release checksum validation failed." }
    $manifest = Get-Content -Raw -LiteralPath (Join-Path $state.path 'release-manifest.json') -Encoding UTF8 | ConvertFrom-Json
    if ($manifest.gitCommit -ne $state.gitCommit) { throw "Active release state does not match the manifest." }
    $env:APP_VERSION_TAG = $state.gitCommit
    $releaseIdentity = Assert-ReleaseImageIdentity -ReleasePath $state.path -Manifest $manifest -CheckLocalImages
    $checks.Add([ordered]@{ name = $currentCheck; status = 'passed'; version = $state.applicationVersion; commit = $state.gitCommit })

    $compose = Get-ComposeBaseArguments -ReleasePath $state.path -EnvPath $layout.FormalEnv -ProjectName 'internal-exam-formal'

    $currentCheck = 'services_and_split_exposure'
    $running = Invoke-DockerCaptured -Arguments ($compose + @('ps', '--status', 'running', '--services'))
    foreach ($service in @('db', 'backend', 'auto-submit-worker', 'frontend', 'nginx', 'operator-nginx')) {
        if (($running -split "`n") -notcontains $service) { throw "Required service is not running: $service" }
    }
    $rendered = Invoke-DockerCaptured -Arguments ($compose + @('config'))
    if ($rendered -notmatch [regex]::Escape("$($configuration.INTERNAL_LAN_BIND_IP):8080") -or
        $rendered -notmatch [regex]::Escape('127.0.0.1:8081')) {
        throw "Rendered gateway bindings do not match the formal split exposure."
    }
    $checks.Add([ordered]@{ name = $currentCheck; status = 'passed'; candidatePort = 8080; operatorPort = 8081 })

    $currentCheck = 'health_and_migration'
    $candidateHealth = Invoke-WebRequest -UseBasicParsing -TimeoutSec 10 -Uri "http://$($configuration.INTERNAL_LAN_BIND_IP):8080/api/health"
    $operatorReady = Invoke-WebRequest -UseBasicParsing -TimeoutSec 10 -Uri 'http://127.0.0.1:8081/api/ready'
    if ($candidateHealth.StatusCode -ne 200 -or $operatorReady.StatusCode -ne 200) { throw "Service health endpoints failed." }
    $migration = Invoke-DockerCaptured -Arguments ($compose + @('exec', '-T', 'backend', 'uv', 'run', '--no-sync', 'alembic', 'current'))
    if ($migration -notmatch [regex]::Escape($manifest.migrationHead)) { throw "Database is not at the release migration head." }
    $checks.Add([ordered]@{ name = $currentCheck; status = 'passed'; migration = $manifest.migrationHead })

    $currentCheck = 'route_isolation'
    try {
        Invoke-WebRequest -UseBasicParsing -TimeoutSec 10 -Uri "http://$($configuration.INTERNAL_LAN_BIND_IP):8080/admin" -ErrorAction Stop | Out-Null
        throw "Candidate gateway unexpectedly exposed /admin."
    } catch {
        if (-not $_.Exception.Response -or [int]$_.Exception.Response.StatusCode -ne 404) { throw }
    }
    $localAdmin = Invoke-WebRequest -UseBasicParsing -TimeoutSec 10 -Uri 'http://127.0.0.1:8081/admin'
    if ($localAdmin.StatusCode -ne 200) { throw "Loopback operator route is unavailable." }
    $checks.Add([ordered]@{ name = $currentCheck; status = 'passed' })

    $currentCheck = 'clock'
    & w32tm /query /status | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Windows time synchronization status is unhealthy." }
    $checks.Add([ordered]@{ name = $currentCheck; status = 'passed' })

    $currentCheck = 'disk_reserve'
    $dbKiB = [int64]((Invoke-DockerCaptured -Arguments ($compose + @('exec', '-T', 'db', 'sh', '-c', 'du -sk /var/lib/postgresql/data | cut -f1'))).Trim())
    $mediaKiB = [int64]((Invoke-DockerCaptured -Arguments ($compose + @('exec', '-T', 'nginx', 'sh', '-c', 'du -sk /var/lib/nginx/learning-media | cut -f1'))).Trim())
    $footprintBytes = ($dbKiB + $mediaKiB) * 1024
    $releaseBytes = [int64](Get-ChildItem -LiteralPath $state.path -File -Recurse | Measure-Object -Property Length -Sum).Sum
    $footprintAfter = $footprintBytes + $releaseBytes
    $requiredFree = [Math]::Max(20GB, 3 * $footprintAfter)
    $drive = Get-PSDrive -Name ([System.IO.Path]::GetPathRoot($layout.Root).TrimEnd(':', '\'))
    $freeAfter = $drive.Free - $releaseBytes
    if ($freeAfter -lt $requiredFree) { throw "Disk reserve is below max(20 GiB, three times post-upgrade data footprint)." }
    $checks.Add([ordered]@{ name = $currentCheck; status = 'passed'; requiredBytes = $requiredFree; freeBytes = $drive.Free; proposedReleaseBytes = $releaseBytes })

    $currentCheck = 'backup'
    $backupFullPath = [System.IO.Path]::GetFullPath($BackupPath)
    Invoke-PortableMigrationValidation -ComposeArguments $compose -BackupPath $backupFullPath | Out-Null
    $checks.Add([ordered]@{ name = $currentCheck; status = 'passed'; backupId = [System.IO.Path]::GetFileName($backupFullPath) })

    $currentCheck = 'smtp'
    Invoke-DockerCaptured -Arguments ($compose + @('exec', '-T', 'backend', 'uv', 'run', '--no-sync', 'python', '-m', 'app.ops.preflight', 'smtp')) | Out-Null
    $checks.Add([ordered]@{ name = $currentCheck; status = 'passed'; delivery = 'real-smtp' })

    $currentCheck = 'browser_smoke'
    $browserEvidence = Assert-PassedEvidence -Path $BrowserSmokeEvidence
    Assert-WindowsEvidenceIdentity -Evidence $browserEvidence -ReleaseIdentity $releaseIdentity -Label 'Windows browser smoke evidence'
    $checks.Add([ordered]@{ name = $currentCheck; status = 'passed'; artifact = [System.IO.Path]::GetFileName($BrowserSmokeEvidence); browser = $browserEvidence.browser })

    $status = 'passed'
} catch {
    $checks.Add([ordered]@{ name = $currentCheck; status = 'failed'; errorType = $_.Exception.GetType().Name })
    throw
} finally {
    $evidence = [ordered]@{
        schemaVersion = 1
        kind = 'formal-preflight'
        status = $status
        checkedAt = [DateTimeOffset]::UtcNow.ToString('o')
        release = if ($state) { [ordered]@{ version = $state.applicationVersion; commit = $state.gitCommit } } else { $null }
        checks = $checks
    }
    if ($null -ne $releaseIdentity) {
        $identityImages = $releaseIdentity.Identity.images
        $imageReferences = [ordered]@{}
        $imageIds = [ordered]@{}
        foreach ($name in @('db', 'backend', 'frontend', 'gateway')) {
            $entry = Get-ReleaseImageEntry -Images $identityImages -Name $name
            $imageReferences[$name] = Get-ObjectPropertyValue -Object $entry -Names @('reference', 'ref')
            $imageIds[$name] = Get-ObjectPropertyValue -Object $entry -Names @('id', 'image_id', 'imageId')
        }
        $evidence.hostOS = 'windows'
        $evidence.host_os = 'windows'
        $evidence.architecture = 'amd64'
        $evidence.targetPlatform = 'linux/amd64'
        $evidence.target_platform = 'linux/amd64'
        $evidence.builtImageIdentitySha256 = $releaseIdentity.IdentityDigest
        $evidence.imageReferences = $imageReferences
        $evidence.image_references = $imageReferences
        $evidence.imageIds = $imageIds
        $evidence.image_ids = $imageIds
    }
    $evidencePath = Write-ChecksummedEvidence -Directory $layout.Evidence -Name 'formal-preflight' -Data $evidence
    if ($hadTag) { $env:APP_VERSION_TAG = $savedTag } else { Remove-Item Env:APP_VERSION_TAG -ErrorAction SilentlyContinue }
    Write-Output "preflight_evidence=$evidencePath status=$status"
}
