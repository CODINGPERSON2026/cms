import sys
import os

sys.path.append(os.path.abspath('.'))

try:
    from app import app, db
    from models.our_items import ScmeItems
    
    with app.app_context():
        # Count items grouped by type and category
        from sqlalchemy import func
        res = db.session.query(
            ScmeItems.type, ScmeItems.category, func.count(ScmeItems.id)
        ).group_by(ScmeItems.type, ScmeItems.category).all()
        
        print("Seeded Items Summary:")
        for r in res:
            print(f"  Type: {r[0]}, Category: {r[1]}, Count: {r[2]}")
except Exception as e:
    print("Error:", e)
