Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-InternalExamLayout {
    param([string]$Root = "C:\ProgramData\InternalExam")

    $resolvedRoot = [System.IO.Path]::GetFullPath($Root)
    return [ordered]@{
        Root = $resolvedRoot
        Configuration = Join-Path $resolvedRoot "configuration"
        Releases = Join-Path $resolvedRoot "releases"
        Backups = Join-Path $resolvedRoot "backups"
        Evidence = Join-Path $resolvedRoot "evidence"
        Diagnostics = Join-Path $resolvedRoot "diagnostics"
        State = Join-Path $resolvedRoot "state"
        FormalEnv = Join-Path $resolvedRoot "configuration\formal.env"
        StagingEnv = Join-Path $resolvedRoot "configuration\staging.env"
        CurrentRelease = Join-Path $resolvedRoot "state\current-release.json"
        PreviousRelease = Join-Path $resolvedRoot "state\previous-release.json"
    }
}

function Initialize-InternalExamLayout {
    param([string]$Root = "C:\ProgramData\InternalExam")

    $layout = Get-InternalExamLayout -Root $Root
    foreach ($key in @("Root", "Configuration", "Releases", "Backups", "Evidence", "Diagnostics", "State")) {
        New-Item -ItemType Directory -Force -Path $layout[$key] | Out-Null
    }
    return $layout
}

function Assert-WindowsHost {
    if ([System.Environment]::OSVersion.Platform -ne [System.PlatformID]::Win32NT) {
        throw "This operation is supported only on the dedicated Windows host."
    }
}

function Assert-DockerReady {
    & docker info --format '{{.ServerVersion}}' | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Desktop is not ready. Start Docker Desktop and wait for WSL2 initialization."
    }
    & docker compose version | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Compose is unavailable."
    }
}

function Read-DotEnv {
    param([Parameter(Mandatory = $true)][string]$Path)

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Required environment file is missing: $Path"
    }
    $values = @{}
    foreach ($line in Get-Content -LiteralPath $Path -Encoding UTF8) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith("#")) { continue }
        $separator = $trimmed.IndexOf("=")
        if ($separator -lt 1) { throw "Invalid environment entry in $Path" }
        $name = $trimmed.Substring(0, $separator).Trim()
        $values[$name] = $trimmed.Substring($separator + 1)
    }
    return $values
}

function Write-DotEnvAtomic {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][hashtable]$Values
    )

    $temporary = "$Path.new"
    $lines = foreach ($name in ($Values.Keys | Sort-Object)) {
        "$name=$($Values[$name])"
    }
    [System.IO.File]::WriteAllLines($temporary, $lines, [System.Text.UTF8Encoding]::new($false))
    Move-Item -Force -LiteralPath $temporary -Destination $Path
}

function Set-DotEnvValueAtomic {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][ValidatePattern('^[A-Z][A-Z0-9_]*$')][string]$Name,
        [Parameter(Mandatory = $true)][ValidateScript({ $_ -notmatch '[\r\n]' })][string]$Value
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "Environment file is missing: $Path" }
    $content = Get-Content -Raw -LiteralPath $Path -Encoding UTF8
    $pattern = "(?m)^$([regex]::Escape($Name))=.*$"
    if ($content -notmatch $pattern) { throw "Environment field is missing: $Name" }
    $updated = [regex]::Replace($content, $pattern, "$Name=$Value", 1)
    $temporary = "$Path.new"
    [System.IO.File]::WriteAllText($temporary, $updated, [System.Text.UTF8Encoding]::new($false))
    Move-Item -Force -LiteralPath $temporary -Destination $Path
}

function Assert-ProtectedConfigurationAcl {
    param([Parameter(Mandatory = $true)][string]$ConfigurationPath)

    Assert-WindowsHost
    $acl = Get-Acl -LiteralPath $ConfigurationPath
    if (-not $acl.AreAccessRulesProtected) {
        throw "Configuration ACL inheritance is enabled; run Initialize-InternalExamHost.ps1."
    }
    $allowed = @("NT AUTHORITY\SYSTEM", "BUILTIN\Administrators", [System.Security.Principal.WindowsIdentity]::GetCurrent().Name)
    foreach ($rule in $acl.Access) {
        if ($rule.AccessControlType -eq "Allow" -and $allowed -notcontains $rule.IdentityReference.Value) {
            throw "Unexpected account can access protected configuration: $($rule.IdentityReference.Value)"
        }
    }
}

