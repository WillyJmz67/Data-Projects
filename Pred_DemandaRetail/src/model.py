"""
=============================================================================
PASO 5: MODELADO Y EVALUACIÓN
=============================================================================
Contexto de Negocio:
    Con los datos procesados, entrenamos modelos para predecir las ventas
    futuras. Comparamos un modelo base (Random Forest) contra un modelo
    avanzado (XGBoost) para demostrar la mejora.

    Métricas de negocio:
    - MAE: Error absoluto medio (en euros). "En promedio, nos equivocamos
      por X euros por día por tienda."
    - RMSE: Penaliza errores grandes. "Si nos equivocamos mucho, la
      penalización es mayor."
    - MAPE: Error porcentual. "Nuestro modelo tiene un X% de precisión."

    Un MAPE < 15% es excelente para predicción de demanda retail.
=============================================================================
"""

import pandas as pd
import numpy as np
import os
import pickle
from sklearn.model_selection import TimeSeriesSplit
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import matplotlib.pyplot as plt
import seaborn as sns

try:
    from xgboost import XGBRegressor
    HAS_XGB = True
except ImportError:
    HAS_XGB = False
    print("⚠️ XGBoost no instalado. Usando solo Random Forest.")

# ============================================================
# CONFIGURACIÓN
# ============================================================
sns.set_style("whitegrid")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'output')
MODEL_DIR = os.path.join(os.path.dirname(__file__), '..', 'models')
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(MODEL_DIR, exist_ok=True)

print("=" * 60)
print("PASO 5: MODELADO Y EVALUACIÓN")
print("=" * 60)

# ============================================================
# 5.1 CARGAR DATOS PROCESADOS
# ============================================================
print("\n📂 Cargando datos procesados...")
df = pd.read_parquet(os.path.join(OUTPUT_DIR, 'dataset_procesado.parquet'))
print(f"   Dataset: {df.shape[0]:,} filas x {df.shape[1]} columnas")

# ============================================================
# 5.2 DEFINIR VARIABLES
# ============================================================
# Target: Sales (lo que queremos predecir)
target = 'Sales'

# Columnas a excluir de las features
exclude_cols = [
    'Store', 'Date', 'Sales', 'Customers',  # Target y identificadores
    'Open',  # Ya lo convertimos en IsOpen
    'Promo2SinceWeek', 'Promo2SinceYear',  # Ya derivamos Promo2
    'CompetitionOpenSinceMonth', 'CompetitionOpenSinceYear',  # Ya derivamos CompetitionOpen
    'StateHoliday', 'SchoolHoliday',  # Categóricas que no procesamos
]

# Features: todas las columnas numéricas excepto las excluidas
feature_cols = [
    col for col in df.select_dtypes(include=[np.number]).columns
    if col not in exclude_cols
]

X = df[feature_cols].copy()
y = df[target].copy()

print(f"\n📊 Features: {len(feature_cols)}")
print(f"   Target: {target}")
print(f"   Features usadas: {feature_cols}")

# ============================================================
# 5.3 DIVISIÓN TEMPORAL (Time-Based Split)
# ============================================================
# ¿Por qué no train_test_split aleatorio?
# En series de tiempo, NO puedes entrenar con datos del futuro
# para predecir el pasado. Sería "trampa" (data leakage).
# Dividimos por fecha: entrenamos con el pasado, validamos con el futuro.
print("\n🔧 División temporal de datos...")

df_sorted = df.sort_values('Date')
split_date = df_sorted['Date'].quantile(0.85)  # 85% train, 15% test

train_mask = df_sorted['Date'] <= split_date
test_mask = df_sorted['Date'] > split_date

X_train = df_sorted.loc[train_mask, feature_cols]
y_train = df_sorted.loc[train_mask, target]
X_test = df_sorted.loc[test_mask, feature_cols]
y_test = df_sorted.loc[test_mask, target]

print(f"   Train: {X_train.shape[0]:,} filas (hasta {split_date.date()})")
print(f"   Test:  {X_test.shape[0]:,} filas (después de {split_date.date()})")

