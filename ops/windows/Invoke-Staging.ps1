param(
    [Parameter(Mandatory = $true)][ValidateSet('Up', 'Down', 'Status')][string]$Action,
    [Parameter(Mandatory = $true)][string]$ReleasePath,
    [string]$Root = "C:\ProgramData\InternalExam"
)

. "$PSScriptRoot\Common.ps1"
Assert-DockerReady
$layout = Get-InternalExamLayout -Root $Root
Assert-ProtectedConfigurationAcl -ConfigurationPath $layout.Configuration
& "$PSScriptRoot\Test-ReleaseBundle.ps1" -ReleasePath $ReleasePath
if (-not $?) { throw "Release verification failed." }
$manifest = Get-Content -Raw -LiteralPath (Join-Path $ReleasePath 'release-manifest.json') -Encoding UTF8 | ConvertFrom-Json
$shortCommit = $manifest.gitCommit.Substring(0, 12)
$projectName = "internal-exam-staging-$shortCommit"

$saved = @{
    APP_VERSION_TAG = $env:APP_VERSION_TAG
    INTERNAL_LAN_BIND_IP = $env:INTERNAL_LAN_BIND_IP
    CANDIDATE_GATEWAY_PORT = $env:CANDIDATE_GATEWAY_PORT
    CANDIDATE_PUBLIC_BASE_URL = $env:CANDIDATE_PUBLIC_BASE_URL
    OPERATOR_GATEWAY_PORT = $env:OPERATOR_GATEWAY_PORT
    POSTGRES_LOOPBACK_PORT = $env:POSTGRES_LOOPBACK_PORT
    FRONTEND_LOOPBACK_PORT = $env:FRONTEND_LOOPBACK_PORT
}
try {
    $env:APP_VERSION_TAG = $manifest.gitCommit
    $env:INTERNAL_LAN_BIND_IP = '127.0.0.1'
    $env:CANDIDATE_GATEWAY_PORT = '18080'
    $env:CANDIDATE_PUBLIC_BASE_URL = 'http://127.0.0.1:18080'
    $env:OPERATOR_GATEWAY_PORT = '18081'
    $env:POSTGRES_LOOPBACK_PORT = '15432'
    $env:FRONTEND_LOOPBACK_PORT = '15173'
    $arguments = Get-ComposeBaseArguments -ReleasePath $ReleasePath -EnvPath $layout.StagingEnv -ProjectName $projectName
    if ($Action -eq 'Up') {
        Invoke-DockerChecked -Arguments ($arguments + @('up', '-d', '--no-build', '--remove-orphans'))
    } elseif ($Action -eq 'Down') {
        Invoke-DockerChecked -Arguments ($arguments + @('down', '-v', '--remove-orphans'))
    } else {
        Invoke-DockerChecked -Arguments ($arguments + @('ps'))
    }
} finally {
    foreach ($name in $saved.Keys) { Set-Item -Path "Env:$name" -Value $saved[$name] }
}
Write-Output "staging_action=$Action project=$projectName candidate=http://127.0.0.1:18080 operator=http://127.0.0.1:18081"
