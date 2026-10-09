# Reporte de demanda potencial y accesibilidad QroBus hacia Corregidora

Fecha de actualización: 5 de octubre de 2026.

## Resumen ejecutivo

El análisis identifica **329 paradas** clasificadas actualmente como acceso confiable hacia la estación Corregidora, porque cuentan con al menos cinco observaciones históricas y su ETA P80 de Google es menor o igual a 30 minutos. De estas paradas, 15 tienen una conexión directa en el camino GTFS calculado y 314 requieren uno o más transbordos.

Alrededor de las 329 paradas se construyó la unión de buffers de 20 metros. Esta cobertura intersecta 395 manzanas del Censo de Población y Vivienda 2020. Al contar toda la población de cada manzana tocada por los buffers, la cobertura suma **42,149 personas**, equivalente al 1.7796 % de la población estatal reportada por el INEGI.

Este resultado debe interpretarse como una aproximación espacial. No significa que 42,149 personas utilicen actualmente QroBus o el tren. Representa la población censada en las manzanas que intersectan los buffers de las paradas clasificadas como accesibles según el criterio vigente.

## Fuentes de información

### GTFS de QroBus

Se utilizaron los siguientes archivos locales:

- `stops.txt`: identificador, nombre y coordenadas de cada parada;
- `routes.txt`: identificador y nombre público de cada ruta;
- `trips.txt`: relación entre viajes y rutas;
- `stop_times.txt`: orden y horario programado de las paradas.

El conjunto no contiene `calendar.txt`, `calendar_dates.txt` ni `shapes.txt`. Por ello no se determina qué servicios operan en una fecha concreta y las líneas del mapa unen paradas consecutivas por el camino más probable sobre la red vial de OpenStreetMap, que puede diferir del derrotero oficial.

### Histórico de Google Routes API

El histórico local contiene estimaciones de viaje en transporte público desde distintas paradas hacia la estación. Google puede incluir espera, caminata, transbordos y rutas alternativas. Por tanto, la ETA se utiliza como un **proxy del tiempo para el pasajero**, no como medición del atraso operativo de una unidad QroBus.

### INEGI

La población procede del **Censo de Población y Vivienda 2020** y de las geometrías de manzanas del servicio del INEGI para Querétaro.

Las unidades descargadas son manzanas censales de geometría irregular; no son necesariamente cuadrados fijos de 500 por 500 metros.

## Ubicación de destino

Las coordenadas definidas para la estación Corregidora son:

```text
Latitud:  20.600611
Longitud: -100.402184
```

La parada GTFS más cercana utilizada como destino de la red es:

| stop_id | Parada | Latitud | Longitud |
|---|---|---:|---:|
| 3025 | Estío/Calle Dr. Manuel Domínguez | 20.599573 | -100.400492 |

La estación y la parada no son exactamente el mismo punto. El mapa conserva un marcador para la estación y otro para la parada destino.

## Cómo se obtuvieron las rutas y tiempos hacia la estación

### 1. Construcción de segmentos GTFS

Los registros se ordenaron por `trip_id` y `stop_sequence`. Cada par de paradas consecutivas forma un segmento dirigido:

```text
tiempo_segmento = llegada_siguiente - salida_actual
```

Para evitar que una observación programada extrema controle la red, se utilizó la mediana de cada combinación:

```text
parada_actual + parada_siguiente + route_id
```

Solo se conservaron segmentos con duración entre 0 y 180 minutos.

### 2. Caminos hacia Corregidora

Se construyó un grafo dirigido y se aplicó Dijkstra en sentido inverso desde la parada destino. El estado del algoritmo considera la parada y la ruta utilizada. Cambiar de ruta agrega una penalización configurada de cinco minutos.

El resultado de cada origen incluye:

- secuencia de paradas;
- rutas utilizadas;
- paradas de transbordo;
- número de transbordos;
- tiempo de red GTFS.

### 3. Tiempo histórico P50 y P80

Las observaciones de Google se agruparon por parada:

- P50: tiempo habitual o mediana;
- P80: tiempo que aproximadamente ocho de cada diez observaciones no superan;
- número de observaciones;
- proporción de observaciones de 30 minutos o menos.

El criterio actual de acceso confiable es:

```text
observaciones >= 5 y P80 de Google <= 30 minutos
```

