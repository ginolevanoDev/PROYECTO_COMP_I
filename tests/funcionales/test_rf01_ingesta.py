"""Pruebas de aceptación de HU-17 / RF-01."""

import json
import logging

import pytest

from src.data.ingestion import cargar_estaciones_y_lecturas


def guardar_json(ruta, datos):
    ruta.write_text(json.dumps(datos), encoding="utf-8")
    return ruta


def test_asocia_lecturas_y_estaciones(tmp_path):
    lecturas = guardar_json(tmp_path / "lecturas.json", [
        {"id": "L1", "station_id": "S1", "timestamp": "2026-04-01T00:00:00Z", "wind_speed_kmh": 20},
        {"id": "L2", "station_id": "S1", "timestamp": "2026-04-01T00:05:00Z", "wind_speed_kmh": 21},
    ])
    estaciones = guardar_json(tmp_path / "estaciones.json", [
        {"id": "S1", "name": "Alto Vista", "latitude": 12.59},
    ])

    resultado = cargar_estaciones_y_lecturas(lecturas, estaciones)

    assert len(resultado) == 2
    assert resultado["name"].tolist() == ["Alto Vista", "Alto Vista"]
    assert resultado["latitude"].tolist() == [12.59, 12.59]
    assert resultado["id"].tolist() == ["L1", "L2"]


def test_registra_lecturas_sin_estacion(tmp_path, caplog):
    lecturas = guardar_json(tmp_path / "lecturas.json", [
        {"id": "L1", "station_id": "DESCONOCIDA", "timestamp": "2026-04-01T00:00:00Z"},
    ])
    estaciones = guardar_json(tmp_path / "estaciones.json", [
        {"id": "S1", "name": "Alto Vista"},
    ])

    with caplog.at_level(logging.WARNING):
        resultado = cargar_estaciones_y_lecturas(lecturas, estaciones)

    assert len(resultado) == 1  # Nunca se pierde una lectura sin estación
    assert resultado.loc[0, "station_id"] == "DESCONOCIDA"
    assert "1 lecturas sin estación" in caplog.text
    assert "DESCONOCIDA" in caplog.text


def test_rechaza_ids_de_estacion_duplicados(tmp_path):
    lecturas = guardar_json(tmp_path / "lecturas.json", [
        {"id": "L1", "station_id": "S1", "timestamp": "2026-04-01T00:00:00Z"},
    ])
    estaciones = guardar_json(tmp_path / "estaciones.json", [
        {"id": "S1", "name": "Estación A"},
        {"id": "S1", "name": "Estación B"},
    ])

    with pytest.raises(ValueError, match="duplicados"):
        cargar_estaciones_y_lecturas(lecturas, estaciones)


def test_rechaza_archivo_con_columnas_obligatorias_ausentes(tmp_path):
    lecturas = guardar_json(tmp_path / "lecturas.json", [
        {"id": "L1", "timestamp": "2026-04-01T00:00:00Z"},
    ])
    estaciones = guardar_json(tmp_path / "estaciones.json", [
        {"id": "S1", "name": "Estación A"},
    ])

    with pytest.raises(ValueError, match="station_id"):
        cargar_estaciones_y_lecturas(lecturas, estaciones)