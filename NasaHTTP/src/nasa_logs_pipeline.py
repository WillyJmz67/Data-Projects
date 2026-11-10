"""Pipeline de PySpark: logs HTTP de la NASA (1995) -> reportes de BI.

Reemplaza la lógica del notebook original corrigiendo los bugs detectados:

  1. Ruta del dataset ya no está hardcodeada a una ruta absoluta inexistente.
  2. El regex es robusto: no descarta peticiones sin protocolo ni con espacios
     dobles (el patrón original perdía ~1.800 líneas válidas en silencio).
  3. `content_size` se castea a entero ("-" -> NULL), antes quedaba como texto.
  4. Se generan los 4 CSV que promete el README (antes faltaba
     `reporte_paginas_visitadas.csv` y otro tenía un nombre distinto).
  5. Las salidas van a `output/` con escritura escalable (coalesce), no volcando
     1.5M filas al driver con `toPandas()`.

Uso:
    python src/nasa_logs_pipeline.py
    python src/nasa_logs_pipeline.py --log data/access.log
    python src/nasa_logs_pipeline.py --sample 200000      # prueba rápida
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------------------
# JAVA_HOME: hay que fijarlo ANTES de crear la SparkSession.
# ---------------------------------------------------------------------------
# Spark 3.5 soporta oficialmente Java 8/11/17. Muchas instalaciones Windows sólo
# tienen 21 o 25, así que se elige el más compatible de los disponibles.
_PREFERRED_JDKS = ("jdk-17", "jdk-11", "jdk-21", "jdk-8")


def configure_java_home() -> str:
    """Fija JAVA_HOME a un JDK compatible con Spark y lo devuelve."""
    if os.environ.get("JAVA_HOME") and Path(os.environ["JAVA_HOME"]).is_dir():
        return os.environ["JAVA_HOME"]

    java_root = Path(r"C:\Program Files\Java")
    if not java_root.is_dir():
        return os.environ.get("JAVA_HOME", "")

    installed = {p.name: p for p in java_root.iterdir() if p.is_dir()}
    for prefix in _PREFERRED_JDKS:
        for name, path in sorted(installed.items(), reverse=True):
            if name.startswith(prefix):
                os.environ["JAVA_HOME"] = str(path)
                return str(path)

    return os.environ.get("JAVA_HOME", "")


JAVA_HOME = configure_java_home()


# ---------------------------------------------------------------------------
# SPARK_HOME: hay que sanearlo ANTES de crear la SparkSession.
# ---------------------------------------------------------------------------
# Si el sistema tiene un SPARK_HOME apuntando a una distribución de Spark que ya
# no existe (o con otra versión), PySpark lo obedece y falla con
#   FileNotFoundError: [WinError 2] ... spark-submit.cmd
# Lo más robusto es usar SIEMPRE el Spark que viene empaquetado con el propio
# paquete `pyspark` instalado en el venv: garantiza que las versiones casan.
def configure_spark_home() -> str:
    """Fuerza SPARK_HOME al Spark empaquetado dentro del paquete pyspark."""
    import pyspark

    bundled = str(Path(pyspark.__file__).resolve().parent)
    submit = Path(bundled) / "bin" / "spark-submit.cmd"
    if not submit.is_file():
        submit = Path(bundled) / "bin" / "spark-submit"
    if not submit.is_file():
        raise RuntimeError(
            f"La instalación de pyspark en {bundled} no trae bin/spark-submit. "
            "Reinstala con: pip install --force-reinstall pyspark==3.5.3"
        )

    previous = os.environ.get("SPARK_HOME")
    if previous and Path(previous).resolve() != Path(bundled).resolve():
        print(f"AVISO: SPARK_HOME apuntaba a {previous}; se usa el pyspark del venv.")
    os.environ["SPARK_HOME"] = bundled
    return bundled


SPARK_HOME = configure_spark_home()


# ---------------------------------------------------------------------------
# HADOOP_HOME / winutils: imprescindible en Windows.
# ---------------------------------------------------------------------------
# Hadoop en Windows necesita `winutils.exe` + `hadoop.dll`; sin ellos Spark
# revienta con "HADOOP_HOME and hadoop.home.dir are unset" al inicializar
# ShutdownHookManager (incluso antes de leer nada).
def configure_hadoop_home() -> str | None:
    """Localiza winutils y exporta HADOOP_HOME + PATH. No hace nada fuera de Windows."""
    if os.name != "nt":
        return None

    candidates: list[Path] = []
    if os.environ.get("HADOOP_HOME"):
        candidates.append(Path(os.environ["HADOOP_HOME"]))
    # Binarios incluidos en el repo del proyecto.
    candidates.append(PROJECT_ROOT / "winutils")

    for home in candidates:
        winutils = home / "bin" / "winutils.exe"
        if winutils.is_file():
            os.environ["HADOOP_HOME"] = str(home)
            os.environ.setdefault("hadoop.home.dir", str(home))
            bin_dir = str(home / "bin")
            if bin_dir not in os.environ.get("PATH", ""):
                os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")
            return str(home)

    print(
        "AVISO: no se encontró winutils.exe. En Windows Spark fallará con "
        "'HADOOP_HOME and hadoop.home.dir are unset'.\n"
        "       Descárgalo en winutils/bin/ (ver README) o define HADOOP_HOME."
    )
    return None


HADOOP_HOME = configure_hadoop_home()

from pyspark.sql import SparkSession  # noqa: E402
from pyspark.sql import functions as F  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nasa_logs import (  # noqa: E402
    GROUP_ENDPOINT,
    GROUP_IP,
    GROUP_METHOD,
    GROUP_PROTOCOL,
    GROUP_SIZE,
    GROUP_STATUS,
    GROUP_TIMESTAMP,
    LOG_PATTERN,
    OUTPUT_FILES,
    STRUCTURED_COLUMNS,
    UNKNOWN_METHOD,
    VALID_METHOD_REGEX,
    resolve_log_path,
)

OUTPUT_DIR = PROJECT_ROOT / "output"


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def write_single_csv(df, target: Path) -> None:
    """Escribe un DataFrame como UN único CSV en `target`.

    `df.write.csv()` genera un directorio con ficheros `part-*`; aquí se usa
    `coalesce(1)` y se renombra el `part-` al nombre final, que es lo que
    promete el README.

    IMPORTANTE — `escape='"'`: por defecto Spark escapa las comillas con una
    barra invertida (`\\"`), lo que NO es RFC 4180. El log tiene endpoints con
    comilla (p. ej. `GET /ksc.html" HTTP/1.0" 404 -`) y ese escapado dejaba el
    CSV ilegible para pandas y Excel: el parser no cierra el campo y se traga
    las filas siguientes. Con `escape='"'` Spark duplica la comilla (`""`),
    que es el estándar.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp_dir = target.parent / f"_tmp_{target.stem}"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)

    (
        df.coalesce(1)
        .write.mode("overwrite")
        .option("header", True)
        .option("quote", '"')
        .option("escape", '"')
        .csv(str(tmp_dir))
    )

    part = next(p for p in tmp_dir.glob("part-*.csv"))
    if target.exists():
        target.unlink()
    shutil.move(str(part), str(target))
    shutil.rmtree(tmp_dir)


