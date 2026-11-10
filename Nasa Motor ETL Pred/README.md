# Pipeline ETL — Mantenimiento Predictivo de Motores

> Portafolio de Ingeniería de Datos | Transición Mecatrónico → Data Engineer

## 1. El problema (¿para qué?)

En entornos industriales los motores fallan sin aviso. El **mantenimiento correctivo**
(reparar cuando ya se rompió) cuesta entre 3 y 4 veces más que el **mantenimiento
predictivo** (reparar justo antes de fallar). Como Ingeniero Mecatrónico entiendo el
costo de paradas de línea y desgaste de equipo, por eso este proyecto usa datos de
sensores (vibración, temperatura, presión vía settings operacionales) para anticipar
fallas.

El objetivo del pipeline es dejar los datos listos para un modelo de Machine Learning
que prediga la **RUL** (*Remaining Useful Life*, ciclos restantes hasta la falla).

## 2. La solución (¿qué hice?)

Pipeline **batch ETL** que:

1. **Ingesta** — lee archivos crudos del dataset NASA Turbofan (CMAPSS).
2. **Transforma** — calcula la variable objetivo `rul` y una etiqueta binaria `label`
   (¿fallará en ≤ 30 ciclos?).
3. **Valida** — aplica controles de calidad de datos (nulos, RUL negativo, vacío).
4. **Orquesta** — programable diariamente con Apache Airflow.

## 3. Arquitectura

```
[NASA CMAPSS .txt]            (raw)
        │  ingest.py
        ▼
[data/processed/*.parquet]    (zona procesada)
        │  transform.py  (+ RUL / label)
        ▼
[data/curated/*.parquet]      (zona lista para ML / Athena)
        │  validate.py
        ▼
[Airflow DAG @daily]  ->  [Power BI / Jupyter / ML]
```

Versión cloud (opcional, nivel avanzado): S3 (raw) → AWS Glue Crawler → Glue Job
PySpark → S3 (Parquet) → AWS Glue Data Catalog → Amazon Athena → BI.

## 4. Stack técnico

| Categoría | Herramienta |
|---|---|
| Lenguaje | Python 3.11 |
| Procesamiento | Pandas, **PySpark** (versión escalable) |
| Formato | **CSV → Parquet** |
| Orquestación | **Apache Airflow** (Local Executor vía Docker) |
| Calidad | Controles en `validate.py` + `pytest` |
| Cloud (nice to have) | AWS S3, Glue, Athena, Glue DataBrew |
| Visualización | Power BI / Jupyter |

## 5. Estructura del repositorio

```
proyecto-etl-predictivo/
├── data/
│   ├── raw/          # .txt originales de NASA (+ sample_FD001_train.txt de ejemplo)
│   ├── processed/    # Parquet tras ingesta
│   └── curated/      # Parquet con RUL/label (+ all_scenarios y dashboard_data)
├── src/
│   ├── config.py     # rutas, columnas y FEATURES centralizadas
│   ├── ingest.py     # lectura cruda -> Parquet
│   ├── transform.py  # RUL + etiqueta (pandas y spark)
│   ├── validate.py   # controles de calidad
│   ├── main.py       # orquestador local
│   ├── train_model.py             # entrena y guarda los modelos (comprimidos)
│   ├── prepare_dashboard_data.py  # une los 4 escenarios para Power BI
│   ├── add_predictions.py         # añade rul_predicho (modelo) al dataset del dashboard
│   ├── warehouse.py               # carga a Data Warehouse (Postgres=Redshift) + cuadratura
│   └── glue_job.py                # TEMPLATE de AWS Glue Job (PySpark) para la nube
├── dags/
│   └── etl_pipeline.py  # DAG de Airflow
├── notebooks/
│   ├── 01_exploracion.ipynb   # EDA de datos curated
│   └── 02_modelo.ipynb        # Modelo ML (clasificación + regresión RUL)
├── docs/
│   └── dashboard_powerbi.md   # guía paso a paso del dashboard
├── models/                    # modelos entrenados (.joblib, comprimidos y versionados)
├── tests/
│   ├── conftest.py
│   ├── test_ingest.py
│   ├── test_transform.py
│   ├── test_validate.py
│   ├── test_prepare_dashboard.py
│   ├── test_add_predictions.py
│   └── test_warehouse.py
├── .gitignore
├── docker-compose.yml   # Airflow + Postgres warehouse (local)
├── requirements.txt
└── README.md
```

## 6. Cómo ejecutar (local, gratis)

```bash
# 1. Crear entorno virtual
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/Mac

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Ejecutar pipeline completo (ingesta -> transforma -> valida)
python -m src.main

# 4. Entrenar los modelos (ya vienen en models/; esto los regenera)
python -m src.train_model

# 5. (Opcional) Dataset con predicciones para Power BI
python -m src.prepare_dashboard_data
python -m src.add_predictions

# 6. Correr pruebas unitarias
pytest tests/
```

El proyecto incluye `data/raw/sample_FD001_train.txt` (datos de ejemplo) para que
corra sin descargar nada.

