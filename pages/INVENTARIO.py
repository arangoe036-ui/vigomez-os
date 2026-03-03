import streamlit as st
import pandas as pd
from db import load_kardex

st.set_page_config(page_title="Inventario Kardex", layout="wide")

st.title("📦 Inventario Actual (Kardex)")
st.markdown("Vista detallada del stock físico vs. tránsito.")

df_kardex = load_kardex()

if not df_kardex.empty:
    # --- 1. DETECT THE COLUMNS ---
    # Find the Fruit column
    col_fruta = next((col for col in df_kardex.columns if col.upper() in ['FRUTA', 'FRUITS', 'FRUIT_CATEGORY', 'PRODUCTO', 'VARIEDAD', 'ARTICULO']), df_kardex.columns[0])

    # All other columns are assumed to be your Warehouse Locations (BOGOTAC, YUMBO, etc.)
    columnas_sedes = [col for col in df_kardex.columns if col != col_fruta]

    # --- 2. THE CEO FILTERS ---
    st.markdown("### ⚙️ Filtros de Inventario")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**1. Filtrar por Fruta**")
        todas_frutas = st.checkbox("✅ Todas las Frutas", value=True)
        if todas_frutas:
            frutas_seleccionadas = df_kardex[col_fruta].dropna().unique()
        else:
            frutas_seleccionadas = st.multiselect(
                "Selecciona frutas:", 
                options=sorted(df_kardex[col_fruta].dropna().astype(str).unique()),
                default=[]
            )
            
    with col2:
        st.markdown("**2. Filtrar por Sede (Ubicación)**")
        todas_sedes = st.checkbox("✅ Todas las Sedes", value=True)
        if todas_sedes:
            sedes_seleccionadas = columnas_sedes
        else:
            sedes_seleccionadas = st.multiselect(
                "Selecciona sedes (ej. BOGOTAC, YUMBO):", 
                options=columnas_sedes,
                default=[]
            )

    # --- 3. APPLY FILTERS ---
    # Filter the rows (Fruits)
    df_filtered = df_kardex[df_kardex[col_fruta].isin(frutas_seleccionadas)].copy()
    
    # Filter the columns (Locations) - Always keep the Fruit column, plus the selected locations
    columnas_finales = [col_fruta] + sedes_seleccionadas
    df_filtered = df_filtered[columnas_finales]

    st.divider()

    # --- 4. CALCULATE METRICS BASED ON SELECTED LOCATIONS ---
    if len(sedes_seleccionadas) > 0:
        # Separate Transit columns from Physical columns based on the word "TRANSITO"
        cols_transito = [col for col in sedes_seleccionadas if 'TRANS' in col.upper()]
        cols_fisico = [col for col in sedes_seleccionadas if col not in cols_transito]
        
        # Ensure all values are treated as numbers so we can do math
        for col in sedes_seleccionadas:
            df_filtered[col] = pd.to_numeric(df_filtered[col], errors='coerce').fillna(0)

        # Sum the totals
        total_fisico = df_filtered[cols_fisico].sum().sum() if cols_fisico else 0
        total_transito = df_filtered[cols_transito].sum().sum() if cols_transito else 0

        m1, m2, m3 = st.columns(3)
        m1.metric("🏢 Total Stock Físico (Seleccionado)", f"{total_fisico:,.0f}")
        m2.metric("🚚 Total en Tránsito (Seleccionado)", f"{total_transito:,.0f}")
        m3.metric("📦 Inventario Total", f"{(total_fisico + total_transito):,.0f}")
        
    st.divider()

    # --- 5. CLEAN DATA TABLE ---
    st.subheader("📋 Composición de Stock")
    # Format numbers with commas so it looks clean, no crash-prone formatting
    st.dataframe(
        df_filtered.style.format(formatter={col: "{:,.0f}" for col in sedes_seleccionadas}),
        use_container_width=True
    )

else:
    st.warning("No hay datos de Inventario disponibles. Por favor, sube el archivo Kardex en la barra lateral.")
