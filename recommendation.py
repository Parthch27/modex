import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import logging

logger = logging.getLogger(__name__)

class MovieRecommender:
    def __init__(self):
        self.movies_df = None
        self.tfidf_matrix = None
        self.cosine_sim = None
        self.indices = None

    def fit(self, movies_data):
        """
        Process movie data and create similarity matrix
        
        Args:
            movies_data: List of movie dictionaries with fields: id, title, overview, genres, keywords, cast, directors
        """
        try:
            # Convert to DataFrame for easier manipulation
            self.movies_df = pd.DataFrame(movies_data)
            
            # Create an ID to index mapping
            self.indices = pd.Series(self.movies_df.index, index=self.movies_df['id']).drop_duplicates()
            
            # Create content string for each movie combining relevant features
            self.movies_df['content'] = self.movies_df.apply(self._create_content_string, axis=1)
            
            # Create TF-IDF matrix
            tfidf = TfidfVectorizer(stop_words='english', max_features=5000)
            self.tfidf_matrix = tfidf.fit_transform(self.movies_df['content'])
            
            # Compute cosine similarity
            self.cosine_sim = cosine_similarity(self.tfidf_matrix, self.tfidf_matrix)
            
            logger.debug(f"Recommendation system fitted with {len(movies_data)} movies")
            return True
        except Exception as e:
            logger.error(f"Error fitting recommendation system: {str(e)}")
            return False

    def _create_content_string(self, row):
        """Create a string combining all relevant movie features for content-based filtering"""
        content = []
        
        # Add title (with higher weight by repeating)
        if not pd.isna(row['title']):
            content.append(row['title'] + " " + row['title'] + " " + row['title'])
        
        # Add overview
        if not pd.isna(row['overview']):
            content.append(row['overview'])
        
        # Add genres
        if isinstance(row.get('genres'), list):
            content.append(' '.join([g.get('name', '') for g in row['genres']]))
        
        # Add keywords
        if isinstance(row.get('keywords'), list):
            content.append(' '.join([k.get('name', '') for k in row['keywords']]))
        
        # Add cast (top 5)
        if isinstance(row.get('cast'), list):
            cast = row['cast'][:5] if len(row['cast']) > 5 else row['cast']
            content.append(' '.join([c.get('name', '') for c in cast]))
        
        # Add directors
        if isinstance(row.get('directors'), list):
            content.append(' '.join([d.get('name', '') for d in row['directors']]))
        
        return ' '.join(content).lower()

    def get_recommendations(self, movie_id, n=10):
        """
        Get movie recommendations based on similarity to a given movie
        
        Args:
            movie_id: ID of the movie to get recommendations for
            n: Number of recommendations to return
            
        Returns:
            List of recommended movie IDs
        """
        try:
            # Check if the model is trained
            if self.cosine_sim is None:
                logger.error("Recommendation system not fitted")
                return []
            
            # Get the index of the movie
            if movie_id not in self.indices:
                logger.error(f"Movie ID {movie_id} not found in indices")
                return []
                
            idx = self.indices[movie_id]
            
            # Get similarity scores for all movies with this one
            sim_scores = list(enumerate(self.cosine_sim[idx]))
            
            # Sort movies by similarity
            sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
            
            # Get top N most similar movies (excluding the movie itself)
            sim_scores = sim_scores[1:n+1]
            
            # Get movie indices
            movie_indices = [i[0] for i in sim_scores]
            
            # Return movie IDs
            recommended_ids = self.movies_df.iloc[movie_indices]['id'].tolist()
            
            return recommended_ids
        except Exception as e:
            logger.error(f"Error getting recommendations: {str(e)}")
            return []
    
    def get_personalized_recommendations(self, watch_history, ratings=None, n=10):
        """
        Get personalized recommendations based on watch history and ratings
        
        Args:
            watch_history: List of movie IDs the user has watched
            ratings: Dictionary of {movie_id: rating} if available
            n: Number of recommendations to return
            
        Returns:
            List of recommended movie IDs
        """
        try:
            if not watch_history or self.cosine_sim is None:
                return []
            
            # Filter for movies in our dataset
            valid_history = [m for m in watch_history if m in self.indices]
            
            if not valid_history:
                return []
            
            # Calculate average similarity to each movie in the catalog
            sim_scores = np.zeros(len(self.movies_df))
            
            for movie_id in valid_history:
                idx = self.indices[movie_id]
                # If ratings are provided, weight by rating
                weight = 1.0
                if ratings and str(movie_id) in ratings:
                    weight = float(ratings[str(movie_id)]) / 5.0  # Normalize to 0-2 range
                
                sim_scores += self.cosine_sim[idx] * weight
            
            # Average the scores
            sim_scores = sim_scores / len(valid_history)
            
            # Create list of (index, score) tuples
            sim_scores = list(enumerate(sim_scores))
            
            # Sort by similarity
            sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
            
            # Filter out already watched movies
            sim_scores = [s for s in sim_scores if self.movies_df.iloc[s[0]]['id'] not in watch_history]
            
            # Get top N
            sim_scores = sim_scores[:n]
            
            # Get movie indices
            movie_indices = [i[0] for i in sim_scores]
            
            # Return movie IDs
            recommended_ids = self.movies_df.iloc[movie_indices]['id'].tolist()
            
            return recommended_ids
        except Exception as e:
            logger.error(f"Error getting personalized recommendations: {str(e)}")
            return []
    
    def predict_rating(self, user_watch_history, movie_id):
        """
        Predict how much a user might like a movie based on their watch history
        
        Args:
            user_watch_history: List of movie IDs the user has watched
            movie_id: ID of the movie to predict rating for
            
        Returns:
            Predicted rating (1-10)
        """
        try:
            if not user_watch_history or movie_id not in self.indices:
                return 5.0  # Default neutral rating
            
            # Get valid watched movies
            valid_history = [m for m in user_watch_history if m in self.indices]
            
            if not valid_history:
                return 5.0
            
            # Get target movie index
            target_idx = self.indices[movie_id]
            
            # Calculate average similarity to watched movies
            avg_sim = 0.0
            for watched_id in valid_history:
                watched_idx = self.indices[watched_id]
                avg_sim += self.cosine_sim[watched_idx][target_idx]
            
            avg_sim = avg_sim / len(valid_history)
            
            # Convert similarity (0-1) to rating (1-10)
            # Using a formula that gives 5 for neutral similarity (0.5)
            predicted_rating = avg_sim * 6 + 4
            
            # Ensure rating is within 1-10 range
            predicted_rating = max(1.0, min(10.0, predicted_rating))
            
            return round(predicted_rating, 1)
        except Exception as e:
            logger.error(f"Error predicting rating: {str(e)}")
            return 5.0

