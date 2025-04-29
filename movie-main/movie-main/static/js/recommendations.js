// Recommendations functionality for Modex

document.addEventListener('DOMContentLoaded', function() {
    initializeRecommendationSystem();
});

function initializeRecommendationSystem() {
    // Handle "Mark as Watched" buttons
    const watchButtons = document.querySelectorAll('[data-watch-id]');
    
    watchButtons.forEach(button => {
        button.addEventListener('click', function() {
            const movieId = this.dataset.watchId;
            markAsWatched(movieId);
        });
    });
    
    // Initialize movie filters if present
    initializeMovieFilters();
    
    // Initialize rating explanation popups
    initializeRatingExplanations();
}

// Initialize movie filters for recommendation page
function initializeMovieFilters() {
    const filterContainer = document.querySelector('.movie-filters');
    
    if (!filterContainer) return;
    
    const genreFilters = filterContainer.querySelectorAll('.filter-genre');
    const yearFilter = filterContainer.querySelector('.filter-year');
    const ratingFilter = filterContainer.querySelector('.filter-rating');
    const movieCards = document.querySelectorAll('.movie-item');
    
    // Handle genre filter clicks
    genreFilters.forEach(filter => {
        filter.addEventListener('click', function() {
            // Toggle active class
            this.classList.toggle('active');
            
            // Apply filters
            applyFilters();
        });
    });
    
    // Handle rating filter changes
    if (ratingFilter) {
        ratingFilter.addEventListener('input', applyFilters);
    }
    
    // Handle year filter changes
    if (yearFilter) {
        yearFilter.addEventListener('input', applyFilters);
    }
    
    // Apply all active filters
    function applyFilters() {
        // Get active genre filters
        const activeGenres = [];
        genreFilters.forEach(filter => {
            if (filter.classList.contains('active')) {
                activeGenres.push(filter.dataset.genre.toLowerCase());
            }
        });
        
        // Get min rating
        const minRating = ratingFilter ? parseFloat(ratingFilter.value) : 0;
        
        // Get min year
        const minYear = yearFilter ? parseInt(yearFilter.value) : 0;
        
        // Apply filters to each movie card
        movieCards.forEach(card => {
            let showCard = true;
            
            // Check genres if we have active genre filters
            if (activeGenres.length > 0) {
                const movieGenres = card.dataset.genres.toLowerCase().split(',');
                // Card needs to have at least one of the active genres
                const hasActiveGenre = activeGenres.some(genre => 
                    movieGenres.includes(genre)
                );
                
                if (!hasActiveGenre) {
                    showCard = false;
                }
            }
            
            // Check rating
            if (showCard && minRating > 0) {
                const movieRating = parseFloat(card.dataset.rating || 0);
                if (movieRating < minRating) {
                    showCard = false;
                }
            }
            
            // Check year
            if (showCard && minYear > 0) {
                const movieYear = parseInt(card.dataset.year || 0);
                if (movieYear < minYear) {
                    showCard = false;
                }
            }
            
            // Show or hide card
            if (showCard) {
                card.style.display = '';
            } else {
                card.style.display = 'none';
            }
        });
        
        // Update filter indicators
        updateFilterIndicators(minRating, minYear);
    }
    
    // Update filter indicators
    function updateFilterIndicators(rating, year) {
        const ratingIndicator = document.querySelector('.rating-value');
        const yearIndicator = document.querySelector('.year-value');
        
        if (ratingIndicator) {
            ratingIndicator.textContent = rating;
        }
        
        if (yearIndicator) {
            yearIndicator.textContent = year;
        }
    }
}

// Initialize rating explanation popups
function initializeRatingExplanations() {
    const predictedRatings = document.querySelectorAll('.predicted-rating');
    
    predictedRatings.forEach(rating => {
        rating.addEventListener('mouseenter', function() {
            const explanation = this.querySelector('.rating-explanation');
            if (explanation) {
                explanation.style.display = 'block';
                
                // Position the explanation
                const rect = this.getBoundingClientRect();
                explanation.style.bottom = `${rect.height + 10}px`;
                explanation.style.left = '50%';
                explanation.style.transform = 'translateX(-50%)';
            }
        });
        
        rating.addEventListener('mouseleave', function() {
            const explanation = this.querySelector('.rating-explanation');
            if (explanation) {
                explanation.style.display = 'none';
            }
        });
    });
}

// Function to fetch similar movies for a specific movie
function fetchSimilarMovies(movieId, containerId) {
    fetch(`/api/movies/${movieId}/similar`)
        .then(response => response.json())
        .then(data => {
            if (data.movies && data.movies.length > 0) {
                const container = document.getElementById(containerId);
                if (container) {
                    // Create movie carousel
                    const carouselElement = createMovieCarousel('Similar Movies', data.movies, containerId);
                    
                    if (carouselElement) {
                        container.parentNode.replaceChild(carouselElement, container);
                        initializeMovieCarousels();
                    }
                }
            }
        })
        .catch(error => console.error('Error fetching similar movies:', error));
}

// Function to load personalized recommendations
function loadPersonalizedRecommendations(containerId) {
    fetch('/api/recommendations/personalized')
        .then(response => response.json())
        .then(data => {
            if (data.movies && data.movies.length > 0) {
                const container = document.getElementById(containerId);
                if (container) {
                    // Create movie carousel
                    const carouselElement = createMovieCarousel('Recommended For You', data.movies, containerId);
                    
                    if (carouselElement) {
                        container.parentNode.replaceChild(carouselElement, container);
                        initializeMovieCarousels();
                    }
                }
            }
        })
        .catch(error => console.error('Error loading personalized recommendations:', error));
}
