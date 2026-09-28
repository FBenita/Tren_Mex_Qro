"""Utilidades compartidas para mapas de caminos QroBus conectados."""

from __future__ import annotations

import colorsys
import hashlib
import html

import folium
import pandas as pd


RUTAS_CAMINATA = {"CAMINATA_FINAL"}


def color_por_ruta(route_id: object) -> str:
    """Genera un color hexadecimal estable y reproducible por route_id."""
    texto = str(route_id)
    if texto in RUTAS_CAMINATA:
        return "#6b7280"
    digest = int(hashlib.sha1(texto.encode("utf-8")).hexdigest()[:8], 16)
    tono = (digest % 360) / 360
    rojo, verde, azul = colorsys.hsv_to_rgb(tono, 0.72, 0.82)
    return f"#{round(rojo * 255):02x}{round(verde * 255):02x}{round(azul * 255):02x}"


def etiqueta_ruta(route_id: object, route_name_map: dict[str, str]) -> str:
    """Traduce un identificador interno a la etiqueta publica de la ruta."""
    route_id_texto = str(route_id)
    if route_id_texto in RUTAS_CAMINATA:
        return "Caminata final"
    etiqueta = route_name_map.get(route_id_texto)
    return str(etiqueta) if pd.notna(etiqueta) else route_id_texto


def ruta_inicial(rutas_por_segmento: object) -> str | None:
    """Obtiene la ruta del primer salto de un camino."""
    if not isinstance(rutas_por_segmento, (list, tuple)) or not rutas_por_segmento:
        return None
    return str(rutas_por_segmento[0])


def extraer_segmentos_conectados(
    caminos: pd.DataFrame,
    coords_por_stop: dict[str, dict[str, float]],
    route_name_map: dict[str, str],
) -> pd.DataFrame:
    """Devuelve todos los segmentos de los caminos y elimina duplicados exactos.

    A diferencia de elegir un camino representativo por itinerario, esta union
    garantiza que cada origen conservado tenga al menos un segmento saliente.
    """
    registros: dict[tuple[str, str, str], dict[str, object]] = {}
    for fila in caminos.itertuples(index=False):
        paradas = [str(stop_id) for stop_id in fila.camino_stop_ids]
        rutas = [str(route_id) for route_id in fila.rutas_por_segmento]
        if len(paradas) != len(rutas) + 1:
            raise ValueError(
                f"Camino inconsistente para {fila.stop_id}: "
                f"{len(paradas)} paradas y {len(rutas)} segmentos."
            )

        for stop_a, stop_b, route_id in zip(paradas, paradas[1:], rutas):
            coord_a = coords_por_stop.get(stop_a)
            coord_b = coords_por_stop.get(stop_b)
            if coord_a is None or coord_b is None:
                continue
            clave = (route_id, stop_a, stop_b)
            registros.setdefault(
                clave,
                {
                    "route_id": route_id,
                    "route_label": etiqueta_ruta(route_id, route_name_map),
                    "stop_id_a": stop_a,
                    "stop_id_b": stop_b,
                    "lat_a": float(coord_a["stop_lat"]),
                    "lon_a": float(coord_a["stop_lon"]),
                    "lat_b": float(coord_b["stop_lat"]),
                    "lon_b": float(coord_b["stop_lon"]),
                },
            )

    columnas = [
        "route_id",
        "route_label",
        "stop_id_a",
        "stop_id_b",
        "lat_a",
        "lon_a",
        "lat_b",
        "lon_b",
    ]
    return pd.DataFrame(registros.values(), columns=columnas)


def separar_origenes_conectados(
    origenes: pd.DataFrame, segmentos: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Separa paradas dibujables de las que no tienen un tramo saliente."""
    stop_ids_con_salida = set(segmentos["stop_id_a"].astype(str))
    mascara = origenes["stop_id"].astype(str).isin(stop_ids_con_salida)
    return origenes.loc[mascara].copy(), origenes.loc[~mascara].copy()


def agregar_segmentos_rutas(
    capa: folium.FeatureGroup,
    segmentos: pd.DataFrame,
    opacity: float = 0.72,
) -> None:
    """Dibuja cada segmento con el color estable de su ruta."""
    for segmento in segmentos.itertuples(index=False):
        es_caminata = str(segmento.route_id) in RUTAS_CAMINATA
        folium.PolyLine(
            [
                [segmento.lat_a, segmento.lon_a],
                [segmento.lat_b, segmento.lon_b],
            ],
            color=color_por_ruta(segmento.route_id),
            weight=4 if not es_caminata else 3,
            opacity=opacity,
            dash_array="7 7" if es_caminata else None,
            tooltip=f"Ruta: {segmento.route_label}",
        ).add_to(capa)


def agregar_leyenda_rutas(
    mapa: folium.Map,
    segmentos: pd.DataFrame,
    titulo: str = "Rutas",
) -> None:
    """Agrega una leyenda desplazable sin ocupar todo el mapa."""
    rutas = (
        segmentos[["route_id", "route_label"]]
        .drop_duplicates()
        .sort_values(["route_label", "route_id"])
    )
    elementos = []
    for fila in rutas.itertuples(index=False):
        color = color_por_ruta(fila.route_id)
        elementos.append(
            "<div style='white-space:nowrap;margin:2px 0'>"
            f"<span style='display:inline-block;width:14px;height:4px;"
            f"background:{color};margin-right:6px;vertical-align:middle'></span>"
            f"{html.escape(str(fila.route_label))}</div>"
        )
    contenido = "".join(elementos) or "Sin segmentos"
    leyenda = folium.Element(
        "<div style='position:fixed;bottom:24px;left:24px;z-index:9999;"
        "background:white;border:1px solid #777;border-radius:5px;padding:8px;"
        "font-size:12px;max-height:260px;overflow-y:auto;box-shadow:0 1px 5px #999'>"
        f"<b>{html.escape(titulo)}</b>{contenido}</div>"
    )
    mapa.get_root().html.add_child(leyenda)
