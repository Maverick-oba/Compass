param(
    [Parameter(Mandatory = $true)][ValidatePattern('^\d{8}$')][string]$Date,
    [Parameter(Mandatory = $true)][ValidatePattern('^\d{2}$')][string]$TrackCode,
    [Parameter(Mandatory = $true)][ValidateRange(1, 12)][int]$Race,
    [Parameter(Mandatory = $true)][ValidateSet('0B41', '0B42')][string]$DataSpec,
    [Parameter(Mandatory = $true)][string]$StageFile
)

$ErrorActionPreference = 'Stop'
$expectedSavePath = 'C:\UmaConn\chiho.k-ba\data\'
$raceKey = $Date + $TrackCode + $Race.ToString('00')

function Write-Stage([string]$Name) {
    [IO.File]::WriteAllText($StageFile, ($Name + '|' + [DateTime]::UtcNow.ToString('o')))
}

$result = [ordered]@{
    started_at = (Get-Date).ToString('o')
    finished_at = $null
    elapsed_seconds = $null
    date = $Date
    track_code = $TrackCode
    race = $Race
    race_key = $raceKey
    dataspec = $DataSpec
    is64bit_process = [Environment]::Is64BitProcess
    com_success = $false
    com_seconds = $null
    nvinit_result = $null
    nvinit_seconds = $null
    m_savepath = $null
    savepath_match = $false
    rtopen_result = $null
    rtopen_seconds = $null
    nvstatus = $null
    nvstatus_seconds = $null
    nvread_records = 0
    nvread_calls = 0
    nvread_seconds = $null
    eof_reached = $false
    last_record_prefix60 = $null
    read_error = $null
    nvclose_result = $null
    nvclose_seconds = $null
    error = $null
}

$whole = [Diagnostics.Stopwatch]::StartNew()
$nv = $null

try {
    if ($result.is64bit_process) { throw 'Is64BitProcess=True; 32-bit PowerShell is required.' }

    Write-Stage 'COM_START'
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $nv = New-Object -ComObject NVDTLabLib.NVLink
    $sw.Stop()
    $result.com_success = $true
    $result.com_seconds = $sw.Elapsed.TotalSeconds
    Write-Stage 'COM_DONE'

    $sw.Restart()
    $result.nvinit_result = [int]$nv.NVInit('UNKNOWN')
    $sw.Stop()
    $result.nvinit_seconds = $sw.Elapsed.TotalSeconds
    if ($result.nvinit_result -ne 0) { throw "NVInit returned $($result.nvinit_result)" }

    $result.m_savepath = [string]$nv.m_savepath
    $result.savepath_match = [string]::Equals($result.m_savepath, $expectedSavePath, [StringComparison]::OrdinalIgnoreCase)
    if (-not $result.savepath_match) {
        throw "m_savepath mismatch. Expected '$expectedSavePath'; actual '$($result.m_savepath)'."
    }

    Write-Stage 'RTOPEN_START'
    $sw.Restart()
    $result.rtopen_result = [int]$nv.NVRTOpen($DataSpec, $raceKey)
    $sw.Stop()
    $result.rtopen_seconds = $sw.Elapsed.TotalSeconds
    Write-Stage 'RTOPEN_DONE'

    if ($result.rtopen_result -ne 0) {
        $result.error = "NVRTOpen returned $($result.rtopen_result)"
    }
    else {
        $sw.Restart()
        $result.nvstatus = [int]$nv.NVStatus()
        $sw.Stop()
        $result.nvstatus_seconds = $sw.Elapsed.TotalSeconds

        if ($result.nvstatus -lt 0) {
            $result.error = "NVStatus returned $($result.nvstatus)"
        }
        else {
            Write-Stage 'READ_START'
            $sw.Restart()
            for ($call = 1; $call -le 1000; $call++) {
                $buff = ''
                [int]$size = 0
                $filename = ''
                $readResult = [int]$nv.NVRead([ref]$buff, [ref]$size, [ref]$filename)
                $result.nvread_calls = $call

                if ($readResult -gt 0) {
                    $result.nvread_records++
                    if ($buff.Length -gt 0) {
                        $take = [Math]::Min(60, $buff.Length)
                        $result.last_record_prefix60 = $buff.Substring(0, $take)
                    }
                    continue
                }
                if ($readResult -eq -1) { continue }
                if ($readResult -eq 0) {
                    $result.eof_reached = $true
                    break
                }

                $result.read_error = $readResult
                $result.error = "NVRead returned $readResult"
                break
            }
            $sw.Stop()
            $result.nvread_seconds = $sw.Elapsed.TotalSeconds

            if (-not $result.eof_reached -and $null -eq $result.error) {
                $result.read_error = 'MAX_READ_CALLS'
                $result.error = 'NVRead did not reach EOF within 1000 calls.'
            }
        }
    }
}
catch {
    if ($null -eq $result.error) { $result.error = $_.Exception.Message }
}
finally {
    if ($null -ne $nv) {
        try {
            $sw = [Diagnostics.Stopwatch]::StartNew()
            $result.nvclose_result = [int]$nv.NVClose()
            $sw.Stop()
            $result.nvclose_seconds = $sw.Elapsed.TotalSeconds
        }
        catch {
            if ($null -eq $result.error) { $result.error = "NVClose failed: $($_.Exception.Message)" }
        }
        try { [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($nv) } catch {}
        $nv = $null
    }
    $whole.Stop()
    $result.finished_at = (Get-Date).ToString('o')
    $result.elapsed_seconds = $whole.Elapsed.TotalSeconds
    Write-Stage 'DONE'
}

Write-Output ('RESULT_JSON|' + ($result | ConvertTo-Json -Depth 6 -Compress))
