import sys
import os

# Add root folder to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from extensions import db
from sqlalchemy import text

with app.app_context():
    try:
        # Run ALTER TABLE query
        query = text("ALTER TABLE ecc_monthly_state ADD COLUMN unit_auth INT DEFAULT 0;")
        db.session.execute(query)
        db.session.commit()
        print("Successfully added column unit_auth to ecc_monthly_state!")
    except Exception as e:
        print("Error running migration:", e)
