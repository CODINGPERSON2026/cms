import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from extensions import db
from models.login_users import User

with app.app_context():
    users = User.query.all()
    if not users:
        print("No users in User table")
    for u in users:
        print(f"User: {u.username}, Role: {u.role}")
