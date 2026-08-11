param(
    [string]$Root = "C:\ProgramData\InternalExam"
)

. "$PSScriptRoot\Common.ps1"
Assert-DockerReady
$layout = Get-InternalExamLayout -Root $Root
$state = Get-ReleaseState -Path $layout.CurrentRelease
$arguments = Get-ComposeBaseArguments -ReleasePath $state.path -EnvPath $layout.FormalEnv -ProjectName 'internal-exam-formal'
Invoke-DockerChecked -Arguments ($arguments + @('ps'))
Write-Output "active_version=$($state.applicationVersion) commit=$($state.gitCommit)"
