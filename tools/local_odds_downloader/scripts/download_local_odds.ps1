param(
    [Parameter(Mandatory = $true)][ValidatePattern('^\d{8}$')][string]$Date,
    [Parameter(Mandatory = $true)][ValidatePattern('^\d{2}$')][string]$TrackCode,
    [Parameter(Mandatory = $true)][ValidateRange(1, 12)][int]$Race
)

$ErrorActionPreference = 'Stop'
$startedAt = Get-Date
$x86PowerShell = 'C:\Windows\SysWOW64\WindowsPowerShell\v1.0\powershell.exe'
$expectedSavePath = 'C:\UmaConn\chiho.k-ba\data\'
$root = Split-Path $PSScriptRoot -Parent
$logRoot = Join-Path $root 'logs'
$archiveRoot = Join-Path $root 'archive'
$worker = Join-Path $PSScriptRoot 'download_one_dataspec.ps1'
$trackConfig = Join-Path $root 'config\track_codes.psd1'
$raceText = $Race.ToString('00')
$raceKey = $Date + $TrackCode + $raceText
$runStamp = $startedAt.ToString('yyyyMMdd_HHmmss')
$logPath = Join-Path $logRoot ("{0}_track{1}_race{2}.log" -f $runStamp, $TrackCode, $raceText)
$runTemp = Join-Path $logRoot ('.run_' + $runStamp + '_' + [Guid]::NewGuid().ToString('N'))

if ([Environment]::Is64BitProcess) {
    throw "This script must run under 32-bit PowerShell: $x86PowerShell"
}
if (-not (Test-Path -LiteralPath $x86PowerShell)) { throw "32-bit PowerShell not found: $x86PowerShell" }
if (-not (Test-Path -LiteralPath $worker)) { throw "Worker script not found: $worker" }

$tracks = Import-PowerShellDataFile -LiteralPath $trackConfig
if (-not $tracks.ContainsKey($TrackCode)) {
    throw "Unsupported track code '$TrackCode'. Only statically confirmed codes are allowed."
}

foreach ($path in @($logRoot, $archiveRoot, $runTemp)) {
    if (-not (Test-Path -LiteralPath $path)) { New-Item -ItemType Directory -Path $path | Out-Null }
}

function Get-FileSnapshot([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return $null }
    $item = Get-Item -LiteralPath $Path
    return [pscustomobject]@{
        length = $item.Length
        last_write_time = $item.LastWriteTime.ToString('o')
        sha256 = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash
    }
}

function Read-RtdSummary([string]$Path) {
    $data = [IO.File]::ReadAllBytes($Path)
    $position = 0
    $records = New-Object Collections.Generic.List[object]
    while ($position + 30 -le $data.Length -and [BitConverter]::ToUInt32($data, $position) -eq 0x04034b50) {
        $method = [BitConverter]::ToUInt16($data, $position + 8)
        $compressedSize = [BitConverter]::ToUInt32($data, $position + 18)
        $nameLength = [BitConverter]::ToUInt16($data, $position + 26)
        $extraLength = [BitConverter]::ToUInt16($data, $position + 28)
        $contentStart = $position + 30 + $nameLength + $extraLength
        if ($contentStart + $compressedSize -gt $data.Length) { throw 'Invalid local ZIP entry length.' }

        $compressed = New-Object byte[] $compressedSize
        [Array]::Copy($data, $contentStart, $compressed, 0, $compressedSize)
        $input = New-Object IO.MemoryStream(,$compressed)
        try {
            if ($method -eq 8) {
                $deflate = New-Object IO.Compression.DeflateStream($input, [IO.Compression.CompressionMode]::Decompress)
                try {
                    $output = New-Object IO.MemoryStream
                    $deflate.CopyTo($output)
                    $raw = $output.ToArray()
                }
                finally { $deflate.Dispose() }
            }
            elseif ($method -eq 0) { $raw = $compressed }
            else { throw "Unsupported ZIP compression method: $method" }
        }
        finally { $input.Dispose() }

        $text = [Text.Encoding]::GetEncoding(932).GetString($raw).TrimEnd("`r", "`n")
        $timestamp = if ($text.Length -ge 35) { $text.Substring(27, 8) } else { $null }
        $prefix = if ($text.Length -gt 0) { $text.Substring(0, [Math]::Min(60, $text.Length)) } else { '' }
        $records.Add([pscustomobject]@{ timestamp = $timestamp; prefix = $prefix })
        $position = $contentStart + $compressedSize
    }

    $latest = $records | Where-Object { $_.timestamp } | Sort-Object timestamp | Select-Object -Last 1
    return [pscustomobject]@{
        entry_count = $records.Count
        latest_timestamp = if ($latest) { $latest.timestamp } else { $null }
        latest_time = if ($latest -and $latest.timestamp.Length -eq 8) { $latest.timestamp.Substring(4, 2) + ':' + $latest.timestamp.Substring(6, 2) } else { $null }
        latest_prefix60 = if ($latest) { $latest.prefix } else { $null }
    }
}

