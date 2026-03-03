import streamlit as st
import pandas as pd
from db import load_arribos

# ... (your existing page config and titles) ...

df_arribos = load_arribos()

if not df_arribos.empty:
    st.subheader("⚙️ Filtros de Inbound")
    
    # Create two columns so the filters sit nicely next to each other
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**1. Filtro por Empresa**")
        # The CEO's request: A checkbox to select all
        todas_empresas = st.checkbox("✅ Todas las Empresas", value=True)
        
        if todas_empresas:
            empresas_seleccionadas = df_arribos['Importador'].unique()
        else:
            empresas_seleccionadas = st.multiselect(
                "Selecciona empresas específicas:", 
                options=df_arribos['Importador'].dropna().unique(),
                default=[]
            )

    with col2:
        st.markdown("**2. Filtro por Fruta**")
        # The CEO's request: Filter by fruit variety
        todas_frutas = st.checkbox("✅ Todas las Frutas", value=True)
        
        # Assuming your fruit column is named 'FRUTA' (Change if it's 'Variedad' or something else)
        if todas_frutas:
            frutas_seleccionadas = df_arribos['FRUTA'].unique()
        else:
            frutas_seleccionadas = st.multiselect(
                "Selecciona frutas específicas:", 
                options=df_arribos['FRUTA'].dropna().unique(),
                default=[]
            )

    # Apply both filters to the Master DataFrame
    filtered_df = df_arribos[
        (df_arribos['Importador'].isin(empresas_seleccionadas)) & 
        (df_arribos['FRUTA'].isin(frutas_seleccionadas))
    ]

    st.divider()
    
    # Now use `filtered_df` for all your charts and tables below this point instead of `df_arribos`
    # st.dataframe(filtered_df) 
    # etc...

else:
    st.warning("No hay datos de arribos disponibles. Por favor sube un archivo en la barra lateral.")
