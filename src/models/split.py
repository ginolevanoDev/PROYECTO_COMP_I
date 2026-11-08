
"""División cronológica para preparar los datos de Machine Learning."""

import pandas as pd


def dividir_train_test(df, proporcion_train=0.8, horizonte_min=15):
    """Divide por fechas, dejando una separación temporal entre conjuntos."""

    datos = df.sort_values(["timestamp", "station_id"]).copy()
    datos["timestamp"] = pd.to_datetime(datos["timestamp"], utc=True)

    fechas = datos["timestamp"].drop_duplicates().sort_values()

    if len(fechas) < 2:
        raise ValueError("No hay suficientes fechas para dividir los datos.")

    posicion = int(len(fechas) * proporcion_train)

    if not 0 < posicion < len(fechas):
        raise ValueError("La proporción de entrenamiento no es válida.")

    fecha_corte = fechas.iloc[posicion]

    # Evita que objetivos futuros del train alcancen el periodo test.
    train = datos[
        datos["timestamp"] < fecha_corte - pd.Timedelta(minutes=horizonte_min)
    ].copy()

    test = datos[
        datos["timestamp"] >= fecha_corte
    ].copy()

    if train.empty or test.empty:
        raise ValueError("La división ha generado un conjunto vacío.")

    if train["timestamp"].max() + pd.Timedelta(minutes=horizonte_min) >= test["timestamp"].min():
        raise AssertionError("No existe separación temporal suficiente.")

    return train, test
