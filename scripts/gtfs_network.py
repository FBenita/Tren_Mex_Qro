"""Motor compartido para calcular y persistir rutas GTFS hacia un destino."""

from collections import defaultdict
from itertools import count
import heapq
import json
from pathlib import Path

import numpy as np
import pandas as pd


LIST_COLUMNS = ("camino_stop_ids", "rutas_por_segmento")

# Línea Juárez simplificada en el entorno de los caminos de 30 minutos.
# Fuente: OpenStreetMap, consulta del 24 de septiembre de 2026 (ODbL).
VIA_FERREA_CORREGIDORA_LATLON = (
    (20.5995317, -100.4489310),
    (20.5995818, -100.4476439),
    (20.6001097, -100.4332137),
    (20.6004068, -100.4251777),
    (20.6006149, -100.4195559),
    (20.6009997, -100.4087681),
    (20.6013683, -100.3992262),
    (20.6015191, -100.3952324),
    (20.6018730, -100.3897692),
    (20.6029540, -100.3829217),
    (20.6034681, -100.3802003),
    (20.6036738, -100.3767069),
    (20.6034556, -100.3739630),
    (20.6030643, -100.3705949),
    (20.6043119, -100.3660711),
    (20.6035799, -100.3624753),
)


def gtfs_time_to_seconds(series):
    """Convierte HH:MM:SS GTFS a segundos, permitiendo horas mayores a 24."""
    partes = series.astype("string").str.extract(
        r"^(?P<h>\d+):(?P<m>[0-5]\d):(?P<s>[0-5]\d)$"
    )
    invalidos = partes.isna().any(axis=1)
    if invalidos.any():
        ejemplos = series[invalidos].head().tolist()
        raise ValueError(f"Horarios GTFS inválidos. Ejemplos: {ejemplos}")

    partes = partes.astype(int)
    return partes["h"] * 3600 + partes["m"] * 60 + partes["s"]


def filtrar_segmentos_mismo_lado_vias(
    segmentos,
    stops,
    via_latlon,
    referencia_stop_id,
    margen_m=15.0,
    muestras_por_segmento=25,
):
    """Conserva segmentos que permanecen del mismo lado de una vía que la referencia.

    La vía debe poder representarse como una función de longitud a latitud en el
    área de análisis. Cada segmento se muestrea entre sus dos paradas para evitar
    conservar una cuerda que atraviese la polilínea aunque sus extremos no lo hagan.
    """
    if muestras_por_segmento < 2:
        raise ValueError("muestras_por_segmento debe ser al menos 2.")

    via = np.asarray(via_latlon, dtype=float)
    if via.ndim != 2 or via.shape[1] != 2 or len(via) < 2:
        raise ValueError("via_latlon debe contener al menos dos pares (lat, lon).")
    orden = np.argsort(via[:, 1])
    via_lat = via[orden, 0]
    via_lon = via[orden, 1]
    if np.any(np.diff(via_lon) <= 0):
        raise ValueError("Las longitudes de la vía deben ser únicas.")

    stops_coords = stops[["stop_id", "stop_lat", "stop_lon"]].copy()
    coincidencia = stops_coords["stop_id"].astype(str).eq(str(referencia_stop_id))
    if coincidencia.sum() != 1:
        raise ValueError("La parada de referencia debe existir exactamente una vez.")
    referencia = stops_coords.loc[coincidencia].iloc[0]
    lat_via_referencia = np.interp(
        float(referencia["stop_lon"]), via_lon, via_lat
    )
    signo_referencia = np.sign(
        float(referencia["stop_lat"]) - lat_via_referencia
    )
    if signo_referencia == 0:
        raise ValueError("La parada de referencia quedó exactamente sobre la vía.")

    origen = stops_coords.rename(
        columns={"stop_lat": "origen_lat", "stop_lon": "origen_lon"}
    )
    destino = stops_coords.rename(
        columns={
            "stop_id": "next_stop_id",
            "stop_lat": "destino_lat",
            "stop_lon": "destino_lon",
        }
    )
    trabajo = (
        segmentos.merge(origen, on="stop_id", how="left", validate="many_to_one")
        .merge(destino, on="next_stop_id", how="left", validate="many_to_one")
    )
    if trabajo[
        ["origen_lat", "origen_lon", "destino_lat", "destino_lon"]
    ].isna().any(axis=None):
        raise ValueError("Hay segmentos con paradas sin coordenadas.")

    proporcion = np.linspace(0.0, 1.0, muestras_por_segmento)
    lat_muestras = (
        trabajo["origen_lat"].to_numpy()[:, None]
        + proporcion
        * (
            trabajo["destino_lat"].to_numpy()
            - trabajo["origen_lat"].to_numpy()
        )[:, None]
    )
    lon_muestras = (
        trabajo["origen_lon"].to_numpy()[:, None]
        + proporcion
        * (
            trabajo["destino_lon"].to_numpy()
            - trabajo["origen_lon"].to_numpy()
        )[:, None]
    )
    lat_via_muestras = np.interp(lon_muestras, via_lon, via_lat)
    margen_lat = float(margen_m) / 111_320.0
    distancia_firmada = (
        lat_muestras - lat_via_muestras
    ) * signo_referencia
    validos = (distancia_firmada >= margen_lat).all(axis=1)

    columnas_originales = list(segmentos.columns)
    return trabajo.loc[validos, columnas_originales].reset_index(drop=True)


