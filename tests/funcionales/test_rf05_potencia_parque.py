"""Pruebas de HU-24 / RF-05: potencia del parque a partir del viento de ERA5, calibrada."""
import numpy as np
import pandas as pd
import pytest

from src.data.power_estimation import add_park_power, hourly_park_power
from src.utils.config_loader import load_turbine


@pytest.fixture
def turbine():
    return load_turbine()


def _entrada(ws100, alpha=0.1):
    idx = pd.date_range("2026-04-01", periods=len(ws100), freq="5min", tz="UTC")
    return pd.DataFrame({"ws100_ms": ws100, "alpha": alpha, "t2m_c": 28.0, "sp_hpa": 1011.0}, index=idx)


def test_potencia_del_parque(turbine):
    out = add_park_power(_entrada([2.0, 10.0, 40.0]), turbine, factor=0.76)
    assert out["park_kw"].iloc[0] == 0  # bajo el arranque
    assert out["park_kw"].iloc[2] == 0  # sobre el corte
    assert 0 < out["park_kw"].iloc[1] <= 30000 * 0.76
    assert (out["kw_por_turbina"] == out["park_kw"] / 10).all()


def test_cero_con_viento_a_buje_menor_de_4_ms(turbine):
    out = add_park_power(_entrada([0.0, 1.0, 3.9]), turbine, factor=0.76)
    assert (out["ws_buje_ms"] < 4).all()
    assert (out["park_kw"] == 0).all()


def test_acotada_entre_0_y_30000_kw(turbine):
    ws = np.random.default_rng(42).uniform(0, 30, 500)
    out = add_park_power(_entrada(ws), turbine, factor=0.76)
    assert out["park_kw_curva"].between(0, turbine["n_turbines"] * turbine["rated_kw"]).all()
    assert out["park_kw"].between(0, 30000).all()
    assert out["park_kw"].notna().all()


def test_viento_a_buje_en_ms_por_debajo_de_100_m(turbine):
    out = add_park_power(_entrada([8.0, 12.0], alpha=0.14), turbine, factor=0.76)
    assert out["ws_buje_ms"].tolist() == pytest.approx([8.0 * 0.8 ** 0.14, 12.0 * 0.8 ** 0.14])


def test_factor_de_calibracion_leido_de_config(cfg, turbine):
    factor = cfg["calibration"]["wind_cf_factor"]
    assert factor == pytest.approx(0.76)
    out = add_park_power(_entrada([9.0, 11.0]), turbine, factor)
    assert np.allclose(out["park_kw"], out["park_kw_curva"] * factor)


def test_factor_invalido(turbine):
    for factor in (0, -0.5, 1.2):
        with pytest.raises(ValueError, match="factor"):
            add_park_power(_entrada([10.0]), turbine, factor)


def test_no_modifica_la_entrada(turbine):
    df = _entrada([10.0])
    add_park_power(df, turbine, 0.76)
    assert list(df.columns) == ["ws100_ms", "alpha", "t2m_c", "sp_hpa"]


def test_viento_nulo_da_potencia_nula(turbine):
    out = add_park_power(_entrada([np.nan, 10.0]), turbine, 0.76)
    assert np.isnan(out["park_kw"].iloc[0])  # un hueco no se convierte en 0 kW
    assert out["park_kw"].iloc[1] > 0


def test_potencia_horaria_desde_load_era5(turbine):
    idx = pd.date_range("2026-04-01", periods=2, freq="h", tz="UTC")
    era = pd.DataFrame({"u100": [-6.0, 0.0], "v100": [-8.0, -12.0], "alpha": 0.1, "t2m_C": 28.0,
                        "sp_hPa": 1011.0}, index=idx)
    out = hourly_park_power(era, turbine, 0.76)
    assert out["ws100_ms"].tolist() == pytest.approx([10.0, 12.0])  # módulo de (u, v)
    assert out.index.equals(idx)
    assert (out["park_kw"] > 0).all()
