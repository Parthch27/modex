import uuid
import logging
import pandas as pd
from datetime import datetime, timedelta
from flask import render_template, request, redirect, url_for, jsonify, session, flash
from flask_login import login_user, logout_user, current_user, login_required
from urllib.parse import urlparse
from app import app, db
from models import User, Movie, UserMovieInteraction
from movie_api import TMDBApi
from recommendation import MovieRecommender, MoodBasedRecommender
from forms import LoginForm, RegistrationForm

# Set up logging
logger = logging.getLogger(__name__)

# Initialize API and recommenders
tmdb_api = TMDBApi()
movie_recommender = MovieRecommender()
mood_recommender = MoodBasedRecommender()

# Ensure user has a session
def get_user_session():
    """Get or create a user session"""
    # If user is authenticated, return current user
    if current_user.is_authenticated:
        return current_user
        
    # Otherwise, use session-based anonymous user
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
        
    user = User.query.filter_by(session_id=session['session_id']).first()
    
    if not user:
        user = User(session_id=session['session_id'])
        db.session.add(user)
        db.session.commit()
        
    return user

# User Registration route
@app.route('/register', methods=['GET', 'POST'])
def register():
    # If user is already authenticated, redirect to home
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data, 
            email=form.email.data,
            is_active=True,
            is_authenticated=True,
            session_id=str(uuid.uuid4())  # Generate a unique session ID
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!', 'success')
        return redirect(url_for('login'))
        
    return render_template('register.html', title='Register', form=form)

# User Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    # If user is already authenticated, redirect to home
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        
        # Check if user exists and password is correct
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password', 'danger')
            return redirect(url_for('login'))
            
        # Log in the user
        login_user(user, remember=form.remember_me.data)
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        # Handle next page redirection
        next_page = request.args.get('next')
        if not next_page or urlparse(next_page).netloc != '':
            next_page = url_for('index')
            
        flash(f'Welcome back, {user.username}!', 'success')
        return redirect(next_page)
        
    return render_template('login.html', title='Sign In', form=form)

# User Logout route
@app.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

# User Dashboard route
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', title='Dashboard')

# Initialize movie recommender system with existing movies
def initialize_recommender():
    """Initialize the movie recommender with data from our database"""
    try:
        movies = Movie.query.all()
        if movies:
            # Convert movies to list of dictionaries
            movies_data = []
            for movie in movies:
                movie_dict = {
                    'id': movie.tmdb_id,
                    'title': movie.title,
                    'overview': movie.overview,
                    'genres': movie.genres,
                    'keywords': movie.keywords,
                    'cast': movie.cast,
                    'directors': movie.directors
                }
                movies_data.append(movie_dict)
            
            # Fit the recommender
            success = movie_recommender.fit(movies_data)
            if success:
                logger.info(f"Recommender system initialized with {len(movies_data)} movies")
            else:
                logger.error("Failed to initialize recommender system")
    except Exception as e:
        logger.error(f"Error initializing recommender: {str(e)}")

# Home page route
@app.route('/')
def index():
    user = get_user_session()
    
    # Get trending movies
    trending_data = tmdb_api.get_trending_movies()
    trending_movies = []
    
    if trending_data and 'results' in trending_data:
        trending_movies = trending_data['results'][:10]  # Get top 10
        
        # Store these movies in our database if not already there
        for movie_data in trending_movies:
            # Check if we already have this movie
            existing_movie = Movie.query.filter_by(tmdb_id=movie_data['id']).first()
            
            if not existing_movie:
                # Get full movie details
                full_movie = tmdb_api.get_movie_details(movie_data['id'])
                
                if full_movie:
                    # Format movie data for our schema
                    formatted_movie = tmdb_api.format_movie_data(full_movie)
                    
                    if formatted_movie:
                        # Create new movie record
                        new_movie = Movie(**formatted_movie)
                        db.session.add(new_movie)
        
        # Commit all new movies
        db.session.commit()
    
    # Get top rated movies
    top_rated_data = tmdb_api.get_top_rated()
    top_rated_movies = []
    
    if top_rated_data and 'results' in top_rated_data:
        top_rated_movies = top_rated_data['results'][:10]  # Get top 10
    
    # Get personalized recommendations if user has watch history
    personalized_movies = []
    if user.watch_history:
        # Initialize recommender if needed
        if movie_recommender.movies_df is None:
            initialize_recommender()
        
        # Get personalized recommendations
        recommended_ids = movie_recommender.get_personalized_recommendations(
            user.watch_history, 
            user.ratings,
            n=10
        )
        
        # Get movie details for recommendations
        for movie_id in recommended_ids:
            movie = Movie.query.filter_by(tmdb_id=movie_id).first()
            if movie:
                # Convert to dict for template
                movie_dict = {
                    'id': movie.tmdb_id,
                    'title': movie.title,
                    'poster_path': movie.poster_path,
                    'vote_average': movie.vote_average
                }
                personalized_movies.append(movie_dict)
    
    return render_template(
        'index.html',
        trending_movies=trending_movies,
        top_rated_movies=top_rated_movies,
        personalized_movies=personalized_movies
    )

