# Plan: completar el Sistema de Predicción y Despacho Energético (Aruba)

## Contexto

El anteproyecto pide un sistema que prediga la potencia del parque eólico Vader Piet (10 × 3 MW) a t+15 min, la compare con la demanda y emita alertas de despacho. Los entregables son `modelo_aruba_energia.pkl`, `predict.py` y una app Streamlit, además de la memoria (RF-01…RF-19, RNF-01…RNF-12, RD-01…RD-04).

**Estado actual del repo (hoy, 14/10/2026):**
- El scaffold está creado pero **todos los `.py`, `config/*.yaml`, `requirements.txt`, docs y el `.pkl` tienen 0 bytes**.
- El trabajo real está en dos notebooks de Colab:
  - [notebooks/EDA_Aruba_Energia.ipynb](notebooks/EDA_Aruba_Energia.ipynb): carga, duplicados, ERA5, curva genérica y persistencia con RMSE 286,9 kW y R² 0,994.
  - [requisitos/funcionales/RF_01_ingesta_de_datos_de_estaciones.ipynb](requisitos/funcionales/RF_01_ingesta_de_datos_de_estaciones.ipynb): merge `station_id` ↔ `id`.
- Datos presentes:
  - `data/raw/aruba_stations.json`: 12 estaciones.
  - `data/external/era5_aruba.csv`: 421 MB, horario de 1940 a 2026-09, 9 puntos de rejilla, columnas `u100, v100, ssrd`.
- **Faltan**:
  - El fichero de lecturas en `data/raw/` (está en el `.gitignore` como `aruba_readings_20260924.json`).
  - Los datos de demanda.
  - La ficha técnica de la turbina.
- La reorganización de carpetas **no está commiteada**. Git muestra los ficheros antiguos como borrados y el scaffold nuevo como no rastreado.

Según el cronograma estamos al final de la tarea 3.1. El **hito ETL es el 6/11 (límite 8/11)**, el Check 1 el 16/11, el Check modelo el 15/12 y la entrega final el 12/01/27.

El objetivo de este plan es pasar la lógica de los notebooks a módulos `src/` reutilizables (RNF-07) y completar el resto del pipeline en el orden del cronograma.

---

## Fase 0: Higiene del repositorio (inmediato, Iván)

1. **Commit de la reorganización.**
   - Hacer `git add` del scaffold y confirmar los borrados de los ficheros antiguos.
   - Mover `era5_aruba.csv` a LFS en su nueva ruta. `.gitattributes` ya tiene `*.csv filter=lfs`.
   - Actualizar el README, que todavía apunta a `DATA/era5_aruba.csv`.
2. **`.gitignore`**: añadir `__pycache__/`, `.env`, `.venv/`, `data/interim/`, `data/processed/`, `data/raw/*readings*.json`, `data/raw/*lecturas*.json`, `.ipynb_checkpoints/` y `.pytest_cache/`.
   - El `.pkl` **sí** se versiona, porque RF-12 y RD-04 lo exigen.
3. **`requirements.txt` con versiones fijadas** (RNF-09 y RNF-10), por ejemplo:
   - `pandas==2.2.*`, `numpy`, `scikit-learn==1.5.*`, `lightgbm` o `xgboost`, `joblib`, `pyyaml`, `streamlit`, `plotly`, `pyarrow`, `python-dotenv`, `pytest`, `cdsapi` (opcional).
   - Al cerrar el entorno, ejecutar `pip freeze` para fijar versiones exactas.
4. **`.env.example`** (RNF-11): `CDSAPI_KEY=`, `CDSAPI_URL=`, `DATA_READINGS_PATH=`.
5. **`LICENSE`**: MIT, con los nombres del grupo.
6. **`data/README.md`**: indicar de dónde obtener cada fichero, sobre todo las lecturas, que no se versionan, y dónde colocarlo.

## Fase 1: Configuración y utilidades (RNF-07, RNF-08)

- **`config/config.yaml`**, la fuente única de parámetros:
  - `paths`: raw, external, interim, processed, model `modelo_aruba_energia.pkl`.
  - `time`: `freq: 5min`, `tz: America/Aruba`, `horizon_min: 15`, `lags_min: [5,10,15,20]`, `windows: [3,6,12]`.
  - `physics`: `station_height_m: 10`, `hub_height_m: 100` (o el valor de la ficha), `shear_alpha: 1/7`, `n_turbines: 10`, `rated_kw_per_turbine: 3000`.
  - `thresholds`: `alert_kw: 500` (RF-13), `p15_kw` (lo calcula RF-08 y se guarda aquí o en `processed/umbrales.json`), `pct_moderate: 0.40`, `pct_critical: 0.15`, `solar_min_wm2: 200`.
  - `split`: `train_frac: 0.8`.
  - `seed: 42` (RNF-04).
  - `validation_ranges`: rangos físicos de cada variable, reutilizando el dict `RANGOS` del EDA.
