import streamlit as st
import pandas as pd
from db import load_arribos

st.set_page_config(page_title="Dashboard de Arribos", layout="wide")

st.title("🚢 Dashboard de Arribos (Inbound)")

# Load data
df_arribos = load_arribos()

if not df_arribos.empty:
    # --- 1. SMART COLUMN DETECTOR ---
    col_fruta_real = next((col for col in df_arribos.columns if col.upper() in ['FRUTA', 'FRUITS', 'FRUIT_CATEGORY', 'PRODUCTO', 'VARIEDAD']), df_arribos.columns[0])
    col_semana_real = next((col for col in df_arribos.columns if 'SEMANA' in col.upper() or 'WEEK' in col.upper()), None)
    col_cajas_real = next((col for col in df_arribos.columns if 'CAJA' in col.upper() or 'QUANTITY' in col.upper() or 'QTY' in col.upper()), None)
    col_fecha_real = next((col for col in df_arribos.columns if 'ETA' in col.upper() or 'FECHA' in col.upper() or 'DATE' in col.upper() or 'LLEGADA' in col.upper()), None)

    st.markdown("### ⚙️ Filtros de Inbound")
    
    # --- 2. THE CEO'S NEW FILTERS ---
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**1. Filtrar por Semana**")
        if col_semana_real:
            semanas_disponibles = sorted(df_arribos[col_semana_real].dropna().unique().tolist())
            semana_seleccionada = st.selectbox("Semana Específica:", ["Todas las Semanas"] + semanas_disponibles)
        else:
            st.info("Sin datos de semana.")
            semana_seleccionada = "Todas las Semanas"
            
    with col2:
        st.markdown("**2. Filtrar por Empresa**")
        todas_empresas = st.checkbox("✅ Todas las Empresas", value=True)
        
        if todas_empresas:
            empresas_seleccionadas = df_arribos['Importador'].dropna().unique()
        else:
            empresas_seleccionadas = st.multiselect(
                "Selecciona empresas:", 
                options=sorted(df_arribos['Importador'].dropna().unique()),
                default=[]
            )

    with col3:
        st.markdown("**3. Filtrar por Fruta**")
        todas_frutas = st.checkbox("✅ Todas las Frutas", value=True)
        
        if todas_frutas:
            frutas_seleccionadas = df_arribos[col_fruta_real].dropna().unique()
        else:
            frutas_seleccionadas = st.multiselect(
                "Selecciona frutas:", 
                options=sorted(df_arribos[col_fruta_real].dropna().unique()),
                default=[]
            )

    # --- 3. APPLY FILTERS TO DATA ---
    mask = (df_arribos['Importador'].isin(empresas_seleccionadas)) & (df_arribos[col_fruta_real].isin(frutas_seleccionadas))
    
    if col_semana_real and semana_seleccionada != "Todas las Semanas":
        mask = mask & (df_arribos[col_semana_real] == semana_seleccionada)
        
    filtered_df = df_arribos[mask]

    st.divider()

    # --- 4. CEO KPI METRICS ---
    kpi1, kpi2, kpi3 = st.columns(3)
    
    total_cajas = int(filtered_df[col_cajas_real].sum()) if col_cajas_real else len(filtered_df)
    
    col_puerto = next((col for col in df_arribos.columns if 'PUERTO' in col.upper() or 'PORT' in col.upper()), None)
    puerto_principal = filtered_df[col_puerto].mode()[0] if col_puerto and not filtered_df.empty else "N/A"
    
    importador_principal = filtered_df['Importador'].mode()[0] if not filtered_df.empty else "N/A"

    kpi1.metric("📦 Cajas Programadas", f"{total_cajas:,.0f}")
    kpi2.metric("⚓ Puerto Principal", puerto_principal)
    kpi3.metric("🏢 Importador Principal", importador_principal)

    st.divider()

    # --- 5. ARRIVALS PER DAY (THE DROP-DOWN TABLES) ---
    st.markdown("### 📅 Arribos por Día (ETA)")
    if col_fecha_real and not filtered_df.empty:
        # Get a list of all unique dates in the filtered data, sorted chronologically
        fechas_unicas = sorted(filtered_df[col_fecha_real].dropna().unique())
        
        for fecha in fechas_unicas:
            # Get only the rows for this specific date
            df_dia = filtered_df[filtered_df[col_fecha_real] == fecha]
            
            # Calculate total boxes for the header
            cajas_dia = int(df_dia[col_cajas_real].sum()) if col_cajas_real else len(df_dia)
            
            # Create the dropdown container
            with st.expander(f"📅 {fecha}  |  📦 {cajas_dia:,.0f} Cajas Totales"):
                # Inside the dropdown, show the clean table for that day
                st.dataframe(df_dia, use_container_width=True)
    else:
        st.info("No se detectó la columna de Fechas (ETA) para agrupar los arribos.")

    st.divider()

    # --- 6. CLEAN DATA TABLE (ALL DATA) ---
    st.markdown("### 📋 Base de Datos Completa (Filtrada)")
    st.dataframe(filtered_df, use_container_width=True)

else:
    st.warning("No hay datos de arribos disponibles. Por favor, sube un archivo en la barra lateral.")
