"""HU-21 / RF-02: integración de reanálisis, demanda y turbinas con las lecturas.

Entrada: las lecturas limpias de RF-03 (una fila por estación y timestamp, en UTC).
Salida: las mismas filas con columnas añadidas. Todas dependen solo del timestamp, no de la estación:
- era5_*: viento a 10 y 100 m, dirección, cizalladura, temperatura y presión de ERA5 en el punto
  de rejilla más cercano al parque.
- ws_buje_ms, rho_kgm3, potencia_parque_kw: viento a buje (ERA5 100 m -> buje con el alpha horario,
  como en el EDA §5), densidad del aire y potencia del parque con la curva de HU-23, sin calibrar
  frente al histórico.
- demanda_mw: demanda sintética del sistema (ver demand.py).
"""
import pandas as pd

from src.data.demand import synthetic_demand
from src.data.power_estimation import air_density, park_power, wind_at_hub
from src.data.resampling import era5_at, load_era5
from src.utils.logger import get_logger

log = get_logger(__name__)

# Altura (m) del viento de ERA5 que se extrapola a buje.
ERA5_ALTURA_M = 100


def system_features(era5, times, turbine, cfg):
    """Columnas por timestamp: ERA5, viento a buje, densidad, potencia del parque y demanda."""
    e = era5_at(era5, times)
    f = pd.DataFrame(index=e.index)
    f["era5_ws10_ms"] = e["ws10_ms"]
    f["era5_ws100_ms"] = e["ws100_ms"]
    f["era5_wdir100_deg"] = e["wdir100_deg"]
    f["era5_alpha"] = e["alpha"]
    f["era5_t2m_c"] = e["t2m_C"]
    f["era5_sp_hpa"] = e["sp_hPa"]
    f["ws_buje_ms"] = wind_at_hub(e["ws100_ms"], ERA5_ALTURA_M, turbine["hub_height_m"], e["alpha"])
    f["rho_kgm3"] = air_density(e["t2m_C"], e["sp_hPa"])
    f["potencia_parque_kw"] = park_power(f["ws_buje_ms"], turbine, rho=f["rho_kgm3"])
    # La temperatura de las estaciones no es fiable (EDA §8), por eso la demanda usa la de ERA5.
    f["demanda_mw"] = synthetic_demand(e.index, cfg, temp_c=e["t2m_C"]).to_numpy()
    return f


def integrate_sources(lecturas, cfg, turbine, era5=None):
    """Añade a `lecturas` (salida de `clean_readings`) las columnas de `system_features`.

    Conserva todas las filas. Los instantes fuera del periodo de ERA5 quedan con NaN en las
    columnas de ERA5 y de potencia, y se avisa en el log.
    """
    if era5 is None:
        era5 = load_era5(cfg["paths"]["era5"], turbine["park_latlon"])

    lecturas = lecturas.assign(timestamp=pd.to_datetime(lecturas["timestamp"], utc=True).dt.as_unit("ns"))
    sistema = system_features(era5, lecturas["timestamp"], turbine, cfg)

    fuera = int(sistema["era5_ws100_ms"].isna().sum())
    if fuera:
        log.warning("RF-02: %d de %d instantes fuera del periodo de ERA5 (%s -> %s): quedan en NaN",
                    fuera, len(sistema), era5.index.min(), era5.index.max())

    resultado = lecturas.merge(sistema, left_on="timestamp", right_index=True, how="left",
                               validate="many_to_one")
    log.info("RF-02: dataset integrado con %d filas y %d columnas", len(resultado), resultado.shape[1])
    return resultado
