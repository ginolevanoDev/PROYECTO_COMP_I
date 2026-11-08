"""HU-24 (RF-05): comprobación de la potencia del parque con el viento de ERA5.

Sobre el periodo de las lecturas:
- Guarda la serie horaria de potencia en data/interim/potencia_parque_horaria.parquet.
- Genera reports/figures/fig_potencia_parque_1.png: viento a buje frente a potencia, con la curva.
- Muestra el factor de capacidad con la curva y calibrado, frente al real de 2025.

Necesita data/interim/clean.parquet: ejecutar antes python scripts/run_etl.py.
Uso: python scripts/check_park_power.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src.data.power_estimation import hourly_park_power, park_power  # noqa: E402
from src.data.resampling import load_era5  # noqa: E402
from src.utils.config_loader import ROOT, load_config, load_turbine  # noqa: E402
from src.utils.logger import get_logger  # noqa: E402

log = get_logger("check_park_power")

FIGURA = ROOT / "reports" / "figures" / "fig_potencia_parque_1.png"

# Colores de la figura (paleta validada para daltonismo) y tinta de texto.
AZUL, NARANJA, GRIS, TEXTO, FONDO = "#2a78d6", "#eb6834", "#8a8984", "#52514e", "#fcfcfb"


def _pct(x):
    return f"{x:.1f}".replace(".", ",") + " %"


def cf_real(path, year):
    """Factor de capacidad real (%) de `year` en historical_figures.json."""
    filas = json.loads(Path(path).read_text(encoding="utf-8"))["historic_figures"]
    return next(f["capacity_percent"] for f in filas if f["year"] == year)


def figura(pot, turbine, factor, texto, ruta):
    """Viento a buje frente a potencia calibrada (puntos horarios) con la curva del parque."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        log.error("Falta matplotlib para la figura: pip install matplotlib")
        return

    v = np.linspace(0, 20, 401)
    curva = park_power(v, turbine) / 1000  # MW, a la densidad de referencia de la curva

    fig, ax = plt.subplots(figsize=(8, 5), dpi=150, facecolor=FONDO)
    ax.set_facecolor(FONDO)
    ax.plot(v, curva, color=GRIS, lw=1.5, ls="--", label="Curva de 10 turbinas, sin calibrar")
    ax.plot(v, curva * factor, color=NARANJA, lw=2, label=f"Curva calibrada (× {str(factor).replace('.', ',')})")
    ax.scatter(pot["ws_buje_ms"], pot["park_kw"] / 1000, s=10, color=AZUL, alpha=0.35, linewidths=0,
               label="park_kw horario (ERA5, con densidad)", zorder=3)

    ax.set_xlim(0, 20)
    ax.set_ylim(0, 35)  # margen sobre los 30 MW para el texto
    ax.set_xticks(range(0, 21, 2))
    ax.set_yticks(range(0, 31, 5))
    ax.set_xlabel("Viento a buje, 80 m (m/s)", color=TEXTO)
    ax.set_ylabel("Potencia del parque (MW)", color=TEXTO)
    ax.set_title("Viento a buje frente a potencia del parque Vader Piet", color="#0b0b0b", loc="left")
    ax.text(0.01, 0.97, texto, transform=ax.transAxes, va="top", ha="left", fontsize=9, color=TEXTO)
    ax.grid(color="#e6e5e1", lw=0.6)
    ax.tick_params(colors=TEXTO)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        ax.spines[lado].set_color("#c3c2b7")
    ax.legend(loc="lower right", frameon=False, fontsize=9, labelcolor=TEXTO)

    ruta.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(ruta, facecolor=FONDO)
    plt.close(fig)
    log.info("Figura guardada en %s", ruta.relative_to(ROOT))


def main():
    cfg = load_config()
    p = cfg["paths"]
    turbine = load_turbine()
    if not p["clean"].exists():
        log.error("Falta %s: ejecuta antes python scripts/run_etl.py", p["clean"].relative_to(ROOT))
        sys.exit(1)

    ts = pd.read_parquet(p["clean"], columns=["timestamp"])["timestamp"]
    lat, lon = cfg["era5"]["point"]
    factor = cfg["calibration"]["wind_cf_factor"]
    pot = hourly_park_power(load_era5(p["era5"], lat, lon, ts.min(), ts.max()), turbine, factor)

    capacidad = turbine["n_turbines"] * turbine["rated_kw"]
    cf_curva = 100 * pot["park_kw_curva"].mean() / capacidad
    cf_cal = 100 * pot["park_kw"].mean() / capacidad
    cf_2025 = cf_real(p["external"] / "historical_figures.json", 2025)
    log.info("RF-05: factor de capacidad del %s al %s: curva %s, calibrado %s (real 2025: %s)",
             pot.index.min(), pot.index.max(), _pct(cf_curva), _pct(cf_cal), _pct(cf_2025))
    log.info("RF-05: park_kw entre %.0f y %.0f kW, %d valores nulos", pot["park_kw"].min(), pot["park_kw"].max(),
             pot["park_kw"].isna().sum())

    serie = p["interim"] / "potencia_parque_horaria.parquet"
    serie.parent.mkdir(parents=True, exist_ok=True)
    pot.to_parquet(serie)
    log.info("Serie horaria guardada en %s: %d horas", serie.relative_to(ROOT), len(pot))

    texto = (f"ERA5 horario, {pot.index.min():%d/%m} a {pot.index.max():%d/%m/%Y} ({len(pot)} h)\n"
             f"Factor de capacidad: curva {_pct(cf_curva)}, calibrado {_pct(cf_cal)}, real 2025 {_pct(cf_2025)}")
    figura(pot, turbine, factor, texto, FIGURA)


if __name__ == "__main__":
    main()
