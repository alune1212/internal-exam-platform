param(
    [Parameter(Mandatory = $true)][System.Security.SecureString]$AdminToken,
    [string]$Root = "C:\ProgramData\InternalExam"
)

. "$PSScriptRoot\Common.ps1"
Assert-WindowsHost
Assert-DockerReady
$layout = Initialize-InternalExamLayout -Root $Root
$state = Get-ReleaseState -Path $layout.CurrentRelease
$compose = Get-ComposeBaseArguments -ReleasePath $state.path -EnvPath $layout.FormalEnv -ProjectName 'internal-exam-formal'
$timestamp = [DateTimeOffset]::UtcNow.ToString('yyyyMMddTHHmmssZ')
$working = Join-Path $layout.Diagnostics ".diagnostic-$timestamp"
$archive = Join-Path $layout.Diagnostics "diagnostic-$timestamp.zip"
New-Item -ItemType Directory -Force -Path $working | Out-Null
$tokenPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($AdminToken)

try {
    $plainToken = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($tokenPointer)
    $headers = @{ 'X-Admin-Token' = $plainToken }
    $snapshot = Invoke-RestMethod -Method Get -Uri 'http://127.0.0.1:8081/api/admin/operations/snapshot' -Headers $headers
    $plainToken = $null
    $headers = $null
    $snapshot | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath (Join-Path $working 'operations.json') -Encoding UTF8

    $serviceStatus = Invoke-DockerCaptured -Arguments ($compose + @('ps', '--format', 'json'))
    $serviceStatus | Set-Content -LiteralPath (Join-Path $working 'services.jsonl') -Encoding UTF8
    Copy-Item -LiteralPath (Join-Path $state.path 'release-manifest.json') -Destination (Join-Path $working 'release-manifest.json')

    $logs = Invoke-DockerCaptured -Arguments ($compose + @('logs', '--no-color', '--tail', '500'))
    $redacted = $logs -replace '(?i)(authorization|token|password|otp|secret)(\s*[:=]\s*)\S+', '$1$2[REDACTED]'
    $redacted | Set-Content -LiteralPath (Join-Path $working 'bounded-logs.txt') -Encoding UTF8

    $manifest = [ordered]@{
        schemaVersion = 1; kind = 'diagnostic-export'; createdAt = [DateTimeOffset]::UtcNow.ToString('o')
        releaseVersion = $state.applicationVersion; gitCommit = $state.gitCommit
        logTailLinesPerService = 500; secrets = 'redacted'; files = @()
    }
    foreach ($file in Get-ChildItem -LiteralPath $working -File | Sort-Object Name) {
        $manifest.files += [ordered]@{ name = $file.Name; sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $file.FullName).Hash.ToLowerInvariant() }
    }
    $manifest | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $working 'manifest.json') -Encoding UTF8
    Compress-Archive -Path (Join-Path $working '*') -DestinationPath $archive -CompressionLevel Optimal
    $digest = (Get-FileHash -Algorithm SHA256 -LiteralPath $archive).Hash.ToLowerInvariant()
    "$digest  $([System.IO.Path]::GetFileName($archive))" | Set-Content -LiteralPath "$archive.sha256" -Encoding ASCII
} finally {
    if ($tokenPointer -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($tokenPointer) }
    $plainToken = $null
    $headers = $null
    if (Test-Path -LiteralPath $working) { Remove-Item -LiteralPath $working -Recurse -Force }
}

Write-Output "diagnostic_export=$archive checksum=$archive.sha256"
