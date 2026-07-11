# Gera o executavel Pop-Spot para Windows usando PyInstaller.
# Resultado: pasta dist\PopSpot\ — compacte e envie para amigos.
#
# Pre-requisito: execute install_windows.ps1 primeiro.
#
# Uso:
#   Clique com botao direito > "Executar com PowerShell"
#   Opcao para limpar build anterior: .\build_windows.ps1 -Limpar

param([switch]$Limpar)

$ErrorActionPreference = "Stop"

$msys2Root = "C:\msys64"
$bash      = "$msys2Root\usr\bin\bash.exe"
$projectWin = $PSScriptRoot

# Converte caminho Windows → MSYS2 (ex: C:\Foo → /c/Foo)
function To-MsysPath($p) {
    $drive = $p[0].ToString().ToLower()
    "/" + $drive + "/" + ($p.Substring(3) -replace "\\", "/")
}
$projectMsys = To-MsysPath $projectWin

function Step($msg) { Write-Host ""; Write-Host "==> $msg" -ForegroundColor Cyan }
function Fail($msg) {
    Write-Host "ERRO: $msg" -ForegroundColor Red
    Read-Host "Pressione Enter para fechar"
    exit 1
}

if (-not (Test-Path $bash)) { Fail "MSYS2 nao encontrado em $msys2Root. Execute install_windows.ps1 primeiro." }

function MSYS2([string]$cmd) {
    & $bash --login -c "export MSYSTEM=MINGW64; source /etc/profile; cd '$projectMsys'; $cmd"
    if ($LASTEXITCODE -ne 0) { Fail "Falha ao executar comando MSYS2." }
}

# ── Limpar build anterior ──────────────────────────────────────────────────────
if ($Limpar) {
    Step "Limpando builds anteriores..."
    Remove-Item -Recurse -Force "$projectWin\dist"  -ErrorAction SilentlyContinue
    Remove-Item -Recurse -Force "$projectWin\build" -ErrorAction SilentlyContinue
    Write-Host "   Pasta dist\ e build\ removidas."
}

# ── Instalar PyInstaller ───────────────────────────────────────────────────────
Step "Instalando PyInstaller..."
MSYS2 "pip install pyinstaller pyinstaller-hooks-contrib --break-system-packages --quiet"

# ── Build ──────────────────────────────────────────────────────────────────────
Step "Compilando Pop-Spot... (1-3 minutos)"

$typelibSrc = "/c/msys64/mingw64/lib/girepository-1.0"

MSYS2 @"
pyinstaller main.py \
  --name PopSpot \
  --windowed \
  --onedir \
  --noconfirm \
  --runtime-hook _gi_hook.py \
  --collect-all gi \
  --hidden-import gi.repository.Gtk \
  --hidden-import gi.repository.Gdk \
  --hidden-import gi.repository.GLib \
  --hidden-import gi.repository.GObject \
  --hidden-import gi.repository.Pango \
  --hidden-import gi.repository.GdkPixbuf \
  --hidden-import cairo \
  --hidden-import requests \
  --hidden-import numpy \
  --hidden-import soundcard \
  --add-data '${typelibSrc}:girepository-1.0'
"@

# ── Copiar arquivos de config ──────────────────────────────────────────────────
Step "Copiando arquivos de configuracao..."
Copy-Item -Path "$projectWin\config" -Destination "$projectWin\dist\PopSpot\config" -Recurse -Force

# ── Resultado ─────────────────────────────────────────────────────────────────
$distPath = "$projectWin\dist\PopSpot"
$sizeMB   = [math]::Round((Get-ChildItem $distPath -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB, 0)

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host " Build concluido!  ($sizeMB MB)" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host " Executavel: dist\PopSpot\PopSpot.exe"
Write-Host ""
Write-Host " Para distribuir:" -ForegroundColor Yellow
Write-Host "   1. Compacte a pasta dist\PopSpot\ em um .zip"
Write-Host "   2. Envie o .zip para o amigo"
Write-Host "   3. O amigo extrai e da duplo clique em PopSpot.exe"
Write-Host ""
Write-Host " Para testar agora: abra dist\PopSpot\PopSpot.exe" -ForegroundColor Cyan
Write-Host ""
Read-Host "Pressione Enter para fechar"
