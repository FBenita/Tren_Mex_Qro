# Reporte de demanda potencial y accesibilidad QroBus hacia Corregidora

Fecha de actualización: 2 de noviembre de 2026.

## Resumen ejecutivo

El análisis identifica **327 paradas** con acceso confiable hacia la estación Corregidora: tienen al menos cinco observaciones históricas y su ETA P80 de Google es menor o igual a 30 minutos. De ellas, 15 tienen una conexión directa en el camino GTFS calculado y 312 requieren uno o más transbordos.

Alrededor de esas 327 paradas se trazó un buffer de 400 m de radio (800 m de diámetro) y se cruzó la unión de buffers con la **malla geoestadística del INEGI de nivel 9**, proporcionada por el Instituto de Movilidad. Al prorratear la población de cada celda por la fracción de su superficie cubierta, la cobertura suma **227,442 personas**, el 9.60 % de la población estatal del Censo 2020. Si se contaran completas todas las celdas tocadas, el techo sería de 323,435 personas.

Este resultado es una aproximación espacial. No significa que 227,442 personas usen actualmente QroBus o el tren: es la población censada que vive cerca de paradas clasificadas como accesibles según el criterio vigente.

## Fuentes de información

### GTFS de QroBus

Se utilizaron los siguientes archivos locales:

- `stops.txt`: identificador, nombre y coordenadas de cada parada;
- `routes.txt`: identificador y nombre público de cada ruta;
- `trips.txt`: relación entre viajes y rutas;
- `stop_times.txt`: orden y horario programado de las paradas.

El conjunto no contiene `calendar.txt`, `calendar_dates.txt` ni `shapes.txt`. Por ello no se determina qué servicios operan en una fecha concreta, y las líneas del mapa unen paradas consecutivas por el camino más probable sobre la red vial de OpenStreetMap, que puede diferir del derrotero oficial.

### Histórico de Google Routes API

El histórico local contiene estimaciones de viaje en transporte público desde distintas paradas hacia la estación. Google puede incluir espera, caminata, transbordos y rutas alternativas. Por tanto, la ETA se utiliza como un **proxy del tiempo para el pasajero**, no como medición del atraso operativo de una unidad QroBus.

### Malla geoestadística del INEGI

La población procede del **Censo de Población y Vivienda 2020** agregado en la malla geoestadística del INEGI de nivel 9, que proporcionó el Instituto de Movilidad (`data/InegiMalla/`):

- `Datos totales.csv`: 38,937 celdas de Querétaro y zonas vecinas.
- `Datos filtrados.csv`: las seis celdas que rodean la estación (11,548 personas), usadas para validar la geometría.

Cada celda es un cuadro de unos 468 m por lado (0.219 km², unas 22 hectáreas). Antes se usaban las manzanas del servicio del INEGI; como ambas fuentes dan resultados muy parecidos, se adoptó la malla, que es uniforme y no depende de descargas externas.

Los CSV no incluyen geometría. `src/scripts/malla_inegi.py` reconstruye cada celda desde su código rHEALPix y corrige la latitud con una calibración contra las manzanas del censo: con ella, la población de cada celda y la de las manzanas que contiene tienen una correlación de 0.99. Es una reconstrucción validada, no la geometría oficial.

### OpenStreetMap

La red vial se usa para trazar las rutas por calles, y la red peatonal del lado sur de la vía para medir el último tramo a pie del escenario sin cruces. Datos © colaboradores de OpenStreetMap, ODbL.

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

Se construyó un grafo dirigido y se aplicó Dijkstra en sentido inverso desde la parada destino. El estado del algoritmo considera la parada y la ruta utilizada. Cambiar de ruta agrega una penalización configurada de cinco minutos. Los transbordos solo ocurren en la misma parada.

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

