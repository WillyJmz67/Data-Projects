"""Integración con base de datos SQLite: almacena datos procesados y predicciones del modelo."""

import pandas as pd
import numpy as np
import sqlite3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import select_feature_cols, load_latest_model  # noqa: E402

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'output')
MODEL_DIR = os.path.join(os.path.dirname(__file__), '..', 'models')
DB_DIR = os.path.join(os.path.dirname(__file__), '..', 'db')
os.makedirs(DB_DIR, exist_ok=True)

DB_PATH = os.path.join(DB_DIR, 'demanda.db')

print("=" * 60)
print("PASO 6: INTEGRACIÓN CON BASE DE DATOS SQL")
print("=" * 60)

print("\n📂 Cargando datos y modelo...")
df = pd.read_parquet(os.path.join(OUTPUT_DIR, 'dataset_procesado.parquet'))

try:
    model, model_file = load_latest_model(MODEL_DIR)
    print(f"   ✅ Modelo cargado: {model_file}")
except FileNotFoundError as exc:
    print(f"   ⚠️ {exc}")
    model = None

print("\n🔧 Creando base de datos SQLite...")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

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

print("\n📝 Insertando datos históricos...")

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

available_cols = {k: v for k, v in cols_mapping.items() if k in df.columns}
insert_df = df[list(available_cols.keys())].copy()

insert_df.rename(columns=available_cols, inplace=True)

insert_df['date'] = insert_df['date'].astype(str)

insert_df.to_sql('historical_data', conn, if_exists='append', index=False, chunksize=5000)
print(f"   ✅ {len(insert_df):,} filas insertadas en historical_data")

if model is not None:
    print("\n📝 Generando predicciones y almacenando...")

    # Mismo corte temporal que model.py (cuantil 0.85 de la fecha). Antes aquí se
    # usaba iloc[int(len*0.85)], que con filas desbalanceadas por día deja un test
    # distinto al de model.py: las métricas de la tabla predictions no cuadraban
    # con las de metricas_modelo.txt.
    df_sorted = df.sort_values('Date')
    split_date = df_sorted['Date'].quantile(0.85)
    test_data = df_sorted[df_sorted['Date'] > split_date].copy()

    feature_cols = select_feature_cols(df)

    X_test = test_data[feature_cols]
    test_data['predicted_sales'] = model.predict(X_test)
    test_data['error'] = test_data['predicted_sales'] - test_data['Sales']

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

print("\n" + "=" * 60)
print("🔍 CONSULTAS SQL DE VALIDACIÓN")
print("=" * 60)

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

conn.close()

db_size = os.path.getsize(DB_PATH) / (1024 * 1024)

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
"""
print(summary)

with open(os.path.join(OUTPUT_DIR, 'resumen_sql.txt'), 'w', encoding='utf-8') as f:
    f.write(summary)

print("\n✅ PASO 6 COMPLETADO")
print(f"📁 Base de datos en: {os.path.abspath(DB_PATH)}")
