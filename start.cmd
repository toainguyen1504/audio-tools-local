@echo off
cd /d "%~dp0"
set PYTHONUTF8=1
py -3.12 -m pion_audio.server
pause
