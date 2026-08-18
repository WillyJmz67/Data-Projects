"""
=============================================================================
PASO 6: INTEGRACIÓN CON BASE DE DATOS (SQL)
=============================================================================
Contexto de Negocio:
    En un entorno real, las predicciones no se quedan en un archivo Python.
    Se almacenan en una base de datos para que otros sistemas (dashboards,
    ERPs, equipos de logística) puedan consultarlas.

    Aquí simulamos ese flujo:
    1. Guardamos los datos procesados en SQLite
    2. Guardamos las predicciones del modelo
    3. Ejecutamos consultas SQL para extraer insights
    4. Demostramos que el pipeline es reproducible y consultable

    ¿Por qué SQLite? Es gratuito, no requiere servidor, y demuestra
    las mismas habilidades SQL que PostgreSQL o MySQL.
=============================================================================
"""

import pandas as pd
import numpy as np
import sqlite3
import os
import pickle

# ============================================================
# CONFIGURACIÓN
# ============================================================
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'output')
MODEL_DIR = os.path.join(os.path.dirname(__file__), '..', 'models')
DB_DIR = os.path.join(os.path.dirname(__file__), '..', 'db')
os.makedirs(DB_DIR, exist_ok=True)

DB_PATH = os.path.join(DB_DIR, 'demanda.db')

print("=" * 60)
print("PASO 6: INTEGRACIÓN CON BASE DE DATOS SQL")
print("=" * 60)

# ============================================================
# 6.1 CARGAR DATOS Y MODELO
# ============================================================
print("\n📂 Cargando datos y modelo...")
df = pd.read_parquet(os.path.join(OUTPUT_DIR, 'dataset_procesado.parquet'))

# Buscar el modelo guardado
model_files = [f for f in os.listdir(MODEL_DIR) if f.endswith('.pkl')]
if model_files:
    model_path = os.path.join(MODEL_DIR, model_files[0])
    with open(model_path, 'rb') as f:
        model = pickle.load(f)
    print(f"   ✅ Modelo cargado: {model_files[0]}")
else:
    print("   ⚠️ No se encontró modelo. Ejecuta step5_model.py primero.")
    model = None

# ============================================================
# 6.2 CREAR BASE DE DATOS Y TABLAS
# ============================================================
print("\n🔧 Creando base de datos SQLite...")

# Conectar (crea el archivo si no existe)
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Tabla 1: Datos históricos procesados
# ¿Por qué? Almacena el dataset limpio para consultas futuras.
cursor.execute('DROP TABLE IF EXISTS historical_data')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS historical_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        store_id INTEGER,
        date TEXT,
        sales REAL,
        customers INTEGER,
        day_of_week INTEGER,
        month INTEGER,
        year INTEGER,
        is_weekend INTEGER,
        is_open INTEGER,
        competition_distance REAL,
        promo INTEGER,
        promo2 INTEGER
    )
