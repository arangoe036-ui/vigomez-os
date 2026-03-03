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

    # --- 2. DETECTOR DE COLUMNAS MEJORADO ---
    cols_upper = {col.upper().strip(): col for col in df_ventas.columns}
    
    col_ciudad_candidates = ['CIUDAD', 'BODEGA', 'SEDE', 'SUCURSAL', 'UBICACION', 'ZONA']
    col_ciudad = next((cols_upper[c] for c in cols_upper if any(cand in c for cand in col_ciudad_candidates)), None)
    
    col_fruta = next((cols_upper[c] for c in cols_upper if c in ['FRUTA', 'REFERENCIA', 'PRODUCTO', 'ARTICULO', 'VARIEDAD']), df_ventas.columns[0])
    
    col_cajas_candidates = ['CAJA', 'CANTIDAD', 'QTY', 'VOLUMEN']
    col_cajas = next((cols_upper[c] for c in cols_upper if any(cand in c for cand in col_cajas_candidates)), None)
    
    col_ingreso_candidates = ['INGRESO', 'VALOR', 'MONTO', 'REVENUE']
    col_ingreso = next((cols_upper[c] for c in cols_upper if any(cand in c for cand in col_ingreso_candidates)), None)

    # --- 3. PANEL DE CONFIGURACIÓN MANUAL ---
    st.markdown("### ⚙️ Configuración de Columnas")
    st.info("Revisa que el sistema haya seleccionado las columnas correctas para hacer la matemática.")
    
    c1, c2, c3, c4 = st.columns(4)
    
    with c1:
        opciones_ciudad = df_ventas.columns.tolist()
        idx_ciudad = opciones_ciudad.index(col_ciudad) if col_ciudad in opciones_ciudad else 0
        col_ciudad_sel = st.selectbox("1. Bodega/Ciudad:", opciones_ciudad, index=idx_ciudad)
        
    with c2:
        opciones_fruta = df_ventas.columns.tolist()
        idx_fruta = opciones_fruta.index(col_fruta) if col_fruta in opciones_fruta else 0
        col_fruta_sel = st.selectbox("2. Fruta:", opciones_fruta, index=idx_fruta)
        
    with c3:
        opciones_cajas = df_ventas.columns.tolist()
        idx_cajas = opciones_cajas.index(col_cajas) if col_cajas in opciones_cajas else 0
        col_cajas_sel = st.selectbox("3. Cajas Vendidas:", opciones_cajas, index=idx_cajas)
        
    with c4:
        opciones_dinero = ['Ninguna'] + df_ventas.columns.tolist()
        idx_dinero = opciones_dinero.index(col_ingreso) if col_ingreso in opciones_dinero else 0
        col_dinero_sel = st.selectbox("4. Ingresos Totales:", opciones_dinero, index=idx_dinero)

    # --- BLOQUEOS DE SEGURIDAD PARA EVITAR EL BUG DEL 1.0 ---
    if col_cajas_sel == col_dinero_sel and col_dinero_sel != 'Ninguna':
        st.error("🛑 ERROR: Has seleccionado la misma columna para 'Cajas' y para 'Ingresos'. Esto causará que el precio promedio sea 1.0. Por favor, selecciona columnas distintas.")
        st.stop()
        
    if len({col_ciudad_sel, col_fruta_sel, col_cajas_sel}) < 3:
        st.error("🛑 ERROR: Las primeras tres columnas (Bodega, Fruta, Cajas) deben ser diferentes entre sí.")
        st.stop()

    st.divider()

    # --- 4. LIMPIEZA Y PROCESAMIENTO DE DATOS ---
    df_ventas[col_cajas_sel] = df_ventas[col_cajas_sel].apply(limpiar_numero)
    
    if col_dinero_sel != 'Ninguna':
        df_ventas[col_dinero_sel] = df_ventas[col_dinero_sel].apply(limpiar_numero)

    ciudades = sorted(df_ventas[col_ciudad_sel].dropna().astype(str).unique())

    # --- 5. VISUALIZACIÓN POR PESTAÑAS (TABS) ---
    if ciudades:
        tabs = st.tabs(ciudades)

        for i, ciudad in enumerate(ciudades):
            with tabs[i]:
                df_ciudad = df_ventas[df_ventas[col_ciudad_sel].astype(str) == ciudad]
                total_cajas_ciudad = df_ciudad[col_cajas_sel].sum()
                
                st.markdown(f"### 📍 {ciudad}")
                st.metric("📦 Total Cajas Vendidas", f"{total_cajas_ciudad:,.0f}")
                
                if col_dinero_sel != 'Ninguna':
                    # Agrupar por fruta y sumar cajas e ingresos
                    df_grouped = df_ciudad.groupby(col_fruta_sel).agg(
                        Cajas_Vendidas=(col_cajas_sel, 'sum'),
                        Dinero_Total=(col_dinero_sel, 'sum')
                    ).reset_index()
                    
                    # Calcular el Precio Promedio (Ingresos / Cajas)
                    df_grouped['Precio_Promedio'] = df_grouped.apply(
                        lambda row: row['Dinero_Total'] / row['Cajas_Vendidas'] if row['Cajas_Vendidas'] > 0 else 0, 
                        axis=1
                    )
                    
                    df_display = df_grouped[[col_fruta_sel, 'Cajas_Vendidas', 'Precio_Promedio']].copy()
                    df_display.columns = ['Referencia (Fruta)', 'Cajas Vendidas', 'Precio Promedio ($)']
                    df_display = df_display.sort_values(by='Cajas Vendidas', ascending=False)
                    
                    # Mostrar tabla limpia sin index y con formato
                    st.dataframe(
                        df_display.style.format({
                            'Cajas Vendidas': "{:,.0f}",
                            'Precio Promedio ($)': "${:,.0f}" 
                        }),
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info("Selecciona la columna de Ingresos en el panel superior para calcular los precios.")
    else:
        st.warning("No se encontraron bodegas en la columna seleccionada.")

else:
    st.warning("No hay datos de Ventas disponibles. Por favor, sube el archivo correspondiente en la barra lateral.")
