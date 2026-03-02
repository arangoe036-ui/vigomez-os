import streamlit as st
import pandas as pd
import numpy as np
from db import load_ventas, load_kardex, load_arribos
from sidebar import render_sidebar

st.set_page_config(page_title="VIGOMEZ OS", layout="wide", page_icon="🌍")

# 1. Call the universal sidebar
render_sidebar()

st.title("🌍 Torre de Control Maestral (Command Center)")
st.markdown("Visión macroscópica del negocio: Inventario Físico vs. Velocidad de Salida vs. Presión de Entrada (Mercado).")

# 2. Load All Data
master_ventas_df = load_ventas()
master_kardex_df = load_kardex()
master_arribos_df = load_arribos()

if master_ventas_df.empty or master_kardex_df.empty or master_arribos_df.empty:
    st.info("👋 Bienvenido a VIGOMEZ OS. Usa el menú de la izquierda para subir tus archivos de Kardex, Arribos y Ventas para inicializar el sistema.")
    st.stop()

# 3. Process Data for the Master View
df_k = master_kardex_df.copy()
phys_cols = [col for col in ['BOGOTAT', 'BOGOTAC', 'VIGOMED', 'VIGOBAR', 'VIGOPAL', 'VIGOPER', 'YUMBO'] if col in df_k.columns]
df_k['Stock_Fisico'] = df_k[phys_cols].sum(axis=1)
kardex_cat = df_k.groupby('Fruit_Category')['Stock_Fisico'].sum().reset_index()

df_v = master_ventas_df.copy()
ventas_cat = df_v.groupby('Fruit_Category').agg(
    Cajas_Vendidas=('Total_Cajas_Vendidas', 'sum'),
    Ingresos_Totales=('Valor_Total_Ventas', 'sum')
).reset_index()

df_a = master_arribos_df.copy()
df_a['Fruit_Type'] = df_a['Fruit_Type'].str.upper().str.strip()

vigomez_mask = df_a['Importador'].str.contains('VIGOMEZ', case=False, na=False)
arribos_vigomez = df_a[vigomez_mask].groupby('Fruit_Type')['Quantity'].sum().reset_index()
arribos_vigomez.rename(columns={'Fruit_Type': 'Fruit_Category', 'Quantity': 'Arribos_VIGOMEZ'}, inplace=True)

arribos_comp = df_a[~vigomez_mask].groupby('Fruit_Type')['Quantity'].sum().reset_index()
arribos_comp.rename(columns={'Fruit_Type': 'Fruit_Category', 'Quantity': 'Arribos_Competencia'}, inplace=True)

# Merge
master_df = pd.merge(kardex_cat, ventas_cat, on='Fruit_Category', how='outer')
master_df = pd.merge(master_df, arribos_vigomez, on='Fruit_Category', how='outer')
master_df = pd.merge(master_df, arribos_comp, on='Fruit_Category', how='outer').fillna(0)
master_df = master_df[master_df['Fruit_Category'] != 'DESCONOCIDO']
master_df = master_df[master_df['Fruit_Category'] != '0']

master_df['Market_Share_Arribos (%)'] = np.where(
    (master_df['Arribos_VIGOMEZ'] + master_df['Arribos_Competencia']) > 0,
    (master_df['Arribos_VIGOMEZ'] / (master_df['Arribos_VIGOMEZ'] + master_df['Arribos_Competencia'])) * 100,
    0
)
master_df['Rotacion_Semanal (x)'] = np.where(
    master_df['Stock_Fisico'] > 0,
    master_df['Cajas_Vendidas'] / master_df['Stock_Fisico'],
    0
)

# -----------------------------------------------------------------------------
# DASHBOARD RENDERING
# -----------------------------------------------------------------------------
st.subheader("📊 Indicadores Globales VIGOMEZ")
col1, col2, col3, col4 = st.columns(4)
col1.metric("📦 Inventario Físico Total", f"{int(master_df['Stock_Fisico'].sum()):,}")
col2.metric("💸 Cajas Vendidas (Semana)", f"{int(master_df['Cajas_Vendidas'].sum()):,}")
col3.metric("🚢 Arribos VIGOMEZ (Próximos)", f"{int(master_df['Arribos_VIGOMEZ'].sum()):,}")
col4.metric("🦈 Arribos Competencia", f"{int(master_df['Arribos_Competencia'].sum()):,}")

st.divider()

st.subheader("📈 Ecuación de Oferta y Demanda por Categoría")
chart_df = master_df[['Fruit_Category', 'Stock_Fisico', 'Cajas_Vendidas', 'Arribos_VIGOMEZ', 'Arribos_Competencia']].set_index('Fruit_Category')
st.bar_chart(chart_df, use_container_width=True)

st.divider()

st.subheader("🔬 Matriz de Correlación Estratégica")
st.dataframe(
    master_df.sort_values('Stock_Fisico', ascending=False),
    column_config={
        "Fruit_Category": "Categoría de Fruta",
        "Stock_Fisico": st.column_config.NumberColumn("🏢 Stock Físico", format="%d"),
        "Cajas_Vendidas": st.column_config.NumberColumn("🛒 Ventas (Semana)", format="%d"),
        "Arribos_VIGOMEZ": st.column_config.NumberColumn("🚢 Arribos VIGOMEZ", format="%d"),
        "Arribos_Competencia": st.column_config.NumberColumn("🦈 Arribos Competencia", format="%d"),
        "Market_Share_Arribos (%)": st.column_config.ProgressColumn(
            "Share de Arribos",
            format="%.1f%%",
            min_value=0,
            max_value=100
        ),
        "Rotacion_Semanal (x)": st.column_config.NumberColumn("Velocidad de Rotación", format="%.2f x"),
        "Ingresos_Totales": None 
    },
    hide_index=True,
    use_container_width=True
)