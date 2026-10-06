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


## Dataset y descarga del proyecto

El archivo `DATA/era5_aruba.csv` ocupa aproximadamente 421,5 MB
y se almacena mediante Git LFS.

Para descargar el proyecto con el dataset completo, es necesario
tener Git y Git LFS instalados.

### 1. Instalar Git LFS

En macOS, si utilizas Homebrew:

```bash
brew install git-lfs
```

Para Windows u otros sistemas, consulta:
https://git-lfs.com

Después de instalarlo, ejecuta una vez por ordenador:

```bash
git lfs install
```

### 2. Descargar el proyecto

Si el repositorio es privado, necesitas acceso como colaborador
y autenticarte con una cuenta de GitHub autorizada.

Desde la carpeta donde quieras guardar el proyecto:

```bash
git clone https://github.com/ginolevanoDev/PROYECTO_COMP_I.git
cd PROYECTO_COMP_I
git lfs pull
```

El CSV estará en `DATA/era5_aruba.csv`.


### 3. Actualizar una copia existente

Antes de empezar a trabajar, guarda tus cambios pendientes
en un commit. Después, desde la carpeta del repositorio:

```bash
git pull
git lfs pull
```

Git LFS solo descargará los archivos necesarios que no estén
disponibles en tu copia local.

### 4. Compartir cambios

Después de crear, modificar o eliminar archivos:

```bash
git status
git add .
git commit -m "Descripción de los cambios realizados"
git push
```

Revisa `git status` antes de añadir los archivos para comprobar
qué cambios vas a compartir.

Los CSV ya están configurados para utilizar Git LFS mediante
`.gitattributes`. Los colaboradores no necesitan repetir
`git lfs track`.

### Uso del dataset en equipo

- Conservar el CSV original como fuente de datos.
- Realizar la limpieza, las transformaciones y la creación
  de variables desde el notebook.
- Evitar subir versiones innecesarias del CSV: cada versión
  modificada ocupa espacio adicional en Git LFS.
- Trabajar con la copia local del dataset para evitar
  descargas completas repetidas.
