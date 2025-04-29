// Carousel functionality for Modex

document.addEventListener('DOMContentLoaded', function() {
    initializeHeroCarousel();
    initializeMovieCarousels();
});

function initializeHeroCarousel() {
    const heroCarousel = document.querySelector('.hero-carousel');
    
    if (!heroCarousel) return;
    
    // Get hero slides
    const slides = heroCarousel.querySelectorAll('.hero-slide');
    
    if (slides.length <= 1) return;
    
    let currentSlide = 0;
    
    // Create indicators
    const indicators = document.createElement('div');
    indicators.className = 'hero-indicators';
    
    for (let i = 0; i < slides.length; i++) {
        const indicator = document.createElement('div');
        indicator.className = 'hero-indicator';
        if (i === 0) indicator.classList.add('active');
        
        // Add click event to indicator
        indicator.addEventListener('click', () => {
            goToSlide(i);
        });
        
        indicators.appendChild(indicator);
    }
    
    heroCarousel.appendChild(indicators);
    
    // Create navigation arrows
    const prevArrow = document.createElement('div');
    prevArrow.className = 'hero-nav hero-prev';
    prevArrow.innerHTML = '<i class="fas fa-chevron-left"></i>';
    prevArrow.addEventListener('click', () => {
        goToSlide(currentSlide - 1);
    });
    
    const nextArrow = document.createElement('div');
    nextArrow.className = 'hero-nav hero-next';
    nextArrow.innerHTML = '<i class="fas fa-chevron-right"></i>';
    nextArrow.addEventListener('click', () => {
        goToSlide(currentSlide + 1);
    });
    
    heroCarousel.appendChild(prevArrow);
    heroCarousel.appendChild(nextArrow);
    
    // Set initial state
    slides.forEach((slide, index) => {
        if (index !== 0) {
            slide.style.opacity = '0';
            slide.style.zIndex = '0';
        } else {
            slide.style.opacity = '1';
            slide.style.zIndex = '1';
        }
    });
    
    // Auto-transition
    let interval = setInterval(() => {
        goToSlide(currentSlide + 1);
    }, 5000);
    
    // Pause on hover
    heroCarousel.addEventListener('mouseenter', () => {
        clearInterval(interval);
    });
    
    heroCarousel.addEventListener('mouseleave', () => {
        interval = setInterval(() => {
            goToSlide(currentSlide + 1);
        }, 5000);
    });
    
    // Function to go to a specific slide
    function goToSlide(index) {
        // Handle wrapping
        if (index < 0) index = slides.length - 1;
        if (index >= slides.length) index = 0;
        
        // If same slide, do nothing
        if (index === currentSlide) return;
        
        // Get elements
        const currentElement = slides[currentSlide];
        const nextElement = slides[index];
        
        // Update indicators
        const allIndicators = indicators.querySelectorAll('.hero-indicator');
        allIndicators[currentSlide].classList.remove('active');
        allIndicators[index].classList.add('active');
        
        // Animate transition
        currentElement.style.opacity = '0';
        currentElement.style.zIndex = '0';
        
        nextElement.style.opacity = '1';
        nextElement.style.zIndex = '1';
        
        // Update current slide
        currentSlide = index;
    }
    
    // Add CSS for hero carousel
    const style = document.createElement('style');
    style.textContent = `
        .hero-carousel {
            position: relative;
            width: 100%;
            height: 70vh;
            overflow: hidden;
        }
        
        .hero-slide {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            transition: opacity 0.8s ease;
            background-size: cover;
            background-position: center;
        }
        
        .hero-indicators {
            position: absolute;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            display: flex;
            z-index: 10;
        }
        
        .hero-indicator {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.5);
            margin: 0 5px;
            cursor: pointer;
            transition: background 0.3s ease;
        }
        
        .hero-indicator.active {
            background: var(--primary-color);
        }
        
        .hero-nav {
            position: absolute;
            top: 50%;
            transform: translateY(-50%);
            width: 50px;
            height: 50px;
            background: rgba(0, 0, 0, 0.5);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            cursor: pointer;
            z-index: 10;
            opacity: 0.7;
            transition: opacity 0.3s ease, background 0.3s ease;
        }
        
        .hero-nav:hover {
            opacity: 1;
            background: var(--primary-color);
        }
        
        .hero-prev {
            left: 20px;
        }
        
        .hero-next {
            right: 20px;
        }
        
        @media (max-width: 768px) {
            .hero-carousel {
                height: 50vh;
            }
            
            .hero-nav {
                width: 40px;
                height: 40px;
            }
        }
    `;
    
    document.head.appendChild(style);
}