# Movie details route
@app.route('/movie/<int:movie_id>')
def movie_details(movie_id):
    user = get_user_session()
    
    # Check if movie exists in our database
    movie = Movie.query.filter_by(tmdb_id=movie_id).first()
    
    # If not, fetch from API and store
    if not movie:
        movie_data = tmdb_api.get_movie_details(movie_id)
        
        if not movie_data:
            flash("Movie not found", "error")
            return redirect(url_for('index'))
        
        formatted_movie = tmdb_api.format_movie_data(movie_data)
        
        if formatted_movie:
            movie = Movie(**formatted_movie)
            db.session.add(movie)
            db.session.commit()
    
    # Get similar movies
    similar_movies = []
    
    # Initialize recommender if needed
    if movie_recommender.movies_df is None:
        initialize_recommender()
    
    # Get recommendations based on this movie
    if movie_recommender.movies_df is not None:
        similar_ids = movie_recommender.get_recommendations(movie.tmdb_id, n=6)
        
        for similar_id in similar_ids:
            similar_movie = Movie.query.filter_by(tmdb_id=similar_id).first()
            if similar_movie:
                similar_movies.append({
                    'id': similar_movie.tmdb_id,
                    'title': similar_movie.title,
                    'poster_path': similar_movie.poster_path
                })
    
    # Check if user has watched this movie
    interaction = UserMovieInteraction.query.filter_by(
        user_id=user.id,
        movie_id=movie.id
    ).first()
    
    watched = False
    user_rating = None
    predicted_rating = None
    
    if interaction:
        watched = interaction.watched
        user_rating = interaction.rating
    else:
        # Predict rating if user has watch history
        if user.watch_history and movie_recommender.movies_df is not None:
            predicted_rating = movie_recommender.predict_rating(user.watch_history, movie.tmdb_id)
            
            # Store the prediction
            interaction = UserMovieInteraction(
                user_id=user.id,
                movie_id=movie.id,
                predicted_rating=predicted_rating,
                prediction_date=datetime.utcnow()
            )
            db.session.add(interaction)
            db.session.commit()
    
    # Convert movie data for template
    movie_data = {
        'id': movie.tmdb_id,
        'title': movie.title,
        'overview': movie.overview,
        'release_date': movie.release_date,
        'poster_path': movie.poster_path,
        'backdrop_path': movie.backdrop_path,
        'genres': movie.genres,
        'vote_average': movie.vote_average,
        'vote_count': movie.vote_count,
        'cast': movie.cast[:8] if movie.cast else [],  # Only top 8 cast members
        'directors': movie.directors
    }
    
    return render_template(
        'movie_details.html',
        movie=movie_data,
        similar_movies=similar_movies,
        watched=watched,
        user_rating=user_rating,
        predicted_rating=predicted_rating
    )