function Get-ReleaseState {
    param([Parameter(Mandatory = $true)][string]$Path)

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Release state is missing: $Path"
    }
    return Get-Content -Raw -LiteralPath $Path -Encoding UTF8 | ConvertFrom-Json
}

function Get-ComposeBaseArguments {
    param(
        [Parameter(Mandatory = $true)][string]$ReleasePath,
        [Parameter(Mandatory = $true)][string]$EnvPath,
        [Parameter(Mandatory = $true)][string]$ProjectName
    )

    return @(
        "compose", "--project-name", $ProjectName,
        "--env-file", $EnvPath,
        "-f", (Join-Path $ReleasePath "docker-compose.yml")
    )
}

function Invoke-DockerChecked {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)

    & docker @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Docker operation failed. Review the preceding non-secret Docker output."
    }
}

function Invoke-DockerCaptured {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)

    $output = & docker @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Docker validation failed. Review Docker service logs locally."
    }
    return ($output -join "`n")
}

function Assert-PassedEvidence {
    param([Parameter(Mandatory = $true)][string]$Path)

    $checksumPath = "$Path.sha256"
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf) -or
        -not (Test-Path -LiteralPath $checksumPath -PathType Leaf)) {
        throw "Required checksummed evidence is missing: $Path"
    }
    $checksumLine = (Get-Content -Raw -LiteralPath $checksumPath -Encoding ASCII).Trim()
    if ($checksumLine -notmatch '^([0-9a-f]{64})  (.+)$') { throw "Evidence checksum format is invalid." }
    $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
    if ($actual -ne $Matches[1]) { throw "Evidence checksum failed." }
    $evidence = Get-Content -Raw -LiteralPath $Path -Encoding UTF8 | ConvertFrom-Json
    if ($evidence.status -ne 'passed') { throw "Required evidence is not passed." }
    return $evidence
}

function Write-ChecksummedEvidence {
    param(
        [Parameter(Mandatory = $true)][string]$Directory,
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][object]$Data
    )

    New-Item -ItemType Directory -Force -Path $Directory | Out-Null
    $timestamp = [DateTimeOffset]::UtcNow.ToString("yyyyMMddTHHmmssZ")
    $jsonPath = Join-Path $Directory "$Name-$timestamp.json"
    $checksumPath = "$jsonPath.sha256"
    $Data | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $jsonPath -Encoding UTF8
    $digest = (Get-FileHash -Algorithm SHA256 -LiteralPath $jsonPath).Hash.ToLowerInvariant()
    "$digest  $([System.IO.Path]::GetFileName($jsonPath))" | Set-Content -LiteralPath $checksumPath -Encoding ASCII
    return $jsonPath
}

function Write-ChecksummedJsonFile {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][object]$Data
    )

    $parent = [System.IO.Path]::GetDirectoryName([System.IO.Path]::GetFullPath($Path))
    if ($parent) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }
    $json = ($Data | ConvertTo-Json -Depth 20) + "`n"
    [System.IO.File]::WriteAllText($Path, $json, [System.Text.UTF8Encoding]::new($false))
    $digest = (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
    [System.IO.File]::WriteAllText(
        "$Path.sha256",
        "$digest  $([System.IO.Path]::GetFileName($Path))`n",
        [System.Text.Encoding]::ASCII
    )
    return $digest
}

function Get-ObjectPropertyValue {
    param(
        [Parameter(Mandatory = $false)][object]$Object,
        [Parameter(Mandatory = $true)][string[]]$Names
    )

    if ($null -eq $Object) { return $null }
    foreach ($name in $Names) {
        $property = $Object.PSObject.Properties[$name]
        if ($null -ne $property) { return $property.Value }
        if ($Object -is [System.Collections.IDictionary] -and $Object.Contains($name)) {
            return $Object[$name]
        }
    }
    return $null
}

function Set-ObjectPropertyValue {
    param(
        [Parameter(Mandatory = $true)][object]$Object,
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $false)][object]$Value
    )

    $property = $Object.PSObject.Properties[$Name]
    if ($null -eq $property) {
        $Object | Add-Member -MemberType NoteProperty -Name $Name -Value $Value -Force | Out-Null
    } else {
        [void]($property.Value = $Value)
    }
}