function Invoke-OneDataSpec([string]$DataSpec) {
    $expectedFileName = $DataSpec + $raceKey + '.rtd'
    $sourcePath = Join-Path $expectedSavePath (Join-Path 'cache' (Join-Path $Date.Substring(0, 4) $expectedFileName))
    $before = Get-FileSnapshot $sourcePath
    $stageFile = Join-Path $runTemp ($DataSpec + '.stage')
    $stdoutFile = Join-Path $runTemp ($DataSpec + '.stdout')
    $stderrFile = Join-Path $runTemp ($DataSpec + '.stderr')

    $arguments = @(
        '-NoProfile', '-STA', '-ExecutionPolicy', 'Bypass', '-File', $worker,
        '-Date', $Date, '-TrackCode', $TrackCode, '-Race', [string]$Race,
        '-DataSpec', $DataSpec, '-StageFile', $stageFile
    )
    $processStarted = Get-Date
    $process = Start-Process -FilePath $x86PowerShell -ArgumentList $arguments -PassThru -WindowStyle Hidden -RedirectStandardOutput $stdoutFile -RedirectStandardError $stderrFile
    $watchdogError = $null

    while (-not $process.HasExited) {
        if (Test-Path -LiteralPath $stageFile) {
            $stage = [IO.File]::ReadAllText($stageFile).Split('|')
            if ($stage.Count -ge 2 -and ($stage[0] -eq 'COM_START' -or $stage[0] -eq 'RTOPEN_START')) {
                $stageStarted = [DateTime]::Parse($stage[1]).ToUniversalTime()
                if (([DateTime]::UtcNow - $stageStarted).TotalSeconds -gt 30) {
                    $watchdogError = $stage[0] + '_TIMEOUT_30S'
                    Stop-Process -Id $process.Id -Force
                    break
                }
            }
        }
        if (((Get-Date) - $processStarted).TotalSeconds -gt 180) {
            $watchdogError = 'OVERALL_TIMEOUT_180S'
            Stop-Process -Id $process.Id -Force
            break
        }
        Start-Sleep -Milliseconds 200
        $process.Refresh()
    }
    try { $process.WaitForExit() } catch {}

    $stdout = if (Test-Path $stdoutFile) { [IO.File]::ReadAllText($stdoutFile) } else { '' }
    $stderr = if (Test-Path $stderrFile) { [IO.File]::ReadAllText($stderrFile).Trim() } else { '' }
    $resultLine = @($stdout -split "`r?`n" | Where-Object { $_ -like 'RESULT_JSON|*' }) | Select-Object -Last 1
    $workerResult = if ($resultLine) { $resultLine.Substring(12) | ConvertFrom-Json } else { $null }

    $item = [ordered]@{
        dataspec = $DataSpec
        expected_rtd = $sourcePath
        source_before = $before
        worker = $workerResult
        watchdog_error = $watchdogError
        stderr = $stderr
        source_after = $null
        source_changed = $null
        zip_entry_count = $null
        latest_timestamp = $null
        latest_time = $null
        last_record_prefix60 = if ($workerResult) { $workerResult.last_record_prefix60 } else { $null }
        archive_path = $null
        archive_size = $null
        archive_sha256 = $null
        hash_match = $false
        error = $null
    }

    if ($watchdogError) { $item.error = $watchdogError; return [pscustomobject]$item }
    if (-not $workerResult) { $item.error = 'Worker returned no result. ' + $stderr; return [pscustomobject]$item }
    if ($workerResult.error) { $item.error = $workerResult.error; return [pscustomobject]$item }
    if ($workerResult.rtopen_result -ne 0 -or -not $workerResult.eof_reached -or $workerResult.nvclose_result -ne 0) {
        $item.error = 'Acquisition did not finish cleanly.'
        return [pscustomobject]$item
    }
    if (-not (Test-Path -LiteralPath $sourcePath)) { $item.error = "Expected .rtd not found: $sourcePath"; return [pscustomobject]$item }

    $after = Get-FileSnapshot $sourcePath
    $item.source_after = $after
    $item.source_changed = ($null -eq $before -or $before.sha256 -ne $after.sha256 -or $before.last_write_time -ne $after.last_write_time)
    $rtd = Read-RtdSummary $sourcePath
    $item.zip_entry_count = $rtd.entry_count
    $item.latest_timestamp = $rtd.latest_timestamp
    $item.latest_time = $rtd.latest_time
    $item.last_record_prefix60 = $rtd.latest_prefix60

    $destinationDirectory = Join-Path $archiveRoot (Join-Path $Date (Join-Path $TrackCode (Join-Path ($raceText + 'R') $DataSpec)))
    if (-not (Test-Path -LiteralPath $destinationDirectory)) { New-Item -ItemType Directory -Path $destinationDirectory -Force | Out-Null }
    $copyStamp = (Get-Date).ToString('yyyyMMdd_HHmmss')
    $destinationName = $copyStamp + '_' + $expectedFileName
    $destinationPath = Join-Path $destinationDirectory $destinationName
    $suffix = 1
    while (Test-Path -LiteralPath $destinationPath) {
        $destinationName = $copyStamp + '_' + $suffix.ToString('000') + '_' + $expectedFileName
        $destinationPath = Join-Path $destinationDirectory $destinationName
        $suffix++
    }

    Copy-Item -LiteralPath $sourcePath -Destination $destinationPath
    $archive = Get-FileSnapshot $destinationPath
    $item.archive_path = $destinationPath
    $item.archive_size = $archive.length
    $item.archive_sha256 = $archive.sha256
    $item.hash_match = ($after.length -eq $archive.length -and $after.sha256 -eq $archive.sha256)
    if (-not $item.hash_match) { $item.error = 'Archive copy hash/size mismatch.' }
    return [pscustomobject]$item
}