# Mark movie as watched
@app.route('/movie/<int:movie_id>/watched', methods=['POST'])
def mark_watched(movie_id):
    user = get_user_session()
    
    # Get movie from database
    movie = Movie.query.filter_by(tmdb_id=movie_id).first()
    
    if not movie:
        return jsonify({'success': False, 'error': 'Movie not found'}), 404
    
    # Check if interaction exists
    interaction = UserMovieInteraction.query.filter_by(
        user_id=user.id,
        movie_id=movie.id
    ).first()
    
    if interaction:
        interaction.watched = True
        interaction.watch_date = datetime.utcnow()
    else:
        interaction = UserMovieInteraction(
            user_id=user.id,
            movie_id=movie.id,
            watched=True,
            watch_date=datetime.utcnow()
        )
        db.session.add(interaction)
    
    # Initialize watch_history as a list if None or not a list
    if user.watch_history is None:
        user.watch_history = []
    
    # Add to user's watch history if not already there
    # Convert to string for consistent comparison
    str_movie_id = str(movie.tmdb_id)
    watch_history_ids = [str(movie_id) for movie_id in user.watch_history]
    
    if str_movie_id not in watch_history_ids:
        user.watch_history.append(movie.tmdb_id)
        
    # Update total watch time (assume average movie is 120 minutes)
    if user.total_watch_time is None:
        user.total_watch_time = 0
    user.total_watch_time += 120
    
    db.session.commit()
    
    # Log success for debugging
    logger.debug(f"Movie {movie_id} marked as watched. User watch history: {user.watch_history}")
    
    return jsonify({'success': True})

# Rate movie
@app.route('/movie/<int:movie_id>/rate', methods=['POST'])
def rate_movie(movie_id):
    user = get_user_session()
    
    # Get rating from form
    try:
        rating = float(request.form.get('rating', 0))
    except ValueError:
        return jsonify({'success': False, 'error': 'Invalid rating'}), 400
    
    # Validate rating
    if rating < 1 or rating > 10:
        return jsonify({'success': False, 'error': 'Rating must be between 1 and 10'}), 400
    
    # Get movie from database
    movie = Movie.query.filter_by(tmdb_id=movie_id).first()
    
    if not movie:
        return jsonify({'success': False, 'error': 'Movie not found'}), 404
    
    # Check if interaction exists
    interaction = UserMovieInteraction.query.filter_by(
        user_id=user.id,
        movie_id=movie.id
    ).first()
    
    if interaction:
        interaction.rating = rating
    else:
        interaction = UserMovieInteraction(
            user_id=user.id,
            movie_id=movie.id,
            rating=rating
        )
        db.session.add(interaction)
    
    # Initialize ratings as a dictionary if it doesn't exist
    if not user.ratings:
        user.ratings = {}
    
    # Add to user's ratings
    user.ratings[str(movie.tmdb_id)] = rating
    
    # Also mark as watched if it's not already in watch history
    # Initialize watch_history as a list if None
    if user.watch_history is None:
        user.watch_history = []
    
    # Add to user's watch history if not already there (when rating a movie, we assume it's watched)
    str_movie_id = str(movie.tmdb_id)
    watch_history_ids = [str(m_id) for m_id in user.watch_history]
    
    if str_movie_id not in watch_history_ids:
        user.watch_history.append(movie.tmdb_id)
        
        # Also update the interaction to mark as watched
        interaction.watched = True
        interaction.watch_date = datetime.utcnow()
        
        # Update total watch time (assume average movie is 120 minutes)
        if user.total_watch_time is None:
            user.total_watch_time = 0
        user.total_watch_time += 120
    
    db.session.commit()
    
    # Log success for debugging
    logger.debug(f"Movie {movie_id} rated {rating}. User ratings: {user.ratings}")
    
    return jsonify({'success': True})

# Search route
@app.route('/search')
def search():
    query = request.args.get('query', '')
    
    if not query:
        return render_template('index.html')
    
    # Search movies via API
    search_data = tmdb_api.search_movies(query)
    search_results = []
    
    if search_data and 'results' in search_data:
        search_results = search_data['results']
    
    return render_template('recommendations.html', movies=search_results, title="Search Results")

# Quiz route
@app.route('/quiz')
def quiz():
    return render_template('quiz.html')

