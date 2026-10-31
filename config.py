from sqlalchemy.engine import URL
from datetime import timedelta

class Config:
    SECRET_KEY = "dev-secret-key-change-in-production"
    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)

    SQLALCHEMY_DATABASE_URI = URL.create(
        drivername="mysql+pymysql",
        username="root",
        password="yawar@123",
        host="127.0.0.1",
        port=3306,
        database="cms",
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    CONDEMNATION_UPLOAD_FOLDER = r"C:\Condemnation_pdf"