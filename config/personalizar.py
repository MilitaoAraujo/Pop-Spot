# Personalizações do widget — tudo que você pode querer mudar está aqui
# Widget personalizations — everything you may want to change is here

# --------------------------------------------------------------------
# Localização / Location
# --------------------------------------------------------------------

# Cidade para o clima.
#   - Preenchida: usada como está (ex: "Campina Grande", "-7.23,-35.88").
#   - Vazia (""): detecção automática —
#       1. ip-api.com fornece lat/lon pela localização do IP
#       2. Nominatim (OpenStreetMap) refina o nome da cidade pelas coordenadas
#       3. lat/lon são passados ao wttr.in para maior precisão de previsão
#
# City for weather.
#   - Set: used as-is (e.g. "Campina Grande" or "-7.23,-35.88").
#   - Empty (""): auto-detection via ip-api.com (lat/lon) + Nominatim (city name).
CIDADE = "Campina Grande"

# --------------------------------------------------------------------
# Textos do Spotify / Spotify texts
# --------------------------------------------------------------------

# Ícone ao lado do cabeçalho do Spotify / Icon next to the Spotify header
ICONE_SPOTIFY        = "♫"

# Cabeçalho quando uma música está tocando / Header when a song is playing
TEXTO_TOCANDO        = "TOCANDO"

# Cabeçalho quando uma música está pausada / Header when a song is paused
TEXTO_PAUSADO        = "PAUSADO"

# Prefixo antes do título quando pausado / Prefix before the title when paused
PREFIXO_PAUSADO      = "⏸  "

# Mensagem quando o Spotify não está aberto / Message when Spotify is not running
TEXTO_SEM_SPOTIFY    = "Spotify não está rodando"

# Botões MPRIS (faixa anterior, reproduzir/pausar, próxima faixa)
# MPRIS control buttons (previous, play/pause, next)
ICONE_SPOTIFY_ANTERIOR = "⏮"
ICONE_SPOTIFY_PROXIMO  = "⏭"
# Rótulo do botão central conforme o estado / Center button label by state
ICONE_SPOTIFY_REPRODUZIR = "▶"
ICONE_SPOTIFY_PAUSAR     = "⏸"

# Dicas ao passar o mouse / Tooltips
TOOLTIP_SPOTIFY_ANTERIOR = "Faixa anterior"
TOOLTIP_SPOTIFY_PLAY     = "Reproduzir"
TOOLTIP_SPOTIFY_PAUSE    = "Pausar"
TOOLTIP_SPOTIFY_PROXIMO  = "Próxima faixa"

# --------------------------------------------------------------------
# Textos do clima / Weather texts
# --------------------------------------------------------------------

# Ícone padrão enquanto o clima carrega / Default icon while weather loads
ICONE_CLIMA_PADRAO   = "☀"

# Mensagem enquanto busca o clima / Message while fetching weather
TEXTO_BUSCANDO_CLIMA = "Buscando clima…"

# Mensagem quando não há conexão / Message when there is no internet connection
TEXTO_SEM_CONEXAO    = "Sem conexão"

# Formato da linha de vento e umidade
# Wind and humidity line format
# {vento} → speed in m/s    {umidade} → percentage
FORMATO_VENTO_UMIDADE = "Vento {vento} m/s  ·  Umidade {umidade}%"

# Unidade de temperatura exibida / Temperature unit displayed
UNIDADE_TEMPERATURA  = "°C"

# --------------------------------------------------------------------
# Progresso do dia / Day progress
# --------------------------------------------------------------------

# Rótulo exibido acima da barra de progresso do dia.
# Deixe vazio ("") para ocultar o rótulo.
# Label shown above the day progress bar. Set to "" to hide it.
TEXTO_PROGRESSO_DIA = "Progresso do dia"

# --------------------------------------------------------------------
# Calendário / Calendar
# --------------------------------------------------------------------

# Abreviações dos dias da semana (Seg → Dom) / Weekday abbreviations (Mon → Sun)
DIAS_SEMANA = ["Sg", "Te", "Qa", "Qi", "Sx", "Sb", "Do"]
