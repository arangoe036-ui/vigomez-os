import streamlit as st
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine

# 1. CLOUD CONNECTION
try:
    db_url = st.secrets["SUPABASE_URL"]
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    if "sslmode=require" not in db_url:
        db_url = db_url + ("&sslmode=require" if "?" in db_url else "?sslmode=require")
        
    engine = create_engine(
        db_url, pool_pre_ping=True, pool_recycle=300,
        connect_args={"keepalives": 1, "keepalives_idle": 30, "keepalives_interval": 10, "keepalives_count": 5}
    )
except Exception as e:
    st.error(f"⚠️ Database connection failed: {e}")
    st.stop()

# 2. SKU TRANSLATOR
def translate_sku(sku):
    if not isinstance(sku, str): return "Otros"
    sku = sku.upper()
    if sku.startswith('MV'): return 'Manzana Verde'
    if sku.startswith(('MG', 'MR', 'MC', 'MB', 'MGC', 'MGL', 'MGT', 'MGU', 'MCO', 'MCD')): return 'Manzana Bicolor'
    if sku.startswith(('PB', 'PP', 'PA')): return 'Peras'
    if sku.startswith('NE'): return 'Nectarines'
    if sku.startswith('CI'): return 'Ciruelas'
    if sku.startswith('KI'): return 'Kiwi'
    if sku.startswith('UV'): return 'Uva Blanca Sin Semilla'
    if sku.startswith('UR'): return 'Uva Roja Sin Semilla'
    if sku.startswith('AR'): return 'Arandanos'
    return 'Otros'

# 3. ARRIBOS LOGIC
def load_arribos():
    try:
        return pd.read_sql("SELECT * FROM arribos_history", engine)
    except:
        return pd.DataFrame()

def save_arribos(new_df):
    existing_df = load_arribos()
    if not existing_df.empty:
        combined = pd.concat([existing_df, new_df]).drop_duplicates()
    else:
        combined = new_df
        
    for col in ['Fecha estimada de salida', 'Fecha estimada de llegada']:
        if col in combined.columns:
            combined[col] = combined[col].astype(str)
            
    combined.to_sql('arribos_history', engine, if_exists='replace', index=False)
    return combined

# 4. KARDEX LOGIC
def load_kardex():
    try:
        return pd.read_sql("SELECT * FROM kardex_inventory", engine)
    except:
        return pd.DataFrame()

def process_and_save_kardex(file_path):
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        raw_content = f.read()
    try:
        df = pd.read_html(raw_content)[0]
    except Exception:
        try:
            df = pd.read_csv(file_path)
        except:
            df = pd.read_excel(file_path)
            
    if 'FRUTA' not in df.columns:
        header_idx = None
        for i, row in df.iterrows():
            if any('FRUTA' == str(val).strip() for val in row.values):
                header_idx = i
                break
        if header_idx is not None:
            df.columns = df.iloc[header_idx]
            df = df.iloc[header_idx + 1:].reset_index(drop=True)
            df.columns = [str(c).strip() for c in df.columns]
            
    df = df[~df['FRUTA'].astype(str).str.startswith('TOTAL', na=False)].dropna(subset=['FRUTA'])
    df['Fruit_Category'] = df['FRUTA'].apply(translate_sku)
    
    warehouses = ['BOGOTAT', 'BOGOTAC', 'VIGOMED', 'VIGOBAR', 'VIGOPAL', 'VIGOPER', 'YUMBO', 'TRANSITO']
    for w in warehouses:
        if w in df.columns:
            df[w] = pd.to_numeric(df[w], errors='coerce').fillna(0)
            
    df['Last_Updated'] = datetime.now().strftime("%Y-%m-%d %H:%M")
    df.to_sql('kardex_inventory', engine, if_exists='replace', index=False) 
    return df

# -----------------------------------------------------------------------------
# 5. SKU DICTIONARY (AI REFERENCE GUIDE)
# -----------------------------------------------------------------------------
def load_sku_mapping():
    try:
        return pd.read_sql("SELECT * FROM sku_mapping", engine)
    except:
        return pd.DataFrame()