- **`config/turbinas.yaml`**: modelo de turbina, `cut_in`, `rated`, `cut_out`, altura de buje y la curva (`ws_pts`, `kw_pts`).
  - Usar la ficha del fabricante. Para Vader Piet (Vestas V90-3.0 MW) son: cut-in 3,5, nominal unos 15, corte 25 m/s y buje de 80 m.
  - **Verificarlo con la fuente** (WEB Aruba o The Wind Power) y citarlo en `docs/design/inventario_fuentes.md`.
  - Si no se confirma, usar provisionalmente la curva genérica del EDA.
- **`src/utils/config_loader.py`**: `load_config()` y `load_turbine()`, que devuelven dicts y resuelven las rutas respecto a la raíz del repo con `pathlib`.
- **`src/utils/logger.py`**: `get_logger(name)` con `logging` estándar.

## Fase 2: ETL (tareas 3.1–3.5, hito 6/11). Miguel, José, Javier, Iván

La lógica se porta desde los notebooks, no se reescribe.

| Módulo | Funciones | Requisito | Origen en notebooks |
|---|---|---|---|
| `src/data/ingestion.py` | `load_stations()`, `load_readings(path)`, `merge_readings_stations()`: left-merge `station_id`→`id`, verifica 0 huérfanas | RF-01 | Notebook RF-01 |
| `src/data/cleaning.py` | `to_datetime_utc()`, `sort_series()`, `drop_duplicates()` por (station_id, timestamp), `fix_types()`, `flag_out_of_range()` con los rangos de config, `treat_outliers()` (IQR → NaN → interpolación corta), `filter_active()` | RF-03 | EDA §2–4 |
| `src/data/resampling.py` | `resample_station(df, '5min')`, `load_era5(period, points)` (lectura por chunks filtrando periodo y punto (12.5, -70.0), cálculo de `ws100 = hypot(u100,v100)`, `wdir100` y `ssrd_wm2 = ssrd/3600`), `era5_to_5min()` con interpolación temporal, `align_sources()` | RF-02, RF-04 | EDA §6–7 |
| `src/data/power_estimation.py` | `wind_at_hub(ws, h_meas, h_hub, alpha)`, `turbine_power(ws, curve)` con `np.interp` y corte, `park_power()` (× n_turbinas), `hub_wind_corrected()` (ERA5 corregido por bias con la estación, o extrapolación con la ley potencial) | RF-05 | EDA §8 |
| `src/data/demand.py` (nuevo) | `load_or_build_demand()` | RF-02 | — |
| `scripts/run_etl.py` | Orquesta todo lo anterior y escribe `data/interim/clean.parquet` y `data/processed/dataset_5min.parquet` | — | — |
| `scripts/download_external_data.py` | Descarga ERA5 con `cdsapi`, usando la clave de `.env`, solo para el periodo de las lecturas. Así nadie depende del CSV de 421 MB | RNF-11 | — |

Indicaciones clave:
- **Recorte de ERA5**: el CSV abarca 1940–2026. En la ETL quedarse solo con el periodo de las lecturas y guardar un parquet pequeño en `data/interim/era5_periodo.parquet`, para cumplir RNF-02 (8 GB de RAM).
- **Viento a buje**: el EDA muestra una correlación de solo 0,01–0,15 entre la estación y ERA5. Recomendación:
  - Usar como serie principal el **viento de las estaciones extrapolado a buje** (media de las estaciones cercanas al parque, como Vader Piet, en la costa sureste). Tiene la dinámica de 5 min que se necesita para t+15.
  - Usar ERA5 como **variable explicativa** (ws100, ssrd), no como fuente de la potencia.
  - Documentar esta decisión en la memoria.
- **Demanda** (no existe en el repo): construir un perfil sintético calibrado con cifras públicas.
  - Usar el consumo anual de WEB Aruba / IRENA (en torno a 900–1000 GWh/año, con pico de unos 130–140 MW; **verificar y citar**).
  - Forma diaria y semanal más un término de temperatura (`temperature_c` de las estaciones) y ruido con semilla.
  - Declararlo explícitamente como supuesto en el Alcance. Si el profesorado aporta datos reales, `load_or_build_demand()` los cargará en su lugar.
