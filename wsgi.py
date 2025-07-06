from mspro_app import create_app
import click
from flask.cli import with_appcontext
from mspro_app.extensions import db
from mspro_app.models import User, Booking, Expense
import pandas as pd
import os
import glob
import uuid

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
    
    if not booking_files:
        print("WARNING: No valid Booking excel files found.")
    else:
        all_bookings_df = pd.concat(
            (pd.read_excel(f, engine='openpyxl') for f in booking_files), 
            ignore_index=True
        )
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

        # --- Data Validation and Cleaning ---
        all_bookings_df['pax'] = pd.to_numeric(all_bookings_df['pax'], errors='coerce')
        all_bookings_df['duration'] = pd.to_numeric(all_bookings_df['duration'], errors='coerce')

        INT_MAX = 2147483647
        pax_problems = all_bookings_df['pax'] > INT_MAX
        duration_problems = all_bookings_df['duration'] > INT_MAX
        problematic_rows = all_bookings_df[pax_problems | duration_problems]

        if not problematic_rows.empty:
            print("\n--- WARNING: Found Data Quality Issues ---")
            print("The following rows contain 'pax' or 'duration' values that are too large for the database:")
            print(problematic_rows[['unit_name', 'checkin', 'pax', 'duration']])
            all_bookings_df = all_bookings_df[~(pax_problems | duration_problems)]
            print(f"\nFiltered out {len(problematic_rows)} problematic rows. Continuing with {len(all_bookings_df)} valid rows.")

        all_bookings_df.dropna(subset=['pax', 'duration'], inplace=True)
        all_bookings_df['pax'] = all_bookings_df['pax'].astype(int)
        all_bookings_df['duration'] = all_bookings_df['duration'].astype(int)
        
        model_columns = [c.name for c in Booking.__table__.columns if c.name != 'id']
        final_df = all_bookings_df[all_bookings_df.columns.intersection(model_columns)]

        bookings_to_add = [Booking(**row) for index, row in final_df.iterrows()]
        db.session.bulk_save_objects(bookings_to_add)
        db.session.commit()
        print(f"SUCCESS: Imported {len(bookings_to_add)} booking records.")

    # --- Expense Data Processing ---
    all_expense_files = glob.glob(os.path.join(DATA_FOLDER, '*expenses.xlsx'))
    expense_files = [f for f in all_expense_files if not os.path.basename(f).startswith('~$')]

    if not expense_files:
        print("WARNING: No valid expense excel files found.")
    else:
        all_expenses_df = pd.concat(
            (pd.read_excel(f, engine='openpyxl') for f in expense_files), 
            ignore_index=True
        )
        print(f"Found and merged {len(expense_files)} expense files. Total rows: {len(all_expenses_df)}")
        
        all_expenses_df.rename(columns={
            'Date': 'date', 'Unit Name': 'unit_name', 'Particulars': 'particulars', 'Debit': 'debit'
        }, inplace=True)
        
        all_expenses_df['date'] = pd.to_datetime(all_expenses_df['date'], errors='coerce')
        all_expenses_df.dropna(subset=['date'], inplace=True)

        expense_model_columns = [c.name for c in Expense.__table__.columns if c.name != 'id']
        final_expense_df = all_expenses_df[all_expenses_df.columns.intersection(expense_model_columns)]

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