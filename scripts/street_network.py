"""Descarga de la red vial de OpenStreetMap y enrutamiento entre paradas."""

from pathlib import Path

import networkx as nx
import numpy as np
import osmnx as ox
import pandas as pd
import shapely
from pyproj import Transformer
from shapely.geometry import LineString
from shapely.ops import substring

from geo import (
    COLUMNAS_TRAZOS,
    TRAZO_LINEA_RECTA,
    TRAZO_RED_VIAL,
    distancia_firmada_a_via,
    haversine_m,
)


# UTM 14N: unidades en metros para el área metropolitana de Querétaro.
CRS_METRICO = "EPSG:32614"

# Un autobús prefiere vialidades principales aunque el atajo por calles locales
# sea unos metros más corto. El factor solo ordena alternativas; la distancia
# reportada siempre es la longitud real del trazo.
FACTORES_VIA_AUTOBUS = {
    "residential": 1.3,
    "living_street": 2.0,
    "unclassified": 1.3,
    "service": 2.0,
}


def cargar_red_osm(
    cache_path,
    *,
    bbox=None,
    centro=None,
    radio_m=None,
    network_type="drive",
    actualizar=False,
):
    """Descarga una red de OpenStreetMap o la recupera de la caché local.

    `bbox` es (oeste, sur, este, norte); como alternativa se puede indicar
    `centro` como (lat, lon) junto con `radio_m`.
    """
    cache_path = Path(cache_path)
    if cache_path.exists() and not actualizar:
        return ox.load_graphml(cache_path)

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    ox.settings.cache_folder = cache_path.parent / "osmnx_http"
    if bbox is not None:
        grafo = ox.graph_from_bbox(tuple(bbox), network_type=network_type)
    elif centro is not None and radio_m is not None:
        grafo = ox.graph_from_point(
            tuple(centro), dist=radio_m, network_type=network_type
        )
    else:
        raise ValueError("Indique bbox, o bien centro y radio_m.")
    ox.save_graphml(grafo, cache_path)
    return grafo


def recortar_red_a_lado_de_via(grafo, via_latlon, referencia_latlon, margen_m=15.0):
    """Conserva las aristas situadas por completo del lado de la referencia.

    Usa el mismo criterio que `filtrar_segmentos_mismo_lado_vias`: la vía se
    trata como una función de longitud a latitud y cada arista debe quedar a
    más de `margen_m` de ella, sin tocarla ni cruzarla.
    """
    conservadas = []
    for u, v, clave, datos in grafo.edges(keys=True, data=True):
        geometria = datos.get("geometry")
        if geometria is None:
            lon_lat = np.array(
                [
                    (grafo.nodes[u]["x"], grafo.nodes[u]["y"]),
                    (grafo.nodes[v]["x"], grafo.nodes[v]["y"]),
                ]
            )
        else:
            lon_lat = np.asarray(geometria.coords)
        # Se agregan puntos medios para no pasar por alto tramos largos.
        lon_lat = np.vstack([lon_lat, (lon_lat[:-1] + lon_lat[1:]) / 2])
        distancia = distancia_firmada_a_via(
            lon_lat[:, 1], lon_lat[:, 0], via_latlon, referencia_latlon
        )
        if (distancia >= margen_m).all():
            conservadas.append((u, v, clave))
    return grafo.edge_subgraph(conservadas).copy()


