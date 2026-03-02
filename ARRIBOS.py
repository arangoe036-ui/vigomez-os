import streamlit as st
import pandas as pd
from db import load_arribos
from sidebar import render_sidebar
render_sidebar()

st.set_page_config(page_title="Dashboard Arribos", layout="wide")
st.title("🚢 Dashboard de Arribos (Inbound)")

master_arribos_df = load_arribos()

if master_arribos_df.empty:
    st.info("La base de datos está vacía. Por favor sube un archivo de Arribos en la página principal.")
else:
    arribos_df = master_arribos_df.copy()
    
    # Standardize Dates
    arribos_df['Fecha estimada de llegada'] = pd.to_datetime(arribos_df['Fecha estimada de llegada'], errors='coerce')
    arribos_df['Year'] = arribos_df['Fecha estimada de llegada'].dt.year
    arribos_df = arribos_df.dropna(subset=['Year', 'Week_Number']).copy()
    
    if 'Fruit_Type' not in arribos_df.columns:
        arribos_df['Fruit_Type'] = "Desconocido"

    # -------------------------------------------------------------------------
    # 1. FILTERS 
    # -------------------------------------------------------------------------
    arribos_df['Year_Str'] = arribos_df['Year'].astype(int).astype(str)
    arribos_df['Week_Str'] = arribos_df['Week_Number'].astype(int).apply(lambda x: f"{x:02d}")
    arribos_df['Timeframe'] = arribos_df['Year_Str'] + " - Semana " + arribos_df['Week_Str']

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        available_timeframes = sorted(arribos_df['Timeframe'].unique(), reverse=True)
        selected_timeframe = st.selectbox("📅 Filtrar por Semana Específica", ["Todas las Semanas"] + available_timeframes)
    
    with col_f2:
        all_companies = sorted(arribos_df['Importador'].dropna().unique())
        selected_companies = st.multiselect("🏢 Filtrar por Empresa", options=all_companies, default=all_companies)

    # Apply filters
    filtered_df = arribos_df[arribos_df['Importador'].isin(selected_companies)]
    if selected_timeframe != "Todas las Semanas":
        filtered_df = filtered_df[filtered_df['Timeframe'] == selected_timeframe]
        
    if filtered_df.empty:
        st.warning("No hay datos para esta combinación de filtros.")
    else:
        # -------------------------------------------------------------------------
        # 2. HIGH-LEVEL KPIs
        # -------------------------------------------------------------------------
        col1, col2, col3 = st.columns(3)
        total_boxes = int(filtered_df['Quantity'].sum())
        top_port = filtered_df.groupby('Puerto de arribo')['Quantity'].sum().idxmax()
        top_importer = filtered_df.groupby('Importador')['Quantity'].sum().idxmax()
            
        col1.metric("Cajas Programadas", f"{total_boxes:,}")
        col2.metric("Puerto Principal", top_port)
        col3.metric("Importador Principal", top_importer)
        
        st.divider()

        # -------------------------------------------------------------------------
        # 3. MAIN CHARTS (Volume by Fruit & Importer)
        # -------------------------------------------------------------------------
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            st.markdown("### 📦 Volumen por Fruta")
            fruit_summary = filtered_df.groupby('Fruit_Type')['Quantity'].sum().sort_values(ascending=False)
            st.bar_chart(fruit_summary, color="#ffaa00")
            
        with col_c2:
            st.markdown("### 🏢 Volumen por Importador")
            importer_summary = filtered_df.groupby('Importador')['Quantity'].sum().sort_values(ascending=False)
            st.bar_chart(importer_summary, color="#0055ff")
        
        st.divider()

        # -------------------------------------------------------------------------
        # 4. AGENDA DE LLEGADAS DIARIAS (COLLAPSIBLE WINDOWS)
        # -------------------------------------------------------------------------
        st.subheader("📆 Agenda de Llegadas Diarias")
        st.markdown("Haz clic en cualquier fecha para desplegar el detalle de los contenedores que llegan ese día.")
        
        # Sort chronologically
        filtered_df = filtered_df.sort_values('Fecha estimada de llegada')
        unique_dates = filtered_df['Fecha estimada de llegada'].dt.date.unique()

        if len(unique_dates) == 0:
            st.info("No hay arribos programados para las fechas seleccionadas.")
        else:
            # Create a collapsible expander for each day
            for date in unique_dates:
                date_str = date.strftime('%Y-%m-%d')
                day_data = filtered_df[filtered_df['Fecha estimada de llegada'].dt.date == date]
                
                # Calculate total volume for this specific day to put in the title
                daily_volume = int(day_data['Quantity'].sum())
                
                # st.expander creates the open/close window!
                with st.expander(f"📅 {date_str}  —  {daily_volume:,} Cajas Totales"):
                    
                    # Group it cleanly by Fruit, Importer, and Port
                    day_summary = day_data.groupby(['Fruit_Type', 'Importador', 'Puerto de arribo'])['Quantity'].sum().reset_index()
                    day_summary = day_summary.sort_values('Quantity', ascending=False)
                    
                    # Display a clean, index-less table just for this day
                    st.dataframe(
                        day_summary,
                        column_config={
                            "Fruit_Type": "Categoría (Fruta)",
                            "Importador": "Empresa Importadora",
                            "Puerto de arribo": "Puerto de Descarga",
                            "Quantity": st.column_config.NumberColumn("Cajas", format="%d")
                        },
                        hide_index=True,
                        use_container_width=True
                    )
        
        st.divider()
        
        # -------------------------------------------------------------------------
        # 5. RAW DATA TABLE
        # -------------------------------------------------------------------------
        with st.expander("📋 Ver Base de Datos Completa de Contenedores"):
            st.dataframe(filtered_df, use_container_width=True, hide_index=True)