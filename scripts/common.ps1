$ErrorActionPreference = 'Stop'
function Check-Exit {
    if ($LASTEXITCODE -ne 0) { throw 'Lenh that bai. Xem loi o tren va thu lai.' }
}
function Find-Python([string[]]$Versions) {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        foreach ($version in $Versions) {
            try {
                $result = & py "-$version" -c "import sys,struct; assert struct.calcsize('P')==8; print(sys.executable)" 2>$null
                if ($LASTEXITCODE -eq 0 -and $result) { return ($result | Select-Object -Last 1) }
            } catch { }
        }
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        try {
            $allowed = $Versions -join ','
            $result = & python -c "import sys,struct; assert struct.calcsize('P')==8; assert '.'.join(map(str,sys.version_info[:2])) in '$allowed'.split(','); print(sys.executable)" 2>$null
            if ($LASTEXITCODE -eq 0 -and $result) { return ($result | Select-Object -Last 1) }
        } catch { }
    }
    throw "Can Python x64 ($($Versions -join ' / ')). Kiem tra bang: py -0p"
}
function Check-Venv([string]$Python, [string[]]$Versions) {
    $allowed = $Versions -join ','
    & $Python -c "import sys,struct; assert struct.calcsize('P')==8, 'Can Python x64'; assert '.'.join(map(str,sys.version_info[:2])) in '$allowed'.split(','), 'Sai phien ban Python cua venv'"
    Check-Exit
}