class RedVial:
    """Red vial enrutable con puntos (paradas) enganchados a sus calles.

    Cada punto se engancha a la arista más cercana y a las que quedan hasta
    `tolerancia_candidatos_m` más lejos; el enrutamiento elige la mejor. Esto
    evita rodeos artificiales cuando la coordenada de una parada cae más cerca
    del sentido o del cuerpo contrario de una avenida. Los puntos no son nodos
    de paso: un trazo no puede usarlos para saltar de una calle a otra.

    Con `contar_enganche=True` la distancia incluye el tramo recto entre cada
    punto y su calle, como corresponde a un recorrido a pie.
    """

    def __init__(
        self,
        grafo,
        puntos,
        *,
        col_id="stop_id",
        col_lat="stop_lat",
        col_lon="stop_lon",
        factores_via=None,
        tolerancia_candidatos_m=35.0,
        max_distancia_enganche_m=150.0,
        penalizacion_enganche=2.0,
        contar_enganche=False,
    ):
        factores_via = factores_via or {}
        proyectado = ox.project_graph(grafo, to_crs=CRS_METRICO)
        self._a_metrico = Transformer.from_crs("EPSG:4326", CRS_METRICO, always_xy=True)
        self._a_latlon = Transformer.from_crs(CRS_METRICO, "EPSG:4326", always_xy=True)

        self._grafo = nx.DiGraph()
        aristas = {}
        for u, v, datos in proyectado.edges(data=True):
            if u == v:
                continue
            geometria = datos.get("geometry")
            if geometria is None:
                geometria = LineString(
                    [
                        (proyectado.nodes[u]["x"], proyectado.nodes[u]["y"]),
                        (proyectado.nodes[v]["x"], proyectado.nodes[v]["y"]),
                    ]
                )
            tipos = datos.get("highway")
            tipos = tipos if isinstance(tipos, list) else [tipos]
            factor = min(factores_via.get(tipo, 1.0) for tipo in tipos)
            peso = geometria.length * factor
            # Entre aristas paralelas se conserva la de menor costo.
            if (u, v) not in aristas or peso < aristas[(u, v)][1]:
                aristas[(u, v)] = (geometria, peso, factor)
        for (u, v), (geometria, peso, _) in aristas.items():
            self._agregar_arista(u, v, geometria, peso)

        ids = puntos[col_id].astype(str).to_numpy()
        self._latlon = dict(
            zip(ids, zip(puntos[col_lat].astype(float), puntos[col_lon].astype(float)))
        )
        x, y = self._a_metrico.transform(
            puntos[col_lon].to_numpy(dtype=float), puntos[col_lat].to_numpy(dtype=float)
        )
        geometrias_puntos = shapely.points(x, y)
        claves = list(aristas)
        geometrias = np.array([aristas[clave][0] for clave in claves], dtype=object)
        arbol = shapely.STRtree(geometrias)
        _, distancia_minima = arbol.query_nearest(
            geometrias_puntos, return_distance=True, all_matches=False
        )
        self.distancia_enganche_m = dict(zip(ids, distancia_minima))
        indices_punto, indices_arista = arbol.query(
            geometrias_puntos,
            predicate="dwithin",
            distance=distancia_minima + tolerancia_candidatos_m,
        )

        cortes = {}
        for indice_punto, indice_arista in zip(indices_punto, indices_arista):
            if distancia_minima[indice_punto] > max_distancia_enganche_m:
                continue
            geometria = geometrias[indice_arista]
            punto = geometrias_puntos[indice_punto]
            cortes.setdefault(indice_arista, []).append(
                (
                    shapely.line_locate_point(geometria, punto, normalized=True),
                    ids[indice_punto],
                    shapely.distance(geometria, punto),
                )
            )

        # Cada arista se parte en todas las posiciones enganchadas, de modo que
        # dos paradas de la misma cuadra queden unidas directamente.
        self._enganchados = set()
        for indice_arista, lista in cortes.items():
            u, v = claves[indice_arista]
            geometria, _, factor = aristas[(u, v)]
            anterior, fraccion_anterior = u, 0.0
            for fraccion, punto_id, separacion in sorted(lista):
                nodo = ("corte", punto_id, indice_arista)
                self._agregar_tramo(
                    anterior, nodo, geometria, fraccion_anterior, fraccion, factor
                )
                enganche = {
                    "peso": separacion * penalizacion_enganche,
                    "largo": separacion if contar_enganche else 0.0,
                    "xy": [],
                }
                self._grafo.add_edge(("origen", punto_id), nodo, **enganche)
                self._grafo.add_edge(nodo, ("destino", punto_id), **enganche)
                self._enganchados.add(punto_id)
                anterior, fraccion_anterior = nodo, fraccion
            self._agregar_tramo(anterior, v, geometria, fraccion_anterior, 1.0, factor)

    def _agregar_arista(self, u, v, geometria, peso):
        self._grafo.add_edge(
            u, v, peso=peso, largo=geometria.length, xy=list(geometria.coords)
        )

    def _agregar_tramo(self, u, v, geometria, inicio, fin, factor):
        tramo = substring(geometria, inicio, fin, normalized=True)
        if tramo.geom_type == "Point":
            tramo = LineString([tramo, tramo])
        self._agregar_arista(u, v, tramo, tramo.length * factor)

    def trazar(self, origen_id, destino_id, simplificar_m=1.0):
        """Devuelve (distancia_m, [[lat, lon], ...]) o None si no hay camino."""
        origen_id, destino_id = str(origen_id), str(destino_id)
        if origen_id not in self._enganchados or destino_id not in self._enganchados:
            return None
        try:
            _, nodos = nx.bidirectional_dijkstra(
                self._grafo,
                ("origen", origen_id),
                ("destino", destino_id),
                weight="peso",
            )
        except nx.NetworkXNoPath:
            return None

        distancia = 0.0
        xy = []
        for u, v in zip(nodos, nodos[1:]):
            datos = self._grafo.edges[u, v]
            distancia += datos["largo"]
            xy.extend(datos["xy"])
        if len(xy) >= 2:
            xy = list(LineString(xy).simplify(simplificar_m).coords)
        lon, lat = self._a_latlon.transform(
            [punto[0] for punto in xy], [punto[1] for punto in xy]
        )
        # Los extremos son las coordenadas originales para tocar los marcadores.
        coordenadas = (
            [list(self._latlon[origen_id])]
            + [[round(la, 6), round(lo, 6)] for la, lo in zip(lat, lon)]
            + [list(self._latlon[destino_id])]
        )
        return distancia, coordenadas

    def trazar_pares(
        self,
        pares,
        col_origen="stop_id",
        col_destino="next_stop_id",
        max_factor_desvio=3.0,
        min_exceso_m=500.0,
    ):
        """Calcula el trazo de cada par único; usa línea recta si no hay camino.

        También se descarta un trazo cuando supera `max_factor_desvio` veces la
        línea recta y la excede por más de `min_exceso_m`: ese rodeo casi siempre
        indica una parada mal ubicada o un sentido de calle mal registrado.
        Pase `max_factor_desvio=None` para aceptar cualquier camino.
        """
        unicos = pares[[col_origen, col_destino]].astype(str).drop_duplicates()
        registros = []
        for origen_id, destino_id in unicos.itertuples(index=False):
            if origen_id not in self._latlon or destino_id not in self._latlon:
                continue
            lat_a, lon_a = self._latlon[origen_id]
            lat_b, lon_b = self._latlon[destino_id]
            recta = float(haversine_m(lat_a, lon_a, lat_b, lon_b))
            trazo = self.trazar(origen_id, destino_id)
            if (
                trazo is not None
                and max_factor_desvio is not None
                and trazo[0] > max_factor_desvio * recta
                and trazo[0] - recta > min_exceso_m
            ):
                trazo = None
            if trazo is None:
                distancia, coordenadas = recta, [[lat_a, lon_a], [lat_b, lon_b]]
                metodo = TRAZO_LINEA_RECTA
            else:
                # El recorrido por calles nunca es menor que la línea recta.
                distancia, coordenadas = max(trazo[0], recta), trazo[1]
                metodo = TRAZO_RED_VIAL
            registros.append(
                {
                    "stop_id": origen_id,
                    "next_stop_id": destino_id,
                    "distancia_recta_m": round(recta, 1),
                    "distancia_red_m": round(distancia, 1),
                    "factor_desvio": round(distancia / recta, 3) if recta > 0 else np.nan,
                    "metodo_trazo": metodo,
                    "coordenadas": coordenadas,
                }
            )
        return pd.DataFrame(registros, columns=COLUMNAS_TRAZOS)
