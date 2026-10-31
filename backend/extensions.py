from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

# Database extension
db = SQLAlchemy()

# Login management extension
login_manager = LoginManager()
login_manager.login_view = "main.login"
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "warning"