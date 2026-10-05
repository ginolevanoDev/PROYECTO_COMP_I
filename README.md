## Estado actual del proyecto

Actualmente se ha completado la primera fase de análisis exploratorio
y preparación de los datos energéticos de Aruba.

### Trabajo realizado

- Carga de los datos de las 12 estaciones meteorológicas.
- Análisis inicial de 421.584 registros.
- Detección y eliminación de registros duplicados.
- Conversión y normalización de variables meteorológicas.
- Comprobación de la frecuencia temporal de los datos (5 minutos).
- Análisis exploratorio de temperatura, humedad, viento, presión,
  precipitación, visibilidad e índice UV.
- Integración de datos meteorológicos ERA5.
- Asociación de estaciones con los puntos ERA5 más cercanos.
- Primera estimación del viento a altura de buje.
- Primera estimación de la potencia del parque eólico.
- Implementación de un modelo de persistencia como línea base
  para la predicción a t+15 minutos.

El análisis se encuentra en:

`EDA_Aruba_Energia.ipynb`

### Próximos pasos

Crear las Lag Features, integrar los datos de demanda eléctrica,
construir el dataset de entrenamiento, entrenar los modelos de
regresión y evaluar su rendimiento mediante RMSE(ROOT MEAN SQUARED ERROR) y R^2.
