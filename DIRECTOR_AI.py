import streamlit as st
import anthropic
import re
from sidebar import render_sidebar
from db import load_arribos, load_kardex, load_sku_mapping, load_ventas, load_ai_logs, save_ai_log

st.set_page_config(page_title="AI Strategy Director", layout="wide")

# Call the universal sidebar
render_sidebar()

st.title("🤖 DIRECTOR DE ESTRATEGIA AI (VIGOMEZ)")
st.markdown("Consultor experto enfocado en **Maximización de Ingresos**, Precios Dinámicos y Arbitraje Logístico.")

try:
    api_key = st.secrets["ANTHROPIC_API_KEY"]
except Exception:
    st.error("Missing Anthropic API Key in secrets.toml")
    st.stop()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# -----------------------------------------------------------------------------
# 1. FETCH LIVE DATA
# -----------------------------------------------------------------------------
master_kardex_df = load_kardex()
master_arribos_df = load_arribos()
sku_mapping_df = load_sku_mapping() 
master_ventas_df = load_ventas()

sku_guide_text = ""
if not sku_mapping_df.empty:
    for _, row in sku_mapping_df.iterrows():
        sku_guide_text += f"- {row['Codigo']}: {row['Categoria']} | {row['Descripcion']}\n"

current_stock_detailed = {}
if not master_kardex_df.empty:
    df_k = master_kardex_df.copy()
    locations = [col for col in ['BOGOTAT', 'BOGOTAC', 'VIGOMED', 'VIGOBAR', 'VIGOPAL', 'VIGOPER', 'YUMBO', 'TRANSITO'] if col in df_k.columns]
    for loc in locations:
        loc_data = df_k[df_k[loc] > 0]
        if not loc_data.empty:
            current_stock_detailed[loc] = loc_data.set_index('FRUTA')[loc].to_dict()

sales_financials = {}
if not master_ventas_df.empty:
    grouped = master_ventas_df.groupby(['Bodega', 'FRUTA']).agg(
        Cajas_Vendidas=('Total_Cajas_Vendidas', 'sum'),
        Precio_Promedio=('Precio_Promedio', 'mean')
    ).reset_index()
    
    for _, row in grouped.iterrows():
        bodega = row['Bodega']
        if bodega not in sales_financials:
            sales_financials[bodega] = {}
        sales_financials[bodega][row['FRUTA']] = {
            "Cajas_Vendidas": row['Cajas_Vendidas'], 
            "Precio_Promedio_COP": row['Precio_Promedio']
        }

vigomez_inbound = {}
competitor_inbound = {}
if not master_arribos_df.empty:
    vigomez_mask = master_arribos_df['Importador'].str.contains('VIGOMEZ', case=False, na=False)
    vigomez_inbound = master_arribos_df[vigomez_mask].groupby('Fruit_Type')['Quantity'].sum().to_dict()
    competitor_inbound = master_arribos_df[~vigomez_mask].groupby('Fruit_Type')['Quantity'].sum().to_dict()

# -----------------------------------------------------------------------------
# 2. FETCH LONG-TERM MEMORY
# -----------------------------------------------------------------------------
past_logs = load_ai_logs(limit=3)
memory_text = ""
if past_logs:
    for log in past_logs:
        memory_text += f"\n- [{log['timestamp']}] USER: {log['user_query']} | AI: {log['ai_response']}"
else:
    memory_text = "(No past history available)"

