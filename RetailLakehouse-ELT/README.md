# 🏗️ RetailLakehouse-ELT — Manual de uso

**Migración ELT de una base relacional a un data lakehouse abierto**
`PostgreSQL → MinIO (staging) → Spark (Parquet) → Hive Metastore → dbt → Trino`

> Este README es el manual del proyecto: **qué hace**, **cómo funciona por dentro**,
> **de dónde salen los datos** y **qué tienes que ejecutar tú, paso a paso** (con y sin Airflow).

---

## 0. TL;DR (30 segundos)

```bash
cd RetailLakehouse-ELT
cp .env.example .env                       # 1) credenciales (opcional, hay valores por defecto)

mkdir -p config/hive/lib                   # 2) driver JDBC del Hive Metastore (~1 MB, no se versiona)
curl -sSL -o config/hive/lib/postgresql-42.7.3.jar \
  https://jdbc.postgresql.org/download/postgresql-42.7.3.jar

python scripts/generate_sample_data.py --out-dir data/raw   # 3) datos de origen (CSV)
docker compose up -d --build               # 4) levanta el stack (5-10 min la 1ª vez)
docker compose --profile tools run --rm seed-postgres       # 5) carga los CSV en PostgreSQL
docker compose exec -T airflow-scheduler airflow dags unpause retail_lakehouse_elt
docker compose exec -T airflow-scheduler airflow dags trigger retail_lakehouse_elt
```

Y abre <http://localhost:8081> (Airflow, `airflow`/`airflow`) para ver el DAG correr.
Al terminar: documentación dbt en <http://localhost:8080> y consultas en Trino.