- **Escala parque frente a umbral de 500 kW**: con una potencia media de unos 23 MW, el umbral de 500 kW de RF-13 casi nunca salta (0,0 % en el EDA).
  - Mantener `alert_kw: 500` **literal** para RF-13, porque lo exige el enunciado.
  - Las alertas por niveles de RF-08 y RF-18 (P15 y % de capacidad nominal) dan la señal útil.
  - Justificarlo en la memoria. **Confirmar con la profesora** si los 500 kW se refieren a la potencia por turbina.

**Entregable del hito ETL**: `dataset_5min.parquet`, un notebook `notebooks/01_ETL_resultados.ipynb` que **importa `src/`** y muestra los resultados, `docs/design/arquitectura.md` (diagrama del flujo de datos) y `docs/design/inventario_fuentes.md`.

## Fase 3: Características, objetivos y umbrales (tareas 4.1–4.2). Javier, José, Miguel

- **`src/feature/lag_features.py`**: `add_lags(df, cols, lags_min, freq)` se aplica con `groupby('station_id')` (RF-06 exige que sea por estación) para la potencia, el viento y la demanda. `add_rolling(df, cols, windows)` calcula media, desviación y variación (diff) con `shift(1)` para **no filtrar el futuro**. `add_time_features()` añade hora sin/cos, día de la semana y fin de semana.
- **`src/feature/targets.py`**: `add_targets(df, horizons=[5,10,15,20])` desplaza la potencia con `shift(-h/5)` por grupo (RF-07). El objetivo principal es `power_t+15`. Después hace `dropna`.
- **`src/feature/thresholds.py`**: `compute_thresholds(train_df)` usa **solo el train** para evitar fuga de información y devuelve P15, los niveles por % del nominal y `overload = demand_pred > renewable_available`. Escribe `data/processed/umbrales.json` (RF-08). `classify(power_pred, demand, ssrd, thr)` devuelve `{nivel, texto, icono, color}` con los niveles *estable / moderado (solar o baterías si ssrd ≥ solar_min) / crítico térmico / sobrecarga*. Esta función **la comparten `predict.py` y la app**.
- **Agregación**: entrenar sobre una **serie agregada del parque** (una fila por timestamp, con las columnas de las estaciones relevantes como features) o con station_id como feature. Recomendación: la serie agregada, porque la variable a predecir es la potencia del parque y no la de cada estación. Las lags por estación se pivotan a columnas.

## Fase 4: Modelado (tareas 4.3–4.5, Check modelo 15/12). Javier, José, Miguel

- **`src/models/split.py`**: `chronological_split(df, 0.8)` sin barajar (RF-09, RD-03). Para el ajuste de hiperparámetros, opcionalmente `TimeSeriesSplit` sobre el train.
- **`src/models/train.py`**: `PersistenceModel` (predice `power_t`), una clase sklearn-compatible con `fit`/`predict`. Además, al menos dos regresores (RF-10): `Ridge`/`LinearRegression`, `RandomForestRegressor(random_state=seed)` y `LightGBM`/`HistGradientBoostingRegressor`. Todos se entrenan dentro de un `Pipeline` con el escalado para que el `.pkl` sea autocontenido.
  - **Clave**: la persistencia tiene R² 0,994, así que es difícil de superar. Hay que entrenar también una variante que **prediga el incremento** `power_t+15 − power_t` y reconstruya después la potencia, y evaluar aparte en **eventos de rampa** (caídas mayores del X % en 15 min). Ahí es donde el modelo debe aportar sobre la persistencia (OE-06).
- **`src/models/evaluate.py`**: `evaluate(models, X_test, y_test)` devuelve una tabla de RMSE, MAE y R², más el RMSE en rampas. Incluye `plot_pred_vs_real()` y `save_report()`, que escribe `docs/resultados/metricas.csv` y figuras en `reports/figures/` (RF-11).
- **`src/models/export.py`**: `export_model(model, feature_names, thresholds, meta)` guarda con `joblib` un **dict** `{model, features, thresholds, horizon, versions:{sklearn, pandas}, trained_at}` en la raíz como `modelo_aruba_energia.pkl` (RF-12, RNF-10). `load_model()` valida claves y versiones y lanza un error claro (RNF-03).
- **`scripts/run_training.py`** y **`src/pipeline.py`**: el comando completo `python -m src.pipeline` encadena ETL, features, split, train, evaluate y export. Debe ser reproducible con la semilla fija (RNF-04).

