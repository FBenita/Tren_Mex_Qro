"""Calcula la duracion programada completa de todas las rutas QroBus.

No utiliza Google Maps. Para cada trip_id toma la primera salida y la ultima
llegada segun stop_sequence; despues resume las duraciones por ruta y sentido.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from gtfs_network import gtfs_time_to_seconds


def calcular_duraciones_viajes(
    stop_times: pd.DataFrame,
    trips: pd.DataFrame,
    routes: pd.DataFrame,
) -> pd.DataFrame:
    """Devuelve una fila por viaje con su duracion programada extremo a extremo."""
    stop_times = stop_times.copy()
    stop_times["arrival_sec"] = gtfs_time_to_seconds(stop_times["arrival_time"])
    stop_times["departure_sec"] = gtfs_time_to_seconds(stop_times["departure_time"])
    stop_times["stop_sequence"] = pd.to_numeric(
        stop_times["stop_sequence"], errors="raise"
    )
    ordenados = stop_times.sort_values(["trip_id", "stop_sequence"])

    extremos = ordenados.groupby("trip_id", as_index=False).agg(
        stop_id_inicio=("stop_id", "first"),
        stop_id_fin=("stop_id", "last"),
        salida_inicio_sec=("departure_sec", "first"),
        llegada_fin_sec=("arrival_sec", "last"),
        numero_paradas=("stop_id", "size"),
    )
    extremos["duracion_programada_min"] = (
        extremos["llegada_fin_sec"] - extremos["salida_inicio_sec"]
    ) / 60
    invalidos = extremos["duracion_programada_min"].lt(0)
    if invalidos.any():
        ejemplos = extremos.loc[invalidos, "trip_id"].head().tolist()
        raise ValueError(f"Hay viajes con duracion negativa: {ejemplos}")

    viajes = (
        extremos.merge(trips, on="trip_id", how="left", validate="one_to_one")
        .merge(routes, on="route_id", how="left", validate="many_to_one")
    )
    if viajes["route_id"].isna().any():
        raise ValueError("Hay trip_id de stop_times que no existen en trips.txt.")
    return viajes


def resumir_por_ruta_sentido(viajes: pd.DataFrame) -> pd.DataFrame:
    """Resume variacion de tiempos sin ocultarla tras un solo promedio."""

    def percentil(q: float):
        return lambda serie: float(np.nanpercentile(serie, q))

    agrupadores = [
        "route_id",
        "route_short_name",
        "route_long_name",
        "direction_id",
    ]
    resumen = viajes.groupby(agrupadores, dropna=False, as_index=False).agg(
        numero_viajes=("trip_id", "nunique"),
        numero_servicios=("service_id", "nunique"),
        duracion_min_min=("duracion_programada_min", "min"),
        duracion_p10_min=("duracion_programada_min", percentil(10)),
        duracion_mediana_min=("duracion_programada_min", "median"),
        duracion_promedio_min=("duracion_programada_min", "mean"),
        duracion_p90_min=("duracion_programada_min", percentil(90)),
        duracion_max_min=("duracion_programada_min", "max"),
        paradas_mediana=("numero_paradas", "median"),
    )
    columnas_tiempo = [c for c in resumen if c.startswith("duracion_")]
    resumen[columnas_tiempo] = resumen[columnas_tiempo].round(2)
    resumen["paradas_mediana"] = resumen["paradas_mediana"].round(1)
    resumen["estado_calculo"] = "calculado"
    return resumen.sort_values(["route_short_name", "direction_id"])


def agregar_rutas_sin_viajes(
    resumen: pd.DataFrame, routes: pd.DataFrame
) -> pd.DataFrame:
    """Conserva el catalogo completo e identifica rutas sin horarios calculables."""
    route_ids_con_viajes = set(resumen["route_id"].dropna().astype(str))
    faltantes = routes.loc[
        ~routes["route_id"].astype(str).isin(route_ids_con_viajes),
        ["route_id", "route_short_name", "route_long_name"],
    ].copy()
    if faltantes.empty:
        return resumen

    faltantes["direction_id"] = np.nan
    faltantes["numero_viajes"] = 0
    faltantes["numero_servicios"] = 0
    for columna in [
        "duracion_min_min",
        "duracion_p10_min",
        "duracion_mediana_min",
        "duracion_promedio_min",
        "duracion_p90_min",
        "duracion_max_min",
        "paradas_mediana",
    ]:
        faltantes[columna] = np.nan
    faltantes["estado_calculo"] = "sin viajes en trips.txt"
    return (
        pd.concat([resumen, faltantes[resumen.columns]], ignore_index=True)
        .sort_values(["route_short_name", "direction_id"], na_position="last")
        .reset_index(drop=True)
    )


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data/gtfs"))
    parser.add_argument(
        "--salida-resumen",
        type=Path,
        default=Path("data/processed/tiempos_totales_rutas_gtfs.csv"),
    )
    parser.add_argument(
        "--salida-viajes",
        type=Path,
        default=Path("data/processed/duraciones_viajes_gtfs.csv"),
    )
    return parser


def main() -> None:
    args = construir_parser().parse_args()
    stop_times = pd.read_csv(
        args.data_dir / "stop_times.txt",
        dtype={"trip_id": "string", "stop_id": "string"},
    )
    trips = pd.read_csv(
        args.data_dir / "trips.txt",
        dtype={"trip_id": "string", "route_id": "string"},
    )
    routes = pd.read_csv(
        args.data_dir / "routes.txt", dtype={"route_id": "string"}
    )

    viajes = calcular_duraciones_viajes(stop_times, trips, routes)
    resumen = agregar_rutas_sin_viajes(resumir_por_ruta_sentido(viajes), routes)
    args.salida_resumen.parent.mkdir(parents=True, exist_ok=True)
    resumen.to_csv(args.salida_resumen, index=False)
    viajes.to_csv(args.salida_viajes, index=False)

    print(f"Viajes analizados: {viajes['trip_id'].nunique():,}")
    print(f"Rutas analizadas: {viajes['route_id'].nunique():,}")
    print(
        "Rutas sin viajes GTFS: "
        f"{resumen.loc[resumen['estado_calculo'].ne('calculado'), 'route_id'].nunique():,}"
    )
    print(
        "Combinaciones ruta-sentido calculadas: "
        f"{len(resumen.loc[resumen['estado_calculo'].eq('calculado')]):,}"
    )
    print(f"Filas del resumen completo: {len(resumen):,}")
    print(f"Resumen: {args.salida_resumen}")
    print(f"Detalle: {args.salida_viajes}")


if __name__ == "__main__":
    main()
