import streamlit as st
import pandas as pd
from db import load_ventas, load_kardex
from sidebar import render_sidebar
render_sidebar()

st.set_page_config(page_title="Dashboard Ventas", layout="wide")
st.title("💸 Rendimiento Comercial y Correlación")

master_ventas_df = load_ventas()

# -----------------------------------------------------------------------------
# LOCATION TRANSLATION DICTIONARY
# -----------------------------------------------------------------------------
location_map = {
    'BOGOTAT': 'Bogotá',
    'BOGOTAC': 'Bogotá',
    'VIGOMED': 'Medellín',
    'VIGOBAR': 'Barranquilla',
    'VIGOPAL': 'Cali',
    'VIGOPER': 'Pereira',
    'YUMBO': 'Yumbo'
}

if master_ventas_df.empty:
    st.info("No hay datos de ventas en la nube. Sube los PDFs en la página principal.")
else:
    df_ventas = master_ventas_df.copy()
    
    # Automatically translate the internal warehouse codes to City Names
    df_ventas['Ciudad'] = df_ventas['Bodega'].map(location_map).fillna(df_ventas['Bodega'])
    
    # -------------------------------------------------------------------------
    # 1. NEW: MASTER COMPARISON CHART (NATIONAL)
    # -------------------------------------------------------------------------
    st.subheader("🏆 Comparativa Nacional")
    st.markdown("Comparación directa de rendimiento entre Bogotá, Medellín y Cali.")
    
    city_summary = df_ventas.groupby('Ciudad')[['Total_Cajas_Vendidas', 'Valor_Total_Ventas']].sum().reset_index()
    
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        st.markdown("**📦 Total Cajas Vendidas por Ciudad**")
        st.bar_chart(city_summary.set_index('Ciudad')['Total_Cajas_Vendidas'], color="#ffaa00")
        
    with col_m2:
        st.markdown("**💰 Ingresos Generados por Ciudad ($)**")
        st.bar_chart(city_summary.set_index('Ciudad')['Valor_Total_Ventas'], color="#0055ff")
        
    st.divider()

    # -------------------------------------------------------------------------
    # 2. RENDIMIENTO POR SEDE (SEPARATED FILES VIEW)
    # -------------------------------------------------------------------------
    st.subheader("📊 Ventas Aisladas por Ciudad (Semana Actual)")
    
    ciudades = df_ventas['Ciudad'].unique()
    cols = st.columns(len(ciudades))
    
    for i, ciudad in enumerate(ciudades):
        ciudad_data = df_ventas[df_ventas['Ciudad'] == ciudad]
        cajas = int(ciudad_data['Total_Cajas_Vendidas'].sum())
        ingresos = int(ciudad_data['Valor_Total_Ventas'].sum())
        
        with cols[i]:
            st.markdown(f"### 📍 {ciudad}")
            st.metric("Cajas Vendidas", f"{cajas:,}")
            st.metric("Ingresos Generados", f"${ingresos:,}")
            
            # Top selling fruit chart for this specific location
            top_fruits = ciudad_data.groupby('Fruit_Category')['Total_Cajas_Vendidas'].sum().sort_values(ascending=False)
            st.bar_chart(top_fruits, color="#2cb55e")
            
    st.divider()

    # -------------------------------------------------------------------------
    # 3. VISTA MAESTRA (CORRELATION MATRIX WITH "ESTANCADO" FIX)
    # -------------------------------------------------------------------------
    st.subheader("🧠 Matriz Maestra: Salud del Inventario")
    st.markdown("Compara a qué velocidad se vende la fruta a nivel nacional contra lo que hay físicamente en bodega.")
    
    master_kardex_df = load_kardex()
    if not master_kardex_df.empty:
        # Get total physical stock per SKU
        df_kardex = master_kardex_df.copy()
        physical_wh = [col for col in ['BOGOTAT', 'BOGOTAC', 'VIGOMED', 'VIGOBAR', 'VIGOPAL', 'VIGOPER', 'YUMBO'] if col in df_kardex.columns]
        df_kardex['Stock_Fisico'] = df_kardex[physical_wh].sum(axis=1)
        kardex_summary = df_kardex.groupby(['FRUTA', 'Fruit_Category'])['Stock_Fisico'].sum().reset_index()
        
        # Get total sales velocity per SKU
        ventas_summary = df_ventas.groupby('FRUTA')['Total_Cajas_Vendidas'].sum().reset_index()
        
        # Merge them together to find correlations
        correlation_df = pd.merge(kardex_summary, ventas_summary, on='FRUTA', how='left').fillna(0)
        
        # CALCULATE WEEKS OF STOCK (Fixing the Infinite Zero Issue)
        correlation_df['Semanas_Num'] = correlation_df.apply(
            lambda row: (row['Stock_Fisico'] / row['Total_Cajas_Vendidas']) if row['Total_Cajas_Vendidas'] > 0 else (999 if row['Stock_Fisico'] > 0 else 0), axis=1
        )
        
        # Sort by the hidden numeric value
        correlation_df = correlation_df.sort_values('Semanas_Num')
        
        # Create a clean, human-readable text column for the UI
        correlation_df['Estado_Cobertura'] = correlation_df.apply(
            lambda row: f"{round(row['Semanas_Num'], 1)} Semanas" if row['Semanas_Num'] not in [0, 999] else ("Agotado (0 Cajas)" if row['Semanas_Num'] == 0 else "⚠️ Estancado (Sin Ventas)"), axis=1
        )
        
        # Select and rename columns for a clean UI presentation
        display_df = correlation_df[['Fruit_Category', 'FRUTA', 'Stock_Fisico', 'Total_Cajas_Vendidas', 'Estado_Cobertura']]
        
        st.dataframe(
            display_df,
            column_config={
                "Fruit_Category": "Categoría",
                "FRUTA": "SKU",
                "Stock_Fisico": st.column_config.NumberColumn("Cajas en Inventario", format="%d"),
                "Total_Cajas_Vendidas": st.column_config.NumberColumn("Cajas Vendidas (Última Sem)", format="%d"),
                "Estado_Cobertura": "Estado de Cobertura"
            },
            hide_index=True,
            use_container_width=True
        )