## Fase 5: Aplicación (tareas 5.1–5.4). Iván, Javier, José

- **`predict.py`** (RF-13):
  - Uso: `python predict.py --input registro.json` (o `--csv`, o `--values k=v ...`).
  - Carga el `.pkl` con `load_model()`, construye el vector en el orden de `features`, predice t+15, imprime la potencia y luego exactamente `[ALERTA] Despacho Térmico/Solar requerido en 15m` si es menor de 500 kW, u `[OK] Operación Estable` en otro caso. También imprime el nivel de `classify()`.
  - Gestiona con `try/except` la falta del modelo y las entradas inválidas (RNF-03).
  - Mide el tiempo de inferencia, que debe ser menor de 2 s (RNF-01).
  - Incluir `data/samples/registro_ejemplo.json` y `.csv`.
- **`app.py`** (Streamlit; RF-14 a RF-19):
  - Cargar el modelo con `@st.cache_resource` desde una **ruta fija de config**. Sin `file_uploader` para `.pkl` (RNF-12). Si falta, mostrar `st.error` y no caerse (RNF-03).
  - **`src/app/input_handler.py`**: formulario manual con `st.form` (valores por defecto de ejemplo) y carga de JSON/CSV que acepta un registro o un histórico corto, a partir del cual se calculan los lags (RF-15).
  - **`src/app/validation.py`**: `validate_record(rec, ranges)` comprueba campos completos, tipos y rangos físicos de config, y devuelve una lista de errores legibles (RF-16).
  - **`src/app/alerts.py`**: `render_alert(level)` muestra **color, texto e icono** (RNF-06), con `st.success`, `st.warning` o `st.error` más emoji y la etiqueta del nivel (RF-18).
  - **`src/app/charts.py`**: Plotly con la potencia reciente y el punto t+15, más las líneas de umbral (RF-19).
  - Métricas con `st.metric` para la potencia prevista, la demanda y el déficit (RF-17).
  - Un texto de ayuda breve para operadores sin conocimientos de ML (RNF-05).

## Fase 6: Pruebas y cierre (tareas 6.1–6.4)

- **`tests/conftest.py`**: fixtures con un mini-dataset sintético de unas 200 filas en `tests/fixtures/`.
- **`tests/funcionales/`**: un test por RF, con el nombre `test_rf01_ingesta.py`, etc. Por ejemplo:
  - El merge no deja huérfanas.
  - Hay duplicados antes y 0 después.
  - La frecuencia es de 5 min.
  - La curva da 0 por debajo del cut-in y por encima del corte, y el nominal en la meseta.
  - Las lags no contienen el futuro.
  - El split es cronológico (max train < min test).
  - El `.pkl` existe y carga.
  - La salida de `predict.py` contiene el mensaje exacto (con `subprocess`).
  - La validación rechaza valores fuera de rango.
- **`tests/no_funcionales/`**:
  - Tiempo de predicción menor de 2 s (RNF-01).
  - Pico de memoria del entrenamiento con `tracemalloc`/`psutil` (RNF-02).
  - Dos entrenamientos dan las mismas métricas (RNF-04).
  - El modelo ausente produce un mensaje y no una excepción (RNF-03).
  - `grep` de secretos (RNF-11).
- **`requisitos/matriz_trazabilidad.md`**: tabla RF/RNF → módulo → test → estado. Corregir también la incoherencia del anteproyecto, que cita RNF-13 y RNF-14 cuando solo existen hasta RNF-12.
- **Docs**:
  - `docs/gestion/plan_de_trabajo.md` y actas semanales en `docs/gestion/actas/`.
  - Entregas en `docs/entregas/`.
  - Informes de pruebas en `docs/pruebas/`.
  - Exportar el WBS y el Gantt reales (ahora son ficheros de 0 bytes).
- Memoria final y presentación.

---

## Checklist de requisitos por fase

Cada casilla se marca solo cuando su test de `tests/` pasa. El mismo estado se refleja en `requisitos/matriz_trazabilidad.md`.

