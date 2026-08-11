param(
    [string]$Root = "C:\ProgramData\InternalExam"
)

. "$PSScriptRoot\Common.ps1"
Assert-WindowsHost
Assert-DockerReady
$layout = Get-InternalExamLayout -Root $Root
Assert-ProtectedConfigurationAcl -ConfigurationPath $layout.Configuration
$state = Get-ReleaseState -Path $layout.CurrentRelease
& (Join-Path $state.path 'ops\windows\Test-ReleaseBundle.ps1') -ReleasePath $state.path
if (-not $?) { throw "Active release verification failed." }
$manifest = Get-Content -Raw -LiteralPath (Join-Path $state.path 'release-manifest.json') -Encoding UTF8 | ConvertFrom-Json
$releaseIdentity = Assert-ReleaseImageIdentity -ReleasePath $state.path -Manifest $manifest -CheckLocalImages

$previousTag = $env:APP_VERSION_TAG
$formalStartAttempted = $false
try {
    $env:APP_VERSION_TAG = $state.gitCommit
    $arguments = Get-ComposeBaseArguments -ReleasePath $state.path -EnvPath $layout.FormalEnv -ProjectName 'internal-exam-formal'
    $formalStartAttempted = $true
    Invoke-DockerChecked -Arguments ($arguments + @('up', '-d', 'db'))
    Assert-WriterFenceClearBeforeExpose -ComposeArguments $arguments
    Invoke-DockerChecked -Arguments ($arguments + @('up', '-d', '--no-build', '--remove-orphans'))
} catch {
    if ($formalStartAttempted) {
        try {
            # Preserve volumes and release evidence, but leave the entire
            # formal project stopped when the writer-fence gate fails.
            Invoke-DockerChecked -Arguments ($arguments + @('down', '--remove-orphans'))
        } catch {
            Write-Warning "Formal project cleanup after failed start was unsuccessful. Stop it manually before retrying."
        }
    }
    throw
} finally {
    $env:APP_VERSION_TAG = $previousTag
}
Write-Output "formal_started version=$($state.applicationVersion)"
