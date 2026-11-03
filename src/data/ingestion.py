"""HU-17 / RF-01: carga de JSON y unión de lecturas con estaciones."""

from pathlib import Path

import pandas as pd

from src.utils.logger import get_logger

LOGGER = get_logger(__name__)


def cargar_estaciones_y_lecturas(
    ruta_lecturas: str | Path = "data/raw/train_aruba_lecturas.json",
    ruta_estaciones: str | Path = "data/raw/aruba_stations.json",
) -> pd.DataFrame:
    """Lee los JSON de lecturas y estaciones y los une con `unir_lecturas_estaciones`."""
    ruta_lecturas = Path(ruta_lecturas)
    ruta_estaciones = Path(ruta_estaciones)

    for ruta in (ruta_lecturas, ruta_estaciones):
        if not ruta.is_file():
            raise FileNotFoundError(f"No se ha encontrado el archivo: {ruta}")

    # convert_dates=False: el timestamp se parsea en cleaning.to_datetime_utc (HU-19)
    lecturas = pd.read_json(ruta_lecturas, convert_dates=False)
    estaciones = pd.read_json(ruta_estaciones, convert_dates=False)
    return unir_lecturas_estaciones(lecturas, estaciones)


def unir_lecturas_estaciones(lecturas: pd.DataFrame, estaciones: pd.DataFrame) -> pd.DataFrame:
    """Devuelve las lecturas enriquecidas con los datos de su estación.

    Se conservan todas las lecturas, incluso las que no tienen una estación
    conocida; estas últimas se registran en el log. No se limpian datos ni
    se convierten tipos, ya que esas operaciones corresponden a otras HU.
    """
    columnas_lecturas = {"id", "station_id", "timestamp"}
    columnas_estaciones = {"id", "name"}
    for nombre, tabla, columnas in (
        ("lecturas", lecturas, columnas_lecturas),
        ("estaciones", estaciones, columnas_estaciones),
    ):
        faltantes = columnas - set(tabla.columns)
        if faltantes:
            raise ValueError(
                f"Faltan columnas obligatorias en {nombre}: {sorted(faltantes)}"
            )

    if estaciones["id"].isna().any():
        raise ValueError("Hay estaciones sin identificador 'id'")
    if estaciones["id"].duplicated().any():
        raise ValueError("Hay identificadores 'id' duplicados en estaciones")

    # El id del registro de estación es la clave station_id de las lecturas.
    estaciones = estaciones.rename(columns={"id": "station_id"})
    resultado = lecturas.merge(
        estaciones,
        on="station_id",
        how="left",
        validate="many_to_one",
        indicator=True,
        suffixes=("", "_estacion"),
    )

    sin_estacion = resultado["_merge"] == "left_only"
    cantidad = int(sin_estacion.sum())
    if cantidad:
        ejemplos = resultado.loc[sin_estacion, "station_id"].drop_duplicates().head(5).tolist()
        LOGGER.warning(
            "Se encontraron %d lecturas sin estación asociada. station_id de ejemplo: %s",
            cantidad,
            ejemplos,
        )
    else:
        LOGGER.info("Todas las %d lecturas tienen estación asociada", len(resultado))

    return resultado.drop(columns=["_merge"])