# Process quiz results
@app.route('/quiz/process', methods=['POST'])
def process_quiz():
    user = get_user_session()
    
    # Get quiz answers from form
    quiz_results = {
        'day': request.form.get('day', 'calm'),
        'color': request.form.get('color', 'blue'),
        'movie': request.form.get('movie', 'adventure'),
        'stress': request.form.get('stress', 'watching'),
        'weather': request.form.get('weather', 'sunny')
    }
    
    # Store quiz results for user
    user.quiz_results = quiz_results
    db.session.commit()
    
    # Get movies from database for mood-based recommendations
    movies = Movie.query.all()
    
    if not movies:
        # If no movies in database, fetch trending as fallback
        trending_data = tmdb_api.get_trending_movies(page=1)
        
        if trending_data and 'results' in trending_data:
            for movie_data in trending_data['results']:
                full_movie = tmdb_api.get_movie_details(movie_data['id'])
                
                if full_movie:
                    formatted_movie = tmdb_api.format_movie_data(full_movie)
                    
                    if formatted_movie:
                        new_movie = Movie(**formatted_movie)
                        db.session.add(new_movie)
            
            db.session.commit()
            movies = Movie.query.all()
    
    # Convert movies to pandas DataFrame for mood recommender
    movies_data = []
    for movie in movies:
        movie_dict = {
            'id': movie.tmdb_id,
            'title': movie.title,
            'genres': movie.genres,
            'vote_average': movie.vote_average
        }
        movies_data.append(movie_dict)
    
    movies_df = pd.DataFrame(movies_data)
    
    # Get mood-based recommendations
    recommended_ids = mood_recommender.get_mood_based_recommendations(
        movies_df, 
        quiz_results,
        n=12
    )
    
    # Get movie details for recommendations
    recommended_movies = []
    for movie_id in recommended_ids:
        movie = Movie.query.filter_by(tmdb_id=movie_id).first()
        if movie:
            recommended_movies.append({
                'id': movie.tmdb_id,
                'title': movie.title,
                'poster_path': movie.poster_path,
                'vote_average': movie.vote_average,
                'release_date': movie.release_date,
                'genres': movie.genres
            })
    
    return render_template(
        'recommendations.html', 
        movies=recommended_movies, 
        title="Your Mood-Based Recommendations"
    )

# This or That movie preference quiz
@app.route('/this-or-that')
def this_or_that():
    user = get_user_session()
    
    # Only show this feature to authenticated users
    if not current_user.is_authenticated:
        flash("Please login to access the movie preference quiz.", "info")
        return redirect(url_for('login'))
    
    # Get 10 random movies from database released at least 6 months ago
    # Filter by release_date <= 6 months ago
    six_months_ago = datetime.now() - timedelta(days=180)
    movies = Movie.query.filter(
        Movie.release_date <= six_months_ago
    ).order_by(db.func.random()).limit(20).all()
    
    if len(movies) < 2:
        # If not enough movies in database, fetch more from API that are at least 6 months old
        for page in range(1, 4):  # Fetch up to 3 pages to ensure enough variety
            older_movies_data = tmdb_api.get_movies_released_before_six_months(page=page)
            
            if older_movies_data and 'results' in older_movies_data:
                for movie_data in older_movies_data['results']:
                    # Check if we already have this movie
                    existing = Movie.query.filter_by(tmdb_id=movie_data['id']).first()
                    if not existing:
                        full_movie = tmdb_api.get_movie_details(movie_data['id'])
                        
                        if full_movie:
                            formatted_movie = tmdb_api.format_movie_data(full_movie)
                            
                            if formatted_movie:
                                new_movie = Movie(**formatted_movie)
                                db.session.add(new_movie)
        
        db.session.commit()
        # Try again to get movies now that we've added some
        movies = Movie.query.filter(
            Movie.release_date <= six_months_ago
        ).order_by(db.func.random()).limit(20).all()
    
    # Get two random movies
    movie1 = movies[0] if len(movies) > 0 else None
    movie2 = movies[1] if len(movies) > 1 else None
    
    if not movie1 or not movie2:
        flash("Not enough movies available for the quiz. Please try again later.", "error")
        return redirect(url_for('index'))
    
    # Generate a quiz ID to track this pair
    quiz_id = str(uuid.uuid4())
    
    # Calculate progress based on number of choices made so far
    total_questions = 5  # Updated to 5 selections per user request
    
    # Ensure unique selections are counted for progress
    unique_choices = set()
    if user.this_or_that_choices:
        unique_choices = set(str(choice_id) for choice_id in user.this_or_that_choices)
    
    current_progress = len(unique_choices)
    
    # Check if user already has 5 or more selections
    if current_progress >= total_questions:
        logger.debug(f"User already has {current_progress} selections - redirecting to recommendations")
        return redirect(url_for('recommendations'))
    
    current_question = min(current_progress + 1, total_questions)
    progress = (current_progress / total_questions) * 100
    
    # Log for debugging
    logger.debug(f"Current progress: {current_progress}/{total_questions} unique selections")
    logger.debug(f"Unique choices: {unique_choices}")
    
    # Check if quiz is completed
    completed = request.args.get('completed', 'false') == 'true'
    
    return render_template(
        'this_or_that.html',
        movie1=movie1,
        movie2=movie2,
        quiz_id=quiz_id,
        current_question=current_question,
        total_questions=total_questions,
        progress=progress,
        completed=completed
    )

