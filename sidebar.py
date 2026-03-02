import streamlit as st
import os
import anthropic
from fpdf import FPDF
from cleaner import clean_fruit_data
from db import process_and_save_kardex, save_arribos, process_and_save_sku_mapping, process_and_save_ventas, load_kardex, load_arribos, load_ventas

# -----------------------------------------------------------------------------
# 1. CUSTOM PDF GENERATOR CLASS
# -----------------------------------------------------------------------------
class PDF_Report(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 14)
        self.cell(0, 10, 'VIGOMEZ - PLAN DE ACCION ESTRATEGICO', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Pagina {self.page_no()}', 0, 0, 'C')

def create_pdf(text_content):
    pdf = PDF_Report()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=11)
    
    for line in text_content.split('\n'):
        clean_line = line.encode('latin-1', 'ignore').decode('latin-1')
        if clean_line.startswith('# '):
            pdf.set_font("Arial", 'B', 14)
            pdf.multi_cell(0, 8, txt=clean_line.replace('# ', '').strip())
            pdf.set_font("Arial", size=11)
            pdf.ln(2)
        elif clean_line.startswith('## '):
            pdf.set_font("Arial", 'B', 12)
            pdf.ln(4)
            pdf.multi_cell(0, 8, txt=clean_line.replace('## ', '').strip())
            pdf.set_font("Arial", size=11)
            pdf.ln(2)
        elif clean_line.strip() == '':
            pdf.ln(3)
        else:
            clean_line = clean_line.replace('**', '')
            pdf.multi_cell(0, 6, txt=clean_line.strip())
            
    return pdf.output(dest='S').encode('latin-1')

# -----------------------------------------------------------------------------
# 2. UNIVERSAL SIDEBAR RENDERER
# -----------------------------------------------------------------------------
def render_sidebar():
    with st.sidebar:
        
        # --- PDF GENERATOR SECTION ---
        st.header("📅 PLAN EJECUTIVO")
        st.markdown("Reporte semanal estratégico.")
        
        if "pdf_ready" not in st.session_state:
            st.session_state.pdf_ready = False
            st.session_state.pdf_bytes = None

        # Button to trigger AI generation
        if st.button("🚀 Generar Plan Semanal", use_container_width=True):
            with st.spinner("Analizando datos y creando PDF..."):
                try:
                    api_key = st.secrets["ANTHROPIC_API_KEY"]
                    client = anthropic.Anthropic(api_key=api_key)
                    
                    master_kardex_df = load_kardex()
                    master_arribos_df = load_arribos()
                    master_ventas_df = load_ventas()

                    total_stock = master_kardex_df.select_dtypes(include='number').sum().sum() if not master_kardex_df.empty else 0
                    total_sales_volume = master_ventas_df['Total_Cajas_Vendidas'].sum() if not master_ventas_df.empty else 0
                    total_revenue = master_ventas_df['Valor_Total_Ventas'].sum() if not master_ventas_df.empty else 0

                    vigomez_inbound = 0
                    comp_inbound = 0
                    if not master_arribos_df.empty:
                        vigomez_mask = master_arribos_df['Importador'].str.contains('VIGOMEZ', case=False, na=False)
                        vigomez_inbound = master_arribos_df[vigomez_mask]['Quantity'].sum()
                        comp_inbound = master_arribos_df[~vigomez_mask]['Quantity'].sum()

                    memo_prompt = f"""You are the Chief Commercial Officer of VIGOMEZ. 
Write the definitive Monday Morning Executive Memo for the CEO. 

MACRO SNAPSHOT:
- Total Physical Stock: {total_stock} boxes
- Last Week Sales Vol: {total_sales_volume} boxes
- Last Week Revenue: ${total_revenue:,.2f} COP
- VIGOMEZ Inbound: {vigomez_inbound} boxes
- Competitor Inbound: {comp_inbound} boxes

REQUIRED FORMAT (Must be in professional Spanish. DO NOT USE EMOJIS. Keep it concise):
# Resumen Ejecutivo Semanal VIGOMEZ
**Vision Macro:** [1 paragraph analyzing the balance of power between our stock, velocity, and competitor inbound pressure.]

## Top 3 Prioridades Estrategicas
1. [Priority 1]
2. [Priority 2]
3. [Priority 3]

## Plan de Accion Detallado y Justificacion
**Accion 1: [Name]**
* Directriz: [What exactly to do]
* Justificacion: [The hard numbers proving WHY]

**Accion 2: [Name]**
* Directriz: [What exactly to do]
* Justificacion: [The hard numbers proving WHY]
"""
                    response = client.messages.create(
                        model="claude-sonnet-4-6",
                        max_tokens=1500,
                        temperature=0.2, 
                        system="You are an elite corporate strategist. Output strictly in the requested Markdown format without emojis.",
                        messages=[{"role": "user", "content": memo_prompt}]
                    )
                    
                    # Generate PDF bytes and save to session state quietly
                    st.session_state.pdf_bytes = create_pdf(response.content[0].text)
                    st.session_state.pdf_ready = True
                    
                except Exception as e:
                    st.error(f"Error: {e}")

        # If PDF is ready, show the download button right below the generate button
        if st.session_state.pdf_ready and st.session_state.pdf_bytes:
            st.download_button(
                label="📥 Descargar PDF",
                data=st.session_state.pdf_bytes,
                file_name="Plan_De_Accion_VIGOMEZ.pdf",
                mime="application/pdf",
                use_container_width=True
            )

        st.divider()

        # --- DATA INGESTION SECTION ---
        st.header("☁️ INGESTA DE DATOS")
        st.markdown("SUBE TUS REPORTES AQUÍ:")
        
        upload_type = st.radio(
            "SELECCIONA EL TIPO DE DATO:", 
            ["ARRIBOS (INBOUND)", "KARDEX (INVENTORY)", "VENTAS (SALES PDF)", "GUÍA DE SKUS"]
        )
        
        uploaded_file = st.file_uploader("ARRASTRA TU ARCHIVO AQUÍ", type=["xlsx", "csv", "xls", "pdf"])
        
        if uploaded_file is not None:
            temp_filename = uploaded_file.name
            with open(temp_filename, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            with st.spinner("Procesando y guardando en la nube..."):
                if upload_type == "KARDEX (INVENTORY)":
                    process_and_save_kardex(temp_filename)
                    st.success("✅ Kardex actualizado!")
                elif upload_type == "GUÍA DE SKUS":
                    process_and_save_sku_mapping(temp_filename)
                    st.success("✅ Guía AI actualizada!")
                elif upload_type == "VENTAS (SALES PDF)":
                    process_and_save_ventas(temp_filename)
                    st.success("✅ Ventas actualizadas!")
                else:
                    clean_df = clean_fruit_data(temp_filename)
                    save_arribos(clean_df)
                    st.success("✅ Arribos actualizados!")