# Widget de Desktop / Desktop Widget

Um widget de desktop feito em Python com GTK3, exibindo relógio, clima, Spotify e um visualizador de espectro de áudio.

A desktop widget built in Python with GTK3, showing a clock, weather, Spotify info and an audio spectrum visualizer.

> Este projeto foi minha primeira modificação no Linux. Se você está começando também, sinta-se em casa — todo o código foi feito para ser fácil de personalizar.
>
> This project was my first Linux customization. If you're just getting started too, feel free to make it yours — the entire code was built to be easy to customize.

---

## Visual / Preview

Captura do widget no desktop (relógio, progresso do dia, calendário, clima, Spotify e espectro de áudio).

Screenshot of the widget on the desktop (clock, day progress, calendar, weather, Spotify, and audio spectrum).

![Widget no desktop — Pop!_OS / Widget on desktop — Pop!_OS](docs/screenshot.png)

---

## Funcionalidades / Features

- Relógio digital com data / Digital clock with date
- Progresso do dia em porcentagem e barra / Day progress percentage and bar
- Mini calendário do mês atual / Mini calendar of the current month
- Clima em tempo real via wttr.in (sem chave de API) / Real-time weather via wttr.in (no API key)
- Informações do Spotify (música, artista, álbum, capa) / Spotify info (track, artist, album, cover)
- Visualizador de espectro de áudio ao vivo / Live audio spectrum visualizer
- Totalmente personalizável por arquivos de configuração / Fully customizable via config files
- Suporte a Wayland (gtk-layer-shell) e X11 / Wayland (gtk-layer-shell) and X11 support

---

## Requisitos / Requirements

| Pacote / Package | Função / Purpose |
|---|---|
| `python3-gi` | Interface GTK3 |
| `python3-gi-cairo` | Desenho com Cairo / Cairo drawing |
| `python3-dbus` | Integração com Spotify / Spotify integration |
| `python3-requests` | Requisições HTTP (clima) / HTTP requests (weather) |
| `python3-numpy` | Processamento de áudio / Audio processing |
| `gir1.2-gtk-3.0` | Bindings GTK3 |
| `gir1.2-gdkpixbuf-2.0` | Carregamento de imagens / Image loading |
| `pulseaudio-utils` | `parec` para captura de áudio / `parec` for audio capture |
| `gtk-layer-shell` *(opcional)* | Fixa o widget no desktop (Wayland) / Pins widget to desktop (Wayland) |

---

## Instalação / Installation

### Pop!_OS, Ubuntu, Debian e derivados / Pop!_OS, Ubuntu, Debian and derivatives

> Este widget foi desenvolvido e testado no **Pop!_OS**. É o ambiente recomendado.
> This widget was developed and tested on **Pop!_OS**. It is the recommended environment.

```bash
# Clone ou baixe o projeto / Clone or download the project
git clone https://github.com/seu-usuario/widget.git
cd widget

# Instale as dependências automaticamente / Install dependencies automatically
bash install.sh
```

Ou manualmente / Or manually:

```bash
sudo apt install python3-gi python3-gi-cairo python3-dbus python3-requests \
                 python3-numpy gir1.2-gtk-3.0 gir1.2-gdkpixbuf-2.0 \
                 pulseaudio-utils
```

### Fedora / RHEL

```bash
sudo dnf install python3-gobject python3-dbus python3-requests python3-numpy \
                 gtk3 gdk-pixbuf2
# parec via: sudo dnf install pulseaudio-utils
```

### Arch Linux / Manjaro

```bash
sudo pacman -S python-gobject python-dbus python-requests python-numpy \
               gtk3 gdk-pixbuf2 libpulse
```

---

## Como rodar / How to run

```bash
cd ~/Documentos/widget
python3 main.py &
```

Para rodar sem precisar manter o terminal aberto / To run without keeping the terminal open:

```bash
nohup python3 ~/Documentos/widget/main.py &>/dev/null &
```

Para iniciar automaticamente com o sistema / To start automatically with the system:

```bash
bash setup_autostart.sh
```

---

## Compatibilidade com outros sistemas / Compatibility with other systems

### Outras distros Linux / Other Linux distros

O widget funciona em qualquer distro Linux com GTK3 e PulseAudio ou PipeWire. Use o gerenciador de pacotes da sua distro para instalar os requisitos listados acima.

The widget works on any Linux distro with GTK3 and PulseAudio or PipeWire. Use your distro's package manager to install the requirements listed above.

- **Pop!_OS** — ambiente principal de desenvolvimento, funciona perfeitamente / main development environment, works perfectly
- **Arch / Manjaro** — funcional, use `pacman` / works, use `pacman`
- **Fedora / openSUSE** — funcional, use `dnf` / works, use `dnf`
- **NixOS** — possível via `nix-shell`, requer adaptação do `shell.nix` / possible via `nix-shell`, requires a `shell.nix`
- **Gentoo** — funcional compilando as dependências via `emerge` / works by compiling deps via `emerge`

### macOS

Parcialmente compatível. O GTK3 pode ser instalado via Homebrew, mas há limitações:

Partially compatible. GTK3 can be installed via Homebrew, but with limitations:

