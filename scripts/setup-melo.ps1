$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
function Check-Exit { if ($LASTEXITCODE -ne 0) { throw 'Lenh that bai. Xem loi o tren va thu lai.' } }
py -3.10 -c "import struct; assert struct.calcsize('P') == 8, 'Can Python x64'"
Check-Exit
if (-not (Test-Path '.venv-melo/Scripts/python.exe')) {
    py -3.10 -m venv .venv-melo
    Check-Exit
}
$python = '.venv-melo/Scripts/python.exe'
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
