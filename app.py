import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager

# Set up logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "modex-development-key")

# ✅ Configure the database
database_url = os.environ.get("DATABASE_URL")

if not database_url:
    # Fallback to SQLite for local development
    database_url = "sqlite:///cinemasync.db"
elif database_url.startswith("postgres://"):
    # Fix PostgreSQL URL format (for Heroku)
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize the app with the extension
db.init_app(app)

# Set up TMDB API key from environment or use default key
app.config["TMDB_API_KEY"] = os.environ.get("TMDB_API_KEY", "52a7843a92a4a748cda06c930a191f9e")

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Specify the login route

@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

# ✅ Create database tables when app starts
with app.app_context():
    # Import models here to ensure they're registered with SQLAlchemy
    import models
    db.create_all()

# @app.route("/init-db")
# def init_db():
#     db.create_all()
#     return "Database initialized!"
