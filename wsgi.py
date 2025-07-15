from mspro_app import create_app, db
import click
from flask.cli import with_appcontext
from mspro_app.models import User, Booking, Expense
import pandas as pd
import os
import glob
import uuid
import math

app = create_app()

# Only apply WhiteNoise in production to avoid conflicts with dev server
if os.environ.get("FLASK_ENV") == "production":
    from whitenoise import WhiteNoise
    app.wsgi_app = WhiteNoise(app.wsgi_app, root='static/', prefix='static/')

@app.cli.command("import-data")
@with_appcontext
def import_data_command():
    """Clears existing booking and expense data, then robustly imports new data from excel files."""
    print("--- Starting Data Import Command ---")
    
    # --- Step 1: Clear existing data without dropping tables ---
    try:
        # Use a more targeted deletion that is database-agnostic
        db.session.query(Booking).delete()
        db.session.query(Expense).delete()
        db.session.commit()
        print("Step 1: All existing booking and expense records have been deleted.")
    except Exception as e:
        db.session.rollback()
        print(f"An error occurred while clearing data: {e}")
        return

    DATA_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'excel_data')
    print(f"Step 2: Reading data from '{DATA_FOLDER}'...")

    # --- Booking Data Processing ---
    booking_files = [f for f in glob.glob(os.path.join(DATA_FOLDER, '*Booking.xlsx')) if not os.path.basename(f).startswith('~$')]
    if booking_files:
        df_b = pd.concat((pd.read_excel(f, engine='openpyxl', dtype={'Booking Number': str}) for f in booking_files), ignore_index=True)
        print(f"Found and merged {len(booking_files)} booking files. Total rows: {len(df_b)}")
        
        df_b.rename(columns={
            'Unit Name': 'unit_name', 'CHECKIN': 'checkin', 'CHECKOUT': 'checkout',
            'Channel': 'channel', 'ON/OFFLINE': 'on_offline', 'Booking Number': 'booking_number',
            'Pax': 'pax', 'Duration': 'duration', 'Price': 'price',
            'CLEANING FEE': 'cleaning_fee', 'Platform Charge': 'platform_charge', 'TOTAL': 'total'
        }, inplace=True)
        
        numeric_cols = ['pax', 'duration', 'price', 'cleaning_fee', 'platform_charge', 'total']
        for col in numeric_cols:
            if col not in df_b.columns:
                df_b[col] = 0
            df_b[col] = pd.to_numeric(df_b[col], errors='coerce').fillna(0)

        df_b['pax'] = df_b['pax'].astype(int)
        df_b['duration'] = df_b['duration'].astype(int)

        df_b['checkin'] = pd.to_datetime(df_b['checkin'], errors='coerce')
        df_b['checkout'] = pd.to_datetime(df_b['checkout'], errors='coerce')
        df_b.dropna(subset=['checkin', 'checkout'], inplace=True)

        model_columns = [c.name for c in Booking.__table__.columns]
        final_df_b = df_b[df_b.columns.intersection(model_columns)]
        
        bookings_to_add = [Booking(**row) for _, row in final_df_b.iterrows() if 'id' not in row]
        db.session.bulk_save_objects(bookings_to_add)
        db.session.commit()
        print(f"SUCCESS: Imported {len(bookings_to_add)} booking records.")

    # --- Expense Data Processing ---
    expense_files = [f for f in glob.glob(os.path.join(DATA_FOLDER, '*expenses*.xlsx')) if not os.path.basename(f).startswith('~$')]
    if expense_files:
        df_e = pd.concat((pd.read_excel(f, engine='openpyxl') for f in expense_files), ignore_index=True)
        print(f"Found and merged {len(expense_files)} expense files. Total rows: {len(df_e)}")
        
        # --- Robustly coalesce alternate column names into a standard set ---
        column_map = {
            'Expenses Date': 'Date',
            'PARTICULARS': 'Particulars',
            'DEBIT': 'Amount'
        }
        for old_col, new_col in column_map.items():
            if old_col in df_e.columns:
                if new_col not in df_e.columns:
                    df_e[new_col] = df_e[old_col]
                else:
                    # Use the recommended, future-proof way to fill NaN values
                    df_e[new_col] = df_e[new_col].fillna(df_e[old_col])
        
        df_e.rename(columns={'Date': 'date', 'Unit Name': 'unit_name', 'Particulars': 'particulars', 'Amount': 'debit'}, inplace=True)
        
        df_e['date'] = pd.to_datetime(df_e['date'], errors='coerce')
        df_e['debit'] = pd.to_numeric(df_e['debit'], errors='coerce').fillna(0)
        df_e.dropna(subset=['date', 'debit'], inplace=True)

        expense_model_columns = [c.name for c in Expense.__table__.columns]
        final_df_e = df_e[df_e.columns.intersection(expense_model_columns)]

        expenses_to_add = [Expense(**row) for _, row in final_df_e.iterrows() if 'id' not in row]
        db.session.bulk_save_objects(expenses_to_add)
        db.session.commit()
        print(f"SUCCESS: Imported {len(expenses_to_add)} expense records.")
    else:
        print("No expense files found to import.")

    # --- Add Default User ---
    print("\nStep 3: Checking for default user...")
    if not User.query.filter_by(id='admin').first():
        default_user = User(id='admin', role='admin'); default_user.set_password('admin123')
        db.session.add(default_user); db.session.commit()
        print("SUCCESS: Default user 'admin' created.")
    else:
        print("INFO: Default user 'admin' already exists. No changes made to users.")

    print("\n--- Data Import Command Finished ---")

if __name__ == "__main__":
    app.run()
