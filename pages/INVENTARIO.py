import streamlit as st
import pandas as pd
from db import load_kardex

st.set_page_config(page_title="Inventario Kardex", layout="wide")

st.title("📦 Inventario Actual (Kardex)")
st.markdown("Vista detallada del stock físico vs. tránsito.")

df_kardex = load_kardex()

if not df_kardex.empty:
    # --- 1. SMART COLUMN DETECTOR ---
    col_fruta = next((col for col in df_kardex.columns if col.upper() in ['FRUTA', 'FRUITS', 'FRUIT_CATEGORY', 'PRODUCTO', 'ARTICULO']), df_kardex.columns[0])
    col_bodega = next((col for col in df_kardex.columns if col.upper() in ['BODEGA', 'SEDE', 'UBICACION', 'LOCATION', 'SUCURSAL']), None)
    col_cajas = next((col for col in df_kardex.columns if 'CAJA' in col.upper() or 'STOCK' in col.upper() or 'CANTIDAD' in col.upper() or 'SALDO' in col.upper()), None)

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
                options=sorted(df_kardex[col_fruta].dropna().unique()),
                default=[]
            )
            
    with col2:
        if col_bodega:
            st.markdown("**2. Filtrar por Bodega/Sede**")
            todas_bodegas = st.checkbox("✅ Todas las Bodegas", value=True)
            if todas_bodegas:
                bodegas_seleccionadas = df_kardex[col_bodega].dropna().unique()
            else:
                bodegas_seleccionadas = st.multiselect(
                    "Selecciona bodegas:", 
                    options=sorted(df_kardex[col_bodega].dropna().unique()),
                    default=[]
                )
        else:
            bodegas_seleccionadas = []

    # --- 3. APPLY FILTERS ---
    mask = df_kardex[col_fruta].isin(frutas_seleccionadas)
    if col_bodega:
        mask = mask & df_kardex[col_bodega].isin(bodegas_seleccionadas)
        
    df_filtered = df_kardex[mask]

    st.divider()

    if col_bodega and col_cajas:
        # --- 4. SEPARATE TRANSIT VS PHYSICAL ---
        mask_transito = df_filtered[col_bodega].astype(str).str.contains('TRANSITO|TRÁNSITO|TRANS', case=False, na=False)
        
        df_transito = df_filtered[mask_transito]
        df_fisico = df_filtered[~mask_transito]

        # --- 5. HIGH-LEVEL METRICS ---
        total_fisico = df_fisico[col_cajas].sum()
        total_transito = df_transito[col_cajas].sum()

        m1, m2, m3 = st.columns(3)
        m1.metric("🏢 Total Stock Físico (Cajas)", f"{total_fisico:,.0f}")
        m2.metric("🚚 Total en Tránsito (Cajas)", f"{total_transito:,.0f}")
        m3.metric("📦 Inventario Total (Físico + Tránsito)", f"{(total_fisico + total_transito):,.0f}")

        st.divider()

        # --- 6. TABLE 1: PHYSICAL STOCK MATRIX (WITH HEATMAP) ---
        st.subheader("🏢 Composición de Stock Físico por Sede")
        if not df_fisico.empty:
            pivot_fisico = pd.pivot_table(
                df_fisico, 
                values=col_cajas, 
                index=col_fruta, 
                columns=col_bodega, 
                aggfunc='sum', 
                fill_value=0
            )
            # Add a master Total column
            pivot_fisico['TOTAL FÍSICO'] = pivot_fisico.sum(axis=1)
            
            # Display it with a blue color gradient to highlight large quantities
            st.dataframe(
                pivot_fisico.style.format("{:,.0f}").background_gradient(cmap="Blues", axis=None), 
                use_container_width=True
            )
        else:
            st.info("No hay stock físico registrado para estos filtros.")

        st.divider()

        # --- 7. TABLE 2: TRANSIT STOCK MATRIX (WITH HEATMAP) ---
        st.subheader("🚚 Stock en Tránsito")
        if not df_transito.empty:
            pivot_transito = pd.pivot_table(
                df_transito, 
                values=col_cajas, 
                index=col_fruta, 
                columns=col_bodega, 
                aggfunc='sum', 
                fill_value=0
            )
            pivot_transito['TOTAL TRÁNSITO'] = pivot_transito.sum(axis=1)
            
            # Display it with an orange color gradient to visually separate it from physical stock
            st.dataframe(
                pivot_transito.style.format("{:,.0f}").background_gradient(cmap="Oranges", axis=None), 
                use_container_width=True
            )
        else:
            st.info("No hay stock en tránsito en este momento.")

    else:
        st.warning("No se pudieron detectar las columnas de Bodega o Cajas.")
        st.dataframe(df_filtered, use_container_width=True)
        
else:
    st.warning("No hay datos de Inventario disponibles. Por favor, sube el archivo Kardex en la barra lateral.")
