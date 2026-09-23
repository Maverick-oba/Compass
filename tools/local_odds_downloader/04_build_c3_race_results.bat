@echo off
setlocal
chcp 65001 >nul
set "PYTHONUTF8=1"
set "ROOT=%~dp0"

echo C3 Race Results Dataset
echo.

set "PYTHON_EXE="
set "PYTHON_ARGS="
where python.exe >nul 2>&1
if not errorlevel 1 set "PYTHON_EXE=python.exe"

if not defined PYTHON_EXE (
  py.exe -3 -c "import sys" >nul 2>&1
  if not errorlevel 1 (
    set "PYTHON_EXE=py.exe"
    set "PYTHON_ARGS=-3"
  )
)

if not defined PYTHON_EXE if exist "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" (
  set "PYTHON_EXE=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
)

if not defined PYTHON_EXE (
  echo ERROR: Python 3 was not found.
  echo.
  pause
  exit /b 1
)

"%PYTHON_EXE%" %PYTHON_ARGS% "%ROOT%scripts\research\build_c3_race_results.py"
set "EXIT_CODE=%ERRORLEVEL%"

echo.
if not "%EXIT_CODE%"=="0" echo Completed with exit code %EXIT_CODE%.
pause
exit /b %EXIT_CODE%
