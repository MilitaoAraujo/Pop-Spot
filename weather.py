# Clima via wttr.in, com fallback Open-Meteo e detecção de localização
import json
import logging
import subprocess
import sys
import time
from pathlib import Path

import requests

# Nomes dos ícones (o desenho GTK fica em weather_icons — import tardio).
SOL = "sol"
NUVEM = "nuvem"
SOL_NUVEM = "sol_nuvem"
CHUVA = "chuva"
SOL_CHUVA = "sol_chuva"
TEMPESTADE = "tempestade"
NEVE = "neve"
NEBLINA = "neblina"

log = logging.getLogger("widget.weather")

_CACHE_ARQ = Path(__file__).parent / "config" / ".weather_cache.json"
_CHUVA_ARQ = Path(__file__).parent / "config" / ".chuva_notify.json"

# Códigos wttr.in de chuva forte / tempestade
_CHUVA_FORTE_CODIGOS = {
    302, 305, 308, 311, 314, 356, 359, 365, 377, 386, 389, 392, 395,
}

_ICONES = {
    113: SOL, 116: SOL_NUVEM, 119: NUVEM, 122: NUVEM, 143: NEBLINA,
    176: SOL_CHUVA, 185: NEVE, 200: TEMPESTADE, 227: NEVE, 230: NEVE,
    248: NEBLINA, 260: NEBLINA, 263: SOL_CHUVA, 266: CHUVA, 281: NEVE,
    284: NEVE, 293: SOL_CHUVA, 296: CHUVA, 299: CHUVA, 302: CHUVA,
    305: CHUVA, 308: CHUVA, 311: NEVE, 314: NEVE, 317: NEVE, 320: NEVE,
    323: NEVE, 326: NEVE, 329: NEVE, 332: NEVE, 335: NEVE, 338: NEVE,
    350: NEVE, 353: SOL_CHUVA, 356: CHUVA, 359: CHUVA, 362: NEVE,
    365: NEVE, 368: NEVE, 371: NEVE, 374: NEVE, 377: NEVE,
    386: TEMPESTADE, 389: TEMPESTADE, 392: TEMPESTADE, 395: TEMPESTADE,
}

# Open-Meteo WMO → mesmo conjunto de ícones
_WMO = {
    0: SOL, 1: SOL_NUVEM, 2: SOL_NUVEM, 3: NUVEM,
    45: NEBLINA, 48: NEBLINA,
    51: SOL_CHUVA, 53: CHUVA, 55: CHUVA,
    61: SOL_CHUVA, 63: CHUVA, 65: CHUVA,
    71: NEVE, 73: NEVE, 75: NEVE, 77: NEVE,
    80: SOL_CHUVA, 81: CHUVA, 82: CHUVA,
    85: NEVE, 86: NEVE,
    95: TEMPESTADE, 96: TEMPESTADE, 99: TEMPESTADE,
}

_DESC_PT = {
    "Clear": "Céu limpo", "Sunny": "Ensolarado",
    "Partly cloudy": "Parcialmente nublado", "Cloudy": "Nublado",
    "Overcast": "Encoberto", "Mist": "Névoa", "Fog": "Neblina",
    "Patchy rain nearby": "Chuva irregular nas redondezas",
    "Patchy rain possible": "Possibilidade de chuva irregular",
    "Light drizzle": "Garoa leve", "Light rain": "Chuva fraca",
    "Moderate rain": "Chuva moderada", "Heavy rain": "Chuva forte",
    "Light rain shower": "Pancadas de chuva fraca",
    "Thundery outbreaks possible": "Possíveis trovoadas",
    "Patchy light rain with thunder": "Chuva fraca com trovoadas",
    "Moderate or heavy rain with thunder": "Chuva com trovoadas",
    "Light snow": "Neve fraca", "Patchy light snow": "Neve fraca irregular",
}

_loc_cache: dict | None = None

# UF → estado (consulta tipo "Campina Grande PB")
_UF_BR = {
    "AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas",
    "BA": "Bahia", "CE": "Ceará", "DF": "Distrito Federal",
    "ES": "Espírito Santo", "GO": "Goiás", "MA": "Maranhão",
    "MT": "Mato Grosso", "MS": "Mato Grosso do Sul", "MG": "Minas Gerais",
    "PA": "Pará", "PB": "Paraíba", "PR": "Paraná", "PE": "Pernambuco",
    "PI": "Piauí", "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte",
    "RS": "Rio Grande do Sul", "RO": "Rondônia", "RR": "Roraima",
    "SC": "Santa Catarina", "SP": "São Paulo", "SE": "Sergipe",
    "TO": "Tocantins",
}


