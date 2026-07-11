# Instalador do Pop-Spot para Windows
# Instala MSYS2, Python, GTK3, PyGObject e todas as dependencias automaticamente.
#
# Como usar:
#   Clique com botao direito > "Executar com PowerShell"
#   (nao precisa de administrador)

$ErrorActionPreference = "Stop"
$msys2Root  = "C:\msys64"
$bash       = "$msys2Root\usr\bin\bash.exe"
$python     = "$msys2Root\mingw64\bin\python.exe"

function Step($msg) {
    Write-Host ""
    Write-Host "==> $msg" -ForegroundColor Cyan
}

# ── 1. Instalar MSYS2 (se ainda nao estiver) ──────────────────────────────────
if (Test-Path $bash) {
    Write-Host "MSYS2 ja esta instalado em $msys2Root." -ForegroundColor Green
} else {
    Step "Instalando MSYS2 via winget..."
    winget install --id MSYS2.MSYS2 --location $msys2Root --accept-source-agreements --accept-package-agreements
    if (-not (Test-Path $bash)) {
        Write-Host "Erro: MSYS2 nao foi instalado. Tente instalar manualmente em https://www.msys2.org/" -ForegroundColor Red
        Read-Host "Pressione Enter para fechar"
        exit 1
    }
    Write-Host "MSYS2 instalado!" -ForegroundColor Green
}

# ── Funcao auxiliar: rodar comando dentro do MSYS2 MinGW64 ────────────────────
function MSYS2($cmd) {
    & $bash --login -c "export MSYSTEM=MINGW64; source /etc/profile; $cmd"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Erro ao executar: $cmd" -ForegroundColor Red
        Read-Host "Pressione Enter para fechar"
        exit 1
    }
}

# ── 2. Atualizar repositorios do pacman ───────────────────────────────────────
Step "Atualizando repositorios do MSYS2..."
MSYS2 "pacman -Sy --noconfirm"

# ── 3. Instalar Python + GTK3 + PyGObject + dependencias ─────────────────────
Step "Instalando Python, GTK3 e PyGObject..."
$pkgs = @(
    "mingw-w64-x86_64-python",
    "mingw-w64-x86_64-python-gobject",
    "mingw-w64-x86_64-gtk3",
    "mingw-w64-x86_64-python-requests",
    "mingw-w64-x86_64-python-numpy",
    "mingw-w64-x86_64-python-pip",
    "mingw-w64-x86_64-python-cffi",
    "mingw-w64-x86_64-gcc",
    "mingw-w64-x86_64-cmake",
    "mingw-w64-x86_64-ninja"
) -join " "
MSYS2 "pacman -S --noconfirm $pkgs"

# ── 4. Instalar sounddevice (espectro de audio) ───────────────────────────────
Step "Instalando sounddevice (espectro de audio)..."
# Tenta via pacman primeiro; se nao existir, usa pip com --break-system-packages
$sdResult = & $bash --login -c "export MSYSTEM=MINGW64; source /etc/profile; pacman -S --noconfirm mingw-w64-x86_64-python-sounddevice 2>&1"
if ($LASTEXITCODE -ne 0) {
    MSYS2 "pip install sounddevice --break-system-packages"
}

# ── 5. Teste rapido ───────────────────────────────────────────────────────────
Step "Verificando instalacao..."
@"
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
print('GTK OK - versao:', Gtk._version)
"@ | Out-File -FilePath "$PSScriptRoot\_teste_gtk.py" -Encoding utf8
MSYS2 "python _teste_gtk.py; rm -f _teste_gtk.py"

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host " Instalacao concluida com sucesso!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "Para abrir o widget: duplo clique em iniciar.vbs"
Write-Host ""
Write-Host "Para iniciar automaticamente com o Windows:"
Write-Host "  clique com botao direito em autostart_windows.ps1"
Write-Host "  > 'Executar com PowerShell'"
Write-Host ""
Read-Host "Pressione Enter para fechar"
