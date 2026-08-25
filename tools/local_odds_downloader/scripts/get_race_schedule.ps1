param(
    [Parameter(Mandatory = $true)][ValidatePattern('^\d{8}$')][string]$Date,
    [ValidatePattern('^\d{2}$')][string]$TrackCode,
    [switch]$NoPostgresFallback
)

$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$tracks = Import-PowerShellDataFile -LiteralPath (Join-Path $root 'config\track_codes.psd1')
$umaRoot = 'C:\UmaConn\chiho.k-ba\data\'
$year = $Date.Substring(0, 4)

if ($TrackCode -and -not $tracks.ContainsKey($TrackCode)) {
    throw "Unsupported track code '$TrackCode'."
}

function New-ScheduleRow([string]$Code, [string]$RaceNumber, [string]$PostTime, [string]$Source) {
    if (-not $tracks.ContainsKey($Code)) { return $null }
    if ($TrackCode -and $Code -ne $TrackCode) { return $null }
    $post = [DateTime]::ParseExact($Date + $PostTime, 'yyyyMMddHHmm', [Globalization.CultureInfo]::InvariantCulture)
    return [pscustomobject]@{
        race_date = $Date
        track_code = $Code
        track_name = $tracks[$Code]
        race = [int]$RaceNumber
        post_time = $PostTime.Substring(0, 2) + ':' + $PostTime.Substring(2, 2)
        post_datetime = $post
        race_key = $Date + $Code + ([int]$RaceNumber).ToString('00')
        source = $Source
    }
}

function Read-UmaConnRaceData {
    $cacheDirectory = Join-Path $umaRoot (Join-Path 'cache' $year)
    $files = @(Get-ChildItem -LiteralPath $cacheDirectory -Filter ('RANV' + $Date + '*.nvd') -File -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending)
    if ($files.Count -eq 0) { return @() }

    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $rows = New-Object Collections.Generic.List[object]
    $zip = [IO.Compression.ZipFile]::OpenRead($files[0].FullName)
    try {
        foreach ($entry in $zip.Entries) {
            $stream = $entry.Open()
            try {
                $reader = New-Object IO.StreamReader($stream, [Text.Encoding]::GetEncoding(932), $false)
                try { $text = $reader.ReadToEnd() } finally { $reader.Dispose() }
            }
            finally { $stream.Dispose() }

            foreach ($line in ($text -split "`r?`n")) {
                if ($line.Length -lt 877 -or $line.Substring(0, 2) -ne 'RA') { continue }
                $recordDate = $line.Substring(11, 4) + $line.Substring(15, 4)
                if ($recordDate -ne $Date) { continue }
                $row = New-ScheduleRow $line.Substring(19, 2) $line.Substring(25, 2) $line.Substring(873, 4) ('UmaConn:' + $files[0].Name)
                if ($row) { $rows.Add($row) }
            }
        }
    }
    finally { $zip.Dispose() }
    return $rows.ToArray()
}

function Read-PostgresRaceData {
    $psql = 'C:\Program Files\PostgreSQL\16\bin\psql.exe'
    $pgpass = Join-Path $env:APPDATA 'postgresql\pgpass.conf'
    if (-not (Test-Path -LiteralPath $psql) -or -not (Test-Path -LiteralPath $pgpass)) { return @() }

    $codes = if ($TrackCode) { "'$TrackCode'" } else { ($tracks.Keys | Sort-Object | ForEach-Object { "'$_'" }) -join ',' }
    $sql = "SELECT keibajo_code,race_bango,hasso_jikoku FROM public.nvd_ra WHERE kaisai_nen='$($Date.Substring(0,4))' AND kaisai_tsukihi='$($Date.Substring(4,4))' AND keibajo_code IN ($codes) ORDER BY keibajo_code,race_bango;"
    $oldPassFile = $env:PGPASSFILE
    $oldOptions = $env:PGOPTIONS
    try {
        $env:PGPASSFILE = $pgpass
        $env:PGOPTIONS = '-c default_transaction_read_only=on'
        $lines = @(& $psql -w -h localhost -p 5432 -U postgres -d pckeiba -At -F "`t" -c $sql)
        if ($LASTEXITCODE -ne 0) { throw "psql exited with code $LASTEXITCODE" }
    }
    finally {
        $env:PGPASSFILE = $oldPassFile
        $env:PGOPTIONS = $oldOptions
    }

    $rows = New-Object Collections.Generic.List[object]
    foreach ($line in $lines) {
        $parts = $line -split "`t"
        if ($parts.Count -ne 3) { continue }
        $row = New-ScheduleRow $parts[0] $parts[1] $parts[2] 'PostgreSQL:public.nvd_ra(read-only)'
        if ($row) { $rows.Add($row) }
    }
    return $rows.ToArray()
}

$schedule = @(Read-UmaConnRaceData)
if ($schedule.Count -eq 0 -and -not $NoPostgresFallback) {
    $schedule = @(Read-PostgresRaceData)
}
if ($schedule.Count -eq 0) { throw "No RACE data found for $Date." }
$schedule | Sort-Object track_code, race