def _lang() -> str:
    try:
        from config.i18n import idioma
        return idioma()
    except Exception:
        return "pt"


def _api_lang() -> str:
    return "en" if _lang() == "en" else "pt"


def tipo_icone(codigo: int) -> str:
    return _ICONES.get(codigo, SOL_NUVEM)


def icone_pixbuf(codigo: int, tamanho: int = 36, cor: str = "#e0e0e0"):
    from weather_icons import renderizar as renderizar_icone
    return renderizar_icone(tipo_icone(codigo), tamanho=tamanho, cor=cor)


def limpar_cache_localizacao():
    global _loc_cache
    _loc_cache = None


def limpar_cache_clima():
    """Apaga cache de previsões (ex.: ao mudar a cidade)."""
    try:
        _CACHE_ARQ.unlink(missing_ok=True)
    except Exception:
        pass


def _ttl_fresco() -> int:
    try:
        from config import ATUALIZAR_CLIMA_SEG
        return max(60, int(ATUALIZAR_CLIMA_SEG) - 30)
    except Exception:
        return 570


def _ttl_max() -> int:
    try:
        from config import CACHE_CLIMA_MAX_SEG
        return max(600, int(CACHE_CLIMA_MAX_SEG))
    except Exception:
        return 6 * 3600


def _ler_cache(chave: str, max_idade: int):
    try:
        blob = json.loads(_CACHE_ARQ.read_text(encoding="utf-8"))
        if blob.get("chave") != chave:
            return None
        if time.time() - float(blob.get("ts", 0)) > max_idade:
            return None
        dados = blob.get("dados")
        return dados if isinstance(dados, dict) else None
    except Exception:
        return None


def _gravar_cache(chave: str, dados: dict):
    try:
        _CACHE_ARQ.parent.mkdir(parents=True, exist_ok=True)
        payload = {"chave": chave, "ts": time.time(), "dados": dados}
        _CACHE_ARQ.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        log.debug("cache clima: %s", e)


def _ler_estado_chuva():
    try:
        return json.loads(_CHUVA_ARQ.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _gravar_estado_chuva(estado: dict):
    try:
        _CHUVA_ARQ.write_text(json.dumps(estado), encoding="utf-8")
    except Exception:
        pass


def _traduzir(desc: str) -> str:
    if not desc:
        return desc
    if _lang() == "en":
        return desc
    low = desc.lower()
    if any(p in low for p in ("chuva", "nublado", "céu", "garoa", "neve", "neblina", "enso")):
        return desc
    return _DESC_PT.get(desc, _DESC_PT.get(desc.title(), desc))


def _coords_geoclue():
    try:
        import dbus, time
        bus = dbus.SystemBus()
        mgr = dbus.Interface(
            bus.get_object("org.freedesktop.GeoClue2", "/org/freedesktop/GeoClue2/Manager"),
            "org.freedesktop.GeoClue2.Manager",
        )
        path = str(mgr.GetClient())
        obj = bus.get_object("org.freedesktop.GeoClue2", path)
        cli = dbus.Interface(obj, "org.freedesktop.GeoClue2.Client")
        prop = dbus.Interface(obj, "org.freedesktop.DBus.Properties")
        prop.Set("org.freedesktop.GeoClue2.Client", "DesktopId", "desktop-widget")
        cli.Start()
        for _ in range(30):
            time.sleep(0.1)
            loc = str(prop.Get("org.freedesktop.GeoClue2.Client", "Location"))
            if loc not in ("", "/"):
                lp = dbus.Interface(
                    bus.get_object("org.freedesktop.GeoClue2", loc),
                    "org.freedesktop.DBus.Properties",
                )
                lat = float(lp.Get("org.freedesktop.GeoClue2.Location", "Latitude"))
                lon = float(lp.Get("org.freedesktop.GeoClue2.Location", "Longitude"))
                cli.Stop()
                return lat, lon
        cli.Stop()
    except Exception as e:
        log.debug("GeoClue2: %s", e)
    return None


def _detectar_localizacao():
    global _loc_cache
    if _loc_cache is not None:
        return _loc_cache

    lat = lon = cidade = None
    gc = _coords_geoclue()
    if gc:
        lat, lon = gc
    else:
        try:
            d = requests.get(
                "http://ip-api.com/json/?fields=lat,lon,city", timeout=5).json()
            lat, lon, cidade = d["lat"], d["lon"], d.get("city", "")
        except Exception as e:
            log.warning("ip-api: %s", e)
            return None

    try:
        addr = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"lat": lat, "lon": lon, "format": "json", "zoom": 10},
            headers={"User-Agent": "desktop-widget/1.0"},
            timeout=5,
        ).json().get("address", {})
        cidade = (
            addr.get("city") or addr.get("town") or addr.get("village")
            or addr.get("county") or cidade
        )
    except Exception as e:
        log.warning("Nominatim: %s", e)

    _loc_cache = {"lat": lat, "lon": lon, "cidade": cidade}
    log.info("localização: %s (%.4f, %.4f)", cidade, lat, lon)
    return _loc_cache