# ============================================================
# 5.4 ENTRENAR MODELOS
# ============================================================

def calculate_metrics(y_true, y_pred, model_name):
    """Calcula métricas de negocio y las imprime en formato legible."""
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2 = r2_score(y_true, y_pred)

    # MAPE: solo donde y_true > 0 (evitar división por cero)
    mask = y_true > 0
    mape = np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100

    print(f"\n{'='*50}")
    print(f"📊 MÉTRICAS - {model_name}")
    print(f"{'='*50}")
    print(f"  MAE:  {mae:,.0f} €  (error absoluto promedio)")
    print(f"  RMSE: {rmse:,.0f} €  (penaliza errores grandes)")
    print(f"  R²:   {r2:.4f}  (varianza explicada)")
    print(f"  MAPE: {mape:.2f}%  (error porcentual)")
    print(f"\n  💡 Interpretación de negocio:")
    print(f"     En promedio, la predicción se desvía {mae:,.0f}€ por tienda/día")
    print(f"     El modelo tiene una precisión del {(100-mape):.1f}%")

    return {'MAE': mae, 'RMSE': rmse, 'R2': r2, 'MAPE': mape}


# --- Modelo 1: Random Forest (Baseline) ---
print("\n" + "=" * 60)
print("🌲 Entrenando Random Forest (modelo base)...")
print("=" * 60)

rf_model = RandomForestRegressor(
    n_estimators=100,
    max_depth=15,
    min_samples_split=10,
    min_samples_leaf=5,
    random_state=42,
    n_jobs=-1,
    verbose=0
)
rf_model.fit(X_train, y_train)
rf_pred = rf_model.predict(X_test)
rf_metrics = calculate_metrics(y_test, rf_pred, "Random Forest")

# --- Modelo 2: XGBoost (Avanzado) ---
if HAS_XGB:
    print("\n" + "=" * 60)
    print("🚀 Entrenando XGBoost (modelo avanzado)...")
    print("=" * 60)

    xgb_model = XGBRegressor(
        n_estimators=200,
        max_depth=8,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=1,
        reg_lambda=1,
        random_state=42,
        n_jobs=-1,
        verbosity=0
    )
    xgb_model.fit(X_train, y_train)
    xgb_pred = xgb_model.predict(X_test)
    xgb_metrics = calculate_metrics(y_test, xgb_pred, "XGBoost")

    # Comparación
    print("\n" + "=" * 60)
    print("📈 COMPARACIÓN DE MODELOS")
    print("=" * 60)
    comparison = pd.DataFrame({
        'Random Forest': rf_metrics,
        'XGBoost': xgb_metrics
    })
    print(comparison.round(2))

    # Seleccionar el mejor modelo
    if xgb_metrics['MAPE'] < rf_metrics['MAPE']:
        best_model = xgb_model
        best_name = "XGBoost"
        best_metrics = xgb_metrics
        best_pred = xgb_pred
    else:
        best_model = rf_model
        best_name = "Random Forest"
        best_metrics = rf_metrics
        best_pred = rf_pred
else:
    best_model = rf_model
    best_name = "Random Forest"
    best_metrics = rf_metrics
    best_pred = rf_pred

print(f"\n🏆 Mejor modelo: {best_name} (MAPE: {best_metrics['MAPE']:.2f}%)")

# ============================================================
# 5.5 IMPORTANCIA DE FEATURES
# ============================================================
# ¿Por qué? Los reclutadores quieren saber QUÉ variables importan.
# Esto demuestra que entiendes el modelo, no solo lo ejecutas.
print("\n🔍 Top 15 Features más importantes:")
feature_importance = pd.DataFrame({
    'feature': feature_cols,
    'importance': best_model.feature_importances_
}).sort_values('importance', ascending=False)

for i, row in feature_importance.head(15).iterrows():
    print(f"  {row['feature']}: {row['importance']:.4f}")

# ============================================================
# 5.6 VISUALIZACIONES DE EVALUACIÓN
# ============================================================
print("\n📊 Generando gráficos de evaluación...")

fig, axes = plt.subplots(2, 2, figsize=(16, 12))

