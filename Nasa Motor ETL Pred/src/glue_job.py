"""Template de AWS Glue Job (PySpark) para ejecutar el ETL en la nube.

NOTA: este fichero sólo corre dentro de AWS Glue (depende de las librerías
`awsglue`). El equivalente ejecutable en local es `src/transform.py`
(`transform_pandas` / `transform_spark`).
"""

from __future__ import annotations

import sys

# Librerías solo disponibles en el entorno de AWS Glue
from awsglue.utils import getResolvedOptions  # type: ignore
from pyspark.context import SparkContext  # type: ignore
from awsglue.context import GlueContext  # type: ignore
from pyspark.sql import Window  # type: ignore
from pyspark.sql import functions as F  # type: ignore

RUL_THRESHOLD = 30
COLUMNS = ["id", "cycle", "op1", "op2", "op3", *[f"s{i}" for i in range(1, 22)]]
INT_COLS = {"id", "cycle"}


def read_cmapss(spark, src: str):
    """Lee un .txt de CMAPSS tolerando los espacios finales de cada línea.

    Los ficheros de NASA terminan en espacio, así que un split por " " puede
    generar columnas vacías al final. Se toman las 26 primeras columnas por
    posición y se castean explícitamente a int/double.
    """
    raw = spark.read.option("header", False).option("sep", " ").csv(src)
    cols = raw.columns
    if len(cols) < len(COLUMNS):
        raise ValueError(
            f"{src}: se esperaban al menos {len(COLUMNS)} columnas, hay {len(cols)}"
        )
    selected = [
        F.col(cols[i]).cast("int" if name in INT_COLS else "double").alias(name)
        for i, name in enumerate(COLUMNS)
    ]
    return raw.select(*selected).filter(F.col("id").isNotNull())


def run_job(src: str, dst: str) -> None:
    sc = SparkContext()
    glue_ctx = GlueContext(sc)
    spark = glue_ctx.spark_session

    df = read_cmapss(spark, src)

    # Ojo: F.window() es para ventanas TEMPORALES (exige columna timestamp +
    # duración). Para "máximo por motor" se usa Window.partitionBy.
    w = Window.partitionBy("id")
    max_c = F.max("cycle").over(w)
    df = df.withColumn("rul", (max_c - F.col("cycle")).cast("int"))
    df = df.withColumn("label", (F.col("rul") <= RUL_THRESHOLD).cast("int"))

    df.write.mode("overwrite").parquet(dst)
    print(f"Glue job completado: {src} -> {dst}")


def main() -> None:
    args = getResolvedOptions(sys.argv, ["JOB_NAME", "SRC", "DST"])
    run_job(args["SRC"], args["DST"])


if __name__ == "__main__":
    main()