function Get-ReleaseImageEntry {
    param(
        [Parameter(Mandatory = $true)][object]$Images,
        [Parameter(Mandatory = $true)][string]$Name
    )

    $entry = Get-ObjectPropertyValue -Object $Images -Names @($Name)
    if ($null -eq $entry) { throw "Release image identity is missing: $Name" }
    return $entry
}

function Assert-CanonicalWindowsIdentity {
    param(
        [Parameter(Mandatory = $true)][object]$Metadata,
        [Parameter(Mandatory = $true)][string]$Label
    )

    # The snake-case fields are the cross-host contract.  Camel-case aliases
    # may be retained for older display consumers but cannot satisfy this
    # Windows gate by themselves.
    $hostOS = Get-ObjectPropertyValue -Object $Metadata -Names @('host_os')
    $architecture = Get-ObjectPropertyValue -Object $Metadata -Names @('architecture')
    $targetPlatform = Get-ObjectPropertyValue -Object $Metadata -Names @('target_platform')
    if ($hostOS -cne 'windows' -or
        $architecture -cne 'amd64' -or
        $targetPlatform -cne 'linux/amd64') {
        throw "$Label must prove canonical host_os=windows, architecture=amd64, target_platform=linux/amd64."
    }
}

function Read-ReleaseImageIdentity {
    param(
        [Parameter(Mandatory = $true)][string]$ReleasePath,
        [Parameter(Mandatory = $false)][object]$Manifest,
        [switch]$AllowPending
    )

    $resolvedRelease = [System.IO.Path]::GetFullPath($ReleasePath)
    if ($null -eq $Manifest) {
        $manifestPath = Join-Path $resolvedRelease 'release-manifest.json'
        if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
            throw "Release manifest is missing."
        }
        $Manifest = Get-Content -Raw -LiteralPath $manifestPath -Encoding UTF8 | ConvertFrom-Json
    }
    $identityPath = Join-Path $resolvedRelease 'ops\release\built-image-identity.json'
    $identityChecksumPath = "$identityPath.sha256"
    if (-not (Test-Path -LiteralPath $identityPath -PathType Leaf) -or
        -not (Test-Path -LiteralPath $identityChecksumPath -PathType Leaf)) {
        throw "Checksummed final image identity is missing."
    }
    $checksumLine = (Get-Content -Raw -LiteralPath $identityChecksumPath -Encoding ASCII).Trim()
    if ($checksumLine -notmatch '^([0-9a-f]{64})  ([^\r\n]+)$' -or
        $Matches[2] -ne [System.IO.Path]::GetFileName($identityPath)) {
        throw "Final image identity checksum format is invalid."
    }
    $identityDigest = (Get-FileHash -Algorithm SHA256 -LiteralPath $identityPath).Hash.ToLowerInvariant()
    if ($identityDigest -ne $Matches[1]) { throw "Final image identity checksum failed." }
    $identity = Get-Content -Raw -LiteralPath $identityPath -Encoding UTF8 | ConvertFrom-Json
    $status = [string](Get-ObjectPropertyValue -Object $identity -Names @('status'))
    if ($status -ne 'passed' -and (-not $AllowPending -or $status -ne 'pending')) {
        throw "Final image identity is not passed."
    }
    Assert-CanonicalWindowsIdentity -Metadata $identity -Label 'Final image identity'

    $manifestCommit = [string](Get-ObjectPropertyValue -Object $Manifest -Names @('git_commit', 'gitCommit'))
    $identityCommit = [string](Get-ObjectPropertyValue -Object $identity -Names @('git_commit', 'gitCommit'))
    if ($manifestCommit -notmatch '^[0-9a-f]{40}$' -or $identityCommit -cne $manifestCommit) {
        throw "Final image identity commit does not match the release manifest."
    }
    $manifestIdentity = Get-ObjectPropertyValue -Object $Manifest -Names @('builtImageIdentity', 'built_image_identity')
    if ($null -eq $manifestIdentity -or
        (Get-ObjectPropertyValue -Object $manifestIdentity -Names @('path')) -cne 'ops/release/built-image-identity.json' -or
        (Get-ObjectPropertyValue -Object $manifestIdentity -Names @('sha256')) -cne $identityDigest) {
        throw "Release manifest is not bound to the final image identity."
    }

    $identityImages = Get-ObjectPropertyValue -Object $identity -Names @('images')
    $manifestImages = Get-ObjectPropertyValue -Object $Manifest -Names @(
        'finalImageReferences', 'final_image_references', 'imageReferences',
        'image_references', 'imageDigests'
    )
    $finalReferences = [ordered]@{}
    foreach ($name in @('db', 'backend', 'frontend', 'gateway')) {
        $entry = Get-ReleaseImageEntry -Images $identityImages -Name $name
        $reference = [string](Get-ObjectPropertyValue -Object $entry -Names @('reference', 'ref'))
        $imageID = [string](Get-ObjectPropertyValue -Object $entry -Names @('id', 'image_id', 'imageId'))
        $imageOS = [string](Get-ObjectPropertyValue -Object $entry -Names @('os', 'host_os', 'hostOS'))
        $imageArchitecture = [string](Get-ObjectPropertyValue -Object $entry -Names @('architecture', 'arch'))
        if ($status -eq 'pending') {
            if ($reference -or $imageID) { throw "Pending final image identity contains an image record." }
            continue
        }
        if ($reference -notmatch "^[a-z0-9][a-z0-9._/-]{0,254}:$manifestCommit$" -or
            $imageID -notmatch '^sha256:[0-9a-f]{64}$' -or
            $imageOS -cne 'linux' -or
            $imageArchitecture -cne 'amd64') {
            throw "Final image identity is not an exact linux/amd64 release image set."
        }
        $manifestReference = [string](Get-ObjectPropertyValue -Object $manifestImages -Names @($name))
        if ($manifestReference -cne $reference) {
            throw "Release manifest final image reference does not match $name identity."
        }
        $finalReferences[$name] = $reference
    }
    if ($status -eq 'passed' -and $finalReferences.Count -ne 4) {
        throw "Release final image identity must contain db, backend, frontend, and gateway."
    }
    return [pscustomobject]@{
        ReleasePath = $resolvedRelease
        Manifest = $Manifest
        Identity = $identity
        IdentityPath = $identityPath
        IdentityDigest = $identityDigest
        FinalImageReferences = $finalReferences
    }
}

