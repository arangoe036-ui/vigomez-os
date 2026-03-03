import streamlit as st
import pandas as pd
from db import load_ventas

st.set_page_config(page_title="Dashboard de Ventas", layout="wide")

st.title("📈 Ventas Aisladas por Ciudad")
st.markdown("Comparativa de volumen y precio promedio por referencia en cada ciudad.")

df_ventas = load_ventas()

if not df_ventas.empty:
    # --- 1. FUNCIÓN PARA LIMPIAR DINERO ---
    # Esto elimina los $, puntos y comas para que Python pueda hacer la matemática real
    def limpiar_numero(val):
        if pd.isna(val): return 0.0
        if isinstance(val, (int, float)): return float(val)
        val_str = str(val).replace('$', '').replace('COP', '').replace(' ', '').strip()
        # Quitamos comas y puntos (asumiendo formato de pesos colombianos donde no hay centavos)
        val_str = val_str.replace(',', '').replace('.', '')
        try:
            return float(val_str)
        except:
            return 0.0

    # --- 2. DETECTOR DE COLUMNAS A PRUEBA DE BALAS ---
    cols_upper = {col.upper().strip(): col for col in df_ventas.columns}
    
    col_ciudad_candidates = ['CIUDAD', 'SEDE', 'SUCURSAL', 'UBICACION', 'ZONA', 'LUGAR', 'AGENCIA']
    col_ciudad = next((cols_upper[c] for c in cols_upper if any(cand in c for cand in col_ciudad_candidates)), None)
    
    col_fruta = next((cols_upper[c] for c in cols_upper if c in ['FRUTA', 'REFERENCIA', 'PRODUCTO', 'ARTICULO', 'VARIEDAD', 'ITEM']), df_ventas.columns[0])
    
    col_cajas_candidates = ['CAJA', 'CANTIDAD', 'QTY', 'VENDIDAS', 'VOLUMEN']
    col_cajas = next((cols_upper[c] for c in cols_upper if any(cand in c for cand in col_cajas_candidates)), None)
    
    col_ingreso_candidates = ['INGRESO', 'VENTA', 'TOTAL', 'VALOR', 'MONTO', 'REVENUE']
    col_ingreso = next((cols_upper[c] for c in cols_upper if any(cand in c for cand in col_ingreso_candidates)), None)
    
    col_precio_candidates = ['PRECIO', 'UNITARIO', 'PRICE']
    col_precio = next((cols_upper[c] for c in cols_upper if any(cand in c for cand in col_precio_candidates)), None)

    # --- 3. INTERFAZ DE EMERGENCIA ---
    if not col_ciudad:
        st.warning("⚠️ No pude detectar la columna de 'Ciudad' o 'Sede'.")
        col_ciudad = st.selectbox("Selecciona la columna que divide las ubicaciones (ej. Bogotá):", df_ventas.columns.tolist())

    if not col_cajas:
        st.warning("⚠️ No pude detectar la columna de 'Cajas'.")
        col_cajas = st.selectbox("Selecciona la columna de Cajas/Cantidades:", df_ventas.columns.tolist())

    if not col_ingreso and not col_precio:
        st.warning("⚠️ No pude detectar una columna de 'Ingresos' o 'Precio'.")
        col_ingreso = st.selectbox("Selecciona la columna de Ingresos Totales o Precio Unitario:", df_ventas.columns.tolist())

    # --- BLOQUEO DE SEGURIDAD ---
    if len({col_ciudad, col_fruta, col_cajas}) < 3:
        st.error("🛑 Esperando configuración: Por favor selecciona columnas distintas en los menús de arriba.")
        st.stop()

    st.divider()

    # --- 4. LIMPIEZA Y PROCESAMIENTO DE DATOS ---
    # Aplicamos la limpieza matemática estricta
    df_ventas[col_cajas] = df_ventas[col_cajas].apply(limpiar_numero)
    
    has_total_revenue = bool(col_ingreso)
    if has_total_revenue:
        df_ventas[col_ingreso] = df_ventas[col_ingreso].apply(limpiar_numero)
    elif col_precio:
        df_ventas[col_precio] = df_ventas[col_precio].apply(limpiar_numero)

    ciudades = sorted(df_ventas[col_ciudad].dropna().astype(str).unique())

    # --- 5. VISUALIZACIÓN POR PESTAÑAS (TABS) ---
    tabs = st.tabs(ciudades)

    for i, ciudad in enumerate(ciudades):
        with tabs[i]:
            df_ciudad = df_ventas[df_ventas[col_ciudad].astype(str) == ciudad]
            total_cajas_ciudad = df_ciudad[col_cajas].sum()
            
            st.markdown(f"### 📍 {ciudad}")
            st.metric("📦 Total Cajas Vendidas", f"{total_cajas_ciudad:,.0f}")
            
            # --- MATEMÁTICA DEL PRECIO PROMEDIO ---
            if has_total_revenue:
                df_grouped = df_ciudad.groupby(col_fruta).agg(
                    Cajas_Vendidas=(col_cajas, 'sum'),
                    Ingreso_Total=(col_ingreso, 'sum')
                ).reset_index()
                
                # Dividir el Ingreso Total / Cajas para obtener el valor real por caja
                df_grouped['Precio_Promedio'] = df_grouped.apply(
                    lambda row: row['Ingreso_Total'] / row['Cajas_Vendidas'] if row['Cajas_Vendidas'] > 0 else 0, 
                    axis=1
                )
                df_display = df_grouped[[col_fruta, 'Cajas_Vendidas', 'Precio_Promedio']].copy()
                
            elif col_precio:
                df_grouped = df_ciudad.groupby(col_fruta).agg(
                    Cajas_Vendidas=(col_cajas, 'sum'),
                    Precio_Promedio=(col_precio, 'mean')
                ).reset_index()
                df_display = df_grouped.copy()

            df_display.columns = ['Referencia (Fruta)', 'Cajas Vendidas', 'Precio Promedio ($)']
            df_display = df_display.sort_values(by='Cajas Vendidas', ascending=False)
            
            # Formatear visualmente a pesos ($) en la tabla final
            st.dataframe(
                df_display.style.format({
                    'Cajas Vendidas': "{:,.0f}",
                    'Precio Promedio ($)': "${:,.0f}" 
                }),
                use_container_width=True,
                hide_index=True
            )

else:
    st.warning("No hay datos de Ventas disponibles. Por favor, sube el archivo correspondiente en la barra lateral.")
