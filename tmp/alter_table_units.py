import sys
import os
from sqlalchemy import text

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from extensions import db

with app.app_context():
    # Try to add authorized_strength column
    try:
        db.session.execute(text("ALTER TABLE units ADD COLUMN authorized_strength INT DEFAULT 0"))
        db.session.commit()
        print("Added authorized_strength column successfully")
    except Exception as e:
        db.session.rollback()
        print("authorized_strength column error/already exists:", e)

    # Try to add posted_strength column
    try:
        db.session.execute(text("ALTER TABLE units ADD COLUMN posted_strength INT DEFAULT 0"))
        db.session.commit()
        print("Added posted_strength column successfully")
    except Exception as e:
        db.session.rollback()
        print("posted_strength column error/already exists:", e)

    # Update dummy values for authorized_strength and posted_strength
    updates = [
        ("19 INF DIV", 15000, 14200),
        ("28 INF DIV", 12000, 11500),
        ("KFSR", 8000, 7700),
        ("VFSR", 9500, 9100),
        ("2 FOD", 3500, 3200),
        ("28 MOU", 4000, 3800)
    ]

    for name, auth, posted in updates:
        try:
            db.session.execute(
                text("UPDATE units SET authorized_strength = :auth, posted_strength = :posted WHERE UPPER(name) = :name"),
                {"auth": auth, "posted": posted, "name": name.upper()}
            )
            db.session.commit()
            print(f"Updated {name}: auth={auth}, posted={posted}")
        except Exception as e:
            db.session.rollback()
            print(f"Error updating {name}:", e)

print("MySQL Alteration finished successfully!")