### Fase 0: Higiene del repositorio
- [ ] **RD-04**: reestructura commiteada y repositorio con acceso de la profesora. *Hecho cuando* `git status` está limpio y el README está actualizado.
- [ ] **RNF-09**: `requirements.txt` instala en un venv limpio con Python 3.10 o superior.
- [ ] **RNF-10**: versiones exactas fijadas (`==`).
- [ ] **RNF-11**: `.env.example` existe, `.env` está en `.gitignore` y no hay claves en el repo.
- [ ] **RD-01**: el proyecto es Python con Streamlit en requirements.

### Fase 1: Configuración y utilidades
- [ ] **RNF-08**: umbrales, rutas, semilla y curva en `config/*.yaml`. *Hecho cuando* cambiar un umbral en el YAML cambia la salida sin tocar el código.
- [ ] **RNF-07**: módulos separados `src/data`, `src/feature`, `src/models` y `src/app`, sin lógica en los notebooks.

### Fase 2: ETL (hito 6/11)
- [ ] **RF-01**: ingesta de lecturas y estaciones con merge por `station_id`. *Hecho cuando* hay 0 lecturas huérfanas y el test `test_rf01_ingesta.py` pasa.
- [ ] **RF-03**: datos ordenados por timestamp, 0 duplicados (station_id, timestamp), tipos corregidos y anómalos marcados y tratados. *Hecho cuando* `test_rf03_limpieza.py` pasa.
- [ ] **RF-02**: ERA5, la ficha de turbina y la demanda integrados en el dataset. *Hecho cuando* las columnas `ws100`, `ssrd_wm2` y `demand_kw` existen sin huecos en el periodo.
- [ ] **RF-04**: todas las series en una rejilla regular de 5 min. *Hecho cuando* `index.to_series().diff().unique() == [5min]`.
- [ ] **RF-05**: potencia del parque calculada con la curva a altura de buje (m/s). *Hecho cuando* la potencia es 0 por debajo del cut-in y por encima del corte, el nominal está en la meseta y el máximo es 30 MW.
- [ ] **RNF-02 (parcial)**: la ETL corre con menos de 8 GB de RAM gracias al recorte de ERA5.

### Fase 3: Características, objetivos y umbrales
- [ ] **RF-06**: lags t−5/10/15/20 de potencia, viento y demanda por estación, más media, desviación y variación de ventana. *Hecho cuando* el test confirma que ninguna feature usa datos posteriores a t.
- [ ] **RF-07**: objetivos t+5/10/15/20, con t+15 como principal, y filas con nulos eliminadas. *Hecho cuando* `power_t+15[i] == power[i+3]` y no quedan NaN.
- [ ] **RF-08**: umbrales P15, % del nominal y sobrecarga calculados **solo con el train** y guardados en `umbrales.json`. *Hecho cuando* el JSON existe y `classify()` devuelve los 4 niveles.

### Fase 4: Modelado (Check modelo 15/12)
- [ ] **RF-09**: división cronológica 80/20. *Hecho cuando* `max(train.ts) < min(test.ts)`.
- [ ] **RD-03**: no se usa K-Fold aleatorio en ningún sitio, solo split cronológico o `TimeSeriesSplit` (revisión de código con grep de `KFold` y `shuffle=True`).
- [ ] **RF-10**: entrenados el modelo de persistencia y al menos 2 regresores.
- [ ] **RF-11**: RMSE y R² de cada modelo en el test, mejor modelo seleccionado y tabla en `docs/resultados/metricas.csv`.
- [ ] **RF-12 / RD-02**: `modelo_aruba_energia.pkl` en la raíz con más de 0 bytes y carga correcta.
- [ ] **RNF-04**: dos ejecuciones de `run_training.py` dan las mismas métricas.
- [ ] **RNF-02**: el entrenamiento completo tiene un pico de memoria inferior a 8 GB (medido).

### Fase 5: Aplicación
- [ ] **RF-13**: `predict.py` imprime exactamente `[ALERTA] Despacho Térmico/Solar requerido en 15m` (menos de 500 kW) u `[OK] Operación Estable`. *Hecho cuando* el test con `subprocess` cubre ambos casos.
- [ ] **RNF-01**: la predicción de un registro tarda menos de 2 s, tanto en `predict.py` como en la app.
- [ ] **RF-14**: la app carga el `.pkl` al iniciar.
- [ ] **RNF-12**: no hay `file_uploader` que acepte `.pkl` y el modelo se carga solo desde la ruta de config.
- [ ] **RNF-03**: si falta el `.pkl` o la entrada es inválida, se muestra un mensaje claro sin caída (app y `predict.py`).
- [ ] **RF-15**: entrada manual por formulario y carga desde JSON y CSV.
- [ ] **RF-16**: validación de completitud y rangos físicos con errores legibles.
- [ ] **RF-17**: se muestran la potencia t+15, la demanda y el déficit.
- [ ] **RF-18**: alertas en 4 niveles (estable, moderado, crítico térmico y sobrecarga).
- [ ] **RNF-06**: cada nivel tiene color, texto **e** icono.
- [ ] **RF-19**: gráfica de la potencia reciente con la predicción.
- [ ] **RNF-05**: prueba con un usuario ajeno al grupo que obtiene una predicción sin ayuda (anotada en el informe de pruebas).

