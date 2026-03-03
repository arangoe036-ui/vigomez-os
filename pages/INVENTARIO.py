import streamlit as st
import pandas as pd
from db import load_kardex

st.set_page_config(page_title="Inventario Kardex", layout="wide")

st.title("📦 Inventario Actual (Kardex)")
st.markdown("Vista detallada del stock físico vs. tránsito.")

df_kardex = load_kardex()

if not df_kardex.empty:
    # --- 1. BULLETPROOF COLUMN DETECTOR ---
    cols_upper = {col.upper().strip(): col for col in df_kardex.columns}
    
    col_fruta = next((cols_upper[c] for c in cols_upper if c in ['FRUTA', 'FRUITS', 'FRUIT_CATEGORY', 'PRODUCTO', 'ARTICULO', 'VARIEDAD', 'DESCRIPCION']), df_kardex.columns[0])
    
    col_bodega_candidates = ['BODEGA', 'SEDE', 'UBICACION', 'UBICACIÓN', 'LOCATION', 'SUCURSAL', 'ALMACEN', 'CENTRO', 'LUGAR', 'CIUDAD']
    col_bodega = next((cols_upper[c] for c in cols_upper if any(cand in c for cand in col_bodega_candidates)), None)
    
    col_cajas_candidates = ['CAJA', 'STOCK', 'CANTIDAD', 'SALDO', 'QTY', 'QUANTITY', 'INVENTARIO']
    col_cajas = next((cols_upper[c] for c in cols_upper if any(cand in c for cand in col_cajas_candidates)), None)

    # --- FAIL-SAFE UI ---
    if not col_bodega:
        st.warning("⚠️ No pude detectar automáticamente la columna de 'Bodega' o 'Sede'.")
        col_bodega = st.selectbox("Por favor, selecciona la columna que contiene las ubicaciones (ej. BOGOTAC):", df_kardex.columns.tolist())

    if not col_cajas:
        st.warning("⚠️ No pude detectar automáticamente la columna de 'Cajas/Cantidades'.")
        col_cajas = st.selectbox("Por favor, selecciona la columna que contiene las cantidades/cajas:", df_kardex.columns.tolist())

    # --- NEW SAFETY LOCK ---
    # Stops the app from crashing if the user hasn't picked distinct columns yet
    if col_bodega == col_fruta or col_cajas == col_fruta or col_bodega == col_cajas:
        st.error("🛑 Esperando configuración: Usa los menús desplegables de arriba para seleccionar las columnas correctas de Ubicación y Cantidad.")
        st.stop()

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
        st.markdown(f"**2. Filtrar por {col_bodega}**")
        todas_bodegas = st.checkbox("✅ Todas las Bodegas", value=True)
        if todas_bodegas:
            bodegas_seleccionadas = df_kardex[col_bodega].dropna().unique()
        else:
            bodegas_seleccionadas = st.multiselect(
                "Selecciona bodegas:", 
                options=sorted(df_kardex[col_bodega].dropna().astype(str).unique()),
                default=[]
            )

    # --- 3. APPLY FILTERS ---
    mask = df_kardex[col_fruta].isin(frutas_seleccionadas) & df_kardex[col_bodega].isin(bodegas_seleccionadas)
    df_filtered = df_kardex[mask]

    st.divider()

    # --- 4. SEPARATE TRANSIT VS PHYSICAL ---
    mask_transito = df_filtered[col_bodega].astype(str).str.contains('TRANSITO|TRÁNSITO|TRANS', case=False, na=False)
    
    df_transito = df_filtered[mask_transito]
    df_fisico = df_filtered[~mask_transito]

    # --- 5. HIGH-LEVEL METRICS ---
    total_fisico = pd.to_numeric(df_fisico[col_cajas], errors='coerce').sum()
    total_transito = pd.to_numeric(df_transito[col_cajas], errors='coerce').sum()

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
        pivot_fisico['TOTAL FÍSICO'] = pivot_fisico.sum(axis=1)
        
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
        
        st.dataframe(
            pivot_transito.style.format("{:,.0f}").background_gradient(cmap="Oranges", axis=None), 
            use_container_width=True
        )
    else:
        st.info("No hay stock en tránsito para estos filtros.")

else:
    st.warning("No hay datos de Inventario disponibles. Por favor, sube el archivo Kardex en la barra lateral.")