> **Nota:** `pyspark` sólo hace falta para la ruta escalable (`transform_spark`,
> `glue_job.py`). El pipeline local funciona sin instalarlo.

## 7. Cómo usar los datos reales de NASA

1. Descarga **CMAPSS** en:
   https://www.nasa.gov/intelligent-systems-division/
   (busca "Turbofan Engine Degradation Simulation Dataset").
2. Coloca los ficheros de cada escenario en `data/raw/` con su nombre original:
   `train_FD001.txt` … `train_FD004.txt`, `test_FD001.txt` … `test_FD004.txt` y
   `RUL_FD001.txt` … `RUL_FD004.txt` (estos últimos son el ground-truth del test).
3. Vuelve a ejecutar `python -m src.main`.

> Los ficheros de NASA separan las columnas con **un solo espacio** y cada línea
> termina en espacio. El nombre importa poco (la ingesta valida el **número de
> columnas**, 26), pero un `RUL_*.txt` (1 columna) se omite automáticamente.

## 8. Cómo levantar Airflow (opcional)

```bash
docker-compose up
```

Abre http://localhost:8080 (usuario/contraseña: `admin`/`admin`) y activa el DAG
`etl_mantenimiento_predictivo`.

## 9. Modelo de Machine Learning

Se entrenan dos modelos RandomForest sobre los datos `curated` (los 4 escenarios FD001-4):

- **Clasificación** de `label` (¿fallo en ≤30 ciclos?).
- **Regresión** de `rul` (ciclos restantes).

Detalle técnico clave: el split es **por motor** (anti-fuga temporal) y el RUL del test set
se **reconstruye** con `RUL_FD00X.txt` (porque en `test_*` el motor no llega a falla).

Dos formas de reproducirlo (dan las mismas cifras):

```bash
python -m src.train_model          # script reproducible (recomendado)
```

```bash
jupyter notebook notebooks/02_modelo.ipynb
# o ejecutar sin abrir: jupyter nbconvert --to notebook --execute --inplace notebooks/02_modelo.ipynb
```

Resultados obtenidos (RandomForest, 100 árboles, `random_state=42`):

| Métrica | Validación | Test (RUL real) |
|---|---|---|
| Accuracy (clasificación) | 0.963 | 0.986 |
| F1 clase `label=1` | 0.860 | 0.692 |
| RMSE RUL (regresión) | 49.70 ciclos | 62.28 ciclos |

Los modelos se guardan comprimidos en `models/` (`modelo_label.joblib`, `modelo_rul.joblib`) y
**sí se versionan**, para que quien clone el repo no tenga que entrenar.

> **Sobre el tamaño del modelo.** El regresor usa `min_samples_leaf=5`. Con 100 árboles sin
> límite de profundidad crecía hasta ~15 M de nodos (593 MB sin comprimir, **206 MB** ya
> comprimido: GitHub rechaza ficheros de más de 100 MB) y además sobreajustaba. Con
> `min_samples_leaf=5` baja a ~2.6 M de nodos (**54 MB** comprimido) y el RMSE de test
> **mejora** (62.28 vs 62.36): el ruido de los sensores se promedia en hojas más grandes.

## 10. Dashboard en Power BI

Guía paso a paso en [`docs/dashboard_powerbi.md`](docs/dashboard_powerbi.md). Requiere
**Power BI Desktop** (gratis). El dataset unificado con predicciones del modelo:

```
data/curated/dashboard_data.parquet   # train+test FD001-4 + rul, rul_predicho, conjunto
```

Generado por `src/add_predictions.py` (carga `models/modelo_rul.joblib` y predice
`rul_predicho`). Incluye medidas DAX (Motores_Total, RUL_Promedio, %_Ciclos_Riesgo,
Motores_Riesgo, RMSE_RUL) y visuales KPI, degradación por motor, riesgo por escenario,
tabla "top motores en riesgo" y panel **Real vs Predicho** (scatter + RMSE).

## 11. Próximos pasos sugeridos

- [ ] Subir a AWS Glue (Job PySpark) y consultar con Athena.
- [ ] Pruebas de calidad con `dbt` (nice to have de reclutadores).
- [ ] Servir el modelo en un job batch orquestado por Airflow.

## 12. Orquestación y Data Warehouse (Proyecto 2)

Pipeline completo **orquestado con Airflow** que además carga los datos a un **Data Warehouse**
(Postgres local como sustituto de Redshift, $0). Cubre lo que piden las vacantes: Airflow/MWAA,
Redshift, SQL, ETL batch, calidad y cuadratura.

### Arquitectura
```
[S3 raw .txt] -> [ingest] -> [Parquet] -> [transform + RUL] -> [validate]
                                                        |
                              Airflow DAG (@daily) -----+--> [warehouse: dim_motor + fact_lecturas]
                                                        |        -> [cuadratura SQL]
                                                        v
                                                  [Power BI] / [ML]
```
En la nube, el `ingest/transform` sería un **AWS Glue Job PySpark** (ver `src/glue_job.py`)
leyendo/escribiendo desde S3, y el warehouse real sería **Amazon Redshift**.

