import streamlit as st
import pandas as pd
from db import load_kardex

st.set_page_config(page_title="Inventario Kardex", layout="wide")

st.title("📦 Inventario Actual (Kardex)")

df_kardex = load_kardex()

if not df_kardex.empty:
    # 1. Detect Fruit Column
    col_fruta = next((col for col in df_kardex.columns if col.upper() in ['FRUTA', 'FRUITS', 'FRUIT_CATEGORY', 'PRODUCTO', 'VARIEDAD']), df_kardex.columns[0])

    # 2. Fruit Filter
    st.markdown("### ⚙️ Filtros de Inventario")
    todas_frutas = st.checkbox("✅ Todas las Frutas", value=True)
    if todas_frutas:
        frutas_seleccionadas = df_kardex[col_fruta].dropna().unique()
    else:
        frutas_seleccionadas = st.multiselect(
            "Selecciona frutas:", 
            options=sorted(df_kardex[col_fruta].dropna().astype(str).unique()),
            default=[]
        )

    # 3. Apply Filter
    df_filtered = df_kardex[df_kardex[col_fruta].isin(frutas_seleccionadas)]
    
    st.divider()

    # 4. Display the Clean Data Table
    st.subheader("📋 Datos de Inventario")
    st.dataframe(df_filtered, use_container_width=True)

else:
    st.warning("No hay datos de Inventario disponibles. Por favor, sube el archivo Kardex en la barra lateral.")
