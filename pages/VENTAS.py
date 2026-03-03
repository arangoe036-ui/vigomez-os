import streamlit as st
import pandas as pd
from db import load_kardex

st.set_page_config(page_title="Inventario Kardex", layout="wide")

st.title("📦 Inventario Actual (Kardex)")
st.markdown("Vista detallada del stock físico vs. tránsito.")

df_kardex = load_kardex()

if not df_kardex.empty:
    # --- 1. EXACT COLUMNS (NO GUESSING) ---
    col_fruta = 'FRUTA'
    sedes_fisicas = ['BOGOTAT', 'BOGOTAC', 'VIGOMED', 'VIGOBAR', 'VIGOPAL', 'VIGOPER', 'YUMBO']
    col_transito = 'TRANSITO'

    # Convertir a números para poder sumar
    columnas_numericas = sedes_fisicas + [col_transito, 'TOTAL']
    for col in columnas_numericas:
        if col in df_kardex.columns:
            df_kardex[col] = pd.to_numeric(df_kardex[col], errors='coerce').fillna(0)

    # --- 2. FILTRO DE FRUTA ÚNICAMENTE ---
    st.markdown("### ⚙️ Filtros de Inventario")
    todas_frutas = st.checkbox("✅ Todas las Frutas", value=True)
    
    if col_fruta in df_kardex.columns:
        if todas_frutas:
            frutas_seleccionadas = df_kardex[col_fruta].dropna().unique()
        else:
            frutas_seleccionadas = st.multiselect(
                "Selecciona frutas:", 
                options=sorted(df_kardex[col_fruta].dropna().astype(str).unique()),
                default=[]
            )
        df_filtered = df_kardex[df_kardex[col_fruta].isin(frutas_seleccionadas)].copy()
    else:
        st.error(f"No se encontró la columna '{col_fruta}'.")
        st.stop()

    st.divider()

    # --- 3. SEPARAR FÍSICO VS TRÁNSITO Y CALCULAR ---
    sedes_presentes = [col for col in sedes_fisicas if col in df_filtered.columns]
    
    # Calcular totales
    total_fisico = df_filtered[sedes_presentes].sum().sum() if sedes_presentes else 0
    total_transito = df_filtered[col_transito].sum() if col_transito in df_filtered.columns else 0

    m1, m2, m3 = st.columns(3)
    m1.metric("🏢 Total Stock Físico", f"{total_fisico:,.0f}")
    m2.metric("🚚 Total en Tránsito", f"{total_transito:,.0f}")
    m3.metric("📦 Inventario Total", f"{(total_fisico + total_transito):,.0f}")

    st.divider()

    # --- 4. TABLA 1: STOCK FÍSICO [cite: 25, 68] ---
    st.subheader("🏢 Composición de Stock Físico por Sede [cite: 28]")
    
    # Mostrar solo la fruta y las sedes físicas (BOGOTAC, YUMBO, etc.)
    df_fisico = df_filtered[[col_fruta] + sedes_presentes].copy()
    df_fisico['TOTAL FÍSICO'] = df_fisico[sedes_presentes].sum(axis=1)
    
    formato_fisico = {col: "{:,.0f}" for col in sedes_presentes + ['TOTAL FÍSICO']}
    st.dataframe(df_fisico.style.format(formato_fisico), use_container_width=True, hide_index=True)

    st.divider()

    # --- 5. TABLA 2: STOCK EN TRÁNSITO  ---
    st.subheader("🚚 Stock en Tránsito")
    if col_transito in df_filtered.columns:
        df_transito = df_filtered[[col_fruta, col_transito]].copy()
        
        # Ocultar filas que tengan 0 en tránsito para no ensuciar la vista
        df_transito = df_transito[df_transito[col_transito] > 0]
        
        if not df_transito.empty:
            st.dataframe(df_transito.style.format({col_transito: "{:,.0f}"}), use_container_width=True, hide_index=True)
        else:
            st.info("No hay inventario en tránsito para las frutas seleccionadas.")
    else:
        st.warning("No se encontró la columna 'TRANSITO'.")

else:
    st.warning("No hay datos de Inventario disponibles. Por favor, sube el archivo Kardex en la barra lateral.")
