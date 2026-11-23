@echo off
cd /d "%~dp0"
set PYTHONUTF8=1
if not exist ".venv-kokoro\Scripts\python.exe" (
  echo Chua cai Kokoro. Chay scripts\setup-kokoro.ps1 truoc.
  pause
  exit /b 1
)
".venv-kokoro\Scripts\python.exe" -X utf8 -m pion_audio.server
pause
