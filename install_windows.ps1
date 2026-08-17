# Instala dependências, liga o widget no login e abre o Pop Spot (Windows).
# Uso: powershell -ExecutionPolicy Bypass -File install_windows.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Invoke-SystemPython {
    param([Parameter(Mandatory = $true, ValueFromRemainingArguments = $true)]$Args)
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) { & $py.Source -3 @Args; return }
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) { & $python.Source @Args; return }
    throw "Python 3 não encontrado. Instale Python 3.10+ e marque 'Add python.exe to PATH'."
}

$venvPy = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
$venvW = Join-Path $PSScriptRoot ".venv\Scripts\pythonw.exe"
if (-not (Test-Path $venvPy)) {
    Write-Host "==> Criando .venv..."
    Invoke-SystemPython -m venv .venv
    if (-not (Test-Path $venvPy)) {
        throw "Falha ao criar .venv"
    }
}

Write-Host "==> Instalando pacotes (requirements-windows.txt)..."
& $venvPy -m pip install --upgrade pip
& $venvPy -m pip install -r (Join-Path $PSScriptRoot "requirements-windows.txt")

Write-Host "==> Ligando autostart (pasta Inicializar)..."
& $venvPy (Join-Path $PSScriptRoot "win\autostart.py") on

Write-Host "==> Iniciando Pop Spot..."
$main = Join-Path $PSScriptRoot "main.py"
Start-Process -FilePath $venvW -ArgumentList "`"$main`"" -WorkingDirectory $PSScriptRoot

Write-Host ""
Write-Host "Pop Spot instalado e vai abrir no login."
Write-Host "Abrir na mão:  .\launch_windows.ps1"
Write-Host "Desinstalar autostart:  .\uninstall_windows.ps1"
