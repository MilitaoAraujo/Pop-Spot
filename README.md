# Pop Spot

**A desktop widget for Pop!_OS** / **Um widget de desktop para o Pop!_OS**

Python + GTK3. Clock, weather, Spotify and a live audio spectrum — built for **Pop!_OS / COSMIC**, with Wayland layer-shell (and an X11 fallback).

![Pop Spot on the desktop](docs/screenshot.png)

![Settings](docs/screenshot-settings.png)

---

## English

A floating desktop widget: time, calendar, weather (with 3-day forecast), Spotify controls and an audio visualizer. Drag it, theme it, hide blocks you don’t need. Changes in settings apply without restarting.

### Features

- Clock, day progress and mini calendar
- Weather (wttr.in, Open-Meteo fallback) + 3-day forecast + local cache
- Auto location, city autocomplete and heavy-rain notification
- Spotify (MPRIS): cover, controls, volume — click the cover to open the app
- Live audio spectrum
- Drag to reposition (saved); right-click to reset
- Settings (gear): language **English / Português**, colors, opacity, size, themes, city, visible blocks
- Match colors to the COSMIC wallpaper
- Hide calendar, Spotify, spectrum or forecast
- Wayland (gtk-layer-shell) so it stays off the taskbar; X11 fallback

### Requirements (Pop!_OS / Ubuntu / Debian)

| Package | Role |
|---|---|
| `python3-gi` / `python3-gi-cairo` | GTK3 + Cairo |
| `python3-dbus` | Spotify / GeoClue |
| `python3-requests` / `python3-numpy` | HTTP + FFT |
| `gir1.2-gtk-3.0` / `gir1.2-gdkpixbuf-2.0` | Bindings |
| `pulseaudio-utils` | `parec` (spectrum) |
| `gir1.2-gtklayershell-0.1` + `libgtk-layer-shell0` | Wayland (recommended) |
| `geoclue-2.0` *(optional)* | More accurate location |

### Install

```bash
git clone https://github.com/MilitaoAraujo/Pop-Spot.git
cd Pop-Spot
bash install.sh
bash setup_autostart.sh   # start on login
```

Run now:

```bash
bash launch_desktop_widget.sh
```

Logs: `journalctl --user -u desktop-widget.service -f`

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

Quick themes in settings: Purple, Blue, Mono, Green. **Match wallpaper** pulls dominant colors from the COSMIC background.

```python
# config/layout.py
LADO = "direita"   # or "esquerda"
ESCALA = 1.00      # 0.80–1.30 (also: settings → widget size)
```

Drag position is stored in `config/.widget_pos` (right-click → Reset position).

### COSMIC / Wayland

The launcher uses **layer-shell** on Wayland (no taskbar icon, no SSD chrome). Layer `BOTTOM` + `exclusive_zone=-1` keeps a normal desktop cursor. Without layer-shell it falls back to X11.

Right-click: Settings, Reload weather, Reset position, Quit.

---

## Português

Widget flutuante na área de trabalho: hora, calendário, clima (previsão de 3 dias), controles do Spotify e espectro de áudio. Arraste, troque o tema, esconda blocos. As configs aplicam **sem reiniciar**.

### Funcionalidades

- Relógio, progresso do dia e mini calendário
- Clima (wttr.in, fallback Open-Meteo) + previsão de 3 dias + cache local
- Localização automática, autocomplete de cidade e aviso de chuva forte
- Spotify (MPRIS): capa, controles, volume — clique na capa para abrir o app
- Espectro de áudio ao vivo
- Arrastar para reposicionar (posição salva); botão direito para resetar
- Configurações (engrenagem): idioma **Português / English**, cores, opacidade, tamanho, temas, cidade, blocos
- Adaptar cores ao wallpaper do COSMIC
- Blocos ocultáveis (calendário, Spotify, espectro, previsão)
- Wayland (gtk-layer-shell) fora da taskbar; fallback X11

### Requisitos (Pop!_OS / Ubuntu / Debian)

| Pacote | Função |
|---|---|
| `python3-gi` / `python3-gi-cairo` | GTK3 + Cairo |
| `python3-dbus` | Spotify / GeoClue |
| `python3-requests` / `python3-numpy` | HTTP + FFT |
| `gir1.2-gtk-3.0` / `gir1.2-gdkpixbuf-2.0` | Bindings |
| `pulseaudio-utils` | `parec` (espectro) |
| `gir1.2-gtklayershell-0.1` + `libgtk-layer-shell0` | Wayland (recomendado) |
| `geoclue-2.0` *(opcional)* | Localização mais precisa |

### Instalação

```bash
git clone https://github.com/MilitaoAraujo/Pop-Spot.git
cd Pop-Spot
bash install.sh
bash setup_autostart.sh   # inicia no login
```

Rodar agora:

```bash
bash launch_desktop_widget.sh
```

Logs: `journalctl --user -u desktop-widget.service -f`

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

Temas rápidos: Roxo, Azul, Mono, Verde. **Adaptar ao wallpaper** usa as cores do fundo no COSMIC.

Lado e tamanho: `config/layout.py` (`LADO`, `ESCALA` 0.80–1.30). Posição ao arrastar: `config/.widget_pos`.

### COSMIC / Wayland

O launcher usa **layer-shell** no Wayland (some da taskbar, sem borda). Camada `BOTTOM` + `exclusive_zone=-1` evita o cursor de “mãozinha” na área de trabalho. Sem layer-shell, cai no X11.

Menu do botão direito: Configurações, Recarregar clima, Resetar posição, Sair.

---

## Layout

```
Pop-Spot/
├── main.py
├── window.py
├── css.py
├── weather.py / weather_icons.py
├── spotify.py / spectrum.py
├── wallpaper_theme.py
├── launch_desktop_widget.sh
├── setup_autostart.sh / install.sh
├── docs/screenshot.png
├── docs/screenshot-settings.png
└── config/
    ├── personalizar.py    # city, language, blocks
    ├── colors.py / themes.py
    ├── layout.py / general.py
    └── i18n.py
```

## License / Licença

MIT
