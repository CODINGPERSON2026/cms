import sys
import os

sys.path.append(os.path.abspath('.'))

try:
    from app import app, db
    from models.login_users import User
    
    with app.app_context():
        scme_users = User.query.filter_by(role='scme').all()
        print("SCME Users in DB:")
        for u in scme_users:
            print(f"  Username: {u.username}, Password: {u.password}")
except Exception as e:
    print("Error:", e)
