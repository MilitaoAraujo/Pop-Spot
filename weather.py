# Busca e processa dados do clima via wttr.in (sem chave de API)
# Fetches and parses weather data from wttr.in (no API key required)
import logging
import requests
from config import CIDADE

log = logging.getLogger("widget.weather")

# Mapeamento de código wttr.in para emoji / wttr.in weather code to emoji mapping
ICONES = {
    113: "☀",  116: "⛅", 119: "☁",  122: "☁",
    143: "🌫", 176: "🌦", 185: "🌨", 200: "⛈",
    227: "❄",  230: "❄",  248: "🌫", 260: "🌫",
    263: "🌦", 266: "🌦", 281: "🌨", 284: "🌨",
    293: "🌦", 296: "🌦", 299: "🌧", 302: "🌧",
    305: "🌧", 308: "🌧", 311: "🌨", 314: "🌨",
    317: "🌨", 320: "🌨", 323: "🌨", 326: "🌨",
    329: "❄",  332: "❄",  335: "❄",  338: "❄",
    350: "🌨", 353: "🌦", 356: "🌧", 359: "🌧",
    362: "🌨", 365: "🌨", 368: "🌨", 371: "❄",
    374: "🌨", 377: "🌨", 386: "⛈", 389: "⛈",
    392: "⛈", 395: "⛈",
}

# Cache da localização detectada automaticamente.
# None           → ainda não tentou (ou falhou — vai tentar de novo)
# {"lat", "lon", "cidade"} → detectado com sucesso, reutiliza
_loc_cache: dict | None = None


def _coords_geoclue() -> tuple[float, float] | None:
    """Tenta obter lat/lon via GeoClue2 (D-Bus, sistema).
    Mais preciso que IP — usa Wi-Fi para triangulação quando disponível.
    Requer: sudo apt install geoclue-2.0
    Retorna (lat, lon) ou None se GeoClue2 não estiver disponível."""
    try:
        import dbus, time  # noqa: F401
        bus  = dbus.SystemBus()
        mgr  = dbus.Interface(
            bus.get_object("org.freedesktop.GeoClue2", "/org/freedesktop/GeoClue2/Manager"),
            "org.freedesktop.GeoClue2.Manager",
        )
        cli_path = str(mgr.GetClient())
        cli_obj  = bus.get_object("org.freedesktop.GeoClue2", cli_path)
        cli_if   = dbus.Interface(cli_obj, "org.freedesktop.GeoClue2.Client")
        cli_prop = dbus.Interface(cli_obj, "org.freedesktop.DBus.Properties")
        cli_prop.Set("org.freedesktop.GeoClue2.Client", "DesktopId", "desktop-widget")
        cli_if.Start()
        for _ in range(30):   # até 3 s
            time.sleep(0.1)
            loc_path = str(cli_prop.Get("org.freedesktop.GeoClue2.Client", "Location"))
            if loc_path not in ("", "/"):
                lp = dbus.Interface(
                    bus.get_object("org.freedesktop.GeoClue2", loc_path),
                    "org.freedesktop.DBus.Properties",
                )
                lat = float(lp.Get("org.freedesktop.GeoClue2.Location", "Latitude"))
                lon = float(lp.Get("org.freedesktop.GeoClue2.Location", "Longitude"))
                cli_if.Stop()
                return lat, lon
        cli_if.Stop()
    except Exception as e:
        log.debug("GeoClue2 não disponível: %s", e)
    return None


def _detectar_localizacao() -> dict | None:
    """Detecta localização com múltiplas fontes (melhor precisão primeiro).

    Prioridade:
      1. GeoClue2 (Wi-Fi triangulation) — mais preciso, requer geoclue-2.0
      2. ip-api.com                     — localização por IP
      Em ambos os casos, Nominatim (OpenStreetMap) refina o nome da cidade.

    Retorna dict com 'lat', 'lon' e 'cidade', ou None se tudo falhar."""
    global _loc_cache
    if _loc_cache is not None:
        return _loc_cache

    lat = lon = cidade = None

    # Fonte 1: GeoClue2 (mais preciso)
    gc = _coords_geoclue()
    if gc:
        lat, lon = gc
        log.debug("coordenadas via GeoClue2: %.4f, %.4f", lat, lon)
    else:
        # Fonte 2: ip-api.com
        try:
            r = requests.get(
                "http://ip-api.com/json/?fields=lat,lon,city",
                timeout=5,
            )
            r.raise_for_status()
            d      = r.json()
            lat    = d["lat"]
            lon    = d["lon"]
            cidade = d.get("city", "")
        except Exception as e:
            log.warning("ip-api.com falhou: %s", e)
            return None  # não cacheia; tenta de novo na próxima atualização

    # Nominatim para nome de cidade mais preciso que o retornado pelo IP
    try:
        r2 = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"lat": lat, "lon": lon, "format": "json", "zoom": 10},
            headers={"User-Agent": "desktop-widget/1.0 (github.com/widget)"},
            timeout=5,
        )
        r2.raise_for_status()
        addr   = r2.json().get("address", {})
        cidade = (
            addr.get("city")
            or addr.get("town")
            or addr.get("village")
            or addr.get("county")
            or cidade
        )
    except Exception as e:
        log.warning("Nominatim falhou (usando cidade detectada): %s", e)

    _loc_cache = {"lat": lat, "lon": lon, "cidade": cidade}
    log.warning("localização detectada: %s (%.4f, %.4f)", cidade, lat, lon)
    return _loc_cache


def buscar() -> dict | None:
    """Retorna dict com dados do clima ou None em caso de erro.

    Prioridade da localização:
      1. CIDADE definida em config/personalizar.py  →  usada como nome E como alvo do wttr.in
      2. Detecção automática (ip-api.com + Nominatim)  →  lat,lon para wttr.in;
         nome da cidade exibido vem do Nominatim (mais preciso que wttr.in)
    """
    try:
        if CIDADE:
            # Cidade configurada manualmente: usa como está
            alvo          = CIDADE
            cidade_exibir = None   # wttr.in retornará o nome correto
        else:
            loc = _detectar_localizacao()
            if loc:
                alvo          = f"{loc['lat']},{loc['lon']}"
                cidade_exibir = loc["cidade"]
            else:
                alvo          = ""   # wttr.in decide pelo IP
                cidade_exibir = None

        url = f"https://wttr.in/{alvo}?format=j1&lang=pt"
        r   = requests.get(url, timeout=10)
        r.raise_for_status()
        d    = r.json()
        cc   = d["current_condition"][0]
        area = d["nearest_area"][0]

        return {
            # Se cidade_exibir está definida (detecção auto), usa ela;
            # caso contrário, usa o que o wttr.in retornou (CIDADE manual)
            "cidade":    cidade_exibir or area["areaName"][0]["value"],
            "temp":      cc["temp_C"],
            "descricao": cc["weatherDesc"][0]["value"],
            "umidade":   cc["humidity"],
            "vento_ms":  round(int(cc["windspeedKmph"]) / 3.6, 1),
            "codigo":    int(cc["weatherCode"]),
        }
    except Exception as e:
        log.warning("erro ao buscar clima: %s", e)
        return None


def icone(codigo: int) -> str:
    """Retorna o emoji correspondente ao código de clima wttr.in."""
    return ICONES.get(codigo, "🌤")
