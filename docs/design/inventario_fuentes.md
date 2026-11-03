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
