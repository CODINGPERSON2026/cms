import sys
import os

sys.path.append(os.path.abspath('.'))

try:
    from app import app, db
    
    with app.app_context():
        from sqlalchemy import text
        res = db.session.execute(text("SELECT * FROM users")).all()
        print("Columns description:")
        print(res[0].keys() if res else "No columns")
        print("Users details:")
        for r in res:
            print(dict(r._mapping))
except Exception as e:
    print("Error:", e)
