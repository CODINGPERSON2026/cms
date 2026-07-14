import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from extensions import db
from models.our_items import Units

with app.app_context():
    all_units = Units.query.all()
    print("Units count:", len(all_units))
    for u in all_units:
        print(f"ID: {u.id}, Name: {u.name}")