def _partir_consulta(nome: str) -> tuple[str, str | None]:
    """Separa 'Campina Grande PB' / 'Campina Grande, Paraíba' em (cidade, estado)."""
    t = (nome or "").strip()
    if not t:
        return "", None
    if "," in t:
        a, b = t.split(",", 1)
        cidade, extra = a.strip(), b.strip()
    else:
        partes = t.rsplit(None, 1)
        if len(partes) != 2:
            return t, None
        cidade, extra = partes[0].strip(), partes[1].strip()
    if not extra:
        return t, None
    uf = extra.upper()
    if uf in _UF_BR:
        return cidade or t, _UF_BR[uf]
    for estado in _UF_BR.values():
        if extra.casefold() == estado.casefold():
            return cidade or t, estado
    return t, None


def _pontuar_geo(x: dict, nome: str, estado: str | None) -> tuple:
    n = (x.get("name") or "")
    admin = (x.get("admin1") or "")
    pop = int(x.get("population") or 0)
    fc = str(x.get("feature_code") or "")
    score = 0
    if n.casefold() == nome.casefold():
        score += 200
    elif nome.casefold() in n.casefold() or n.casefold() in nome.casefold():
        score += 40
    if estado:
        if admin.casefold() == estado.casefold():
            score += 180
        else:
            score -= 80
    if fc.startswith("PPLA"):
        score += 50
    elif fc == "PPL":
        score += 30
    elif fc == "AIRP":
        score -= 250
    score += min(80, pop // 8000)
    return (score, pop)


def _escolher_geo(results: list, nome: str, estado: str | None):
    if not results:
        return None
    return max(results, key=lambda x: _pontuar_geo(x, nome, estado))


def _resolver_alvo():
    """Retorna (alvo_wttr, cidade_exibir, lat, lon)."""
    from config import CIDADE
    cfg = (CIDADE or "").strip()
    if cfg:
        # coords manuais "lat,lon" (sem espaço de nome de cidade)
        if "," in cfg:
            try:
                a, b = cfg.split(",", 1)
                if a.strip().lstrip("-").replace(".", "", 1).isdigit():
                    return cfg, None, float(a), float(b)
            except ValueError:
                pass
        geo = _geocode_cidade(cfg)
        if geo:
            lat, lon, nome = geo
            return f"{lat},{lon}", nome, lat, lon
        return cfg, cfg, None, None

    loc = _detectar_localizacao()
    if loc:
        return f"{loc['lat']},{loc['lon']}", loc["cidade"], loc["lat"], loc["lon"]
    return "", None, None, None


def _dias_semana_pt(iso_date: str) -> str:
    try:
        import datetime
        from config.i18n import t
        d = datetime.date.fromisoformat(iso_date[:10])
        return t(f"fc_{d.weekday()}")
    except Exception:
        return iso_date[5:10]


def _buscar_wttr(alvo: str, cidade_exibir):
    lang = _api_lang()
    accept = "en-US,en;q=0.9" if lang == "en" else "pt-BR,pt;q=0.9"
    url = (
        f"https://wttr.in/{requests.utils.quote(alvo, safe=',.-')}?format=j1&lang={lang}"
        if alvo else f"https://wttr.in/?format=j1&lang={lang}"
    )
    d = requests.get(
        url, timeout=10,
        headers={"Accept-Language": accept, "User-Agent": "desktop-widget/1.0"},
    ).json()
    cc = d["current_condition"][0]
    area = d["nearest_area"][0]
    previsao = []
    for dia in d.get("weather", [])[:3]:
        previsao.append({
            "dia": _dias_semana_pt(dia.get("date", "")),
            "max_c": int(dia.get("maxtempC", 0)),
            "min_c": int(dia.get("mintempC", 0)),
            "codigo": int(dia.get("hourly", [{}])[4].get("weatherCode", 113)
                          if len(dia.get("hourly", [])) > 4
                          else dia.get("hourly", [{}])[0].get("weatherCode", 113)),
        })
    return {
        "cidade": cidade_exibir or area["areaName"][0]["value"],
        "temp": int(cc["temp_C"]),
        "temp_c": int(cc["temp_C"]),
        "temp_f": int(cc.get("temp_F") or round(int(cc["temp_C"]) * 9 / 5 + 32)),
        "descricao": _traduzir(cc["weatherDesc"][0]["value"]),
        "umidade": cc["humidity"],
        "vento_ms": round(int(cc["windspeedKmph"]) / 3.6, 1),
        "codigo": int(cc["weatherCode"]),
        "previsao": previsao,
        "fonte": "wttr.in",
    }


def _geocode_cidade(nome: str):
    cidade, estado = _partir_consulta(nome)
    q = cidade or nome
    try:
        r = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": q, "count": 10, "language": _api_lang()},
            timeout=8,
        ).json()
        x = _escolher_geo(r.get("results") or [], q, estado)
        if not x:
            return None
        return x["latitude"], x["longitude"], x.get("name") or q
    except Exception as e:
        log.debug("geocode: %s", e)
        return None


