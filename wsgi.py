from mspro_app import create_app
import click
from flask.cli import with_appcontext
from mspro_app.extensions import db
from mspro_app.models import Booking, Expense
import pandas as pd
import os
import glob
import uuid

app = create_app()

@app.cli.command("import-data")
@with_appcontext
def import_data_command():
    """Drops, creates, and imports all data."""
    print("--- Starting Data Import Command ---")
    
    print("Step 1: Dropping all existing tables...")
    db.drop_all()
    
    print("Step 2: Creating all tables from models...")
    db.create_all()
    print("SUCCESS: All tables created.")

    DATA_FOLDER = "excel_data"
    
    # ... (The rest of the import logic) ...
    print("\n--- Data Import Command Finished ---")

if __name__ == "__main__":
    app.run()