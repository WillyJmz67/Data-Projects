"""
=============================================================================
PASO 4: FEATURE ENGINEERING (Ingeniería de Características)
=============================================================================
Contexto de Negocio:
    Los algoritmos de ML no entienden fechas ni textos. Necesitan números.
    Este paso transforma los datos crudos en características que el modelo
    puede interpretar:
    - Variables temporales (día, mes, semana, ¿es fin de semana?)
    - Variables de retraso (ventas de hace 7, 14, 30 días)
    - Variables de ventana móvil (promedio de últimos 7 días)
    - Variables de la tienda (tipo, tamaño, competencia)

    ¿Por qué? Un modelo sin estas features sería como predecir el clima
    sin saber la estación del año.
=============================================================================
"""

import pandas as pd
import numpy as np
import os
import pickle

# ============================================================
# CONFIGURACIÓN
# ============================================================
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'output')
os.makedirs(OUTPUT_DIR, exist_ok=True)

print("=" * 60)
print("PASO 4: FEATURE ENGINEERING")
print("=" * 60)

# ============================================================
# 4.1 CARGA Y UNIÓN DE DATOS
# ============================================================
print("\n📂 Cargando datos...")
train = pd.read_csv(
    os.path.join(DATA_DIR, 'train.csv'),
    parse_dates=['Date'],
    dtype={'StateHoliday': str},  # Forzar tipo string desde la carga
    low_memory=False
)
stores = pd.read_csv(os.path.join(DATA_DIR, 'store.csv'))
df = train.merge(stores, on='Store', how='left')
# CORRECCIÓN: Convertir StateHoliday a string uniforme
# ¿Por qué? Tiene tipos mixtos ("0" como string y 0 como int).
# PyArrow requiere tipos consistentes para guardar en Parquet.
df['StateHoliday'] = df['StateHoliday'].astype(str).replace({'nan': '0', 'None': '0'})

# También corregir PromoInterval que puede tener el mismo problema
if 'PromoInterval' in df.columns:
    df['PromoInterval'] = df['PromoInterval'].astype(str).replace({'nan': '', 'None': ''})
print(f"   Dataset unido: {df.shape[0]:,} filas")

# ============================================================
# 4.2 FEATURES TEMPORALES
# ============================================================
# ¿Por qué? El modelo necesita saber EN QUÉ MOMENTO del tiempo estamos.
# Las ventas de diciembre no son iguales a las de marzo.
print("\n🔧 Creando features temporales...")

df['Year'] = df['Date'].dt.year
df['Month'] = df['Date'].dt.month
df['Day'] = df['Date'].dt.day
df['DayOfWeek'] = df['Date'].dt.dayofweek       # 0=Lunes, 6=Domingo
df['WeekOfYear'] = df['Date'].dt.isocalendar().week.astype(int)
df['DayOfYear'] = df['Date'].dt.dayofyear
df['Quarter'] = df['Date'].dt.quarter

# Features binarias (flags)
# ¿Por qué? Simplifican la información para el modelo.
# "¿Es fin de semana?" es más directo que "¿Es día 5 o 6?"
df['IsWeekend'] = (df['DayOfWeek'] >= 5).astype(int)
df['IsMonthStart'] = df['Date'].dt.is_month_start.astype(int)
df['IsMonthEnd'] = df['Date'].dt.is_month_end.astype(int)

# ¿Está la tienda abierta? (Open = 1 abierto, 0 cerrado)
df['IsOpen'] = df['Open'].fillna(1).astype(int)

print(f"   ✅ 10 features temporales creadas")

# ============================================================
# 4.3 FEATURES DE LA TIENDA
# ============================================================
# ¿Por qué? Una tienda grande con surtido amplio vende diferente
# a una tienda pequeña. El modelo debe capturar esta diferencia.
print("\n🔧 Creando features de tienda...")

# Encode de variables categóricas
# StoreType: a, b, c, d -> one-hot encoding
# Assortment: a, b, c -> one-hot encoding
df = pd.get_dummies(df, columns=['StoreType', 'Assortment'], prefix=['Type', 'Assort'])

# CompetitionDistance: distancia a la competencia más cercana
# ¿Por qué? Si hay competencia cerca, las ventas pueden ser menores.
# Reemplazamos nulos con la mediana (no sabemos la distancia)
df['CompetitionDistance'] = df['CompetitionDistance'].fillna(
    df['CompetitionDistance'].median()
)

# CompetitionOpenSince: ¿cuántos meses lleva abierta la competencia?
# ¿Por qué? Una competencia nueva tiene menos impacto que una establecida.
df['CompetitionOpen'] = (
    12 * (df['Year'] - df['CompetitionOpenSinceYear']) +
    (df['Month'] - df['CompetitionOpenSinceMonth'])
).fillna(0).astype(int)

# Promo2: ¿la tienda tiene promociones continuas?
df['Promo2'] = df['Promo2'].fillna(0).astype(int)

