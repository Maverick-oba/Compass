param(
    [ValidatePattern('^\d{8}$')][string]$Date = (Get-Date -Format 'yyyyMMdd'),
    [ValidateRange(1, 60)][int]$RefreshSeconds = 5,
    [switch]$DryRun,
    [switch]$RunNextOnly
)

$ErrorActionPreference = 'Stop'
$schedulerStartedAt = Get-Date
$root = Split-Path $PSScriptRoot -Parent
$scheduleScript = Join-Path $PSScriptRoot 'get_race_schedule.ps1'
$downloadScript = Join-Path $PSScriptRoot 'download_local_odds.ps1'
$x86PowerShell = 'C:\Windows\SysWOW64\WindowsPowerShell\v1.0\powershell.exe'
$logDirectory = Join-Path $root 'logs'
$logPath = Join-Path $logDirectory ("scheduler_{0}.log" -f $Date)
$trackNames = @{
    '42' = '川崎'
    '43' = '船橋'
    '44' = '大井'
    '45' = '浦和'
}
$mutex = $null
$mutexOwned = $false
$lastExecution = $null

function Write-SchedulerLog([string]$Event, [string]$Message) {
    $line = "{0}`t{1}`t{2}" -f (Get-Date).ToString('o'), $Event, $Message
    Add-Content -LiteralPath $logPath -Value $line -Encoding UTF8
}

function Set-SchedulerTitle([string]$Title) {
    try { [Console]::Title = $Title } catch {}
}

function Format-Remaining([TimeSpan]$Remaining) {
    if ($Remaining.TotalSeconds -lt 0) { $Remaining = [TimeSpan]::Zero }
    return '{0:00}:{1:00}:{2:00}' -f [Math]::Floor($Remaining.TotalHours), $Remaining.Minutes, $Remaining.Seconds
}

function Get-TrackDisplayName([string]$TrackCode) {
    if ($trackNames.ContainsKey($TrackCode)) { return $trackNames[$TrackCode] }
    return $TrackCode
}

function Show-SchedulerStatus([object[]]$Events, [object[]]$Races, [DateTime]$AutoExitAt) {
    $now = Get-Date
    $next = $Events | Where-Object { $_.Status -eq 'PENDING' } | Sort-Object ScheduledAt, TrackCode, Race, LeadMinutes | Select-Object -First 1
    $tracks = @($Races | Select-Object -ExpandProperty TrackCode -Unique | ForEach-Object { Get-TrackDisplayName $_ }) -join ', '
    $finalPost = ($Races | Measure-Object -Property PostDateTime -Maximum).Maximum
    $finalRaces = @($Races | Where-Object { $_.PostDateTime -eq $finalPost } | Sort-Object TrackCode, Race)

    try { Clear-Host } catch {}
    Write-Host '----------------------------------------'
    Write-Host 'Local Odds Scheduler'
    Write-Host ''
    Write-Host ("Current:  {0}" -f $now.ToString('HH:mm:ss'))
    Write-Host ("Tracks:   {0}" -f $tracks)
    Write-Host ''
    Write-Host 'Next:'
    if ($next) {
        Write-Host $next.ScheduledAt.ToString('HH:mm:ss')
        Write-Host ("{0}{1}R" -f (Get-TrackDisplayName $next.TrackCode), $next.Race)
        Write-Host $next.LeadLabel
        Write-Host ("残り {0}" -f (Format-Remaining ($next.ScheduledAt - $now)))
    }
    else { Write-Host '予定なし' }
    Write-Host ''
    Write-Host 'Last:'
    if ($script:lastExecution) {
        Write-Host ("{0}{1}R {2}" -f (Get-TrackDisplayName $script:lastExecution.TrackCode), $script:lastExecution.Race, $script:lastExecution.LeadLabel)
        Write-Host ("Result: {0}" -f $script:lastExecution.Result)
    }
    else { Write-Host '未実行' }
    Write-Host ''
    Write-Host 'Final race:'
    foreach ($race in $finalRaces) {
        Write-Host ("{0}{1}R {2}" -f (Get-TrackDisplayName $race.TrackCode), $race.Race, $race.PostDateTime.ToString('HH:mm'))
    }
    Write-Host ''
    Write-Host 'Auto exit:'
    Write-Host $AutoExitAt.ToString('HH:mm')
    Write-Host '----------------------------------------'
}

