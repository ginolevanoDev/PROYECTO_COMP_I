# Inventario de fuentes de datos

## Aerogeneradores del parque Vader Piet (HU-23, RF-05, RF-02)

| Dato | Valor | Fuente | Consulta |
|---|---|---|---|
| Modelo y ficha técnica | Vestas V90-3.0: 3000 kW, arranque 4 m/s, nominal 15 m/s, corte 25 m/s, rotor 90 m | `data/external/turbinas.json` ([wind-turbine-models.com](https://es.wind-turbine-models.com/turbines/603-vestas-v90-3-0)) | 21/10/2026 |
| Curva de potencia punto a punto | Fila `V90/3000`, a una densidad de 1,225 kg/m³ | Base OEDB de [windpowerlib](https://github.com/wind-python/windpowerlib/blob/master/windpowerlib/oedb/power_curves.csv), con origen en [wind-turbine-models.com](https://www.wind-turbine-models.com/turbines/16-vestas-v90) | 03/11/2026 |
| Número de turbinas | 10 (30 MW / 3 MW) | `data/external/equipment_installed.json` | 21/10/2026 |
| Altura de buje | 80 m | [Wikipedia: Vader Piet Wind Farm](https://en.wikipedia.org/wiki/Vader_Piet_Wind_Farm) y el [documento de South Pole](https://www.southpole.com/uploads/media/1938.pdf) | 03/11/2026 |
| Ubicación del parque | 12,474 N, −69,891 W | [Wikipedia](https://en.wikipedia.org/wiki/Vader_Piet_Wind_Farm) y [thewindpower.net](https://thewindpower.net/windfarm_en_15255_aruba.php) | 03/11/2026 |

Los valores se usan desde `config/turbinas.yaml`.

**Supuestos**
- **Altura de buje de 80 m.** La ficha admite 80 o 105 m y [Windbase](https://www.windbase.eu/projecten/wind-farm-vader-piet-aruba-2/) da 105 m. Se elige 80 m porque es lo que dicen las fuentes específicas del parque.
- **Corrección por densidad.** La curva está medida a 1,225 kg/m³, pero en Aruba la densidad media es de unos 1,174 kg/m³ (calculada con ERA5 en 2026). `turbine_power(..., rho=...)` corrige el viento según IEC 61400-12-1: v · (ρ/ρ_ref)^(1/3).
- **Sin histéresis en el corte.** Se usa un corte simple a 25 m/s. En 2026, el viento de ERA5 a buje no supera 15,9 m/s, así que no afecta.

**Contraste con la producción real**
- Con el viento de ERA5 en el punto (12,5, −70,0), llevado a 80 m, el factor de capacidad estimado es del **69,9 %** (71,6 % sin corregir la densidad).
- El factor de capacidad histórico de 2025 fue del **53,0 %**.
- La diferencia (factor de unos 0,76) se debe a pérdidas por estela, disponibilidad y curtailment, que la curva de una turbina aislada no recoge. Corresponde a la HU de calibración.

## Reanálisis ERA5 (HU-21, RF-02)

| Dato | Valor | Fuente | Consulta |
|---|---|---|---|
| Fichero | `data/external/datos_meteo.csv`, horario, en UTC. Incorporado al repositorio el 21/10/2026 (commit `ebbdf3a`), por Git LFS | Reanálisis ERA5 | 08/11/2026 |
| Cobertura del fichero | 9 puntos de rejilla (latitud 12,25 a 12,75; longitud −70,25 a −69,75; paso de 0,25°), del 01/01/2026 00:00 al 15/10/2026 12:00 UTC: 6.901 horas por punto | `datos_meteo.csv` | 08/11/2026 |
| Punto usado | (12,5, −70,0), el nodo de la rejilla más cercano al parque, a 12,2 km. Se fija en `era5.point` de `config/config.yaml` | `config/turbinas.yaml` (`park_latlon`) | 08/11/2026 |
| Periodo usado | El de las lecturas con una hora de margen: del 01/04/2026 02:00 al 01/07/2026 02:00 UTC, 2.185 horas | `load_era5` | 08/11/2026 |
| Variables usadas | `u10`, `v10`, `u100`, `v100` (componentes del viento a 10 y 100 m), `t2m_C`, `sp_hPa`, `i10fg` (rachas a 10 m) y `alpha`, calculada | `src/data/resampling.py` (`ERA5_COLS`) | 08/11/2026 |

**Cobertura y huecos**
- En el punto y el periodo usados están las 2.185 horas: no hay huecos ni horas repetidas.
- `load_era5` lo comprueba en cada ejecución: si falta alguna hora o el periodo no queda cubierto, el ETL se detiene con un error que dice cuántas horas faltan y cuál es la primera.

**Supuestos y decisiones**
- **Cizalladura.** `alpha = ln(ws100 / ws10) / ln(10)`, recortada entre 0 y 0,5. En el periodo usado va de 0,03 a 0,16, así que el recorte no llega a actuar.
- **Velocidad y dirección.** Se calculan a partir de `u` y `v` después de pasar a 5 minutos (HU-22), no de las columnas `vel_viento_*` ni `dir_viento_100m`, porque interpolar grados directamente da valores erróneos (entre 350° y 10° saldría 180°).
- **Temperatura y presión.** Se usan las de ERA5 y no las de las estaciones, que no son fiables (EDA §8).
- **Columnas sin usar.** `blh`, `tcc` y `fsr` no las necesita ningún paso del sistema.

**Pendiente**
- Registrar la consulta y la fecha de descarga de ERA5 en `scripts/download_external_data.py`, para poder reconstruir el fichero.

## Radiación solar (RF-02)

No se incorpora. `ssrd` y `ssrd_Wm2` están mal desacumuladas: el 24,79 % de los valores del fichero son negativos (el 24,53 % en el punto y el periodo usados) y hay 5.184 nulos. Para usar la radiación (HU-27 y el respaldo solar de las alertas) hay que volver a descargarla de ERA5.

## Demanda eléctrica (HU-21, RF-02)

| Dato | Valor | Fuente | Consulta |
|---|---|---|---|
| Media de la demanda en 2026 | 121 MW (121.000 kW) | `data/external/equipment_installed.json` (`load_demand_2026.average_mw`) | 08/11/2026 |
| Pico de la demanda en 2026 | 172 MW (172.000 kW) | `data/external/equipment_installed.json` (`load_demand_2026.max_peak_mw`) | 08/11/2026 |

**Supuesto: la serie es sintética.** No hay datos reales de demanda en el periodo de las lecturas. `load_or_build_demand` (`src/data/demand.py`) construye un perfil con esta forma:
- Perfil diario en hora local de Aruba (UTC−4): mínimo de madrugada (3 a 4 h) y máximo a las 19 o 20 h.
- Sábado y domingo, × 0,93.
- Ruido normal del 2 %, con la semilla 42 (`seed`), para que dos ejecuciones den lo mismo (RNF-04).
- Reescalado lineal para que la media sea de 121.000 kW y el pico de 172.000 kW.

La forma es una decisión del equipo (guía del Sprint 1), sin fuente que la respalde. Solo se apoyan en datos la media y el pico. Los parámetros están en la sección `demand` de `config/config.yaml`.

**Limitación.** La demanda no interviene en la predicción de la potencia eólica. Sí en el déficit (RF-17) y en las alertas por sobrecarga (RF-08 y RF-18), que por eso solo son ilustrativas mientras no haya serie real.

**Si llegan datos reales.** Basta con dejar el fichero en `data/external/demanda.csv` (columnas `timestamp` en UTC y `demanda_kw`). `load_or_build_demand` lo usa en lugar del perfil sintético, interpolado a los instantes de las lecturas, y da error si no cubre el periodo. Está pendiente preguntar a la docente si existe esa serie.
