"""Pruebas del parsing de logs. No necesitan Spark ni Docker: `pytest` y listo.

Estas pruebas fijan el comportamiento del regex, incluyendo los casos límite
que rompían el patrón original (peticiones sin protocolo, espacios dobles).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from nasa_logs import (  # noqa: E402
    LOG_PATTERN,
    OUTPUT_FILES,
    UNKNOWN_METHOD,
    parse_line,
)


# --------------------------------------------------------------------------
# Casos que SÍ deben parsearse
# --------------------------------------------------------------------------
VALID_LINES = [
    # Línea canónica del dataset.
    (
        'in24.inetnebr.com - - [01/Aug/1995:00:00:01 -0400] '
        '"GET /shuttle/missions/sts-68/news/sts-68-mcc-05.txt HTTP/1.0" 200 1839',
        {
            "ip": "in24.inetnebr.com",
            "method": "GET",
            "endpoint": "/shuttle/missions/sts-68/news/sts-68-mcc-05.txt",
            "protocol": "HTTP/1.0",
            "status_code": 200,
            "content_size": 1839,
            "hour": "00",
        },
    ),
    # Tamaño no reportado por el servidor ("-").
    (
        'uplherc.upl.com - - [01/Aug/1995:00:00:07 -0400] "GET / HTTP/1.0" 304 -',
        {
            "ip": "uplherc.upl.com",
            "method": "GET",
            "endpoint": "/",
            "protocol": "HTTP/1.0",
            "status_code": 304,
            "content_size": None,
            "hour": "00",
        },
    ),
    # BUG 1: petición SIN protocolo. El patrón original la descartaba.
    (
        'pipe1.nyc.pipeline.com - - [01/Aug/1995:00:12:37 -0400] '
        '"GET /history/apollo/apollo-13/apollo-13-patch-small.gif" 200 12',
        {
            "ip": "pipe1.nyc.pipeline.com",
            "method": "GET",
            "endpoint": "/history/apollo/apollo-13/apollo-13-patch-small.gif",
            "protocol": None,
            "status_code": 200,
            "content_size": 12,
            "hour": "00",
        },
    ),
    # BUG 2: espacios dobles de separación dentro de las comillas.
    (
        'macip-dialup-060.cisco.com - - [01/Aug/1995:03:58:23 -0400] '
        '"GET /facts/internet/bdgtti-1.01.html   HTTP/1.0" 200 344064',
        {
            "ip": "macip-dialup-060.cisco.com",
            "method": "GET",
            "endpoint": "/facts/internet/bdgtti-1.01.html",
            "protocol": "HTTP/1.0",
            "status_code": 200,
            "content_size": 344064,
            "hour": "03",
        },
    ),
    # Petición con query string y error 404.
    (
        'dialip-217.den.mmc.com - - [01/Aug/1995:15:00:00 -0400] '
        '"GET /htbin/cdt_main.pl?cdtitem=noaa HTTP/1.0" 404 0',
        {
            "ip": "dialip-217.den.mmc.com",
            "method": "GET",
            "endpoint": "/htbin/cdt_main.pl?cdtitem=noaa",
            "protocol": "HTTP/1.0",
            "status_code": 404,
            "content_size": 0,
            "hour": "15",
        },
    ),
]


@pytest.mark.parametrize("line, expected", VALID_LINES)
def test_parsea_lineas_validas(line, expected):
    parsed = parse_line(line)
    assert parsed is not None, f"no se pudo parsear: {line}"
    for key, value in expected.items():
        assert parsed[key] == value, f"{key}: {parsed[key]!r} != {value!r}"


def test_la_hora_se_extrae_de_las_posiciones_correctas():
    """La hora son los caracteres 13-14 de '01/Aug/1995:00:00:01 -0400'."""
    for hour in ("00", "07", "13", "23"):
        line = (
            'host.dom - - [01/Aug/1995:%s:59:59 -0400] "GET / HTTP/1.0" 200 1' % hour
        )
        assert parse_line(line)["hour"] == hour


def test_metodos_no_get_tambien_se_parsean():
    line = 'host.dom - - [01/Aug/1995:10:00:00 -0400] "HEAD /index.html HTTP/1.0" 200 512'
    assert parse_line(line)["method"] == "HEAD"


def test_metodo_basura_se_normaliza_a_unknown_sin_perder_la_fila():
    """Sondeos binarios: la respuesta 400 es válida, el método no.

    El log contiene 10 líneas con bytes binarios en lugar de una petición. De
    ellas, 4 contienen espacios internos y por tanto coinciden con el patrón.
    Se conservan (el 400 es información de seguridad: el servidor las rechazó)
    pero con method=UNKNOWN para no ensuciar la columna.
    """
    line = (
        '128.159.117.22 - - [30/Aug/1995:13:45:35 -0400] '
        '"\xfd\xd1\xed.\x8a\x0b2\xed.\x8b>\xee .\x8a\x032'
        '\xe4\xd1\xe5\xe9\xe2\xfd\xbd\xff\xff\xc3.\xc7\x06\xe2 " 400 -'
    )
    parsed = parse_line(line)
    assert parsed is not None, "la fila no debe descartarse"
    assert parsed["method"] == UNKNOWN_METHOD
    assert parsed["status_code"] == 400
    assert parsed["ip"] == "128.159.117.22"
    assert parsed["content_size"] is None


def test_sondeo_binario_sin_espacios_se_rechaza():
    """Si el payload no tiene espacios no hay petición que extraer: se descarta."""
    line = (
        '128.159.144.83 - - [14/Aug/1995:15:51:37 -0400] '
        '"\x16\xb1\x02\x896\x9e\x02\xffT7\x89F\x10\xc3\xc7F\x10\x01" 400 -'
    )
    assert parse_line(line) is None


# --------------------------------------------------------------------------
# Casos que deben RECHAZARSE (basura real del fichero)
# --------------------------------------------------------------------------
INVALID_LINES = [
    "",
    "linea completamente rota sin estructura",
    # Comilla extra: el endpoint se cierra antes de tiempo.
    'userp2.snowhill.com - - [05/Aug/1995:14:57:06 -0400] "GET / " HTTP/1.0" 200 7034',
    # Espacio literal dentro del endpoint (URL sin codificar, corrupta).
    'sgate08.st-and.ac.uk - - [04/Aug/1995:17:52:59 -0400] '
    '"GET /htbin/wais.pl?Wake Shield HTTP/1.0" 200 6858',
    # Código de estado truncado (no son 3 dígitos).
    'host.dom - - [01/Aug/1995:00:00:01 -0400] "GET /x HTTP/1.0" 20',
]


@pytest.mark.parametrize("line", INVALID_LINES)
def test_rechaza_lineas_corruptas(line):
    assert parse_line(line) is None


# --------------------------------------------------------------------------
# Contrato con el README
# --------------------------------------------------------------------------
def test_el_patron_es_el_documentado_en_el_readme():
    """El README cita el patrón; debe coincidir con el del código."""
    readme = (Path(__file__).resolve().parents[1] / "NasaHTTP_PySpark_README.md").read_text(
        encoding="utf-8"
    )
    assert LOG_PATTERN in readme, "el README no cita el patrón real de parsing"


def test_el_readme_documenta_los_mismos_ficheros_de_salida():
    readme = (Path(__file__).resolve().parents[1] / "NasaHTTP_PySpark_README.md").read_text(
        encoding="utf-8"
    )
    for filename in OUTPUT_FILES.values():
        assert filename in readme, f"el README no menciona la salida {filename}"
