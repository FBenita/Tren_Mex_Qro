# Accesibilidad QroBus hacia la estación Corregidora

Este repositorio analiza la accesibilidad en transporte público hacia la estación del tren Corregidora, en Querétaro. A partir de los archivos GTFS de QroBus se calculan los tiempos programados desde cada parada, se consideran transbordos y se identifican las paradas e itinerarios que pueden llegar en 30 minutos o menos.

De manera opcional, el proyecto consulta Google Maps Routes API en modo transporte público para obtener estimaciones al momento de la ejecución. El resultado principal agrega el histórico por parada mediante P50, P80, tamaño de muestra y proporción de ETAs de 30 minutos o menos. La última ETA se conserva como contexto actual; el promedio por ruta se exporta únicamente por compatibilidad.

> Google Maps no proporciona en esta consulta el atraso GPS exacto de cada autobús. La diferencia entre su ETA y el tiempo GTFS se utiliza únicamente como una aproximación, ya que también puede incluir espera, caminata y transbordos. Para medir atrasos operativos reales se necesitaría un feed oficial GTFS-Realtime de QroBus.

## Estructura del repositorio

```text
Tren_Mex_Qro/
├── data/
│   ├── gtfs/                  # archivos fuente de QroBus
│   ├── processed/             # CSV y JSON generados
│   ├── cache/                 # descargas externas reutilizables
│   └── README.md
├── maps/                      # copias HTML de los mapas
├── notebooks/                 # análisis, numerados en orden de ejecución
│   ├── 01_PromedioRutas.ipynb
│   ├── 02_RutasQroBus.ipynb
│   └── 03_TiemposTotalesRutasGTFS.ipynb
├── scripts/                   # módulos de Python que importan los notebooks
│   ├── config.py
│   ├── geo.py
│   ├── google_routes.py
│   ├── gtfs_network.py
│   └── street_network.py
├── docs/
│   ├── reporte_demanda_accesibilidad_corregidora.md
│   └── soluciones_tiempos_rutas.md
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

Los archivos de `data/gtfs/` forman el conjunto GTFS local:

- `stops.txt`: paradas y coordenadas.
- `routes.txt`: catálogo de rutas.
- `trips.txt`: viajes asociados a cada ruta.
- `stop_times.txt`: secuencia y horarios de las paradas de cada viaje.

## Notebooks

### `02_RutasQroBus.ipynb`

Es el análisis y la visualización final. Carga los caminos mínimos que `01_PromedioRutas.ipynb` dejó en `data/processed/rutas_base_gtfs.csv`, incorpora las estadísticas históricas por parada y genera el mapa. No vuelve a ejecutar Dijkstra.

El cálculo compartido:

- conserva correctamente horarios GTFS superiores a `24:00:00`;
- usa la mediana del tiempo programado de cada segmento;
- agrega una penalización configurable por cada transbordo;
- separa conexiones directas de recorridos con transbordos;
- genera un mapa interactivo principal sin visualizaciones duplicadas;
- incluye todas las paradas que pueden llegar en menos de 30 minutos por el lado sur sin cruzar las vías, con un último tramo a pie de hasta 10 minutos;
- clasifica las paradas como acceso confiable, acceso habitual variable o datos insuficientes usando P50/P80;
- conserva la última ETA en una capa opcional y las columnas laboral/fin de semana como contexto futuro.

Puede ejecutarse sin nuevas solicitudes facturables cuando ya existe el histórico local, pero requiere ejecutar primero `01_PromedioRutas.ipynb` para regenerar las estadísticas.

El escenario sin cruces se muestra como mapa interactivo dentro de `02_RutasQroBus.ipynb` y también se guarda en `maps/`. Sus tiempos combinan la mediana programada del autobús con una caminata final medida sobre la red peatonal de OpenStreetMap del lado sur, a 80 m/min; no representan navegación ni tráfico en tiempo real.

### Demanda potencial con INEGI

La sección final de `notebooks/02_RutasQroBus.ipynb` consulta las manzanas del estado de Querétaro desde el servicio oficial del INEGI y estima la población cubierta por buffers alrededor de las paradas con acceso confiable a Corregidora. Si un buffer toca una manzana, se incluye la población de toda esa manzana. El radio predeterminado es de 20 metros y puede modificarse en `.env`:

```dotenv
RADIO_DEMANDA_M=20
```

La respuesta se conserva en `data/cache/`, que Git ignora. `ACTUALIZAR_DATOS_INEGI=true` fuerza una descarga nueva de geometrías al ejecutar el notebook. Se generan CSV de manzanas y paradas, comparaciones acumuladas para P80 de 5, 15, 30, 45 y 60 minutos y `maps/mapa_demanda_potencial.html`. La población por manzana proviene del Censo 2020, el último censo nacional disponible; el servicio de geometría puede refrescarse, pero no actualiza el año de referencia censal. El servicio geográfico usado en este notebook solo expone población total, población por sexo y viviendas habitadas. Los indicadores de edad, discapacidad, escolaridad, actividad económica, salud y vivienda del `FD_CPV2020.xlsx` requieren una tabla censal adicional por `CVEGEO`; no deben sustituirse con indicadores agregados de localidad o malla.

El análisis y las utilidades de mapas viven directamente en celdas independientes de `02_RutasQroBus.ipynb`; no requieren módulos auxiliares exclusivos del notebook. Cada mapa queda integrado en su salida y conserva una copia HTML en `maps/`. Los mapas dibujan la unión deduplicada de todos los segmentos utilizados: una parada solo se muestra cuando tiene un tramo conectado hacia el destino. Cada ruta conserva un color estable en líneas, paradas y leyendas; los tramos finales a pie se muestran en gris discontinuo.

### Tiempo total de todas las rutas sin Google

`notebooks/03_TiemposTotalesRutasGTFS.ipynb` contiene todo el cálculo paso a paso, muestra la tabla resumida e integra el mapa. Además aprende del histórico local una calibración robusta `constante + factor × GTFS`, construye escenarios P50/P80 y acumula los segmentos corregidos hacia atrás desde la última parada. No realiza llamadas nuevas a Google ni depende de un script adicional.

Genera `data/processed/tiempos_totales_rutas_gtfs.csv`, `data/processed/duraciones_viajes_gtfs.csv`, `data/processed/calibracion_tiempos_rutas_google.csv`, `data/processed/tiempos_acumulados_paradas_rutas.csv` y `maps/mapa_tiempos_totales_rutas_gtfs.html`. El mapa colorea cada ruta de forma distinta y compara GTFS con P50/P80 por sentido. Como el GTFS no incluye `shapes.txt`, las líneas unen paradas consecutivas siguiendo la red vial de OpenStreetMap: son el recorrido más probable por calles, no el derrotero oficial. Las alternativas, fórmulas y limitaciones están documentadas en `docs/soluciones_tiempos_rutas.md`.

#### Escenarios de 5 a 60 minutos y desglose por sexo y edad

La sección de demanda repite el cálculo para paradas con acceso confiable (P80 histórico y al menos `MIN_OBSERVACIONES_HISTORICAS` observaciones) en 5, 15, 30, 45 y 60 minutos. Los escenarios son acumulados y cada uno tiene su capa en el mapa de demanda. Archivos generados:

```text
data/processed/paradas_acceso_5_15_30_45_60_min.csv    # paradas de cada escenario
data/processed/resumen_acceso_5_15_30_45_60_min.csv    # paradas, manzanas y población
data/processed/personas_acceso_5_15_30_45_60_min.csv   # tabla de resumen por sexo y edad
data/processed/manzanas_acceso_<minutos>_min.csv       # manzanas de cada escenario
```

La tabla de resumen cuenta manzanas completas y únicas, e incluye por cada tiempo: personas totales, mujeres (`POBFEM`), hombres (`POBMAS`), niños de 0 a 14 años (`POB0_14`), personas de 65 años o más (`POB65_MAS`), personas con discapacidad (`PCON_DISC`) y población económicamente activa (`PEA`). Las variables provienen del conjunto por manzana del Censo 2020, que se descarga a `data/cache/`.

El INEGI oculta con `*` los valores de manzanas con muy poca población. Esas manzanas no suman al desglose: mujeres más hombres puede ser menor que el total y los grupos de edad son un mínimo, no un conteo exacto. El notebook muestra junto a la tabla cuántas manzanas tienen cada dato.

El escenario de 60 minutos depende de que Google se haya consultado para paradas con hasta 60 minutos de tiempo GTFS (`UMBRAL_CONSULTA_GOOGLE_MIN=60`). Una parada recién incorporada no cuenta como acceso confiable hasta acumular el mínimo de observaciones, así que el escenario de una hora crece conforme se repiten las consultas en distintos días y horarios.

### Tiempos P50/P80 en los mapas

Cada tramo de ruta muestra, al pasar el cursor, su distancia por calles y el P50 y P80 histórico hacia Corregidora desde la parada donde inicia. La leyenda resume el rango P50 y P80 de cada ruta. El par P50/P80 sigue la medida de confiabilidad *Level of Travel Time Reliability* de la Federal Highway Administration (percentil 80 entre percentil 50, [23 CFR § 490.511](https://www.law.cornell.edu/cfr/text/23/490.511)), adoptada aquí por analogía para transporte público con muestras pequeñas; la justificación completa está en la sección 9 de `02_RutasQroBus.ipynb`.

### Módulos compartidos en `scripts/`

Los notebooks no repiten configuración ni lógica: la importan de estos módulos. Cada notebook agrega `scripts/` a la ruta de importación en su primera celda de código, así que funciona al abrirlo desde `notebooks/` o desde la raíz.

| Módulo | Contenido | Lo usan |
|---|---|---|
| `config.py` | Carpetas del proyecto, lectura de `.env`, coordenadas de la estación y validación de parámetros. | Los tres notebooks |
| `geo.py` | Distancia Haversine, polilínea de la vía férrea, criterio de "mismo lado de la vía" y lectura o escritura de los trazos por calles. No depende de OSMnx. | Los tres notebooks y los otros módulos |
| `gtfs_network.py` | Horarios GTFS, filtro de segmentos que cruzan la vía y Dijkstra con transbordos. | `01` y `02` |
| `street_network.py` | Descarga de la red de OpenStreetMap y enrutamiento de pares de paradas por calles. | `01` |
| `google_routes.py` | Llamadas a Google Maps Routes API (`computeRouteMatrix`) por lotes, con reintentos. | `01` |

Las variables de `.env` se leen una sola vez en `config.py`; una variable definida en el entorno del sistema tiene prioridad sobre el archivo. Para agregar un parámetro nuevo basta declararlo ahí e importarlo en el notebook.

### `01_PromedioRutas.ipynb`

Construye la red GTFS y ejecuta Dijkstra para dos problemas distintos: la red general y la red del lado sur después de retirar los segmentos que cruzan las vías. Guarda ambos resultados para que `02_RutasQroBus.ipynb` no repita los cálculos. También enruta cada par de paradas consecutivas sobre la red vial de OpenStreetMap y guarda la distancia y la geometría por calles, que los mapas usan en lugar de líneas rectas. De forma opcional, complementa el análisis mediante Google Maps Routes API. Genera:

```text
data/processed/google_maps_transit_observaciones.csv
data/processed/estadisticas_historicas_google_por_parada.csv
data/processed/promedio_atrasos_google_por_ruta.csv
data/processed/tiempos_corregidos_google.csv
data/processed/rutas_base_gtfs.csv
data/processed/rutas_base_sur_vias.csv
data/processed/segmentos_red_vial.csv
```

Las consultas están desactivadas de forma predeterminada. Este notebook solamente llama a Google cuando `EJECUTAR_GOOGLE_MAPS=true` en `.env`.

## Requisitos

- Git.
- Python 3.10 o posterior.
- Una instalación de Jupyter Notebook o JupyterLab.
- Una API key de Google Maps Platform únicamente si se desean obtener estimaciones de Google.

## Clonar el repositorio

```bash
git clone https://github.com/FBenita/Tren_Mex_Qro.git
cd Tren_Mex_Qro
```

## Crear el entorno de Python

Se recomienda trabajar en un entorno virtual para no modificar la instalación global de Python.

En macOS o Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

En Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Todas las dependencias directas utilizadas por los notebooks están declaradas en `requirements.txt`. Los rangos de versiones permiten recibir correcciones compatibles sin instalar automáticamente una nueva versión mayor.

## Configurar las variables de entorno

Desde la raíz del repositorio, copia el archivo de ejemplo:

En macOS o Linux:

```bash
cp .env.example .env
```

En Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

El contenido esperado es:

```dotenv
GOOGLE_MAPS_API_KEY=pegue_aqui_su_api_key
EJECUTAR_GOOGLE_MAPS=false
UMBRAL_ANALISIS_MIN=30
PENALIZACION_TRANSBORDO_MIN=5
MAX_EDAD_ETA_HORAS=24
MIN_OBSERVACIONES_HISTORICAS=5
RADIO_DEMANDA_M=20
UMBRAL_CONSULTA_GOOGLE_MIN=60
```

Variables disponibles:

| Variable | Descripción |
|---|---|
| `GOOGLE_MAPS_API_KEY` | Credencial para Routes API. No es necesaria para el análisis GTFS. |
| `EJECUTAR_GOOGLE_MAPS` | Habilita las solicitudes a Google. Mantener en `false` hasta revisar cuotas y facturación. |
| `UMBRAL_ANALISIS_MIN` | Máximo de minutos utilizado para seleccionar paradas; por defecto, 30. |
| `PENALIZACION_TRANSBORDO_MIN` | Minutos aproximados de espera o caminata agregados por cada cambio de ruta. |
| `UMBRAL_CONSULTA_GOOGLE_MIN` | Tiempo GTFS máximo de las paradas que se consultan en Google; por defecto igual a `UMBRAL_ANALISIS_MIN`. Con 60 se alimenta el escenario de una hora (unas 1,700 paradas por ejecución en lugar de unas 400). |
| `MAX_EDAD_ETA_HORAS` | Antigüedad máxima permitida para usar una ETA de Google en el mapa; por defecto, 24 horas. |
| `MIN_OBSERVACIONES_HISTORICAS` | Muestra mínima por parada para una clasificación P50/P80 preliminar; por defecto, 5. Diez o más se etiquetan como calidad alta. |
| `RADIO_DEMANDA_M` | Radio en metros de los buffers usados para estimar demanda potencial; por defecto, 20. |
| `ACTUALIZAR_DATOS_INEGI` | Si es `true`, vuelve a descargar las geometrías de manzana del servicio del INEGI en vez de usar la caché. |
| `ACTUALIZAR_RED_OSM` | Si es `true`, vuelve a descargar las redes vial y peatonal de OpenStreetMap en vez de usar `data/cache/`. |
| `RETENCION_HISTORICO_DIAS` | Ventana de retención para las observaciones de Google; por defecto, 365 días. |

El archivo `.env` está excluido mediante `.gitignore`. Nunca se debe copiar la API key al notebook, al README ni a un commit.

## Cómo obtener una API key de Google Maps

1. Ingresa a [Google Cloud Console](https://console.cloud.google.com/) e inicia sesión.
2. Crea un proyecto nuevo o selecciona uno existente dedicado a este análisis.
3. Vincula una cuenta de facturación. Google Maps Platform requiere facturación habilitada aunque la cuenta tenga créditos o consumo mensual sin cargo.
4. Abre **APIs y servicios > Biblioteca**.
5. Busca **Routes API** y selecciona **Habilitar**. No es necesario habilitar Roads API para estos notebooks.
6. Abre **APIs y servicios > Credenciales**.
7. Selecciona **Crear credenciales > Clave de API**.
8. Edita la clave y, en **Restricciones de API**, elige **Restringir clave** y permite solamente **Routes API**.
9. Como el notebook realiza solicitudes REST desde la computadora, se puede agregar una restricción de aplicación por **Direcciones IP** si se dispone de una IP pública fija. Con una IP dinámica, esta restricción puede dejar de funcionar cuando cambie la dirección; aun así, se debe conservar como mínimo la restricción exclusiva a Routes API y mantener la clave fuera de Git.
10. Guarda la clave en `.env`:

```dotenv
GOOGLE_MAPS_API_KEY=su_clave_real
EJECUTAR_GOOGLE_MAPS=false
```

La guía oficial para habilitar el servicio y crear la clave se encuentra en [Set up the Routes API](https://developers.google.com/maps/documentation/routes/get-api-key). Las recomendaciones oficiales de protección están en [Google Maps Platform security guidance](https://developers.google.com/maps/api-security-best-practices).

## Controlar el consumo y evitar cargos inesperados

Antes de activar las consultas:

1. En Google Cloud Console, selecciona el proyecto correcto.
2. Revisa **APIs y servicios > Routes API > Cuotas y límites del sistema** y reduce las cuotas disponibles cuando la consola permita editarlas.
3. Configura un presupuesto y notificaciones en **Facturación > Presupuestos y alertas**.
4. Revisa la [página vigente de uso y facturación de Routes API](https://developers.google.com/maps/documentation/routes/usage-and-billing) antes de cada ejecución grande.
5. Mantén `EJECUTAR_GOOGLE_MAPS=false` cuando no estés recolectando observaciones.

Un presupuesto configurado únicamente como alerta no detiene automáticamente el consumo. Si la consola ofrece un presupuesto con límite de gasto aplicable al servicio, se puede utilizar como protección adicional; de cualquier forma, conviene controlar también las cuotas y el interruptor del notebook.

El notebook agrega otras protecciones:

- solo consulta paradas cuyo tiempo GTFS no supera `UMBRAL_CONSULTA_GOOGLE_MIN`; cada parada es un elemento facturable, y el notebook imprime el total antes de consultar;
- envía como máximo 100 orígenes por lote;
- solicita únicamente los campos necesarios de la respuesta;
- no ejecuta solicitudes si la bandera permanece en `false`.

## Ejecutar los notebooks

Activa el entorno virtual y, desde la raíz del repositorio, inicia JupyterLab:

```bash
jupyter lab
```

### Opción 1: análisis solamente con GTFS

Esta opción no utiliza Google Maps ni genera cargos.

1. Confirma que `EJECUTAR_GOOGLE_MAPS=false`.
2. Abre `notebooks/01_PromedioRutas.ipynb` y ejecuta todas las celdas. Esto calcula los escenarios general y sin cruces, pero no consulta Google.
3. Abre `notebooks/02_RutasQroBus.ipynb` y ejecuta todas las celdas. Este notebook reutiliza el cálculo anterior.
4. Revisa las tablas de paradas directas, paradas con transbordos e itinerarios dentro de 30 minutos.
5. Usa el control de capas del mapa para mostrar u ocultar cada categoría.

### Opción 2: análisis histórico con Google

1. Verifica la clave, sus restricciones, las cuotas y la facturación.
2. Cambia temporalmente en `.env`:

   ```dotenv
   EJECUTAR_GOOGLE_MAPS=true
   ```

3. Abre `notebooks/01_PromedioRutas.ipynb` y ejecuta todas las celdas.
4. Comprueba que se haya generado `data/processed/estadisticas_historicas_google_por_parada.csv` y revisa el tamaño de muestra reportado por parada.
5. Vuelve a dejar `EJECUTAR_GOOGLE_MAPS=false` para evitar llamadas accidentales.
6. Abre `notebooks/02_RutasQroBus.ipynb` y ejecuta todas las celdas. El notebook utilizará P80 para acceso confiable, P50 para acceso habitual variable y mostrará la última ETA en una capa opcional.

Para obtener un promedio representativo, `01_PromedioRutas.ipynb` debe ejecutarse en diferentes días y horarios. Una sola ejecución es una fotografía del momento, no un promedio histórico confiable.

## Flujo de datos

```text
Archivos GTFS locales
        │
        └──> 01_PromedioRutas.ipynb ──> Dijkstra general ──> rutas_base_gtfs.csv
                    │
                    ├──> retirar cruces ferroviarios
                    │             │
                    │             └──> Dijkstra lado sur ──> rutas_base_sur_vias.csv
                    └──> Routes API opcional ──> observaciones históricas
                                                       │
                                                       └──> P50 / P80 por parada
                                                                  │
                  archivos de rutas base ─────────────────────────┤
                                                                  └──> 02_RutasQroBus.ipynb ──> mapa
```

## Consideraciones del análisis

- El tiempo GTFS representa programación, no la posición real de los vehículos.
- La penalización de transbordo es una aproximación configurable.
- Las distancias entre paradas se miden sobre la red vial de OpenStreetMap (`scripts/street_network.py`), no en línea recta. Sin `shapes.txt` el trazo es el camino más probable, no el derrotero oficial; los pares sin camino razonable conservan la línea recta y quedan marcados en la columna `metodo_trazo`. La primera ejecución descarga la red y necesita conexión a internet.
- Google Transit puede incorporar información actualizada cuando el operador la comparte, pero no garantiza un campo de atraso de QroBus.
- Los datos locales actuales no incluyen `calendar.txt` ni `calendar_dates.txt`, por lo que el análisis no valida qué servicio opera en una fecha específica.
- Las coordenadas y horarios deben actualizarse cuando se publique una versión nueva del GTFS de QroBus.

## Fuente de datos

Los datos corresponden al formato GTFS de QroBus. La publicación oficial puede consultarse en [QroBus GTFS](https://qrobus.gob.mx/gtfs).
