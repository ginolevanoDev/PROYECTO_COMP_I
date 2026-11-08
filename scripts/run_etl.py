"""ETL: ingesta (RF-01), limpieza (RF-03) e integración (RF-02).

Escribe data/interim/clean.parquet y data/processed/dataset_5min.parquet.

Uso: python scripts/run_etl.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data.cleaning import clean_readings
from src.data.ingestion import cargar_estaciones_y_lecturas
from src.data.integration import integrate_sources
from src.utils.config_loader import load_config, load_turbine
from src.utils.logger import get_logger

log = get_logger("run_etl")


def main():
    cfg = load_config()
    p = cfg["paths"]
    df = cargar_estaciones_y_lecturas(p["readings"], p["stations"])
    df = clean_readings(df, cfg)
    p["clean"].parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(p["clean"], index=False)
    log.info("Guardado %s: %d filas, %s -> %s", p["clean"].relative_to(p["clean"].parents[2]), len(df),
             df["timestamp"].min(), df["timestamp"].max())

    # HU-21 / RF-02: ERA5, potencia del parque y demanda
    ds = integrate_sources(df, cfg, load_turbine())
    p["dataset"].parent.mkdir(parents=True, exist_ok=True)
    ds.to_parquet(p["dataset"], index=False)
    log.info("Guardado %s: %d filas, %d columnas", p["dataset"].relative_to(p["dataset"].parents[2]), len(ds),
             ds.shape[1])


if __name__ == "__main__":
    main()
