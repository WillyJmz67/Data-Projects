"""
=============================================================================
USO DEL MODELO: Predicción de demanda para una tienda específica
=============================================================================
Contexto: Un gerente de tienda quiere saber cuánto inventario pedir para
los próximos 7 días. Usamos el modelo entrenado para generar esa predicción.
=============================================================================
"""

import pandas as pd
import numpy as np
import pickle
import os
from datetime import datetime, timedelta

# ============================================================
# CONFIGURACIÓN
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, '..', 'output')
MODEL_DIR = os.path.join(BASE_DIR, '..', 'models')

print("=" * 60)
print("🔮 PREDICCIÓN DE DEMANDA - MODO PRODUCCIÓN")
print("=" * 60)

# ============================================================
# 1. CARGAR EL MODELO ENTRENADO
# ============================================================
model_files = [f for f in os.listdir(MODEL_DIR) if f.endswith('.pkl')]
if not model_files:
    print("❌ No se encontró modelo. Ejecuta src/model.py primero.")
    exit()

model_path = os.path.join(MODEL_DIR, model_files[0])
with open(model_path, 'rb') as f:
    model = pickle.load(f)

print(f"✅ Modelo cargado: {model_files[0]}")

# ============================================================
# 2. CARGAR DATOS HISTÓRICOS (para calcular lags)
# ============================================================
# El modelo necesita los lags (ventas de hace 7, 14, 30 días)
# Por eso cargamos el dataset procesado completo
df_hist = pd.read_parquet(os.path.join(OUTPUT_DIR, 'dataset_procesado.parquet'))
print(f"✅ Datos históricos cargados: {len(df_hist):,} registros")

# ============================================================
# 3. SELECCIONAR TIENDA Y GENERAR FEATURES PARA PREDICCIÓN
# ============================================================
store_id = 1088  # Puedes cambiar esto por cualquier tienda (1-1115)
print(f"\n🏪 Generando predicción para Tienda {store_id}...")

# Filtrar historial de la tienda
store_hist = df_hist[df_hist['Store'] == store_id].sort_values('Date').copy()

if len(store_hist) == 0:
    print(f"❌ No hay datos históricos para la tienda {store_id}")
    exit()

# Obtener la última fecha conocida
last_date = store_hist['Date'].max()
last_sales = store_hist['Sales'].iloc[-1]

print(f"   Última fecha en datos: {last_date.date()}")
print(f"   Últimas ventas registradas: €{last_sales:,.0f}")

# ============================================================
# 4. CREAR FEATURES PARA LOS PRÓXIMOS 7 DÍAS
# ============================================================
# El modelo espera las mismas columnas que usó en entrenamiento
exclude_cols = [
    'Store', 'Date', 'Sales', 'Customers',
    'Open', 'Promo2SinceWeek', 'Promo2SinceYear',
    'CompetitionOpenSinceMonth', 'CompetitionOpenSinceYear',
    'StateHoliday', 'SchoolHoliday',
]
feature_cols = [
    col for col in df_hist.select_dtypes(include=[np.number]).columns
    if col not in exclude_cols
]

print(f"\n📊 Features requeridas por el modelo: {len(feature_cols)}")

# Generar predicciones para los próximos 7 días
predictions = []
current_data = store_hist.copy()