Si prefieres **ejecutar cada etapa a mano**, salta a la [sección 5](#5-ejecución-manual-paso-a-paso).

> **⚠️ El paso 2 no es opcional.** El `docker-compose.yml` monta ese `.jar` dentro del
> contenedor del metastore. Si no existe, Docker crea un **directorio** vacío en su lugar y
> Hive falla con un error confuso de driver JDBC.

> **Windows:** Git Bash **no trae `make`**. El `Makefile` es sólo azúcar sintáctica: todos los
> comandos de este README están escritos con `docker compose`, así que puedes seguirlo tal cual.
> (Si quieres `make`, instálalo con `choco install make`.)

---

## 1. ¿Qué hace?

Saca las ventas de una base transaccional PostgreSQL y las convierte en un **lakehouse**:
ficheros **Parquet** en un object storage tipo S3, **catalogados** en un Hive Metastore y
consultables con **SQL estándar** desde Trino, con las transformaciones **versionadas en dbt**.

| Antes (OLTP) | Después (Lakehouse) |
|---|---|
| El BI compite con la operación | Copia inmutable en object storage |
| Ficheros sueltos sin histórico | Parquet + Snappy particionado por `order_year/order_month` |
| Transformaciones en scripts sueltos | Modelos dbt documentados y con tests |
| Nadie sabe qué significa cada campo | Catálogo (Hive Metastore) + documentación dbt publicada |
| Un motor para todo | Spark para el peso pesado, Trino para consultas ad-hoc |

**Dominio:** e-commerce brasileño (mismo esquema que el dataset público de **Olist**:
`customers`, `orders`, `order_items`, `order_payments`, `order_reviews`, `products`, `sellers`, `geolocation`).

---

## 2. ¿Cómo funciona? (etapa por etapa)

```
PostgreSQL ──(1) extract──► MinIO staging/ (CSV) ──(2) spark──► MinIO lake/raw/ (Parquet)
                                                                        │
                                                          (3) sync_partition_metadata
                                                                        ▼
                                                       ┌─────────────────────────────┐
                                                       │ Hive Metastore (catálogo)   │
                                                       └──────────────┬──────────────┘
                                                                      │
                                    (4) dbt seed/run/test/docs ───────┤
                                                                      ▼
                                                  MinIO lake/lakehouse/ (Parquet de los marts)
                                                                      │
                                                        (5) SELECT … ▼
                                                                Trino
```

| # | Etapa | Quién lo ejecuta | Entra | Sale | Dónde queda |
|---|---|---|---|---|---|
| **1** | **Extract** | Airflow → `extract/extract_postgres_to_minio.py` | Tablas de PostgreSQL | CSV por chunks + `manifest.json` | `s3://staging/postgres/olist/<tabla>/ingest_date=AAAA-MM-DD/` |
| **2** | **Load / RAW** | Airflow → `SparkSubmitOperator` → `spark/jobs/raw_to_parquet.py` | Los CSV de staging | Parquet Snappy, deduplicado, particionado | `s3://lake/raw/<tabla>/` |
| **3** | **Catálogo** | Airflow (cliente Python de Trino) | Ficheros nuevos en `lake/raw/` | Particiones registradas | Hive Metastore (`hive.raw.*`) vía `sync_partition_metadata` |
| **4** | **Transform** | Airflow → `dbt deps/seed/run/test/docs` | `hive.raw.*` + seed de categorías | Tablas y vistas analíticas | `hive.staging.*` (vistas) y `hive.lakehouse.*` (tablas Parquet) |
| **5** | **Consulta** | Tú (CLI/UI de Trino, BI, notebooks) | Catálogo + Parquet | Resultados SQL | — |

### Las 10 tareas del DAG

El DAG `retail_lakehouse_elt` ejecuta en cadena, y cada tarea depende de que la anterior termine bien:

| # | Tarea | Tipo | Qué hace |
|---|---|---|---|
| 1 | `extract_postgres_to_minio` | BashOperator | Lanza el script de extracción con `--run-date {{ ds }}` |
| 2 | `spark_csv_to_parquet` | SparkSubmitOperator | Envía el job PySpark al cluster standalone |
| 3 | `sync_raw_partitions` | PythonOperator | `CALL hive.system.sync_partition_metadata(...)` por cada tabla particionada |
| 4 | `check_raw_not_empty` | PythonOperator | *Smoke test*: falla el DAG si `hive.raw.orders` quedó vacío |
| 5 | `clean_seed_locations` | PythonOperator | Vacía en S3 el prefijo del seed (ver *idempotencia* más abajo) |
| 6 | `dbt_deps` | BashOperator | Instala `dbt_utils`; sin él ningún modelo que lo use compila |
| 7 | `dbt_seed` | BashOperator | Carga la tabla de traducción de categorías |
| 8 | `dbt_run` | BashOperator | Crea vistas (`staging`, `intermediate`) y tablas (`marts`) |
| 9 | `dbt_test` | BashOperator | Tests de calidad; si alguno falla, la tarea falla |
| 10 | `dbt_docs_generate` | BashOperator | Regenera el sitio estático (`ALL_DONE`: se genera aunque haya fallos) |

### Detalle de cada etapa

**1. Extracción — `extract/extract_postgres_to_minio.py`**
- Se conecta con **SQLAlchemy** y lee por *chunks* de 100 000 filas (no carga la tabla en memoria).
- Escribe un CSV por chunk directamente en MinIO con `boto3` (`put_object`).
- Guarda un `manifest.json` por ejecución (filas, bytes, query) → sirve para auditar y cuadrar.
- Soporta **extracción incremental**: con `--run-date D` extrae la ventana `[D, D+1)` de las tablas
  con columna temporal (`orders.order_purchase_timestamp`). El resto de tablas (dimensiones y
  `order_reviews`) se extraen completas en cada ejecución, porque su zona raw no está particionada
  y un `overwrite` incremental borraría el histórico. Con `--full-refresh` extrae todo.

**2. Spark — `spark/jobs/raw_to_parquet.py`**
- Esquema **declarado** (no inferido) para cada tabla → tipos estables y sin escaneo extra.
- Deduplica por clave primaria (`dropDuplicates`).
- Añade `order_year` / `order_month` a `orders`, y se los presta a `order_items` con un
  **broadcast join** por `order_id`.
- Escribe Parquet con compresión **Snappy**, `coalesce(1)` por partición (evita *small files*) y
  `partitionOverwriteMode=dynamic` → reejecutar sólo reescribe las particiones del lote (idempotente).

**3. Catálogo — Hive Metastore + Trino**
- `scripts/init_trino_schemas.sql` crea los esquemas (`raw`, `staging`, `lakehouse`) **apuntando a
  MinIO** y las 8 tablas externas de la zona raw.
- Tras cada carga, el DAG ejecuta `CALL hive.system.sync_partition_metadata('raw','<tabla>','ADD')`
  (el equivalente a `MSCK REPAIR TABLE`) para que el catálogo descubra las carpetas
  `order_year=2017/order_month=5/`.
- **El metastore guarda metadatos, no datos.** Su `warehouse.dir` es un directorio local del
  contenedor (`/tmp/warehouse`); lo que apunta a MinIO son los `LOCATION` de cada esquema/tabla.
  Para poder validarlos, `hive-site.xml` mapea `s3://` → `S3AFileSystem` y el contenedor copia los
  jars `hadoop-aws` / `aws-java-sdk` desde `/opt/hadoop` a `/opt/hive/lib` al arrancar.

**4. dbt (con el adaptador dbt-trino)**
- `staging/` (8 vistas): limpieza, tipado, normalización (estados en mayúsculas, categorías traducidas al inglés…).
- `intermediate/` (3 vistas): `int_order_lines` (líneas enriquecidas), agregados de pagos y reseñas por pedido.
- `marts/` (6 tablas Parquet): `fct_orders`, `dim_customers`, `dim_products`, `agg_sales_monthly`,
  `agg_category_monthly`, `customer_retention_cohorts`.
  - `dim_customers` se construye a grano `customer_unique_id` (**persona**), no `customer_id`
    (que en Olist es una clave por pedido): así `lifetime_value` no se duplica al sumarlo en un BI.
- Macro propio `title_case()`: **Trino 442 no implementa `INITCAP` ni `TITLE_CASE`**, así que se
  resuelve con `split` + `transform` + `array_join` (`dbt/macros/title_case.sql`).
- Las dependencias se instalan en `/opt/airflow/dbt_packages` (`packages-install-path` en
  `dbt_project.yml`), **fuera** del bind-mount de `./dbt`, para que el volumen montado no las borre.
- **Idempotencia del seed:** en este stack `DROP TABLE` borra la tabla del metastore pero **deja los
  Parquet en S3**; el `CREATE` siguiente fallaría con `HIVE_PATH_ALREADY_EXISTS`. Por eso la tarea
  `clean_seed_locations` vacía el prefijo del seed antes de `dbt seed`.
- Tests y documentación en cada ejecución.

**5. Trino**
- Motor SQL federado: puede consultar **a la vez** el PostgreSQL de origen y el lakehouse,
  lo que permite la **cuadratura** origen↔lakehouse en una sola query.

---

## 3. ¿Qué base de datos usa y de dónde salen los datos?

### Base de datos de ORIGEN
| | |
|---|---|
| Motor | **PostgreSQL 15** (contenedor `rl-postgres-source`) |
| Base / usuario / password | `olist` / `olist` / `olist` |
| Puerto en tu máquina | `5432` (cambiable con `PG_HOST_PORT` en `.env`) |
| Esquema | 8 tablas con FKs, PKs e índices (ver `scripts/seed_postgres.py`) |

| Tabla | Descripción | Filas (muestra, semilla 42) |
|---|---|---|
| `customers` | Maestro de clientes | 12 000 |
| `geolocation` | Referencia geográfica por CP | 3 000 |
| `sellers` | Vendedores | 300 |
| `products` | Productos + categoría | 2 000 |
| `orders` | Pedidos (cabecera) | 18 000 |
| `order_items` | Líneas de pedido (1-4 por pedido) | 44 604 |
| `order_payments` | Pagos (1-2 por pedido, **suman** el total) | 22 478 |
| `order_reviews` | Reseñas y score 1-5 (~65 % de los entregados) | 10 472 |

Rango temporal de los pedidos: **2016-09 → 2018-08**.

### ¿De dónde saco los datos? Dos opciones

**A) Dataset sintético (por defecto, ya incluido)** ✅
- `scripts/generate_sample_data.py` genera CSVs **deterministas** (semilla fija `42`) con el mismo
  esquema del dataset público de Olist: estados, categorías, distribución de precios, estatus de
  pedido, tiempos de entrega y reseñas realistas. Los pagos se generan de forma que **la suma de las
  cuotas es exactamente el total del pedido**, igual que en el Olist real.
