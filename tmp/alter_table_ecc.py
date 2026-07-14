import sys
import os

sys.path.append(os.path.abspath('.'))

try:
    from app import app, db
    
    with app.app_context():
        # Execute query to add deficiency column to ecc_monthly_state table
        db.session.execute(db.text("ALTER TABLE ecc_monthly_state ADD COLUMN deficiency INT NOT NULL DEFAULT 0;"))
        db.session.commit()
        print("Successfully added deficiency column to ecc_monthly_state table in MySQL.")
except Exception as e:
    print("Error (column might already exist):", e)
