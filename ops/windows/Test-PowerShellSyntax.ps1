param(
    [string]$Path = $PSScriptRoot
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$failed = $false
foreach ($script in Get-ChildItem -LiteralPath $Path -File -Filter '*.ps1') {
    $tokens = $null
    $errors = $null
    [System.Management.Automation.Language.Parser]::ParseFile(
        $script.FullName,
        [ref]$tokens,
        [ref]$errors
    ) | Out-Null
    if ($errors.Count -gt 0) {
        $failed = $true
        foreach ($parseError in $errors) {
            Write-Error "$($script.Name):$($parseError.Extent.StartLineNumber): $($parseError.Message)" -ErrorAction Continue
        }
    }
}
if ($failed) { throw 'PowerShell syntax validation failed.' }
Write-Output 'powershell_syntax_valid=true'