- Total ≈ **12 MB** en `data/raw/`. Están en el `.gitignore` (se regeneran con `make gen-data`),
  así que el repo pesa poco y nunca falla por falta de credenciales.
- Los conteos de `order_items` / `order_payments` / `order_reviews` dependen del azar, pero al usar
  semilla fija son **siempre los mismos**.

**B) Dataset real de Olist (Kaggle)** — opcional
1. Descarga <https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce>
   (`olist_customers_dataset.csv`, `olist_orders_dataset.csv`, …).
2. Renómbralos sin el prefijo `olist_` y sin el sufijo `_dataset` → `customers.csv`, `orders.csv`, …
   y déjalos en `data/raw/` (mismo nombre de columnas: ya coincide).
3. `docker compose --profile tools run --rm seed-postgres`.

> Ojo: con el dataset real algunos productos no tienen categoría. El modelo `stg_products` ya lo
> contempla (`coalesce(..., 'unknown')`), así que los tests siguen pasando.

### Bases de datos *de soporte* (no son el origen)
- `postgres-meta` (`rl-postgres-meta`): aloja el esquema del **Hive Metastore** (`metastore`)
  y la metadata de **Airflow** (`airflow`). Se agrupan para ahorrar RAM.
- **MinIO**: object storage con dos buckets → `staging/` (CSV crudo) y `lake/` (Parquet).
- **Hive Metastore**: guarda *metadatos* (esquemas, tablas, particiones, rutas S3), no datos.

