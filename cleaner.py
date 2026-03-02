import pandas as pd
import os

def clean_fruit_data(file_path):
    print(f"🔄 Processing: {file_path}")
    
    # 1. Load the Excel/CSV file
    if file_path.endswith('.csv'):
        df = pd.read_csv(file_path)
    else:
        df = pd.read_excel(file_path)

    # 2. Extract the Week Number
    # Convert arrival date to datetime and get the ISO week of the year
    df['Fecha estimada de llegada'] = pd.to_datetime(df['Fecha estimada de llegada'], errors='coerce')
    df['Week_Number'] = df['Fecha estimada de llegada'].dt.isocalendar().week

    # 3. Define the exact columns we want to keep (The "Dimensions")
    # Notice we added 'Week_Number' to this list so it carries over
    id_vars = [
        'Buque', 
        'Puerto de salida', 
        'Fecha estimada de salida', 
        'Fecha estimada de llegada', 
        'Week_Number',
        'Puerto de arribo', 
        'Importador', 
        'Exportador'
    ]

    # 4. Define the Fruit Columns (The "Values")
    fruit_cols = [
        'Manzana Bicolor', 'Manzana Verde', 'Peras', 'Nectarines', 
        'Uva De Mesa Blanca sin semilla', 'Uva De Mesa Red Globe', 
        'Uva De Mesa Roja Sin Semilla', 'Uva De Mesa Negra Sin Semilla', 
        'Ciruelas', 'Arandanos'
    ]

    # Ensure these columns exist, even if the file is missing one
    for col in fruit_cols:
        if col not in df.columns:
            df[col] = 0

    # 5. The "Unpivot" (Melting)
    clean_df = df.melt(
        id_vars=[col for col in id_vars if col in df.columns], 
        value_vars=fruit_cols, 
        var_name='Fruit_Type', 
        value_name='Quantity'
    )

    # 6. Cleaning the Numbers (The Fix for footer text)
    # Remove commas first (e.g., "1,000" -> "1000")
    clean_df['Quantity'] = clean_df['Quantity'].astype(str).str.replace(',', '')
    
    # Force the conversion to numbers (turns weird text like '*Resultados' into NaN)
    clean_df['Quantity'] = pd.to_numeric(clean_df['Quantity'], errors='coerce')
    
    # Fill those NaNs (and any other empties) with 0
    clean_df['Quantity'] = clean_df['Quantity'].fillna(0)

    # 7. Remove rows with 0 quantity (Empty shipments)
    final_df = clean_df[clean_df['Quantity'] > 0].copy()

    print(f"✅ Success! Transformed into {len(final_df)} clean records.")
    return final_df

if __name__ == "__main__":
    current_files = [f for f in os.listdir('.') if f.endswith('.csv') or f.endswith('.xlsx')]
    
    if current_files:
        target_file = current_files[0]
        try:
            cleaned_data = clean_fruit_data(target_file)
            cleaned_data.to_csv('cleaned_data_master.csv', index=False)
            print("💾 Saved clean data to 'cleaned_data_master.csv'")
            print("\n--- Preview of Clean Data ---")
            print(cleaned_data.head())
        except Exception as e:
            print(f"❌ Error: {e}")
    else:
        print("⚠️ No Excel or CSV file found in this folder. Please drop your 'Arribos' file here.")