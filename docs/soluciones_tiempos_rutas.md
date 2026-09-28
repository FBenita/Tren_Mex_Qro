# Propuestas para obtener el tiempo total de las rutas QroBus

## Qué tiempo se quiere medir

Antes de elegir una fuente conviene separar tres métricas:

1. **Tiempo programado:** duración publicada entre la primera y la última parada.
2. **Tiempo observado:** duración que realmente hizo un autobús concreto.
3. **Tiempo para el pasajero:** espera + recorrido + transbordos + caminatas.

No son intercambiables. Google Transit se aproxima a la tercera; el GTFS estático permite calcular la primera. Para evaluar la operación se necesita la segunda.

## Solución aplicada: GTFS más calibración histórica P50/P80

El notebook autosuficiente `scripts/TiemposTotalesRutasGTFS.ipynb` presenta el análisis completo. No realiza llamadas nuevas a Google: utiliza el GTFS y, si existe, el histórico local creado previamente por `PromedioRutas.ipynb`.

Para cada `trip_id` calcula primero la línea base programada:

```text
duración = llegada de la última parada - salida de la primera parada
```

Después agrupa por `route_id` y `direction_id` y entrega mínimo, percentil 10, mediana, promedio, percentil 90 y máximo. La mediana es el valor de referencia porque un mismo recorrido puede tener duraciones programadas distintas según el horario.

### Modelo de atraso aplicado

Las observaciones históricas válidas de Google se comparan con el tiempo GTFS hacia Corregidora. Para cada percentil se ajusta el modelo:

```text
tiempo_estimado = constante + factor × tiempo_GTFS
```

Se calculan dos escenarios independientes:

```text
P50 = constante_P50 + factor_P50 × GTFS
P80 = constante_P80 + factor_P80 × GTFS
```

La calibración usa pérdida cuantílica y pondera las observaciones por recencia con una semivida de 14 días. Para representar únicamente atraso adicional se imponen dos restricciones:

- `constante >= 0`;
- `factor >= 1`.

Por tanto, el modelo calibrado nunca reduce el tiempo programado. Las rutas requieren por lo menos 30 observaciones y un rango de tiempos GTFS de 10 minutos para obtener un modelo propio. Aun cuando cumplen esos criterios, sus parámetros se suavizan hacia el modelo global según el tamaño y la diversidad de su muestra. Las rutas restantes usan directamente el modelo global.

Con el histórico disponible al ejecutar esta versión se utilizaron 7,960 observaciones válidas y 41 rutas obtuvieron una calibración propia suavizada. El modelo global resultó:

```text
P50 = 0.00 + 1.000 × GTFS
P80 = 6.16 + 1.000 × GTFS
```

Esto significa que el conjunto actual no respalda un incremento global para el escenario habitual P50. Para P80 sí aparece un margen conservador aproximado de 6.16 minutos, aplicado una sola vez por viaje. Estos parámetros cambiarán automáticamente cuando cambie el histórico.

### Propagación hacia atrás por segmentos

Para cada ruta y sentido se selecciona el viaje cuya duración está más cerca de la mediana. Sus paradas se ordenan por `stop_sequence` y se calcula cada segmento:

```text
segmento_GTFS = llegada_siguiente - salida_actual
segmento_P50 = segmento_GTFS × factor_P50
segmento_P80 = segmento_GTFS × factor_P80
```

Los tiempos pequeños de segmento no proceden directamente de Google. La matriz actual entrega una duración completa origen-destino; el modelo aprende la relación entre esa duración y el camino GTFS y después distribuye el componente proporcional mediante el factor. Por ello los segmentos corregidos son estimaciones modeladas.

Después se realiza una suma acumulada inversa desde la última parada. Así se obtiene, para cada parada, el tiempo restante hasta el final de la ruta. La constante se agrega una sola vez al tiempo del pasajero y no se repite en cada segmento:

```text
tiempo_operativo = suma(segmentos corregidos)
tiempo_pasajero = constante + suma(segmentos corregidos)
```

El notebook genera:

- `data/processed/tiempos_totales_rutas_gtfs.csv`: resumen por ruta y sentido con GTFS, P50, P80 y calidad del modelo;
- `data/processed/calibracion_tiempos_rutas_google.csv`: constantes, factores, observaciones y peso de suavizado;
- `data/processed/tiempos_acumulados_paradas_rutas.csv`: segmentos y tiempos acumulados desde cada parada;
- `data/processed/duraciones_viajes_gtfs.csv`: duración programada por viaje;
- `maps/mapa_tiempos_totales_rutas_gtfs.html`: mapa integrado y copia HTML.

