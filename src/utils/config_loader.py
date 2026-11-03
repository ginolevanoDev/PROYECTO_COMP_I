"""Carga de la configuración del proyecto (RNF-08)."""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def load_config(path=None):
    """Devuelve config/config.yaml como dict, con `paths` resueltas a Path absolutas."""
    path = Path(path) if path else ROOT / "config" / "config.yaml"
    cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    cfg["paths"] = {k: ROOT / v for k, v in cfg.get("paths", {}).items()}
    return cfg


def load_turbine(path=None):
    """Devuelve config/turbinas.yaml como dict. Falla si la curva de potencia no es válida (HU-23)."""
    path = Path(path) if path else ROOT / "config" / "turbinas.yaml"
    turbine = yaml.safe_load(path.read_text(encoding="utf-8"))
    ws, kw = turbine["curve"]["ws_ms"], turbine["curve"]["kw"]
    if len(ws) != len(kw):
        raise ValueError(f"Curva de potencia inválida: {len(ws)} velocidades y {len(kw)} potencias")
    if any(b <= a for a, b in zip(ws, ws[1:])):
        raise ValueError("Curva de potencia inválida: las velocidades deben ser crecientes")
    return turbine
