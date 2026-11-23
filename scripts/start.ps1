$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$env:PYTHONUTF8 = '1'
if (-not (Test-Path '.venv-kokoro/Scripts/python.exe')) {
    throw 'Chua cai Kokoro. Chay scripts/setup-kokoro.ps1 truoc.'
}
& '.venv-kokoro/Scripts/python.exe' -X utf8 -m pion_audio.server
