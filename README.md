# Widget de Desktop / Desktop Widget

Um widget de desktop em Python + GTK3: relógio, clima, Spotify e espectro de áudio.

> Feito para ser fácil de personalizar — especialmente no **Pop!_OS / COSMIC**.

## Visual

![Widget no desktop — Pop!_OS](docs/screenshot.png)

## Funcionalidades

- Relógio, progresso do dia e mini calendário
- Clima (wttr.in, com fallback Open-Meteo) + previsão de 3 dias + cache local
- Localização automática, cidade manual com **autocomplete** e aviso de chuva forte
- Spotify (MPRIS): capa, controles e **volume**; clique na capa abre o app
- Espectro de áudio ao vivo
- Arrastar para reposicionar (posição salva)
- Tela de configurações (engrenagem): cores, opacidade, temas, blocos, cidade
- Menu do botão direito: Configurações, Recarregar clima, Resetar posição, Sair
- Blocos ocultáveis (calendário, Spotify, espectro, previsão)
- Configuração aplicada **sem reiniciar** o processo
- Wayland (gtk-layer-shell) e fallback X11

## Requisitos

| Pacote | Função |
|---|---|
| `python3-gi` / `python3-gi-cairo` | GTK3 + Cairo |
| `python3-dbus` | Spotify / GeoClue |
| `python3-requests` / `python3-numpy` | HTTP + FFT |
| `gir1.2-gtk-3.0` / `gir1.2-gdkpixbuf-2.0` | Bindings |
| `pulseaudio-utils` | `parec` (espectro) |
| `gir1.2-gtklayershell-0.1` + `libgtk-layer-shell0` | Wayland (recomendado) |
| `geoclue-2.0` *(opcional)* | Localização mais precisa |

## Instalação (Pop!_OS / Ubuntu / Debian)

```bash
git clone <seu-repo>
cd Pop-Spot
bash install.sh
bash setup_autostart.sh   # inicia no login
```

Rodar agora:

```bash
bash launch_desktop_widget.sh
# ou: python3 main.py &
```

Logs do serviço: `journalctl --user -u desktop-widget.service -f`

## Personalização

Tudo em `config/`. Também dá para editar pela engrenagem do widget (aplica na hora).

### `config/personalizar.py`

```python
CIDADE = ""                 # vazia = automático; ou "Recife", "-7.23,-35.88"
MOSTRAR_CALENDARIO = True
MOSTRAR_SPOTIFY = True
MOSTRAR_ESPECTRO = True
MOSTRAR_PREVISAO = True
UNIDADE_TEMPERATURA = "°C"  # ou "°F"
```

### `config/colors.py`

```python
COR_BASE = "#0c0c12"
COR_TEXTO = "#e0e0e0"
COR_DESTAQUE = "#9b59b6"
OPACIDADE_FUNDO = 1.00
```

Temas rápidos na tela de configs: Roxo, Azul, Mono, Verde.
Também dá para **Adaptar ao wallpaper** (cores dominantes do fundo no COSMIC).

### `config/layout.py`

```python
LARGURA = 270
LADO = "direita"          # ou "esquerda"
MARGEM_DIREITA = 24
TAMANHO_CAPA = 170
TAMANHO_FONTE_HORA = 68
ESCALA = 1.00             # 0.80–1.30 (também na engrenagem: Tamanho do widget)
```

Posição ao arrastar: `config/.widget_pos` (reset pelo menu).

### `config/general.py`

```python
ATUALIZAR_CLIMA_SEG = 600
ATUALIZAR_SPOTIFY_SEG = 3
```

## Estrutura

```
Pop-Spot/
├── main.py
├── window.py              # UI + janela
├── css.py                 # estilos gerados
├── weather.py / weather_icons.py
├── spotify.py / spectrum.py
├── launch_desktop_widget.sh
├── setup_autostart.sh / install.sh
└── config/
    ├── personalizar.py
    ├── colors.py / themes.py
    ├── layout.py / general.py
    └── .widget_pos        # gerado ao arrastar
```

## Dicas COSMIC / Wayland

O launcher usa **layer-shell** no Wayland (some da taskbar, sem borda SSD). Camada `BOTTOM` + `exclusive_zone=-1` evita o cursor “mãozinha” na mesa. Sem layer-shell, cai no X11.

## Licença

MIT
