// Main JavaScript file for Modex

document.addEventListener('DOMContentLoaded', function() {
    // Initialize components
    initializeNavbar();
    initializeCarousels();
    initializeAnimations();
    initializeRatings();
    initializeSearchBar();
});

// Navbar functionality
function initializeNavbar() {
    // Make navbar transparent at top and solid when scrolled
    const navbar = document.querySelector('.navbar');
    
    if (navbar) {
        window.addEventListener('scroll', function() {
            if (window.scrollY > 50) {
                navbar.classList.add('navbar-scrolled');
                navbar.style.background = 'rgba(18, 18, 18, 0.95)';
                navbar.style.boxShadow = '0 2px 10px rgba(0, 0, 0, 0.2)';
            } else {
                navbar.classList.remove('navbar-scrolled');
                navbar.style.background = 'var(--glass-bg)';
                navbar.style.boxShadow = 'none';
            }
        });
    }
}

// Movie carousels
function initializeCarousels() {
    const carousels = document.querySelectorAll('.movie-carousel');
    
    carousels.forEach(carousel => {
        // Get the associated controls
        const container = carousel.closest('.carousel-section');
        const prevBtn = container.querySelector('.carousel-prev');
        const nextBtn = container.querySelector('.carousel-next');
        
        if (prevBtn && nextBtn) {
            // Add click event listeners for controls
            prevBtn.addEventListener('click', () => {
                carousel.scrollBy({ left: -500, behavior: 'smooth' });
            });
            
            nextBtn.addEventListener('click', () => {
                carousel.scrollBy({ left: 500, behavior: 'smooth' });
            });
        }
        
        // Add hover effect to pause auto-scrolling
        let autoScrollInterval;
        
        // Start auto-scroll
        startAutoScroll();
        
        // Pause auto-scroll on hover
        carousel.addEventListener('mouseenter', () => {
            clearInterval(autoScrollInterval);
        });
        
        // Resume auto-scroll when mouse leaves
        carousel.addEventListener('mouseleave', () => {
            startAutoScroll();
        });
        
        function startAutoScroll() {
            autoScrollInterval = setInterval(() => {
                carousel.scrollBy({ left: 1, behavior: 'auto' });
            }, 30);
        }
    });
}

// Animation effects
function initializeAnimations() {
    // Apply fade-in effect to elements as they enter the viewport
    const fadeElements = document.querySelectorAll('.fade-in');
    const scaleElements = document.querySelectorAll('.scale-in');
    
    // Create an Intersection Observer
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
                observer.unobserve(entry.target);
            }
        });
    }, {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    });
    
    // Observe fade elements
    fadeElements.forEach(element => {
        element.style.opacity = '0';
        element.style.transform = 'translateY(20px)';
        element.style.transition = 'opacity 0.8s ease, transform 0.8s ease';
        observer.observe(element);
    });
    
    // Observe scale elements
    scaleElements.forEach(element => {
        element.style.opacity = '0';
        element.style.transform = 'scale(0.95)';
        element.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
        observer.observe(element);
    });
    
    // Apply parallax effect to hero section
    const hero = document.querySelector('.hero');
    if (hero) {
        window.addEventListener('scroll', () => {
            const scrollPosition = window.scrollY;
            hero.style.backgroundPosition = `center ${scrollPosition * 0.5}px`;
        });
    }
}

// Rating system
function initializeRatings() {
    const ratingContainers = document.querySelectorAll('.rating-stars');
    
    ratingContainers.forEach(container => {
        const stars = container.querySelectorAll('.star');
        const movieId = container.dataset.movieId;
        const ratingInput = container.querySelector('input[name="rating"]');
        
        stars.forEach((star, index) => {
            // Set initial active state based on value
            if (ratingInput && parseInt(ratingInput.value) >= index + 1) {
                star.classList.add('active');
            }
            
            // Handle click events
            star.addEventListener('click', () => {
                // Update visual state
                stars.forEach((s, i) => {
                    if (i <= index) {
                        s.classList.add('active');
                    } else {
                        s.classList.remove('active');
                    }
                });
                
                // Update input value
                if (ratingInput) {
                    ratingInput.value = index + 1;
                }
                
                // Submit rating if an AJAX form is present
                if (movieId) {
                    submitRating(movieId, index + 1);
                }
            });
            
            // Handle hover events
            star.addEventListener('mouseenter', () => {
                stars.forEach((s, i) => {
                    if (i <= index) {
                        s.style.color = '#ffc107';
                    } else {
                        s.style.color = '#aaa';
                    }
                });
            });
            
            star.addEventListener('mouseleave', () => {
                stars.forEach((s, i) => {
                    if (s.classList.contains('active')) {
                        s.style.color = '#ffc107';
                    } else {
                        s.style.color = '#aaa';
                    }
                });
            });
        });
    });
}

// Submit rating via AJAX
function submitRating(movieId, rating) {
    const formData = new FormData();
    formData.append('rating', rating);
    
    fetch(`/movie/${movieId}/rate`, {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Rating submitted successfully!', 'success');
        } else {
            showNotification('Error submitting rating', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('Error submitting rating', 'error');
    });
}

// Mark movie as watched
function markAsWatched(movieId) {
    fetch(`/movie/${movieId}/watched`, {
        method: 'POST',
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const watchButton = document.querySelector(`[data-watch-id="${movieId}"]`);
            if (watchButton) {
                watchButton.innerHTML = '<i class="fas fa-check"></i> Watched';
                watchButton.classList.remove('btn-outline-primary');
                watchButton.classList.add('btn-success');
                watchButton.disabled = true;
            }
            showNotification('Movie marked as watched!', 'success');
        } else {
            showNotification('Error updating watch status', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('Error updating watch status', 'error');
    });
}

// Search functionality
function initializeSearchBar() {
    const searchForm = document.querySelector('.search-form');
    const searchInput = document.querySelector('.navbar-search');
    
    if (searchForm && searchInput) {
        searchInput.addEventListener('focus', () => {
            searchInput.style.width = '250px';
        });
        
        searchInput.addEventListener('blur', () => {
            if (!searchInput.value) {
                searchInput.style.width = '180px';
            }
        });
    }
}

// Notification system
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <div class="notification-content">
            <p>${message}</p>
        </div>
    `;
    
    // Add to document
    document.body.appendChild(notification);
    
    // Trigger animation
    setTimeout(() => {
        notification.classList.add('show');
    }, 10);
    
    // Remove after a delay
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => {
            notification.remove();
        }, 300);
    }, 3000);
    
    // Style the notification with CSS
    const style = document.createElement('style');
    style.textContent = `
        .notification {
            position: fixed;
            bottom: -100px;
            right: 20px;
            background: var(--glass-bg);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border-radius: 10px;
            padding: 15px 20px;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
            z-index: 1000;
            transition: transform 0.3s ease;
            border-left: 3px solid var(--primary-color);
        }
        
        .notification.show {
            transform: translateY(-120px);
        }
        
        .notification-success {
            border-left-color: #28a745;
        }
        
        .notification-error {
            border-left-color: #dc3545;
        }
        
        .notification-warning {
            border-left-color: #ffc107;
        }
    `;
    document.head.appendChild(style);
}
