"""Malla geoestadística del INEGI (rHEALPix, nivel 9): indicadores y geometría."""

from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
from rhealpixdggs.dggs import RHEALPixDGGS
from rhealpixdggs.ellipsoids import WGS84_ELLIPSOID, Ellipsoid


# Una letra de cara y un dígito (0-8) por nivel: nueve dígitos son el nivel 9,
# con celdas de unos 468 m por lado (0.219 km²).
PATRON_CODIGO_NIVEL_9 = r"[N-S][0-8]{9}"
_MALLA_ELIPSOIDE = RHEALPixDGGS(
    ellipsoid=WGS84_ELLIPSOID, north_square=0, south_square=0, N_side=3
)
_MALLA_ESFERA = RHEALPixDGGS(
    ellipsoid=Ellipsoid(a=6_371_007.181, b=6_371_007.181, lon_0=0),
    north_square=0,
    south_square=0,
    N_side=3,
)


def leer_indicadores_malla(path):
    """Lee un CSV de la malla y convierte en vacíos los códigos de reserva.

    El INEGI usa valores negativos (-6, -7, -9) para datos reservados por
    confidencialidad o no disponibles; no son cantidades y no deben sumarse.
    """
    datos = pd.read_csv(Path(path), dtype={"CODIGO": "string"}).dropna(how="all")
    if not datos["CODIGO"].str.fullmatch(PATRON_CODIGO_NIVEL_9).all():
        raise ValueError("Hay códigos que no corresponden a la malla de nivel 9.")
    if datos["CODIGO"].duplicated().any():
        raise ValueError("Hay códigos de celda repetidos.")
    columnas = datos.columns.difference(["ID", "CODIGO"])
    datos[columnas] = datos[columnas].apply(pd.to_numeric, errors="coerce")
    datos[columnas] = datos[columnas].mask(datos[columnas] < 0)
    return datos.reset_index(drop=True)


def _vertices(malla, codigo):
    identificador = (codigo[0], *(int(digito) for digito in codigo[1:]))
    return np.asarray(malla.cell(identificador).vertices(plane=False), dtype=float)


def geometria_celdas(codigos):
    """Reconstruye el polígono de cada celda a partir de su código.

    Los CSV de la malla no incluyen geometría. La longitud sale directamente
    del estándar rHEALPix; la latitud se toma como el promedio entre la
    solución sobre el elipsoide y la solución sobre la esfera, que es la
    posición que reproduce la población por manzana del Censo 2020 (calibrado
    con las manzanas urbanas de Querétaro; ver README). Es una reconstrucción:
    si se dispone del shapefile oficial de la malla, debe preferirse.
    """
    poligonos = []
    for codigo in codigos:
        elipsoide = _vertices(_MALLA_ELIPSOIDE, codigo)
        esfera = _vertices(_MALLA_ESFERA, codigo)
        vertices = np.column_stack(
            [elipsoide[:, 0], (elipsoide[:, 1] + esfera[:, 1]) / 2]
        )
        poligonos.append(shapely.Polygon(vertices))
    return gpd.GeoSeries(poligonos, crs="EPSG:4326")


def cargar_malla(path):
    """Devuelve los indicadores de la malla con la geometría de cada celda."""
    datos = leer_indicadores_malla(path)
    return gpd.GeoDataFrame(datos, geometry=geometria_celdas(datos["CODIGO"]).values, crs="EPSG:4326")


def estimar_demanda_malla(celdas_m, cobertura_m, columnas):
    """Cruza un área de cobertura con las celdas, en un CRS métrico.

    Devuelve las celdas tocadas con su fracción de área cubierta y cada
    columna prorrateada por esa fracción (`<columna>_prorrateada`), bajo el
    supuesto de población uniforme dentro de la celda.
    """
    tocadas = celdas_m.loc[celdas_m.geometry.intersects(cobertura_m)].copy()
    tocadas["fraccion_area_cubierta"] = (
        tocadas.geometry.intersection(cobertura_m).area / tocadas.geometry.area
    )
    for columna in columnas:
        tocadas[f"{columna}_prorrateada"] = (
            tocadas[columna] * tocadas["fraccion_area_cubierta"]
        )
    return tocadas
