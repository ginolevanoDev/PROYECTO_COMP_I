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