print(f"   ✅ Features de tienda creadas")

# ============================================================
# 4.4 FEATURES DE RETRASO (LAGS) Y VENTANAS MÓVILES
# ============================================================
# ¿Por qué? Las ventas de hoy están correlacionadas con las de ayer,
# la semana pasada y el mes pasado. Estas features capturan esa inercia.
# IMPORTANTE: Se calculan POR TIENDA para no mezclar datos entre tiendas.
print("\n🔧 Creando features de lags y ventanas móviles...")
print("   ⚠️ Esto puede tardar unos minutos...")

# Ordenar por tienda y fecha (CRÍTICO para lags correctos)
df = df.sort_values(['Store', 'Date']).reset_index(drop=True)

# Lags: ventas de hace N días
# ¿Por qué 7, 14, 30? Capturan semanalidad, quincenalidad y mensualidad.
for lag in [7, 14, 21, 30]:
    df[f'Sales_Lag_{lag}'] = df.groupby('Store')['Sales'].shift(lag)

# Ventanas móviles: promedio de ventas de los últimos N días
# ¿Por qué? Suaviza la volatilidad diaria y captura la tendencia reciente.
for window in [7, 14, 30]:
    df[f'Sales_RollingMean_{window}'] = (
        df.groupby('Store')['Sales']
        .transform(lambda x: x.shift(7).rolling(window=window, min_periods=1).mean())
    )
    df[f'Sales_RollingStd_{window}'] = (
        df.groupby('Store')['Sales']
        .transform(lambda x: x.shift(7).rolling(window=window, min_periods=1).std())
    )

# Clientes: también tienen inercia
df['Customers_Lag_7'] = df.groupby('Store')['Customers'].shift(7)
df['Customers_RollingMean_7'] = (
    df.groupby('Store')['Customers']
    .transform(lambda x: x.shift(7).rolling(window=7, min_periods=1).mean())
)

print(f"   ✅ Features de lags y rolling creadas")

# ============================================================
# 4.5 LIMPIEZA FINAL
# ============================================================
print("\n🔧 Limpieza final...")

# Los lags generan NaN en las primeras filas (no hay datos previos)
# Las eliminamos porque el modelo no puede usarlas
rows_before = len(df)
df = df.dropna().reset_index(drop=True)
rows_after = len(df)
print(f"   Filas eliminadas por NaN de lags: {rows_before - rows_after:,}")

# Verificar tipos de datos
print(f"\n📊 Dataset final: {df.shape[0]:,} filas x {df.shape[1]} columnas")

# ============================================================
# 4.6 GUARDAR DATASET PROCESADO
# ============================================================
# Guardamos en Parquet (más rápido y comprimido que CSV)
# ¿Por qué Parquet? Es el formato estándar en pipelines de datos
# empresariales (AWS Glue, Spark, Athena lo usan nativamente).
output_path = os.path.join(OUTPUT_DIR, 'dataset_procesado.parquet')
df.to_parquet(output_path, index=False)
print(f"\n✅ Dataset guardado: {output_path}")

# También guardar como CSV para inspección manual
csv_path = os.path.join(OUTPUT_DIR, 'dataset_procesado.csv')
df.to_csv(csv_path, index=False)
print(f"✅ Dataset guardado: {csv_path}")

# ============================================================
# 4.7 RESUMEN DE FEATURES
# ============================================================
feature_summary = f"""
RESUMEN DE FEATURE ENGINEERING
===============================

Features Temporales:
  - Year, Month, Day, DayOfWeek, WeekOfYear, DayOfYear, Quarter
  - IsWeekend, IsMonthStart, IsMonthEnd, IsOpen

Features de Tienda:
  - Type_a, Type_b, Type_c, Type_d (one-hot)
  - Assort_a, Assort_b, Assort_c (one-hot)
  - CompetitionDistance, CompetitionOpen, Promo2

Features de Inercia (Lags):
  - Sales_Lag_7, Sales_Lag_14, Sales_Lag_21, Sales_Lag_30
  - Customers_Lag_7

Features de Tendencia (Rolling Windows):
  - Sales_RollingMean_7/14/30
  - Sales_RollingStd_7/14/30
  - Customers_RollingMean_7

Total de columnas: {df.shape[1]}
Filas finales: {df.shape[0]:,}

JUSTIFICACIÓN DE NEGOCIO:
  Las features de lags y rolling windows son las más importantes
  porque capturan la inercia de las ventas. Una tienda que vendió
  bien la semana pasada probablemente venderá bien esta semana.
  Las features temporales capturan la estacionalidad (navidad,
  verano, fines de semana).
"""
print(feature_summary)

with open(os.path.join(OUTPUT_DIR, 'resumen_features.txt'), 'w', encoding='utf-8') as f:
    f.write(feature_summary)

print("\n✅ PASO 4 COMPLETADO")