# 1. Predicción vs Real
axes[0, 0].scatter(y_test, best_pred, alpha=0.3, s=5, color='#2196F3')
axes[0, 0].plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()],
                'r--', linewidth=2, label='Predicción perfecta')
axes[0, 0].set_xlabel('Ventas Reales (€)')
axes[0, 0].set_ylabel('Ventas Predichas (€)')
axes[0, 0].set_title(f'{best_name}: Predicción vs Real', fontweight='bold')
axes[0, 0].legend()

# 2. Distribución de errores
errors = y_test - best_pred
axes[0, 1].hist(errors, bins=50, color='#FF9800', edgecolor='black', alpha=0.7)
axes[0, 1].axvline(x=0, color='red', linestyle='--', linewidth=2)
axes[0, 1].set_xlabel('Error (Predicho - Real)')
axes[0, 1].set_ylabel('Frecuencia')
axes[0, 1].set_title('Distribución de Errores', fontweight='bold')

# 3. Feature Importance (top 15)
top_features = feature_importance.head(15)
axes[1, 0].barh(range(len(top_features)), top_features['importance'].values,
                color='#4CAF50', edgecolor='black')
axes[1, 0].set_yticks(range(len(top_features)))
axes[1, 0].set_yticklabels(top_features['feature'].values)
axes[1, 0].set_xlabel('Importancia')
axes[1, 0].set_title('Top 15 Features Más Importantes', fontweight='bold')
axes[1, 0].invert_yaxis()

# 4. Comparación de métricas (si hay XGBoost)
if HAS_XGB:
    metrics_df = pd.DataFrame({
        'Random Forest': [rf_metrics['MAE'], rf_metrics['RMSE'], rf_metrics['MAPE']],
        'XGBoost': [xgb_metrics['MAE'], xgb_metrics['RMSE'], xgb_metrics['MAPE']]
    }, index=['MAE (€)', 'RMSE (€)', 'MAPE (%)'])

    x = np.arange(len(metrics_df.index))
    width = 0.35
    axes[1, 1].bar(x - width/2, metrics_df['Random Forest'], width,
                   label='Random Forest', color='#2196F3', edgecolor='black')
    axes[1, 1].bar(x + width/2, metrics_df['XGBoost'], width,
                   label='XGBoost', color='#FF5722', edgecolor='black')
    axes[1, 1].set_xticks(x)
    axes[1, 1].set_xticklabels(metrics_df.index)
    axes[1, 1].set_title('Comparación de Métricas', fontweight='bold')
    axes[1, 1].legend()
else:
    axes[1, 1].text(0.5, 0.5, 'XGBoost no disponible', ha='center', va='center',
                    fontsize=16, transform=axes[1, 1].transAxes)

plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, '06_evaluacion_modelo.png'), dpi=150)
plt.close()
print("  ✅ 06_evaluacion_modelo.png")

# ============================================================
# 5.7 GUARDAR MODELO
# ============================================================
model_path = os.path.join(MODEL_DIR, f'{best_name.lower()}_model.pkl')
with open(model_path, 'wb') as f:
    pickle.dump(best_model, f)
print(f"\n✅ Modelo guardado: {model_path}")

# Guardar métricas
metrics_path = os.path.join(OUTPUT_DIR, 'metricas_modelo.txt')
with open(metrics_path, 'w', encoding='utf-8') as f:
    f.write(f"MODELO SELECCIONADO: {best_name}\n")
    f.write(f"{'='*50}\n\n")
    for metric, value in best_metrics.items():
        f.write(f"{metric}: {value:.4f}\n")
    f.write(f"\nFEATURES USADAS ({len(feature_cols)}):\n")
    for col in feature_cols:
        f.write(f"  - {col}\n")
    f.write(f"\nIMPORTANCIA DE FEATURES:\n")
    for _, row in feature_importance.iterrows():
        f.write(f"  {row['feature']}: {row['importance']:.4f}\n")

print(f"✅ Métricas guardadas: {metrics_path}")

print("\n✅ PASO 5 COMPLETADO")