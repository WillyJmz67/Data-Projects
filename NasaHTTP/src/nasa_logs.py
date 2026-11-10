"""Núcleo del parsing de logs HTTP de la NASA (formato Common Log Format ampliado).

Este módulo es la **única fuente de verdad** del patrón de parsing: lo usa tanto
el pipeline de PySpark (`nasa_logs_pipeline.py`) como las pruebas (`tests/`).

Se mantiene libre de dependencias de Spark a propósito, para poder validar el
regex con Python puro sin levantar un cluster.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Patrón de parsing
# ---------------------------------------------------------------------------
# Formato de una línea válida:
#   in24.inetnebr.com - - [01/Aug/1995:00:00:01 -0400] "GET /ruta HTTP/1.0" 200 1839
#
# Grupos de captura:
#   1 -> ip
#   2 -> timestamp
#   3 -> method
#   4 -> endpoint
#   5 -> protocol  (OPCIONAL: el log real trae peticiones sin "HTTP/1.0")
#   6 -> status_code
#   7 -> content_size  ("-" cuando el servidor no reporta tamaño)
#
# Notas de robustez (corrigen bugs del patrón original):
#   * El protocolo es opcional: 1.791 líneas del log real son peticiones
#     sin "HTTP/x.x" y el patrón original las descartaba en silencio.
#   * Se usa \s+ en lugar de un espacio literal: hay líneas con espacios
#     dobles de separación ("GET /ruta   HTTP/1.0").
LOG_PATTERN = (
    r'^(\S+) - - \[(.*?)\] "(\S+)\s+(\S+?)(?:\s+(\S+))?\s*"\s+(\d{3})\s+(\d+|-)'
)

LOG_REGEX = re.compile(LOG_PATTERN)

# Un método HTTP válido es un token alfabético (GET, HEAD, POST, ...).
# El log contiene 4 líneas con bytes binarios en lugar de una petición (sondeos
# de exploits que el servidor rechazó con 400); su "método" es basura. Se
# normalizan a UNKNOWN para no ensuciar la columna, pero NO se descartan: la
# respuesta 400 es información de seguridad válida.
VALID_METHOD_REGEX = re.compile(r"^[A-Za-z]+$")
UNKNOWN_METHOD = "UNKNOWN"

# Orden de los grupos tal como los expone regexp_extract (1-indexado en Spark).
GROUP_IP = 1
GROUP_TIMESTAMP = 2
GROUP_METHOD = 3
GROUP_ENDPOINT = 4
GROUP_PROTOCOL = 5
GROUP_STATUS = 6
GROUP_SIZE = 7

# Nombres de los ficheros de salida (contrato con el README).
OUTPUT_FILES = {
    "estructurado": "nasa_logs_estructurados_FULL.csv",
    "seguridad": "reporte_seguridad_ips.csv",
    "trafico": "reporte_trafico_hora.csv",
    "paginas": "reporte_paginas_visitadas.csv",
}

# Columnas del dataset estructurado, en orden. Es el contrato entre el pipeline
# (que las construye) y la verificación de integridad del CSV (que las comprueba).
STRUCTURED_COLUMNS = [
    "ip",
    "timestamp",
    "method",
    "endpoint",
    "protocol",
    "status_code",
    "content_size",
]

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def parse_line(line: str) -> dict | None:
    """Parsea una línea del log con Python puro. Devuelve None si es corrupta.

    Se usa en las pruebas y sirve de referencia de comportamiento para la
    versión Spark (mismo patrón, mismos grupos).
    """
    m = LOG_REGEX.match(line.rstrip("\n"))
    if not m:
        return None

    ip, timestamp, method, endpoint, protocol, status, size = m.groups()

    # El tamaño puede venir como "-" (el servidor no lo reporta).
    content_size = None if size == "-" else int(size)

    # La hora está en las posiciones 13-14 de "01/Aug/1995:00:00:01 -0400".
    hour = timestamp[12:14]

    return {
        "ip": ip,
        "timestamp": timestamp,
        "method": method if VALID_METHOD_REGEX.match(method) else UNKNOWN_METHOD,
        "endpoint": endpoint,
        "protocol": protocol or None,
        "status_code": int(status),
        "content_size": content_size,
        "hour": hour,
    }


def resolve_log_path(cli_path: str | None = None) -> Path:
    """Localiza el access.log de forma portable (sin rutas absolutas fijas).

    Orden de prioridad:
      1. Argumento de línea de comandos (--log).
      2. Variable de entorno NASA_LOG_PATH.
      3. data/access.log dentro del proyecto.
    """
    candidates: list[Path] = []

    if cli_path:
        candidates.append(Path(cli_path))
    if os.environ.get("NASA_LOG_PATH"):
        candidates.append(Path(os.environ["NASA_LOG_PATH"]))

    candidates.append(PROJECT_ROOT / "data" / "access.log")

    for candidate in candidates:
        if candidate.is_file():
            return candidate

    checked = "\n  - ".join(str(c) for c in candidates)
    raise FileNotFoundError(
        "No se encontró el fichero access.log. Rutas comprobadas:\n  - "
        f"{checked}\n\n"
        "Descarga el dataset 'NASA HTTP logs' (Datacamp / Kaggle) y colócalo en "
        "data/access.log, o indica la ruta con --log RUTA o la variable de "
        "entorno NASA_LOG_PATH."
    )
