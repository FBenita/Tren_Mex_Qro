# Organización de datos

Esta carpeta separa las fuentes, los resultados reproducibles y las descargas pesadas:

- `gtfs/`: archivos fuente publicados por QroBus (`routes.txt`, `trips.txt`, `stops.txt` y `stop_times.txt`). Los scripts los leen, pero no los modifican.
- `processed/`: tablas y resúmenes generados por los notebooks o scripts. Estos archivos pueden regenerarse a partir del GTFS y de las observaciones disponibles.
- `cache/`: respuestas externas pesadas, como las manzanas del INEGI. Está excluida de Git y evita descargar nuevamente la misma información.

Los mapas HTML no se guardan aquí. Se encuentran en la carpeta `maps/` de la raíz y también se muestran dentro de `scripts/RutasQroBus.ipynb`.