def _buscar_open_meteo(lat, lon, cidade_exibir):
    from config.i18n import t
    r = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min",
            "timezone": "auto",
            "forecast_days": 3,
            "wind_speed_unit": "ms",
        },
        timeout=10,
    ).json()
    cur = r["current"]
    daily = r["daily"]
    codigo_wmo = int(cur["weather_code"])
    tipo = _WMO.get(codigo_wmo, SOL_NUVEM)
    # mapeia tipo → um código wttr aproximado para o renderer
    rev = {v: k for k, v in _ICONES.items()}
    codigo = rev.get(tipo, 116)
    previsao = []
    for i in range(min(3, len(daily.get("time", [])))):
        tw = _WMO.get(int(daily["weather_code"][i]), SOL_NUVEM)
        previsao.append({
            "dia": _dias_semana_pt(daily["time"][i]),
            "max_c": int(round(daily["temperature_2m_max"][i])),
            "min_c": int(round(daily["temperature_2m_min"][i])),
            "codigo": rev.get(tw, 116),
        })
    temp_c = int(round(cur["temperature_2m"]))
    return {
        "cidade": cidade_exibir or "—",
        "temp": temp_c,
        "temp_c": temp_c,
        "temp_f": int(round(temp_c * 9 / 5 + 32)),
        "descricao": {
            SOL: t("wx_clear"), SOL_NUVEM: t("wx_partly"), NUVEM: t("wx_cloudy"),
            CHUVA: t("wx_rain"), SOL_CHUVA: t("wx_showers"), TEMPESTADE: t("wx_storm"),
            NEVE: t("wx_snow"), NEBLINA: t("wx_fog"),
        }.get(tipo, "—"),
        "umidade": str(int(round(cur["relative_humidity_2m"]))),
        "vento_ms": round(float(cur["wind_speed_10m"]), 1),
        "codigo": codigo,
        "previsao": previsao,
        "fonte": "open-meteo",
    }


def buscar() -> dict | None:
    from config import CIDADE
    chave = (CIDADE or "").strip() or "__auto__"
    fresco = _ler_cache(chave, max_idade=_ttl_fresco())
    if fresco is not None:
        return fresco

    try:
        alvo, cidade_exibir, lat, lon = _resolver_alvo()
        dados = None
        try:
            dados = _buscar_wttr(alvo, cidade_exibir)
        except Exception as e:
            log.warning("wttr.in falhou (%s) — tentando Open-Meteo", e)

        if dados is None:
            if lat is None and alvo and "," not in alvo:
                geo = _geocode_cidade(alvo)
                if geo:
                    lat, lon, cidade_exibir = geo[0], geo[1], cidade_exibir or geo[2]
            if lat is None:
                loc = _detectar_localizacao()
                if loc:
                    lat, lon = loc["lat"], loc["lon"]
                    cidade_exibir = cidade_exibir or loc["cidade"]
            if lat is not None:
                dados = _buscar_open_meteo(lat, lon, cidade_exibir)

        if dados is not None:
            _gravar_cache(chave, dados)
            return dados
    except Exception as e:
        log.warning("clima: %s", e)

    # Rede falhou: usa cache antigo (até CACHE_CLIMA_MAX_SEG)
    antigo = _ler_cache(chave, max_idade=_ttl_max())
    if antigo is not None:
        antigo = dict(antigo)
        antigo["cache"] = True
        return antigo
    return None


