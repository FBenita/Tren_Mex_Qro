# Mapas generados

`02_RutasQroBus.ipynb` muestra los mapas dentro de sus celdas y además guarda aquí copias HTML independientes:

- `mapa_rutas_qrobus.html`
- `mapa_paradas_sur_vias_30_min.html`
- `mapa_demanda_potencial.html`

Los HTML se sobrescriben cada vez que se ejecutan las celdas correspondientes.

`03_TiemposTotalesRutasGTFS.ipynb` genera `mapa_tiempos_totales_rutas_gtfs.html`: isócronas de 5 a 60 minutos desde la Estación Corregidora o desde cualquier parada, con filtro y lista de las paradas de cada banda de tiempo, el tiempo total de cada ruta y las conexiones entre rutas como capas opcionales.

En `mapa_demanda_potencial.html`, un clic en cualquier punto muestra la ruta óptima hacia Corregidora y los datos de la celda de la malla geoestadística.
