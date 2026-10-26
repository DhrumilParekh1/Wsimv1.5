@echo off
setlocal
cd /d "%~dp0"
title RINGSIDE - Wrestling Promotion Simulator V1.3
set "RINGSIDE_OLLAMA_ENABLED=1"
if not defined RINGSIDE_OLLAMA_MODEL set "RINGSIDE_OLLAMA_MODEL=llama3.2"
where py >nul 2>&1
if %ERRORLEVEL%==0 (
  set "PYTHON_CMD=py"
) else (
  set "PYTHON_CMD=python"
)
if not exist ".venv\Scripts\python.exe" (
  echo Creating local Python environment...
  %PYTHON_CMD% -m venv .venv
  if errorlevel 1 goto :error
)
echo Installing or updating game dependencies...
".venv\Scripts\python.exe" -m pip install -e .
if errorlevel 1 goto :error
echo RINGSIDE uses Ollama automatically for narrative content.
echo Model: %RINGSIDE_OLLAMA_MODEL%
echo If Ollama is unavailable, simulation remains playable and AI narration shows a warning.
echo Launching RINGSIDE in your browser...
".venv\Scripts\wrestling-sim.exe" web
if errorlevel 1 goto :error
goto :end
:error
echo.
echo Something went wrong. See the error messages above.
pause
:end
endlocal
