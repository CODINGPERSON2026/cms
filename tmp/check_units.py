import sys
import os

sys.path.append(os.path.abspath('.'))

try:
    from app import app, db
    from models.our_items import Units
    
    with app.app_context():
        units = Units.query.all()
        print("Units in DB:")
        for u in units:
            print(f"  ID: {u.id}, Name: {u.name}")
except Exception as e:
    print("Error:", e)