$results = New-Object Collections.Generic.List[object]
$fatalError = $null
try {
    foreach ($spec in @('0B41', '0B42')) { $results.Add((Invoke-OneDataSpec $spec)) }
}
catch { $fatalError = $_.Exception.Message }

$finishedAt = Get-Date
$totalOk = (-not $fatalError -and $results.Count -eq 2 -and @($results | Where-Object { $_.error -or -not $_.hash_match }).Count -eq 0)
$logObject = [ordered]@{
    started_at = $startedAt.ToString('o')
    finished_at = $finishedAt.ToString('o')
    elapsed_seconds = ($finishedAt - $startedAt).TotalSeconds
    date = $Date
    track_code = $TrackCode
    track_name = $tracks[$TrackCode]
    race = $Race
    race_key = $raceKey
    expected_savepath = $expectedSavePath
    is64bit_process = [Environment]::Is64BitProcess
    results = $results
    total_ok = $totalOk
    fatal_error = $fatalError
}
$logObject | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $logPath -Encoding UTF8

Write-Output 'Local Odds Downloader'
Write-Output ("Date: {0}" -f $Date)
Write-Output ("Track: {0} ({1})" -f $TrackCode, $tracks[$TrackCode])
Write-Output ("Race: {0}" -f $raceText)
Write-Output ("Key: {0}" -f $raceKey)
Write-Output ''
foreach ($item in $results) {
    Write-Output ($item.dataspec + ':')
    Write-Output ('  result: ' + $(if ($item.error) { 'ERROR' } else { 'OK' }))
    if ($item.worker) { Write-Output ("  records: {0}" -f $item.worker.nvread_records) }
    Write-Output ("  latest: {0}" -f $item.latest_time)
    Write-Output ("  archive: {0}" -f $item.archive_path)
    if ($item.error) { Write-Output ("  error: {0}" -f $item.error) }
}
Write-Output ''
Write-Output ('Total: ' + $(if ($totalOk) { 'OK' } else { 'ERROR' }))
Write-Output ("Log: {0}" -f $logPath)

if (-not $totalOk) { exit 1 }
