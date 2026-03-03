import streamlit as st
import pandas as pd
from db import load_ventas

st.set_page_config(page_title="Dashboard de Ventas", layout="wide")

st.title("📈 Ventas Aisladas por Ciudad")
st.markdown("Comparativa de volumen y precio promedio por referencia en cada ciudad.")

df_ventas = load_ventas()

if not df_ventas.empty:
    # --- 1. BULLETPROOF COLUMN DETECTOR ---
    cols_upper = {col.upper().strip(): col for col in df_ventas.columns}
    
    col_ciudad_candidates = ['CIUDAD', 'SEDE', 'SUCURSAL', 'UBICACION', 'ZONA', 'LUGAR']
    col_ciudad = next((cols_upper[c] for c in cols_upper if any(cand in c for cand in col_ciudad_candidates)), None)
    
    col_fruta = next((cols_upper[c] for c in cols_upper if c in ['FRUTA', 'REFERENCIA', 'PRODUCTO', 'ARTICULO', 'VARIEDAD']), df_ventas.columns[0])
    
    col_cajas_candidates = ['CAJA', 'CANTIDAD', 'QTY', 'VENDIDAS', 'VOLUMEN']
    col_cajas = next((cols_upper[c] for c in cols_upper if any(cand in c for cand in col_cajas_candidates)), None)
    
    # Look for Total Revenue or Unit Price to calculate the average
    col_ingreso_candidates = ['INGRESO', 'VENTA', 'TOTAL', 'VALOR', 'MONTO', 'REVENUE']
    col_ingreso = next((cols_upper[c] for c in cols_upper if any(cand in c for cand in col_ingreso_candidates)), None)
    
    col_precio_candidates = ['PRECIO', 'UNITARIO', 'PRICE']
    col_precio = next((cols_upper[c] for c in cols_upper if any(cand in c for cand in col_precio_candidates)), None)

    # --- FAIL-SAFE UI ---
    if not col_ciudad:
        st.warning("⚠️ No pude detectar la columna de 'Ciudad'.")
        col_ciudad = st.selectbox("Selecciona la columna de Ciudad (ej. Bogotá, Medellín):", df_ventas.columns.tolist())

    if not col_cajas:
        st.warning("⚠️ No pude detectar la columna de 'Cajas Vendidas'.")
        col_cajas = st.selectbox("Selecciona la columna de Cajas/Cantidades:", df_ventas.columns.tolist())

    if not col_ingreso and not col_precio:
        st.warning("⚠️ No pude detectar una columna de 'Ingresos' o 'Precio'.")
        col_ingreso = st.selectbox("Selecciona la columna de Ingresos Totales o Precio Unitario para calcular el promedio:", df_ventas.columns.tolist())

    # --- SAFETY LOCK ---
    if len({col_ciudad, col_fruta, col_cajas}) < 3:
        st.error("🛑 Esperando configuración: Por favor selecciona columnas distintas en los menús de arriba.")
        st.stop()

    st.divider()

    # --- 2. DATA PROCESSING ---
    # Ensure our math columns are actual numbers
    df_ventas[col_cajas] = pd.to_numeric(df_ventas[col_cajas], errors='coerce').fillna(0)
    
    # Determine how to calculate the average price
    has_total_revenue = bool(col_ingreso)
    if has_total_revenue:
        df_ventas[col_ingreso] = pd.to_numeric(df_ventas[col_ingreso], errors='coerce').fillna(0)
    elif col_precio:
        df_ventas[col_precio] = pd.to_numeric(df_ventas[col_precio], errors='coerce').fillna(0)

    # Get unique cities
    ciudades = sorted(df_ventas[col_ciudad].dropna().astype(str).unique())

    # --- 3. DISPLAY CITY BY CITY ---
    # We will use Streamlit Tabs so the CEO can easily flip between cities
    tabs = st.tabs(ciudades)

    for i, ciudad in enumerate(ciudades):
        with tabs[i]:
            # Filter data for just this city
            df_ciudad = df_ventas[df_ventas[col_ciudad].astype(str) == ciudad]
            
            # Total boxes for the city
            total_cajas_ciudad = df_ciudad[col_cajas].sum()
            
            st.markdown(f"### 📍 {ciudad}")
            st.metric("📦 Total Cajas Vendidas", f"{total_cajas_ciudad:,.0f}")
            
            # Group by Fruit to get total boxes and average price
            if has_total_revenue:
                # Weighted average: Total Revenue / Total Boxes
                df_grouped = df_ciudad.groupby(col_fruta).agg(
                    Cajas_Vendidas=(col_cajas, 'sum'),
                    Ingreso_Total=(col_ingreso, 'sum')
                ).reset_index()
                
                # Prevent division by zero
                df_grouped['Precio_Promedio'] = df_grouped.apply(
                    lambda row: row['Ingreso_Total'] / row['Cajas_Vendidas'] if row['Cajas_Vendidas'] > 0 else 0, 
                    axis=1
                )
                
                # Drop the total revenue column as requested by the CEO
                df_display = df_grouped[[col_fruta, 'Cajas_Vendidas', 'Precio_Promedio']].copy()
                
            elif col_precio:
                # If we only have unit prices, average them
                df_grouped = df_ciudad.groupby(col_fruta).agg(
                    Cajas_Vendidas=(col_cajas, 'sum'),
                    Precio_Promedio=(col_precio, 'mean')
                ).reset_index()
                df_display = df_grouped.copy()

            # Rename columns for a clean presentation
            df_display.columns = ['Referencia (Fruta)', 'Cajas Vendidas', 'Precio Promedio ($)']
            
            # Sort by highest volume
            df_display = df_display.sort_values(by='Cajas Vendidas', ascending=False)
            
            # Display as a clean table with currency formatting
            st.dataframe(
                df_display.style.format({
                    'Cajas Vendidas': "{:,.0f}",
                    'Precio Promedio ($)': "${:,.2f}"
                }),
                use_container_width=True,
                hide_index=True
            )

else:
    st.warning("No hay datos de Ventas disponibles. Por favor, sube el archivo correspondiente en la barra lateral.")
