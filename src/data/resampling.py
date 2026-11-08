"""Reanálisis ERA5 y rejilla común de 5 minutos (RF-02, RF-04).

HU-21 (RF-02): lectura de ERA5 en el punto del parque (`load_era5`).
HU-22 (RF-04): paso a 5 minutos y unión de fuentes (se añade en este mismo fichero).

ERA5 es horario y viene en UTC sin zona; aquí se marca como UTC. Las lecturas de las
estaciones ya salen en UTC de `clean_readings`, así que no hay que sumar ningún desfase.
"""
import numpy as np
import pandas as pd

from src.utils.logger import get_logger

log = get_logger(__name__)

# Columnas de datos_meteo.csv que se conservan: viento a 10 y 100 m (componentes u y v),
# temperatura, presión y rachas a 10 m. No se usan ssrd ni ssrd_Wm2: la radiación está mal
# desacumulada (el EDA encontró un 25 % de valores negativos).
ERA5_COLS = ["u100", "v100", "u10", "v10", "t2m_C", "sp_hPa", "i10fg"]

# Recorte del exponente de cizalladura (decisión del EDA, §5).
ALPHA_MIN, ALPHA_MAX = 0.0, 0.5


def _utc(t):
    """Timestamp en UTC; si llega sin zona, se interpreta como UTC."""
    t = pd.Timestamp(t)
    return t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")


def shear_alpha(ws100, ws10):
    """Exponente de cizalladura entre 10 y 100 m: ln(ws100 / ws10) / ln(10), recortado a [0, 0,5].

    Es el `alpha` de la ley potencial que usa `wind_at_hub` para llevar el viento a 80 m.
    """
    with np.errstate(divide="ignore", invalid="ignore"):
        alpha = np.log(ws100 / ws10) / np.log(10)
    return alpha.clip(ALPHA_MIN, ALPHA_MAX)


def load_era5(path, lat, lon, start, end):
    """ERA5 horario del punto (lat, lon) entre `start` y `end` (HU-21, RF-02).

    Se queda con una hora de margen a cada lado (hora en punto anterior a `start` y posterior a
    `end`) para que la interpolación a 5 minutos de HU-22 cubra los extremos.

    Devuelve un DataFrame con índice horario en UTC, las columnas de `ERA5_COLS` y `alpha`
    (cizalladura horaria). Lanza ValueError si el punto no está en el fichero o si en el periodo
    falta alguna hora, para que el ETL no siga con huecos sin avisar.
    """
    era = pd.read_csv(path, usecols=["time", "latitude", "longitude", *ERA5_COLS])
    era = era[np.isclose(era["latitude"], lat) & np.isclose(era["longitude"], lon)]
    if era.empty:
        raise ValueError(f"El punto ({lat}, {lon}) no está en {path}: revisa era5.point en config.yaml")

    era["time"] = pd.to_datetime(era["time"], utc=True)
    era = era.drop_duplicates("time").set_index("time").sort_index()
    era = era.drop(columns=["latitude", "longitude"])

    ini, fin = _utc(start).floor("h"), _utc(end).ceil("h")
    era = era.loc[ini:fin]
    faltan = pd.date_range(ini, fin, freq="h").difference(era.index)
    if len(faltan):
        raise ValueError(f"ERA5 no cubre el periodo {ini} -> {fin}: faltan {len(faltan)} horas "
                         f"(la primera, {faltan[0]})")

    era["alpha"] = shear_alpha(np.hypot(era["u100"], era["v100"]), np.hypot(era["u10"], era["v10"]))
    log.info("RF-02: ERA5 en (%s, %s): %d horas de %s a %s, sin huecos", lat, lon, len(era), ini, fin)
    return era
