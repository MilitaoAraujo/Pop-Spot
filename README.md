# Pop Spot

**A desktop widget for Pop!_OS and Windows** / **Um widget de desktop para o Pop!_OS e o Windows**

Python + **PySide6**. Clock, weather, Spotify and a live audio spectrum. Same UI on both systems. On **Pop!_OS / COSMIC** the Qt window is hosted in GTK + layer-shell so it stays on the desktop (not in the dock). On **Windows** it is a native frameless tool window. Version **0.1.0**.

![Pop Spot on the desktop](docs/screenshot.png)

![Settings](docs/screenshot-settings.png)

---

## English

A floating desktop widget: time, calendar, weather (3-day forecast), Spotify controls and an audio visualizer. Drag it, theme it, hide blocks you don’t need. Settings apply without restarting.

### Specs

| | **Pop!_OS** | **Windows** |
|---|---|---|
| UI | PySide6 | PySide6 |
| Desktop chrome | GTK layer-shell host | Native tool window (no taskbar) |
| Spotify | MPRIS (D-Bus) | SMTC + session volume (`pycaw`) |
| Spectrum | Pulse/`parec` | WASAPI loopback (`sounddevice`) |
| Wallpaper colors | COSMIC / GNOME | Desktop wallpaper API |
| Rain alert | `notify-send` | Balloon / toast |
| Autostart | systemd user (`install.sh`) | Startup folder (`install_windows.ps1`) |
| Entry point | `main.py` | `main.py` |

Also: auto location, city autocomplete, local weather cache, hide calendar / Spotify / spectrum / forecast, English / Português, match-wallpaper themes.

### Install on Pop!_OS

Needs **Pop!_OS / Ubuntu / Debian**, Python 3, and (recommended) gtk-layer-shell.

```bash
git clone https://github.com/MilitaoAraujo/Pop-Spot.git
cd Pop-Spot
bash install.sh
```

`install.sh` installs the system packages below, creates `.venv` with PySide6, and enables login autostart.

Run by hand: `bash launch_desktop_widget.sh`

Stop autostart (does **not** delete the folder): `bash uninstall.sh`

Logs: `journalctl --user -u desktop-widget.service -f`

| Package | Role |
|---|---|
| `python3-gi` / `python3-gi-cairo` | GTK3 host (layer-shell) |
| `gir1.2-gtk-3.0` / `gir1.2-gdkpixbuf-2.0` | GTK bindings |
| `gir1.2-gtklayershell-0.1` + `libgtk-layer-shell0` | Stay on the desktop (Wayland) |
| `python3-dbus` | Spotify MPRIS / GeoClue |
| `python3-pip` / `python3-venv` | `.venv` + PySide6 |
| `pulseaudio-utils` | `parec` (spectrum) |
| `python3-requests` / `python3-numpy` | HTTP + FFT (also in the venv) |
| `geoclue-2.0` *(optional)* | More accurate location |
| **PySide6** (venv, via `requirements.txt`) | Widget UI |

Without layer-shell the launcher falls back to X11 (may show in the taskbar).

### Install on Windows

Needs **Python 3.10+** with **Add python.exe to PATH**. Spotify desktop app for media controls.

```powershell
git clone https://github.com/MilitaoAraujo/Pop-Spot.git
cd Pop-Spot
powershell -ExecutionPolicy Bypass -File install_windows.ps1
```

Creates `.venv`, installs `requirements-windows.txt`, starts the widget and adds it to **Startup**.

Run by hand: `.\launch_windows.ps1`

Remove autostart (does **not** delete the folder): `.\uninstall_windows.ps1`

In settings: **Open when Windows starts**. Spectrum needs audio on the default output device; volume needs Spotify actually playing.

| Package (`requirements-windows.txt`) | Role |
|---|---|
| `PySide6` | Widget UI |
| `requests` / `numpy` | Weather + FFT |
| `sounddevice` | WASAPI loopback (spectrum) |
| `pycaw` / `comtypes` | Spotify volume |
| `winrt-runtime` + `winrt-Windows.Media.Control` (+ Storage / Streams) | SMTC (track, cover, play/pause) |

### Customize

Everything lives in `config/`. The gear UI writes the same files and applies live.

**Language** — settings → Português / English (`IDIOMA` in `config/personalizar.py`).

```python
# config/personalizar.py
CIDADE = ""                 # empty = auto; or "Recife", "-7.23,-35.88"
IDIOMA = "en"               # "pt" or "en"
MOSTRAR_CALENDARIO = True
MOSTRAR_SPOTIFY = True
MOSTRAR_ESPECTRO = True
MOSTRAR_PREVISAO = True
UNIDADE_TEMPERATURA = "°C"  # or "°F"
```

```python
# config/colors.py
COR_BASE = "#0c0c12"
COR_TEXTO = "#e0e0e0"
COR_DESTAQUE = "#9b59b6"
OPACIDADE_FUNDO = 0.92
```

Quick themes in settings: Purple, Blue, Mono, Green. **Match wallpaper** uses the current desktop background.

```python
# config/layout.py
LADO = "direita"   # or "esquerda"
ESCALA = 1.00      # 0.80–1.30 (also: settings → widget size)
```

Drag position: `config/.widget_pos` (right-click → Reset position).

### COSMIC / Wayland

The launcher uses **layer-shell** so the Qt widget stays off the taskbar. Layer `BOTTOM` + `exclusive_zone=-1` keeps a normal desktop cursor. Right-click: Settings, Reload weather, Reset position, Quit.

---

## Português

