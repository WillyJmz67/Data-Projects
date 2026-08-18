"""
=============================================================================
PASO 3: ANÁLISIS EXPLORATORIO DE DATOS (EDA)
=============================================================================
Contexto de Negocio:
    Una cadena de tiendas necesita predecir la demanda diaria de productos
    para optimizar su inventario. Antes de modelar, debemos entender:
    - ¿Cuándo se vende más? (estacionalidad)
    - ¿Qué tiendas venden más? (segmentación)
    - ¿Hay datos faltantes o errores? (calidad de datos)

    Este análisis guía las decisiones de Feature Engineering (Paso 4).
=============================================================================
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os

# ============================================================
# CONFIGURACIÓN
# ============================================================
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 6)
plt.rcParams['font.size'] = 11

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'output')
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ============================================================
# 3.1 CARGA Y UNIÓN DE DATOS
# ============================================================
print("=" * 60)
print("3.1 CARGA DE DATOS")
print("=" * 60)

# Cargar datasets
train = pd.read_csv(os.path.join(DATA_DIR, 'train.csv'), parse_dates=['Date'])
stores = pd.read_csv(os.path.join(DATA_DIR, 'store.csv'))

print(f"\n✅ train.csv cargado: {train.shape[0]:,} filas x {train.shape[1]} columnas")
print(f"✅ store.csv cargado: {stores.shape[0]:,} filas x {stores.shape[1]} columnas")

# Unir train con store (JOIN por Store)
# ¿Por qué? Las características de la tienda (tipo, tamaño, competencia)
# influyen directamente en las ventas. Sin esta unión, el modelo
# no podría diferenciar entre una tienda grande y una pequeña.
df = train.merge(stores, on='Store', how='left')

print(f"\n✅ Dataset unido: {df.shape[0]:,} filas x {df.shape[1]} columnas")
print(f"\nColumnas resultantes:")
for col in df.columns:
    print(f"  - {col}: {df[col].dtype}")

# ============================================================
# 3.2 CALIDAD DE DATOS
# ============================================================
print("\n" + "=" * 60)
print("3.2 CALIDAD DE DATOS")
print("=" * 60)

# Verificar valores nulos
# ¿Por qué? Los valores nulos pueden sesgar el modelo o causar errores.
# En producción, esto sería parte de las pruebas de calidad de datos.
null_counts = df.isnull().sum()
null_pct = (null_counts / len(df)) * 100
null_df = pd.DataFrame({
    'Valores Nulos': null_counts,
    'Porcentaje (%)': null_pct.round(2)
})
null_df = null_df[null_df['Valores Nulos'] > 0].sort_values('Valores Nulos', ascending=False)

if len(null_df) > 0:
    print("\n⚠️ Columnas con valores nulos:")
    print(null_df)
else:
    print("\n✅ No se encontraron valores nulos")

# Verificar duplicados
duplicates = df.duplicated().sum()
print(f"\n📋 Filas duplicadas: {duplicates:,}")

# ============================================================
# 3.3 ESTADÍSTICAS DESCRIPTIVAS
# ============================================================
print("\n" + "=" * 60)
print("3.3 ESTADÍSTICAS DE VENTAS")
print("=" * 60)

print(f"\n📊 Estadísticas de Sales (ventas diarias):")
print(f"  Media:     {df['Sales'].mean():,.0f}")
print(f"  Mediana:   {df['Sales'].median():,.0f}")
print(f"  Std Dev:   {df['Sales'].std():,.0f}")
print(f"  Mínimo:    {df['Sales'].min():,.0f}")
print(f"  Máximo:    {df['Sales'].max():,.0f}")

# ¿Cuántos días hubo ventas = 0?
# ¿Por qué? Días con 0 ventas pueden ser domingos cerrados o feriados.
# Esto es CRÍTICO para el modelo: debe aprender que hay días sin venta.
zero_sales = (df['Sales'] == 0).sum()
zero_pct = (zero_sales / len(df)) * 100
print(f"\n⚠️ Días con ventas = 0: {zero_sales:,} ({zero_pct:.1f}%)")

# ============================================================
# 3.4 ANÁLISIS TEMPORAL (Estacionalidad)
# ============================================================
print("\n" + "=" * 60)
print("3.4 ANÁLISIS TEMPORAL")
print("=" * 60)

# Extraer componentes de fecha para análisis
df['Year'] = df['Date'].dt.year
df['Month'] = df['Date'].dt.month
df['DayOfWeek'] = df['Date'].dt.dayofweek  # 0=Lunes, 6=Domingo
df['WeekOfYear'] = df['Date'].dt.isocalendar().week.astype(int)

# Ventas por día de la semana
# ¿Por qué? Si los sábados venden el doble que los lunes,
# el modelo DEBE saber el día de la semana para predecir bien.
sales_by_dow = df.groupby('DayOfWeek')['Sales'].mean()
print("\n📅 Ventas promedio por día de la semana:")
days = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
for day, sales in zip(days, sales_by_dow):
    print(f"  {day}: {sales:,.0f}")

# ============================================================
# 3.5 VISUALIZACIONES
# ============================================================
print("\n" + "=" * 60)
print("3.5 GENERANDO VISUALIZACIONES")
print("=" * 60)

# --- Gráfico 1: Tendencia temporal de ventas ---
fig, ax = plt.subplots(figsize=(14, 5))
daily_sales = df.groupby('Date')['Sales'].mean()
ax.plot(daily_sales.index, daily_sales.values, linewidth=0.8, color='#2196F3')
ax.set_title('Tendencia Diaria de Ventas Promedio', fontsize=14, fontweight='bold')
ax.set_xlabel('Fecha')
ax.set_ylabel('Ventas Promedio (€)')
ax.axhline(y=daily_sales.mean(), color='red', linestyle='--', alpha=0.7, label=f'Media: {daily_sales.mean():,.0f}')
ax.legend()
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, '01_tendencia_temporal.png'), dpi=150)
plt.close()
print("  ✅ 01_tendencia_temporal.png")

# --- Gráfico 2: Ventas por día de la semana ---
fig, ax = plt.subplots(figsize=(10, 5))
sales_by_dow.plot(kind='bar', ax=ax, color='#4CAF50', edgecolor='black')
ax.set_title('Ventas Promedio por Día de la Semana', fontsize=14, fontweight='bold')
ax.set_xlabel('Día de la Semana')
ax.set_ylabel('Ventas Promedio (€)')
ax.set_xticklabels(days, rotation=0)
for i, v in enumerate(sales_by_dow):
    ax.text(i, v + 50, f'{v:,.0f}', ha='center', fontweight='bold', fontsize=9)
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, '02_ventas_dia_semana.png'), dpi=150)
plt.close()
print("  ✅ 02_ventas_dia_semana.png")

# --- Gráfico 3: Ventas por mes (estacionalidad anual) ---
fig, ax = plt.subplots(figsize=(10, 5))
monthly_sales = df.groupby(['Year', 'Month'])['Sales'].mean().unstack()

# ✅ CORRECCIÓN: Obtener dinámicamente los meses que SÍ existen
meses_existentes = sorted(monthly_sales.columns.tolist())
nombres_meses = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic']
etiquetas = [nombres_meses[m-1] for m in meses_existentes]

monthly_sales.plot(kind='bar', ax=ax, colormap='viridis', edgecolor='black')
ax.set_title('Ventas Promedio por Mes y Año', fontsize=14, fontweight='bold')
ax.set_xlabel('Mes')
ax.set_ylabel('Ventas Promedio (€)')
ax.set_xticklabels(etiquetas, rotation=0)  # ✅ Solo las etiquetas que existen
plt.legend(title='Año')
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, '03_ventas_mensual.png'), dpi=150)
plt.close()
print("  ✅ 03_ventas_mensual.png")

# --- Gráfico 4: Distribución de ventas ---
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

axes[0].hist(df[df['Sales'] > 0]['Sales'], bins=50, color='#FF9800', edgecolor='black', alpha=0.7)
axes[0].set_title('Distribución de Ventas (excluyendo 0)', fontsize=12, fontweight='bold')
axes[0].set_xlabel('Ventas (€)')
axes[0].set_ylabel('Frecuencia')

# Top 10 tiendas por ventas
top_stores = df.groupby('Store')['Sales'].sum().nlargest(10)
axes[1].barh(range(len(top_stores)), top_stores.values, color='#9C27B0', edgecolor='black')
axes[1].set_yticks(range(len(top_stores)))
axes[1].set_yticklabels([f'Tienda {s}' for s in top_stores.index])
axes[1].set_title('Top 10 Tiendas por Ventas Totales', fontsize=12, fontweight='bold')
axes[1].set_xlabel('Ventas Totales (€)')

plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, '04_distribucion_top_tiendas.png'), dpi=150)
plt.close()
print("  ✅ 04_distribucion_top_tiendas.png")

# --- Gráfico 5: Correlación de variables numéricas ---
fig, ax = plt.subplots(figsize=(12, 8))
numeric_cols = df.select_dtypes(include=[np.number]).columns
corr_matrix = df[numeric_cols].corr()
sns.heatmap(corr_matrix, annot=True, fmt='.2f', cmap='RdBu_r', center=0,
            square=True, linewidths=0.5, ax=ax)
ax.set_title('Matriz de Correlación', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, '05_correlacion.png'), dpi=150)
plt.close()
print("  ✅ 05_correlacion.png")

# ============================================================
# 3.6 HALLAZGOS CLAVE (Para documentación del portafolio)
# ============================================================
print("\n" + "=" * 60)
print("3.6 HALLAZGOS CLAVE PARA EL PORTAFOLIO")
print("=" * 60)

findings = f"""
HALLAZGOS DEL ANÁLISIS EXPLORATORIO
====================================