# Process This or That choice
@app.route('/this-or-that/process', methods=['POST'])
def process_this_or_that():
    user = get_user_session()
    
    choice = request.form.get('choice')
    current_question = int(request.form.get('current_question', 1))
    
    # Skip if user clicked skip
    if choice != 'skip':
        # Get the chosen movie - this is the database ID, not the tmdb_id
        movie = Movie.query.filter_by(id=int(choice)).first()
        
        if movie:
            # Initialize this_or_that_choices as a list if None
            if user.this_or_that_choices is None:
                user.this_or_that_choices = []
            
            # Convert to string for consistent comparison
            str_movie_id = str(movie.tmdb_id)
            choice_ids = [str(movie_id) for movie_id in user.this_or_that_choices]
            
            if str_movie_id not in choice_ids:
                # Make a copy of the list, modify it, then assign it back (for SQLAlchemy to detect the change)
                current_choices = user.this_or_that_choices.copy() if user.this_or_that_choices else []
                current_choices.append(movie.tmdb_id)
                user.this_or_that_choices = current_choices
                
                # Log for debugging
                logger.debug(f"Added movie {movie.tmdb_id} to This or That choices")
                logger.debug(f"Current choices after adding: {user.this_or_that_choices}")
                
                db.session.add(user)
                db.session.commit()
    
    # Check if quiz is completed - count unique selections
    unique_selections = set()
    if user.this_or_that_choices:
        unique_selections = set(str(choice_id) for choice_id in user.this_or_that_choices)
    
    logger.debug(f"Checking completion: {len(unique_selections)}/5 unique selections made")
    
    logger.debug(f"Checking for completion - unique selections: {len(unique_selections)}")
    
    if len(unique_selections) >= 5:  # Check for 5 unique selections
        logger.debug(f"Selection condition met! Redirecting to recommendations")
        # Update user preferences based on their choices
        if user.this_or_that_choices:
            # Add selected movies to user's watch history if not already there
            if user.watch_history is None:
                user.watch_history = []
                
            for movie_id in user.this_or_that_choices:
                # Get the movie from database
                movie = Movie.query.filter_by(tmdb_id=int(movie_id)).first()
                
                if movie:
                    # Add to watch history if not already there
                    str_movie_id = str(movie.tmdb_id)
                    watch_history_ids = [str(m_id) for m_id in user.watch_history]
                    
                    if str_movie_id not in watch_history_ids:
                        # Make a copy, modify it, then reassign (for SQLAlchemy to detect the change)
                        current_history = user.watch_history.copy() if user.watch_history else []
                        current_history.append(movie.tmdb_id)
                        user.watch_history = current_history
                        
                        # Update total watch time
                        if user.total_watch_time is None:
                            user.total_watch_time = 0
                        user.total_watch_time += 120
                        
                        # Also create an interaction record
                        interaction = UserMovieInteraction.query.filter_by(
                            user_id=user.id,
                            movie_id=movie.id
                        ).first()
                        
                        if not interaction:
                            interaction = UserMovieInteraction(
                                user_id=user.id,
                                movie_id=movie.id,
                                watched=True,
                                watch_date=datetime.utcnow()
                            )
                            db.session.add(interaction)
            
            # Extract genres from chosen movies for user preferences
            chosen_movies = Movie.query.filter(Movie.tmdb_id.in_(user.this_or_that_choices)).all()
            
            # Extract genres from chosen movies
            genre_counts = {}
            for movie in chosen_movies:
                for genre_data in movie.genres:
                    # Handle genre being a dictionary with 'id' and 'name' keys
                    if isinstance(genre_data, dict) and 'name' in genre_data:
                        genre_name = genre_data['name']
                        if genre_name in genre_counts:
                            genre_counts[genre_name] += 1
                        else:
                            genre_counts[genre_name] = 1
                    # Also handle the case where it might be just a string
                    elif isinstance(genre_data, str):
                        if genre_data in genre_counts:
                            genre_counts[genre_data] += 1
                        else:
                            genre_counts[genre_data] = 1
            
            # Log for debugging
            logger.debug(f"Genre counts collected: {genre_counts}")
            
            # Sort genres by frequency
            sorted_genres = sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)
            
            # Update user preferences with top genres - reassign to trigger SQLAlchemy change detection
            new_preferences = [genre for genre, count in sorted_genres[:5]]
            user.preferences = new_preferences
            logger.debug(f"Setting user preferences to: {new_preferences}")
            
            # Log for debugging
            logger.debug(f"User preferences updated to: {user.preferences}")
            logger.debug(f"User watch history now: {user.watch_history}")
            
            db.session.commit()
        
        # Directly redirect to recommendations instead of showing the completion modal
        logger.debug("Redirecting to recommendations page")
        return redirect(url_for('recommendations'))
    else:
        return redirect(url_for('this_or_that'))

