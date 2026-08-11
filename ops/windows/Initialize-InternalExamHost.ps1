param(
    [string]$Root = "C:\ProgramData\InternalExam"
)

. "$PSScriptRoot\Common.ps1"
Assert-WindowsHost
$layout = Initialize-InternalExamLayout -Root $Root
$operator = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name

& icacls $layout.Root /inheritance:r /grant:r "${operator}:(OI)(CI)F" "BUILTIN\Administrators:(OI)(CI)F" "NT AUTHORITY\SYSTEM:(OI)(CI)F" | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Unable to protect C:\ProgramData\InternalExam ACLs." }
& icacls $layout.Configuration /inheritance:r /grant:r "${operator}:(OI)(CI)F" "BUILTIN\Administrators:(OI)(CI)F" "NT AUTHORITY\SYSTEM:(OI)(CI)F" | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Unable to protect formal configuration ACLs." }
Assert-ProtectedConfigurationAcl -ConfigurationPath $layout.Configuration

Write-Output "initialized root=$($layout.Root) operator=$operator"
