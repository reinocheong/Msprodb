import pandas as pd
import os
import glob

def diagnose_excel_data():
    """
    Diagnoses booking Excel files to find integer values that are out of range.
    """
    print("--- Starting Data Diagnosis Script ---")
    
    DATA_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'excel_data')
    booking_files = [f for f in glob.glob(os.path.join(DATA_FOLDER, '*Booking.xlsx')) if not os.path.basename(f).startswith('~$')]

    if not booking_files:
        print("No booking files found to diagnose.")
        return

    print(f"Found {len(booking_files)} booking files. Starting diagnosis...")

    # The standard range for a 32-bit signed integer in most databases
    INT_MAX = 2147483647
    INT_MIN = -2147483648
    error_found = False

    for file_path in booking_files:
        print(f"\nDiagnosing file: {os.path.basename(file_path)}")
        try:
            df = pd.read_excel(file_path, engine='openpyxl')
            
            columns_to_check = ['Pax', 'Duration']
            
            for col_name in columns_to_check:
                if col_name in df.columns:
                    for index, value in df[col_name].items():
                        # Skip empty cells
                        if pd.isna(value):
                            continue

                        try:
                            # Attempt to convert to a number, this handles strings that look like numbers
                            numeric_value = float(value)
                        except (ValueError, TypeError):
                            # This cell contains non-numeric text, which is not our target error
                            continue
                        
                        if not (INT_MIN <= numeric_value <= INT_MAX):
                            print("\n" + "="*50)
                            print("!!! INTEGER OUT OF RANGE ERROR FOUND !!!")
                            print(f"  File:                {os.path.basename(file_path)}")
                            print(f"  Excel Row Number:    {index + 2}")  # +2 because index is 0-based and header is row 1
                            print(f"  Column Name:         '{col_name}'")
                            print(f"  Problematic Value:   {value}")
                            print("  Reason:              This value is outside the standard 32-bit integer range.")
                            print("="*50 + "\n")
                            error_found = True
                            
        except Exception as e:
            print(f"Could not process file {os.path.basename(file_path)}. Error: {e}")

    if not error_found:
        print("\n--- Diagnosis Complete: No out-of-range integer values were found. ---")
    else:
        print("\n--- Diagnosis Complete: Found one or more potential errors as listed above. ---")


if __name__ == "__main__":
    diagnose_excel_data()