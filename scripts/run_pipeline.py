
"""HU-04: ejecuta el ETL completo con un único comando."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    scripts = [
        "run_etl.py",
        "run_integracion_5min.py",
    ]

    for script in scripts:
        print(f"\nEjecutando {script}...", flush=True)
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / script)],
            cwd=ROOT,
            check=True,
        )

    print("\nPipeline ETL completado correctamente.")


if __name__ == "__main__":
    main()