El uso de percentiles en lugar del promedio sigue la práctica de la Federal Highway Administration de Estados Unidos: su medida oficial de confiabilidad, *Level of Travel Time Reliability* (LOTTR), es el tiempo de viaje del percentil 80 dividido entre el tiempo "normal" del percentil 50 ([23 CFR § 490.511](https://www.law.cornell.edu/cfr/text/23/490.511); [preguntas frecuentes de la FHWA](https://www.fhwa.dot.gov/tpm/faq.cfm)), y su guía [*Travel Time Reliability: Making It There On Time, All The Time*](https://ops.fhwa.dot.gov/publications/tt_reliability/TTR_Report.htm) explica por qué un promedio no describe la confiabilidad. Esa norma se diseñó para tramos carreteros con muchas mediciones; aquí se adopta por analogía para ETA de transporte público con muestras de entre 1 y 9 observaciones por parada, por lo que el P80 es preliminar.

Las clasificaciones laboral y fin de semana se conservan como contexto, pero no se filtran todavía porque la muestra de algunos grupos es pequeña.

## Resultados de accesibilidad

| Indicador | Resultado |
|---|---:|
| Paradas con acceso confiable | 329 |
| Paradas con conexión GTFS directa | 15 |
| Paradas cuyo camino incluye transbordos | 314 |
| Itinerarios diferentes | 79 |
| Rutas públicas diferentes presentes en los itinerarios | 51 |
| Paradas confiables con tiempo de red GTFS ≤ 30 min | 107 |
| Paradas confiables con tiempo de red GTFS > 30 min | 222 |

### Principales rutas presentes en los itinerarios

Una parada puede utilizar varias rutas. Por ello la columna de paradas no debe sumarse entre filas. C54 aparece en las 329 porque es el último tramo de todos los caminos actuales; solo 15 paradas tienen una conexión completamente directa mediante C54.

| Ruta | Paradas cuyos caminos la utilizan | P50 observado mínimo–máximo | P80 observado mínimo–máximo | Mediana de observaciones |
|---|---:|---:|---:|---:|
| C54 | 329 | 4.55–29.92 | 5.00–29.96 | 9 |
| C33 | 219 | 6.65–29.82 | 6.65–29.85 | 9 |
| C62 | 56 | 5.00–29.92 | 5.00–29.96 | 7 |
| C46 | 49 | 6.65–25.48 | 6.65–27.61 | 9 |
| C52 | 29 | 9.42–29.73 | 11.83–29.73 | 7 |
| C22 | 28 | 9.42–29.78 | 11.83–29.78 | 7 |
| C34 | 27 | 7.33–29.82 | 7.33–29.82 | 9 |
| C55 | 22 | 7.33–29.73 | 7.33–29.85 | 7 |
| L154 | 22 | 15.67–29.73 | 15.84–29.73 | 7 |
| T07 | 20 | 5.00–28.27 | 5.00–28.27 | 7 |
| C24 | 19 | 16.85–29.47 | 17.52–29.80 | 9 |
| C68 | 19 | 14.60–29.65 | 15.06–29.96 | 7 |

El detalle completo de las 51 rutas está en [`rutas_acceso_corregidora.csv`](../data/processed/rutas_acceso_corregidora.csv).

### Itinerarios con mayor cobertura inicial

| Itinerario | Tipo | Transbordos | Paradas de origen | P80 promedio | Rango P80 |
|---|---|---:|---:|---:|---:|
| C54 | Directa | 0 | 15 | 15.63 | 9.77–21.93 |
| C33 → C54 | Con transbordo | 1 | 22 | 19.79 | 10.50–28.65 |
| L154 → C54 | Con transbordo | 1 | 10 | 22.30 | 15.84–29.63 |
| T07 → C54 | Con transbordo | 1 | 3 | 24.07 | 18.22–27.67 |
| C62 → C54 | Con transbordo | 1 | 5 | 23.20 | 18.94–29.79 |
| T03 → C54 | Con transbordo | 1 | 1 | 23.15 | 23.15–23.15 |
| C46 → C33 → C54 | Con transbordo | 2 | 18 | 17.01 | 8.90–27.61 |
| C69 → C33 → C54 | Con transbordo | 2 | 6 | 14.23 | 8.98–26.40 |
| C22 → C33 → C54 | Con transbordo | 2 | 10 | 19.22 | 12.83–28.92 |
| C34 → C62 → C54 | Con transbordo | 2 | 3 | 15.24 | 13.67–16.45 |

El detalle completo de los 79 itinerarios está en [`itinerarios_acceso_corregidora.csv`](../data/processed/itinerarios_acceso_corregidora.csv).

### Muestra de paradas con menor P80

| stop_id | Parada | Itinerario GTFS | Transbordos | Red GTFS | P50 Google | P80 Google | n |
|---|---|---|---:|---:|---:|---:|---:|
| 5200 | Calle Nicolás Bravo/Calle Primavera | T07 → T03 → C62 → C54 | 3 | 44.70 | 5.00 | 5.00 | 9 |
| 3263 | San Agustín del Retablo/Salvador Galván | C53 → C46 → C33 → C54 | 3 | 37.20 | 6.65 | 6.65 | 9 |
| 5193 | San Agustín del Retablo/Estío | C53 → C46 → C33 → C54 | 3 | 36.25 | 6.92 | 6.92 | 9 |
| 2680 | Av. Universidad/Calle Ezequiel Montes | C55 → C34 → C62 → C54 | 3 | 37.18 | 7.33 | 7.33 | 9 |
| 2316 | Calle Nicolás Bravo/Calle Segunda de Las Rosas | T07 → T03 → C62 → C54 | 3 | 45.65 | 7.92 | 7.92 | 9 |
| 5194 | Av. Universidad/Calle Rafael Osuna | C54 → C35 → C33 → C54 | 3 | 44.08 | 8.48 | 8.48 | 9 |
| 5070 | San Agustín del Retablo | C53 → C46 → C33 → C54 | 3 | 37.97 | 7.77 | 8.86 | 9 |
| 2394 | Av. Universidad/Calle Nicolás Bravo | C46 → C33 → C54 | 2 | 31.47 | 8.90 | 8.90 | 9 |
| 2315 | Av. Universidad/San Andrés | C69 → C33 → C54 | 2 | 34.03 | 8.98 | 8.98 | 9 |
| 2342 | Ezequiel Montes/Mariano Escobedo | C46 → C33 → C54 | 2 | 30.62 | 9.42 | 9.42 | 9 |
| 2341 | Av. Felipe Ángeles/Av. San Roque | C54 | 0 | 1.53 | 4.55 | 9.77 | 9 |
| 4256 | Epigmenio González/Departamental Parques | C54 | 0 | 5.37 | 9.77 | 9.77 | 9 |

La tabla completa de las 329 paradas, con nombres, itinerarios, transbordos, GTFS, P50, P80, observaciones y contexto temporal, está en [`paradas_acceso_corregidora.csv`](../data/processed/paradas_acceso_corregidora.csv).

## Cómo se obtuvo la demanda potencial

### 1. Selección de paradas

Se utilizaron las 329 paradas clasificadas como acceso confiable y que poseen al menos un segmento dibujable hacia el destino. Las paradas aisladas se excluyen.

### 2. Buffer alrededor de las paradas

Las paradas se proyectaron a `EPSG:32614`, un sistema métrico apropiado para Querétaro. Se creó un buffer de 20 metros alrededor de cada punto y después se calculó la unión de todos los buffers. La unión evita contar dos veces las áreas donde se superponen paradas cercanas.

### 3. Cruce con las manzanas del INEGI

Se descargaron 44,827 manzanas de Querétaro. Para cada manzana intersectada se conserva la fracción de área cubierta como referencia y se cuenta la población completa de la manzana:

```text
fracción cubierta = área de la manzana dentro del buffer / área total de la manzana
```

La medida principal sigue la regla solicitada: si el buffer toca la manzana, se incluye toda su población. El prorrateo anterior se conserva en una columna separada para comparación:

```text
población incluida = población total de la manzana intersectada
población prorrateada = población de la manzana × fracción cubierta
```

Finalmente se sumó la población incluida de todas las manzanas intersectadas. Es un conteo de bloques censales completos, no una localización de domicilios.

## Resultado de demanda potencial

| Indicador | Resultado |
|---|---:|
| Radio del buffer | 20 m |
| Paradas incluidas | 329 |
| Manzanas del conjunto INEGI | 44,827 |
| Manzanas intersectadas | 395 |
| Manzanas sin población numérica | 3,248 |
| Población numérica representada en manzanas | 1,854,152 |
| Población estatal reportada por INEGI | 2,368,467 |
| Población de manzanas completas intersectadas | **42,149** |
| Porcentaje sobre población en manzanas | 2.2731 % |
| Porcentaje sobre población estatal | 1.7796 % |
| Estimación prorrateada conservada para comparación | 1,428.19 |
| Población mediante punto representativo | 229 |

Los valores responden a supuestos espaciales distintos:

- **42,149:** población de todas las manzanas tocadas por los buffers;
- **1,428.19:** prorrateo por fracción de área, conservado para comparación;
- **229:** solo cuenta manzanas cuyo punto representativo cae dentro de la cobertura;

La diferencia refleja el cambio de unidad de análisis: el buffer cubre una fracción pequeña de varias manzanas, pero la medida principal incluye bloques completos.

### Comparación por umbral de tiempo

Los escenarios usan acceso confiable cuando hay al menos cinco observaciones y P80 histórico menor o igual al umbral. Son acumulados, no intervalos excluyentes.

| P80 máximo | Paradas | Manzanas tocadas | Población de manzanas completas |
|---:|---:|---:|---:|
| 5 min | 1 | 4 | 617 |
| 15 min | 64 | 76 | 11,498 |
| 30 min | 329 | 395 | 42,149 |

Los resultados detallados se exportan en `resumen_acceso_5_15_30_min.csv`, `paradas_acceso_5_15_30_min.csv` y `manzanas_acceso_{5,15,30}_min.csv`.

## Advertencias de interpretación

### Diferencia entre el camino GTFS y Google

De las 329 paradas clasificadas como confiables por P80, 222 tienen un tiempo de red GTFS superior a 30 minutos. La diferencia `P80 - GTFS` tiene una mediana de aproximadamente −9.4 minutos y en algunos casos llega a −39.7 minutos.

Esto no significa que los autobuses circulen 39 minutos más rápido que el horario. Probablemente Google eligió otro itinerario, otra parada, una combinación de rutas diferente o una caminata que la matriz actual no permite identificar. La columna `route_id_principal` procede del camino GTFS, no de una confirmación de la línea utilizada por Google.

Por tanto, la cifra de 42,149 personas debe describirse como **población censada en manzanas tocadas bajo el criterio P80 vigente**, no como una medición definitiva de cobertura operativa.

Para una estimación conservadora se recomienda recalcular un segundo escenario que exija simultáneamente:

```text
P80 Google <= 30 minutos
y tiempo de red GTFS <= 30 minutos
```

Actualmente 107 paradas cumplen ambas condiciones.

### Radio de 20 metros

Un radio de 20 metros mide cercanía inmediata a la parada, no una zona peatonal habitual. Para planeación de transporte conviene presentar un análisis de sensibilidad con 20, 200, 400 y 500 metros, preferentemente utilizando distancia caminable por la red de calles y barreras físicas.

### Antigüedad censal

La población corresponde a 2020. No captura crecimiento urbano ni redistribución residencial posterior.

### Transbordos

La penalización fija de cinco minutos aproxima espera y conexión. No garantiza que los horarios reales de dos rutas estén sincronizados.

## Archivos reproducibles

- [`02_RutasQroBus.ipynb`](../notebooks/02_RutasQroBus.ipynb): caminos, clasificación, mapas y demanda.
- [`01_PromedioRutas.ipynb`](../notebooks/01_PromedioRutas.ipynb): GTFS, Dijkstra e histórico de Google.
- [`03_TiemposTotalesRutasGTFS.ipynb`](../notebooks/03_TiemposTotalesRutasGTFS.ipynb): duración total y calibración P50/P80 por segmentos.
- [`demanda_potencial_resumen.json`](../data/processed/demanda_potencial_resumen.json): indicadores de demanda.
- [`demanda_potencial_manzanas.csv`](../data/processed/demanda_potencial_manzanas.csv): detalle de manzanas intersectadas.
- [`paradas_acceso_corregidora.csv`](../data/processed/paradas_acceso_corregidora.csv): detalle completo de paradas.
- [`itinerarios_acceso_corregidora.csv`](../data/processed/itinerarios_acceso_corregidora.csv): resumen de itinerarios.
- [`rutas_acceso_corregidora.csv`](../data/processed/rutas_acceso_corregidora.csv): resumen por ruta pública.

Los resultados dependen del GTFS, el histórico de Google, la configuración del umbral y el radio existentes en la fecha de ejecución. Deben regenerarse cuando cualquiera de esas entradas cambie.