# -----------------------------------------------------------------------------
# 3. CONCISE SYSTEM PROMPT
# -----------------------------------------------------------------------------
system_prompt = f"""You are an elite, profit-driven Supply Chain Director for VIGOMEZ. 
Your output must be EXTREMELY CONCISE, CLEAR, and ACTIONABLE. No fluff. No long paragraphs.

LOCATION TRANSLATION: BOGOTAC/BOGOTAT=BOGOTÁ, VIGOMED=MEDELLÍN, VIGOPAL=CALI.
SKU GUIDE: {sku_guide_text}

DATA CONTEXT:
1. Physical Stock: {current_stock_detailed}
2. Sales Velocity & Pricing: {sales_financials}
3. Inbound VIGOMEZ: {vigomez_inbound}
4. Inbound COMPETITOR: {competitor_inbound}

PAST RECOMMENDATION HISTORY:
{memory_text}

PROFIT RULES:
1. DYNAMIC PRICING: Low stock + high velocity -> RAISE PRICES.
2. LIQUIDATION: High stock OR massive competitor inbound -> DROP PRICES.
3. ARBITRAGE: High price delta between cities -> TRANSFER STOCK.

MANDATORY OUTPUT FORMAT:
Do all your math inside <thinking> tags. 
Your visible response MUST use this exact format and be very short:

**🧠 Insight Estratégico**
[1 sentence defining the main market situation]

**🎯 Plan de Acción**
* [Action 1: e.g. "Subir precio de MGCX100 en BOGOTÁ un 10%"]
* [Action 2: e.g. "Trasladar 500 cajas de Kiwi de CALI a MEDELLÍN"]

**📊 Justificación Numérica**
* [Stat 1: e.g. "Kiwi se vende $30k más caro en Medellín"]
* [Stat 2: e.g. "Solo quedan 0.5 semanas de stock de MGCX100"]
"""

# -----------------------------------------------------------------------------
# 4. SUGGESTED PROMPTS UI (Only shows when chat is empty)
# -----------------------------------------------------------------------------
button_prompt = None
if len(st.session_state.chat_history) == 0:
    st.markdown("### 💡 Preguntas Sugeridas para el CEO:")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📊 Rentabilidad y Arbitraje"):
            button_prompt = "¿Qué oportunidades de arbitraje de precios entre ciudades tenemos hoy?"
    with col2:
        if st.button("⚠️ Riesgos de Quiebre"):
            button_prompt = "¿Qué productos están a punto de agotarse y requieren ajuste de precio?"
    with col3:
        if st.button("💰 Análisis de Competencia"):
            button_prompt = "¿Qué está trayendo la competencia y cómo debemos ajustar nuestros precios hoy?"
    st.divider()

# -----------------------------------------------------------------------------
# 5. CHAT RENDERING ENGINE
# -----------------------------------------------------------------------------
for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        if message["role"] == "assistant":
            # Upgraded Regex: Hides math even if the AI gets cut off and forgets the closing tag
            clean_content = re.sub(r'<thinking>.*?(?:</thinking>|$)', '', message["content"], flags=re.DOTALL).strip()
            st.markdown(clean_content)
        else:
            st.markdown(message["content"])

# Capture input from either the chat bar OR the buttons above
user_query = st.chat_input("Escribe tu pregunta o selecciona una opción arriba...") or button_prompt

if user_query:
    with st.chat_message("user"):
        st.markdown(user_query)
    st.session_state.chat_history.append({"role": "user", "content": user_query})

    with st.chat_message("assistant"):
        with st.spinner("Generating concise executive report..."):
            try:
                client = anthropic.Anthropic(api_key=api_key)
                api_messages = [{"role": m["role"], "content": m["content"]} for m in st.session_state.chat_history]
                
                response = client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=2500, # Increased to prevent text cut-offs during heavy math
                    temperature=0.2, 
                    system=system_prompt,
                    messages=api_messages
                )
                
                ai_raw_answer = response.content[0].text
                st.session_state.chat_history.append({"role": "assistant", "content": ai_raw_answer})
                save_ai_log(user_query, ai_raw_answer)
                
                # Show clean answer
                clean_content = re.sub(r'<thinking>.*?(?:</thinking>|$)', '', ai_raw_answer, flags=re.DOTALL).strip()
                st.markdown(clean_content)
                
            except Exception as e:
                st.error(f"AI Connection Error: {e}")