### Fase 6: Pruebas y cierre
- [ ] Informe de pruebas funcionales (RF-01 a RF-19), con `pytest -q` en verde, en `docs/pruebas/`.
- [ ] Informe de pruebas no funcionales (RNF-01 a RNF-12), con mediciones de tiempo, RAM, reproducibilidad y portabilidad.
- [ ] **RNF-09**: instalación probada en Windows y al menos en otro sistema operativo (Linux o macOS).
- [ ] `requisitos/matriz_trazabilidad.md` al 100 %, con RF/RNF → módulo → test → estado.
- [ ] Memoria final y presentación (OE-09).

**Resumen de avance** (para actualizarlo en cada reunión semanal):

| Fase | Requisitos | Completados |
|---|---|---|
| 0 | RD-01, RD-04, RNF-09, RNF-10, RNF-11 | 0/5 |
| 1 | RNF-07, RNF-08 | 0/2 |
| 2 | RF-01, RF-02, RF-03, RF-04, RF-05 | 0/5 |
| 3 | RF-06, RF-07, RF-08 | 0/3 |
| 4 | RF-09, RF-10, RF-11, RF-12, RD-02, RD-03, RNF-02, RNF-04 | 0/8 |
| 5 | RF-13 a RF-19, RNF-01, RNF-03, RNF-05, RNF-06, RNF-12 | 0/12 |
| 6 | Informes, matriz, memoria | 0/5 |

> Nota: RF-01 aparece como "cumplido" en el notebook de Colab. Solo se marca aquí cuando esté portado a `src/data/ingestion.py` con su test.

## Orden recomendado y fechas

| Fecha límite | Hito | Contenido mínimo |
|---|---|---|
| 17/10 | Fase 0 + Fase 1 | Commit de la reestructura, requirements, config |
| 6/11 (máx. 8/11) | **Entrega ETL** | Fase 2 completa, notebook ETL y docs de arquitectura y fuentes |
| 16/11 | Check 1 | Fase 3 + borrador de umbrales, interfaz Streamlit con esqueleto |
| 15/12 | **Check modelo** | Fase 4 completa, `.pkl` real, `predict.py`, alertas y validación |
| 12/01/27 | **Entrega final** | Fase 5 pulida, Fase 6, memoria y presentación |

## Decisiones pendientes con el equipo o la profesora

1. Qué fichero de lecturas es el oficial: `train_aruba_lecturas.json` (31/03–30/06/2026) o `aruba_readings_20260924.json` (desde 01/09/2025, 1,35 M de filas). Hay que dejar el elegido en `data/raw/`.
2. Si existen datos de demanda reales. Si no, se usa el perfil sintético documentado.
3. Si los 500 kW de RF-13 son por parque o por turbina.
4. La ficha de turbina confirmada (modelo y altura de buje).

## Verificación end-to-end

1. `python -m venv .venv && pip install -r requirements.txt` en Windows (y en Linux o macOS si es posible) para RNF-09.
2. `python scripts/run_etl.py` debe generar `data/processed/dataset_5min.parquet`, con frecuencia de 5 min y sin duplicados.
3. `python scripts/run_training.py` debe imprimir la tabla de métricas, con el mejor modelo por encima de la persistencia al menos en rampas, y escribir un `modelo_aruba_energia.pkl` de más de 0 bytes. Al ejecutarlo dos veces, las métricas deben ser idénticas.
4. `python predict.py --input data/samples/registro_ejemplo.json` debe mostrar el mensaje `[OK]` o `[ALERTA]` en menos de 2 s.
5. `streamlit run app.py`: probar el formulario, la carga de JSON/CSV, un valor fuera de rango (que debe dar un error legible) y el `.pkl` renombrado (que debe dar un error sin caída).
6. `pytest -q` debe pasar en verde y la matriz de trazabilidad debe estar completa.