def sugerir_cidades(texto: str, limite: int = 8) -> list[dict]:
    """Autocomplete: [{"rotulo": "Campina Grande, Paraíba, Brasil", "cidade": "Campina Grande"}, ...]"""
    q = (texto or "").strip()
    if len(q) < 2:
        return []
    cidade, estado = _partir_consulta(q)
    busca = cidade or q
    try:
        r = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": busca, "count": max(limite, 10), "language": _api_lang()},
            timeout=6,
        ).json()
        results = list(r.get("results") or [])
        results.sort(key=lambda x: _pontuar_geo(x, busca, estado), reverse=True)
        out = []
        vistos = set()
        for x in results:
            if str(x.get("feature_code") or "") == "AIRP":
                continue
            nome = x.get("name") or busca
            admin = x.get("admin1") or ""
            chave = (nome.casefold(), admin.casefold())
            if chave in vistos:
                continue
            vistos.add(chave)
            partes = [nome]
            if admin:
                partes.append(admin)
            if x.get("country"):
                partes.append(x["country"])
            out.append({"rotulo": ", ".join(partes), "cidade": nome})
            if len(out) >= limite:
                break
        return out
    except Exception as e:
        log.debug("sugerir_cidades: %s", e)
        return []


def eh_chuva_forte(dados: dict | None) -> bool:
    if not dados:
        return False
    codigo = int(dados.get("codigo") or 0)
    if codigo in _CHUVA_FORTE_CODIGOS:
        return True
    desc = (dados.get("descricao") or "").lower()
    return any(
        p in desc
        for p in (
            "chuva forte", "tempestade", "trovoada", "torrencial",
            "heavy rain", "thunder", "storm",
        )
    )


def notificar_chuva_forte(dados: dict) -> bool:
    """Aviso de chuva forte (notify-send no Linux, balloon no Windows)."""
    if not eh_chuva_forte(dados):
        return False
    try:
        from config import NOTIFICAR_CHUVA_FORTE
        if not NOTIFICAR_CHUVA_FORTE:
            return False
    except Exception:
        pass

    estado = _ler_estado_chuva()
    agora = time.time()
    codigo = int(dados.get("codigo") or 0)
    if (
        estado.get("codigo") == codigo
        and agora - float(estado.get("ts", 0)) < 3 * 3600
    ):
        return False

    from config.i18n import t
    cidade = dados.get("cidade") or t("rain_region")
    desc = dados.get("descricao") or t("rain_title")
    titulo, corpo = t("rain_title"), f"{cidade}: {desc}"
    ok = False
    if sys.platform == "win32":
        ok = _notificar_windows(titulo, corpo)
    else:
        ok = _notificar_linux(titulo, corpo)
    if not ok:
        return False
    _gravar_estado_chuva({"codigo": codigo, "ts": agora, "cidade": cidade})
    return True


def _notificar_linux(titulo: str, corpo: str) -> bool:
    try:
        subprocess.run(
            [
                "notify-send",
                "-u", "critical",
                "-a", "Pop Spot",
                "-i", "weather-showers",
                titulo,
                corpo,
            ],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
        return True
    except Exception as e:
        log.debug("notify-send: %s", e)
        return False


def _notificar_windows(titulo: str, corpo: str) -> bool:
    import json
    t_js, c_js = json.dumps(titulo), json.dumps(corpo)
    ps = (
        "Add-Type -AssemblyName System.Windows.Forms; "
        "Add-Type -AssemblyName System.Drawing; "
        "$n = New-Object System.Windows.Forms.NotifyIcon; "
        "$n.Icon = [System.Drawing.SystemIcons]::Information; "
        "$n.Visible = $true; "
        f"$n.ShowBalloonTip(8000, {t_js}, {c_js}, "
        "[System.Windows.Forms.ToolTipIcon]::Info); "
        "Start-Sleep -Seconds 8; $n.Dispose()"
    )
    try:
        subprocess.Popen(
            ["powershell", "-NoProfile", "-STA", "-WindowStyle", "Hidden", "-Command", ps],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except Exception as e:
        log.debug("toast win: %s", e)
        return False
