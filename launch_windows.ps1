# Abre o Pop Spot (UI Windows / Qt).
# Primeira vez: powershell -ExecutionPolicy Bypass -File install_windows.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$venv = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (Test-Path $venv) {
    & $venv "main.py"
    exit $LASTEXITCODE
}
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { $py = Get-Command py -ErrorAction SilentlyContinue }
if (-not $py) {
    Write-Error "Python não encontrado. Instale Python 3 e marque 'Add to PATH'."
}
& $py.Source "main.py"
