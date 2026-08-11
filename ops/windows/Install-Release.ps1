param(
    [Parameter(Mandatory = $true)][string]$BundlePath,
    [string]$Root = "C:\ProgramData\InternalExam"
)

. "$PSScriptRoot\Common.ps1"
Assert-WindowsHost
$layout = Initialize-InternalExamLayout -Root $Root
Assert-ProtectedConfigurationAcl -ConfigurationPath $layout.Configuration
& "$PSScriptRoot\Test-ReleaseBundle.ps1" -ReleasePath $BundlePath
if (-not $?) { throw "Release verification failed." }

$manifest = Get-Content -Raw -LiteralPath (Join-Path $BundlePath 'release-manifest.json') -Encoding UTF8 | ConvertFrom-Json
$target = Join-Path $layout.Releases $manifest.applicationVersion
if (Test-Path -LiteralPath $target) { throw "Release version is already installed: $($manifest.applicationVersion)" }
Copy-Item -Recurse -LiteralPath $BundlePath -Destination $target
& (Join-Path $target 'ops\windows\Test-ReleaseBundle.ps1') -ReleasePath $target
if (-not $?) { throw "Installed release verification failed." }

Write-Output "installed version=$($manifest.applicationVersion) path=$target"