---

## 4. Requisitos y arranque

- **Docker Desktop encendido** con **≥ 8 GB de RAM** y **≥ 4 CPUs** asignados.
  El stack define 14 servicios, de los que **10 quedan corriendo**, 3 son de inicialización
  (`minio-init`, `trino-init`, `airflow-init`: terminan y salen) y `seed-postgres` sólo se usa a mano.
  > ⚠️ Si `docker compose ps` da error de `npipe`/daemon, es que Docker Desktop no está abierto.
- **Conexión a internet la primera vez**: descarga imágenes (~3 GB) y, dentro del build de Airflow,
  paquetes de `apt` y de `pip`.
- **Python 3.11+** en tu máquina (sólo para generar datos y correr los tests unitarios).
- Puertos libres: `5432, 7077, 8080-8084, 9000, 9001, 9083`.

```bash
cp .env.example .env     # opcional: cambia credenciales / PG_HOST_PORT si choca con tu Postgres local
```

### Servicios, puertos y accesos

| Servicio | URL | Credenciales |
|---|---|---|
| **dbt docs** (documentación) | <http://localhost:8080> | — |
| **Airflow** | <http://localhost:8081> | `airflow` / `airflow` |
| **Trino** | <http://localhost:8082> | usuario `dbt` (sin password) |
| **Spark Master** | <http://localhost:8083> | — |
| **Spark Worker** | <http://localhost:8084> | — |
| **MinIO API / Consola** | <http://localhost:9000> · <http://localhost:9001> | `minioadmin` / `minioadmin` |
| **PostgreSQL origen** | `localhost:5432` | db `olist`, user `olist`, pass `olist` |
| **Hive Metastore** | thrift `localhost:9083` | — |

