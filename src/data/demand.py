"""HU-21 / RF-02: demanda eléctrica del sistema de Aruba.

No hay datos reales de demanda, así que se construye un perfil SINTÉTICO:
- La media y el pico salen de data/external/equipment_installed.json (`load_demand_2026`).
- La forma (ciclo diario, fin de semana, efecto de la temperatura y ruido) es un supuesto del
  modelo, sin fuente, con los parámetros de la sección `demand` de config.yaml.
Hay que declararlo como supuesto en el Alcance de la memoria.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.utils.logger import get_logger

log = get_logger(__name__)


def load_demand_reference(path):
    """Devuelve (media_mw, pico_mw) de `load_demand_2026` en equipment_installed.json."""
    datos = json.loads(Path(path).read_text(encoding="utf-8"))
    ref = datos["equipment_installed_capacity"]["load_demand_2026"]
    return float(ref["average_mw"]), float(ref["max_peak_mw"])


def build_demand(times, average_mw, peak_mw, params, tz, temp_c=None, seed=42):
    """Perfil sintético de demanda (MW) en los instantes `times` (DatetimeIndex con zona horaria).

    Forma = ciclo diario (máximo en `peak_hour_local`) x factor de fin de semana
    + efecto de la temperatura + ruido con semilla. Después se reescala para que en el periodo
    la media sea `average_mw` y el máximo `peak_mw`, así que de los parámetros de la forma solo
    importa la proporción entre ellos.
    """
    times = pd.DatetimeIndex(times)
    if len(times) == 0:
        raise ValueError("No hay instantes para construir la demanda")
    local = times.tz_convert(tz)
    hora = np.asarray(local.hour + local.minute / 60, dtype="float64")
    dia = np.asarray(local.day_of_week)

    forma = 1 + params["daily_amplitude"] * np.cos(2 * np.pi * (hora - params["peak_hour_local"]) / 24)
    forma = forma * np.where(dia >= 5, params["weekend_factor"], 1.0)
    if temp_c is not None:
        t = np.asarray(temp_c, dtype="float64")
        if np.isfinite(t).any():
            t = np.where(np.isfinite(t), t, np.nanmean(t))
            forma = forma + params["temp_coef_per_c"] * (t - t.mean())
    forma = forma + np.random.default_rng(seed).normal(0, params["noise_std"], len(times))

    rango = forma.max() - forma.mean()
    escala = (peak_mw - average_mw) / rango if rango > 0 else 0.0
    return pd.Series(average_mw + (forma - forma.mean()) * escala, index=times, name="demanda_mw")


def synthetic_demand(times, cfg, temp_c=None):
    """Demanda sintética en `times` con la referencia de equipment_installed.json y los parámetros de config."""
    media, pico = load_demand_reference(cfg["paths"]["equipment"])
    log.info("RF-02: demanda SINTÉTICA calibrada a media %.0f MW y pico %.0f MW (equipment_installed.json)",
             media, pico)
    return build_demand(times, media, pico, cfg["demand"], cfg["time"]["tz"], temp_c=temp_c, seed=cfg["seed"])