### Cómo levantarlo (local, gratis)
```bash
docker-compose up          # Airflow :8080  +  Postgres warehouse :5433
```
Abre http://localhost:8080 (admin/admin) y activa el DAG `etl_mantenimiento_predictivo`.
El DAG encadena: `ingest >> transform >> validate >> create_tables >> load_warehouse >> cuadratura`.

### Componentes
- **`dags/etl_pipeline.py`** — DAG con las 6 tareas anteriores.
- **`src/warehouse.py`** — `run_ddl` (modelo estrella), `load` (COPY desde CSV), `cuadratura`
  (reconcilia `#filas` warehouse vs Parquet y lanza error si no cuadran).
- **`src/glue_job.py`** — template de Glue Job (PySpark) listo para AWS.
- **`docker-compose.yml`** — Airflow (webserver+scheduler) + Postgres `warehouse` + volúmenes
  montados (`./src`, `./dags`, `./data`, `./requirements.txt`).

### Migrar a Redshift real
1. Cambiar las variables `WAREHOUSE_*` a tu endpoint de Redshift (mismo SQL, mismo DDL).
2. En `load()`, sustituir el `COPY ... FROM STDIN` por
   `COPY fact_lecturas FROM 's3://<bucket>/curated/dashboard_data.csv' IAM_ROLE '...' CSV`.
3. El DAG y la cuadratura quedan iguales.

### Pruebas
`tests/test_warehouse.py` valida el DDL, las columnas de la tabla de hechos y la lógica de
cuadratura (sin necesidad de levantar Postgres). Para la prueba en vivo: `docker-compose up`.

---

## 13. Desafíos técnicos (bugs reales encontrados y arreglados)

Lo que sigue no es teoría: son fallos que aparecieron al **ejecutar** el pipeline y comparar
la salida con lo que el README afirmaba.

| # | Síntoma | Causa raíz | Arreglo |
|---|---|---|---|
| 1 | `pytest` fallaba con `FileNotFoundError: .../data/raw/RUL_FD001.txt` | El test creaba `curated/` con `mkdir` pero no `data/raw/` | `raw.mkdir(parents=True, exist_ok=True)` en `test_add_predictions.py` |
| 2 | `models/modelo_rul.joblib` pesaba **593 MB** (GitHub rechaza >100 MB) | `joblib.dump()` sin comprimir, 100 árboles sin límite de profundidad (~15 M nodos) | `compress=3` + `min_samples_leaf=5` → 206 MB a **54 MB** (y mejor RMSE) |
| 3 | El modelo guardado daba RMSE test **62.52** y el código del notebook **62.36** | El `.joblib` versionado venía de una ejecución antigua y no era reproducible | `src/train_model.py` regenera los modelos y **reproduce la tabla de métricas** |
| 4 | `F.window("id")` en la ruta PySpark | `F.window()` es para ventanas **temporales** (exige columna timestamp + duración), no para particionar | `Window.partitionBy("id")` en `transform_spark` y `glue_job.py` |
| 5 | `curated/test_*.parquet` traía una `rul` que parecía válida y no lo era | En `test_*` el motor **no** llega a falla, así que `max_cycle - cycle` no es la RUL | Aviso explícito en `transform_pandas`; la RUL real se reconstruye con `RUL_FD00X.txt` |
| 6 | El template de Glue podía fallar al leer el `.txt` | Los ficheros de NASA terminan en espacio → el split por `" "` genera columnas vacías | `read_cmapss()` toma las 26 primeras columnas por posición y castea a int/double |
| 7 | El dashboard "no cuadraba" con la guía | La guía decía 28 columnas (hay 32) y las medidas DAX usaban una tabla `all_scenarios` inexistente | Conteo corregido y DAX apuntando a la tabla real `dashboard_data` |
| 8 | Riesgo de subir el repo con `venv/` (11k ficheros) y los datos intermedios | No existía `.gitignore` | `.gitignore` con `venv/`, `__pycache__/`, `.pytest_cache/`, `data/processed|curated/`, `data/raw/*.txt` (salvo la muestra) |
| 9 | `python -m src.ingest` terminaba con **exit 1** | Su bloque `__main__` no capturaba el `ValueError` de los `RUL_*.txt`, a diferencia de `src/main.py` | `try/except ValueError` con `[omitido]`, igual que el orquestador |

**Verificado ejecutando:** `python -m src.main` (13 ficheros `.txt`: 9 de lecturas → 265 263 filas,
y los 4 `RUL_*.txt` omitidos por tener 1 columna), `python -m src.train_model` (métricas de la §9),
`python -m src.prepare_dashboard_data` (160 359 filas) y `pytest tests/` → **14/14 en verde**.

**No verificado en local:** las rutas PySpark/Glue (`pyspark` no está instalado y Java 25 no
es compatible con Spark 3.5) y el DAG de Airflow con Postgres (requiere el daemon de Docker
en marcha). El `docker compose config` sí se validó.