function Assert-LocalReleaseImageIdentity {
    param([Parameter(Mandatory = $true)][object]$ReleaseIdentity)

    foreach ($name in @('db', 'backend', 'frontend', 'gateway')) {
        $entry = Get-ReleaseImageEntry -Images $ReleaseIdentity.Identity.images -Name $name
        $reference = [string](Get-ObjectPropertyValue -Object $entry -Names @('reference', 'ref'))
        $expectedID = [string](Get-ObjectPropertyValue -Object $entry -Names @('id', 'image_id', 'imageId'))
        $raw = Invoke-DockerCaptured -Arguments @('image', 'inspect', '--format', '{{json .}}', $reference)
        $record = $raw | ConvertFrom-Json
        if ($record -is [array]) { $record = $record[0] }
        $actualID = [string](Get-ObjectPropertyValue -Object $record -Names @('Id', 'ID', 'id'))
        $actualOS = [string](Get-ObjectPropertyValue -Object $record -Names @('Os', 'OS', 'os'))
        $actualArchitecture = [string](Get-ObjectPropertyValue -Object $record -Names @('Architecture', 'architecture', 'arch'))
        if ($actualID -cne $expectedID -or $actualOS -cne 'linux' -or $actualArchitecture -cne 'amd64' -or
            @($record.RepoTags) -notcontains $reference) {
            throw "Local Docker image does not match the exact release identity: $name."
        }
    }
}

function Assert-ReleaseImageIdentity {
    param(
        [Parameter(Mandatory = $true)][string]$ReleasePath,
        [Parameter(Mandatory = $false)][object]$Manifest,
        [switch]$AllowPending,
        [switch]$CheckLocalImages
    )

    $releaseIdentity = Read-ReleaseImageIdentity -ReleasePath $ReleasePath -Manifest $Manifest -AllowPending:$AllowPending
    if ($CheckLocalImages) {
        if ($releaseIdentity.Identity.status -ne 'passed') { throw "Local image checks require a passed final image identity." }
        Assert-LocalReleaseImageIdentity -ReleaseIdentity $releaseIdentity
    }
    return $releaseIdentity
}

