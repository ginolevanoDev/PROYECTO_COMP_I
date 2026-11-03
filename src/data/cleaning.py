"""RF-03: limpieza de las lecturas de estación (portado del EDA §2-4)."""
import numpy as np
import pandas as pd

from src.utils.logger import get_logger

log = get_logger(__name__)

KEY = ["station_id", "timestamp"]


def to_datetime_utc(df, col="timestamp", offset_h=0):
    """Parsea `col` a UTC y suma `offset_h` horas (corrige la hora local etiquetada como Z)."""
    df = df.copy()
    df[col] = pd.to_datetime(df[col], utc=True, errors="coerce") + pd.Timedelta(hours=offset_h)
    malos = df[col].isna().sum()
    if malos:
        log.warning("RF-03: %d timestamps no parseables descartados", malos)
        df = df.dropna(subset=[col])
    return df


def fix_types(df, columns):
    df = df.copy()
    df[columns] = df[columns].apply(pd.to_numeric, errors="coerce").astype("float64")
    return df


def drop_duplicates(df, columns):
    """Una fila por (station_id, timestamp). Si las copias difieren, se promedian `columns`."""
    n = df.duplicated(KEY).sum()
    means = df.groupby(KEY, sort=False)[columns].mean()
    out = df.drop_duplicates(KEY).set_index(KEY)
    out[columns] = means
    log.info("RF-03: %d filas duplicadas eliminadas", n)
    return out.reset_index()


def sort_series(df):
    return df.sort_values(KEY).reset_index(drop=True)


def flag_out_of_range(df, ranges):
    """Valores fuera del rango físico -> NaN. Suma en `qc_flags` cuántas variables se anularon por fila."""
    df = df.copy()
    if "qc_flags" not in df:
        df["qc_flags"] = 0
    for col, (lo, hi) in ranges.items():
        if col not in df:
            continue
        mask = (df[col] < lo) | (df[col] > hi)
        df.loc[mask, col] = np.nan
        df["qc_flags"] += mask.astype(int)
        if mask.any():
            log.info("RF-03: %s, %d valores fuera de [%s, %s]", col, mask.sum(), lo, hi)
    return df


def _interp_short_gaps(s, max_steps):
    """Interpolación lineal solo en huecos internos de como mucho `max_steps` NaN seguidos."""
    na = s.isna()
    run = na.groupby((~na).cumsum()).transform("sum")
    return s.interpolate(limit_area="inside").where(~na | (run <= max_steps))


def _run_length(mask):
    """Longitud de la racha de True a la que pertenece cada posición (0 donde es False)."""
    return mask.groupby((~mask).cumsum()).transform("sum").where(mask, 0)


def treat_outliers(df, columns, k=3.0, max_steps=3):
    """Outliers por IQR, calculados por estación.

    - Rachas de hasta `max_steps` pasos: picos de sensor -> NaN e interpolación.
    - Rachas más largas: eventos meteorológicos reales (en el dataset, chubascos de ~4 h con viento
      ~50 km/h, presión ~1000 hPa y lluvia). Se conservan y se marcan en `qc_event`, porque son las
      rampas que el modelo debe aprender.

    Requiere el df ordenado por (station_id, timestamp).
    """
    df = df.copy()
    if "qc_flags" not in df:
        df["qc_flags"] = 0
    g = df.groupby("station_id")[columns]
    q1, q3 = g.transform(lambda s: s.quantile(0.25)), g.transform(lambda s: s.quantile(0.75))
    iqr = q3 - q1
    mask = (df[columns] < q1 - k * iqr) | (df[columns] > q3 + k * iqr)
    run = mask.groupby(df["station_id"]).transform(_run_length)
    spike = mask & (run <= max_steps)
    df["qc_event"] = (mask & ~spike).any(axis=1)
    df[columns] = df[columns].mask(spike)
    df["qc_flags"] += spike.sum(axis=1)
    log.info("RF-03: picos IQR (k=%s) anulados por variable: %s | filas en evento: %d",
             k, spike.sum().to_dict(), df["qc_event"].sum())

    huecos = df[columns].isna().sum().sum()
    df[columns] = df.groupby("station_id")[columns].transform(lambda s: _interp_short_gaps(s, max_steps))
    log.info("RF-03: %d valores interpolados, %d siguen en NaN", huecos - df[columns].isna().sum().sum(),
             df[columns].isna().sum().sum())
    return df


def filter_active(df):
    if "is_active" not in df:
        return df
    return df[df["is_active"].astype(bool)].reset_index(drop=True)


def clean_readings(df, cfg):
    """Pipeline RF-03 completo sobre las lecturas ya unidas a sus estaciones (RF-01)."""
    variables = list(cfg["validation_ranges"])
    c = cfg["cleaning"]
    df = to_datetime_utc(df, offset_h=cfg["time"]["station_utc_offset_h"])
    df = fix_types(df, variables)
    df = drop_duplicates(df, variables)
    df = sort_series(df)
    df = filter_active(df)
    df = flag_out_of_range(df, cfg["validation_ranges"])
    df = treat_outliers(df, c["outlier_columns"], k=c["iqr_k"], max_steps=c["max_interp_steps"])
    if c.get("unreliable_columns"):
        log.warning("RF-03: columnas poco fiables según el EDA (no usar como feature principal): %s",
                    c["unreliable_columns"])
    return df.drop(columns=["id"], errors="ignore")
