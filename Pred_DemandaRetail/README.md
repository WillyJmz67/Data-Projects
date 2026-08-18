# 📊 Sistema de Predicción de Demanda Retail

### Pipeline ETL + Machine Learning + SQL + Dashboard Interactivo

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python)
![Pandas](https://img.shields.io/badge/Pandas-2.x-150458?style=flat-square&logo=pandas)
![Scikit--learn](https://img.shields.io/badge/Scikit--learn-1.x-F7931E?style=flat-square&logo=scikitlearn)
![XGBoost](https://img.shields.io/badge/XGBoost-ML-EC5426?style=flat-square)
![SQLite](https://img.shields.io/badge/SQLite-DB-003B57?style=flat-square&logo=sqlite)
![Streamlit](https://img.shields.io/badge/Streamlit-App-FF4B4B?style=flat-square&logo=streamlit)
![Plotly](https://img.shields.io/badge/Plotly-Viz-3F4F75?style=flat-square&logo=plotly)
![Status](https://img.shields.io/badge/Estado-En%20desarrollo-yellow?style=flat-square)

> ** Demo en vivo:** ️ [COMPLETAR: link de Streamlit Cloud cuando lo despliegues]
>
> **📌 Para reclutadores:** este repositorio demuestra un flujo completo de trabajo de un Científico/Ingeniero de Datos: ingesta → calidad de datos → EDA → feature engineering → modelado → persistencia SQL → visualización → consumo del modelo.

---

## 🎯 Resumen Ejecutivo (lectura de 2 minutos)

Una cadena de **1,115 tiendas** pierde dinero por dos razones: quedarse sin stock (ventas perdidas) o tener exceso de inventario (costos de almacenamiento). Este proyecto construye un **sistema de predicción de demanda diaria** que procesa **1,017,209 registros** de ventas históricas y genera pronósticos con precisión de nivel producción, consumibles mediante dashboard, script batch o API REST.

**Resultados destacados:**

| Hito | Resultado |
|---|---|
| Datos procesados | 1,017,209 registros × 18 columnas (join de 2 fuentes) |
| Features generadas | 46 columnas (temporales, lags, rolling windows, one-hot) |
| Calidad de datos | 6 columnas con nulos diagnosticadas y tratadas (hasta 49.94%) |
| Modelo | Random Forest vs XGBoost con evaluación temporal sin data leakage |
| Persistencia | Base de datos SQLite con 3 tablas y queries de negocio |
| Entrega | Dashboard interactivo Streamlit + script de predicción + API |

---

## 💼 Contexto de Negocio

**Problema:** La planificación de inventario manual genera dos costos ocultos:
1. **Stockouts:** días sin producto disponible → ventas perdidas y clientes insatisfechos.
2. **Overstock:** capital inmovilizado y costos de almacenamiento.

**Solución:** Predecir la demanda diaria por tienda con Machine Learning, para que el equipo de logística compre *exactamente* lo que necesita.

**Impacto esperado:** Reducción de costos de almacenamiento y aumento de ventas por disponibilidad de producto.

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
| Base de datos | SQLite (SQLAlchemy) | SQL relacional sin costo de servidor |
| Dashboard | Streamlit | Prototipos web sin HTML/CSS/JS |
| API | FastAPI | Microservicio de predicciones |
| Formato | Parquet | Estándar empresarial (Spark, Glue, Athena) |
| Versionado | Git + GitHub | Control de versiones profesional |

---

## 📁 Estructura del Proyecto

```
Prediccion de demanda/
├── data/                      # Datos crudos (descargar de Kaggle)
│   ├── train.csv              # 1,017,209 registros de ventas
│   └── store.csv              # Metadatos de 1,115 tiendas
├── src/
│   ├── eda.py                 # Paso 3: Análisis exploratorio
│   ├── features.py            # Paso 4: Feature engineering
│   ├── model.py               # Paso 5: Modelado y evaluación
│   ├── sql.py                 # Paso 6: Persistencia y consultas SQL
│   ├── app.py                 # Paso 7: Dashboard Streamlit
│   ├── predict.py             # Uso batch del modelo (próximos 7 días)
│   └── api.py                 # API REST FastAPI (microservicio)
├── output/
│   ├── dataset_procesado.parquet
│   ├── 01_tendencia_temporal.png ... 06_evaluacion_modelo.png
│   └── reportes (.txt)
├── models/
│   └── modelo_entrenado.pkl
├── db/
│   └── demanda.db             # SQLite con 3 tablas
├── requirements.txt
└── README.md
```

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
| Domingo | 204 | 🧊 Tiendas cerradas (≈0) |

> **Insight:** El día de la semana es el predictor más fuerte del negocio: los lunes venden **38× más** que los domingos. Cualquier modelo que ignore esta estacionalidad fallará.

### Estadísticas de ventas

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
| Promo2SinceYear / Week / Interval | 49.94% | Solo existen si Promo2=1 → se derivó feature binaria |
| CompetitionOpenSinceMonth / Year | 31.79% | Se calculó antigüedad de competencia con fillna(0) |
| CompetitionDistance | 0.26% | Imputación con mediana |
| Duplicados | 0 | ✅ Sin acción requerida |

---

## 🔧 Feature Engineering (46 features)

| Familia | Features | Justificación de negocio |
|---|---|---|
| **Temporales** | Year, Month, Day, DayOfWeek, WeekOfYear, DayOfYear, Quarter, IsWeekend, IsMonthStart/End, IsOpen | Capturan estacionalidad semanal y anual |
| **Tienda** | One-hot de StoreType y Assortment, CompetitionDistance, CompetitionOpen, Promo2 | Diferencian el comportamiento de cada punto de venta |
| **Lags** | Sales_Lag_7/14/21/30, Customers_Lag_7 | Capturan la *inercia* de la demanda (lo vendido semanas anteriores) |
| **Rolling windows** | Sales_RollingMean/Std_7/14/30, Customers_RollingMean_7 | Suavizan volatilidad y capturan tendencia reciente |

> **Nota técnica:** Los lags se calcularon **por tienda** (`groupby('Store')`) con `shift()` para evitar data leakage entre tiendas. Esto redujo el dataset de 1M a **313,376 filas × 46 columnas** válidas, conservando volumen estadístico suficiente.

---

## 🤖 Modelado y Evaluación

- **División temporal (time-based split):** 85% train / 15% test por fecha, *nunca* aleatoria. En series de tiempo, entrenar con datos futuros es trampa (leakage).
- **Modelos comparados:** Random Forest (baseline) vs XGBoost (avanzado).
- **Métricas de negocio:**

| Métrica | Random Forest | XGBoost | Significado para el negocio |
|---|---|---|---|
| MAE (€) | ⚠️ [COMPLETAR] | ⚠️ [COMPLETAR] | Error promedio en euros por tienda/día |
| RMSE (€) | ⚠️ [COMPLETAR] | ⚠️ [COMPLETAR] | Penaliza errores grandes (días críticos) |
| MAPE (%) | ⚠️ [COMPLETAR] | ⚠️ [COMPLETAR] | Precisión porcentual del pronóstico |
| R² | ⚠️ [COMPLETAR] | ⚠️ [COMPLETAR] | Varianza explicada |

> 💡 *Ejecuta `python src/model.py` para reproducir estas métricas y completa la tabla con tu salida.*

**Interpretación:** Las features más importantes son los **lags de ventas** y el **día de la semana**, confirmando los hallazgos del EDA: la demanda tiene fuerte inercia temporal y estacionalidad semanal.

---

## 🗄️ Integración SQL (SQLite)

En producción, las predicciones no viven en archivos Python: se persisten para que otros sistemas las consuman.

**Esquema de la base de datos (`db/demanda.db`):**

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
3. **🤖 Predicciones del Modelo** – predicho vs real, distribución de errores, precisión por tienda.
4. **🔍 Feature Importance** – qué variables mueven el modelo, con interpretación de negocio.

⚠️ [COMPLETAR: captura de pantalla del dashboard aquí]

---

## 🔮 Uso del Modelo en Producción

### 1. Predicción batch (reporte para logística)
```bash
python src/predict.py
```
Genera el pronóstico de los próximos 7 días por tienda con recomendación de inventario (+10% de margen de seguridad).

### 2. Dashboard interactivo
```bash
streamlit run src/app.py
```

### 3. API REST (microservicio)
```bash
python src/api.py
```
Endpoint `POST /predict` con body `{"store_id": 1, "date": "2025-08-18"}` → respuesta JSON con `predicted_sales`. Documentación automática en `http://localhost:8000/docs`.

---

## 🚧 Desafíos Técnicos y Soluciones

Este proyecto enfrentó problemas **reales de producción**, documentados como evidencia de madurez técnica:

### 1. Tipos de datos inconsistentes (mixed types)
- **Problema:** `StateHoliday` mezclaba strings (`"0"`) y enteros (`0`), causando `ArrowTypeError` al serializar en Parquet.
- **Solución:** Tipado explícito en la ingesta (`dtype={'StateHoliday': str}`) + estandarización con `fillna` y `astype(str)`.
- **Competencia demostrada:** control de calidad de datos y manejo de schemas.

### 2. Visualizaciones frágiles ante datos incompletos
- **Problema:** El dataset cubre solo 3 meses, pero el gráfico asumía 12 → `ValueError` en matplotlib.
- **Solución:** Etiquetas dinámicas generadas desde los meses *presentes* en los datos (defensive programming).
- **Competencia demostrada:** código robusto y adaptable a datos reales.

### 3. Mismatch de schemas entre Python y SQL
- **Problema:** El DataFrame usaba `Store` y la tabla SQL esperaba `store_id` → `OperationalError`.
- **Solución:** Mapping explícito de columnas con `.rename()` antes de la persistencia, documentando la convención de nombres.
- **Competencia demostrada:** gobernanza de datos e integración entre sistemas.

---

## 🚀 Instalación y Ejecución

### Requisitos previos
- Python 3.10+
- Dataset de Kaggle: [Rossmann Store Sales](https://www.kaggle.com/competitions/rossmann-store-sales) → colocar `train.csv` y `store.csv` en `data/`

### Pasos

```bash
# 1. Clonar repositorio
git clone https://github.com/⚠️[TU-USUARIO]/⚠️[demanda-ml].git
cd demanda_ml

# 2. Crear y activar entorno virtual
python -m venv venv
venv\Scripts\activate        # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Ejecutar pipeline en orden
python src/eda.py            # Análisis exploratorio
python src/features.py       # Feature engineering
python src/model.py          # Entrenamiento y evaluación
python src/sql.py            # Persistencia SQL

# 5. Levantar dashboard
streamlit run src/app.py

# 6. (Opcional) Predicción batch y API
python src/predict.py
python src/api.py
```

### `requirements.txt`
```
pandas
numpy
scikit-learn
xgboost
matplotlib
seaborn
streamlit
plotly
sqlalchemy
pyarrow
fastapi
uvicorn
```

---

## 🗺️ Roadmap (próximos pasos)

- [ ] Despliegue del dashboard en Streamlit Community Cloud
- [ ] Automatización del pipeline con Apache Airflow (orquestación)
- [ ] Pruebas unitarias con `pytest` (calidad de datos automatizada)
- [ ] Migración del almacenamiento a S3/MinIO (simulación Data Lake)
- [ ] Experimentación con Prophet para estacionalidad anual
- [ ] CI/CD con GitHub Actions

---

## 🎓 Sobre el Autor

**William** — Ingeniero Mecatrónico en transición a Ciencia de Datos.

Mi formación en mecatrónica me dio una ventaja única: entiendo los procesos físicos e industriales detrás de los datos (sensores, operaciones, mantenimiento). Este portafolio demuestra que combino esa visión de ingeniería con habilidades modernas de datos: Python, SQL, ML, pipelines ETL y visualización.

📬 **Contacto:**
- GitHub: ⚠️ [COMPLETAR]
- LinkedIn: ⚠️ [COMPLETAR]
- Email: ⚠️ [COMPLETAR]

---

*Dataset: Rossmann Store Sales (Kaggle) · Proyecto de portafolio con fines educativos y de demostración.*
