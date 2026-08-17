# Remove o autostart do Pop Spot no Windows (não apaga a pasta do projeto).
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$venvPy = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (Test-Path $venvPy) {
    & $venvPy (Join-Path $PSScriptRoot "win\autostart.py") off
} else {
    $startup = [Environment]::GetFolderPath("Startup")
    Remove-Item (Join-Path $startup "Pop Spot.lnk") -ErrorAction SilentlyContinue
}

Write-Host "Pop Spot autostart removed."
Write-Host "The project folder was not deleted."
Write-Host "To start again: .\launch_windows.ps1"
Write-Host "To enable login start: .\install_windows.ps1"
