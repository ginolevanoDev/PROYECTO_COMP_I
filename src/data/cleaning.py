
"""HU-19: Corrección de tipos y formatos de datos."""

import logging
import pandas as pd

# Configuración del sistema de registro de errores
LOGGER = logging.getLogger(__name__)


def corregir_tipos_y_formatos(datos: pd.DataFrame) -> pd.DataFrame:
    """Corrige los formatos del dataset sin modificar el original."""

    # Comprobamos que existe la columna timestamp
    if "timestamp" not in datos.columns:
        raise ValueError("No existe la columna timestamp")

    # Creamos una copia para conservar los datos originales
    resultado = datos.copy()

    # Convertimos las fechas al formato datetime (UTC)
    resultado["timestamp"] = pd.to_datetime(
        resultado["timestamp"],
        errors="coerce",
        utc=True
    )

    # Detectamos fechas que no se han podido convertir
    fechas_invalidas = resultado["timestamp"].isna().sum()

    if fechas_invalidas > 0:
        LOGGER.warning(
            "Se encontraron %d fechas invalidas",
            fechas_invalidas
        )

    # Columnas meteorológicas que deben ser numéricas
    columnas_numericas = [
        "temperature_c",
        "humidity_pct",
        "wind_speed_kmh",
        "wind_direction_deg",
        "pressure_hpa",
        "precipitation_mm",
        "visibility_km",
        "uv_index"
    ]

    # Comprobamos que existen todas las columnas
    for columna in columnas_numericas:
        if columna not in resultado.columns:
            raise ValueError(f"No existe la columna {columna}")

        # Guardamos los valores originales
        valores_originales = resultado[columna].copy()

        # Convertimos los valores a float
        resultado[columna] = pd.to_numeric(
            resultado[columna],
            errors="coerce"
        ).astype(float)

        # Detectamos valores que no se pudieron convertir
        valores_invalidos = (
            valores_originales.notna() &
            resultado[columna].isna()
        ).sum()

        if valores_invalidos > 0:
            LOGGER.warning(
                "Se encontraron %d valores invalidos en %s",
                valores_invalidos,
                columna
            )

    return resultado