### Ajustes de memoria (si tu equipo va justo)

Ya vienen rebajados para caber en 8 GB. Si necesitas más margen, toca estos dos ficheros:

| Fichero | Qué cambiar |
|---|---|
| `config/trino/jvm.config` | `-Xmx2G` → `-Xmx1G` |
| `docker-compose.yml` (servicio `spark-worker`) | `SPARK_WORKER_MEMORY=1G` → `512M` y/o `SPARK_WORKER_CORES` |

> **Windows sin `make`**: todos los comandos del Makefile tienen su equivalente `docker compose …`
> en este README. Si tienes `make` (Git Bash / WSL / Chocolatey), `make help` los lista todos.

---

## 5. Ejecución manual paso a paso

### 5-A. Puesta en marcha (una sola vez)

```bash
# 0) Driver JDBC para el Hive Metastore (no se versiona, ~1 MB)
mkdir -p config/hive/lib
curl -sSL -o config/hive/lib/postgresql-42.7.3.jar https://jdbc.postgresql.org/download/postgresql-42.7.3.jar

# 1) Datos de origen (CSV en data/raw)
python scripts/generate_sample_data.py --out-dir data/raw

# 2) Levantar el stack (la 1ª vez construye la imagen de Airflow: Java 17 + PySpark + dbt)
docker compose up -d --build

# 3) Crear el esquema de ventas en PostgreSQL y cargar los CSV
docker compose --profile tools run --rm seed-postgres

# 4) Comprobar que todo está arriba
docker compose ps
```

Salida esperada de `docker compose ps`: 10 contenedores corriendo
(`rl-postgres-source`, `rl-postgres-meta`, `rl-minio`, `rl-hive-metastore`, `rl-spark-master`,
`rl-spark-worker`, `rl-trino`, `rl-airflow-webserver`, `rl-airflow-scheduler`, `rl-dbt-docs`),
más `rl-minio-init`, `rl-trino-init` y `rl-airflow-init` en estado `Exited (0)` — es lo normal:
son tareas de inicialización que terminan.

---

### 5-B. Ejecutar TODO con Airflow (lo habitual)

```bash
docker compose exec -T airflow-scheduler airflow dags unpause retail_lakehouse_elt
docker compose exec -T airflow-scheduler airflow dags trigger retail_lakehouse_elt
docker compose logs -f airflow-scheduler      # Ctrl+C para salir
```

Para seguir el avance:

```bash
# Estado de la última ejecución (running / success / failed)
docker compose exec -T airflow-scheduler airflow dags list-runs --dag-id retail_lakehouse_elt

# Estado tarea por tarea (copia el dag_run_id de la salida anterior)
docker compose exec -T airflow-scheduler airflow tasks states-for-dag-run \
  retail_lakehouse_elt manual__2024-01-01T00:00:00+00:00
```

O desde la UI: <http://localhost:8081> → DAG `retail_lakehouse_elt` → **▶ Trigger**
(y la vista *Graph* para ver las 10 tareas en vivo).

---

### 5-C. Ejecutar cada etapa A MANO (sin Airflow)

Úsalo para entender/depurar el pipeline. **Importante:** la fecha que pasas a la extracción
(`--run-date`) y a Spark (`--ingest-date`) **debe ser la misma**, porque Spark lee justo el prefijo
`ingest_date=` que escribió la extracción.

```bash
FECHA=2024-01-01
```

