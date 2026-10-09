"""Configuración compartida por los notebooks: carpetas, .env y constantes."""

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_ROOT = PROJECT_ROOT / "data"
GTFS_DIR = DATA_ROOT / "gtfs"
PROCESSED_DIR = DATA_ROOT / "processed"
CACHE_DIR = DATA_ROOT / "cache"
MAPS_DIR = PROJECT_ROOT / "maps"
ENV_PATH = PROJECT_ROOT / ".env"

if not GTFS_DIR.exists():
    raise FileNotFoundError(f"No se encontró la carpeta GTFS: {GTFS_DIR}")
for directorio in [PROCESSED_DIR, CACHE_DIR, MAPS_DIR]:
    directorio.mkdir(parents=True, exist_ok=True)

CORREGIDORA_LAT = 20.600611
CORREGIDORA_LON = -100.402184


def cargar_env(env_path=ENV_PATH):
    """Carga pares CLAVE=VALOR sencillos sin imprimir secretos.

    Las variables ya definidas en el entorno tienen prioridad sobre el archivo.
    """
    if not env_path.exists():
        return False

    for numero_linea, linea_original in enumerate(
        env_path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        linea = linea_original.strip()
        if not linea or linea.startswith("#"):
            continue
        if linea.startswith("export "):
            linea = linea[7:].strip()
        if "=" not in linea:
            raise ValueError(f"Línea inválida en .env: {numero_linea}")

        clave, valor = linea.split("=", 1)
        clave, valor = clave.strip(), valor.strip()
        if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in {"'", '"'}:
            valor = valor[1:-1]
        os.environ.setdefault(clave, valor)

    return True


def _booleano(clave):
    return os.getenv(clave, "false").strip().lower() == "true"


ENV_CARGADO = cargar_env()

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "").strip() or None
EJECUTAR_GOOGLE_MAPS = _booleano("EJECUTAR_GOOGLE_MAPS")
UMBRAL_ANALISIS_MIN = float(os.getenv("UMBRAL_ANALISIS_MIN", "30"))
# Tiempo GTFS máximo de las paradas que se consultan en Google. Debe cubrir
# el escenario más amplio que se quiera evaluar después (60 minutos).
UMBRAL_CONSULTA_GOOGLE_MIN = float(
    os.getenv("UMBRAL_CONSULTA_GOOGLE_MIN", str(UMBRAL_ANALISIS_MIN))
)
PENALIZACION_TRANSBORDO_MIN = float(os.getenv("PENALIZACION_TRANSBORDO_MIN", "5"))
MAX_EDAD_ETA_HORAS = float(os.getenv("MAX_EDAD_ETA_HORAS", "24"))
MIN_OBSERVACIONES_HISTORICAS = int(os.getenv("MIN_OBSERVACIONES_HISTORICAS", "5"))
RETENCION_HISTORICO_DIAS = int(os.getenv("RETENCION_HISTORICO_DIAS", "365"))
RADIO_DEMANDA_M = float(os.getenv("RADIO_DEMANDA_M", "20"))
ACTUALIZAR_DATOS_INEGI = _booleano("ACTUALIZAR_DATOS_INEGI")
ACTUALIZAR_RED_OSM = _booleano("ACTUALIZAR_RED_OSM")

if EJECUTAR_GOOGLE_MAPS and not GOOGLE_MAPS_API_KEY:
    raise RuntimeError("EJECUTAR_GOOGLE_MAPS=true, pero falta GOOGLE_MAPS_API_KEY.")
if UMBRAL_ANALISIS_MIN <= 0:
    raise ValueError("UMBRAL_ANALISIS_MIN debe ser mayor que cero.")
if UMBRAL_CONSULTA_GOOGLE_MIN < UMBRAL_ANALISIS_MIN:
    raise ValueError(
        "UMBRAL_CONSULTA_GOOGLE_MIN no puede ser menor que UMBRAL_ANALISIS_MIN."
    )
if PENALIZACION_TRANSBORDO_MIN < 0:
    raise ValueError("PENALIZACION_TRANSBORDO_MIN no puede ser negativa.")
if MAX_EDAD_ETA_HORAS <= 0:
    raise ValueError("MAX_EDAD_ETA_HORAS debe ser mayor que cero.")
if MIN_OBSERVACIONES_HISTORICAS <= 0:
    raise ValueError("MIN_OBSERVACIONES_HISTORICAS debe ser mayor que cero.")
if RADIO_DEMANDA_M <= 0:
    raise ValueError("RADIO_DEMANDA_M debe ser mayor que cero.")
