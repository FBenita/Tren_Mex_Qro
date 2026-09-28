"""Estima la poblacion con acceso a paradas que llegan a Corregidora.

El script descarga todas las manzanas de Queretaro desde el Servicio Web del
Catalogo Unico de Claves Geoestadisticas de INEGI. Despues selecciona localmente
las paradas cuyo camino GTFS hacia la estacion no excede el umbral indicado y
calcula la interseccion de sus buffers con las manzanas.

La poblacion ponderada es una estimacion areal: supone que la poblacion esta
distribuida uniformemente dentro de cada manzana. No representa domicilios ni
personas geolocalizadas.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from tempfile import NamedTemporaryFile

import folium
import geopandas as gpd
import pandas as pd
import requests


INEGI_MANZANAS_URL = "https://gaia.inegi.org.mx/wscatgeo/v2/geo/mza/22"
INEGI_ENTIDAD_URL = "https://gaia.inegi.org.mx/wscatgeo/v2/mgee/22"
CRS_METRICO_QUERETARO = "EPSG:32614"


def descargar_manzanas_inegi(url: str, cache_path: Path, actualizar: bool) -> Path:
    """Descarga el GeoJSON estatal completo y conserva una copia local."""
    if cache_path.exists() and not actualizar:
        return cache_path

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=(20, 300)) as respuesta:
        respuesta.raise_for_status()
        with NamedTemporaryFile(
            mode="wb", suffix=".geojson", dir=cache_path.parent, delete=False
        ) as temporal:
            temporal_path = Path(temporal.name)
            for bloque in respuesta.iter_content(chunk_size=1024 * 1024):
                if bloque:
                    temporal.write(bloque)

    temporal_path.replace(cache_path)
    return cache_path


def cargar_paradas_con_acceso(
    stops_path: Path, rutas_base_path: Path, umbral_min: float
) -> gpd.GeoDataFrame:
    """Selecciona paradas con un camino GTFS a la estacion dentro del umbral."""
    stops = pd.read_csv(stops_path, dtype={"stop_id": "string"})
    rutas = pd.read_csv(rutas_base_path, dtype={"stop_id": "string"})
    rutas["tiempo_red_min"] = pd.to_numeric(
        rutas["tiempo_red_min"], errors="coerce"
    )
    elegibles = rutas.loc[
        rutas["tiempo_red_min"].le(umbral_min),
        ["stop_id", "tiempo_red_min", "itinerario_rutas"],
    ]
    paradas = elegibles.merge(
        stops[["stop_id", "stop_name", "stop_lat", "stop_lon"]],
        on="stop_id",
        how="left",
        validate="one_to_one",
    )
    if paradas[["stop_lat", "stop_lon"]].isna().any(axis=None):
        raise ValueError("Existen paradas elegibles sin coordenadas.")

    return gpd.GeoDataFrame(
        paradas,
        geometry=gpd.points_from_xy(paradas["stop_lon"], paradas["stop_lat"]),
        crs="EPSG:4326",
    )


def consultar_poblacion_estatal(url: str) -> tuple[int, str]:
    """Consulta el total censal estatal publicado por el mismo servicio."""
    respuesta = requests.get(url, timeout=(20, 60))
    respuesta.raise_for_status()
    contenido = respuesta.json()
    try:
        poblacion = int(contenido["datos"]["pob_total"])
        fuente = str(contenido["metadatos"]["Fuente_informacion_estadistica"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Respuesta estatal de INEGI con formato inesperado.") from exc
    return poblacion, fuente


def estimar_demanda(
    manzanas: gpd.GeoDataFrame,
    paradas: gpd.GeoDataFrame,
    radio_m: float,
    poblacion_estatal: int,
    fuente_estatal: str,
) -> tuple[gpd.GeoDataFrame, dict[str, object], gpd.GeoDataFrame]:
    """Cruza la union de buffers con manzanas y calcula tres estimadores."""
    requeridas = {"cvegeo", "pob_total", "geometry"}
    faltantes = requeridas - set(manzanas.columns)
    if faltantes:
        raise ValueError(f"La respuesta de INEGI no contiene {sorted(faltantes)}")

    manzanas = manzanas.copy()
    manzanas["pob_total_numerica"] = pd.to_numeric(
        manzanas["pob_total"], errors="coerce"
    )
    manzanas_m = manzanas.to_crs(CRS_METRICO_QUERETARO)
    paradas_m = paradas.to_crs(CRS_METRICO_QUERETARO)
    cobertura_m = paradas_m.geometry.buffer(radio_m).union_all()

    candidatas = manzanas_m.loc[manzanas_m.geometry.intersects(cobertura_m)].copy()
    candidatas["area_manzana_m2"] = candidatas.geometry.area
    candidatas["area_cubierta_m2"] = candidatas.geometry.intersection(
        cobertura_m
    ).area
    candidatas["fraccion_area_cubierta"] = (
        candidatas["area_cubierta_m2"] / candidatas["area_manzana_m2"]
    ).clip(0, 1)
    candidatas["poblacion_estimada_area"] = (
        candidatas["pob_total_numerica"]
        * candidatas["fraccion_area_cubierta"]
    )
    punto_interno_cubierto = candidatas.geometry.representative_point().within(
        cobertura_m
    )
    candidatas["punto_representativo_cubierto"] = punto_interno_cubierto

    poblacion_base = float(manzanas["pob_total_numerica"].sum())
    poblacion_area = float(candidatas["poblacion_estimada_area"].sum())
    poblacion_manzanas = float(candidatas["pob_total_numerica"].sum())
    poblacion_punto = float(
        candidatas.loc[
            candidatas["punto_representativo_cubierto"], "pob_total_numerica"
        ].sum()
    )
    resumen: dict[str, object] = {
        "fuente": fuente_estatal,
        "metodo": "prorrateo por fraccion de area de manzana cubierta",
        "radio_buffer_m": radio_m,
        "numero_paradas": int(len(paradas)),
        "numero_manzanas_inegi": int(len(manzanas)),
        "numero_manzanas_intersectadas": int(len(candidatas)),
        "manzanas_sin_poblacion_numerica": int(
            manzanas["pob_total_numerica"].isna().sum()
        ),
        "poblacion_base_manzanas_inegi": round(poblacion_base, 2),
        "poblacion_total_estatal_inegi": poblacion_estatal,
        "poblacion_estimada_area": round(poblacion_area, 2),
        "porcentaje_sobre_poblacion_en_manzanas": (
            round(100 * poblacion_area / poblacion_base, 6)
            if poblacion_base
            else None
        ),
        "porcentaje_sobre_poblacion_estatal": (
            round(100 * poblacion_area / poblacion_estatal, 6)
            if poblacion_estatal
            else None
        ),
        "poblacion_manzanas_intersectadas_cota_alta": round(
            poblacion_manzanas, 2
        ),
        "poblacion_por_punto_representativo": round(poblacion_punto, 2),
    }

    cobertura = gpd.GeoDataFrame(
        {"radio_m": [radio_m]}, geometry=[cobertura_m], crs=CRS_METRICO_QUERETARO
    ).to_crs("EPSG:4326")
    return candidatas.to_crs("EPSG:4326"), resumen, cobertura


def crear_mapa(
    candidatas: gpd.GeoDataFrame,
    paradas: gpd.GeoDataFrame,
    radio_m: float,
    salida_html: Path,
) -> None:
    """Genera un mapa ligero con buffers, paradas y manzanas intersectadas."""
    centro = [float(paradas["stop_lat"].mean()), float(paradas["stop_lon"].mean())]
    mapa = folium.Map(location=centro, zoom_start=12, tiles="OpenStreetMap")

    columnas = [
        columna
        for columna in [
            "cvegeo",
            "nom_mun",
            "nom_loc",
            "pob_total_numerica",
            "fraccion_area_cubierta",
            "poblacion_estimada_area",
            "geometry",
        ]
        if columna in candidatas.columns
    ]
    folium.GeoJson(
        candidatas[columnas],
        name="Manzanas intersectadas",
        style_function=lambda _: {
            "color": "#7b2cbf",
            "weight": 1,
            "fillColor": "#c77dff",
            "fillOpacity": 0.35,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=[c for c in columnas if c != "geometry"],
            aliases=[
                {
                    "cvegeo": "Clave:",
                    "nom_mun": "Municipio:",
                    "nom_loc": "Localidad:",
                    "pob_total_numerica": "Poblacion de manzana:",
                    "fraccion_area_cubierta": "Fraccion cubierta:",
                    "poblacion_estimada_area": "Poblacion estimada:",
                }[c]
                for c in columnas
                if c != "geometry"
            ],
            localize=True,
        ),
    ).add_to(mapa)

    capa_paradas = folium.FeatureGroup(name=f"Paradas y buffer de {radio_m:g} m")
    for parada in paradas.itertuples(index=False):
        ubicacion = [float(parada.stop_lat), float(parada.stop_lon)]
        folium.Circle(
            location=ubicacion,
            radius=radio_m,
            color="#006d77",
            fill=True,
            fill_opacity=0.12,
            weight=1,
        ).add_to(capa_paradas)
        folium.CircleMarker(
            location=ubicacion,
            radius=2,
            color="#004c54",
            fill=True,
            tooltip=(
                f"{parada.stop_name}<br>Tiempo GTFS: "
                f"{float(parada.tiempo_red_min):.1f} min"
            ),
        ).add_to(capa_paradas)
    capa_paradas.add_to(mapa)
    folium.LayerControl(collapsed=False).add_to(mapa)
    salida_html.parent.mkdir(parents=True, exist_ok=True)
    mapa.save(salida_html)


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--radio-m", type=float, default=20.0)
    parser.add_argument("--umbral-min", type=float, default=30.0)
    parser.add_argument(
        "--actualizar-inegi",
        action="store_true",
        help="Ignora el cache y vuelve a descargar las manzanas.",
    )
    parser.add_argument(
        "--cache-inegi",
        type=Path,
        default=Path("data/cache/inegi_manzanas_queretaro.geojson"),
    )
    parser.add_argument(
        "--stops", type=Path, default=Path("data/gtfs/stops.txt")
    )
    parser.add_argument(
        "--rutas-base",
        type=Path,
        default=Path("data/processed/rutas_base_gtfs.csv"),
    )
    parser.add_argument(
        "--salida-csv",
        type=Path,
        default=Path("data/processed/demanda_potencial_manzanas.csv"),
    )
    parser.add_argument(
        "--salida-resumen",
        type=Path,
        default=Path("data/processed/demanda_potencial_resumen.json"),
    )
    parser.add_argument(
        "--salida-mapa",
        type=Path,
        default=Path("maps/mapa_demanda_potencial.html"),
    )
    return parser


def main() -> None:
    args = construir_parser().parse_args()
    if args.radio_m <= 0 or args.umbral_min <= 0:
        raise ValueError("El radio y el umbral deben ser mayores que cero.")

    geojson_path = descargar_manzanas_inegi(
        INEGI_MANZANAS_URL, args.cache_inegi, args.actualizar_inegi
    )
    manzanas = gpd.read_file(geojson_path)
    poblacion_estatal, fuente_estatal = consultar_poblacion_estatal(
        INEGI_ENTIDAD_URL
    )
    paradas = cargar_paradas_con_acceso(
        args.stops, args.rutas_base, args.umbral_min
    )
    candidatas, resumen, _ = estimar_demanda(
        manzanas,
        paradas,
        args.radio_m,
        poblacion_estatal,
        fuente_estatal,
    )

    args.salida_csv.parent.mkdir(parents=True, exist_ok=True)
    candidatas.drop(columns="geometry").to_csv(args.salida_csv, index=False)
    args.salida_resumen.write_text(
        json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    crear_mapa(candidatas, paradas, args.radio_m, args.salida_mapa)

    print(json.dumps(resumen, ensure_ascii=False, indent=2))
    print(f"Detalle: {args.salida_csv}")
    print(f"Mapa: {args.salida_mapa}")


if __name__ == "__main__":
    main()
