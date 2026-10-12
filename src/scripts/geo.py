"""Utilidades geográficas ligeras: distancias, vía férrea y trazos guardados."""

import json
from pathlib import Path

import numpy as np
import pandas as pd


METROS_POR_GRADO_LAT = 111_320.0
TRAZO_RED_VIAL = "red_vial"
TRAZO_LINEA_RECTA = "linea_recta"
COLUMNAS_TRAZOS = [
    "stop_id",
    "next_stop_id",
    "distancia_recta_m",
    "distancia_red_m",
    "factor_desvio",
    "metodo_trazo",
    "coordenadas",
]

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


def haversine_m(lat1, lon1, lat2, lon2):
    """Distancia en línea recta sobre la esfera, en metros."""
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    delta_phi = phi2 - phi1
    delta_lambda = np.radians(np.asarray(lon2) - np.asarray(lon1))
    a = (
        np.sin(delta_phi / 2) ** 2
        + np.cos(phi1) * np.cos(phi2) * np.sin(delta_lambda / 2) ** 2
    )
    return 6_371_008.8 * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))


def distancia_firmada_a_via(lat, lon, via_latlon, referencia_latlon):
    """Distancia norte-sur a la vía, en metros; positiva del lado de la referencia.

    La vía debe poder representarse como una función de longitud a latitud en
    el área de análisis. Un punto queda del mismo lado que la referencia, con
    cierto margen, cuando el resultado es mayor o igual que ese margen.
    """
    via = np.asarray(via_latlon, dtype=float)
    if via.ndim != 2 or via.shape[1] != 2 or len(via) < 2:
        raise ValueError("via_latlon debe contener al menos dos pares (lat, lon).")
    orden = np.argsort(via[:, 1])
    via_lat, via_lon = via[orden, 0], via[orden, 1]
    if np.any(np.diff(via_lon) <= 0):
        raise ValueError("Las longitudes de la vía deben ser únicas.")

    referencia_lat, referencia_lon = (float(valor) for valor in referencia_latlon)
    signo = np.sign(referencia_lat - np.interp(referencia_lon, via_lon, via_lat))
    if signo == 0:
        raise ValueError("La referencia quedó exactamente sobre la vía.")

    lat = np.asarray(lat, dtype=float)
    lon = np.asarray(lon, dtype=float)
    return (lat - np.interp(lon, via_lon, via_lat)) * signo * METROS_POR_GRADO_LAT


def guardar_trazos(trazos, path):
    """Guarda los trazos con sus coordenadas como JSON dentro del CSV."""
    salida = trazos.copy()
    salida["coordenadas"] = salida["coordenadas"].apply(
        lambda valores: json.dumps(valores, separators=(",", ":"))
    )
    salida.to_csv(Path(path), index=False)


def cargar_trazos(path):
    """Carga los trazos como un diccionario indexado por (stop_id, next_stop_id)."""
    trazos = pd.read_csv(
        Path(path), dtype={"stop_id": "string", "next_stop_id": "string"}
    )
    faltantes = set(COLUMNAS_TRAZOS) - set(trazos.columns)
    if faltantes:
        raise ValueError(f"El archivo de trazos no contiene: {sorted(faltantes)}")
    trazos["coordenadas"] = trazos["coordenadas"].apply(json.loads)
    return {
        (fila.stop_id, fila.next_stop_id): {
            "coordenadas": fila.coordenadas,
            "distancia_red_m": float(fila.distancia_red_m),
            "distancia_recta_m": float(fila.distancia_recta_m),
            "metodo_trazo": fila.metodo_trazo,
        }
        for fila in trazos.itertuples(index=False)
    }