**① Extracción: PostgreSQL → CSV en MinIO**
```bash
docker compose exec -T airflow-scheduler \
  python /opt/airflow/extract/extract_postgres_to_minio.py --run-date $FECHA --full-refresh
```
- Quita `--full-refresh` para extracción incremental de ese día.
- Verifica en MinIO (<http://localhost:9001>): bucket `staging` →
  `postgres/olist/orders/ingest_date=2024-01-01/orders_0000.csv` y
  `postgres/olist/_manifest/ingest_date=2024-01-01/manifest.json`.

**② Spark: CSV → Parquet particionado**
```bash
docker compose exec -T airflow-scheduler spark-submit \
  --master spark://spark-master:7077 \
  --packages org.apache.hadoop:hadoop-aws:3.3.4,com.amazonaws:aws-java-sdk-bundle:1.12.262 \
  /opt/airflow/spark/jobs/raw_to_parquet.py --ingest-date $FECHA --mode overwrite
```
- La primera ejecución tarda más: descarga los jars de S3A.
- Verifica: Spark UI <http://localhost:8083> y MinIO bucket `lake` →
  `raw/orders/order_year=2016/order_month=9/…parquet`.

**③ Registrar las particiones en el catálogo**
```bash
docker compose exec -T trino trino --server localhost:8080 --execute \
  "CALL hive.system.sync_partition_metadata('raw','orders','ADD')"
docker compose exec -T trino trino --server localhost:8080 --execute \
  "CALL hive.system.sync_partition_metadata('raw','order_items','ADD')"
docker compose exec -T trino trino --server localhost:8080 --execute \
  "SELECT count(*) FROM hive.raw.orders"
```
Debe devolver 18 000.

**④ dbt: dependencias, modelos, tests y documentación**
```bash
D="--project-dir /opt/airflow/dbt --profiles-dir /opt/airflow/dbt"
docker compose exec -T airflow-scheduler dbt deps $D     # 1º SIEMPRE: instala dbt_utils
docker compose exec -T airflow-scheduler dbt seed $D     # carga la tabla de traducción de categorías
docker compose exec -T airflow-scheduler dbt run  $D     # crea vistas y tablas
docker compose exec -T airflow-scheduler dbt test $D     # tests de calidad
docker compose exec -T airflow-scheduler dbt docs generate $D --static
```
- Si repites `dbt seed` a mano y falla con `HIVE_PATH_ALREADY_EXISTS`, es el problema de los
  ficheros huérfanos en S3 que resuelve la tarea `clean_seed_locations`. Borra a mano el prefijo
  `lake/staging/product_category_name_translation/` desde la consola de MinIO y reintenta.

**⑤ Consultar con Trino**
```bash
docker compose exec -T trino trino --server localhost:8080 --execute \
  "SELECT date_format(order_month_start,'%Y-%m') AS mes, orders, revenue
   FROM hive.lakehouse.agg_sales_monthly ORDER BY order_month_start"
```
Más consultas listas en [`docs/queries_trino.sql`](docs/queries_trino.sql).

---

## 6. Cómo saber que funcionó ✅

| # | Comprobación | Resultado esperado |
|---|---|---|
| 1 | `docker compose ps` | 10 servicios `Up (healthy)` + 3 init `Exited (0)` |
| 2 | MinIO → bucket `staging` | CSV + `manifest.json` bajo `ingest_date=<fecha>/` |
| 3 | MinIO → bucket `lake` | `raw/orders/order_year=…/order_month=…/*.parquet` |
| 4 | `SELECT count(*) FROM hive.raw.orders` | 18 000 |
| 5 | `SHOW TABLES IN hive.lakehouse` | `fct_orders`, `dim_customers`, `dim_products`, `agg_sales_monthly`, `agg_category_monthly`, `customer_retention_cohorts` |
| 6 | Cuadratura origen vs lakehouse | `filas_postgres = filas_lakehouse` |
| 7 | `dbt test` | `PASS=…` y `Done.` sin `FAIL` |
| 8 | <http://localhost:8080> | Documentación dbt con el grafo de linaje |
| 9 | Airflow → *Graph view* | 10 tareas en verde |

Cuadratura (Trino consulta los dos orígenes a la vez):
```sql
SELECT (SELECT count(*) FROM postgresql.public.orders)  AS filas_postgres,
       (SELECT count(*) FROM hive.lakehouse.fct_orders) AS filas_lakehouse;
```

Particiones registradas en el catálogo (Trino **no** tiene `information_schema.partitions`;
se consulta la tabla de sistema `$partitions` de cada tabla):
```sql
SELECT count(*) AS particiones_orders      FROM hive.raw."orders$partitions";
SELECT count(*) AS particiones_order_items FROM hive.raw."order_items$partitions";
```

---

## 7. Estructura del repositorio

```
RetailLakehouse-ELT/
├── docker-compose.yml              # 14 servicios (10 permanentes + 3 init + 1 herramienta)
├── Makefile                        # atajos: up / seed / trigger / dbt-* / trino-cli
├── .env.example                    # credenciales y puertos (copiar a .env)
├── .gitattributes                  # normaliza finales de línea a LF
├── LICENSE                         # MIT
├── docker/airflow/
│   ├── Dockerfile                  # Airflow 2.9.3 + Java 17 + PySpark + dbt-trino
│   └── requirements.txt            # versiones pinneadas (Airflow 2.x, sqlalchemy 1.4)
├── config/
│   ├── hive/
│   │   ├── hive-site.xml           # metastore → PostgreSQL; mapeo s3:// → S3A
│   │   └── lib/                    # driver JDBC (NO versionado: se descarga, ver 5-A)
│   ├── spark/spark-defaults.conf   # S3A (MinIO) + Snappy + dynamic partition overwrite
│   └── trino/…                     # config + catálogos hive y postgresql
├── scripts/
│   ├── generate_sample_data.py     # dataset sintético determinista (origen de los datos)
│   ├── seed_postgres.py            # crea el OLTP y carga los CSV
│   ├── init_trino_schemas.sql      # esquemas + tablas externas sobre el Parquet
│   └── init_meta_databases.sql     # crea la BD `airflow` en el Postgres de metadata
├── extract/extract_postgres_to_minio.py   # E: SQLAlchemy → CSV en MinIO
├── spark/jobs/raw_to_parquet.py           # L: CSV → Parquet Snappy particionado
├── dbt/                            # modelos staging/intermediate/marts + tests + seeds
├── dags/dag_retail_lakehouse_elt.py       # orquestador (10 tareas)
├── tests/
│   ├── test_extract.py             # lógica pura de la extracción (sin Docker)
│   └── test_dbt_models.py          # validación estática del proyecto dbt (sin Docker)
├── .github/workflows/ci.yml        # CI: pytest + dbt parse + YAML + compileall
├── data/raw/                       # CSV de origen (generados, gitignoreados)
└── docs/arquitectura.md, queries_trino.sql, video_script.md
```

---

## 8. Troubleshooting

Problemas que ya aparecieron al ejecutar el proyecto de verdad (y cómo se resolvieron):

| Síntoma | Causa | Solución |
|---|---|---|
| `error during connect: … npipe … dockerDesktopLinuxEngine` | Docker Desktop cerrado | Ábrelo y espera a que diga *Running* |
| `failed to resolve reference "minio/minio:RELEASE.2024-…": not found` | MinIO purga los tags antiguos de Docker Hub | Ya está fijado a `RELEASE.2025-04-22…` / `RELEASE.2025-04-08…`; si desaparecen, cámbialos por otro de <https://hub.docker.com/r/minio/minio/tags> |
| Hive Metastore: `/bin/bash: curl: command not found` | La imagen `apache/hive` no trae `curl` | Ya no se descarga nada dentro: el driver se monta desde `config/hive/lib/` |
| Hive: `The authentication type 10 is not supported` | El driver JDBC de la imagen (9.4.1208) no soporta SCRAM-SHA-256 (Postgres 15) | El contenedor borra ese jar y usa el 42.7.3 montado |
| Hive: `ClassNotFoundException: org.apache.hadoop.fs.s3a.S3AFileSystem` | La imagen no trae los jars de S3A en el classpath de Hive | El `command` los copia desde `/opt/hadoop/share/hadoop/tools/lib/` |
| Trino: `Defunct property 'query.max-total-memory-per-node'` | Propiedades obsoletas en Trino 442 | Ya corregidas en `config/trino/config.properties` |
| `docker compose run seed-postgres` termina con código 0 **pero no carga nada** | El `command` sin comillas se parte en argumentos y `bash -c` sólo recibe `python` (abre el REPL y sale) | Ya está entre comillas; usa siempre `docker compose --profile tools run --rm seed-postgres` |
| Airflow: `airflow: command not found` o CLI roto | `pip` subió a Airflow 3.x (el provider Spark ≥4.9 lo exige) | `requirements.txt` fija `apache-airflow==2.9.3` y `sqlalchemy<2.0` |
| Spark: `Could not parse Master URL` | El hook construye `--master` como `host:port`; un `spark://host:7077` plano pierde el esquema | `AIRFLOW_CONN_SPARK_DEFAULT` va en JSON con `host: spark://spark-master` |
| `dbt seed` → `HIVE_PATH_ALREADY_EXISTS` | `DROP TABLE` deja los Parquet en S3 | Lo resuelve la tarea `clean_seed_locations`; a mano, vacía el prefijo en MinIO |
| `dbt run` → `dbt_utils` no encontrado | Faltó `dbt deps` | Ejecuta `dbt deps` antes de `seed`/`run` |
| `dbt run` no encuentra `hive.lakehouse` | `trino-init` no terminó | `docker compose logs trino-init` y `docker compose up -d trino-init` |
| Spark: `Failed to connect to master` | master inaccesible desde el driver | `docker compose ps` → `rl-spark-master` debe estar `Up` |
| Trino no ve particiones nuevas | falta sincronizar | `CALL hive.system.sync_partition_metadata('raw','orders','ADD')` |
| Airflow no lista el DAG | error de importación | `docker compose exec -T airflow-scheduler airflow dags list-import-errors` |
| Puerto 5432 ocupado | Postgres local | `PG_HOST_PORT=5433` en `.env` y `docker compose up -d` |
| El equipo va muy lento | 10 contenedores | Ver *Ajustes de memoria* en la sección 4 |

**Empezar de cero:** `docker compose down -v` (borra también los datos de MinIO y Postgres)
y repite la sección 5-A.

---

## 9. Para el portafolio

**Pitch de 30 s para una entrevista:**
> *"Migramos el OLTP de ventas a un lakehouse abierto. Airflow orquesta diez tareas: extracción
> incremental con SQLAlchemy que deja CSV inmutables en un bucket de staging; un job de PySpark que
> los convierte a Parquet Snappy particionado por año/mes y deduplicado; la sincronización del
> catálogo; y dbt, que construye staging → intermediate → marts sobre Trino. El Hive Metastore es la
> única fuente de verdad del catálogo y Trino sincroniza las particiones tras cada carga. La calidad
> se asegura con cerca de 50 tests de dbt —incluida una cuadratura automática origen vs lakehouse— y
> la documentación se publica en cada ejecución."*

**Equivalencias cloud (muy preguntadas):** MinIO↔S3 · Hive Metastore↔Glue Data Catalog ·
Spark↔EMR/Glue Jobs · Trino↔Athena · Airflow↔MWAA.

**Roadmap:** Apache Iceberg (time travel / MERGE) · Great Expectations en staging · modelos
incrementales diarios · Superset/Metabase sobre Trino · Terraform a AWS.

El guion del **video de 3 minutos** está en [`docs/video_script.md`](docs/video_script.md).

---

**Licencia:** MIT · **Datos:** sintéticos deterministas (o Olist real si lo descargas de Kaggle).
