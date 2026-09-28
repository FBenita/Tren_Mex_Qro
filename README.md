# Accesibilidad QroBus hacia la estación Corregidora

Este repositorio analiza la accesibilidad en transporte público hacia la estación del tren Corregidora, en Querétaro. A partir de los archivos GTFS de QroBus se calculan los tiempos programados desde cada parada, se consideran transbordos y se identifican las paradas e itinerarios que pueden llegar en 30 minutos o menos.

De manera opcional, el proyecto consulta Google Maps Routes API en modo transporte público para obtener estimaciones al momento de la ejecución. Esas observaciones se comparan con el tiempo programado del GTFS y se utilizan para construir una corrección promedio por ruta.

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
├── scripts/
│   ├── demanda_potencial_inegi.py
│   ├── PromedioRutas.ipynb
│   ├── qrobus_maps.py
│   ├── RutasQroBus.ipynb
│   ├── tiempos_totales_rutas_gtfs.py
│   └── gtfs_network.py
├── docs/
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

### `RutasQroBus.ipynb`

Es el análisis y la visualización final. Carga los caminos mínimos que `PromedioRutas.ipynb` dejó en `data/processed/rutas_base_gtfs.csv`, incorpora las correcciones disponibles y genera el mapa. No vuelve a ejecutar Dijkstra.

El cálculo compartido:

- conserva correctamente horarios GTFS superiores a `24:00:00`;
- usa la mediana del tiempo programado de cada segmento;
- agrega una penalización configurable por cada transbordo;
- separa conexiones directas de recorridos con transbordos;
- genera un mapa interactivo principal sin visualizaciones duplicadas;
- incluye todas las paradas que pueden llegar en menos de 30 minutos por el lado sur sin cruzar las vías, con un último tramo a pie de hasta 10 minutos;
- consume las correcciones de Google si ya fueron generadas.

Puede ejecutarse sin una API key y sin realizar solicitudes facturables, pero requiere ejecutar primero `PromedioRutas.ipynb` con la API activada o desactivada.

El escenario sin cruces se muestra como mapa interactivo dentro de `RutasQroBus.ipynb` y también se guarda en `maps/`. Sus tiempos combinan la mediana programada del autobús con una caminata final aproximada en línea recta; no representan navegación ni tráfico en tiempo real.

### Demanda potencial con INEGI

`scripts/demanda_potencial_inegi.py` descarga las manzanas completas del estado de Querétaro desde el servicio oficial del INEGI y estima la población cubierta por buffers alrededor de las paradas que llegan a Corregidora dentro del umbral GTFS. El radio predeterminado es de 20 metros y puede modificarse:

```bash
python scripts/demanda_potencial_inegi.py --radio-m 20 --umbral-min 30
```

La respuesta de aproximadamente 50 MB se conserva en `data/cache/`, que Git ignora. Se generan el resumen `data/processed/demanda_potencial_resumen.json`, el detalle por manzana y `maps/mapa_demanda_potencial.html`. El resultado principal prorratea la población según la fracción del área de cada manzana cubierta; es una estimación y no localiza domicilios. El resumen distingue la población estatal total de la población numérica representada en manzanas, pues no todas las personas viven en áreas amanzanadas y existen valores protegidos. Para un estudio de acceso peatonal conviene comparar también radios de 400 o 500 metros.

Este análisis también se ejecuta en una celda independiente al final de `RutasQroBus.ipynb`. Cada mapa queda integrado en la salida del notebook y conserva una copia HTML en `maps/`. Los mapas dibujan la unión deduplicada de todos los segmentos utilizados: una parada solo se muestra cuando tiene un tramo conectado hacia el destino. Cada ruta conserva un color estable en líneas, paradas y leyendas; los tramos finales a pie se muestran en gris discontinuo.

### Tiempo total de todas las rutas sin Google

`scripts/tiempos_totales_rutas_gtfs.py` calcula la duración programada de cada viaje completo y la resume por ruta y sentido:

```bash
python scripts/tiempos_totales_rutas_gtfs.py
```

Genera `data/processed/tiempos_totales_rutas_gtfs.csv` y `data/processed/duraciones_viajes_gtfs.csv` sin consumir la API de Google. Las alternativas para obtener tiempos observados y reducir costos están documentadas en `docs/soluciones_tiempos_rutas.md`.

### `PromedioRutas.ipynb`

