# PROYECTO COMP I — Aruba Energía

## Estado actual del proyecto

Se ha desarrollado y ejecutado un pipeline ETL para la preparación de datos meteorológicos y energéticos de Aruba, con el objetivo de obtener un dataset integrado, depurado y preparado para comenzar posteriormente el modelado mediante Machine Learning.

El proceso incluye la ingesta, limpieza, integración con datos meteorológicos ERA5, remuestreo temporal a 5 minutos, estimación de potencia eólica y generación del dataset procesado.

## 1. Trabajo realizado

### Ingesta y limpieza de datos

- Carga de datos de 12 estaciones meteorológicas.
- Procesamiento de 421.584 lecturas originales.
- Asociación de las lecturas con sus respectivas estaciones.
- Eliminación de 107.136 registros duplicados.
- Obtención de 314.448 registros depurados.
- Corrección de tipos de datos y normalización temporal.
- Identificación y tratamiento de valores fuera de rango y anomalías.
- Análisis de valores nulos y variables poco fiables.

### Integración meteorológica

Se utiliza ERA5 como fuente meteorológica adicional para enriquecer los datos de las estaciones.

- Incorporación de componentes del viento, temperatura y presión.
- Identificación del punto ERA5 más cercano a las estaciones.
- Selección del punto ERA5 situado en las coordenadas (12.5, -70.0).
- Interpolación de los datos horarios a intervalos de 5 minutos.
- Comprobación de la frecuencia temporal.
- Validación de correspondencia temporal y ausencia de duplicados tras la integración.

### Estimación de potencia eólica

Se han implementado funciones para estimar la generación del parque eólico a partir de los datos meteorológicos y de los parámetros de los aerogeneradores.

Las principales variables derivadas son:

- `ws_buje_ms`: velocidad del viento a altura de buje.
- `rho`: densidad del aire.
- `park_kw_curva`: potencia estimada utilizando la curva de los aerogeneradores.
- `park_kw`: potencia estimada calibrada del parque.
- `kw_por_turbina`: potencia estimada por aerogenerador.

La potencia calculada se encuentra entre 0 y 22.783,05 kW, dentro del límite de 30.000 kW establecido para el parque.

**Nota:** la potencia es una estimación basada en ERA5 y la curva de potencia. No representa una medición directa de producción eléctrica real.

### Demanda eléctrica

El pipeline contempla la integración de demanda eléctrica.

Cuando no existe una serie real disponible, se utiliza un perfil sintético parametrizado en `config/config.yaml`.

La demanda sintética se identifica mediante la variable `demanda_sintetica` y no debe confundirse con demanda eléctrica observada.

## 2. Pipeline ETL

El proyecto dispone de un comando para ejecutar el proceso completo de ingesta, limpieza e integración.

### Requisitos

- Python 3.11.
- Dependencias especificadas en `requirements.txt`.
- Archivos originales disponibles en las rutas configuradas.

### Instalación

Desde la raíz del repositorio:

```bash
python3.11 -m venv .venv311
source .venv311/bin/activate
python -m pip install -r requirements.txt
```

En Windows debe utilizarse el comando de activación correspondiente al entorno virtual.

### Ejecución completa

```bash
python scripts/run_pipeline.py
```

Este comando ejecuta:

1. `scripts/run_etl.py`: carga y limpieza de estaciones y lecturas.
2. `scripts/run_integracion_5min.py`: integración meteorológica, estimación de potencia y generación del dataset final.

Los resultados se guardan en:

```text
data/interim/clean.parquet
data/processed/dataset_5min.parquet
```

## 3. Dataset final

El dataset integrado generado contiene:

| Característica | Resultado |
|---|---|
| Registros | 314.448 |
| Estaciones | 12 |
| Frecuencia temporal | 5 minutos |
| Duplicados estación-fecha | 0 |
| Intervalos irregulares | 0 |
| Nulos en viento ERA5 y potencia | 0 |
| Potencia eólica estimada | 0–22.783,05 kW |

Se han conservado las lecturas meteorológicas y añadido variables relacionadas con ERA5, potencia eólica, demanda y tiempo.

El archivo resultante es:

`data/processed/dataset_5min.parquet`

## 4. Preparación para Machine Learning

Se ha implementado una función de división cronológica en:

`src/models/split.py`

La estrategia utiliza aproximadamente:

- 80 % de las fechas para entrenamiento.
- 20 % de las fechas para prueba.
- Separación temporal para un horizonte de predicción de 15 minutos.
- Conservación de las 12 estaciones en ambos conjuntos.

Resultados de la comprobación:

| Conjunto | Registros |
|---|---:|
| Entrenamiento | 251.520 |
| Prueba | 62.892 |

La función establece la división temporal. La construcción definitiva de la variable objetivo futura y el entrenamiento de modelos quedan para la fase de modelado.

Debe evitarse utilizar variables que calculan directamente `park_kw` como predictores de ese mismo objetivo sin justificarlo, para prevenir una evaluación engañosa.

## 5. EDA

El análisis exploratorio se encuentra en:

`notebooks/EDA_Aruba_Energia.ipynb`

Se han estudiado las dimensiones, tipos de datos, distribuciones, valores nulos, duplicados, valores anómalos y relaciones entre variables meteorológicas.

También se ha documentado la calidad de los datos, las limitaciones de algunas mediciones y la utilidad de fuentes meteorológicas externas.

## 6. Pruebas

El proyecto utiliza pytest para verificar las funcionalidades implementadas.

Para ejecutar las pruebas:

```bash
python -m pytest tests/ -v
```

**Última ejecución comprobada: 57 pruebas superadas.**

Las pruebas cubren la ingesta, limpieza, integración de fuentes, validaciones meteorológicas y cálculos de potencia.

## 7. Configuración

Los principales parámetros se encuentran en:

`config/config.yaml`

El archivo permite configurar las rutas, frecuencia temporal, umbrales de limpieza, parámetros meteorológicos, demanda y factor de calibración.

Los parámetros de las turbinas se mantienen en:

`config/turbinas.yaml`

## 8. GitHub y Git LFS

El repositorio se encuentra en:

https://github.com/ginolevanoDev/PROYECTO_COMP_I

Para clonar el proyecto:

```bash
git clone https://github.com/ginolevanoDev/PROYECTO_COMP_I.git
cd PROYECTO_COMP_I
git lfs install
git lfs pull
```

Git LFS se utiliza para gestionar archivos grandes configurados en `.gitattributes`.

Los archivos de entrada necesarios para ejecutar el pipeline deben estar disponibles en las rutas definidas en `config/config.yaml`.

No se deben subir entornos virtuales, credenciales ni archivos temporales.

Antes de compartir cambios:

```bash
git status
```

Los cambios deben integrarse mediante el flujo de ramas y Pull Requests establecido por el equipo.

## 9. Próximos pasos

El dataset se encuentra preparado para iniciar la fase posterior de modelado.

Las siguientes tareas previstas son:

- Completar las variables *lag* y las variables objetivo futuras.
- Entrenar modelos de regresión para predicción a 15 minutos.
- Evaluar los modelos mediante RMSE y R².
- Comparar los resultados con un modelo de persistencia.
- Evaluar las limitaciones derivadas del uso de potencia estimada y demanda sintética.