function initializeMovieCarousels() {
    const carousels = document.querySelectorAll('.movie-carousel');
    
    carousels.forEach(carousel => {
        // Create a touch/mouse drag scroll functionality
        let isDown = false;
        let startX;
        let scrollLeft;
        
        carousel.addEventListener('mousedown', (e) => {
            isDown = true;
            carousel.style.cursor = 'grabbing';
            startX = e.pageX - carousel.offsetLeft;
            scrollLeft = carousel.scrollLeft;
            e.preventDefault();
        });
        
        carousel.addEventListener('mouseleave', () => {
            isDown = false;
            carousel.style.cursor = 'grab';
        });
        
        carousel.addEventListener('mouseup', () => {
            isDown = false;
            carousel.style.cursor = 'grab';
        });
        
        carousel.addEventListener('mousemove', (e) => {
            if (!isDown) return;
            e.preventDefault();
            const x = e.pageX - carousel.offsetLeft;
            const walk = (x - startX) * 2; // Scroll speed multiplier
            carousel.scrollLeft = scrollLeft - walk;
        });
        
        // Touch events for mobile
        carousel.addEventListener('touchstart', (e) => {
            isDown = true;
            startX = e.touches[0].pageX - carousel.offsetLeft;
            scrollLeft = carousel.scrollLeft;
        });
        
        carousel.addEventListener('touchend', () => {
            isDown = false;
        });
        
        carousel.addEventListener('touchmove', (e) => {
            if (!isDown) return;
            const x = e.touches[0].pageX - carousel.offsetLeft;
            const walk = (x - startX) * 2;
            carousel.scrollLeft = scrollLeft - walk;
        });
    });
}

// Function to create movie carousel element
function createMovieCarousel(title, movies, containerId) {
    if (!movies || movies.length === 0) return null;
    
    // Create container if it doesn't exist
    let container = document.getElementById(containerId);
    if (!container) {
        container = document.createElement('div');
        container.id = containerId;
        container.className = 'carousel-section';
    }
    
    // Create carousel HTML
    container.innerHTML = `
        <div class="carousel-title">
            <h2>${title}</h2>
            <div class="carousel-controls">
                <div class="carousel-control carousel-prev">
                    <i class="fas fa-chevron-left"></i>
                </div>
                <div class="carousel-control carousel-next">
                    <i class="fas fa-chevron-right"></i>
                </div>
            </div>
        </div>
        <div class="movie-carousel">
            ${movies.map(movie => `
                <div class="movie-carousel-item">
                    <div class="movie-card">
                        <a href="/movie/${movie.id}">
                            <img src="${movie.poster_path ? 'https://image.tmdb.org/t/p/w500' + movie.poster_path : '/static/img/no-poster.svg'}" alt="${movie.title}" class="movie-poster">
                            <div class="movie-info">
                                <h3 class="movie-title">${movie.title}</h3>
                                <div class="movie-rating">
                                    <i class="fas fa-star"></i> ${movie.vote_average ? movie.vote_average.toFixed(1) : 'N/A'}
                                </div>
                            </div>
                        </a>
                    </div>
                </div>
            `).join('')}
        </div>
    `;
    
    return container;
}

// Function to load a movie carousel via AJAX
function loadMovieCarousel(url, title, containerId) {
    fetch(url)
        .then(response => response.json())
        .then(data => {
            if (data.results && data.results.length > 0) {
                const container = document.getElementById(containerId);
                const carouselElement = createMovieCarousel(title, data.results, containerId);
                
                if (container && carouselElement) {
                    container.parentNode.replaceChild(carouselElement, container);
                    initializeMovieCarousels();
                }
            }
        })
        .catch(error => console.error('Error loading carousel:', error));
}
