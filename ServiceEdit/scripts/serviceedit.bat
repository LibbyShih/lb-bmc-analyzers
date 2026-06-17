@echo off
cd /d "%~dp0.."
setlocal EnableDelayedExpansion
set "USE_CLI=0"
for %%A in (%*) do if /i "%%~A"=="--cli" set "USE_CLI=1"
if "!USE_CLI!"=="1" (
  python src\main.py %*
  if errorlevel 1 pause
) else (
  start "" pythonw src\main.py %*
)
endlocal
