import streamlit as st
import pandas as pd
from db import load_kardex
from sidebar import render_sidebar
render_sidebar()

st.set_page_config(page_title="Inventario Kardex", layout="wide")
st.title("🏭 Inventario Actual (Kardex)")

master_kardex_df = load_kardex()

if master_kardex_df.empty:
    st.info("No se encontró Kardex en la nube. Sube un archivo en la página principal.")
else:
    st.caption(f"Última actualización: {master_kardex_df['Last_Updated'].iloc[0] if 'Last_Updated' in master_kardex_df.columns else 'N/A'}")
    
    df_kardex = master_kardex_df.copy()
    
    # 1. Identify Physical Warehouses vs Transit
    physical_wh = [col for col in ['BOGOTAT', 'BOGOTAC', 'VIGOMED', 'VIGOBAR', 'VIGOPAL', 'VIGOPER', 'YUMBO'] if col in df_kardex.columns]
    
    df_kardex['Total_Bodega'] = df_kardex[physical_wh].sum(axis=1)
    df_kardex['En_Transito'] = df_kardex['TRANSITO'] if 'TRANSITO' in df_kardex.columns else 0
    df_kardex['Total_General'] = df_kardex['TOTAL'] if 'TOTAL' in df_kardex.columns else df_kardex['Total_Bodega'] + df_kardex['En_Transito']

    # -------------------------------------------------------------------------
    # NEW VISUALIZATION: SEPARATE CHARTS PER WAREHOUSE WITH UNIQUE COLORS
    # -------------------------------------------------------------------------
    st.subheader("🗺️ Composición de Stock por Sede Física")
    st.markdown("Cajas disponibles de cada fruta, separadas por ubicación.")
    
    # Melt the data to make it easy to group
    melted_df = df_kardex.melt(
        id_vars=['Fruit_Category'], 
        value_vars=physical_wh, 
        var_name='Bodega', 
        value_name='Cajas'
    )
    
    # Group by Bodega and Fruit Category
    bodega_composition = melted_df.groupby(['Bodega', 'Fruit_Category'])['Cajas'].sum().reset_index()
    bodega_composition = bodega_composition[bodega_composition['Cajas'] > 0] # Remove empty stock

    # Create a grid layout (3 charts per row)
    active_warehouses = bodega_composition['Bodega'].unique()
    cols = st.columns(3)
    
    for i, wh in enumerate(active_warehouses):
        wh_data = bodega_composition[bodega_composition['Bodega'] == wh]
        wh_data = wh_data.sort_values('Cajas', ascending=False)
        
        with cols[i % 3]:
            st.markdown(f"### 📍 {wh}")
            # By passing the DataFrame directly and setting color='Fruit_Category',
            # Streamlit will automatically assign a distinct color to each fruit!
            st.bar_chart(
                wh_data,
                x='Fruit_Category',
                y='Cajas',
                color='Fruit_Category',
                use_container_width=True
            )
            
    st.divider()

    # -------------------------------------------------------------------------
    # WAREHOUSE DRILL-DOWN & RAW DATA
    # -------------------------------------------------------------------------
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.markdown("### 🔍 Filtro Rápido")
        selected_wh = st.selectbox("Ver detalle de una bodega específica:", ["Todas"] + physical_wh)
        
    with col2:
        st.markdown("### 📦 Detalle por SKU")
        display_cols = ['Fruit_Category', 'FRUTA'] + physical_wh + ['Total_Bodega', 'En_Transito', 'Total_General']
        grouped_view = df_kardex[display_cols].sort_values(['Fruit_Category', 'FRUTA'])
        
        # Filter logic if a specific warehouse is selected
        if selected_wh != "Todas":
            grouped_view = grouped_view[grouped_view[selected_wh] > 0]
            
        st.dataframe(
            grouped_view,
            column_config={
                "Fruit_Category": "Categoría",
                "FRUTA": "Código SKU",
                "Total_Bodega": st.column_config.NumberColumn("∑ Total Físico"),
                "En_Transito": st.column_config.NumberColumn("🚚 En Tránsito"),
                "Total_General": "Stock Total"
            },
            hide_index=True,
            use_container_width=True
        )