# Year-End User Report route
@app.route('/year-end-report')
def year_end_report():
    user = get_user_session()
    
    # If user has no watch history, redirect to discover page
    if not user.watch_history or len(user.watch_history) < 3:
        flash("Watch at least 3 movies to generate your year-end report.", "info")
        return redirect(url_for('index'))
    
    # Get user's watched movies
    watched_movies = []
    for movie_id in user.watch_history:
        movie = Movie.query.filter_by(tmdb_id=movie_id).first()
        if movie:
            # Get user rating if available
            user_rating = user.ratings.get(str(movie_id), None) if user.ratings else None
            
            watched_movies.append({
                'id': movie.id,
                'tmdb_id': movie.tmdb_id,
                'title': movie.title,
                'poster_path': movie.poster_path,
                'genres': movie.genres,
                'release_date': movie.release_date,
                'user_rating': user_rating
            })
    
    # Get user's top rated movies
    top_movies = []
    if user.ratings:
        # Sort movies by user rating
        sorted_ratings = sorted(user.ratings.items(), key=lambda x: float(x[1]), reverse=True)
        
        # Get top 5 rated movies
        for movie_id, rating in sorted_ratings[:5]:
            movie = Movie.query.filter_by(tmdb_id=int(movie_id)).first()
            if movie:
                top_movies.append({
                    'id': movie.tmdb_id,
                    'title': movie.title,
                    'poster_path': movie.poster_path,
                    'user_rating': rating
                })
    
    # Calculate stats
    total_movies = len(user.watch_history)
    # Assuming average movie length of 120 minutes
    total_watch_time = user.total_watch_time or (total_movies * 120)
    
    # Count genres
    genre_counts = {}
    for movie in watched_movies:
        for genre_data in movie['genres']:
            # Handle genre being a dictionary with 'id' and 'name' keys
            if isinstance(genre_data, dict) and 'name' in genre_data:
                genre_name = genre_data['name']
                if genre_name in genre_counts:
                    genre_counts[genre_name] += 1
                else:
                    genre_counts[genre_name] = 1
            # Also handle the case where it might be just a string
            elif isinstance(genre_data, str):
                if genre_data in genre_counts:
                    genre_counts[genre_data] += 1
                else:
                    genre_counts[genre_data] = 1
    
    # Sort genres by count
    sorted_genres = sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)
    top_genres = [genre for genre, count in sorted_genres[:3]] if sorted_genres else []
    
    # Calculate average rating
    avg_rating = 0
    if user.ratings:
        ratings = list(user.ratings.values())
        avg_rating = sum(float(r) for r in ratings) / len(ratings)
    
    # Prepare data for charts
    genre_data = {
        'genre_labels': [genre for genre, _ in sorted_genres[:7]] if sorted_genres else [],
        'genre_counts': [count for _, count in sorted_genres[:7]] if sorted_genres else []
    }
    
    # Rating distribution
    rating_distribution = [0] * 10  # Initialize counts for ratings 1-10
    if user.ratings:
        for rating in user.ratings.values():
            rating_idx = min(int(float(rating)) - 1, 9)  # Ratings 1-10 map to indices 0-9
            rating_distribution[rating_idx] += 1
    
    # Watch history timeline (by month)
    # In a real app, this would use actual watch dates
    # For this demo, we'll create mock data based on number of movies
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    watch_counts = [0] * 12
    
    # Distribute watches across months (simplified demo)
    import random
    random.seed(user.id)  # Use user ID as seed for reproducibility
    for i in range(total_movies):
        month_idx = random.randint(0, 11)
        watch_counts[month_idx] += 1
    
    watch_history_data = {
        'months': months,
        'counts': watch_counts
    }
    
    # Calculate personalized insights
    # Determine movie personality type based on preferences and ratings
    personality_types = [
        "The Cinephile",
        "The Genre Enthusiast",
        "The Critical Viewer",
        "The Blockbuster Fan",
        "The Indie Explorer"
    ]
    
    # Select personality based on user ID for consistency
    personality_idx = user.id % len(personality_types)
    personality_type = personality_types[personality_idx]
    
    # Personalized descriptions
    personality_descriptions = {
        "The Cinephile": "You appreciate film as an art form and enjoy a diverse range of movies.",
        "The Genre Enthusiast": f"You have a strong preference for {top_genres[0] if top_genres else 'specific'} movies.",
        "The Critical Viewer": "You have high standards and prefer quality over quantity.",
        "The Blockbuster Fan": "You enjoy popular, action-packed entertainment and big-budget spectacles.",
        "The Indie Explorer": "You seek out unique, thought-provoking stories off the beaten path."
    }
    
    # Best movie day based on watch history
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    best_day_idx = (user.id + total_movies) % 7
    best_movie_day = days[best_day_idx]
    
    day_descriptions = {
        "Monday": "You start your week with movies, setting a positive tone for the days ahead.",
        "Tuesday": "Mid-week movies provide you with a perfect escape from daily routine.",
        "Wednesday": "Wednesday movie nights help you get through the week with entertainment.",
        "Thursday": "You enjoy pre-weekend movie sessions to unwind before Friday arrives.",
        "Friday": "Friday night movies mark the perfect start to your weekend relaxation.",
        "Saturday": "Weekend movie marathons are your preferred way to enjoy entertainment.",
        "Sunday": "Sunday films help you relax and prepare for the week ahead."
    }
    
    # Calculate recommendation accuracy (simplified for demo)
    # In a real app, this would compare predicted ratings vs. actual ratings
    recommendation_accuracy = random.randint(78, 94)
    
    # Combine all stats
    stats = {
        'total_movies': total_movies,
        'total_hours': total_watch_time // 60,
        'avg_rating': avg_rating,
        'top_genres': top_genres,
        'genre_counts': genre_data['genre_counts'],
        'genre_labels': genre_data['genre_labels'],
        'rating_distribution': rating_distribution,
        'rating_labels': [str(i) for i in range(1, 11)]
    }
    
    # Insights object
    insights = {
        'personality_type': personality_type,
        'personality_description': personality_descriptions[personality_type],
        'best_movie_day': best_movie_day,
        'day_description': day_descriptions[best_movie_day],
        'recommendation_accuracy': recommendation_accuracy
    }
    
    return render_template(
        'year_end_report.html',
        stats=stats,
        top_movies=top_movies,
        watch_history=watch_history_data,
        insights=insights
    )

