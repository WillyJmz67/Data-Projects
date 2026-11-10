# 📊 Sistema de Predicción de Demanda Retail

### Pipeline ETL + Machine Learning + SQL + Dashboard Interactivo

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python)
![Pandas](https://img.shields.io/badge/Pandas-3.x-150458?style=flat-square&logo=pandas)
![Scikit--learn](https://img.shields.io/badge/Scikit--learn-1.9-F7931E?style=flat-square&logo=scikitlearn)
![XGBoost](https://img.shields.io/badge/XGBoost-3.x-EC5426?style=flat-square)
![SQLite](https://img.shields.io/badge/SQLite-DB-003B57?style=flat-square&logo=sqlite)
![Streamlit](https://img.shields.io/badge/Streamlit-App-FF4B4B?style=flat-square&logo=streamlit)
![Plotly](https://img.shields.io/badge/Plotly-Viz-3F4F75?style=flat-square&logo=plotly)
![Status](https://img.shields.io/badge/Estado-Funcional-brightgreen?style=flat-square)

> **📌 Para reclutadores:** este repositorio demuestra un flujo completo de trabajo de un Científico/Ingeniero de Datos: ingesta → calidad de datos → EDA → feature engineering → modelado → persistencia SQL → visualización → consumo del modelo (dashboard, batch y API).

> **⚠️ Antes de publicar:** sustituye el enlace de demo y los datos de contacto de la sección [Sobre el autor](#-sobre-el-autor).

---

## 🎯 Resumen Ejecutivo (lectura de 2 minutos)

Una cadena de **1,115 tiendas** pierde dinero por dos razones: quedarse sin stock (ventas perdidas) o tener exceso de inventario (costos de almacenamiento). Este proyecto construye un **sistema de predicción de demanda diaria** que procesa **1,017,209 registros** de ventas históricas y genera pronósticos consumibles mediante dashboard, script batch o API REST.

**Resultados destacados:**

| Hito | Resultado |
|---|---|
| Datos crudos | 1,017,209 registros × 18 columnas (join de `train.csv` + `store.csv`) |
| Dataset procesado | 983,759 filas × 46 columnas · **1,115 tiendas** |
| Features del modelo | 34 (temporales, lags, rolling windows, one-hot de tienda) |
| Calidad de datos | 6 columnas con nulos diagnosticadas y tratadas (hasta 49.94%) |
| Modelo | Random Forest vs XGBoost con split temporal (sin data leakage) |
| Error del modelo | **MAPE 10.19%** · MAE 594 € · R² 0.941 |
| Persistencia | SQLite con 3 tablas y 5 consultas de negocio |
| Entrega | Dashboard Streamlit (4 vistas) + script batch + API REST |

---

## 💼 Contexto de Negocio

**Problema:** la planificación de inventario manual genera dos costos ocultos:

1. **Stockouts:** días sin producto disponible → ventas perdidas y clientes insatisfechos.
2. **Overstock:** capital inmovilizado y costos de almacenamiento.

**Solución:** predecir la demanda diaria por tienda con Machine Learning, para que el equipo de logística compre *exactamente* lo que necesita.

**Impacto esperado:** reducción de costos de almacenamiento y aumento de ventas por disponibilidad de producto.

---

## 🏗️ Arquitectura del Pipeline

```
┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ 1. INGESTA   │──▶│ 2. EDA       │──▶│ 3. FEATURES  │──▶│ 4. MODELO ML │
│ train+store  │   │ calidad+viz  │   │ 46 columnas  │   │ RF vs XGBoost│
└──────────────┘   └──────────────┘   └──────────────┘   └──────┬───────┘
                                                               ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ 7. DASHBOARD │◀──│ 6. CONSULTAS │◀──│ 5. PERSIST.  │◀──│ Predicciones │
│ Streamlit    │   │ SQL insights │   │ SQLite       │   │ + métricas   │
└──────────────┘   └──────────────┘   └──────────────┘   └──────────────┘
```

**Flujo de datos:** CSV (fuentes) → Parquet (capa procesada) → SQLite (capa de consumo) → Streamlit/API (capa de presentación). Esta separación por capas simula una arquitectura Data Lake real.

---

## 🛠️ Stack Tecnológico (100% herramientas gratuitas)

| Categoría | Herramienta | Por qué |
|---|---|---|
| Lenguaje | Python 3.11 | Estándar de la industria de datos |
| Manipulación | Pandas, NumPy, PyArrow | ETL y procesamiento vectorizado |
| Visualización | Matplotlib, Seaborn, Plotly | EDA estático + dashboards interactivos |
| Machine Learning | Scikit-learn, XGBoost | Modelos de regresión de alto rendimiento |
| Persistencia del modelo | Joblib (comprimido) | Un `.pkl` de pickle puro pesa 105 MB y GitHub rechaza >100 MB |
| Base de datos | SQLite | SQL relacional sin costo de servidor |
| Dashboard | Streamlit | Prototipos web sin HTML/CSS/JS |
| API | FastAPI + Uvicorn | Microservicio de predicciones con validación |
| Formato | Parquet | Estándar empresarial (Spark, Glue, Athena) |
| Versionado | Git + GitHub | Control de versiones profesional |

---

## 📁 Estructura del Proyecto

```
Pred_DemandaRetail/
├── data/                              # Datos crudos (descargar de Kaggle, no se versionan)
│   ├── train.csv                      # 1,017,209 registros de ventas
│   └── store.csv                      # Metadatos de 1,115 tiendas
├── src/
│   ├── utils.py                       # Helpers compartidos (features, carga de modelo, predicción)
│   ├── eda.py                         # Paso 3: Análisis exploratorio
│   ├── features.py                    # Paso 4: Feature engineering
│   ├── model.py                       # Paso 5: Modelado y evaluación
│   ├── sql.py                         # Paso 6: Persistencia y consultas SQL
│   ├── app.py                         # Paso 7: Dashboard Streamlit
│   ├── predict.py                     # Uso batch del modelo (próximos N días)
│   └── api.py                         # API REST FastAPI (microservicio)
├── output/                            # Artefactos generados (regenerables, no se versionan)
│   ├── dataset_procesado.parquet
│   ├── 01_tendencia_temporal.png … 06_evaluacion_modelo.png
│   ├── hallazgos_eda.txt · resumen_features.txt · resumen_sql.txt
│   ├── metricas_modelo.txt
│   └── prediccion_tienda_<id>.csv
├── models/
│   └── random_forest_model.joblib     # Modelo ganador (comprimido)
├── db/
│   └── demanda.db                     # SQLite con 3 tablas
├── requirements.txt
├── .gitignore
└── README.md
```

> **`src/utils.py`** centraliza la lista de features, la carga del modelo y la construcción
> de features para una fecha futura. Antes esa lógica estaba duplicada en 5 ficheros: bastaba
> tocar uno para que entrenamiento y producción dejaran de coincidir.

---

## 📊 Hallazgos Clave del EDA

### Análisis temporal (insight de negocio)

| Día | Venta promedio (€) | Interpretación |
|---|---|---|
| Lunes | 7,809 | 🔥 Pico post fin de semana |
| Martes | 7,005 | |
| Miércoles | 6,556 | |
| Jueves | 6,248 | |
| Viernes | 6,723 | |
| Sábado | 5,848 | |
| Domingo | 204 | 🧊 La mayoría de tiendas cerradas (≈0) |

> **Insight:** el día de la semana es el predictor más fuerte del negocio: los lunes venden
> **38× más** que los domingos. Cualquier modelo que ignore esta estacionalidad fallará.
>
> **Matiz importante:** no todas las tiendas cierran el domingo. La tienda 262, por ejemplo,
> abre los 7 días y su mejor día es el domingo (€28,601 de media). El modelo aprende ese
> patrón por tienda en lugar de asumir una regla global.

### Estadísticas de ventas (datos crudos)

| Métrica | Valor |
|---|---|
| Media | €5,774 |
| Mediana | €5,744 |
| Desviación estándar | €3,850 |
| Máximo diario | €41,551 |
| Días con ventas = 0 | 172,871 (17.0%) |

### Calidad de datos diagnosticada

| Columna | % Nulos | Tratamiento |
|---|---|---|
| `Promo2SinceWeek` / `Promo2SinceYear` / `PromoInterval` | 49.94% | Sólo existen si `Promo2=1` → `PromoInterval` se normaliza a `''` |
| `CompetitionOpenSinceMonth` / `CompetitionOpenSinceYear` | 31.79% | Se calculó antigüedad de competencia con `fillna(0)` |
| `CompetitionDistance` | 0.26% | Imputación con la mediana |
| Duplicados | 0 | ✅ Sin acción requerida |

> ⚠️ **Trampa crítica:** las 544 tiendas sin `Promo2` tienen `PromoInterval` nulo. Un
> `df.dropna()` sin `subset` las borra **enteras**. Ver la sección de desafíos técnicos.

---

## 🔧 Feature Engineering (46 columnas, 34 features de modelo)

| Familia | Features | Justificación de negocio |
|---|---|---|
| **Temporales** (13) | Year, Month, Day, DayOfWeek, WeekOfYear, DayOfYear, Quarter, IsWeekend, IsMonthStart/End, IsOpen | Capturan estacionalidad semanal y anual |
| **Tienda** (9) | One-hot de `StoreType` (4) y `Assortment` (3), CompetitionDistance, CompetitionOpen, Promo2 | Diferencian el comportamiento de cada punto de venta |
| **Lags** (5) | Sales_Lag_7/14/21/30, Customers_Lag_7 | Capturan la *inercia* de la demanda |
| **Rolling windows** (7) | Sales_RollingMean/Std_7/14/30, Customers_RollingMean_7 | Suavizan volatilidad y capturan tendencia reciente |

> **Nota técnica:** los lags se calcularon **por tienda** (`groupby('Store')`) con `shift()` para
> evitar data leakage entre tiendas. Las ventanas móviles se desplazan 7 días
> (`shift(7).rolling(w)`), de modo que en el día *t* el modelo sólo ve información hasta *t−7*.
> El dataset queda en **983,759 filas** (se descartan 33,450 filas iniciales de cada tienda, que
> no tienen historia suficiente para calcular `Sales_Lag_30`).

---

## 🤖 Modelado y Evaluación

- **División temporal (time-based split):** 85% train / 15% test **por fecha**, *nunca* aleatoria.
  En series de tiempo, entrenar con datos futuros es trampa (leakage).
  - Train: 836,579 filas (hasta 2015-03-21)
  - Test: 147,180 filas (después de 2015-03-21)
- **Modelos comparados:** Random Forest (baseline) vs XGBoost (avanzado).

| Métrica | Random Forest | XGBoost | Significado para el negocio |
|---|---|---|---|
| MAE (€) | **593.91** | 618.80 | Error promedio en euros por tienda/día |
| RMSE (€) | 966.29 | **960.39** | Penaliza errores grandes (días críticos) |
| MAPE (%) | **10.19** | 10.60 | Precisión porcentual del pronóstico |
| R² | 0.9410 | **0.9417** | Varianza explicada |

**Modelo seleccionado: Random Forest** (mejor MAPE, que es la métrica que se traduce directamente
en euros de error de compra). XGBoost gana por muy poco en RMSE y R²; la diferencia es
despreciable y Random Forest es más barato de reentrenar.

> 💡 *Ejecuta `python src/model.py` para reproducir estas métricas. Quedan guardadas en
> `output/metricas_modelo.txt`.*

**Top 5 features más importantes:**

| Feature | Importancia | Lectura |
|---|---|---|
| `IsOpen` | 0.474 | Si la tienda está cerrada, no hay ventas: domina el modelo |
| `Sales_Lag_14` | 0.336 | La venta de hace dos semanas es el mejor predictor |
| `Sales_RollingMean_30` | 0.044 | Tendencia del último mes |
| `Promo` | 0.040 | Las promociones mueven la demanda |
| `Sales_Lag_21` | 0.017 | Inercia a tres semanas |

**Interpretación:** la demanda tiene **fuerte inercia temporal** y un componente de
**estacionalidad semanal** claro. Para predecir mañana lo más importante es saber si la tienda
abre, cuánto se vendió hace 7-30 días y si hay promoción.

---

## 🗄️ Integración SQL (SQLite)

En producción, las predicciones no viven en archivos Python: se persisten para que otros sistemas las consuman.

**Esquema de la base de datos (`db/demanda.db`, ~50 MB):**

| Tabla | Propósito |
|---|---|
| `historical_data` | Datos históricos procesados y consultables |
| `predictions` | Predicciones con error calculado (auditoría) |
| `model_metrics` | Métricas del modelo con fecha (gobernanza/MLOps) |

**Ejemplo de query de negocio (precisión por tienda):**

```sql
SELECT
    store_id,
    COUNT(*) AS predictions,
    ROUND(AVG(ABS(error)), 0) AS mae,
    ROUND(AVG(ABS(error) / NULLIF(actual_sales, 0)) * 100, 2) AS mape_pct
FROM predictions
GROUP BY store_id
ORDER BY mape_pct DESC
LIMIT 10;
```

---

## 📈 Dashboard Interactivo (Streamlit)

4 vistas para distintos stakeholders:

1. **📈 Análisis Temporal** – tendencia diaria, estacionalidad semanal, distribución de ventas.
2. **🏪 Análisis por Tienda** – filtros interactivos, top 10 tiendas, resumen operativo.
3. **🤖 Predicciones del Modelo** – predicho vs real, distribución de errores, precisión por tienda
   y **simulador de predicción en vivo** (ejecuta el modelo de verdad, no es un mock).
4. **🔍 Feature Importance** – qué variables mueven el modelo, con interpretación de negocio.

---

## 🔮 Uso del Modelo en Producción

### 1. Predicción batch (reporte para logística)

```bash
python src/predict.py                          # tienda de más ventas, 7 días
python src/predict.py --store 1088             # una tienda concreta
python src/predict.py --stores 262,1088        # varias tiendas
python src/predict.py --days 14                # otro horizonte
```

Genera `output/prediccion_tienda_<id>.csv` con el pronóstico y una recomendación de inventario
(+10% de margen de seguridad).

### 2. Dashboard interactivo

```bash
streamlit run src/app.py
```

### 3. API REST (microservicio)

```bash
python src/api.py
```

| Endpoint | Descripción |
|---|---|
| `GET /` | Estado del servicio, modelo cargado y fecha del último dato |
| `GET /stores` | Tiendas disponibles |
| `POST /predict` | `{"store_id": 1088, "date": "2015-08-05"}` → `predicted_sales` + `confidence` |

Documentación automática en `http://localhost:8000/docs`.

> **Nota:** la fecha debe ser **posterior** al último día con datos (2015-07-31) y no más de
> 30 días vista. La API construye las features temporales y de inercia para esa fecha concreta,
> así que dos fechas distintas devuelven predicciones distintas.

---

## 🚧 Desafíos Técnicos y Soluciones

Problemas **reales** encontrados y corregidos, documentados como evidencia de madurez técnica.

### 1. Un `dropna()` que borraba 750 de las 1,115 tiendas

- **Síntoma:** el dataset procesado tenía 313,376 filas y sólo **365 tiendas**. El modelo
  entrenaba con un tercio del negocio y las métricas parecían buenas.
- **Causa raíz:** `df.dropna()` sin `subset` descarta la fila si **cualquier** columna es nula.
  `PromoInterval` es nulo en las 544 tiendas sin `Promo2` y `CompetitionOpenSinceYear` lo es en
  206 más → esas tiendas desaparecían por completo. Ninguna de esas columnas entra al modelo.
- **Solución:** `dropna(subset=[columnas de lags])`, y el script ahora reporta cuántas tiendas
  sobreviven: **1,115 → 1,115** (sólo se pierden 33,450 filas de calentamiento).
- **Competencia demostrada:** control de calidad de datos y detección de fallos silenciosos.

### 2. One-hot que el modelo nunca veía

- **Síntoma:** el modelo usaba 27 features aunque el dataset tenía 46 columnas.
- **Causa raíz:** pandas 2+ crea las columnas de `get_dummies` con dtype **`bool`**, y
  `select_dtypes(include=[np.number])` **no** incluye `bool`. `StoreType` y `Assortment`
  se descartaban en silencio.
- **Solución:** `get_dummies(..., dtype=np.int8)` + selección de features que incluye `bool`.
  El modelo pasó de 27 a **34 features**.

### 3. Train/serve skew en las ventanas móviles

- **Síntoma:** las predicciones de producción no cuadraban con el error de validación.
- **Causa raíz:** en entrenamiento la ventana se calculaba con `shift(7).rolling(w)`, pero el
  script de predicción usaba los últimos `w` días *pegados al presente*. El modelo recibía
  features distintas a las del entrenamiento.
- **Solución:** `utils._shifted_window()` reproduce exactamente la misma ventana que el
  entrenamiento. Entrenamiento y producción comparten ahora una única implementación.

### 4. Gráfico de ventas mensual que rompía el EDA

- **Síntoma:** `ValueError: The number of FixedLocator locations (3) ... does not match the
  number of labels (12)`. El script moría en el gráfico 03 y nunca generaba el 04, el 05 ni el
  informe de hallazgos.
- **Causa raíz:** `groupby(['Year','Month']).mean().unstack()` deja los **meses como columnas**
  (12) y los **años como filas** (3). El gráfico tenía 3 ticks y se le pedían 12 etiquetas.
- **Solución:** `unstack(level='Year')` para poner los meses en el índice, y los ticks se fijan
  desde la longitud real del eje en vez de desde una constante.

### 5. Modelo de 105 MB que GitHub rechaza

- **Síntoma:** `random_forest_model.pkl` pesaba 105 MB. GitHub bloquea cualquier fichero de más
  de 100 MB.
- **Solución:** persistencia con `joblib.dump(..., compress=3)`. El modelo cabe holgadamente en
  el límite y el repositorio queda publicable.

### 6. Lógica de features duplicada en cinco ficheros

- **Síntoma:** `predict.py` usaba `feature_cols` antes de definirla (`NameError`), `api.py`
  ignoraba la fecha del request y devolvía siempre la misma predicción, y el dashboard tenía un
  "simulador" que sólo mostraba un mensaje de éxito.
- **Solución:** `src/utils.py` como única fuente de verdad (`select_feature_cols`,
  `load_latest_model`, `predict_for_date`). La API valida la fecha y predice de verdad, y el
  simulador del dashboard ejecuta el modelo.

---

## 🚀 Instalación y Ejecución

### Requisitos previos

- Python 3.10+
- Dataset de Kaggle: [Rossmann Store Sales](https://www.kaggle.com/competitions/rossmann-store-sales)
  → colocar `train.csv` y `store.csv` en `data/`

### Pasos

```bash
# 1. Clonar repositorio
git clone https://github.com/WillyJmz67/Pred_DemandaRetail.git
cd Pred_DemandaRetail

# 2. Crear y activar entorno virtual
python -m venv venv
venv\Scripts\activate           # Windows
# source venv/bin/activate      # Linux/macOS

# 3. Instalar dependencias (desde la RAÍZ del proyecto)
pip install -r requirements.txt

# 4. Ejecutar el pipeline en orden
python src/eda.py               # Análisis exploratorio + gráficos
python src/features.py          # Feature engineering (dataset_procesado.parquet)
python src/model.py             # Entrenamiento y evaluación (RF vs XGBoost)
python src/sql.py               # Persistencia SQLite + consultas de negocio

# 5. Levantar dashboard
streamlit run src/app.py

# 6. (Opcional) Predicción batch y API
python src/predict.py --stores 262,1088
python src/api.py
```

> El orden importa: cada paso consume la salida del anterior. `model.py` necesita
> `dataset_procesado.parquet` (lo genera `features.py`) y `sql.py` necesita el modelo.

### Tiempos orientativos (equipo de desarrollo, 1,115 tiendas)

| Paso | Duración |
|---|---|
| `eda.py` | ~1 min |
| `features.py` | ~3 min |
| `model.py` | ~4 min (Random Forest + XGBoost) |
| `sql.py` | ~1 min |

---

## 🗺️ Roadmap (próximos pasos)

- [ ] Despliegue del dashboard en Streamlit Community Cloud
- [ ] **Dockerfile + docker-compose** para ejecutar el pipeline sin depender del entorno local
- [ ] **Pruebas con `pytest`**: validación de calidad de datos y de contratos de features
- [ ] Automatización del pipeline con Apache Airflow (orquestación)
- [ ] Migración del almacenamiento a S3/MinIO (simulación Data Lake)
- [ ] Experimentación con Prophet/LightGBM para estacionalidad anual
- [ ] CI/CD con GitHub Actions
- [ ] Reentrenamiento periódico del modelo (MLOps)

---

## 🎓 Sobre el Autor

**William** — Ingeniero Mecatrónico en transición a Ciencia de Datos / Data Engineering.

Mi formación en mecatrónica me dio una ventaja concreta: entiendo los procesos físicos e
industriales detrás de los datos (sensores, operaciones, mantenimiento, cadena de suministro).
Este portafolio demuestra que combino esa visión de ingeniería con habilidades modernas de
datos: Python, SQL, ML, pipelines ETL y visualización.

📬 **Contacto:**

- GitHub: [WillyJmz67](https://github.com/WillyJmz67)
- LinkedIn: ⚠️ *[pendiente: añadir tu URL de LinkedIn]*
- Email: junior7472@hotmail.com

---

*Dataset: Rossmann Store Sales (Kaggle) · Proyecto de portafolio con fines educativos y de demostración.*
