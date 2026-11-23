$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
. "$PSScriptRoot/common.ps1"
$env:PYTHONUTF8 = '1'
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw 'Can cai Git truoc.' }
if (-not (Test-Path '.venv-melo/Scripts/python.exe')) {
    $basePython = Find-Python @('3.10')
    & $basePython -m venv .venv-melo
    Check-Exit
}
$python = '.venv-melo/Scripts/python.exe'
Check-Venv $python @('3.10')
& $python -m pip install --upgrade pip 'setuptools<81' wheel
Check-Exit
& $python -m pip install torch==2.5.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cpu
Check-Exit
& $python -m pip install -r requirements/melo.txt
Check-Exit
& $python -m unidic download
Check-Exit
& $python -c "import nltk; [nltk.download(p, raise_on_error=True) for p in ['averaged_perceptron_tagger', 'averaged_perceptron_tagger_eng', 'cmudict', 'punkt', 'punkt_tab']]"
Check-Exit
Write-Host 'MeloTTS da cai. Lan tao dau se tai them model tu Hugging Face.'
