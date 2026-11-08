"""HU-23 / RF-05: del viento a buje a la potencia de las turbinas del parque.

Todas las funciones aceptan escalares, arrays o Series (y devuelven una Series con el mismo índice).
"""
import numpy as np
import pandas as pd

R_AIRE_SECO = 287.05  # J/(kg·K)


def _like(x, values):
    return pd.Series(values, index=x.index, name=x.name) if isinstance(x, pd.Series) else values


def wind_at_hub(ws, h_meas, h_hub, alpha):
    """Extrapola el viento medido a `h_meas` hasta `h_hub` con la ley potencial de exponente `alpha`."""
    return ws * (h_hub / h_meas) ** alpha


def air_density(t_c, p_hpa):
    """Densidad del aire seco (kg/m³). Usar t2m y sp de ERA5: la temperatura de las estaciones no es fiable (EDA §8)."""
    return p_hpa * 100 / (R_AIRE_SECO * (t_c + 273.15))


def turbine_power(ws, turbine, rho=None):
    """Potencia de una turbina (kW) con la curva de `turbine` (ver `load_turbine`).

    Con `rho`, el viento se corrige antes a la densidad de la curva (IEC 61400-12-1):
    ws · (rho / rho_ref)^(1/3). Da 0 por debajo de cut_in y a partir de cut_out, y NaN si el viento es NaN.
    """
    v = np.asarray(ws, dtype="float64")
    if rho is not None:
        v = v * (np.asarray(rho, dtype="float64") / turbine["rho_ref"]) ** (1 / 3)
    curve = turbine["curve"]
    kw = np.interp(v, curve["ws_ms"], curve["kw"])
    kw = np.where((v < turbine["cut_in_ms"]) | (v >= turbine["cut_out_ms"]), 0.0, kw)
    return _like(ws, kw)


def park_power(ws, turbine, rho=None):
    """Potencia del parque (kW): n_turbines × potencia de una turbina."""
    return turbine["n_turbines"] * turbine_power(ws, turbine, rho)


# Altura (m) del viento de ERA5 que se lleva a buje.
ERA5_ALTURA_M = 100


def add_park_power(df, turbine, factor):
    """Añade al dataset el viento a buje, la densidad y la potencia del parque (HU-24, RF-05).

    `df` necesita `ws100_ms` (viento de ERA5 a 100 m, en m/s), `alpha`, `t2m_c` (°C) y `sp_hpa` (hPa),
    como los deja la rejilla de 5 minutos de HU-22. Devuelve una copia con:
    - `ws_buje_ms`: viento a buje (80 m) con la ley potencial y el `alpha` de ERA5.
    - `rho`: densidad del aire (kg/m³).
    - `park_kw_curva`: potencia de las 10 turbinas con la curva, sin calibrar (0 a 30.000 kW).
    - `park_kw`: potencia calibrada, `park_kw_curva` x `factor`. Es la variable a predecir.
    - `kw_por_turbina`: `park_kw` / n_turbines, la que compara la alerta de RF-13 con 500 kW.
    `factor` es `calibration.wind_cf_factor` de config.yaml.
    """
    if not 0 < factor <= 1:
        raise ValueError(f"El factor de calibración debe estar entre 0 y 1, no {factor}")
    df = df.copy()
    df["ws_buje_ms"] = wind_at_hub(df["ws100_ms"], ERA5_ALTURA_M, turbine["hub_height_m"], df["alpha"])
    df["rho"] = air_density(df["t2m_c"], df["sp_hpa"])
    df["park_kw_curva"] = park_power(df["ws_buje_ms"], turbine, df["rho"])
    df["park_kw"] = df["park_kw_curva"] * factor
    df["kw_por_turbina"] = df["park_kw"] / turbine["n_turbines"]
    return df


def hourly_park_power(era, turbine, factor):
    """Potencia horaria del parque a partir de la salida de `load_era5` (HU-21), sin pasar a 5 minutos.

    Sirve para comprobar la curva y la calibración sobre el ERA5 original
    (scripts/check_park_power.py). El dataset de 5 minutos usa `add_park_power` sobre la rejilla de HU-22.
    """
    entrada = pd.DataFrame({"ws100_ms": np.hypot(era["u100"], era["v100"]), "alpha": era["alpha"],
                            "t2m_c": era["t2m_C"], "sp_hpa": era["sp_hPa"]}, index=era.index)
    return add_park_power(entrada, turbine, factor)
