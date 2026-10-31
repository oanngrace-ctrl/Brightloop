import os

class Config:
    SECRET_KEY = os.environ.get(
        "SECRET_KEY",
        "brightloop-development-key"
    )

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "sqlite:///brightloop.db"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False