def process_and_save_sku_mapping(file_path):
    if file_path.endswith('.csv'):
        df = pd.read_csv(file_path)
    else:
        df = pd.read_excel(file_path)
        
    start_idx = 0
    code_col = None
    desc_col = None
    
    # Automatically hunt for the "CODIGO VIGOMEZ" header in the messy Excel file
    for r_idx, row in df.iterrows():
        for c_idx, val in row.items():
            if str(val).strip().upper() == 'CODIGO VIGOMEZ':
                start_idx = r_idx + 1
                code_col = c_idx
                # The description is usually the very next column
                desc_col = df.columns[min(len(df.columns)-1, list(df.columns).index(code_col) + 1)]
                break
        if code_col: break
        
    # Fallback if it can't find the exact header
    if not code_col:
        code_col = 'CODIGOS' if 'CODIGOS' in df.columns else df.columns[1]
        desc_col = 'Unnamed: 2' if 'Unnamed: 2' in df.columns else df.columns[2]
        
    df_clean = df.iloc[start_idx:].copy()
    df_clean = df_clean.dropna(subset=[code_col])
    
    current_cat = "Desconocido"
    mappings = []
    
    for _, row in df_clean.iterrows():
        c = str(row[code_col]).strip()
        d = str(row[desc_col]).strip()
        
        # If there is no description, it's a Fruit Category Title (e.g., "MANZANA ROJA")
        if d == 'nan' or d == 'None' or d == '':
            current_cat = c  
        elif c != 'nan' and c != 'None' and c != '':
            # It's an exact SKU map!
            mappings.append({'Codigo': c, 'Categoria': current_cat, 'Descripcion': d})
            
    mapping_df = pd.DataFrame(mappings)
    mapping_df.to_sql('sku_mapping', engine, if_exists='replace', index=False)
    return mapping_df

# -----------------------------------------------------------------------------
# 6. LÓGICA DE VENTAS (SALES ENGINE)
# -----------------------------------------------------------------------------
def load_ventas():
    try:
        return pd.read_sql("SELECT * FROM ventas_history", engine)
    except:
        return pd.DataFrame()

def process_and_save_ventas(file_path):
    import PyPDF2
    import re
    
    if file_path.lower().endswith('.pdf'):
        try:
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text = ""
                for p in reader.pages:
                    text += p.extract_text() + "\n"
        except Exception as e:
            st.error(f"Error leyendo PDF: {e}")
            return pd.DataFrame()
        
        # Extract location and dates using Regex
        bodega_match = re.search(r'Bodega:\s*([A-Za-z]+)', text)
        bodega = bodega_match.group(1) if bodega_match else "Desconocido"
        
        date_match = re.search(r'(\d{8}\s*-\s*\d{8})', text)
        date_range = date_match.group(1) if date_match else "Desconocido"

        lines = text.split('\n')
        data = []
        
        for line in lines:
            line = line.strip()
            if line.startswith("TOTAL") or not line: continue
            
            parts = line.split()
            # Identify valid SKU rows
            if len(parts) > 10 and parts[0].isalnum() and parts[1].isalnum() and len(parts[0]) >= 4:
                # Clean currency symbols and decimals for clean math
                clean_line = re.sub(r'[\$\.\(\)]', '', line)
                cparts = clean_line.split()
                if len(cparts) >= 11:
                    try:
                        sku = cparts[0]
                        embarque = cparts[1]
                        tot_qty = float(cparts[-5]) # Cajas Totales
                        tot_val = float(cparts[-4]) # Valor Total
                        tot_avg = float(cparts[-3]) # Promedio Total
                        
                        data.append({
                            'Bodega': bodega,
                            'Rango_Fechas': date_range,
                            'FRUTA': sku,
                            'Embarque': embarque,
                            'Total_Cajas_Vendidas': tot_qty,
                            'Valor_Total_Ventas': tot_val,
                            'Precio_Promedio': tot_avg
                        })
                    except:
                        pass
        new_df = pd.DataFrame(data)
    else:
        if file_path.endswith('.csv'):
            new_df = pd.read_csv(file_path)
        else:
            new_df = pd.read_excel(file_path)
            
    if new_df.empty: return pd.DataFrame()

    # Translate the SKUs for Ventas as well!
    new_df['Fruit_Category'] = new_df['FRUTA'].apply(translate_sku)
    
    # Merge with history
    existing_df = load_ventas()
    if not existing_df.empty:
        combined = pd.concat([existing_df, new_df]).drop_duplicates(subset=['Bodega', 'Rango_Fechas', 'FRUTA', 'Embarque'])
    else:
        combined = new_df
        
    combined.to_sql('ventas_history', engine, if_exists='replace', index=False)
    return combined

# -----------------------------------------------------------------------------
# 7. MÓDULO DE MEMORIA DE LA IA (LONG-TERM MEMORY)
# -----------------------------------------------------------------------------
def save_ai_log(user_query, ai_response):
    import pandas as pd
    from datetime import datetime
    
    # Create a small dataframe with the interaction
    new_log = pd.DataFrame([{
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'user_query': user_query,
        'ai_response': ai_response
    }])
    
    # Append it to the 'ai_strategy_logs' table in the database
    try:
        new_log.to_sql('ai_strategy_logs', engine, if_exists='append', index=False)
    except Exception as e:
        print(f"Error saving AI log: {e}")

def load_ai_logs(limit=3):
    import pandas as pd
    try:
        # Load the last few interactions to give the AI context of recent days
        df = pd.read_sql("SELECT * FROM ai_strategy_logs ORDER BY timestamp DESC", engine)
        if not df.empty:
            return df.head(limit).to_dict('records')
        return []
    except:
        return []