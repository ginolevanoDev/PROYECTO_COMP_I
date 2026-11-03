import numpy as np
import pandas as pd

from src.data.cleaning import KEY, clean_readings, drop_duplicates, flag_out_of_range, treat_outliers
from src.data.ingestion import unir_lecturas_estaciones


def _limpio(readings, stations, cfg):
    return clean_readings(unir_lecturas_estaciones(readings, stations), cfg)


def test_sin_duplicados_y_ordenado(readings, stations, cfg):
    df = _limpio(readings, stations, cfg)
    assert not df.duplicated(KEY).any()
    assert len(df) == 12
    assert df.equals(df.sort_values(KEY).reset_index(drop=True))


def test_timestamp_utc_con_correccion_horaria(readings, stations, cfg):
    df = _limpio(readings, stations, cfg)
    assert str(df["timestamp"].dt.tz) == "UTC"
    offset = pd.Timedelta(hours=cfg["time"]["station_utc_offset_h"])
    assert df["timestamp"].min() == pd.Timestamp("2026-04-01T00:00:00Z") + offset


def test_tipos_numericos(readings, stations, cfg):
    readings["pressure_hpa"] = readings["pressure_hpa"].astype(str)
    df = _limpio(readings, stations, cfg)
    assert all(df[c].dtype == "float64" for c in cfg["validation_ranges"])


def test_duplicados_contradictorios_se_promedian():
    df = pd.DataFrame({"station_id": ["A", "A"], "timestamp": [pd.Timestamp("2026-04-01", tz="UTC")] * 2,
                       "wind_speed_kmh": [10.0, 20.0]})
    assert drop_duplicates(df, ["wind_speed_kmh"])["wind_speed_kmh"].tolist() == [15.0]


def test_fuera_de_rango_se_anula_y_marca():
    df = pd.DataFrame({"humidity_pct": [50.0, 120.0], "uv_index": [3.0, -1.0]})
    out = flag_out_of_range(df, {"humidity_pct": [0, 100], "uv_index": [0, 16]})
    assert out["humidity_pct"].isna().tolist() == [False, True]
    assert out["qc_flags"].tolist() == [0, 2]


def test_outlier_se_marca_e_interpola():
    s = [20.0, 21.0, 20.0, 21.0, 500.0, 21.0, 20.0, 21.0]
    df = pd.DataFrame({"station_id": "A", "wind_speed_kmh": s})
    out = treat_outliers(df, ["wind_speed_kmh"], k=3.0, max_steps=3)
    assert out.loc[4, "wind_speed_kmh"] == 21.0
    assert out.loc[4, "qc_flags"] == 1
    assert not out["qc_event"].any()


def test_evento_sostenido_se_conserva():
    s = [20.0, 21.0] * 10 + [50.0] * 6 + [20.0, 21.0] * 10
    df = pd.DataFrame({"station_id": "A", "wind_speed_kmh": s})
    out = treat_outliers(df, ["wind_speed_kmh"], k=3.0, max_steps=3)
    assert out["wind_speed_kmh"].tolist() == s
    assert out["qc_event"].sum() == 6
    assert out["qc_flags"].sum() == 0


def test_huecos_largos_no_se_inventan():
    s = [20.0] + [np.nan] * 5 + [20.0]
    df = pd.DataFrame({"station_id": "A", "wind_speed_kmh": s})
    out = treat_outliers(df, ["wind_speed_kmh"], k=3.0, max_steps=3)
    assert out["wind_speed_kmh"].isna().sum() == 5
