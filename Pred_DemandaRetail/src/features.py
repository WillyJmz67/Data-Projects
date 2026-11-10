"""Feature engineering: transforma datos crudos en características para el modelo ML.

Uso:
    python src/features.py          # guarda el dataset procesado en Parquet
    python src/features.py --csv    # además, una copia en CSV (útil para inspeccionar)
"""

import argparse
import pandas as pd
import numpy as np
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import LAG_COLUMN_PREFIXES  # noqa: E402

parser = argparse.ArgumentParser(description="Feature engineering del dataset de demanda")
parser.add_argument('--csv', action='store_true',
                    help="Exportar también dataset_procesado.csv (ocupa ~5x más que el Parquet)")
args = parser.parse_args()

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'output')
os.makedirs(OUTPUT_DIR, exist_ok=True)

print("=" * 60)
print("PASO 4: FEATURE ENGINEERING")
print("=" * 60)

print("\n📂 Cargando datos...")
train = pd.read_csv(
    os.path.join(DATA_DIR, 'train.csv'),
    parse_dates=['Date'],
    dtype={'StateHoliday': str},
    low_memory=False
)
stores = pd.read_csv(os.path.join(DATA_DIR, 'store.csv'))
df = train.merge(stores, on='Store', how='left')

df['StateHoliday'] = df['StateHoliday'].astype(str).replace({'nan': '0', 'None': '0'})
if 'PromoInterval' in df.columns:
    df['PromoInterval'] = df['PromoInterval'].astype(str).replace({'nan': '', 'None': ''})
print(f"   Dataset unido: {df.shape[0]:,} filas")

print("\n🔧 Creando features temporales...")

df['Year'] = df['Date'].dt.year
df['Month'] = df['Date'].dt.month
df['Day'] = df['Date'].dt.day
df['DayOfWeek'] = df['Date'].dt.dayofweek
df['WeekOfYear'] = df['Date'].dt.isocalendar().week.astype(int)
df['DayOfYear'] = df['Date'].dt.dayofyear
df['Quarter'] = df['Date'].dt.quarter

df['IsWeekend'] = (df['DayOfWeek'] >= 5).astype(int)
df['IsMonthStart'] = df['Date'].dt.is_month_start.astype(int)
df['IsMonthEnd'] = df['Date'].dt.is_month_end.astype(int)
df['IsOpen'] = df['Open'].fillna(1).astype(int)

print(f"   ✅ 10 features temporales creadas")

print("\n🔧 Creando features de tienda...")

# dtype=np.int8 es importante: sin él pandas 2+ crea columnas de tipo bool, y
# select_dtypes(include=[np.number]) NO las detecta, así que el modelo entrenaría
# ignorando StoreType y Assortment sin dar ningún error.
df = pd.get_dummies(
    df, columns=['StoreType', 'Assortment'], prefix=['Type', 'Assort'], dtype=np.int8
)

df['CompetitionDistance'] = df['CompetitionDistance'].fillna(
    df['CompetitionDistance'].median()
)

df['CompetitionOpen'] = (
    12 * (df['Year'] - df['CompetitionOpenSinceYear']) +
    (df['Month'] - df['CompetitionOpenSinceMonth'])
).fillna(0).astype(int)

df['Promo2'] = df['Promo2'].fillna(0).astype(int)

print(f"   ✅ Features de tienda creadas")

print("\n🔧 Creando features de lags y ventanas móviles...")
print("   ⚠️ Esto puede tardar unos minutos...")

df = df.sort_values(['Store', 'Date']).reset_index(drop=True)

for lag in [7, 14, 21, 30]:
    df[f'Sales_Lag_{lag}'] = df.groupby('Store')['Sales'].shift(lag)

for window in [7, 14, 30]:
    df[f'Sales_RollingMean_{window}'] = (
        df.groupby('Store')['Sales']
        .transform(lambda x: x.shift(7).rolling(window=window, min_periods=1).mean())
    )
    df[f'Sales_RollingStd_{window}'] = (
        df.groupby('Store')['Sales']
        .transform(lambda x: x.shift(7).rolling(window=window, min_periods=1).std())
    )

df['Customers_Lag_7'] = df.groupby('Store')['Customers'].shift(7)
df['Customers_RollingMean_7'] = (
    df.groupby('Store')['Customers']
    .transform(lambda x: x.shift(7).rolling(window=7, min_periods=1).mean())
)

print(f"   ✅ Features de lags y rolling creadas")

print("\n🔧 Limpieza final...")

# Sólo se descartan las filas sin historia suficiente para calcular los lags.
# Un dropna() a secas es una trampa: si cualquier columna ajena al modelo
# (p. ej. PromoInterval, que es nula en las 544 tiendas sin Promo2) tiene NaN,
# dropna() borra esas tiendas ENTERAS y el modelo se entrena con una fracción
# del negocio sin que nada avise.
rows_before = len(df)
stores_before = df['Store'].nunique()

lag_cols = [c for c in df.columns if c.startswith(LAG_COLUMN_PREFIXES)]
df = df.dropna(subset=lag_cols).reset_index(drop=True)

rows_after = len(df)
print(f"   Columnas usadas para el dropna: {len(lag_cols)} (sólo lags/rolling)")
print(f"   Filas eliminadas por falta de historia: {rows_before - rows_after:,}")
print(f"   Tiendas: {stores_before} -> {df['Store'].nunique()}")

print(f"\n📊 Dataset final: {df.shape[0]:,} filas x {df.shape[1]} columnas")

print("\n💾 Guardando dataset procesado...")

# El Parquet es el artefacto canónico: conserva los tipos (incluidas las one-hot
# int8) y pesa ~5x menos que el CSV equivalente. El CSV sólo se genera si se pide
# con --csv, porque 983k filas x 46 columnas ocupan ~260 MB.
output_path = os.path.join(OUTPUT_DIR, 'dataset_procesado.parquet')
df.to_parquet(output_path, index=False)
print(f"✅ Dataset guardado: {output_path}")

if args.csv:
    csv_path = os.path.join(OUTPUT_DIR, 'dataset_procesado.csv')
    df.to_csv(csv_path, index=False)
    print(f"✅ Dataset guardado: {csv_path}")
else:
    print("ℹ️  CSV omitido (usa --csv para exportarlo)")

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
"""
print(feature_summary)

with open(os.path.join(OUTPUT_DIR, 'resumen_features.txt'), 'w', encoding='utf-8') as f:
    f.write(feature_summary)

print("\n✅ PASO 4 COMPLETADO")
