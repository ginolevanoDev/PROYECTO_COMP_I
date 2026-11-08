"""Integración de estaciones, ERA5, potencia estimada y demanda a 5 minutos.

Uso desde la raíz del proyecto: python scripts/run_integracion_5min.py
Requiere ejecutar antes: python scripts/run_etl.py
No modifica los datos originales ni los scripts existentes.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from src.data.resampling import load_era5, interpolar_era5_5min, shear_alpha
from src.data.power_estimation import add_park_power
from src.data.demand import load_or_build_demand
from src.utils.config_loader import load_config, load_turbine


def main():
    cfg = load_config()
    paths = cfg["paths"]
    turbine = load_turbine()
    clean = pd.read_parquet(paths["clean"])
    clean["timestamp"] = pd.to_datetime(clean["timestamp"], utc=True, errors="raise")
    if clean.empty or clean["timestamp"].isna().any():
        raise ValueError("El dataset limpio está vacío o contiene fechas inválidas")
    if clean.duplicated(["station_id", "timestamp"]).any():
        raise ValueError("El dataset limpio aún contiene duplicados por estación y fecha")

    freq = cfg["time"]["freq"]
    if pd.Timedelta(freq) != pd.Timedelta(minutes=5):
        raise ValueError("Este script exige una frecuencia configurada de 5 minutos")
    start, end = clean["timestamp"].min(), clean["timestamp"].max()
    # La limpieza ya corrigió el desfase +4 horas. No volver a aplicarlo.
    lat, lon = cfg["era5"]["point"]
    era = load_era5(paths["era5"], lat, lon, start, end)
    meteo = interpolar_era5_5min(era)
    # Reconstruimos alpha desde u/v interpolados; la función de HU-22 no interpola alpha.
    meteo["ws100_ms"] = np.hypot(meteo["u100"], meteo["v100"])
    ws10 = np.hypot(meteo["u10"], meteo["v10"])
    meteo["alpha"] = shear_alpha(meteo["ws100_ms"], ws10)
    meteo["t2m_c"] = meteo["t2m_C"]
    meteo["sp_hpa"] = meteo["sp_hPa"]
    required = ["ws100_ms", "alpha", "t2m_c", "sp_hpa"]
    if meteo[required].isna().any().any():
        raise ValueError("ERA5 contiene nulos en las variables necesarias para calcular la potencia")
    meteo = add_park_power(meteo, turbine, cfg["calibration"]["wind_cf_factor"])
    capacity = turbine["n_turbines"] * turbine["rated_kw"]
    if not meteo["park_kw"].between(0, capacity).all():
        raise ValueError("La potencia estimada está fuera del rango permitido")
    meteo = meteo.reset_index()

    # Una rejilla homogénea de 5 minutos por estación, sin crear lecturas inventadas.
    # Las filas nuevas conservan NaN en sensores; no se extrapolan las observaciones.
    blocks = []
    for station_id, group in clean.groupby("station_id", sort=True):
        group = group.sort_values("timestamp").set_index("timestamp")
        aligned = group.index == group.index.floor("5min")
        if not aligned.all():
            raise ValueError(f"La estación {station_id} tiene fechas fuera de la rejilla de 5 min")
        grid = pd.date_range(group.index.min(), group.index.max(), freq="5min", tz="UTC", name="timestamp")
        out = group.reindex(grid)
        original = out["station_id"].notna()
        out["station_id"] = station_id
        out["lectura_observada"] = original
        # Los atributos estáticos de estación, cuando existan, no son mediciones de sensor.
        for col in ("name", "code", "latitude", "longitude", "elevation_m", "district", "is_active"):
            if col in out.columns:
                valores = group[col].dropna().unique()
                if len(valores) == 1:
                    out[col] = out[col].fillna(valores[0])
        blocks.append(out.reset_index())
    stations_5min = pd.concat(blocks, ignore_index=True)
    n_pre = len(stations_5min)
    combined = stations_5min.merge(meteo, on="timestamp", how="left", validate="many_to_one", indicator=True)
    without_meteo = int(combined["_merge"].eq("left_only").sum())
    combined = combined.drop(columns=["_merge"])
    if len(combined) != n_pre:
        raise AssertionError("La integración temporal modificó inesperadamente la cantidad de filas")
    if combined.duplicated(["station_id", "timestamp"]).any():
        raise AssertionError("La integración generó duplicados estación-fecha")
    if without_meteo:
        raise ValueError(f"Hay {without_meteo} filas sin cobertura ERA5; revisar límites y fechas")

    dcfg = cfg["demand"]
    unique_index = pd.DatetimeIndex(combined["timestamp"].unique()).sort_values()
    demand = load_or_build_demand(
        unique_index, dcfg["mean_kw"], dcfg["peak_kw"],
        weekend=dcfg["weekend_factor"], noise=dcfg["noise"],
        seed=cfg["seed"], tz=cfg["time"]["tz"],
        real_path=paths.get("demand"),
    )
    combined = combined.merge(demand.rename("demanda_kw").rename_axis("timestamp").reset_index(),
                              on="timestamp", how="left", validate="many_to_one")
    combined["demanda_sintetica"] = not (paths.get("demand") and paths["demand"].exists())
    local = combined["timestamp"].dt.tz_convert(cfg["time"]["tz"])
    combined["hora_local"] = local.dt.hour
    combined["dia_semana_local"] = local.dt.dayofweek
    combined["mes_local"] = local.dt.month
    combined["viento_100m_ms"] = combined["ws100_ms"]

    # Verificaciones finales antes de publicar el dataset.
    if combined[["ws100_ms", "park_kw", "demanda_kw"]].isna().any().any():
        raise ValueError("El dataset final contiene nulos en meteorología, potencia o demanda")
    if not combined["park_kw"].between(0, capacity).all():
        raise ValueError("El dataset final tiene potencias fuera de los límites del parque")
    if combined.duplicated(["station_id", "timestamp"]).any():
        raise ValueError("El dataset final contiene filas duplicadas estación-tiempo")

    result = paths["processed"] / "dataset_5min.parquet"
    result.parent.mkdir(parents=True, exist_ok=True)
    combined.to_parquet(result, index=False)
    print(f"Archivo final: {result}")
    print(f"Filas: {len(combined):,} | Estaciones: {combined.station_id.nunique()} | "
          f"lecturas reales: {int(combined.lectura_observada.sum()):,}")
    print(f"Filas creadas por regularización temporal (sensores NaN): "
          f"{int((~combined.lectura_observada).sum()):,}")
    print(f"Duplicados (estación, fecha): {int(combined.duplicated(['station_id','timestamp']).sum())}")
    print(f"Nulos ERA5 para viento y potencia: {combined[['ws100_ms','park_kw']].isna().sum().to_dict()}")
    print(f"Potencia estimada: {combined.park_kw.min():.2f} a {combined.park_kw.max():.2f} kW")
    print(f"Demanda sintética: {bool(combined.demanda_sintetica.iloc[0])}")
    print("IMPORTANTE: la potencia es un objetivo estimado a partir de ERA5, no una medida real. "
          "No utilizar variables derivadas del mismo cálculo como features de un modelo evaluado contra park_kw sin declararlo.")


if __name__ == "__main__":  
    main()