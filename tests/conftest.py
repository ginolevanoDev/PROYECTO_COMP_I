import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.utils.config_loader import load_config  # noqa: E402


@pytest.fixture
def cfg():
    return load_config()


@pytest.fixture
def stations():
    return pd.DataFrame({"id": ["A", "B"], "name": ["Palm Beach", "Hooiberg"], "elevation_m": [3, 165],
                         "is_active": [True, True]})


@pytest.fixture
def readings():
    """Dos estaciones x 6 pasos de 5 min, desordenadas, con un duplicado exacto en A."""
    ts = pd.date_range("2026-04-01T00:00:00Z", periods=6, freq="5min").strftime("%Y-%m-%dT%H:%M:%SZ")
    filas = []
    for st, base in [("A", 20.0), ("B", 30.0)]:
        for i, t in enumerate(ts):
            filas.append({"id": f"{st}{i}", "station_id": st, "timestamp": t, "temperature_c": 29.0,
                          "humidity_pct": 75.0, "wind_speed_kmh": base + i % 2, "wind_direction_deg": 45.0,
                          "pressure_hpa": 1015.0, "precipitation_mm": 0.0, "visibility_km": 10.0, "uv_index": 0.0})
    df = pd.DataFrame(filas)
    dup = df.iloc[[2]].assign(id="A2-copia")
    return pd.concat([df.iloc[::-1], dup], ignore_index=True)
