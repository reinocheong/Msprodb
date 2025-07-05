import os
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import glob
import time

# --- CONFIGURATION ---
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found in .env file.")

DATA_FOLDER = "excel_data"
CHUNK_SIZE = 500  # How many rows to upload in a single batch
MAX_RETRIES = 3   # How many times to retry a failed chunk
RETRY_DELAY = 5   # Seconds to wait between retries
# --- END CONFIGURATION ---

def get_db_engine():
    """Creates a SQLAlchemy engine and tests the connection."""
    try:
        engine = create_engine(DATABASE_URL)
        # Test connection to wake up a sleeping DB
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        print("Database connection successful and database is awake.")
        return engine
    except Exception as e:
        print(f"Error creating database engine or connecting to the database: {e}")
        raise

def process_excel_files(engine, file_pattern, table_name, column_mapping):
    """
    Processes Excel files and uploads their data to a database table in chunks.
    """
    all_files = glob.glob(os.path.join(DATA_FOLDER, file_pattern))
    if not all_files:
        print(f"Warning: No files found for pattern: {file_pattern}")
        return

    print(f"Found {len(all_files)} files for '{table_name}'. Reading and consolidating...")
    
    all_data_df = pd.DataFrame()
    for f in all_files:
        if os.path.basename(f).startswith('~$'):
            print(f"  - Skipping temporary file: {os.path.basename(f)}")
            continue
        try:
            df = pd.read_excel(f, engine='openpyxl')
            all_data_df = pd.concat([all_data_df, df], ignore_index=True)
        except Exception as e:
            print(f"  - Error reading {os.path.basename(f)}: {e}")
            continue
    
    if all_data_df.empty:
        print(f"No data to process for '{table_name}'.")
        return

    print("Consolidation complete. Cleaning data...")
    all_data_df.rename(columns=column_mapping, inplace=True)

    for db_col in column_mapping.values():
        if db_col not in all_data_df.columns:
            all_data_df[db_col] = None

    date_columns = [col for col in ['checkin_date', 'checkout_date', 'date'] if col in all_data_df.columns]
    for col in date_columns:
        all_data_df[col] = pd.to_datetime(all_data_df[col], errors='coerce').dt.date

    numeric_columns = ['pax', 'duration', 'price', 'cleaning_fee', 'platform_charge', 'total_revenue', 'debit']
    for col in numeric_columns:
        if col in all_data_df.columns:
            all_data_df[col] = pd.to_numeric(all_data_df[col], errors='coerce')

    if 'checkin_date' in all_data_df.columns:
         all_data_df.dropna(subset=['checkin_date', 'checkout_date'], inplace=True)
    if 'date' in all_data_df.columns and table_name == 'expense':
        all_data_df.dropna(subset=['date'], inplace=True)

    final_columns = [col for col in column_mapping.values() if col in all_data_df.columns]
    final_df = all_data_df[final_columns]
    
    total_rows = len(final_df)
    print(f"Data cleaning complete. Total rows to upload: {total_rows}")

    try:
        # Clear the table once before uploading new data
        print(f"Clearing existing data from '{table_name}' table...")
        with engine.connect() as connection:
            connection.execute(text(f'TRUNCATE TABLE "{table_name}" RESTART IDENTITY;'))
            connection.commit()
        print("Table cleared.")

        # Upload in chunks
        for i in range(0, total_rows, CHUNK_SIZE):
            chunk = final_df[i:i + CHUNK_SIZE]
            retries = 0
            while retries < MAX_RETRIES:
                try:
                    print(f"  - Uploading chunk {i//CHUNK_SIZE + 1}: rows {i+1}-{min(i+CHUNK_SIZE, total_rows)}...")
                    chunk.to_sql(table_name, engine, if_exists='append', index=False)
                    print(f"  - Chunk {i//CHUNK_SIZE + 1} uploaded successfully.")
                    break 
                except Exception as e:
                    retries += 1
                    print(f"  - Error uploading chunk. Attempt {retries}/{MAX_RETRIES}. Error: {e}")
                    if retries < MAX_RETRIES:
                        print(f"  - Waiting {RETRY_DELAY} seconds before retrying...")
                        time.sleep(RETRY_DELAY)
                    else:
                        print(f"  - Max retries reached for this chunk. Aborting upload for '{table_name}'.")
                        return # Stop processing this table

        print(f"All chunks for '{table_name}' uploaded successfully.")

    except Exception as e:
        print(f"An overall error occurred during the upload process for '{table_name}': {e}")


def main():
    """Main function to run the import process."""
    print("--- Starting Data Import Script ---")
    
    engine = get_db_engine()

    booking_column_mapping = {
        'Unit Name': 'unit_name', 'CHECKIN': 'checkin_date', 'CHECKOUT': 'checkout_date',
        'Channel': 'channel', 'ON/OFFLINE': 'on_offline', 'Booking Number': 'booking_number',
        'Pax': 'pax', 'Duration': 'duration', 'Price': 'price',
        'CLEANING FEE': 'cleaning_fee', 'Patform Charge': 'platform_charge', 'TOTAL': 'total_revenue'
    }

    expense_column_mapping = {
        'Unit Name': 'unit_name', 'Date': 'date', 
        'PARTICULARS': 'particulars', 'DEBIT': 'debit'
    }
    
    process_excel_files(engine, "*Booking.xlsx", "booking", booking_column_mapping)
    print("-" * 20)
    process_excel_files(engine, "*expenses.xlsx", "expense", expense_column_mapping)

    print("\n--- Data Import Script Finished ---")


if __name__ == "__main__":
    main()