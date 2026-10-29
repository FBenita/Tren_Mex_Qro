"""Consulta de tiempos en transporte público con Google Maps Routes API."""

from datetime import datetime, timezone
import time

import numpy as np
import pandas as pd
import requests


ROUTE_MATRIX_URL = (
    "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix"
)
FIELD_MASK = (
    "originIndex,destinationIndex,duration,distanceMeters,status,condition"
)
CODIGOS_REINTENTABLES = {429, 500, 502, 503, 504}


def duracion_google_a_minutos(valor):
    if valor is None or not str(valor).endswith("s"):
        return np.nan
    return float(str(valor)[:-1]) / 60


def crear_waypoint(latitud, longitud):
    return {
        "waypoint": {
            "location": {
                "latLng": {
                    "latitude": float(latitud),
                    "longitude": float(longitud),
                }
            }
        }
    }


def consultar_lote_google(
    df_lote, departure_time, api_key, destino_latlon, max_intentos=4
):
    """Consulta hasta 100 paradas origen hacia un destino en modo autobús.

    Reintenta con espera exponencial los errores temporales (429 y 5xx) y
    conserva en la salida los elementos que Google marca con error.
    """
    payload = {
        "origins": [
            crear_waypoint(f.stop_lat, f.stop_lon)
            for f in df_lote.itertuples(index=False)
        ],
        "destinations": [crear_waypoint(*destino_latlon)],
        "travelMode": "TRANSIT",
        "departureTime": departure_time,
        "transitPreferences": {"allowedTravelModes": ["BUS"]},
    }
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": FIELD_MASK,
    }

    for intento in range(max_intentos):
        respuesta = requests.post(
            ROUTE_MATRIX_URL,
            headers=headers,
            json=payload,
            timeout=(10, 90),
        )
        if respuesta.status_code not in CODIGOS_REINTENTABLES:
            break
        if intento == max_intentos - 1:
            break
        time.sleep(2 ** intento)

    if not respuesta.ok:
        detalle = respuesta.text[:1_000]
        raise RuntimeError(
            f"Google Routes API respondió {respuesta.status_code}: {detalle}"
        )

    try:
        elementos = respuesta.json()
    except requests.JSONDecodeError as exc:
        raise RuntimeError("La respuesta de Google no es JSON válido.") from exc

    if not isinstance(elementos, list):
        raise RuntimeError(f"Formato inesperado de Google: {elementos}")

    ahora_utc = datetime.now(timezone.utc).isoformat()
    resultados = []

    for elemento in elementos:
        indice = elemento.get("originIndex")
        if indice is None or indice >= len(df_lote):
            continue
        origen = df_lote.iloc[int(indice)]
        status = elemento.get("status") or {}
        resultados.append(
            {
                "observed_at_utc": ahora_utc,
                "departure_time_utc": departure_time,
                "stop_id": origen["stop_id"],
                "route_id_principal": origen["route_id_principal"],
                "tiempo_gtfs_min": origen["tiempo_gtfs_min"],
                "google_eta_min": duracion_google_a_minutos(
                    elemento.get("duration")
                ),
                "google_distance_m": elemento.get("distanceMeters"),
                "condition": elemento.get("condition"),
                "status_code": status.get("code", 0),
                "status_message": status.get("message"),
            }
        )

    return pd.DataFrame(resultados)


def consultar_paradas_google(
    df_consulta,
    api_key,
    destino_latlon,
    tamano_lote=100,
    espera_entre_lotes_seg=0.25,
):
    """Consulta todas las paradas por lotes con una misma hora de salida.

    Cada fila de `df_consulta` es un elemento facturable. Devuelve una fila por
    respuesta, o un DataFrame vacío si no hay paradas.
    """
    departure_time = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    total_lotes = int(np.ceil(len(df_consulta) / tamano_lote))
    observaciones = []
    for numero, inicio in enumerate(
        range(0, len(df_consulta), tamano_lote), start=1
    ):
        lote = df_consulta.iloc[inicio : inicio + tamano_lote].reset_index(drop=True)
        resultado_lote = consultar_lote_google(
            lote, departure_time, api_key, destino_latlon
        )
        observaciones.append(resultado_lote)
        print(
            f"Lote {numero}/{total_lotes}: "
            f"{len(resultado_lote)} respuestas recibidas."
        )
        if numero < total_lotes:
            time.sleep(espera_entre_lotes_seg)
    return (
        pd.concat(observaciones, ignore_index=True) if observaciones else pd.DataFrame()
    )