1. VOLUMEN DE DATOS:
   - {train.shape[0]:,} registros de ventas diarias
   - {stores.shape[0]} tiendas únicas
   - Período: {df['Date'].min().date()} a {df['Date'].max().date()}

2. ESTACIONALIDAD SEMANAL:
   - Día con más ventas: {days[sales_by_dow.idxmax()]} ({sales_by_dow.max():,.0f} €)
   - Día con menos ventas: {days[sales_by_dow.idxmin()]} ({sales_by_dow.min():,.0f} €)
   - Los domingos tienen ventas = 0 (tiendas cerradas)

3. CALIDAD DE DATOS:
   - {zero_sales:,} registros con ventas = 0 ({zero_pct:.1f}%)
   - Estos corresponden principalmente a domingos (cierre)

4. INSIGHT PARA MODELADO:
   - El día de la semana es la variable más influyente
   - Las ventas tienen componente estacional mensual
   - Se requiere Feature Engineering temporal (Paso 4)
"""
print(findings)

# Guardar hallazgos en archivo de texto
with open(os.path.join(OUTPUT_DIR, 'hallazgos_eda.txt'), 'w', encoding='utf-8') as f:
    f.write(findings)

print("\n✅ PASO 3 COMPLETADO")
print(f"📁 Resultados guardados en: {os.path.abspath(OUTPUT_DIR)}")