def verify_csv(csv_path: Path) -> int:
    """Relee el CSV generado y comprueba que ningún parser se atraganta.

    Devuelve el número de filas legibles. Existe porque ya pasó: Spark escribía
    las comillas escapadas con `\\`, el fichero parecía correcto y
    `pandas.read_csv` reventaba con "Expected 7 fields, saw 8" sin que nada
    avisara.
    """
    import pandas as pd

    total = 0
    for chunk in pd.read_csv(csv_path, dtype=str, chunksize=200_000, on_bad_lines="error"):
        if list(chunk.columns) != STRUCTURED_COLUMNS:
            raise ValueError(
                f"cabecera inesperada en {csv_path.name}: {list(chunk.columns)}"
            )
        total += len(chunk)
    return total


def build_spark(app_name: str = "Nasa_Log_Analysis") -> SparkSession:
    return (
        SparkSession.builder.appName(app_name)
        # Necesario: el log trae tamaños "-" y campos que no siempre castean.
        .config("spark.sql.ansi.enabled", "false")
        .config("spark.driver.memory", "4g")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.ui.showConsoleProgress", "false")
        .getOrCreate()
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", help="ruta al access.log (por defecto data/access.log)")
    parser.add_argument(
        "--sample", type=int, default=None, help="procesar sólo N líneas (pruebas)"
    )
    parser.add_argument("--no-plot", action="store_true", help="no generar la gráfica")
    parser.add_argument(
        "--output-dir",
        help="carpeta de salida (por defecto output/ del proyecto)",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve() if args.output_dir else OUTPUT_DIR

    if JAVA_HOME:
        print(f"JAVA_HOME = {JAVA_HOME}")
    else:
        print("AVISO: no se detectó JAVA_HOME; Spark puede fallar al arrancar.")
    print(f"SPARK_HOME = {SPARK_HOME}")
    if HADOOP_HOME:
        print(f"HADOOP_HOME = {HADOOP_HOME}")

    log_path = resolve_log_path(args.log)
    print(f"Dataset   = {log_path} ({log_path.stat().st_size / 1e6:.1f} MB)")

    spark = build_spark()
    spark.sparkContext.setLogLevel("ERROR")

    try:
        # ------------------------------------------------------------------
        # 1. Ingesta
        # ------------------------------------------------------------------
        raw_logs = spark.read.text(str(log_path))
        if args.sample:
            raw_logs = raw_logs.limit(args.sample)
            print(f"Modo muestra: primeras {args.sample:,} líneas")

        # ------------------------------------------------------------------
        # 2. Estructuración (regex robusto, definido en src/nasa_logs.py)
        # ------------------------------------------------------------------
        structured = raw_logs.select(
            F.regexp_extract("value", LOG_PATTERN, GROUP_IP).alias("ip"),
            F.regexp_extract("value", LOG_PATTERN, GROUP_TIMESTAMP).alias("timestamp"),
            # Métodos basura (bytes binarios de sondeos) -> UNKNOWN, sin descartar
            # la fila: la respuesta 400 que generaron sí es información útil.
            F.when(
                F.regexp_extract("value", LOG_PATTERN, GROUP_METHOD).rlike(
                    VALID_METHOD_REGEX.pattern
                ),
                F.regexp_extract("value", LOG_PATTERN, GROUP_METHOD),
            )
            .otherwise(F.lit(UNKNOWN_METHOD))
            .alias("method"),
            F.regexp_extract("value", LOG_PATTERN, GROUP_ENDPOINT).alias("endpoint"),
            F.regexp_extract("value", LOG_PATTERN, GROUP_PROTOCOL).alias("protocol"),
            F.regexp_extract("value", LOG_PATTERN, GROUP_STATUS)
            .cast("int")
            .alias("status_code"),
            # "-" no castea a int -> NULL (equivalente al None de Python puro).
            F.regexp_extract("value", LOG_PATTERN, GROUP_SIZE)
            .cast("int")
            .alias("content_size"),
        )

        total_lines = raw_logs.count()
        # Una línea válida es la que tiene IP Y código de estado.
        structured = structured.filter(
            (F.col("ip") != "") & F.col("status_code").isNotNull()
        )
        parsed = structured.count()
        dropped = total_lines - parsed

        print(f"Líneas leídas      : {total_lines:,}")
        print(f"Registros parseados: {parsed:,}")
        print(f"Líneas descartadas : {dropped:,} ({dropped / total_lines * 100:.3f}%)")

        # ------------------------------------------------------------------
        # 3. Análisis
        # ------------------------------------------------------------------
        # 3a. Seguridad: errores 4xx/5xx por IP (con tasa de fallo real)
        total_por_ip = structured.groupBy("ip").count().withColumnRenamed(
            "count", "total_peticiones"
        )
        errores_por_ip = (
            structured.filter(F.col("status_code") >= 400)
            .groupBy("ip")
            .count()
            .withColumnRenamed("count", "errores")
        )
        reporte_seguridad = (
            total_por_ip.join(errores_por_ip, on="ip", how="inner")
            .withColumn(
                "tasa_error_pct",
                F.round(F.col("errores") / F.col("total_peticiones") * 100, 2),
            )
            .orderBy(F.col("errores").desc(), F.col("tasa_error_pct").desc())
        )

        # 3b. Contenido: recursos más solicitados
        reporte_paginas = (
            structured.groupBy("endpoint")
            .agg(
                F.count("*").alias("peticiones"),
                F.countDistinct("ip").alias("ips_distintas"),
            )
            .orderBy(F.col("peticiones").desc())
        )

        # 3c. Tráfico temporal por hora del día
        structured_hora = structured.withColumn("hour", F.substring("timestamp", 13, 2))
        reporte_trafico = (
            structured_hora.groupBy("hour")
            .agg(
                F.count("*").alias("peticiones"),
                F.countDistinct("ip").alias("ips_distintas"),
            )
            .orderBy("hour")
        )

        # ------------------------------------------------------------------
        # 4. Exportación
        # ------------------------------------------------------------------
        output_dir.mkdir(parents=True, exist_ok=True)
        full_csv = output_dir / OUTPUT_FILES["estructurado"]
        write_single_csv(structured, full_csv)
        written = verify_csv(full_csv)
        status = "OK" if written == parsed else "INCOHERENTE"
        print(
            f"  verificación CSV: {written:,} filas legibles "
            f"(esperadas {parsed:,}) -> {status}"
        )
        if written != parsed:
            raise RuntimeError(
                f"el CSV tiene {written:,} filas pero el DataFrame tenía {parsed:,}"
            )
        reporte_seguridad.limit(100).toPandas().to_csv(
            output_dir / OUTPUT_FILES["seguridad"], index=False
        )
        reporte_trafico.toPandas().to_csv(
            output_dir / OUTPUT_FILES["trafico"], index=False
        )
        reporte_paginas.limit(100).toPandas().to_csv(
            output_dir / OUTPUT_FILES["paginas"], index=False
        )

        # ------------------------------------------------------------------
        # 5. Consola + gráfica
        # ------------------------------------------------------------------
        print("\nTOP 5 IPs CON MÁS ERRORES (posibles atacantes/bots):")
        reporte_seguridad.select(
            "ip", "errores", "total_peticiones", "tasa_error_pct"
        ).show(5, truncate=False)

        print("TOP 5 RECURSOS MÁS SOLICITADOS:")
        reporte_paginas.show(5, truncate=False)

        print("TRÁFICO POR HORA DEL DÍA:")
        reporte_trafico.show(24, truncate=False)

        if not args.no_plot:
            import matplotlib

            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            pdf = reporte_trafico.toPandas()
            fig, ax = plt.subplots(figsize=(10, 4))
            ax.plot(pdf["hour"], pdf["peticiones"], marker="o", color="#1f77b4")
            ax.set_title("Peticiones por hora del día - servidores HTTP NASA (Ago-1995)")
            ax.set_xlabel("Hora del día")
            ax.set_ylabel("Número de peticiones")
            ax.grid(True, alpha=0.3)
            fig.tight_layout()
            plot_path = output_dir / "trafico_por_hora.png"
            fig.savefig(plot_path, dpi=120)
            plt.close(fig)
            print(f"\nGráfica guardada en {plot_path}")

        print(f"\nFicheros generados en {output_dir}:")
        for key, name in OUTPUT_FILES.items():
            f = output_dir / name
            if f.exists():
                print(f"  - {name} ({f.stat().st_size / 1e6:.1f} MB)")

        return 0

    finally:
        spark.stop()


if __name__ == "__main__":
    raise SystemExit(main())
