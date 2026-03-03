import streamlit as st
import pandas as pd
from db import load_ventas

st.set_page_config(page_title="Dashboard de Ventas", layout="wide")

st.title("📈 Ventas Aisladas por Ciudad")
st.markdown("Comparativa de volumen y precio promedio por referencia en cada ciudad.")

df_ventas = load_ventas()

if not df_ventas.empty:
    # --- 1. FUNCIÓN PARA LIMPIAR DINERO ---
    def limpiar_numero(val):
        if pd.isna(val): return 0.0
        if isinstance(val, (int, float)): return float(val)
        val_str = str(val).replace('$', '').replace('COP', '').replace(' ', '').strip()
        val_str = val_str.replace(',', '').replace('.', '')
        try:
            return float(val_str)
        except:
            return 0.0

    # --- 2. COLUMNAS EXACTAS (SIN DROPDOWNS) ---
    col_ciudad = 'Bodega'
    col_fruta = 'FRUTA'
    col_cajas = 'Total_Cajas_Vendidas'
    col_dinero = 'Valor_Total_Ventas'

    st.divider()

    # --- 3. LIMPIEZA Y PROCESAMIENTO ---
    # Convertimos los textos a números reales para poder dividir
    if col_cajas in df_ventas.columns and col_dinero in df_ventas.columns:
        df_ventas[col_cajas] = df_ventas[col_cajas].apply(limpiar_numero)
        df_ventas[col_dinero] = df_ventas[col_dinero].apply(limpiar_numero)
    else:
        st.error(f"Faltan columnas en tu archivo de ventas. Asegúrate de tener: '{col_cajas}' y '{col_dinero}'.")
        st.stop()

    ciudades = sorted(df_ventas[col_ciudad].dropna().astype(str).unique())

    # --- 4. TABS POR CIUDAD (BOGOTAC, VIGOMED, ETC.) ---
    if ciudades:
        tabs = st.tabs(ciudades)

        for i, ciudad in enumerate(ciudades):
            with tabs[i]:
                df_ciudad = df_ventas[df_ventas[col_ciudad].astype(str) == ciudad]
                total_cajas_ciudad = df_ciudad[col_cajas].sum()
                
                st.markdown(f"### 📍 {ciudad}")
                st.metric("📦 Total Cajas Vendidas", f"{total_cajas_ciudad:,.0f}")
                
                # Agrupar por fruta y calcular el precio promedio real
                df_grouped = df_ciudad.groupby(col_fruta).agg(
                    Cajas_Vendidas=(col_cajas, 'sum'),
                    Dinero_Total=(col_dinero, 'sum')
                ).reset_index()
                
                # Precio Promedio = Ingresos / Cajas
                df_grouped['Precio_Promedio'] = df_grouped.apply(
                    lambda row: row['Dinero_Total'] / row['Cajas_Vendidas'] if row['Cajas_Vendidas'] > 0 else 0, 
                    axis=1
                )
                
                # Ocultar el ingreso total (pedido del CEO) y mostrar la tabla final
                df_display = df_grouped[[col_fruta, 'Cajas_Vendidas', 'Precio_Promedio']].copy()
                df_display.columns = ['Referencia (Fruta)', 'Cajas Vendidas', 'Precio Promedio ($)']
                df_display = df_display.sort_values(by='Cajas Vendidas', ascending=False)
                
                st.dataframe(
                    df_display.style.format({
                        'Cajas Vendidas': "{:,.0f}",
                        'Precio Promedio ($)': "${:,.0f}" 
                    }),
                    use_container_width=True,
                    hide_index=True
                )
    else:
        st.warning("No se encontraron bodegas en el archivo.")

else:
    st.warning("No hay datos de Ventas disponibles. Por favor, sube el archivo correspondiente en la barra lateral.")
