import os
import requests
import logging
from datetime import datetime
from app import app

logger = logging.getLogger(__name__)

class TMDBApi:
    """Class for interacting with The Movie Database (TMDB) API"""
    
    def __init__(self, api_key=None):
        """Initialize with API key"""
        self.api_key = api_key or app.config.get('TMDB_API_KEY')
        self.base_url = "https://api.themoviedb.org/3"
        
        if not self.api_key:
            logger.warning("TMDB API key not provided. API calls will fail.")
    
    def _make_request(self, endpoint, params=None):
        """Make a request to the TMDB API"""
        if not self.api_key:
            logger.error("TMDB API key not available")
            return None
            
        url = f"{self.base_url}/{endpoint}"
        
        params = params or {}
        params['api_key'] = self.api_key
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error making request to TMDB API: {str(e)}")
            return None
    
    def get_trending_movies(self, time_window="week", page=1):
        """Get trending movies for the day or week"""
        endpoint = f"trending/movie/{time_window}"
        return self._make_request(endpoint, params={'page': page})
    
    def get_movie_details(self, movie_id):
        """Get detailed information for a specific movie"""
        endpoint = f"movie/{movie_id}"
        params = {
            'append_to_response': 'credits,keywords,recommendations'
        }
        return self._make_request(endpoint, params=params)
    
    def search_movies(self, query, page=1):
        """Search for movies by title"""
        endpoint = "search/movie"
        params = {
            'query': query,
            'page': page,
            'include_adult': 'false'
        }
        return self._make_request(endpoint, params=params)
    
    def get_now_playing(self, page=1):
        """Get movies that are currently in theaters"""
        endpoint = "movie/now_playing"
        return self._make_request(endpoint, params={'page': page})
    
    def get_top_rated(self, page=1):
        """Get top rated movies"""
        endpoint = "movie/top_rated"
        return self._make_request(endpoint, params={'page': page})
    
    def get_movie_recommendations(self, movie_id, page=1):
        """Get movie recommendations based on a movie"""
        endpoint = f"movie/{movie_id}/recommendations"
        return self._make_request(endpoint, params={'page': page})
    
    def get_genre_list(self):
        """Get the list of official genres for movies"""
        endpoint = "genre/movie/list"
        return self._make_request(endpoint)
    
    def discover_movies(self, params=None):
        """Discover movies by different types of data"""
        endpoint = "discover/movie"
        return self._make_request(endpoint, params=params)
        
    def get_movies_released_before_six_months(self, page=1):
        """Get movies released at least 6 months ago"""
        from datetime import datetime, timedelta
        
        # Calculate date 6 months ago
        six_months_ago = datetime.now() - timedelta(days=180)
        release_date = six_months_ago.strftime("%Y-%m-%d")
        
        # Use discover endpoint to filter by release date
        params = {
            'sort_by': 'popularity.desc',
            'include_adult': 'false',
            'include_video': 'false',
            'page': page,
            'vote_count.gte': 100,  # Ensure some votes for quality
            'release_date.lte': release_date,  # Released before 6 months ago
            'with_original_language': 'en'  # English language movies for better recognition
        }
        
        return self.discover_movies(params)
    
    def format_movie_data(self, movie):
        """Format movie data for our database schema"""
        try:
            # Extract director(s) from credits if available
            directors = []
            if 'credits' in movie and 'crew' in movie['credits']:
                directors = [crew for crew in movie['credits']['crew'] if crew['job'] == 'Director']
            
            # Extract cast if available
            cast = []
            if 'credits' in movie and 'cast' in movie['credits']:
                cast = movie['credits']['cast'][:10]  # Get top 10 cast members
            
            # Extract keywords if available
            keywords = []
            if 'keywords' in movie and 'keywords' in movie['keywords']:
                keywords = movie['keywords']['keywords']
            
            # Format release date
            release_date = None
            if movie.get('release_date'):
                try:
                    release_date = datetime.strptime(movie['release_date'], '%Y-%m-%d').date()
                except ValueError:
                    pass
            
            # Create formatted movie data
            formatted_movie = {
                'tmdb_id': movie['id'],
                'title': movie['title'],
                'overview': movie.get('overview', ''),
                'release_date': release_date,
                'poster_path': movie.get('poster_path', ''),
                'backdrop_path': movie.get('backdrop_path', ''),
                'genres': movie.get('genres', []),
                'vote_average': movie.get('vote_average', 0),
                'vote_count': movie.get('vote_count', 0),
                'keywords': keywords,
                'cast': cast,
                'directors': directors,
                'last_updated': datetime.utcnow()
            }
            
            return formatted_movie
        except Exception as e:
            logger.error(f"Error formatting movie data: {str(e)}")
            return None
