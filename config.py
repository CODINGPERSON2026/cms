from sqlalchemy.engine import URL

class Config:
    SECRET_KEY = "your-super-secret-key"

    SQLALCHEMY_DATABASE_URI = URL.create(
        drivername="mysql+pymysql",
        username="root",
        password="qaz123QAZ!@#",
        host="localhost",
        database="cms"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False