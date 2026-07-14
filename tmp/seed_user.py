import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from extensions import db
from models.login_users import User

with app.app_context():
    existing = User.query.filter_by(username='scme').first()
    if not existing:
        print("Creating user 'scme'...")
        new_u = User(username='scme', password='123', role='scme')
        db.session.add(new_u)
        db.session.commit()
        print("User 'scme' created successfully with password '123'!")
    else:
        print(f"User 'scme' already exists. Password: {existing.password}, Role: {existing.role}")
