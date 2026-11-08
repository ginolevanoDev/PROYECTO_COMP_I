"""Demanda eléctrica de Aruba (HU-21, RF-02).

No hay serie real de demanda. Si existe el fichero de `paths.demand` en config.yaml, se carga;
si no, se construye un perfil sintético. Es un supuesto, documentado en
docs/design/inventario_fuentes.md; está pendiente preguntar a la docente si hay datos reales.
"""
from pathlib import Path

import numpy as np
import pandas as pd

from src.utils.logger import get_logger

log = get_logger(__name__)

# Carga relativa por hora local de Aruba (0 a 23 h): mínimo de madrugada, máximo a las 19-20 h.
PERFIL_HORARIO = [0.80, 0.77, 0.75, 0.74, 0.74, 0.76, 0.81, 0.87, 0.92, 0.96, 0.99, 1.01,
                  1.02, 1.03, 1.04, 1.04, 1.05, 1.07, 1.10, 1.13, 1.12, 1.06, 0.97, 0.88]


def build_synthetic_demand(index, mean_kw, peak_kw, weekend=0.93, noise=0.02, seed=42, tz="America/Aruba"):
    """Demanda sintética en kW sobre `index` (DatetimeIndex con zona horaria).

    Forma: `PERFIL_HORARIO` en hora local, x `weekend` en sábado y domingo, x (1 + ruido normal de
    desviación `noise` con semilla `seed`). Después se reescala linealmente para que en `index` la
    media sea `mean_kw` y el máximo `peak_kw`. Con la misma semilla sale siempre igual (RNF-04).
    """
    local = index.tz_convert(tz)
    hora = np.asarray(local.hour + local.minute / 60, dtype="float64")
    base = np.interp(hora, np.arange(25), PERFIL_HORARIO + PERFIL_HORARIO[:1])
    base = base * np.where(np.asarray(local.day_of_week) >= 5, weekend, 1.0)
    base = base * (1 + np.random.default_rng(seed).normal(0, noise, len(index)))
    b = (peak_kw - mean_kw) / (base.max() - base.mean())
    return pd.Series(mean_kw + b * (base - base.mean()), index=index, name="demanda_kw")


def load_real_demand(path, index):
    """Serie real de demanda llevada a `index` (UTC).

    El fichero es un CSV con las columnas `timestamp` (UTC) y `demanda_kw`. Se interpola en el
    tiempo sin extrapolar; si algún instante de `index` queda fuera de la serie, lanza ValueError.
    """
    real = pd.read_csv(path, usecols=["timestamp", "demanda_kw"])
    real["timestamp"] = pd.to_datetime(real["timestamp"], utc=True)
    serie = real.drop_duplicates("timestamp").set_index("timestamp")["demanda_kw"].sort_index()
    out = serie.reindex(serie.index.union(index)).interpolate(method="time", limit_area="inside").reindex(index)
    faltan = int(out.isna().sum())
    if faltan:
        raise ValueError(f"La demanda real de {path} no cubre {faltan} de {len(index)} instantes")
    return out.rename("demanda_kw")


def load_or_build_demand(index, mean_kw, peak_kw, weekend=0.93, noise=0.02, seed=42, tz="America/Aruba",
                         real_path=None):
    """Demanda en kW sobre `index`, alineada con las lecturas por timestamp (HU-21, RF-02).

    Si `real_path` existe, carga la serie real (`load_real_demand`). Si no, construye el perfil
    sintético (`build_synthetic_demand`) con los parámetros de la sección `demand` de config.yaml.
    """
    if real_path is not None and Path(real_path).exists():
        log.info("RF-02: demanda real desde %s", real_path)
        return load_real_demand(real_path, index)
    log.info("RF-02: sin serie real de demanda: perfil SINTÉTICO con media %.0f kW y pico %.0f kW",
             mean_kw, peak_kw)
    return build_synthetic_demand(index, mean_kw, peak_kw, weekend, noise, seed, tz)
