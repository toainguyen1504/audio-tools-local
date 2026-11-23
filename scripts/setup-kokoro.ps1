$ErrorActionPreference = 'Stop'
. "$PSScriptRoot/common.ps1"
Set-Location (Split-Path $PSScriptRoot -Parent)
$env:PYTHONUTF8 = '1'
if (-not (Test-Path '.venv-kokoro/Scripts/python.exe')) {
    $basePython = Find-Python @('3.12', '3.11')
    & $basePython -m venv .venv-kokoro
    Check-Exit
}
$python = '.venv-kokoro/Scripts/python.exe'
Check-Venv $python @('3.12', '3.11')
& $python -m pip install --upgrade pip
Check-Exit
& $python -m pip install -r requirements/kokoro.txt
Check-Exit
& $python -m pion_audio.download
Check-Exit
Write-Host 'Kokoro san sang. Mo start.cmd de test.'
