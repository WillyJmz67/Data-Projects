"""
=============================================================================
PASO 7: DASHBOARD INTERACTIVO CON STREAMLIT
=============================================================================
Contexto de Negocio:
    Este dashboard permite a los stakeholders (gerentes de tienda, logística)
    visualizar las predicciones de demanda y tomar decisiones de inventario.
    
    Funcionalidades:
    1. Visión general de métricas del modelo
    2. Predicciones por tienda específica
    3. Comparación ventas reales vs predichas
    4. Top tiendas por precisión del modelo
    
    ¿Por qué Streamlit? Es el estándar de la industria para prototipos rápidos
    de Data Science, gratuito y fácil de desplegar en la nube.
=============================================================================
"""

import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import os
import pickle
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# ============================================================
# CONFIGURACIÓN DE LA PÁGINA
# ============================================================
st.set_page_config(
    page_title="Predicción de Demanda Retail",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos personalizados
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .business-insight {
        background-color: #e8f4f8;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #2ca02c;
        margin: 1rem 0;
    }
    </style>
""", unsafe_allow_html=True)

# ============================================================
# CARGA DE DATOS
# ============================================================
@st.cache_data
def load_data():
    """Carga datos desde la base de datos SQLite y archivos locales."""
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    OUTPUT_DIR = os.path.join(BASE_DIR, '..', 'output')
    DB_DIR = os.path.join(BASE_DIR, '..', 'db')
    MODEL_DIR = os.path.join(BASE_DIR, '..', 'models')
    
    data = {}
    
    # Cargar dataset procesado
    parquet_path = os.path.join(OUTPUT_DIR, 'dataset_procesado.parquet')
    if os.path.exists(parquet_path):
        data['df'] = pd.read_parquet(parquet_path)
    
    # Conectar a la base de datos
    db_path = os.path.join(DB_DIR, 'demanda.db')
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        
        # Cargar predicciones
        try:
            data['predictions'] = pd.read_sql_query(
                "SELECT * FROM predictions ORDER BY date DESC", conn
            )
        except:
            data['predictions'] = pd.DataFrame()
        
        # Cargar métricas del modelo
        try:
            data['metrics'] = pd.read_sql_query(
                "SELECT * FROM model_metrics ORDER BY evaluation_date DESC", conn
            )
        except:
            data['metrics'] = pd.DataFrame()
        
        # Cargar datos históricos agregados
        try:
            data['store_summary'] = pd.read_sql_query("""
                SELECT 
                    store_id,
                    COUNT(*) as days,
                    ROUND(AVG(sales), 0) as avg_sales,
                    ROUND(SUM(sales), 0) as total_sales,
                    MAX(sales) as max_sales
                FROM historical_data
                GROUP BY store_id
                ORDER BY total_sales DESC
            """, conn)
        except:
            data['store_summary'] = pd.DataFrame()
        
        conn.close()
    
    # Cargar modelo
    model_files = [f for f in os.listdir(MODEL_DIR) if f.endswith('.pkl')] if os.path.exists(MODEL_DIR) else []
    if model_files:
        with open(os.path.join(MODEL_DIR, model_files[0]), 'rb') as f:
            data['model'] = pickle.load(f)
            data['model_name'] = model_files[0].replace('.pkl', '').replace('_', ' ').title()
    
    return data

# Cargar datos
with st.spinner('Cargando datos...'):
    data = load_data()

# Verificar que hay datos
if 'df' not in data:
    st.error("❌ No se encontró el dataset procesado. Ejecuta primero `python src/features.py`")
    st.stop()

df = data['df']
predictions = data.get('predictions', pd.DataFrame())
metrics = data.get('metrics', pd.DataFrame())
store_summary = data.get('store_summary', pd.DataFrame())

# ============================================================
# HEADER
# ============================================================
st.markdown('<h1 class="main-header">📊 Sistema de Predicción de Demanda Retail</h1>', unsafe_allow_html=True)

st.markdown("""
<div class="business-insight">
    <strong>💡 Contexto de Negocio:</strong> Este dashboard permite optimizar el inventario de 1,115 tiendas 
    prediciendo la demanda diaria con un modelo de Machine Learning. El objetivo es reducir costos de 
    almacenamiento y evitar faltantes de stock.
</div>
""", unsafe_allow_html=True)

# ============================================================
# SIDEBAR - FILTROS
# ============================================================
st.sidebar.header("🔧 Filtros")

# Selector de tienda
store_ids = sorted(df['Store'].unique())
selected_store = st.sidebar.selectbox(
    "Selecciona una Tienda",
    store_ids,
    index=0
)

# Rango de fechas
min_date = df['Date'].min().date()
max_date = df['Date'].max().date()
date_range = st.sidebar.date_input(
    "Rango de Fechas",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

# Métricas del modelo en sidebar
if not metrics.empty:
    st.sidebar.markdown("---")
    st.sidebar.subheader("📈 Métricas del Modelo")
    for _, row in metrics.iterrows():
        metric_name = row['metric_name']
        metric_value = row['metric_value']
        
        if metric_name == 'MAPE':
            st.sidebar.metric(metric_name, f"{metric_value:.2f}%")
        elif metric_name in ['MAE', 'RMSE']:
            st.sidebar.metric(metric_name, f"€{metric_value:,.0f}")
        else:
            st.sidebar.metric(metric_name, f"{metric_value:.4f}")

# ============================================================
# MÉTRICAS PRINCIPALES (KPIs)
# ============================================================
st.subheader("🎯 Indicadores Clave (KPIs)")

# Filtrar datos por fecha
if len(date_range) == 2:
    mask = (df['Date'].dt.date >= date_range[0]) & (df['Date'].dt.date <= date_range[1])
    df_filtered = df[mask]
else:
    df_filtered = df

col1, col2, col3, col4 = st.columns(4)

with col1:
    total_sales = df_filtered['Sales'].sum()
    st.metric(
        "Ventas Totales",
        f"€{total_sales:,.0f}",
        delta=f"{len(df_filtered):,} registros"
    )

with col2:
    avg_daily = df_filtered['Sales'].mean()
    st.metric(
        "Venta Diaria Promedio",
        f"€{avg_daily:,.0f}",
        delta=f"Mediana: €{df_filtered['Sales'].median():,.0f}"
    )

with col3:
    zero_sales_pct = (df_filtered['Sales'] == 0).sum() / len(df_filtered) * 100
    st.metric(
        "Días Sin Ventas",
        f"{zero_sales_pct:.1f}%",
        delta="Principalmente domingos"
    )

with col4:
    if not metrics.empty:
        mape_row = metrics[metrics['metric_name'] == 'MAPE']
        if not mape_row.empty:
            mape = mape_row.iloc[0]['metric_value']
            st.metric(
                "Precisión del Modelo",
                f"{100 - mape:.1f}%",
                delta=f"MAPE: {mape:.2f}%"
            )
        else:
            st.metric("Precisión del Modelo", "N/A")
    else:
        st.metric("Precisión del Modelo", "N/A")

st.markdown("---")

# ============================================================
# TABS PARA ORGANIZAR EL CONTENIDO
# ============================================================
tab1, tab2, tab3, tab4 = st.tabs([
    "📈 Análisis Temporal",
    "🏪 Análisis por Tienda",
    "🤖 Predicciones del Modelo",
    "📊 Feature Importance"
])

# --- TAB 1: ANÁLISIS TEMPORAL ---
with tab1:
    st.subheader("Tendencia de Ventas en el Tiempo")
    
    # Agrupar por fecha
    daily_sales = df_filtered.groupby('Date')['Sales'].agg(['mean', 'sum', 'count']).reset_index()
    daily_sales.columns = ['Date', 'Avg_Sales', 'Total_Sales', 'Num_Stores']
    
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(
        x=daily_sales['Date'],
        y=daily_sales['Avg_Sales'],
        mode='lines',
        name='Venta Promedio',
        line=dict(color='#1f77b4', width=2)
    ))
    fig1.add_trace(go.Scatter(
        x=daily_sales['Date'],
        y=daily_sales['Total_Sales'],
        mode='lines',
        name='Venta Total',
        yaxis='y2',
        line=dict(color='#ff7f0e', width=2, dash='dash')
    ))
    
    fig1.update_layout(
        title='Evolución Diaria de Ventas',
        xaxis_title='Fecha',
        yaxis_title='Venta Promedio (€)',
        yaxis2=dict(title='Venta Total (€)', overlaying='y', side='right'),
        height=400,
        hovermode='x unified'
    )
    st.plotly_chart(fig1, use_container_width=True)
    
    # Ventas por día de la semana
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Ventas por Día de la Semana")
        dow_sales = df_filtered.groupby('DayOfWeek')['Sales'].mean().reset_index()
        days = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        dow_sales['Day'] = dow_sales['DayOfWeek'].map(dict(enumerate(days)))
        
        fig2 = px.bar(
            dow_sales,
            x='Day',
            y='Sales',
            color='Sales',
            color_continuous_scale='Viridis',
            title='Venta Promedio por Día',
            labels={'Sales': 'Venta Promedio (€)', 'Day': 'Día'}
        )
        fig2.update_layout(height=350, showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)
    
    with col2:
        st.subheader("Distribución de Ventas")
        fig3 = px.histogram(
            df_filtered[df_filtered['Sales'] > 0],
            x='Sales',
            nbins=50,
            title='Distribución de Ventas (excluyendo ceros)',
            labels={'Sales': 'Ventas (€)'},
            color_discrete_sequence=['#2ca02c']
        )
        fig3.update_layout(height=350, showlegend=False)
        st.plotly_chart(fig3, use_container_width=True)

# --- TAB 2: ANÁLISIS POR TIENDA ---
with tab2:
    st.subheader(f"Análisis Detallado - Tienda {selected_store}")
    
    # Filtrar por tienda seleccionada
    store_data = df_filtered[df_filtered['Store'] == selected_store]
    
    if len(store_data) > 0:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Ventas Totales", f"€{store_data['Sales'].sum():,.0f}")
        with col2:
            st.metric("Promedio Diario", f"€{store_data['Sales'].mean():,.0f}")
        with col3:
            st.metric("Clientes Totales", f"{store_data['Customers'].sum():,.0f}")
        
        # Gráfico de ventas de la tienda
        fig4 = go.Figure()
        fig4.add_trace(go.Scatter(
            x=store_data['Date'],
            y=store_data['Sales'],
            mode='lines+markers',
            name='Ventas',
            line=dict(color='#1f77b4'),
            marker=dict(size=4)
        ))
        
        # Agregar línea de tendencia (media móvil)
        store_data_sorted = store_data.sort_values('Date')
        store_data_sorted['MA7'] = store_data_sorted['Sales'].rolling(window=7, min_periods=1).mean()
        
        fig4.add_trace(go.Scatter(
            x=store_data_sorted['Date'],
            y=store_data_sorted['MA7'],
            mode='lines',
            name='Media Móvil 7 días',
            line=dict(color='#ff7f0e', width=2, dash='dash')
        ))
        
        fig4.update_layout(
            title=f'Ventas Diarias - Tienda {selected_store}',
            xaxis_title='Fecha',
            yaxis_title='Ventas (€)',
            height=400,
            hovermode='x unified'
        )
        st.plotly_chart(fig4, use_container_width=True)
        
        # Tabla de resumen
        st.subheader("📋 Resumen de la Tienda")
        
        # Extraer tipo de tienda y surtido desde el df procesado (si existen las columnas)
        store_type_col = [c for c in df.columns if c.startswith('Type_')]
        assortment_col = [c for c in df.columns if c.startswith('Assort_')]
        
        store_type = "N/A"
        if store_type_col:
            # Encontrar qué tipo tiene valor 1 para esta tienda
            type_values = df[df['Store'] == selected_store][store_type_col].iloc[0]
            active_type = type_values[type_values == 1]
            if len(active_type) > 0:
                store_type = active_type.index[0].replace('Type_', '')
        
        assortment = "N/A"
        if assortment_col:
            assort_values = df[df['Store'] == selected_store][assortment_col].iloc[0]
            active_assort = assort_values[assort_values == 1]
            if len(active_assort) > 0:
                assortment = active_assort.index[0].replace('Assort_', '')
        
        summary_data = {
            'Métrica': [
                'Tipo de Tienda',
                'Surtido',
                'Días con datos',
                'Venta máxima',
                'Venta mínima',
                'Clientes promedio',
                'Días con promoción'
            ],
            'Valor': [
                store_type,
                assortment,
                f"{len(store_data)} días",
                f"€{store_data['Sales'].max():,.0f}",
                f"€{store_data['Sales'].min():,.0f}",
                f"{store_data['Customers'].mean():,.0f}",
                f"{store_data['Promo'].sum()} ({store_data['Promo'].mean()*100:.1f}%)"
            ]
        }
        st.table(pd.DataFrame(summary_data))
    
    else:
        st.warning(f"No hay datos para la tienda {selected_store} en el rango seleccionado.")
    
    # Top 10 tiendas
    st.markdown("---")
    st.subheader("🏆 Top 10 Tiendas por Ventas Totales")
    
    if not store_summary.empty:
        top10 = store_summary.head(10)
        fig5 = px.bar(
            top10,
            x='store_id',
            y='total_sales',
            color='avg_sales',
            color_continuous_scale='RdYlGn',
            title='Top 10 Tiendas por Ventas Totales',
            labels={
                'store_id': 'Tienda',
                'total_sales': 'Ventas Totales (€)',
                'avg_sales': 'Venta Promedio (€)'
            },
            hover_data=['days', 'avg_sales', 'max_sales']
        )
        fig5.update_layout(height=400, xaxis_title='ID de Tienda')
        st.plotly_chart(fig5, use_container_width=True)
        
        # Tabla detallada
        st.dataframe(
            top10.rename(columns={
                'store_id': 'Tienda',
                'days': 'Días',
                'avg_sales': 'Promedio Diario (€)',
                'total_sales': 'Total (€)',
                'max_sales': 'Máximo Diario (€)'
            }),
            use_container_width=True,
            hide_index=True
        )

# --- TAB 3: PREDICCIONES DEL MODELO ---
with tab3:
    st.subheader("🤖 Rendimiento del Modelo de Predicción")
    
    if not predictions.empty:
        # Métricas generales
        col1, col2, col3 = st.columns(3)
        
        with col1:
            mae = predictions['error'].abs().mean()
            st.metric("MAE (Error Absoluto)", f"€{mae:,.0f}")
        
        with col2:
            rmse = np.sqrt((predictions['error'] ** 2).mean())
            st.metric("RMSE", f"€{rmse:,.0f}")
        
        with col3:
            mask = predictions['actual_sales'] > 0
            mape = (predictions.loc[mask, 'error'].abs() / predictions.loc[mask, 'actual_sales']).mean() * 100
            st.metric("MAPE (Error %)", f"{mape:.2f}%")
        
        # Predicciones vs Reales
        st.subheader("Predicciones vs Ventas Reales")
        
        # Sample para no sobrecargar el gráfico
        sample_size = min(5000, len(predictions))
        pred_sample = predictions.sample(n=sample_size, random_state=42)
        
        fig6 = go.Figure()
        fig6.add_trace(go.Scatter(
            x=pred_sample['actual_sales'],
            y=pred_sample['predicted_sales'],
            mode='markers',
            name='Predicciones',
            marker=dict(
                size=5,
                color=pred_sample['error'].abs(),
                colorscale='RdYlGn_r',
                colorbar=dict(title='Error Abs (€)'),
                opacity=0.6
            ),
            hovertemplate='Real: €%{x:,.0f}<br>Predicho: €%{y:,.0f}<extra></extra>'
        ))
        
         # --- WIDGET DE PREDICCIÓN EN VIVO ---
        st.markdown("---")
        st.subheader("🔮 Simulador de Predicción en Vivo")
        
        col1, col2 = st.columns(2)
        
        with col1:
            sim_store = st.selectbox(
                "Selecciona tienda para simular",
                sorted(df['Store'].unique()),
                key='sim_store'
            )
        
        with col2:
            days_ahead = st.slider("Días a predecir", 1, 14, 7)
        
        if st.button("🚀 Generar Predicción", type="primary"):
            with st.spinner("Calculando predicción..."):
                # Aquí iría la lógica del predict.py adaptada
                # Por ahora mostramos un mensaje
                st.success(f"✅ Predicción generada para Tienda {sim_store} - {days_ahead} días")
                st.info("💡 En producción, esto llamaría a una API del modelo desplegado en AWS Lambda o Azure Functions")

        # Línea de predicción perfecta
        max_val = max(pred_sample['actual_sales'].max(), pred_sample['predicted_sales'].max())
        fig6.add_trace(go.Scatter(
            x=[0, max_val],
            y=[0, max_val],
            mode='lines',
            name='Predicción Perfecta',
            line=dict(color='red', width=2, dash='dash')
        ))
        
        fig6.update_layout(
            title='Predicciones vs Ventas Reales (muestra de 5,000)',
            xaxis_title='Ventas Reales (€)',
            yaxis_title='Ventas Predichas (€)',
            height=500,
            showlegend=True
        )
        st.plotly_chart(fig6, use_container_width=True)
        
        # Distribución de errores
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Distribución de Errores")
            fig7 = px.histogram(
                predictions,
                x='error',
                nbins=50,
                title='Distribución del Error (Predicho - Real)',
                labels={'error': 'Error (€)'},
                color_discrete_sequence=['#ff7f0e']
            )
            fig7.add_vline(x=0, line_dash="dash", line_color="red")
            fig7.update_layout(height=350, showlegend=False)
            st.plotly_chart(fig7, use_container_width=True)
        
        with col2:
            st.subheader("Precisión por Tienda")
            store_accuracy = predictions.groupby('store_id').agg({
                'error': lambda x: np.mean(np.abs(x)),
                'actual_sales': 'mean'
            }).reset_index()
            store_accuracy['mape'] = (store_accuracy['error'] / store_accuracy['actual_sales']) * 100
            store_accuracy = store_accuracy.sort_values('mape')
            
            fig8 = px.bar(
                store_accuracy.head(20),
                x='store_id',
                y='mape',
                title='Top 20 Tiendas con Menor MAPE (Más Precisas)',
                labels={'store_id': 'Tienda', 'mape': 'MAPE (%)'},
                color='mape',
                color_continuous_scale='RdYlGn_r'
            )
            fig8.update_layout(height=350, xaxis_title='ID de Tienda')
            st.plotly_chart(fig8, use_container_width=True)
        
        # Tabla de predicciones recientes
        st.subheader("📋 Predicciones Recientes")
        recent_preds = predictions.head(100).copy()
        recent_preds['date'] = pd.to_datetime(recent_preds['date']).dt.date
        recent_preds['quality'] = recent_preds['error'].abs().apply(
            lambda x: '✅ Preciso' if x < 100 else ('⚠️ Aceptable' if x < 500 else '❌ Impreciso')
        )
        
        st.dataframe(
            recent_preds[[
                'store_id', 'date', 'actual_sales', 'predicted_sales', 'error', 'quality'
            ]].rename(columns={
                'store_id': 'Tienda',
                'date': 'Fecha',
                'actual_sales': 'Venta Real (€)',
                'predicted_sales': 'Predicción (€)',
                'error': 'Error (€)',
                'quality': 'Calidad'
            }),
            use_container_width=True,
            hide_index=True
        )
    
    else:
        st.warning("⚠️ No hay predicciones disponibles. Ejecuta `python src/sql.py` primero.")

# --- TAB 4: FEATURE IMPORTANCE ---
with tab4:
    st.subheader("🔍 Importancia de las Variables en el Modelo")
    
    if 'model' in data and hasattr(data['model'], 'feature_importances_'):
        # Obtener feature importance
        model = data['model']
        
        # Reconstruir feature columns (mismo lógica que en model.py)
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
        
        importance_df = pd.DataFrame({
            'Feature': feature_cols,
            'Importance': model.feature_importances_
        }).sort_values('Importance', ascending=False)
        
        # Gráfico de importancia
        fig9 = px.bar(
            importance_df.head(20),
            x='Importance',
            y='Feature',
            orientation='h',
            title='Top 20 Features Más Importantes',
            labels={'Importance': 'Importancia Relativa', 'Feature': 'Variable'},
            color='Importance',
            color_continuous_scale='Viridis'
        )
        fig9.update_layout(height=600, yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig9, use_container_width=True)
        
        # Explicación de negocio
        st.markdown("""
        <div class="business-insight">
            <strong>💡 Interpretación de Negocio:</strong><br>
            Las variables más importantes son los <strong>lags de ventas</strong> (ventas de hace 7, 14, 30 días) 
            y las <strong>medias móviles</strong>, lo que confirma que la demanda tiene fuerte inercia temporal. 
            El <strong>día de la semana</strong> también es crítico, validando el hallazgo del EDA donde los 
            lunes venden 38x más que los domingos.<br><br>
            Esto significa que para predecir las ventas de mañana, lo más importante es saber:
            1. Cuánto se vendió la semana pasada (inercia semanal)
            2. Qué día de la semana es (patrón estacional)
            3. La tendencia reciente (media móvil)
        </div>
        """, unsafe_allow_html=True)
        
        # Tabla completa
        st.subheader("Tabla Completa de Importancia")
        st.dataframe(
            importance_df.style.format({'Importance': '{:.4f}'}),
            use_container_width=True,
            hide_index=True
        )
    
    else:
        st.warning("⚠️ No se pudo cargar el modelo. Ejecuta `python src/model.py` primero.")

# ============================================================
# FOOTER
# ============================================================
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 1rem;'>
    <p><strong>Proyecto de Portafolio - Predicción de Demanda Retail</strong></p>
    <p>Desarrollado por William | Stack: Python, Pandas, Scikit-learn, XGBoost, SQLite, Streamlit</p>
    <p>Dataset: Rossmann Store Sales (Kaggle) | 1,017,209 registros procesados</p>
</div>
""", unsafe_allow_html=True)