class MoodBasedRecommender:
    """Recommends movies based on mood quiz results"""
    
    def __init__(self):
        # Define mood categories and their corresponding genre weights
        self.mood_mappings = {
            "happy": {
                "Comedy": 1.5, 
                "Animation": 1.3, 
                "Family": 1.2, 
                "Adventure": 1.1,
                "Romance": 1.0
            },
            "sad": {
                "Drama": 1.5, 
                "Romance": 1.3, 
                "Music": 1.2, 
                "Animation": 1.0
            },
            "excited": {
                "Action": 1.5, 
                "Adventure": 1.4, 
                "Science Fiction": 1.3, 
                "Fantasy": 1.2, 
                "Thriller": 1.1
            },
            "relaxed": {
                "Documentary": 1.5, 
                "Animation": 1.3, 
                "Comedy": 1.1, 
                "Family": 1.0
            },
            "tense": {
                "Thriller": 1.5, 
                "Mystery": 1.4, 
                "Science Fiction": 1.3, 
                "Crime": 1.2, 
                "Horror": 1.1
            },
            "thoughtful": {
                "Drama": 1.5,
                "Mystery": 1.3,
                "Documentary": 1.2,
                "History": 1.1,
                "Science Fiction": 1.0
            },
            "adventurous": {
                "Adventure": 1.5,
                "Action": 1.4,
                "Fantasy": 1.3,
                "Science Fiction": 1.2,
                "Western": 1.0
            }
        }
        
        # Define quiz question weights for each mood
        self.question_weights = {
            "day": {
                "amazing": {"happy": 1.5, "excited": 1.0, "adventurous": 0.8, "sad": -1.0, "thoughtful": -0.3},
                "calm": {"relaxed": 1.5, "thoughtful": 0.7, "happy": 0.3, "tense": -0.8, "excited": -0.5},
                "down": {"sad": 1.5, "thoughtful": 0.8, "relaxed": 0.3, "happy": -1.0, "excited": -0.8},
                "overwhelming": {"tense": 1.5, "excited": 0.5, "thoughtful": 0.3, "relaxed": -1.0, "sad": 0.2}
            },
            "color": {
                "yellow": {"happy": 1.5, "excited": 0.8, "adventurous": 0.7, "sad": -1.0, "tense": -0.5},
                "blue": {"relaxed": 1.3, "thoughtful": 1.0, "sad": 0.6, "excited": -0.5, "tense": -0.8},
                "red": {"tense": 1.3, "excited": 1.0, "adventurous": 0.7, "relaxed": -1.0, "thoughtful": -0.5},
                "black": {"sad": 1.0, "thoughtful": 0.8, "tense": 0.7, "happy": -1.0, "excited": -0.7}
            },
            "movie": {
                "adventure": {"adventurous": 1.5, "happy": 1.0, "excited": 0.8, "sad": -1.0, "thoughtful": -0.5},
                "drama": {"sad": 1.3, "thoughtful": 1.1, "relaxed": 0.5, "excited": -0.8, "adventurous": -0.5},
                "thriller": {"tense": 1.5, "excited": 0.7, "adventurous": 0.5, "relaxed": -1.0, "happy": -0.8},
                "scifi": {"thoughtful": 1.2, "excited": 1.0, "adventurous": 0.8, "sad": -0.5, "relaxed": -0.3}
            },
            "stress": {
                "talking": {"happy": 1.0, "relaxed": 0.8, "thoughtful": 0.7, "tense": -0.8, "sad": -0.3},
                "active": {"excited": 1.2, "adventurous": 1.0, "happy": 0.7, "sad": -1.0, "thoughtful": -0.5},
                "watching": {"relaxed": 1.3, "happy": 0.7, "thoughtful": 0.5, "tense": -0.5, "adventurous": 0.3},
                "thinking": {"thoughtful": 1.5, "sad": 0.7, "relaxed": 0.5, "excited": -0.8, "adventurous": -0.3}
            },
            "weather": {
                "sunny": {"happy": 1.5, "excited": 1.0, "adventurous": 0.8, "sad": -1.0, "tense": -0.7},
                "rainy": {"thoughtful": 1.3, "relaxed": 1.0, "sad": 0.7, "excited": -0.8, "adventurous": -0.5},
                "stormy": {"tense": 1.5, "excited": 0.8, "sad": 0.6, "relaxed": -1.0, "happy": -0.8},
                "cold": {"sad": 1.2, "thoughtful": 0.9, "relaxed": 0.6, "happy": -0.7, "adventurous": -0.5}
            }
        }
    
    def analyze_quiz_results(self, quiz_results):
        """
        Analyze quiz results to determine user's mood
        
        Args:
            quiz_results: Dictionary of quiz answers {question: answer}
            
        Returns:
            Dictionary of mood scores
        """
        # Initialize mood scores
        moods = {
            "happy": 0,
            "sad": 0,
            "excited": 0,
            "relaxed": 0,
            "tense": 0,
            "thoughtful": 0,
            "adventurous": 0
        }
        
        # Process each question's contribution to moods
        for question, answer in quiz_results.items():
            if question in self.question_weights and answer in self.question_weights[question]:
                weight_map = self.question_weights[question][answer]
                for mood, weight in weight_map.items():
                    moods[mood] += weight
        
        return moods
    
    def get_mood_based_recommendations(self, movies_df, quiz_results, n=10):
        """
        Get movie recommendations based on mood analysis
        
        Args:
            movies_df: DataFrame of available movies
            quiz_results: Dictionary of quiz answers
            n: Number of recommendations to return
            
        Returns:
            List of recommended movie IDs
        """
        try:
            # Analyze quiz results
            mood_scores = self.analyze_quiz_results(quiz_results)
            
            # Find dominant mood (highest score)
            dominant_mood = max(mood_scores.items(), key=lambda x: x[1])[0]
            
            # Get genre weights for dominant mood
            genre_weights = self.mood_mappings.get(dominant_mood, {})
            
            # Initialize movie scores
            movie_scores = []
            
            # Score each movie based on genre match with mood
            for _, movie in movies_df.iterrows():
                score = 0
                
                # Extract genres
                if isinstance(movie.get('genres'), list):
                    for genre_obj in movie['genres']:
                        genre_name = genre_obj.get('name', '')
                        # Add genre weight if this genre is relevant to the mood
                        if genre_name in genre_weights:
                            score += genre_weights[genre_name]
                
                # Add base score for popular and well-rated movies
                if 'vote_average' in movie and not pd.isna(movie['vote_average']):
                    score += (movie['vote_average'] / 20)  # Small boost for rating
                
                # Only include movies with some genre match
                if score > 0:
                    movie_scores.append((movie['id'], score))
            
            # Sort by score
            movie_scores.sort(key=lambda x: x[1], reverse=True)
            
            # Get top N movie IDs
            recommended_ids = [movie_id for movie_id, _ in movie_scores[:n]]
            
            return recommended_ids
        except Exception as e:
            logger.error(f"Error getting mood-based recommendations: {str(e)}")
            return []