```bash
brew install gtk+3 pygobject3 py3cairo
pip3 install requests numpy dbus-python
```

- O widget abre como janela normal (sem fixar no desktop) / Widget opens as a normal window (cannot pin to desktop)
- O visualizador de espectro não funciona (`parec` é exclusivo do Linux) / The spectrum visualizer won't work (`parec` is Linux-only)
- A integração com Spotify via D-Bus pode não funcionar / Spotify D-Bus integration may not work
- Temas visuais ficam diferentes dos do Linux / Visual themes look different from Linux

### Windows

Não compatível nativamente. Opções possíveis / Not natively compatible. Possible options:

1. **WSL2 com WSLg** — instale o Ubuntu no WSL2, ative o WSLg (suporte a GUI) e rode normalmente / Install Ubuntu on WSL2, enable WSLg (GUI support) and run normally
2. **VirtualBox / VMware** — rode uma VM Linux e use o widget dentro dela / Run a Linux VM and use the widget inside it

O widget foi projetado para Linux e se aproveita de funcionalidades exclusivas como Wayland Layer Shell e PulseAudio. Uma portabilidade completa para Windows exigiria reescrever o visualizador de áudio e o sistema de janelas.

The widget was designed for Linux and relies on Linux-exclusive features like Wayland Layer Shell and PulseAudio. A full Windows port would require rewriting the audio visualizer and window management system.

---

## Personalização / Customization

Todos os arquivos de configuração estão na pasta `config/`. Você não precisa tocar em nenhum outro arquivo.

All config files are inside the `config/` folder. You don't need to touch any other file.

### `config/personalizar.py` — Nomes e textos / Names and texts

O arquivo principal de personalização. Reúne tudo que você provavelmente vai querer mudar: cidade, textos exibidos, unidade de temperatura e dias da semana no calendário.

The main personalization file. Gathers everything you'll likely want to change: city, displayed texts, temperature unit and calendar weekday names.

```python
CIDADE               = "Campina Grande"  # sua cidade / your city

TEXTO_TOCANDO        = "TOCANDO"         # ou "PLAYING", "NOW PLAYING", etc.
TEXTO_PAUSADO        = "PAUSADO"
TEXTO_SEM_SPOTIFY    = "Spotify não está rodando"
TEXTO_SEM_CONEXAO    = "Sem conexão"

UNIDADE_TEMPERATURA  = "°C"             # mude para "°F" se preferir

DIAS_SEMANA = ["S", "T", "Q", "Q", "S", "S", "D"]  # abreviações do calendário
# Em inglês / In English: ["M", "T", "W", "T", "F", "S", "S"]
```

### `config/colors.py` — Cores / Colors

Mude as 3 cores base do widget. Todas as outras cores são derivadas automaticamente.

Change the 3 base widget colors. All other colors are derived automatically.

```python
COR_BASE     = "#0c0c12"   # fundo escuro / dark background
COR_TEXTO    = "#e0e0e0"   # texto claro / light text
COR_DESTAQUE = "#9b59b6"   # destaque / accent (títulos, barra, hoje no calendário)
```

Exemplos de temas / Theme examples:

```python
# Tema azul / Blue theme
COR_BASE     = "#0a0e1a"
COR_TEXTO    = "#dce8ff"
COR_DESTAQUE = "#5b9bd5"

# Tema verde / Green theme
COR_BASE     = "#0a1a0e"
COR_TEXTO    = "#d8f0dc"
COR_DESTAQUE = "#4caf76"

# Tema neutro / Neutral theme
COR_BASE     = "#111111"
COR_TEXTO    = "#dddddd"
COR_DESTAQUE = "#888888"
```

### `config/layout.py` — Tamanho e posição / Size and position

```python
LARGURA            = 270   # largura do widget / widget width
MARGEM_DIREITA     = 24    # distância da borda direita / distance from right edge
MARGEM_TOPO        = 24    # distância do topo / distance from top
TAMANHO_CAPA       = 170   # tamanho da capa do álbum / album cover size
TAMANHO_FONTE_HORA = 68    # tamanho da fonte do relógio / clock font size
```

### `config/general.py` — Intervalos / Intervals

```python
ATUALIZAR_CLIMA_SEG   = 600  # intervalo do clima em segundos / weather interval in seconds
ATUALIZAR_SPOTIFY_SEG = 3    # intervalo do Spotify em segundos / Spotify interval in seconds
```

---

## Estrutura do projeto / Project structure

```
widget/
├── main.py              # ponto de entrada / entry point
├── window.py            # janela e layout principal / main window and layout
├── css.py               # estilos GTK gerados dinamicamente / dynamically generated GTK styles
├── spectrum.py          # visualizador de espectro de áudio / audio spectrum visualizer
├── weather.py           # integração com clima / weather integration
├── spotify.py           # integração com Spotify / Spotify integration
├── install.sh           # instalação de dependências / dependency installer
├── setup_autostart.sh   # configura inicialização automática / sets up autostart
└── config/
    ├── personalizar.py  # cidade, textos, unidade, dias da semana / city, texts, unit, weekdays
    ├── colors.py        # cores / colors
    ├── layout.py        # tamanho e posição / size and position
    └── general.py       # intervalos de atualização / update intervals
```
