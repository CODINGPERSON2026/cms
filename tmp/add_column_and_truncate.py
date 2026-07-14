import sys
import os

sys.path.append(os.path.abspath('.'))

try:
    from app import app, db
    
    with app.app_context():
        from sqlalchemy import text
        # 1. Add column if it doesn't already exist
        print("Checking/Adding Column 'type' in ecc_scme_items...")
        try:
            db.session.execute(text("ALTER TABLE ecc_scme_items ADD COLUMN type VARCHAR(50) NULL"))
            db.session.commit()
            print("Successfully added type column to ecc_scme_items.")
        except Exception as ex:
            db.session.rollback()
            # Likely already exists, check if that's the case
            print("Notice (column may already exist):", ex)

        # 2. Empty the table
        # Since foreign key constraints exist, we disable foreign key checks first
        print("Emptying ecc_scme_items (and dependent transaction rows for consistency)...")
        try:
            db.session.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
            
            # Empty transaction tables that reference these items
            db.session.execute(text("TRUNCATE TABLE ecc_monthly_state"))
            db.session.execute(text("TRUNCATE TABLE scme_issued_items"))
            # Empty the catalog items table
            db.session.execute(text("TRUNCATE TABLE ecc_scme_items"))
            
            db.session.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
            db.session.commit()
            print("Successfully emptied ecc_scme_items, ecc_monthly_state, and scme_issued_items.")
        except Exception as ex:
            db.session.rollback()
            print("Error while emptying tables:", ex)
            
except Exception as e:
    print("Error:", e)
