from dotenv import load_dotenv
from sqlalchemy.engine import URL
import os

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")

    SQLALCHEMY_DATABASE_URI = URL.create(
        drivername=os.getenv("DB_DRIVER"),
        username=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False