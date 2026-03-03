import streamlit as st
import pandas as pd
import anthropic
from db import load_arribos, load_kardex, load_ventas

st.set_page_config(page_title="Director AI", layout="wide")

st.title("🧠 Director AI - Asistente Estratégico")
st.markdown("Consulta en lenguaje natural sobre el estado de la operación (Arribos, Inventario, Ventas).")

# --- 1. CARGAR DATOS ---
df_arribos = load_arribos()
df_kardex = load_kardex()
df_ventas = load_ventas()

# --- 2. PREPARAR EL CONTEXTO (EL CEREBRO DE LA IA) ---
contexto_arribos = "Sin datos de arribos."
if not df_arribos.empty:
    cols_upper = {c.upper().strip(): c for c in df_arribos.columns}
    col_semana = next((cols_upper[c] for c in cols_upper if 'SEMANA' in c or 'WEEK' in c), None)
    col_fruta = next((cols_upper[c] for c in cols_upper if c in ['FRUTA', 'PRODUCTO', 'VARIEDAD']), df_arribos.columns[0])
    col_importador = next((cols_upper[c] for c in cols_upper if 'IMPORTADOR' in c or 'EMPRESA' in c), None)
    col_cajas = next((cols_upper[c] for c in cols_upper if 'CAJA' in c or 'QTY' in c), None)

    # Agrupamos por semana para que la IA sepa exactamente cuándo llega cada cosa
    if col_semana and col_importador and col_fruta and col_cajas:
        df_arribos[col_cajas] = pd.to_numeric(df_arribos[col_cajas], errors='coerce').fillna(0)
        resumen = df_arribos.groupby([col_semana, col_importador, col_fruta])[col_cajas].sum().reset_index()
        contexto_arribos = resumen.to_csv(index=False)
    else:
        # Si no encuentra las columnas exactas, le pasamos todo
        contexto_arribos = df_arribos.to_csv(index=False)

contexto_kardex = df_kardex.to_csv(index=False) if not df_kardex.empty else "Sin datos de kardex."
contexto_ventas = df_ventas.to_csv(index=False) if not df_ventas.empty else "Sin datos de ventas."

# --- 3. CONFIGURAR EL PROMPT DEL SISTEMA ---
system_prompt = f"""
Eres el Chief Commercial Officer (Director AI) de VIGOMEZ, una empresa de importación de fruta en Colombia.
Tu trabajo es analizar los datos operativos y dar respuestas estratégicas, directas y precisas al CEO.

REGLAS ESTRICTAS:
1. Responde SIEMPRE basándote en los datos CSV proporcionados abajo.
2. Si te preguntan por una semana específica (ej. Semana 08), busca EXACTAMENTE en la columna correspondiente del contexto de Arribos.
3. Si el CEO pregunta por la competencia, compara los datos de 'VIGOMEZ' vs los demás importadores.
4. Sé conciso. Ve directo a los números.

--- DATOS DE ARRIBOS (INBOUND POR SEMANA) ---
{contexto_arribos}

--- DATOS DE INVENTARIO (KARDEX FÍSICO VS TRÁNSITO) ---
{contexto_kardex}

--- DATOS DE VENTAS ---
{contexto_ventas}
"""

# --- 4. INTERFAZ DE CHAT ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# Mostrar historial
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- 5. LLAMADA A ANTHROPIC ---
if prompt := st.chat_input("Ej: ¿Cuántas cajas de pera arribaron en la semana 08 de 2026?"):
    # Agregar mensaje del usuario al chat
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        try:
            client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
            claude_messages = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
            
            response = client.messages.create(
                model="claude-opus-4-6", 
                max_tokens=1000,
                system=system_prompt,
                messages=claude_messages
            )
            
            respuesta_ai = response.content[0].text
            message_placeholder.markdown(respuesta_ai)
            
            # Guardar respuesta en historial
            st.session_state.messages.append({"role": "assistant", "content": respuesta_ai})
            
        except Exception as e:
            st.error(f"Error al conectar con la IA: {e}")