def compactar_rutas(rutas_segmentos):
    """Elimina repeticiones consecutivas sin perder cambios posteriores de ruta."""
    compactas = []
    for route_id in rutas_segmentos:
        if not compactas or route_id != compactas[-1]:
            compactas.append(route_id)
    return compactas


def calcular_rutas_hacia_destino(
    segmentos,
    stops,
    routes,
    destino_stop_id,
    penalizacion_transbordo_min,
    route_ids_sin_penalizacion=(),
    route_ids_auxiliares=(),
):
    """Ejecuta Dijkstra inverso con estados (parada, ruta) una sola vez."""
    rutas_sin_penalizacion = set(route_ids_sin_penalizacion)
    rutas_auxiliares = set(route_ids_auxiliares)
    adj_reverse = defaultdict(list)
    for fila in segmentos.itertuples(index=False):
        adj_reverse[fila.next_stop_id].append(
            (fila.stop_id, float(fila.tiempo_segmento_min), fila.route_id)
        )

    target_state = (destino_stop_id, None)
    dist_state = {target_state: 0.0}
    parent_state = {}
    contador_heap = count()
    heap = [(0.0, next(contador_heap), target_state)]

    while heap:
        costo_actual, _, estado_actual = heapq.heappop(heap)
        if costo_actual > dist_state.get(estado_actual, np.inf):
            continue

        parada_actual, ruta_hacia_destino = estado_actual
        for parada_anterior, tiempo_segmento, route_id in adj_reverse.get(
            parada_actual, []
        ):
            penalizacion = (
                penalizacion_transbordo_min
                if ruta_hacia_destino is not None
                and route_id != ruta_hacia_destino
                and ruta_hacia_destino not in rutas_sin_penalizacion
                and route_id not in rutas_sin_penalizacion
                else 0.0
            )
            nuevo_estado = (parada_anterior, route_id)
            nuevo_costo = costo_actual + tiempo_segmento + penalizacion

            if nuevo_costo < dist_state.get(nuevo_estado, np.inf):
                dist_state[nuevo_estado] = nuevo_costo
                parent_state[nuevo_estado] = estado_actual
                heapq.heappush(
                    heap,
                    (nuevo_costo, next(contador_heap), nuevo_estado),
                )

    best_state_by_stop = {destino_stop_id: target_state}
    for estado, costo in dist_state.items():
        stop_id = estado[0]
        mejor_estado = best_state_by_stop.get(stop_id)
        if mejor_estado is None or costo < dist_state[mejor_estado]:
            best_state_by_stop[stop_id] = estado

    route_short_map = routes.set_index("route_id")["route_short_name"].to_dict()
    stop_name_map = stops.set_index("stop_id")["stop_name"].to_dict()

    registros = []
    for stop_id, mejor_estado in best_state_by_stop.items():
        estado = mejor_estado
        paradas_camino = [stop_id]
        rutas_segmentos = []
        visitados = {estado}

        while estado != target_state:
            if estado not in parent_state:
                raise RuntimeError(f"Camino incompleto para la parada {stop_id}.")
            rutas_segmentos.append(estado[1])
            estado = parent_state[estado]
            if estado in visitados:
                raise RuntimeError(f"Ciclo inesperado para la parada {stop_id}.")
            visitados.add(estado)
            paradas_camino.append(estado[0])

        indices_operativos = [
            indice
            for indice, route_id in enumerate(rutas_segmentos)
            if route_id not in rutas_auxiliares
        ]
        rutas_operativas = [rutas_segmentos[indice] for indice in indices_operativos]
        rutas_compactas = compactar_rutas(rutas_operativas)
        paradas_transbordo = [
            paradas_camino[indice_actual]
            for indice_anterior, indice_actual in zip(
                indices_operativos, indices_operativos[1:]
            )
            if rutas_segmentos[indice_actual]
            != rutas_segmentos[indice_anterior]
        ]
        etiquetas_rutas = [
            route_short_map.get(route_id, route_id) for route_id in rutas_compactas
        ]
        ruta_principal = (
            rutas_operativas[0]
            if rutas_operativas
            else rutas_segmentos[0]
            if rutas_segmentos
            else np.nan
        )

        registros.append(
            {
                "stop_id": stop_id,
                "tiempo_red_min": dist_state[mejor_estado],
                "route_id_principal": ruta_principal,
                "route_short_name": route_short_map.get(ruta_principal),
                "num_transbordos": max(len(rutas_compactas) - 1, 0),
                "num_paradas_camino": len(paradas_camino),
                "num_rutas_camino": len(rutas_compactas),
                "tipo_conexion": (
                    "Destino"
                    if stop_id == destino_stop_id
                    else "Solo caminata"
                    if not rutas_operativas
                    else "Directa"
                    if len(rutas_compactas) <= 1
                    else "Con transbordo"
                ),
                "itinerario_route_ids": " → ".join(map(str, rutas_compactas)),
                "itinerario_rutas": " → ".join(map(str, etiquetas_rutas)),
                "paradas_transbordo": " → ".join(
                    str(stop_name_map.get(s, s)) for s in paradas_transbordo
                ),
                "camino_stop_ids": paradas_camino,
                "rutas_por_segmento": rutas_segmentos,
                "penalizacion_transbordo_config_min": float(
                    penalizacion_transbordo_min
                ),
            }
        )

    resultados = (
        pd.DataFrame(registros)
        .merge(
            stops[["stop_id", "stop_name", "stop_lat", "stop_lon"]],
            on="stop_id",
            how="left",
            validate="one_to_one",
        )
        .sort_values("tiempo_red_min")
        .reset_index(drop=True)
    )
    return resultados


def guardar_rutas_base(resultados, path):
    """Guarda listas como JSON dentro del CSV para recuperarlas sin ambigüedad."""
    salida = resultados.copy()
    for columna in LIST_COLUMNS:
        salida[columna] = salida[columna].apply(
            lambda valores: json.dumps(
                [str(valor) for valor in valores],
                ensure_ascii=False,
            )
        )
    salida.to_csv(Path(path), index=False)


def cargar_rutas_base(path):
    """Carga el cálculo base y restaura las columnas que contienen listas."""
    resultados = pd.read_csv(Path(path), dtype={"stop_id": "string"})
    faltantes = set(LIST_COLUMNS) - set(resultados.columns)
    if faltantes:
        raise ValueError(
            f"El archivo de rutas base no contiene: {sorted(faltantes)}"
        )

    for columna in LIST_COLUMNS:
        resultados[columna] = resultados[columna].apply(
            lambda valor: [str(item) for item in json.loads(valor)]
        )
    return resultados
