from app import db
from datetime import datetime
from sqlalchemy import JSON
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # Authentication fields
    username = db.Column(db.String(64), unique=True)
    email = db.Column(db.String(120), unique=True)
    password_hash = db.Column(db.String(256))
    is_active = db.Column(db.Boolean, default=True)
    is_authenticated = db.Column(db.Boolean, default=False)
    # For non-authenticated users
    session_id = db.Column(db.String(64), unique=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # User preferences stored as JSON
    preferences = db.Column(JSON, default=list)
    # Store quiz results
    quiz_results = db.Column(JSON, default=dict)
    # Store "This or That" quiz results as list of chosen movie IDs
    this_or_that_choices = db.Column(JSON, default=list)
    # Store watch history as a list of movie IDs
    watch_history = db.Column(JSON, default=list)
    # Store ratings as {movie_id: rating}
    ratings = db.Column(JSON, default=dict)
    # Store total watch time in minutes for year-end report
    total_watch_time = db.Column(db.Integer, default=0)
    # Store last login date for year-end report
    last_login = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Movie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tmdb_id = db.Column(db.Integer, unique=True)
    title = db.Column(db.String(255), nullable=False)
    overview = db.Column(db.Text)
    release_date = db.Column(db.Date)
    poster_path = db.Column(db.String(255))
    backdrop_path = db.Column(db.String(255))
    genres = db.Column(JSON, default=list)
    vote_average = db.Column(db.Float)
    vote_count = db.Column(db.Integer)
    # Additional fields for ML features
    keywords = db.Column(JSON, default=list)
    cast = db.Column(JSON, default=list)
    directors = db.Column(JSON, default=list)
    # Store when the movie data was last updated
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

class UserMovieInteraction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    movie_id = db.Column(db.Integer, db.ForeignKey('movie.id'), nullable=False)
    rating = db.Column(db.Float)
    watched = db.Column(db.Boolean, default=False)
    watch_date = db.Column(db.DateTime)
    # Prediction of how much the user might like this movie (1-10)
    predicted_rating = db.Column(db.Float)
    # When this prediction was made
    prediction_date = db.Column(db.DateTime)
