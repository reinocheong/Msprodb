from mspro_app import create_app
import click
from flask.cli import with_appcontext
from mspro_app.extensions import db
from mspro_app.models import User, Booking, Expense
import pandas as pd
import os
import glob
import uuid
import math

app = create_app()

@app.cli.command("import-data")
@with_appcontext
def import_data_command():
    """Drops all tables, recreates them, and imports data from excel files."""
    print("--- Starting Data Import Command ---")
    
    print("Step 1: Dropping all existing tables...")
    db.drop_all()
    
    print("Step 2: Creating all tables from models...")
    db.create_all()
    print("SUCCESS: All tables created.")

    DATA_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'excel_data')
    print(f"\nStep 3: Reading data from '{DATA_FOLDER}'...")

    # --- Booking Data Processing ---
    all_booking_files = glob.glob(os.path.join(DATA_FOLDER, '*Booking.xlsx'))
    booking_files = [f for f in all_booking_files if not os.path.basename(f).startswith('~$')]
    
    if booking_files:
        all_bookings_df = pd.concat((pd.read_excel(f, engine='openpyxl') for f in booking_files), ignore_index=True)
        print(f"Found and merged {len(booking_files)} booking files. Total rows: {len(all_bookings_df)}")
        
        all_bookings_df.rename(columns={
            'Unit Name': 'unit_name', 'CHECKIN': 'checkin', 'CHECKOUT': 'checkout',
            'Channel': 'channel', 'ON/OFFLINE': 'on_offline', 'Booking Number': 'booking_number',
            'Pax': 'pax', 'Duration': 'duration', 'Price': 'price',
            'CLEANING FEE': 'cleaning_fee', 'Platform Charge': 'platform_charge', 'TOTAL': 'total'
        }, inplace=True)
        
        all_bookings_df['checkin'] = pd.to_datetime(all_bookings_df['checkin'], errors='coerce')
        all_bookings_df['checkout'] = pd.to_datetime(all_bookings_df['checkout'], errors='coerce')
        all_bookings_df.dropna(subset=['checkin', 'checkout'], inplace=True)

        all_bookings_df['pax'] = pd.to_numeric(all_bookings_df['pax'], errors='coerce')
        all_bookings_df['duration'] = pd.to_numeric(all_bookings_df['duration'], errors='coerce')

        INT_MAX = 2147483647
        pax_problems = all_bookings_df['pax'] > INT_MAX
        duration_problems = all_bookings_df['duration'] > INT_MAX
        problematic_rows = all_bookings_df[pax_problems | duration_problems]

        if not problematic_rows.empty:
            all_bookings_df = all_bookings_df[~(pax_problems | duration_problems)]

        all_bookings_df.dropna(subset=['pax', 'duration'], inplace=True)
        all_bookings_df['pax'] = all_bookings_df['pax'].astype(int)
        all_bookings_df['duration'] = all_bookings_df['duration'].astype(int)
        
        model_columns = [c.name for c in Booking.__table__.columns if c.name != 'id']
        final_df = all_bookings_df[all_bookings_df.columns.intersection(model_columns)]

        bookings_to_add = [Booking(**row) for index, row in final_df.iterrows()]
        db.session.bulk_save_objects(bookings_to_add)
        db.session.commit()
        print(f"SUCCESS: Imported {len(bookings_to_add)} booking records.")

    # --- Expense Data Processing (Robust Version) ---
    all_expense_files = glob.glob(os.path.join(DATA_FOLDER, '*expenses.xlsx'))
    expense_files = [f for f in all_expense_files if not os.path.basename(f).startswith('~$')]

    if expense_files:
        all_expenses_df = pd.concat((pd.read_excel(f, engine='openpyxl') for f in expense_files), ignore_index=True)
        print(f"Found and merged {len(expense_files)} expense files. Total rows: {len(all_expenses_df)}")
        
        df = all_expenses_df.copy()

        # Coalesce (merge) columns with different names into one canonical column
        if 'Expenses Date' in df.columns and 'Date' in df.columns:
            df['Date'] = df['Date'].fillna(df['Expenses Date'])
        elif 'Expenses Date' in df.columns:
            df['Date'] = df['Expenses Date']

        if 'PARTICULARS' in df.columns and 'Particulars' in df.columns:
            df['Particulars'] = df['Particulars'].fillna(df['PARTICULARS'])
        elif 'PARTICULARS' in df.columns:
            df['Particulars'] = df['PARTICULARS']

        if 'DEBIT' in df.columns and 'Amount' in df.columns:
            df['Amount'] = df['Amount'].fillna(df['DEBIT'])
        elif 'DEBIT' in df.columns:
            df['Amount'] = df['DEBIT']

        # Final rename to match database model
        df.rename(columns={
            'Date': 'date',
            'Unit Name': 'unit_name',
            'Particulars': 'particulars',
            'Amount': 'debit'
        }, inplace=True)
        
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df['debit'] = pd.to_numeric(df['debit'], errors='coerce')
        df.dropna(subset=['date', 'debit'], inplace=True)

        expense_model_columns = [c.name for c in Expense.__table__.columns if c.name != 'id']
        final_expense_df = df[df.columns.intersection(expense_model_columns)]

        expenses_to_add = [Expense(**row) for index, row in final_expense_df.iterrows()]
        db.session.bulk_save_objects(expenses_to_add)
        db.session.commit()
        print(f"SUCCESS: Imported {len(expenses_to_add)} expense records.")

    # --- Add Default User ---
    print("\nStep 4: Adding default user...")
    if not User.query.filter_by(id='admin').first():
        default_user = User(id='admin', role='admin')
        default_user.set_password('admin123') 
        db.session.add(default_user)
        db.session.commit()
        print("SUCCESS: Default user 'admin' created.")
    else:
        print("INFO: Default user 'admin' already exists.")

    print("\n--- Data Import Command Finished ---")

if __name__ == "__main__":
    app.run()