Cada ruta tiene un color estable distinto y cada sentido compara la mediana GTFS con P50 y P80 calibrados. Como el conjunto GTFS local no contiene `shapes.txt`, el mapa toma el viaje más cercano a la mediana y une sus paradas consecutivas con líneas rectas; por ello representa la secuencia de paradas, no la geometría exacta sobre las calles.

Las rutas presentes en `routes.txt` pero ausentes de `trips.txt` también aparecen en la salida con `estado_calculo = "sin viajes en trips.txt"` y duración vacía. Esto distingue correctamente “no hay datos” de una duración igual a cero.

Ventajas:

- costo de API igual a cero;
- cubre todas las rutas y viajes presentes en el GTFS;
- cálculo reproducible y rápido;
- admite horas GTFS superiores a `24:00:00`.
- permite revisar espacialmente todas las rutas calculadas y sus tiempos sin consumir Google.

Limitaciones:

- la línea base GTFS representa el horario publicado; la calibración añade un proxy histórico, no una medición operativa directa;
- la calibración de Google es un proxy de tiempo para el pasajero, no telemetría del autobús;
- `route_id_principal` identifica la ruta principal del camino GTFS, pero la matriz de Google no confirma que haya elegido la misma línea;
- el histórico actual no contiene `direction_id`, por lo que una calibración de ruta se reutiliza en ambos sentidos;
- sin `calendar.txt` y `calendar_dates.txt` no se puede saber qué servicio opera en una fecha concreta;
- sin `frequencies.txt` no se puede incorporar una espera basada en frecuencia;
- si cambia el GTFS, hay que descargarlo y recalcular.

La especificación oficial explica la relación entre `trips.txt`, `stop_times.txt`, `arrival_time`, `departure_time` y `stop_sequence`: [GTFS Schedule Reference](https://gtfs.org/documentation/schedule/reference/).

## Otras soluciones posibles

### 1. GTFS-Realtime o datos AVL de la agencia — mejor opción operativa

Con `VehiclePositions` y `TripUpdates`, o con registros GPS/AVL históricos, se reconstruye el paso real por la primera y última parada. Se compara después contra el horario GTFS por `trip_id`.

- Costo por Google: cero.
- Resultado: tiempo observado, variabilidad, puntualidad y percentiles por franja horaria.
- Requisito: que QroBus publique el feed o facilite históricos con identificadores conciliables con GTFS.

Referencia: [GTFS Realtime Reference](https://gtfs.org/documentation/realtime/reference/).

### 2. Ampliar el muestreo estratificado de Google

La primera versión de este modelo ya está implementada con el histórico disponible. Para mejorarla se deben seleccionar viajes representativos por ruta, sentido, día y franja horaria y verificar que el itinerario de Google incluya la línea esperada.

```text
tiempo estimado = constante + tiempo GTFS × factor(ruta, sentido, franja, día)
```

- Reduce de forma drástica los elementos facturables.
- Permite actualizar solo estratos con datos antiguos.
- Debe validarse fuera de muestra y mostrar intervalos de incertidumbre.
- Sigue sin equivaler a atraso vehicular si Google incluye caminata o espera.

### 3. Motor propio con GTFS + red vial abierta

OpenTripPlanner puede construir itinerarios usando GTFS y OpenStreetMap. Es útil para tiempos puerta a puerta y transbordos sin pagar por cada consulta.

- Costo marginal por consulta casi nulo una vez desplegado.
- Requiere servidor, datos OSM actualizados y operación técnica.
- Con GTFS estático seguirá generando tiempos programados; necesita GTFS-Realtime para reflejar la operación.

Referencia: [OpenTripPlanner documentation](https://docs.opentripplanner.org/).

### 4. Encuestas o recorridos instrumentados

Una aplicación o registrador GPS puede medir una muestra de recorridos completos. Sirve para auditar el GTFS o validar un modelo.

- No consume APIs comerciales.
- Es costoso en personal y lento para cubrir todas las rutas.
- Conviene para rutas prioritarias o para una validación trimestral.

## Recomendación por etapas

1. Usar el cálculo GTFS incluido como línea base para el 100 % de las rutas.
2. Solicitar a la agencia GTFS-Realtime o históricos AVL.
3. Mientras no existan, recolectar una muestra pequeña y estratificada de tiempos observados.
4. Calibrar la línea base por ruta, sentido y franja, y reportar mediana y percentil 90; no presentar un único tiempo como exacto.
5. Reservar Google para validación periódica, no para enumerar todas las combinaciones de paradas.