function Assert-WindowsEvidenceIdentity {
    param(
        [Parameter(Mandatory = $true)][object]$Evidence,
        [Parameter(Mandatory = $true)][object]$ReleaseIdentity,
        [Parameter(Mandatory = $true)][string]$Label
    )

    if ([string](Get-ObjectPropertyValue -Object $Evidence -Names @('status')) -ne 'passed') {
        throw "$Label did not pass."
    }
    $identitySource = $Evidence
    $hostOS = Get-ObjectPropertyValue -Object $identitySource -Names @('host_os', 'hostOS', 'hostOs')
    if ($null -eq $hostOS) {
        $identitySource = Get-ObjectPropertyValue -Object $Evidence -Names @('release', 'releaseIdentity')
    }
    Assert-CanonicalWindowsIdentity -Metadata $identitySource -Label $Label
    $commit = [string](Get-ObjectPropertyValue -Object $identitySource -Names @('git_commit', 'gitCommit', 'commit'))
    if ([string]::IsNullOrWhiteSpace($commit)) {
        $commit = [string](Get-ObjectPropertyValue -Object $Evidence -Names @('git_commit', 'gitCommit', 'commit'))
    }
    if ([string]::IsNullOrWhiteSpace($commit)) {
        $releaseEvidence = Get-ObjectPropertyValue -Object $Evidence -Names @('release', 'releaseIdentity')
        $commit = [string](Get-ObjectPropertyValue -Object $releaseEvidence -Names @('git_commit', 'gitCommit', 'commit'))
    }
    $releaseCommit = [string](Get-ObjectPropertyValue -Object $ReleaseIdentity.Manifest -Names @('git_commit', 'gitCommit'))
    if ($commit -cne $releaseCommit) { throw "$Label belongs to another release commit." }
    $expectedDigest = $ReleaseIdentity.IdentityDigest
    $evidenceDigest = [string](Get-ObjectPropertyValue -Object $Evidence -Names @('builtImageIdentitySha256', 'built_image_identity_sha256', 'imageIdentitySha256'))
    if ($evidenceDigest -cne $expectedDigest) { throw "$Label is not bound to the exact final image identity." }
    $evidenceRefs = Get-ObjectPropertyValue -Object $Evidence -Names @('imageReferences', 'image_references', 'finalImageReferences', 'final_image_references')
    $evidenceIDs = Get-ObjectPropertyValue -Object $Evidence -Names @('imageIds', 'image_ids', 'finalImageIds', 'final_image_ids')
    foreach ($name in @('db', 'backend', 'frontend', 'gateway')) {
        $entry = Get-ReleaseImageEntry -Images $ReleaseIdentity.Identity.images -Name $name
        $expectedRef = [string](Get-ObjectPropertyValue -Object $entry -Names @('reference', 'ref'))
        $expectedID = [string](Get-ObjectPropertyValue -Object $entry -Names @('id', 'image_id', 'imageId'))
        if ([string](Get-ObjectPropertyValue -Object $evidenceRefs -Names @($name)) -cne $expectedRef -or
            [string](Get-ObjectPropertyValue -Object $evidenceIDs -Names @($name)) -cne $expectedID) {
            throw "$Label final image binding is stale: $name."
        }
    }
}

function Invoke-PortableMigrationValidation {
    param(
        [Parameter(Mandatory = $true)][string[]]$ComposeArguments,
        [Parameter(Mandatory = $true)][string]$BackupPath
    )

    $backupFullPath = [System.IO.Path]::GetFullPath($BackupPath)
    if (-not (Test-Path -LiteralPath $backupFullPath -PathType Container)) {
        throw "Paired backup directory is missing."
    }
    $backupMount = "${backupFullPath}:/portable-backup:ro"
    return Invoke-DockerCaptured -Arguments ($ComposeArguments + @(
        'run', '--rm', '--no-deps', '--volume', $backupMount, 'backend',
        'uv', 'run', '--no-sync', 'python', '-m', 'app.ops.host_portability',
        'validate-migration-input', '/portable-backup'
    ))
}

function Get-ConfiguredOperatorSubject {
    param([Parameter(Mandatory = $true)][hashtable]$Configuration)

    $enabled = [string]$Configuration.BACKUP_OPERATOR_ENABLED
    if ($enabled -match '^(?i:true|1|yes)$') {
        if (-not $Configuration.ContainsKey('BACKUP_OPERATOR_USERNAME') -or
            [string]::IsNullOrWhiteSpace([string]$Configuration.BACKUP_OPERATOR_USERNAME)) {
            throw 'BACKUP_OPERATOR_ENABLED requires a configured backup operator.'
        }
        return [string]$Configuration.BACKUP_OPERATOR_USERNAME
    }
    if (-not $Configuration.ContainsKey('PRIMARY_OPERATOR_USERNAME') -or
        [string]::IsNullOrWhiteSpace([string]$Configuration.PRIMARY_OPERATOR_USERNAME)) {
        throw 'Primary operator is not configured.'
    }
    return [string]$Configuration.PRIMARY_OPERATOR_USERNAME
}

