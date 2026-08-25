@echo off
setlocal

if "%~3"=="" (
  echo Usage: %~nx0 YYYYMMDD TrackCode Race
  echo Example: %~nx0 20260825 43 12
  exit /b 2
)

"C:\Windows\SysWOW64\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -STA -ExecutionPolicy Bypass -File "C:\KEIBA_AI\local_odds_downloader\scripts\download_local_odds.ps1" -Date "%~1" -TrackCode "%~2" -Race "%~3"
exit /b %errorlevel%
