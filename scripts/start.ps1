$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$env:PYTHONUTF8 = '1'
py -3.12 -m pion_audio.server
