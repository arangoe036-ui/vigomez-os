import streamlit as st
import pandas as pd
from db import load_kardex

st.set_page_config(page_title="Inventario Kardex", layout="wide")

st.title("📦 Inventario Actual (Kardex)")
st.markdown("Vista detallada del stock físico vs. tránsito en formato tabla cruzada.")

df_kardex = load_kardex()

if not df_kardex.empty:
    # --- 1. SMART COLUMN DETECTOR ---
    # Detect Fruit column
    col_fruta = next((col for col in df_kardex.columns if col.upper() in ['FRUTA', 'FRUITS', 'FRUIT_CATEGORY', 'PRODUCTO', 'ARTICULO']), df_kardex.columns[0])
    
    # Detect Location/Bodega column
    col_bodega = next((col for col in df_kardex.columns if col.upper() in ['BODEGA', 'SEDE', 'UBICACION', 'LOCATION', 'SUCURSAL']), None)
    
    # Detect Quantity column
    col_cajas = next((col for col in df_kardex.columns if 'CAJA' in col.upper() or 'STOCK' in col.upper() or 'CANTIDAD' in col.upper() or 'SALDO' in col.upper()), None)

    if col_bodega and col_cajas:
        
        # --- 2. SEPARATE TRANSIT VS PHYSICAL ---
        # We look for the word "TRANSITO" in the Bodega/Location column to split the data
        mask_transito = df_kardex[col_bodega].astype(str).str.contains('TRANSITO|TRÁNSITO|TRANS', case=False, na=False)
        
        df_transito = df_kardex[mask_transito]
        df_fisico = df_kardex[~mask_transito]

        # --- 3. CALCULATE HIGH-LEVEL METRICS ---
        total_fisico = df_fisico[col_cajas].sum()
        total_transito = df_transito[col_cajas].sum()

        col1, col2 = st.columns(2)
        col1.metric("🏢 Total Stock Físico (Cajas)", f"{total_fisico:,.0f}")
        col2.metric("🚚 Total en Tránsito (Cajas)", f"{total_transito:,.0f}")

        st.divider()

        # --- 4. TABLE 1: PHYSICAL STOCK MATRIX ---
        st.subheader("🏢 Composición de Stock Físico por Sede")
        if not df_fisico.empty:
            # Create an Excel-style pivot table
            pivot_fisico = pd.pivot_table(
                df_fisico, 
                values=col_cajas, 
                index=col_fruta, 
                columns=col_bodega, 
                aggfunc='sum', 
                fill_value=0
            )
            # Add a master Total column on the far right
            pivot_fisico['TOTAL FÍSICO'] = pivot_fisico.sum(axis=1)
            
            # Display it cleanly in Streamlit, formatting numbers with commas
            st.dataframe(pivot_fisico.style.format("{:,.0f}"), use_container_width=True)
        else:
            st.info("No hay stock físico registrado.")

        st.divider()

        # --- 5. TABLE 2: TRANSIT STOCK MATRIX ---
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
            st.dataframe(pivot_transito.style.format("{:,.0f}"), use_container_width=True)
        else:
            st.info("No hay stock en tránsito en este momento.")

    else:
        st.warning("No se pudieron detectar las columnas de Bodega o Cajas. Mostrando tabla general cruda:")
        st.dataframe(df_kardex, use_container_width=True)
        
else:
    st.warning("No hay datos de Inventario disponibles. Por favor, sube el archivo Kardex en la barra lateral.")
