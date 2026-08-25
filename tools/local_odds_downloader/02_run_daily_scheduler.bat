@echo off
setlocal

"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\run_daily_local_odds.ps1" %*
set "scheduler_exit=%errorlevel%"

if not "%scheduler_exit%"=="0" (
  echo.
  echo Scheduler stopped with error code %scheduler_exit%.
  pause
)

exit /b %scheduler_exit%
