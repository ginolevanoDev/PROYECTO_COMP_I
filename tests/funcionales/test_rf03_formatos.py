
"""Pruebas de la HU-19: corrección de tipos y formatos."""

import pandas as pd
import pytest

from src.data.cleaning import corregir_tipos_y_formatos


@pytest.fixture
def datos_prueba():
    """Dataset de ejemplo para las pruebas."""
    return pd.DataFrame({
        "timestamp": ["2026-03-31T22:00:00Z"],
        "temperature_c": ["30.5"],
        "humidity_pct": ["71.6"],
        "wind_speed_kmh": ["21.2"],
        "wind_direction_deg": ["45.3"],
        "pressure_hpa": ["1016"],
        "precipitation_mm": ["0"],
        "visibility_km": ["11.7"],
        "uv_index": ["0"]
    })


# PRUEBA 1: Conversión de fechas
def test_conversion_fechas(datos_prueba):
    resultado = corregir_tipos_y_formatos(datos_prueba)

    assert pd.api.types.is_datetime64_any_dtype(
        resultado["timestamp"]
    )
    assert str(resultado["timestamp"].dt.tz) == "UTC"


# PRUEBA 2: Conversión de variables numéricas
def test_conversion_numerica(datos_prueba):
    resultado = corregir_tipos_y_formatos(datos_prueba)

    columnas = [
        "temperature_c",
        "humidity_pct",
        "wind_speed_kmh",
        "wind_direction_deg",
        "pressure_hpa",
        "precipitation_mm",
        "visibility_km",
        "uv_index"
    ]

    for columna in columnas:
        assert pd.api.types.is_float_dtype(
            resultado[columna]
        )


# PRUEBA 3: Detección de valores incorrectos
def test_valores_invalidos(datos_prueba, caplog):
    datos_prueba.loc[0, "temperature_c"] = "error"
    datos_prueba.loc[0, "timestamp"] = "fecha_invalida"

    with caplog.at_level("WARNING"):
        resultado = corregir_tipos_y_formatos(datos_prueba)

    assert pd.isna(resultado.loc[0, "temperature_c"])
    assert pd.isna(resultado.loc[0, "timestamp"])

    assert "fechas invalidas" in caplog.text
    assert "valores invalidos" in caplog.text


# PRUEBA 4: Detección de columnas ausentes
def test_columnas_obligatorias(datos_prueba):
    datos_incompletos = datos_prueba.drop(
        columns=["temperature_c"]
    )

    with pytest.raises(ValueError):
        corregir_tipos_y_formatos(datos_incompletos)