''')

# Tabla 2: Predicciones del modelo
# ¿Por qué? Las predicciones se almacenan por separado para que
# el equipo de logística las consulte sin tocar los datos crudos.
cursor.execute('DROP TABLE IF EXISTS predictions')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        store_id INTEGER,
        date TEXT,
        predicted_sales REAL,
        actual_sales REAL,
        error REAL,
        model_name TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

# Tabla 3: Métricas del modelo (auditoría)
# ¿Por qué? En producción, necesitas rastrear qué versión del modelo
# generó cada predicción y qué tan preciso fue.
cursor.execute('DROP TABLE IF EXISTS model_metrics')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS model_metrics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        model_name TEXT,
        metric_name TEXT,
        metric_value REAL,
        evaluation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

conn.commit()
print("   ✅ Tablas creadas: historical_data, predictions, model_metrics")

# ============================================================
# 6.3 INSERTAR DATOS HISTÓRICOS
# ============================================================
print("\n📝 Insertando datos históricos...")

# ✅ CORRECCIÓN: Mapear nombres del DataFrame a nombres de la tabla SQL
# El DataFrame tiene 'Store' pero la tabla espera 'store_id'
cols_mapping = {
    'Store': 'store_id',
    'Date': 'date',
    'Sales': 'sales',
    'Customers': 'customers',
    'DayOfWeek': 'day_of_week',
    'Month': 'month',
    'Year': 'year',
    'IsWeekend': 'is_weekend',
    'IsOpen': 'is_open',
    'CompetitionDistance': 'competition_distance',
    'Promo': 'promo',
    'Promo2': 'promo2'
}

# Seleccionar solo las columnas que existen en el DataFrame
available_cols = {k: v for k, v in cols_mapping.items() if k in df.columns}
insert_df = df[list(available_cols.keys())].copy()

# Renombrar columnas para que coincidan con la tabla SQL
insert_df.rename(columns=available_cols, inplace=True)

# Convertir Date a string (SQLite no tiene tipo DATE nativo)
insert_df['date'] = insert_df['date'].astype(str)

# Insertar en bloques
insert_df.to_sql('historical_data', conn, if_exists='append', index=False, chunksize=5000)
print(f"   ✅ {len(insert_df):,} filas insertadas en historical_data")

# ============================================================
# 6.4 GENERAR Y ALMACENAR PREDICCIONES
# ============================================================
if model is not None:
    print("\n📝 Generando predicciones y almacenando...")

    # Usar el último 15% de datos como "test"
    df_sorted = df.sort_values('Date')
    split_idx = int(len(df_sorted) * 0.85)
    test_data = df_sorted.iloc[split_idx:].copy()

    # Obtener features (mismas que en step5)
    exclude_cols = [
        'Store', 'Date', 'Sales', 'Customers',
        'Open', 'Promo2SinceWeek', 'Promo2SinceYear',
        'CompetitionOpenSinceMonth', 'CompetitionOpenSinceYear',
        'StateHoliday', 'SchoolHoliday',
    ]
    feature_cols = [
        col for col in df.select_dtypes(include=[np.number]).columns
        if col not in exclude_cols
    ]

    X_test = test_data[feature_cols]
    test_data['predicted_sales'] = model.predict(X_test)
    test_data['error'] = test_data['predicted_sales'] - test_data['Sales']

    # Preparar datos para inserción
    pred_df = pd.DataFrame({
        'store_id': test_data['Store'],
        'date': test_data['Date'].astype(str),
        'predicted_sales': test_data['predicted_sales'].round(2),
        'actual_sales': test_data['Sales'],
        'error': test_data['error'].round(2),
        'model_name': type(model).__name__
    })

    pred_df.to_sql('predictions', conn, if_exists='append', index=False, chunksize=5000)
    print(f"   ✅ {len(pred_df):,} predicciones insertadas")

    # Insertar métricas
    mae = np.mean(np.abs(test_data['error']))
    rmse = np.sqrt(np.mean(test_data['error'] ** 2))
    mask = test_data['Sales'] > 0
    mape = np.mean(np.abs(test_data.loc[mask, 'error'] / test_data.loc[mask, 'Sales'])) * 100

    metrics = [
        (type(model).__name__, 'MAE', round(mae, 2)),
        (type(model).__name__, 'RMSE', round(rmse, 2)),
        (type(model).__name__, 'MAPE', round(mape, 2)),
    ]
    cursor.executemany(
        'INSERT INTO model_metrics (model_name, metric_name, metric_value) VALUES (?, ?, ?)',
        metrics
    )
    conn.commit()
    print(f"   ✅ Métricas del modelo insertadas")

# ============================================================
# 6.5 CONSULTAS SQL DE VALIDACIÓN
# ============================================================
# ¿Por qué? Esto demuestra que puedes extraer insights directamente
# con SQL, una habilidad CRÍTICA para cualquier rol de datos.
print("\n" + "=" * 60)
print("🔍 CONSULTAS SQL DE VALIDACIÓN")
print("=" * 60)

# Consulta 1: Ventas totales por tienda (Top 10)
print("\n📊 Consulta 1: Top 10 tiendas por ventas totales")
query1 = """
    SELECT
        store_id,
        COUNT(*) as days_of_data,
        ROUND(SUM(sales), 0) as total_sales,
        ROUND(AVG(sales), 0) as avg_daily_sales,
        MAX(sales) as max_daily_sales
    FROM historical_data
    GROUP BY store_id
    ORDER BY total_sales DESC
    LIMIT 10
"""
result1 = pd.read_sql_query(query1, conn)
print(result1.to_string(index=False))

# Consulta 2: Ventas por día de la semana
print("\n📊 Consulta 2: Ventas promedio por día de la semana")
query2 = """
    SELECT
        CASE day_of_week
            WHEN 0 THEN 'Lunes'
            WHEN 1 THEN 'Martes'
            WHEN 2 THEN 'Miércoles'
            WHEN 3 THEN 'Jueves'
            WHEN 4 THEN 'Viernes'
            WHEN 5 THEN 'Sábado'
            WHEN 6 THEN 'Domingo'
        END as dia,
        ROUND(AVG(sales), 0) as avg_sales,
        COUNT(*) as records
    FROM historical_data
    GROUP BY day_of_week
    ORDER BY day_of_week
"""
result2 = pd.read_sql_query(query2, conn)
print(result2.to_string(index=False))

# Consulta 3: Precisión del modelo por tienda
if model is not None:
    print("\n📊 Consulta 3: Precisión del modelo por tienda (Top 10 con más error)")
    query3 = """
        SELECT
            store_id,
            COUNT(*) as predictions,
            ROUND(AVG(ABS(error)), 0) as mae,
            ROUND(AVG(ABS(error) / NULLIF(actual_sales, 0)) * 100, 2) as mape_pct,
            model_name
        FROM predictions
        GROUP BY store_id
        ORDER BY mape_pct DESC
        LIMIT 10
    """
    result3 = pd.read_sql_query(query3, conn)
    print(result3.to_string(index=False))

# Consulta 4: Predicciones vs ventas reales (muestra)
if model is not None:
    print("\n📊 Consulta 4: Muestra de predicciones vs ventas reales")
    query4 = """
        SELECT
            store_id,
            date,
            ROUND(actual_sales, 0) as ventas_reales,
            ROUND(predicted_sales, 0) as ventas_predichas,
            ROUND(error, 0) as error,
            CASE
                WHEN ABS(error) < 100 THEN '✅ Preciso'
                WHEN ABS(error) < 500 THEN '⚠️ Aceptable'
                ELSE '❌ Impreciso'
            END as calidad
        FROM predictions
        WHERE actual_sales > 0
        ORDER BY date DESC
        LIMIT 15
    """
    result4 = pd.read_sql_query(query4, conn)
    print(result4.to_string(index=False))

# Consulta 5: Métricas del modelo
print("\n📊 Consulta 5: Métricas del modelo")
query5 = """
    SELECT
        model_name,
        metric_name,
        metric_value,
        evaluation_date
    FROM model_metrics
    ORDER BY evaluation_date DESC
"""
result5 = pd.read_sql_query(query5, conn)
print(result5.to_string(index=False))

# ============================================================
# 6.6 CERRAR CONEXIÓN Y RESUMEN
# ============================================================
conn.close()

db_size = os.path.getsize(DB_PATH) / (1024 * 1024)  # Convertir a MB

summary = f"""
RESUMEN DE INTEGRACIÓN SQL
===========================

Base de datos: {DB_PATH}
Tamaño: {db_size:.2f} MB

Tablas creadas:
  1. historical_data: Datos históricos procesados
  2. predictions: Predicciones del modelo con errores
  3. model_metrics: Métricas de evaluación para auditoría

Consultas de validación ejecutadas:
  ✅ Top 10 tiendas por ventas
  ✅ Ventas por día de la semana
  ✅ Precisión del modelo por tienda
  ✅ Muestra de predicciones vs reales
  ✅ Métricas del modelo

JUSTIFICACIÓN DE NEGOCIO:
  En un entorno de producción, esta base de datos sería consumida por:
  - Dashboards de Power BI / Metabase
  - Sistemas ERP para planificación de inventario
  - Equipos de logística para programación de entregas
  - APIs para consultas en tiempo real

  La tabla model_metrics permite auditoría y monitoreo del modelo,
  cumpliendo con las prácticas de MLOps y gobernanza de datos.
"""
print(summary)

with open(os.path.join(OUTPUT_DIR, 'resumen_sql.txt'), 'w', encoding='utf-8') as f:
    f.write(summary)

print("\n✅ PASO 6 COMPLETADO")
print(f"📁 Base de datos en: {os.path.abspath(DB_PATH)}")