function Show-DryRun([object[]]$Events, [object[]]$Races, [DateTime]$AutoExitAt) {
    $next = $Events | Where-Object { $_.Status -eq 'PENDING' } | Sort-Object ScheduledAt, TrackCode, Race, LeadMinutes | Select-Object -First 1
    Write-Host 'Local Odds Scheduler - DRY RUN'
    Write-Host ("Date: {0}" -f $Date)
    Write-Host ("Started: {0}" -f $schedulerStartedAt.ToString('yyyy-MM-dd HH:mm:ss'))
    Write-Host ''
    Write-Host 'Races:'
    $Races | Sort-Object PostDateTime, TrackCode, Race | Select-Object @{Name='Track';Expression={Get-TrackDisplayName $_.TrackCode}}, Race, @{Name='Post';Expression={$_.PostDateTime.ToString('HH:mm')}}, Source | Format-Table -AutoSize
    Write-Host 'Schedule:'
    $Events | Sort-Object ScheduledAt, TrackCode, Race, LeadMinutes | Select-Object @{Name='Time';Expression={$_.ScheduledAt.ToString('HH:mm:ss')}}, @{Name='Track';Expression={Get-TrackDisplayName $_.TrackCode}}, Race, LeadLabel, Status | Format-Table -AutoSize
    if ($next) {
        Write-Host ("Next: {0} {1}{2}R {3}" -f $next.ScheduledAt.ToString('HH:mm:ss'), (Get-TrackDisplayName $next.TrackCode), $next.Race, $next.LeadLabel)
    }
    else { Write-Host 'Next: none' }
    Write-Host ("Auto exit: {0}" -f $AutoExitAt.ToString('yyyy-MM-dd HH:mm:ss'))
}

function Invoke-OddsDownload([object]$Event) {
    $trackName = Get-TrackDisplayName $Event.TrackCode
    $title = "ODDS DOWNLOADING - {0}{1}R" -f $trackName, $Event.Race
    Set-SchedulerTitle $title
    try { Clear-Host } catch {}
    Write-Host '*** ODDS DOWNLOADING ***' -ForegroundColor Yellow
    Write-Host ("{0}{1}R / {2}" -f $trackName, $Event.Race, $Event.LeadLabel) -ForegroundColor Yellow
    Write-Host ''

    Write-SchedulerLog 'download_start' ("id={0};track={1};race={2};lead={3};scheduled={4}" -f $Event.Id, $Event.TrackCode, $Event.Race, $Event.LeadMinutes, $Event.ScheduledAt.ToString('o'))
    $started = Get-Date
    $output = @(& $x86PowerShell -NoProfile -STA -ExecutionPolicy Bypass -File $downloadScript -Date $Date -TrackCode $Event.TrackCode -Race $Event.Race 2>&1)
    $exitCode = $LASTEXITCODE
    $elapsed = ((Get-Date) - $started).TotalSeconds
    $resultText = if ($exitCode -eq 0) { 'OK' } else { 'FAILED' }
    Write-SchedulerLog 'download_end' ("id={0};result={1};exit_code={2};elapsed_seconds={3:N3}" -f $Event.Id, $resultText, $exitCode, $elapsed)

    $script:lastExecution = [pscustomobject]@{
        TrackCode = $Event.TrackCode
        Race = $Event.Race
        LeadLabel = $Event.LeadLabel
        Result = $resultText
        ExitCode = $exitCode
    }
    return $exitCode
}

