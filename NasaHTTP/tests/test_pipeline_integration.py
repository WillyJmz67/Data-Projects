"""Test de integración: ejecuta el pipeline de verdad y valida la salida.

Este test existe por un motivo concreto: el bug del escapado de comillas en el
CSV **no lo detectaba ninguna prueba unitaria**. El pipeline terminaba en verde
y el fichero parecía correcto, pero `pandas.read_csv` reventaba porque Spark
escribe las comillas como `\\"` en lugar de `""`.

Es lento (arranca una SparkSession, ~40 s) porque tiene que serlo: la única
forma de verificar que el CSV es legible es escribir un CSV y leerlo.

Se salta automáticamente si PySpark no está instalado.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("pyspark", reason="requiere PySpark instalado en el venv")

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Log sintético con TODOS los casos límite conocidos del dataset real.
SYNTHETIC_LOG = "\n".join(
    [
        # 1. Línea canónica.
        'host1.dom - - [01/Aug/1995:00:00:01 -0400] "GET /a.html HTTP/1.0" 200 100',
        # 2. Sin protocolo (el patrón original la descartaba).
        'host2.dom - - [01/Aug/1995:01:00:02 -0400] "GET /b.html" 200 200',
        # 3. Espacios dobles + tamaño no reportado ("-").
        'host3.dom - - [01/Aug/1995:02:00:03 -0400] "GET /c.html   HTTP/1.0" 404 -',
        # 4. Comilla de más: el endpoint acaba en comilla. ESTE es el caso que
        #    rompía el CSV y que este test protege.
        'host4.dom - - [01/Aug/1995:03:00:04 -0400] "GET /ksc.html" HTTP/1.0" 404 -',
        # 5. Línea corrupta: debe descartarse.
        "linea completamente rota sin estructura",
    ]
) + "\n"

EXPECTED_PARSED = 4


@pytest.fixture(scope="module")
def pipeline_run(tmp_path_factory):
    """Escribe el log sintético, ejecuta el pipeline y devuelve su carpeta de salida."""
    workdir = tmp_path_factory.mktemp("nasa_pipeline")
    log_path = workdir / "synthetic.log"
    log_path.write_text(SYNTHETIC_LOG, encoding="utf-8")
    out_dir = workdir / "out"

    result = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "src" / "nasa_logs_pipeline.py"),
            "--log",
            str(log_path),
            "--output-dir",
            str(out_dir),
            "--no-plot",
        ],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
        timeout=600,
    )

    if result.returncode != 0:
        pytest.fail(
            f"el pipeline falló (rc={result.returncode})\n"
            f"--- stdout ---\n{result.stdout[-3000:]}\n"
            f"--- stderr ---\n{result.stderr[-3000:]}"
        )
    return out_dir, result.stdout


def test_el_pipeline_genera_los_cuatro_csv(pipeline_run):
    out_dir, _ = pipeline_run
    from nasa_logs import OUTPUT_FILES

    for name in OUTPUT_FILES.values():
        assert (out_dir / name).is_file(), f"falta {name}"


def test_el_csv_completo_es_legible_por_pandas(pipeline_run):
    """Regresión del bug de escapado: pandas debe poder leer el CSV sin errores."""
    pd = pytest.importorskip("pandas")
    out_dir, _ = pipeline_run
    from nasa_logs import OUTPUT_FILES, STRUCTURED_COLUMNS

    df = pd.read_csv(
        out_dir / OUTPUT_FILES["estructurado"], dtype=str, keep_default_na=False
    )

    assert list(df.columns) == STRUCTURED_COLUMNS
    assert len(df) == EXPECTED_PARSED, (
        f"el CSV tiene {len(df)} filas y el pipeline parseó {EXPECTED_PARSED}"
    )


def test_los_casos_limite_sobreviven_al_pipeline(pipeline_run):
    """Las 4 líneas válidas deben estar, con sus valores correctos."""
    pd = pytest.importorskip("pandas")
    out_dir, _ = pipeline_run
    from nasa_logs import OUTPUT_FILES

    df = pd.read_csv(out_dir / OUTPUT_FILES["estructurado"], dtype=str, keep_default_na=False)
    by_ip = {row["ip"]: row for _, row in df.iterrows()}

    assert set(by_ip) == {"host1.dom", "host2.dom", "host3.dom", "host4.dom"}

    # Sin protocolo -> protocolo vacío, pero la fila se conserva.
    assert by_ip["host2.dom"]["endpoint"] == "/b.html"
    assert by_ip["host2.dom"]["protocol"] == ""

    # Espacios dobles -> endpoint limpio y content_size vacío (era "-").
    assert by_ip["host3.dom"]["endpoint"] == "/c.html"
    assert by_ip["host3.dom"]["content_size"] == ""

    # Comilla de más -> el endpoint conserva la comilla y el CSV sigue siendo válido.
    assert by_ip["host4.dom"]["endpoint"] == '/ksc.html"'
    assert by_ip["host4.dom"]["status_code"] == "404"


def test_los_reportes_derivados_son_legibles(pipeline_run):
    pd = pytest.importorskip("pandas")
    out_dir, _ = pipeline_run
    from nasa_logs import OUTPUT_FILES

    trafico = pd.read_csv(out_dir / OUTPUT_FILES["trafico"])
    assert list(trafico.columns) == ["hour", "peticiones", "ips_distintas"]
    assert len(trafico) == 4  # 00, 01, 02, 03

    seguridad = pd.read_csv(out_dir / OUTPUT_FILES["seguridad"])
    assert list(seguridad.columns) == [
        "ip",
        "total_peticiones",
        "errores",
        "tasa_error_pct",
    ]
    # host3 y host4 devolvieron 404.
    assert set(seguridad["ip"]) == {"host3.dom", "host4.dom"}
