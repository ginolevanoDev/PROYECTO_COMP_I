# Scraper de turbinas eólicas

Script en Python ([scrapTurbineFeature.py](scrapTurbineFeature.py)) que obtiene la hoja de datos técnicos de una turbina eólica de [es.wind-turbine-models.com](https://es.wind-turbine-models.com/) y la guarda en un archivo JSON.

La página está protegida por **Cloudflare** y muestra un **banner de cookies**, por lo que el script usa un navegador Chrome real controlado con SeleniumBase en modo UC (*Undetected Chrome*).

## Qué hace

1. Abre la página principal y supera la verificación de Cloudflare ("Verifique que es un ser humano").
2. Rechaza las cookies (botón **Declinación**).
3. Escribe el texto de `BUSQUEDA` en el buscador y lista las turbinas de los resultados.
4. Entra en la turbina cuyo nombre coincide con `TURBINA`.
5. Lee la **Hoja de datos** (De energía, Hélice, Caja de cambios, Grupo electrógeno, Torre, Masas / Pesos, Otros).
6. Muestra los datos en consola y los guarda en `datos_turbina.json`.

Si una página falla al cargar, el script la recarga y lo reintenta hasta 3 veces.

## Requisitos

- Python 3.10 o superior
- Google Chrome instalado
- Librerías:

```bash
pip install seleniumbase beautifulsoup4
```

La primera ejecución descarga automáticamente el chromedriver que necesita SeleniumBase.

## Uso

Editar las constantes al inicio del script:

```python
BUSQUEDA = "Vestas 90"        # texto que se escribe en el buscador
TURBINA = "Vestas V90-3.0"    # nombre de la turbina a abrir dentro de los resultados
```

Y ejecutar:

```bash
python scrapTurbineFeature.py
```

La comparación de `TURBINA` ignora mayúsculas, espacios, guiones y la "V" delante del número, así que `"Vestas V90-3.0"` y `"vestas 90-3.0"` son equivalentes. Si la turbina no aparece en los resultados, el script se detiene con un mensaje en lugar de capturar otra.

**Importante:** la ventana de Chrome debe quedar visible y no hay que mover el ratón mientras se marca la casilla de Cloudflare, porque se hace con el ratón real.

## Resultado

Archivo `datos_turbina.json`, con los datos agrupados por sección (hay campos como "Fabricante" que se repiten en varias):

```json
{
  "nombre": "Vestas V90-3.0",
  "enlace": "https://es.wind-turbine-models.com/turbines/603-vestas-v90-3-0",
  "hoja_de_datos": {
    "De energía": {
      "Potencia nominal": "3,000.0 kW",
      "Velocidad del viento": "4.0 m/s",
      "Velocidad nominal del viento": "15.0 m/s",
      "Velocidad del viento de corte": "25.0 m/s"
    },
    "Hélice": {
      "diámetro": "90.0 m",
      "número de hojas": "3"
    },
    "Torre": {
      "Altura del buje": "80/105 m"
    }
  }
}
```

Los valores se guardan como texto, tal como aparecen en la web (con unidades). Un `-` indica que la página no tiene ese dato.

## Archivos generados

| Archivo / carpeta | Contenido |
|---|---|
| `datos_turbina.json` | Datos de la última turbina capturada (se sobrescribe en cada ejecución) |
| `perfil_chrome/` | Perfil de Chrome con las cookies de Cloudflare y la elección de cookies, para que no vuelvan a preguntar en ejecuciones siguientes. Se puede borrar sin problema. |

## Problemas comunes

| Problema | Solución |
|---|---|
| La casilla de Cloudflare se repite en bucle | No usar Selenium normal; el script debe ejecutarse con `SB(uc=True)`. Borrar `perfil_chrome/` y volver a intentarlo. |
| `No se pudo cargar la página de resultados` | Fallaron los 3 reintentos. Comprobar la conexión o ejecutar de nuevo. |
| `'...' no está en los resultados de '...'` | El nombre de `TURBINA` no coincide con ninguna tarjeta. Revisar la lista que imprime la consola y copiar el nombre exacto. |
| `Import "seleniumbase" could not be resolved` | Instalar las dependencias con `pip install seleniumbase beautifulsoup4`. |

## Funciones principales

| Función | Descripción |
|---|---|
| `pasar_cloudflare` | Detecta la página "Just a moment..." y marca la casilla de verificación. |
| `rechazar_cookies` | Pulsa el botón `div.cc-decline-all` del banner de cookies. |
| `cargar_con_reintentos` | Ejecuta una acción, espera a que aparezca un elemento y recarga la página si falla. |
| `normalizar` | Normaliza nombres de turbina para compararlos. |
| `leer_hoja_de_datos` | Extrae la hoja de datos con BeautifulSoup (lee también las pestañas cerradas del acordeón). |