function Assert-OperatorLoginState {
    param(
        [Parameter(Mandatory = $true)][string]$Username,
        [Parameter(Mandatory = $true)][string]$Password,
        [Parameter(Mandatory = $true)][bool]$ExpectedSuccess,
        [string]$Uri = 'http://127.0.0.1:8081/api/admin/login'
    )

    $body = @{ username = $Username; password = $Password } | ConvertTo-Json
    if ($ExpectedSuccess) {
        $login = Invoke-RestMethod -Method Post -Uri $Uri -ContentType 'application/json' -Body $body
        if (-not $login.data.token) { throw "Operator authentication did not return a token: $Username" }
        return
    }
    try {
        Invoke-RestMethod -Method Post -Uri $Uri -ContentType 'application/json' -Body $body | Out-Null
        throw "Operator unexpectedly authenticated: $Username"
    } catch {
        if (-not $_.Exception.Response -or [int]$_.Exception.Response.StatusCode -ne 401) { throw }
    }
}

function Invoke-OperationalLockCommand {
    param(
        [Parameter(Mandatory = $true)][string[]]$ComposeArguments,
        [Parameter(Mandatory = $true)][string[]]$CommandArguments,
        [string[]]$VolumeArguments
    )

    $arguments = $ComposeArguments + @('run', '--rm', '--no-deps')
    if ($VolumeArguments) { $arguments += $VolumeArguments }
    $arguments += @(
        'backend', 'uv', 'run', '--no-sync', 'python', '-m', 'app.ops.operational_lock'
    )
    return Invoke-DockerCaptured -Arguments ($arguments + $CommandArguments)
}

function Invoke-WriterFenceCommand {
    param(
        [Parameter(Mandatory = $true)][string[]]$ComposeArguments,
        [Parameter(Mandatory = $true)][string[]]$CommandArguments
    )

    return Invoke-OperationalLockCommand -ComposeArguments $ComposeArguments -CommandArguments $CommandArguments
}

function Invoke-BackupWriteFreezeAcquire {
    param(
        [Parameter(Mandatory = $true)][string[]]$ComposeArguments,
        [Parameter(Mandatory = $true)][string]$Owner
    )

    $raw = Invoke-OperationalLockCommand -ComposeArguments $ComposeArguments -CommandArguments @(
        'acquire-backup', '--owner', $Owner
    )
    $result = $raw | ConvertFrom-Json
    if ([string](Get-ObjectPropertyValue -Object $result -Names @('status')) -ne 'passed' -or
        [string](Get-ObjectPropertyValue -Object $result -Names @('action')) -ne 'acquired' -or
        [string](Get-ObjectPropertyValue -Object $result -Names @('owner')) -cne $Owner) {
        throw 'Session-closure write freeze acquisition was not confirmed.'
    }
    return $result
}

function Invoke-BackupWriteFreezeRelease {
    param(
        [Parameter(Mandatory = $true)][string[]]$ComposeArguments,
        [Parameter(Mandatory = $true)][string]$Owner
    )

    $raw = Invoke-OperationalLockCommand -ComposeArguments $ComposeArguments -CommandArguments @(
        'release-backup', '--owner', $Owner
    )
    $result = $raw | ConvertFrom-Json
    if ([string](Get-ObjectPropertyValue -Object $result -Names @('status')) -ne 'passed' -or
        [string](Get-ObjectPropertyValue -Object $result -Names @('action')) -ne 'released' -or
        [string](Get-ObjectPropertyValue -Object $result -Names @('owner')) -cne $Owner) {
        throw 'Session-closure write freeze release was not confirmed.'
    }
    return $result
}