Widget flutuante na área de trabalho: hora, calendário, clima (previsão de 3 dias), controles do Spotify e espectro de áudio. Arraste, troque o tema, esconda blocos. As configs aplicam **sem reiniciar**.

### Specs

| | **Pop!_OS** | **Windows** |
|---|---|---|
| Interface | PySide6 | PySide6 |
| Mesa | Host GTK + layer-shell | Janela tool nativa (sem taskbar) |
| Spotify | MPRIS (D-Bus) | SMTC + volume da sessão (`pycaw`) |
| Espectro | Pulse/`parec` | WASAPI loopback (`sounddevice`) |
| Cores do wallpaper | COSMIC / GNOME | API do papel de parede |
| Aviso de chuva | `notify-send` | Balloon / toast |
| Autostart | systemd (`install.sh`) | Pasta Inicializar (`install_windows.ps1`) |
| Entrada | `main.py` | `main.py` |

Também: localização automática, autocomplete de cidade, cache do clima, blocos ocultáveis, Português / English, adaptar ao wallpaper.

### Instalar no Pop!_OS

**Pop!_OS / Ubuntu / Debian**, Python 3, e (recomendado) gtk-layer-shell.

```bash
git clone https://github.com/MilitaoAraujo/Pop-Spot.git
cd Pop-Spot
bash install.sh
```

O `install.sh` instala os pacotes abaixo, cria `.venv` com PySide6 e liga o widget no login.

Na mão: `bash launch_desktop_widget.sh`

Tirar o autostart (**não** apaga a pasta): `bash uninstall.sh`

Logs: `journalctl --user -u desktop-widget.service -f`

| Pacote | Função |
|---|---|
| `python3-gi` / `python3-gi-cairo` | Host GTK3 (layer-shell) |
| `gir1.2-gtk-3.0` / `gir1.2-gdkpixbuf-2.0` | Bindings GTK |
| `gir1.2-gtklayershell-0.1` + `libgtk-layer-shell0` | Prender na mesa (Wayland) |
| `python3-dbus` | Spotify MPRIS / GeoClue |
| `python3-pip` / `python3-venv` | `.venv` + PySide6 |
| `pulseaudio-utils` | `parec` (espectro) |
| `python3-requests` / `python3-numpy` | HTTP + FFT (também no venv) |
| `geoclue-2.0` *(opcional)* | Localização mais precisa |
| **PySide6** (venv, `requirements.txt`) | Interface do widget |

Sem layer-shell o launcher cai no X11 (pode aparecer na taskbar).

### Instalar no Windows

**Python 3.10+** com **Add python.exe to PATH**. App desktop do Spotify para os controles.

```powershell
git clone https://github.com/MilitaoAraujo/Pop-Spot.git
cd Pop-Spot
powershell -ExecutionPolicy Bypass -File install_windows.ps1
```

Cria `.venv`, instala `requirements-windows.txt`, abre o widget e coloca na pasta **Inicializar**.

Na mão: `.\launch_windows.ps1`

Tirar o autostart (**não** apaga a pasta): `.\uninstall_windows.ps1`

Nas configurações: **Abrir ao iniciar o Windows**. O espectro precisa de som no dispositivo padrão; o volume, do Spotify tocando.

| Pacote (`requirements-windows.txt`) | Função |
|---|---|
| `PySide6` | Interface |
| `requests` / `numpy` | Clima + FFT |
| `sounddevice` | WASAPI (espectro) |
| `pycaw` / `comtypes` | Volume do Spotify |
| `winrt-runtime` + `winrt-Windows.Media.Control` (+ Storage / Streams) | SMTC (faixa, capa, play/pause) |

### Personalização

Tudo em `config/`. A engrenagem grava os mesmos arquivos e aplica na hora.

**Idioma** — configurações → Português / English (`IDIOMA` em `config/personalizar.py`).

```python
# config/personalizar.py
CIDADE = ""                 # vazia = automático; ou "Recife", "-7.23,-35.88"
IDIOMA = "pt"               # "pt" ou "en"
MOSTRAR_CALENDARIO = True
MOSTRAR_SPOTIFY = True
MOSTRAR_ESPECTRO = True
MOSTRAR_PREVISAO = True
UNIDADE_TEMPERATURA = "°C"  # ou "°F"
```

Temas rápidos: Roxo, Azul, Mono, Verde. **Adaptar ao wallpaper** usa o fundo de tela atual.

Lado e tamanho: `config/layout.py` (`LADO`, `ESCALA` 0.80–1.30). Posição ao arrastar: `config/.widget_pos`.

### COSMIC / Wayland

O launcher usa **layer-shell** para a UI Qt ficar na mesa (some da taskbar). Camada `BOTTOM` + `exclusive_zone=-1` evita o cursor de “mãozinha”. Menu do botão direito: Configurações, Recarregar clima, Resetar posição, Sair.

---

## Layout

```
Pop-Spot/
├── main.py                     # entrada única (Linux e Windows)
├── window.py                   # UI GTK (fallback: POPSPOT_GTK=1)
├── install.sh / uninstall.sh / setup_autostart.sh / launch_desktop_widget.sh
├── install_windows.ps1 / uninstall_windows.ps1 / launch_windows.ps1
├── requirements.txt            # Linux (PySide6, requests, numpy)
├── requirements-windows.txt    # Windows (+ sounddevice, pycaw, winrt)
├── win/                        # UI Qt (oficial nos dois)
├── weather.py / spotify.py / spectrum.py / wallpaper_theme.py
├── docs/screenshot.png
├── docs/screenshot-settings.png
└── config/                     # cidade, idioma, cores, layout
```

## License / Licença

MIT
