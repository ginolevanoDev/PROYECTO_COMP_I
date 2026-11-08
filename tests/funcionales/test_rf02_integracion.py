"""Pruebas de aceptación de HU-21 / RF-02: integración de ERA5, turbinas y demanda con las lecturas."""
import numpy as np
import pandas as pd
import pytest

from src.data.cleaning import clean_readings
from src.data.demand import build_demand, load_demand_reference
from src.data.ingestion import unir_lecturas_estaciones
from src.data.integration import integrate_sources
from src.data.resampling import era5_at, select_point
from src.utils.config_loader import load_turbine

COLUMNAS_NUEVAS = ["era5_ws10_ms", "era5_ws100_ms", "era5_wdir100_deg", "era5_alpha", "era5_t2m_c",
                   "era5_sp_hpa", "ws_buje_ms", "rho_kgm3", "potencia_parque_kw", "demanda_mw"]


@pytest.fixture
def turbine():
    return load_turbine()


@pytest.fixture
def era5_raw():
    """ERA5 sintético de 03:00 a 06:00 UTC en dos puntos. En (12.5, -70.0) el viento a 100 m sopla
    del este a 10, 11, 12 y 13 m/s; el otro punto, lejos del parque, está en calma."""
    filas = []
    for lat, lon, base in [(12.5, -70.0, 10.0), (12.75, -70.25, 0.0)]:
        for i, hora in enumerate(range(3, 7)):
            v = base + i
            filas.append({"time": f"2026-04-01 0{hora}:00:00", "latitude": lat, "longitude": lon,
                          "u10": -0.8 * v, "v10": 0.0, "u100": -v, "v100": 0.0,
                          "t2m_C": 27.0, "sp_hPa": 1013.0})
    return pd.DataFrame(filas)


@pytest.fixture
def era5(era5_raw, turbine):
    return select_point(era5_raw, turbine["park_latlon"])


def test_elige_el_punto_mas_cercano_al_parque(era5):
    assert len(era5) == 4
    assert era5["u100"].tolist() == [-10.0, -11.0, -12.0, -13.0]
    assert str(era5.index.tz) == "UTC"


def test_interpola_a_5_min_y_no_extrapola(era5):
    t = pd.to_datetime(["2026-04-01T03:30Z", "2026-04-01T03:05Z", "2026-04-01T02:55Z", "2026-04-01T06:05Z"])
    e = era5_at(era5, t)
    assert e.loc[pd.Timestamp("2026-04-01T03:30Z"), "ws100_ms"] == pytest.approx(10.5)
    assert e.loc[pd.Timestamp("2026-04-01T03:05Z"), "ws100_ms"] == pytest.approx(10 + 5 / 60)
    assert e.loc[pd.Timestamp("2026-04-01T02:55Z")].isna().all()
    assert e.loc[pd.Timestamp("2026-04-01T06:05Z")].isna().all()


def test_direccion_y_cizalladura(era5):
    e = era5_at(era5, pd.to_datetime(["2026-04-01T04:00Z"]))
    assert e["wdir100_deg"].iloc[0] == pytest.approx(90.0)  # u < 0, v = 0: viento del este
    assert e["alpha"].iloc[0] == pytest.approx(np.log(1 / 0.8) / np.log(10))


def test_demanda_calibrada_y_reproducible(cfg):
    media, pico = load_demand_reference(cfg["paths"]["equipment"])
    assert 0 < media < pico
    t = pd.date_range("2026-04-01", "2026-04-15", freq="5min", tz="UTC")
    d1 = build_demand(t, media, pico, cfg["demand"], cfg["time"]["tz"], seed=cfg["seed"])
    d2 = build_demand(t, media, pico, cfg["demand"], cfg["time"]["tz"], seed=cfg["seed"])
    assert d1.equals(d2)
    assert d1.mean() == pytest.approx(media)
    assert d1.max() == pytest.approx(pico)
    assert (d1 > 0).all()


def test_integracion_conserva_lecturas_y_anade_columnas(readings, stations, cfg, turbine, era5):
    lecturas = clean_readings(unir_lecturas_estaciones(readings, stations), cfg)
    ds = integrate_sources(lecturas, cfg, turbine, era5=era5)

    assert len(ds) == len(lecturas)
    assert set(COLUMNAS_NUEVAS) <= set(ds.columns)
    assert ds[COLUMNAS_NUEVAS].notna().all().all()
    # Las columnas del sistema dependen del instante, no de la estación
    assert (ds.groupby("timestamp")[COLUMNAS_NUEVAS].nunique() == 1).all().all()
    assert ds["potencia_parque_kw"].between(0, turbine["n_turbines"] * turbine["rated_kw"]).all()
    assert (ds["ws_buje_ms"] < ds["era5_ws100_ms"]).all()  # buje a 80 m, por debajo de 100 m


def test_fuera_del_periodo_de_era5_queda_en_nan(readings, stations, cfg, turbine, era5):
    lecturas = clean_readings(unir_lecturas_estaciones(readings, stations), cfg)
    ds = integrate_sources(lecturas, cfg, turbine, era5=era5.iloc[:2])  # ERA5 solo hasta las 04:00
    assert len(ds) == len(lecturas)
    tarde = ds["timestamp"] > pd.Timestamp("2026-04-01T04:00Z")
    assert ds.loc[tarde, "potencia_parque_kw"].isna().all()
    assert ds.loc[~tarde, "potencia_parque_kw"].notna().all()
    assert ds["demanda_mw"].notna().all()
