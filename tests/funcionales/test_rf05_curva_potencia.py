"""Pruebas de aceptación de HU-23 / RF-05: curva de potencia de la Vestas V90-3.0."""
import json

import numpy as np
import pandas as pd
import pytest

from src.data.power_estimation import air_density, park_power, turbine_power, wind_at_hub
from src.utils.config_loader import ROOT, load_turbine


@pytest.fixture
def turbine():
    return load_turbine()


def _num(texto):
    return float(str(texto).split()[0].replace(",", ""))


def test_coherente_con_la_ficha(turbine):
    ficha = json.loads((ROOT / "data" / "external" / "turbinas.json").read_text(encoding="utf-8"))
    hoja = ficha["hoja_de_datos"]
    energia = hoja["De energía"]
    assert ficha["nombre"] == turbine["modelo"]
    assert _num(energia["Potencia nominal"]) == turbine["rated_kw"] == max(turbine["curve"]["kw"])
    assert _num(energia["Velocidad del viento"]) == turbine["cut_in_ms"]
    assert _num(energia["Velocidad nominal del viento"]) == turbine["rated_ms"]
    assert _num(energia["Velocidad del viento de corte"]) == turbine["cut_out_ms"]
    assert _num(hoja["Hélice"]["diámetro"]) == turbine["rotor_m"]
    alturas = [float(h) for h in hoja["Torre"]["Altura del buje"].split()[0].split("/")]
    assert turbine["hub_height_m"] in alturas


def test_cero_fuera_del_rango_de_operacion(turbine):
    assert turbine_power(np.array([0.0, 3.0, 3.99, 25.0, 30.0]), turbine).tolist() == [0.0] * 5


def test_nominal_en_la_meseta(turbine):
    assert (turbine_power(np.linspace(16, 24.9, 20), turbine) == turbine["rated_kw"]).all()


def test_reproduce_los_puntos_tabulados(turbine):
    assert turbine_power(8.0, turbine) == 886
    assert turbine_power(12.0, turbine) == 2544
    assert turbine_power(8.5, turbine) == pytest.approx((886 + 1273) / 2)


def test_no_decrece_entre_arranque_y_corte(turbine):
    kw = turbine_power(np.linspace(turbine["cut_in_ms"], turbine["cut_out_ms"] - 0.01, 500), turbine)
    assert (np.diff(kw) >= 0).all()


def test_maximo_del_parque_30_mw(turbine):
    assert park_power(np.linspace(0, 40, 801), turbine).max() == 30000


def test_nan_y_series(turbine):
    ws = pd.Series([np.nan, 10.0], index=pd.date_range("2026-04-01", periods=2, freq="5min", tz="UTC"))
    kw = park_power(ws, turbine)
    assert kw.index.equals(ws.index)
    assert np.isnan(kw.iloc[0]) and kw.iloc[1] == 17100


def test_correccion_por_densidad(turbine):
    ws = np.array([8.0, 20.0])
    assert turbine_power(ws, turbine, rho=turbine["rho_ref"]).tolist() == turbine_power(ws, turbine).tolist()
    menos_denso = turbine_power(ws, turbine, rho=1.17)
    assert menos_denso[0] < 886
    assert menos_denso[1] == turbine["rated_kw"]


def test_densidad_del_aire():
    assert air_density(15.0, 1013.25) == pytest.approx(1.225, abs=1e-3)
    assert air_density(28.0, 1011.0) < 1.225


def test_viento_a_buje():
    assert wind_at_hub(10.0, 10, 80, 0.0) == 10.0
    assert wind_at_hub(10.0, 10, 80, 1 / 7) == pytest.approx(10 * 8 ** (1 / 7))


def test_curva_invalida_se_rechaza(tmp_path):
    ruta = tmp_path / "turbinas.yaml"
    ruta.write_text("curve:\n  ws_ms: [0, 4, 5]\n  kw: [0, 77]\n", encoding="utf-8")
    with pytest.raises(ValueError, match="velocidades"):
        load_turbine(ruta)
