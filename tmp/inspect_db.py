import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from extensions import db
from sqlalchemy import text

with app.app_context():
    try:
        # Show columns for ecc_monthly_state
        res = db.session.execute(text("DESCRIBE ecc_monthly_state;")).fetchall()
        print("Columns in ecc_monthly_state:")
        for col in res:
            print(f"  - {col[0]}: {col[1]}")
            
        # Select first row
        row = db.session.execute(text("SELECT * FROM ecc_monthly_state LIMIT 1;")).fetchone()
        if row:
            print("\nFirst row contents:")
            keys = row._mapping.keys()
            for key in keys:
                print(f"  {key}: {row._mapping[key]}")
        else:
            print("\nNo rows in ecc_monthly_state.")
    except Exception as e:
        print("Error inspecting database:", e)