# Special route for recommendations combining This or That results with mood quiz
@app.route('/recommendations')
def recommendations():
    user = get_user_session()
    
    # If user has completed both quizzes, we can make even better recommendations
    
    # Check for 5 unique This or That choices
    unique_this_or_that = set()
    if user.this_or_that_choices:
        unique_this_or_that = set(str(choice_id) for choice_id in user.this_or_that_choices)
    
    # Need both quiz results and at least 5 unique movie choices
    if user.quiz_results and len(unique_this_or_that) >= 5:
        # Get movies from database
        movies = Movie.query.all()
        
        if not movies:
            flash("Not enough movies available for recommendations.", "error")
            return redirect(url_for('index'))
        
        # Convert movies to pandas DataFrame
        movies_data = []
        for movie in movies:
            movie_dict = {
                'id': movie.tmdb_id,
                'title': movie.title,
                'genres': movie.genres,
                'vote_average': movie.vote_average
            }
            movies_data.append(movie_dict)
        
        movies_df = pd.DataFrame(movies_data)
        
        # Get mood-based recommendations
        mood_ids = mood_recommender.get_mood_based_recommendations(
            movies_df, 
            user.quiz_results,
            n=20
        )
        
        # Combine with content-based recommendations from This or That choices
        if movie_recommender.movies_df is None:
            initialize_recommender()
        
        # Initialize content_ids list for recommendations based on user choices
        content_ids = []
        
        # Ensure all 5 "This or That" selections are being used
        # Log for debugging
        logger.debug(f"Using {len(user.this_or_that_choices)} This or That choices for recommendations")
        
        # Loop through each movie the user chose in "This or That"
        for choice_id in user.this_or_that_choices:
            # Get recommendations for each chosen movie (more per movie for fewer total selections)
            similar_ids = movie_recommender.get_recommendations(choice_id, n=6)
            content_ids.extend(similar_ids)
            # Log the movie being used for recommendations
            logger.debug(f"Getting recommendations based on movie ID: {choice_id}")
        
        # Combine mood-based and content-based recommendations and deduplicate
        combined_ids = list(set(mood_ids + content_ids))
        
        # Get movie details
        recommended_movies = []
        for movie_id in combined_ids[:12]:  # Limit to 12 movies
            movie = Movie.query.filter_by(tmdb_id=movie_id).first()
            if movie:
                recommended_movies.append({
                    'id': movie.tmdb_id,
                    'title': movie.title,
                    'poster_path': movie.poster_path,
                    'vote_average': movie.vote_average,
                    'release_date': movie.release_date,
                    'genres': movie.genres
                })
        
        return render_template(
            'recommendations.html', 
            movies=recommended_movies, 
            title="Your Personalized Recommendations"
        )
    
    # If user has only completed one quiz or none, redirect to appropriate quiz
    elif not user.quiz_results:
        flash("Take our mood quiz to get personalized recommendations!", "info")
        return redirect(url_for('quiz'))
    elif len(unique_this_or_that) < 5:  # Check if user has made all 5 required selections
        flash("Complete all 5 selections in the 'This or That' quiz to refine your recommendations!", "info")
        return redirect(url_for('this_or_that'))
    
    # Fallback to recommend trending movies
    trending_data = tmdb_api.get_trending_movies()
    trending_movies = []
    
    if trending_data and 'results' in trending_data:
        trending_movies = trending_data['results'][:12]
    
    return render_template(
        'recommendations.html', 
        movies=trending_movies, 
        title="Trending Movies"
    )

# Initialize recommender with existing data
with app.app_context():
    initialize_recommender()