El uso de percentiles en lugar del promedio sigue la práctica de la Federal Highway Administration de Estados Unidos: su medida oficial de confiabilidad, *Level of Travel Time Reliability* (LOTTR), es el tiempo de viaje del percentil 80 dividido entre el tiempo "normal" del percentil 50 ([23 CFR § 490.511](https://www.law.cornell.edu/cfr/text/23/490.511); [preguntas frecuentes de la FHWA](https://www.fhwa.dot.gov/tpm/faq.cfm)), y su guía [*Travel Time Reliability: Making It There On Time, All The Time*](https://ops.fhwa.dot.gov/publications/tt_reliability/TTR_Report.htm) explica por qué un promedio no describe la confiabilidad. Esa norma se diseñó para tramos carreteros con muchas mediciones; aquí se adopta por analogía para ETA de transporte público con muestras de entre 8 y 10 observaciones por parada entre las paradas confiables, por lo que el P80 es preliminar.

Las clasificaciones laboral y fin de semana se conservan como contexto, pero no se filtran todavía porque la muestra de algunos grupos es pequeña.

## Resultados de accesibilidad

| Indicador | Resultado |
|---|---:|
| Paradas con acceso confiable | 327 |
| Paradas con conexión GTFS directa | 15 |
| Paradas cuyo camino incluye transbordos | 312 |
| Itinerarios diferentes | 79 |
| Rutas públicas diferentes presentes en los itinerarios | 50 |
| Paradas confiables con tiempo de red GTFS ≤ 30 min | 105 |
| Paradas confiables con tiempo de red GTFS > 30 min | 222 |

### Principales rutas presentes en los itinerarios

Una parada puede utilizar varias rutas. Por ello la columna de paradas no debe sumarse entre filas. C54 aparece en las 327 porque es el último tramo de todos los caminos actuales; solo 15 paradas tienen una conexión completamente directa mediante C54.

| Ruta | Paradas cuyos caminos la utilizan | P50 observado mínimo–máximo | P80 observado mínimo–máximo | Mediana de observaciones |
|---|---:|---:|---:|---:|
| C54 | 327 | 4.55–29.92 | 5.00–29.99 | 10 |
| C33 | 218 | 6.65–29.78 | 6.65–29.87 | 10 |
| C62 | 55 | 5.00–29.92 | 5.00–29.92 | 8 |
| C46 | 49 | 6.65–25.48 | 6.65–27.58 | 10 |
| C52 | 30 | 9.42–29.73 | 11.83–29.99 | 8 |
| C22 | 28 | 9.42–29.78 | 11.83–29.78 | 8 |
| C34 | 27 | 7.33–29.12 | 7.33–29.72 | 10 |
| L154 | 23 | 15.67–29.73 | 15.75–29.99 | 8 |
| C55 | 20 | 7.33–29.73 | 7.33–29.73 | 8 |
| T07 | 20 | 5.00–28.27 | 5.00–28.27 | 8 |
| C24 | 19 | 17.12–29.47 | 17.55–29.47 | 10 |
| C68 | 19 | 14.77–28.98 | 14.99–29.88 | 8 |

El detalle completo de las 50 rutas está en [`rutas_acceso_corregidora.csv`](../data/processed/rutas_acceso_corregidora.csv).

### Itinerarios con mayor cobertura inicial

| Itinerario | Tipo | Transbordos | Paradas de origen | P80 promedio | Rango P80 |
|---|---|---:|---:|---:|---:|
| C54 | Directa | 0 | 15 | 15.64 | 9.77–21.93 |
| C33 → C54 | Con transbordo | 1 | 22 | 19.67 | 10.50–28.65 |
| L154 → C54 | Con transbordo | 1 | 10 | 22.31 | 15.75–29.63 |
| T07 → C54 | Con transbordo | 1 | 3 | 24.03 | 18.11–27.67 |
| C62 → C54 | Con transbordo | 1 | 5 | 22.61 | 18.54–29.09 |
| T03 → C54 | Con transbordo | 1 | 1 | 23.15 | 23.15–23.15 |
| C46 → C33 → C54 | Con transbordo | 2 | 18 | 16.83 | 8.90–27.44 |
| C69 → C33 → C54 | Con transbordo | 2 | 6 | 14.21 | 8.98–26.30 |
| C22 → C33 → C54 | Con transbordo | 2 | 10 | 18.99 | 12.83–28.43 |
| C34 → C62 → C54 | Con transbordo | 2 | 3 | 15.23 | 13.67–16.45 |

El detalle completo de los 79 itinerarios está en [`itinerarios_acceso_corregidora.csv`](../data/processed/itinerarios_acceso_corregidora.csv).

### Muestra de paradas con menor P80

| stop_id | Parada | Itinerario GTFS | Transbordos | Red GTFS | P50 Google | P80 Google | n |
|---|---|---|---:|---:|---:|---:|---:|
| 5200 | Calle Nicolás Bravo/Calle Primavera | T07 → T03 → C62 → C54 | 3 | 44.70 | 5.00 | 5.00 | 10 |
| 3263 | San Agustín del Retablo/Salvador Galván | C53 → C46 → C33 → C54 | 3 | 37.20 | 6.65 | 6.65 | 10 |
| 5193 | San Agustín del Retablo/Estío | C53 → C46 → C33 → C54 | 3 | 36.25 | 6.92 | 6.92 | 10 |
| 2680 | Av. Universidad/Calle Ezequiel Montes | C55 → C34 → C62 → C54 | 3 | 37.18 | 7.33 | 7.33 | 10 |
| 2316 | Calle Nicolás Bravo/Calle Segunda de Las Rosas | T07 → T03 → C62 → C54 | 3 | 45.65 | 7.92 | 7.92 | 10 |
| 5194 | Av. Universidad/Calle Rafael Osuna | C54 → C35 → C33 → C54 | 3 | 44.08 | 8.48 | 8.48 | 10 |
| 5070 | San Agustín del Retablo | C53 → C46 → C33 → C54 | 3 | 37.97 | 7.77 | 8.58 | 10 |
| 2394 | Av. Universidad/Calle Nicolás Bravo | C46 → C33 → C54 | 2 | 31.47 | 8.90 | 8.90 | 10 |
| 2315 | Av. Universidad/San Andrés | C69 → C33 → C54 | 2 | 34.03 | 8.98 | 8.98 | 10 |
| 2342 | Ezequiel Montes/Mariano Escobedo | C46 → C33 → C54 | 2 | 30.62 | 9.42 | 9.42 | 10 |
| 2318 | Av. Felipe Ángeles/Arena Querétaro | T07 → T03 → C62 → C54 | 3 | 40.95 | 6.20 | 9.56 | 8 |
| 2341 | Av. Felipe Ángeles/Av. San Roque | C54 | 0 | 1.53 | 4.55 | 9.77 | 10 |

La tabla completa de las 327 paradas, con nombres, itinerarios, transbordos, GTFS, P50, P80, observaciones y contexto temporal, está en [`paradas_acceso_corregidora.csv`](../data/processed/paradas_acceso_corregidora.csv).

## Parámetros de caminata

El proyecto usa tres parámetros de caminata comunes, definidos en `src/scripts/config.py` y modificables en `.env`.

| Parámetro | Valor | Uso |
|---|---|---|
| Velocidad (`VELOCIDAD_CAMINATA_KMH`) | 4 km/h (1.11 m/s) | Último tramo a pie del escenario sin cruces, ruta óptima del mapa de demanda y conexiones a pie entre rutas. |
| Factor de desvío (`FACTOR_DESVIO_CAMINATA`) | 1.25 | Convierte la línea recta en distancia por calles en el mapa de demanda y en las conexiones a pie. |
| Radio de búsqueda (`RADIO_BUSQUEDA_PARADA_M`) | 800 m en línea recta | Paradas candidatas alrededor de un punto del mapa de demanda. |

### Velocidad de caminata: 4 km/h

| Fuente | Valor reportado |
|---|---|
| Weidmann (1993), revisión de literatura, retomada por [Bosina y Weidmann (2017)](https://econpapers.repec.org/RePEc:eee:phsmap:v:468:y:2017:i:c:p:1-29) | Promedio de 1.34 m/s (4.8 km/h); rango de 0.97 a 1.65 m/s |
| [Bohannon y Andrews (2011)](https://bacpar.csp.org.uk/node/338279), meta-análisis con 23,111 personas | De 1.43 m/s (hombres de 40 a 49 años) a 0.94 m/s (mujeres de 80 a 99 años) |
| Manual TCQSM, citado en [Giannoulaki y Christoforou (2024)](https://www.mdpi.com/2071-1050/16/11/4813/html) | 1.25 m/s para diseño; 1.2 m/s para tiempos de semáforo |
| [Estudio de adultos mayores en el Reino Unido](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5536437/) | Hasta 84 % de los hombres y 93 % de las mujeres mayores de 65 años no alcanzan 1.2 m/s |

Se eligió 4 km/h (1.11 m/s) como valor conservador: queda debajo del promedio de los adultos y del estándar de semáforos, y por encima de la velocidad típica de los adultos mayores (0.8 a 0.9 m/s). Así la estimación incluye a personas mayores, niños y cruces con espera, en línea con el criterio conservador del P80. Antes se usaban 80 m/min (4.8 km/h), el promedio de los adultos.

### Factor de desvío: 1.25

El factor de desvío (*circuity* o *pedestrian route directness*) es el cociente entre la distancia por calles y la distancia en línea recta.

| Fuente | Valor reportado |
|---|---|
| [O'Sullivan y Morrall (1996)](https://www.academia.edu/87338913/Walking_Distances_to_and_from_Light_Rail_Transit_Stations), caminatas medidas a estaciones de tren ligero en Calgary, citado en [Levinson y El-Geneidy](https://core.ac.uk/download/76364877.pdf) | Entre 1.21 y 1.24 |
| Estudio de la red ferroviaria de Londres (basado en Ballou et al.) | Escenarios de 1.2 y 1.5 |
| [Giacomin y Levinson (2015)](https://econpapers.repec.org/RePEc:sae:envirb:v:42:y:2015:i:6:p:1040-1053) | El desvío es mayor en trayectos cortos |
| [Gutiérrez y García-Palomares (2008)](https://econpapers.repec.org/RePEc:sae:envirb:v:35:y:2008:i:3:p:480-503) | Los buffers en línea recta sobreestiman la población cubierta; la distancia por red predice mejor el uso del transporte |

Se tomó 1.25, un poco arriba de lo medido en Calgary, porque Querétaro tiene barreras como la vía del tren y vialidades sin cruce. Antes se usaba 1.3.

### Radio de búsqueda de paradas: 800 m

| Fuente | Distancia |
|---|---|
| Estándar de la industria del transporte | 400 m para autobús; 800 m para tren |
| [El-Geneidy et al. (2014)](https://www.worldtransitresearch.info/research/5119), caminatas reales en Montreal | Percentil 85 de 524 m para autobús |
| [Estudio de San José, Costa Rica](https://revistalatam.redilat.org/index.php/lt/article/download/1677/2361/2753), caminatas medidas a paradas de autobús | Mediana de 255 m, percentil 85 de 525 m, percentil 95 de 740 m |
| [ITDP México](https://itdp.org/?p=5745) | 800 m (unos 10 minutos) para estaciones de transporte masivo |

Con el factor de desvío, 800 m en línea recta son unos 1,000 m por calles, cerca del límite superior de lo observado. El radio solo define las paradas candidatas: el ordenamiento suma la caminata al P80, así que una parada lejana solo se elige si su tiempo en autobús lo compensa. Antes se usaban 1,000 m.

El buffer de demanda de 400 m de radio es coherente con estos valores: con el factor de desvío equivale a unos 500 m por calles y 7.5 minutos a 4 km/h, prácticamente el percentil 85 de El-Geneidy et al. (524 m).

### Efecto en el escenario sin cruces de la vía

En este escenario el último tramo a pie se mide sobre la red peatonal de OpenStreetMap y se limita a diez minutos. Con 4 km/h el límite pasó de 800 m a unos 667 m: cuatro paradas perdieron su acceso a pie y las paradas que llegan en 30 minutos o menos según GTFS bajaron de 179 a 134.

### Limitaciones

Varias cifras provienen del resumen de cada artículo o de fuentes que lo citan, no de la lectura del texto completo. Ningún estudio es de Querétaro. Para un valor local convendría medir distancias peatonales sobre la red de OpenStreetMap de toda la zona o levantar encuestas de acceso a paradas.

## Cómo se obtuvo la demanda potencial

### 1. Selección de paradas

Se utilizaron las 327 paradas clasificadas como acceso confiable que tienen al menos un segmento dibujable hacia el destino. Las paradas aisladas se excluyen.

### 2. Buffer alrededor de las paradas

Las paradas se proyectaron a `EPSG:32614`, un sistema métrico apropiado para Querétaro. Se creó un buffer de 400 m de radio alrededor de cada punto (`RADIO_DEMANDA_M`) y después se calculó la unión de todos los buffers. La unión evita contar dos veces las áreas donde se superponen paradas cercanas.

### 3. Cruce con la malla geoestadística

Para cada celda tocada por la unión de buffers se calculó la fracción de su superficie cubierta y se prorrateó cada indicador por esa fracción, suponiendo población uniforme dentro de la celda:

```text
fracción cubierta = área de la celda dentro de los buffers / área total de la celda
población prorrateada = población de la celda × fracción cubierta
```

La suma de las poblaciones prorrateadas es el resultado principal. La suma de celdas completas se reporta solo como techo.

Cuidados con estos datos:

- Los valores negativos (`-6`, `-7`, `-9`) son códigos del INEGI para datos reservados o no disponibles; se tratan como vacíos y no suman.
- La malla publica población de 60 años o más, no de 65 o más.
- No trae mujeres y hombres por separado; se estiman con la relación hombres-mujeres (`REL_H_M`) de cada celda.

## Resultado de demanda potencial

| Indicador | Resultado |
|---|---:|
| Radio del buffer | 400 m |
| Paradas incluidas | 327 |
| Celdas de la malla | 38,937 |
| Celdas tocadas | 249 |
| Población prorrateada | **227,442** |
| Población de celdas completas (techo) | 323,435 |
| Población estatal, Censo 2020 | 2,368,467 |
| Porcentaje sobre población estatal | 9.60 % |

### Comparación por umbral de tiempo

Los escenarios usan acceso confiable cuando hay al menos cinco observaciones y P80 histórico menor o igual al umbral. Son acumulados, no intervalos excluyentes.

| P80 máximo | Paradas | Celdas tocadas | Población prorrateada | Celdas completas (techo) |
|---:|---:|---:|---:|---:|
| 5 min | 1 | 8 | 3,912 | 14,451 |
| 15 min | 66 | 54 | 48,158 | 62,378 |
| 30 min | 327 | 249 | 227,442 | 323,435 |
| 45 min | 775 | 529 | 533,057 | 656,846 |
| 60 min | 1,019 | 662 | 690,982 | 817,840 |

### Desglose por sexo y edad (prorrateado)

| P80 máximo | Mujeres (est.) | Hombres (est.) | 0-14 años | 60 años o más | Con discapacidad | PEA | Viviendas habitadas |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 5 min | 2,068 | 1,844 | 526 | 896 | 250 | 2,236 | 1,289 |
| 15 min | 25,126 | 23,032 | 7,012 | 9,530 | 2,663 | 27,470 | 15,000 |
| 30 min | 117,987 | 109,450 | 38,838 | 37,965 | 10,960 | 128,970 | 67,325 |
| 45 min | 274,854 | 258,170 | 101,946 | 73,254 | 22,419 | 299,490 | 155,217 |
| 60 min | 355,483 | 335,462 | 137,752 | 87,746 | 28,145 | 387,104 | 200,827 |

Las celdas con datos reservados no suman a ese indicador, por lo que los grupos de edad, discapacidad y PEA son un mínimo.

Los resultados detallados se exportan en `resumen_acceso_5_15_30_45_60_min.csv`, `personas_acceso_5_15_30_45_60_min.csv`, `paradas_acceso_5_15_30_45_60_min.csv` y `celdas_acceso_{5,15,30,45,60}_min.csv`.

## Advertencias de interpretación

### Diferencia entre el camino GTFS y Google

De las 327 paradas clasificadas como confiables por P80, 222 tienen un tiempo de red GTFS superior a 30 minutos. La diferencia `P80 - GTFS` tiene una mediana de aproximadamente −9.4 minutos y en algunos casos llega a −39.7 minutos.

Esto no significa que los autobuses circulen 39 minutos más rápido que el horario. Probablemente Google eligió otro itinerario, otra parada, una combinación de rutas diferente o una caminata que la matriz actual no permite identificar. La columna `route_id_principal` procede del camino GTFS, no de una confirmación de la línea utilizada por Google.

Por tanto, la cifra de 227,442 personas debe describirse como **población censada cerca de paradas confiables bajo el criterio P80 vigente**, no como una medición definitiva de cobertura operativa.

Para una estimación conservadora se recomienda recalcular un segundo escenario que exija simultáneamente:

```text
P80 Google <= 30 minutos
y tiempo de red GTFS <= 30 minutos
```

Actualmente 105 paradas cumplen ambas condiciones.

### Distancia en línea recta

El buffer de 400 m se mide en línea recta y el factor de desvío solo lo aproxima. Para planeación conviene un análisis de sensibilidad con varios radios (200, 400 y 500 m) y, de preferencia, áreas de servicio medidas sobre la red peatonal con sus barreras físicas.

### Unidad espacial

Cada celda mide unos 468 m por lado y el prorrateo supone población uniforme dentro de ella. En celdas con parques, industria o grandes vialidades, la población real puede concentrarse lejos o cerca de la parada.

### Antigüedad censal

La población corresponde a 2020. No captura crecimiento urbano ni redistribución residencial posterior.

### Transbordos

La penalización fija de cinco minutos aproxima espera y conexión. No garantiza que los horarios reales de dos rutas estén sincronizados.

## Archivos reproducibles

- [`01_PromedioRutas.ipynb`](../src/notebooks/01_PromedioRutas.ipynb): GTFS, Dijkstra e histórico de Google.
- [`02_RutasQroBus.ipynb`](../src/notebooks/02_RutasQroBus.ipynb): caminos, clasificación, mapas y demanda.
- [`03_TiemposTotalesRutasGTFS.ipynb`](../src/notebooks/03_TiemposTotalesRutasGTFS.ipynb): duración total, calibración P50/P80 por segmentos y conexiones entre rutas.
- [`config.py`](../src/scripts/config.py): parámetros compartidos, incluidos los de caminata.
- [`demanda_potencial_resumen.json`](../data/processed/demanda_potencial_resumen.json): indicadores de demanda.
- [`demanda_potencial_celdas.csv`](../data/processed/demanda_potencial_celdas.csv): detalle de celdas tocadas.
- [`paradas_acceso_corregidora.csv`](../data/processed/paradas_acceso_corregidora.csv): detalle completo de paradas.
- [`itinerarios_acceso_corregidora.csv`](../data/processed/itinerarios_acceso_corregidora.csv): resumen de itinerarios.
- [`rutas_acceso_corregidora.csv`](../data/processed/rutas_acceso_corregidora.csv): resumen por ruta pública.

Los resultados dependen del GTFS, el histórico de Google, la configuración del umbral, el radio y los parámetros de caminata existentes en la fecha de ejecución. Deben regenerarse cuando cualquiera de esas entradas cambie.