Construye la red GTFS y ejecuta Dijkstra para dos problemas distintos: la red general y la red del lado sur después de retirar los segmentos que cruzan las vías. Guarda ambos resultados para que `RutasQroBus.ipynb` no repita los cálculos. De forma opcional, complementa el análisis mediante Google Maps Routes API. Genera:

```text
data/processed/google_maps_transit_observaciones.csv
data/processed/promedio_atrasos_google_por_ruta.csv
data/processed/tiempos_corregidos_google.csv
data/processed/rutas_base_gtfs.csv
data/processed/rutas_base_sur_vias.csv
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
RADIO_DEMANDA_M=20
```

Variables disponibles:

| Variable | Descripción |
|---|---|
| `GOOGLE_MAPS_API_KEY` | Credencial para Routes API. No es necesaria para el análisis GTFS. |
| `EJECUTAR_GOOGLE_MAPS` | Habilita las solicitudes a Google. Mantener en `false` hasta revisar cuotas y facturación. |
| `UMBRAL_ANALISIS_MIN` | Máximo de minutos utilizado para seleccionar paradas; por defecto, 30. |
| `PENALIZACION_TRANSBORDO_MIN` | Minutos aproximados de espera o caminata agregados por cada cambio de ruta. |
| `MAX_EDAD_ETA_HORAS` | Antigüedad máxima permitida para usar una ETA de Google en el mapa; por defecto, 24 horas. |
| `RADIO_DEMANDA_M` | Radio en metros de los buffers usados para estimar demanda potencial; por defecto, 20. |

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

- solo consulta paradas cuyo tiempo GTFS no supera el umbral configurado;
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
2. Abre `scripts/PromedioRutas.ipynb` y ejecuta todas las celdas. Esto calcula los escenarios general y sin cruces, pero no consulta Google.
3. Abre `scripts/RutasQroBus.ipynb` y ejecuta todas las celdas. Este notebook reutiliza el cálculo anterior.
4. Revisa las tablas de paradas directas, paradas con transbordos e itinerarios dentro de 30 minutos.
5. Usa el control de capas del mapa para mostrar u ocultar cada categoría.

### Opción 2: análisis con corrección de Google

1. Verifica la clave, sus restricciones, las cuotas y la facturación.
2. Cambia temporalmente en `.env`:

   ```dotenv
   EJECUTAR_GOOGLE_MAPS=true
   ```

3. Abre `scripts/PromedioRutas.ipynb` y ejecuta todas las celdas.
4. Comprueba que se haya generado `data/processed/tiempos_corregidos_google.csv` y revisa los errores o paradas sin cobertura reportados por el notebook.
5. Vuelve a dejar `EJECUTAR_GOOGLE_MAPS=false` para evitar llamadas accidentales.
6. Abre `scripts/RutasQroBus.ipynb` y ejecuta todas las celdas. El notebook detectará el archivo de correcciones y lo incorporará al tiempo estimado.

Para obtener un promedio representativo, `PromedioRutas.ipynb` debe ejecutarse en diferentes días y horarios. Una sola ejecución es una fotografía del momento, no un promedio histórico confiable.

## Flujo de datos

```text
Archivos GTFS locales
        │
        └──> PromedioRutas.ipynb ──> Dijkstra general ──> rutas_base_gtfs.csv
                    │
                    ├──> retirar cruces ferroviarios
                    │             │
                    │             └──> Dijkstra lado sur ──> rutas_base_sur_vias.csv
                    └──> Routes API opcional ──> tiempos_corregidos_google.csv
                                                       │
                  archivos de rutas base ──────────────┤
                                                       └──> RutasQroBus.ipynb ──> mapa
```

## Consideraciones del análisis

- El tiempo GTFS representa programación, no la posición real de los vehículos.
- La penalización de transbordo es una aproximación configurable.
- Google Transit puede incorporar información actualizada cuando el operador la comparte, pero no garantiza un campo de atraso de QroBus.
- Los datos locales actuales no incluyen `calendar.txt` ni `calendar_dates.txt`, por lo que el análisis no valida qué servicio opera en una fecha específica.
- Las coordenadas y horarios deben actualizarse cuando se publique una versión nueva del GTFS de QroBus.

## Fuente de datos

Los datos corresponden al formato GTFS de QroBus. La publicación oficial puede consultarse en [QroBus GTFS](https://qrobus.gob.mx/gtfs).