for day_offset in range(1, 8):
    future_date = last_date + timedelta(days=day_offset)
    
    # Crear fila base con la última información conocida
    new_row = current_data.iloc[-1].copy()
    new_row['Date'] = future_date
    
    # Actualizar features temporales
    new_row['DayOfWeek'] = future_date.dayofweek
    new_row['Month'] = future_date.month
    new_row['Day'] = future_date.day
    new_row['WeekOfYear'] = future_date.isocalendar()[1]
    new_row['DayOfYear'] = future_date.timetuple().tm_yday
    new_row['Quarter'] = (future_date.month - 1) // 3 + 1
    new_row['IsWeekend'] = 1 if future_date.dayofweek >= 5 else 0
    new_row['IsMonthStart'] = 1 if future_date.day == 1 else 0
    new_row['IsMonthEnd'] = 1 if future_date.day == pd.Period(future_date, freq='M').days_in_month else 0
    
    # Actualizar lags (usar las últimas ventas conocidas o predicciones previas)
    # Esto es una simplificación; en producción usarías un pipeline real
    for lag in [7, 14, 21, 30]:
        lag_col = f'Sales_Lag_{lag}'
        if lag_col in feature_cols:
            # Buscar el valor de hace 'lag' días en current_data
            target_date = future_date - timedelta(days=lag)
            lag_data = current_data[current_data['Date'] == target_date]
            if len(lag_data) > 0:
                new_row[lag_col] = lag_data['Sales'].values[0]
            else:
                # Si no hay dato exacto, usar el último disponible
                new_row[lag_col] = current_data['Sales'].iloc[-1]
    
    # Actualizar rolling means (simplificado)
    for window in [7, 14, 30]:
        mean_col = f'Sales_RollingMean_{window}'
        std_col = f'Sales_RollingStd_{window}'
        if mean_col in feature_cols:
            recent_sales = current_data['Sales'].tail(window)
            new_row[mean_col] = recent_sales.mean()
            new_row[std_col] = recent_sales.std() if len(recent_sales) > 1 else 0
    
    # Extraer solo las features que el modelo espera
    X_pred = pd.DataFrame([new_row])[feature_cols]
    
    # Predecir
    pred_sales = model.predict(X_pred)[0]
    pred_sales = max(0, pred_sales)  # Las ventas no pueden ser negativas
    
    predictions.append({
        'date': future_date.date(),
        'day_name': future_date.strftime('%A'),
        'predicted_sales': round(pred_sales, 2),
        'confidence': 'Alta' if abs(pred_sales - current_data['Sales'].mean()) < current_data['Sales'].std() else 'Media'
    })
    
    # Agregar la predicción al historial para los siguientes lags
    new_row['Sales'] = pred_sales
    current_data = pd.concat([current_data, pd.DataFrame([new_row])], ignore_index=True)

# ============================================================
# 5. MOSTRAR RESULTADOS
# ============================================================
pred_df = pd.DataFrame(predictions)

print("\n" + "=" * 60)
print(f"📈 PREDICCIÓN DE DEMANDA - TIENDA {store_id}")
print("=" * 60)
print(f"\nBasado en datos hasta: {last_date.date()}")
print(f"Ventas promedio históricas: €{store_hist['Sales'].mean():,.0f}/día\n")

print(pred_df.to_string(index=False))

total_week = pred_df['predicted_sales'].sum()
avg_week = pred_df['predicted_sales'].mean()

print(f"\n{'='*60}")
print(f"💡 RESUMEN PARA EL GERENTE DE TIENDA:")
print(f"{'='*60}")
print(f"  📦 Total estimado próxima semana: €{total_week:,.0f}")
print(f"  📊 Promedio diario estimado: €{avg_week:,.0f}")
print(f"  ⚠️ Día con mayor demanda: {pred_df.loc[pred_df['predicted_sales'].idxmax(), 'day_name']} (€{pred_df['predicted_sales'].max():,.0f})")
print(f"  ✅ Día con menor demanda: {pred_df.loc[pred_df['predicted_sales'].idxmin(), 'day_name']} (€{pred_df['predicted_sales'].min():,.0f})")

print(f"\n💼 RECOMENDACIÓN DE INVENTARIO:")
print(f"  - Pedir stock para cubrir €{total_week * 1.1:,.0f} (+10% margen de seguridad)")
print(f"  - Reforzar personal el {pred_df.loc[pred_df['predicted_sales'].idxmax(), 'day_name']}")

# Guardar predicciones en CSV para el equipo de logística
output_pred = os.path.join(OUTPUT_DIR, f'prediccion_tienda_{store_id}.csv')
pred_df.to_csv(output_pred, index=False)
print(f"\n✅ Predicciones guardadas en: {output_pred}")