function Assert-WriterFenceClearBeforeExpose {
    param(
        [Parameter(Mandatory = $true)][string[]]$ComposeArguments,
        [string]$ExpectedDatasetId,
        [string]$ExpectedHostId,
        [int]$ExpectedWriterGeneration
    )

    $raw = Invoke-WriterFenceCommand -ComposeArguments $ComposeArguments -CommandArguments @('inspect-fence')
    $inspection = $raw | ConvertFrom-Json
    if ([string](Get-ObjectPropertyValue -Object $inspection -Names @('status')) -ne 'passed' -or
        [bool](Get-ObjectPropertyValue -Object $inspection -Names @('active'))) {
        throw 'Candidate writes remain fenced or writer-fence inspection failed.'
    }
    # A released row is still authoritative lineage.  Never reopen a stale or
    # foreign host/generation merely because active=false; the caller must
    # provide the exact accepted identity (or use Invoke-WriterFenceTransfer).
    $recordedDatasetId = Get-ObjectPropertyValue -Object $inspection -Names @('dataset_id', 'datasetId')
    $recordedHostId = Get-ObjectPropertyValue -Object $inspection -Names @('host_id', 'hostId')
    $recordedGeneration = Get-ObjectPropertyValue -Object $inspection -Names @('writer_generation', 'writerGeneration')
    if ($null -ne $recordedDatasetId -or $null -ne $recordedHostId -or $null -ne $recordedGeneration) {
        if ([string]::IsNullOrWhiteSpace($ExpectedDatasetId) -or
            [string]::IsNullOrWhiteSpace($ExpectedHostId) -or
            $ExpectedWriterGeneration -lt 1 -or
            [string]$recordedDatasetId -cne $ExpectedDatasetId -or
            [string]$recordedHostId -cne $ExpectedHostId -or
            [int]$recordedGeneration -ne $ExpectedWriterGeneration) {
            throw 'Released writer-fence identity is stale or foreign; transfer/accept is required before exposing candidate writes.'
        }
    }
}

function Invoke-WriterFenceTransfer {
    param(
        [Parameter(Mandatory = $true)][string[]]$ComposeArguments,
        [Parameter(Mandatory = $true)][string]$DatasetId,
        [Parameter(Mandatory = $true)][string]$SourceHostId,
        [Parameter(Mandatory = $true)][int]$SourceWriterGeneration,
        [Parameter(Mandatory = $true)][string]$TargetHostId,
        [Parameter(Mandatory = $true)][int]$TargetWriterGeneration,
        [Parameter(Mandatory = $true)][string]$Reason,
        [Parameter(Mandatory = $true)][object]$TargetPreflightEvidence,
        [Parameter(Mandatory = $true)][string]$RestoredCutoverBackupPath
    )

    if ([string](Get-ObjectPropertyValue -Object $TargetPreflightEvidence -Names @('status')) -ne 'passed') {
        throw 'Writer-fence transfer requires passed target preflight evidence.'
    }
    Assert-CanonicalWindowsIdentity -Metadata $TargetPreflightEvidence -Label 'Target preflight evidence'
    $targetEvidenceGeneration = Get-ObjectPropertyValue -Object $TargetPreflightEvidence -Names @('target_writer_generation', 'targetWriterGeneration', 'writer_generation', 'writerGeneration')
    if ([int]$targetEvidenceGeneration -ne $TargetWriterGeneration) {
        throw 'Target preflight writer_generation does not match the transfer generation.'
    }
    $backupFullPath = [System.IO.Path]::GetFullPath($RestoredCutoverBackupPath)
    if (-not (Test-Path -LiteralPath $backupFullPath -PathType Container)) {
        throw 'Writer-fence transfer requires the verified restored cutover backup directory.'
    }
    $backupMount = "${backupFullPath}:/restored-cutover-backup:ro"
    $commandArguments = @(
        'transfer-fence', '--dataset-id', $DatasetId,
        '--source-host-id', $SourceHostId,
        '--source-writer-generation', [string]$SourceWriterGeneration,
        '--target-host-id', $TargetHostId,
        '--target-writer-generation', [string]$TargetWriterGeneration,
        '--reason', $Reason,
        '--restored-cutover-backup', '/restored-cutover-backup'
    )
    return Invoke-OperationalLockCommand -ComposeArguments $ComposeArguments -CommandArguments $commandArguments -VolumeArguments @('--volume', $backupMount)
}

function Test-PrivateIpv4 {
    param([Parameter(Mandatory = $true)][string]$Address)

    $parsed = $null
    if (-not [System.Net.IPAddress]::TryParse($Address, [ref]$parsed)) { return $false }
    $bytes = $parsed.GetAddressBytes()
    if ($bytes.Length -ne 4) { return $false }
    return ($bytes[0] -eq 10) -or
        ($bytes[0] -eq 192 -and $bytes[1] -eq 168) -or
        ($bytes[0] -eq 172 -and $bytes[1] -ge 16 -and $bytes[1] -le 31)
}