try {
    foreach ($required in @($scheduleScript, $downloadScript, $x86PowerShell)) {
        if (-not (Test-Path -LiteralPath $required -PathType Leaf)) { throw "Required file not found: $required" }
    }
    & $x86PowerShell -NoProfile -Command "if ([Environment]::Is64BitProcess) { exit 2 } else { exit 0 }"
    if ($LASTEXITCODE -ne 0) { throw "32-bit PowerShell preflight failed with exit code $LASTEXITCODE." }
    if (-not (Get-Command Import-PowerShellDataFile -ErrorAction SilentlyContinue)) {
        $utilityModule = Join-Path $PSHOME 'Modules\Microsoft.PowerShell.Utility\Microsoft.PowerShell.Utility.psd1'
        if (-not (Test-Path -LiteralPath $utilityModule -PathType Leaf)) { throw "PowerShell utility module not found: $utilityModule" }
        Import-Module -Name $utilityModule -ErrorAction Stop
    }
    if (-not (Get-Command Import-PowerShellDataFile -ErrorAction SilentlyContinue)) {
        throw 'Import-PowerShellDataFile is unavailable; RACE schedule cannot be loaded.'
    }
    if (-not $DryRun -and $Date -ne (Get-Date -Format 'yyyyMMdd')) {
        throw 'Live scheduler can run only for the current local date. Use -DryRun for another date.'
    }
    if (-not (Test-Path -LiteralPath $logDirectory)) { New-Item -ItemType Directory -Path $logDirectory | Out-Null }

    $mutex = New-Object Threading.Mutex($false, ("Local\LocalOddsScheduler_{0}" -f $Date))
    $mutexOwned = $mutex.WaitOne(0, $false)
    if (-not $mutexOwned) { throw "Another scheduler instance is already running for $Date." }

    Write-SchedulerLog 'scheduler_start' ("date={0};dry_run={1};run_next_only={2};refresh_seconds={3}" -f $Date, $DryRun.IsPresent, $RunNextOnly.IsPresent, $RefreshSeconds)
    Set-SchedulerTitle 'Local Odds Scheduler'

    try { $rawSchedule = @(& $scheduleScript -Date $Date) }
    catch {
        if ($_.Exception.Message -like "No RACE data found for $Date*") {
            Write-SchedulerLog 'no_races' "date=$Date"
            Write-Host "南関東4場の開催はありません: $Date"
            Write-SchedulerLog 'scheduler_end' 'result=NO_RACES'
            return
        }
        throw "RACE schedule acquisition failed: $($_.Exception.Message)"
    }
    if ($rawSchedule.Count -eq 0) {
        Write-SchedulerLog 'no_races' "date=$Date"
        Write-Host "南関東4場の開催はありません: $Date"
        Write-SchedulerLog 'scheduler_end' 'result=NO_RACES'
        return
    }

    $races = New-Object Collections.Generic.List[object]
    foreach ($row in $rawSchedule) {
        $trackCode = [string]$row.track_code
        if (-not $trackNames.ContainsKey($trackCode)) { continue }
        $postText = [string]$row.post_datetime
        $post = [DateTime]::MinValue
        if (-not [DateTime]::TryParse($postText, [ref]$post)) {
            throw "Invalid post time: track=$trackCode race=$($row.race) value='$postText'"
        }
        if ($post.ToString('yyyyMMdd') -ne $Date) {
            throw "Post date mismatch: track=$trackCode race=$($row.race) value='$postText'"
        }
        $raceNumber = [int]$row.race
        if ($raceNumber -lt 1 -or $raceNumber -gt 12) { throw "Invalid race number: $raceNumber" }
        $races.Add([pscustomobject]@{
            TrackCode = $trackCode
            Race = $raceNumber
            PostDateTime = $post
            RaceKey = [string]$row.race_key
            Source = [string]$row.source
        })
    }
    if ($races.Count -eq 0) {
        Write-SchedulerLog 'no_races' "date=$Date"
        Write-Host "南関東4場の開催はありません: $Date"
        Write-SchedulerLog 'scheduler_end' 'result=NO_RACES'
        return
    }

    $sourceText = @($races | Select-Object -ExpandProperty Source -Unique) -join ','
    $trackText = @($races | Select-Object -ExpandProperty TrackCode -Unique | Sort-Object) -join ','
    Write-SchedulerLog 'schedule_source' $sourceText
    Write-SchedulerLog 'tracks' $trackText
    foreach ($race in $races | Sort-Object TrackCode, Race) {
        Write-SchedulerLog 'race' ("track={0};race={1};post={2};key={3}" -f $race.TrackCode, $race.Race, $race.PostDateTime.ToString('o'), $race.RaceKey)
    }

    $events = New-Object Collections.Generic.List[object]
    foreach ($race in $races) {
        foreach ($lead in @(30, 15, 5)) {
            $scheduledAt = $race.PostDateTime.AddMinutes(-$lead)
            $status = if ($scheduledAt -lt $schedulerStartedAt) { 'SKIPPED' } else { 'PENDING' }
            $event = [pscustomobject]@{
                Id = "{0}-{1}-{2:00}-{3}" -f $Date, $race.TrackCode, $race.Race, $lead
                TrackCode = $race.TrackCode
                Race = $race.Race
                RaceKey = $race.RaceKey
                LeadMinutes = $lead
                LeadLabel = "{0}分前" -f $lead
                ScheduledAt = $scheduledAt
                Status = $status
            }
            $events.Add($event)
            Write-SchedulerLog 'schedule' ("id={0};time={1};status={2}" -f $event.Id, $scheduledAt.ToString('o'), $status)
            if ($status -eq 'SKIPPED') { Write-SchedulerLog 'skip' ("id={0};reason=past_at_startup" -f $event.Id) }
        }
    }

    $finalPost = ($races | Measure-Object -Property PostDateTime -Maximum).Maximum
    $autoExitAt = ([DateTime]$finalPost).AddMinutes(10)
    Write-SchedulerLog 'auto_exit_time' $autoExitAt.ToString('o')

    if ($DryRun) {
        Show-DryRun $events.ToArray() $races.ToArray() $autoExitAt
        Write-SchedulerLog 'scheduler_end' 'result=DRY_RUN'
        return
    }

    if ((Get-Date) -ge $autoExitAt) {
        Show-SchedulerStatus $events.ToArray() $races.ToArray() $autoExitAt
        Write-SchedulerLog 'scheduler_end' 'result=AUTO_EXIT_ALREADY_PASSED'
        return
    }

    $executedIds = New-Object 'Collections.Generic.HashSet[string]'
    $attemptCount = 0
    while ((Get-Date) -lt $autoExitAt) {
        $now = Get-Date
        $due = @($events | Where-Object { $_.Status -eq 'PENDING' -and $_.ScheduledAt -le $now } | Sort-Object ScheduledAt, TrackCode, Race, LeadMinutes)
        foreach ($event in $due) {
            if (-not $executedIds.Add($event.Id)) {
                $event.Status = 'DUPLICATE_SKIPPED'
                Write-SchedulerLog 'skip' ("id={0};reason=duplicate" -f $event.Id)
                continue
            }
            $event.Status = 'RUNNING'
            $exitCode = Invoke-OddsDownload $event
            $attemptCount++
            $event.Status = if ($exitCode -eq 0) { 'SUCCEEDED' } else { 'FAILED' }
            Set-SchedulerTitle 'Local Odds Scheduler'
            if ($RunNextOnly) {
                Write-SchedulerLog 'scheduler_end' ("result=RUN_NEXT_ONLY;download_result={0}" -f $event.Status)
                if ($exitCode -ne 0) { exit 1 }
                return
            }
        }
        Show-SchedulerStatus $events.ToArray() $races.ToArray() $autoExitAt
        Start-Sleep -Seconds $RefreshSeconds
    }

    Show-SchedulerStatus $events.ToArray() $races.ToArray() $autoExitAt
    Write-SchedulerLog 'scheduler_end' ("result=AUTO_EXIT;attempts={0}" -f $attemptCount)
}
catch {
    try { Write-SchedulerLog 'fatal_error' $_.Exception.Message; Write-SchedulerLog 'scheduler_end' 'result=FATAL_ERROR' } catch {}
    Write-Error $_
    exit 1
}
finally {
    Set-SchedulerTitle 'Local Odds Scheduler'
    if ($mutexOwned -and $null -ne $mutex) { try { $mutex.ReleaseMutex() } catch {} }
    if ($null -ne $mutex) { $mutex.Dispose() }
}
