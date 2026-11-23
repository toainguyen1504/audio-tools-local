$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
function Check-Exit { if ($LASTEXITCODE -ne 0) { throw 'Lenh that bai. Xem loi o tren va thu lai.' } }
py -3.12 -c "import struct; assert struct.calcsize('P') == 8, 'Can Python x64'"
Check-Exit
if (-not (Test-Path '.venv-kokoro/Scripts/python.exe')) {
    py -3.12 -m venv .venv-kokoro
    Check-Exit
}
$python = '.venv-kokoro/Scripts/python.exe'
& $python -m pip install --upgrade pip
Check-Exit
& $python -m pip install -r requirements/kokoro.txt
Check-Exit
& $python -m pion_audio.download
Check-Exit
Write-Host 'Kokoro san sang. Chay scripts/start.ps1 de mo giao dien.'
