"""Entrenamiento y evaluación de modelos de predicción de demanda."""

import pandas as pd
import numpy as np
import joblib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import select_feature_cols  # noqa: E402

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

sns.set_style("whitegrid")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'output')
MODEL_DIR = os.path.join(os.path.dirname(__file__), '..', 'models')
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(MODEL_DIR, exist_ok=True)

print("=" * 60)
print("PASO 5: MODELADO Y EVALUACIÓN")
print("=" * 60)

print("\n📂 Cargando datos procesados...")
df = pd.read_parquet(os.path.join(OUTPUT_DIR, 'dataset_procesado.parquet'))
print(f"   Dataset: {df.shape[0]:,} filas x {df.shape[1]} columnas")

target = 'Sales'

# La selección de features vive en utils.select_feature_cols para que
# entrenamiento y consumo (predict.py, api.py, app.py, sql.py) usen SIEMPRE la
# misma lista. Antes estaba duplicada en 5 ficheros y bastaba tocar uno para
# romper el resto.
feature_cols = select_feature_cols(df)

X = df[feature_cols].copy()
y = df[target].copy()

print(f"\n📊 Features: {len(feature_cols)}")
print(f"   Target: {target}")
print(f"   Features usadas: {feature_cols}")

print("\n🔧 División temporal de datos...")

df_sorted = df.sort_values('Date')
split_date = df_sorted['Date'].quantile(0.85)

train_mask = df_sorted['Date'] <= split_date
test_mask = df_sorted['Date'] > split_date

X_train = df_sorted.loc[train_mask, feature_cols]
y_train = df_sorted.loc[train_mask, target]
X_test = df_sorted.loc[test_mask, feature_cols]
y_test = df_sorted.loc[test_mask, target]

print(f"   Train: {X_train.shape[0]:,} filas (hasta {split_date.date()})")
print(f"   Test:  {X_test.shape[0]:,} filas (después de {split_date.date()})")

def calculate_metrics(y_true, y_pred, model_name):
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2 = r2_score(y_true, y_pred)

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

    print("\n" + "=" * 60)
    print("📈 COMPARACIÓN DE MODELOS")
    print("=" * 60)
    comparison = pd.DataFrame({
        'Random Forest': rf_metrics,
        'XGBoost': xgb_metrics
    })
    print(comparison.round(2))

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

print("\n🔍 Top 15 Features más importantes:")
feature_importance = pd.DataFrame({
    'feature': feature_cols,
    'importance': best_model.feature_importances_
}).sort_values('importance', ascending=False)

for i, row in feature_importance.head(15).iterrows():
    print(f"  {row['feature']}: {row['importance']:.4f}")

print("\n📊 Generando gráficos de evaluación...")

fig, axes = plt.subplots(2, 2, figsize=(16, 12))

axes[0, 0].scatter(y_test, best_pred, alpha=0.3, s=5, color='#2196F3')
axes[0, 0].plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()],
                'r--', linewidth=2, label='Predicción perfecta')
axes[0, 0].set_xlabel('Ventas Reales (€)')
axes[0, 0].set_ylabel('Ventas Predichas (€)')
axes[0, 0].set_title(f'{best_name}: Predicción vs Real', fontweight='bold')
axes[0, 0].legend()

errors = y_test - best_pred
axes[0, 1].hist(errors, bins=50, color='#FF9800', edgecolor='black', alpha=0.7)
axes[0, 1].axvline(x=0, color='red', linestyle='--', linewidth=2)
axes[0, 1].set_xlabel('Error (Predicho - Real)')
axes[0, 1].set_ylabel('Frecuencia')
axes[0, 1].set_title('Distribución de Errores', fontweight='bold')

top_features = feature_importance.head(15)
axes[1, 0].barh(range(len(top_features)), top_features['importance'].values,
                color='#4CAF50', edgecolor='black')
axes[1, 0].set_yticks(range(len(top_features)))
axes[1, 0].set_yticklabels(top_features['feature'].values)
axes[1, 0].set_xlabel('Importancia')
axes[1, 0].set_title('Top 15 Features Más Importantes', fontweight='bold')
axes[1, 0].invert_yaxis()

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

# Se borran los modelos anteriores para que no queden ficheros obsoletos mezclados
# con el nuevo (load_latest_model coge el más reciente, pero un repo con varios
# modelos del mismo experimento es una fuente de confusión).
for stale in [f for f in os.listdir(MODEL_DIR) if f.endswith(('.pkl', '.joblib'))]:
    os.remove(os.path.join(MODEL_DIR, stale))

# El nombre se sanea: 'Random Forest'.lower() daba "random forest_model.pkl", con
# un espacio en medio, que es frágil en línea de comandos y en URLs.
safe_name = best_name.lower().replace(' ', '_')
model_path = os.path.join(MODEL_DIR, f'{safe_name}_model.joblib')

# joblib + compresión en lugar de pickle a secas: el Random Forest sin comprimir
# ocupa ~105 MB y GitHub rechaza los ficheros de más de 100 MB.
joblib.dump(best_model, model_path, compress=3)
size_mb = os.path.getsize(model_path) / (1024 * 1024)
print(f"\n✅ Modelo guardado: {model_path} ({size_mb:.1f} MB, comprimido)")

metrics_path = os.path.join(OUTPUT_DIR, 'metricas_modelo.txt')
with open(metrics_path, 'w', encoding='utf-8') as f:
    f.write(f"MODELO SELECCIONADO: {best_name}\n")
    f.write(f"{'='*50}\n\n")

    f.write("COMPARACIÓN DE MODELOS (test temporal, 15% final)\n")
    f.write(f"{'-'*50}\n")
    compared = {'Random Forest': rf_metrics}
    if HAS_XGB:
        compared['XGBoost'] = xgb_metrics
    f.write(f"{'Métrica':<8}" + "".join(f"{n:>16}" for n in compared) + "\n")
    for metric in ('MAE', 'RMSE', 'MAPE', 'R2'):
        row = f"{metric:<8}" + "".join(f"{v[metric]:>16.4f}" for v in compared.values())
        f.write(row + "\n")

    f.write(f"\nMÉTRICAS DEL MODELO GUARDADO ({best_name}):\n")
    for metric, value in best_metrics.items():
        f.write(f"  {metric}: {value:.4f}\n")

    f.write(f"\nFEATURES USADAS ({len(feature_cols)}):\n")
    for col in feature_cols:
        f.write(f"  - {col}\n")
    f.write(f"\nIMPORTANCIA DE FEATURES:\n")
    for _, row in feature_importance.iterrows():
        f.write(f"  {row['feature']}: {row['importance']:.4f}\n")

print(f"✅ Métricas guardadas: {metrics_path}")

print("\n✅ PASO 5 COMPLETADO")
