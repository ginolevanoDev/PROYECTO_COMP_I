"""ETL: ingesta (RF-01) y limpieza (RF-03) -> data/interim/clean.parquet.

Uso: python scripts/run_etl.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data.cleaning import clean_readings
from src.data.ingestion import cargar_estaciones_y_lecturas
from src.utils.config_loader import load_config
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


if __name__ == "__main__":
    main()
