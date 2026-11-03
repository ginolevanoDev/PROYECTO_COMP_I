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
