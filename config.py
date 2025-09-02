import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(basedir, 'annotator.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class Dev(Config): DEBUG = True
class Prod(Config): DEBUG = False
