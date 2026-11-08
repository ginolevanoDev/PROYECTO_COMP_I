"""Pruebas de HU-21 / RF-02: ERA5 y demanda eléctrica.

Usan datos pequeños inventados, nunca el fichero real de ERA5 ni el de lecturas.
"""
import json

import numpy as np
import pandas as pd
import pytest

from src.data.demand import load_or_build_demand
from src.data.resampling import ERA5_COLS, load_era5, shear_alpha
from src.utils.config_loader import load_turbine


def _era5_csv(tmp_path, horas=range(6), lats=(12.5, 12.75), u100=-10.0, u10=-8.0):
    """CSV con el formato de datos_meteo.csv: horas del 1/4/2026 en dos puntos de la rejilla."""
    filas = [{"time": f"2026-04-01 {h:02d}:00:00", "latitude": lat, "longitude": -70.0, "u100": u100,
              "v100": 0.0, "u10": u10, "v10": 0.0, "t2m_C": 28.0, "sp_hPa": 1011.0, "i10fg": 12.0,
              "ssrd": -5.0, "ssrd_Wm2": -0.001}
             for h in horas for lat in lats]
    ruta = tmp_path / "era5.csv"
    pd.DataFrame(filas).to_csv(ruta, index=False)
    return ruta


# --- ERA5 -------------------------------------------------------------------------------------

def test_load_era5_filtra_punto_y_periodo(tmp_path):
    era = load_era5(_era5_csv(tmp_path), 12.5, -70.0, "2026-04-01 01:00Z", "2026-04-01 03:00Z")
    assert len(era) == 3
    assert str(era.index.tz) == "UTC"


def test_load_era5_deja_una_hora_de_margen(tmp_path):
    era = load_era5(_era5_csv(tmp_path), 12.5, -70.0, "2026-04-01 01:35Z", "2026-04-01 03:20Z")
    assert era.index[0] == pd.Timestamp("2026-04-01 01:00Z")
    assert era.index[-1] == pd.Timestamp("2026-04-01 04:00Z")


def test_load_era5_columnas_sin_radiacion(tmp_path):
    era = load_era5(_era5_csv(tmp_path), 12.5, -70.0, "2026-04-01 01:00Z", "2026-04-01 03:00Z")
    assert list(era.columns) == [*ERA5_COLS, "alpha"]
    assert not {"ssrd", "ssrd_Wm2"} & set(era.columns)


def test_alpha_de_la_ley_potencial(tmp_path):
    era = load_era5(_era5_csv(tmp_path), 12.5, -70.0, "2026-04-01 01:00Z", "2026-04-01 03:00Z")
    assert era["alpha"].iloc[0] == pytest.approx(np.log(10 / 8) / np.log(10))


def test_alpha_recortado_entre_0_y_05():
    alpha = shear_alpha(pd.Series([5.0, 10.0, 10.0]), pd.Series([10.0, 10.0, 0.5]))
    assert alpha.tolist() == [0.0, 0.0, 0.5]


def test_load_era5_falla_si_el_punto_no_existe(tmp_path):
    with pytest.raises(ValueError, match="no está"):
        load_era5(_era5_csv(tmp_path), 12.25, -70.0, "2026-04-01 01:00Z", "2026-04-01 03:00Z")


def test_load_era5_falla_si_no_cubre_el_periodo(tmp_path):
    with pytest.raises(ValueError, match="no cubre"):
        load_era5(_era5_csv(tmp_path), 12.5, -70.0, "2026-04-01 03:00Z", "2026-04-01 08:00Z")


def test_load_era5_falla_si_falta_una_hora(tmp_path):
    ruta = _era5_csv(tmp_path, horas=[0, 1, 3, 4])
    with pytest.raises(ValueError, match="faltan 1 horas"):
        load_era5(ruta, 12.5, -70.0, "2026-04-01 00:00Z", "2026-04-01 04:00Z")


def test_punto_era5_es_el_mas_cercano_al_parque(cfg):
    # La rejilla de ERA5 va de 0,25 en 0,25 grados: el nodo más cercano es el redondeo a 0,25.
    lat, lon = load_turbine()["park_latlon"]
    assert cfg["era5"]["point"] == [round(lat * 4) / 4, round(lon * 4) / 4]


# --- Demanda ----------------------------------------------------------------------------------

@pytest.fixture
def semana():
    return pd.date_range("2026-04-01", periods=7 * 288, freq="5min", tz="UTC")


def test_demanda_sintetica(semana):
    a = load_or_build_demand(semana, 121000, 172000, seed=42)
    b = load_or_build_demand(semana, 121000, 172000, seed=42)
    assert a.mean() == pytest.approx(121000)
    assert a.max() == pytest.approx(172000)
    assert a.equals(b)  # misma semilla, mismo resultado (RNF-04)


def test_demanda_alineada_con_las_lecturas(semana):
    d = load_or_build_demand(semana, 121000, 172000)
    assert d.index.equals(semana)
    assert d.name == "demanda_kw"
    assert d.notna().all() and (d > 0).all()


def test_demanda_forma_del_perfil(semana):
    d = load_or_build_demand(semana, 121000, 172000, noise=0.0)
    local = d.index.tz_convert("America/Aruba")
    por_hora = d.groupby(local.hour).mean()
    assert por_hora.idxmax() in (19, 20)  # máximo a las 19-20 h locales
    assert por_hora.idxmin() in (3, 4)    # mínimo de madrugada
    assert d[local.day_of_week >= 5].mean() < d[local.day_of_week < 5].mean()  # fin de semana, menos


def test_demanda_real_si_existe(tmp_path, semana):
    ruta = tmp_path / "demanda.csv"
    horas = pd.date_range("2026-04-01", "2026-04-08", freq="h", tz="UTC")
    pd.DataFrame({"timestamp": horas, "demanda_kw": np.arange(len(horas), dtype=float)}).to_csv(ruta, index=False)
    d = load_or_build_demand(semana, 121000, 172000, real_path=ruta)
    assert d.iloc[0] == 0.0
    assert d.loc[pd.Timestamp("2026-04-01 00:30Z")] == pytest.approx(0.5)  # interpolada en el tiempo


def test_demanda_real_que_no_cubre_el_periodo_falla(tmp_path, semana):
    ruta = tmp_path / "demanda.csv"
    horas = pd.date_range("2026-04-01", "2026-04-03", freq="h", tz="UTC")
    pd.DataFrame({"timestamp": horas, "demanda_kw": 1.0}).to_csv(ruta, index=False)
    with pytest.raises(ValueError, match="no cubre"):
        load_or_build_demand(semana, 121000, 172000, real_path=ruta)


def test_sin_fichero_real_usa_la_sintetica(tmp_path, semana):
    d = load_or_build_demand(semana, 121000, 172000, real_path=tmp_path / "no_existe.csv")
    assert d.mean() == pytest.approx(121000)


def test_config_demanda_coincide_con_equipment_installed(cfg):
    ref = json.loads(cfg["paths"]["equipment"].read_text(encoding="utf-8"))
    ref = ref["equipment_installed_capacity"]["load_demand_2026"]
    assert cfg["demand"]["mean_kw"] == ref["average_mw"] * 1000
    assert cfg["demand"]["peak_kw"] == ref["max_peak_mw"] * 1000
