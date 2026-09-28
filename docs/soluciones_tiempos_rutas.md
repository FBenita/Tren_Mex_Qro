# Propuestas para obtener el tiempo total de las rutas QroBus

## Qué tiempo se quiere medir

Antes de elegir una fuente conviene separar tres métricas:

1. **Tiempo programado:** duración publicada entre la primera y la última parada.
2. **Tiempo observado:** duración que realmente hizo un autobús concreto.
3. **Tiempo para el pasajero:** espera + recorrido + transbordos + caminatas.

No son intercambiables. Google Transit se aproxima a la tercera; el GTFS estático permite calcular la primera. Para evaluar la operación se necesita la segunda.

## Solución aplicada: horarios GTFS estáticos

El notebook autosuficiente `scripts/TiemposTotalesRutasGTFS.ipynb` presenta el análisis completo. Para cada `trip_id` calcula:

```text
duración = llegada de la última parada - salida de la primera parada
```

Después agrupa por `route_id` y `direction_id` y entrega mínimo, percentil 10, mediana, promedio, percentil 90 y máximo. La mediana es el valor de referencia recomendado porque un mismo recorrido puede tener duraciones programadas distintas según el horario.

La misma ejecución genera `maps/mapa_tiempos_totales_rutas_gtfs.html`. Cada ruta tiene un color estable distinto y cada sentido muestra su mediana (P50), el intervalo P10-P90 y el número de viajes utilizados. Como el conjunto GTFS local no contiene `shapes.txt`, el mapa toma el viaje más cercano a la mediana y une sus paradas consecutivas con líneas rectas; por ello representa la secuencia de paradas, no la geometría exacta sobre las calles.

Las rutas presentes en `routes.txt` pero ausentes de `trips.txt` también aparecen en la salida con `estado_calculo = "sin viajes en trips.txt"` y duración vacía. Esto distingue correctamente “no hay datos” de una duración igual a cero.

Ventajas:

- costo de API igual a cero;
- cubre todas las rutas y viajes presentes en el GTFS;
- cálculo reproducible y rápido;
- admite horas GTFS superiores a `24:00:00`.
- permite revisar espacialmente todas las rutas calculadas y sus tiempos sin consumir Google.

Limitaciones:

- representa el horario publicado, no congestión ni atrasos;
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

### 2. Muestreo estratificado de Google y modelo de calibración

No se consulta cada parada. Se seleccionan pocos viajes representativos por ruta, sentido, día y franja horaria. Con esas observaciones se estima un factor de corrección para el tiempo GTFS:

```text
tiempo estimado = tiempo GTFS × factor(ruta, sentido, franja, día)
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
