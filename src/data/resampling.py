"""HU-21 / RF-02: reanálisis ERA5 (datos_meteo.csv) llevado a los instantes de las lecturas.

ERA5 es horario y está en UTC. Las lecturas son cada 5 min y RF-03 ya las deja en UTC (+4 h).
Se interpolan en el tiempo las componentes del viento (u, v), no la velocidad ni la dirección,
porque la dirección no se puede interpolar linealmente (salto 359° -> 0°). Después se recalculan
velocidad, dirección y exponente de cizalladura como en el EDA (§3 y §5).
"""
import numpy as np
import pandas as pd

from src.utils.logger import get_logger

log = get_logger(__name__)

# Columnas de ERA5 que se interpolan en el tiempo.
COLUMNAS_ERA5 = ["u10", "v10", "u100", "v100", "t2m_C", "sp_hPa"]

# Recorte del exponente de cizalladura, el mismo que el EDA §5.
ALPHA_MIN, ALPHA_MAX = 0.0, 0.5


def haversine_km(lat1, lon1, lat2, lon2):
    """Distancia en km sobre la esfera entre dos puntos (admite arrays)."""
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371.0 * np.arcsin(np.sqrt(a))


def select_point(era, latlon):
    """Serie horaria de ERA5 (índice UTC, ordenada) del punto de rejilla más cercano a `latlon`."""
    puntos = era[["latitude", "longitude"]].drop_duplicates().reset_index(drop=True)
    dist = haversine_km(latlon[0], latlon[1], puntos["latitude"].to_numpy(), puntos["longitude"].to_numpy())
    i = int(np.argmin(dist))
    lat, lon = puntos.loc[i, "latitude"], puntos.loc[i, "longitude"]
    log.info("RF-02: punto ERA5 (%s, %s), a %.1f km del parque", lat, lon, dist[i])

    serie = era[(era["latitude"] == lat) & (era["longitude"] == lon)]
    tiempo = pd.DatetimeIndex(pd.to_datetime(serie["time"]))
    tiempo = tiempo.tz_localize("UTC") if tiempo.tz is None else tiempo.tz_convert("UTC")
    serie = serie[COLUMNAS_ERA5].set_axis(tiempo.as_unit("ns").rename("timestamp")).sort_index()
    return serie[~serie.index.duplicated()]


def load_era5(path, latlon):
    """Lee `datos_meteo.csv` y devuelve la serie del punto más cercano a `latlon` (ver `select_point`)."""
    return select_point(pd.read_csv(path), latlon)


def era5_at(era5, times):
    """Interpola linealmente la serie horaria `era5` a los instantes `times` (UTC).

    Devuelve un DataFrame indexado por los instantes únicos y ordenados de `times` con las columnas
    de ERA5 más `ws10_ms`, `ws100_ms`, `wdir100_deg` (de dónde viene) y `alpha` (cizalladura 10->100 m).
    No extrapola: fuera del periodo de ERA5 todo queda en NaN.
    """
    times = pd.DatetimeIndex(times).unique().sort_values().as_unit("ns")
    union = era5.index.union(times)
    out = era5.reindex(union).interpolate(method="time", limit_area="inside").reindex(times)

    out["ws10_ms"] = np.hypot(out["u10"], out["v10"])
    out["ws100_ms"] = np.hypot(out["u100"], out["v100"])
    out["wdir100_deg"] = (270 - np.degrees(np.arctan2(out["v100"], out["u100"]))) % 360
    with np.errstate(divide="ignore", invalid="ignore"):
        alpha = np.log(out["ws100_ms"] / out["ws10_ms"]) / np.log(100 / 10)
    out["alpha"] = alpha.clip(ALPHA_MIN, ALPHA_MAX)
    return out
