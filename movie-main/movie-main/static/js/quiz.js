// Quiz functionality for Modex

document.addEventListener('DOMContentLoaded', function() {
    initializeQuiz();
});

function initializeQuiz() {
    const quizContainer = document.querySelector('.quiz-container');
    
    if (!quizContainer) return;
    
    // Quiz questions
    const questions = [
        {
            id: 'day',
            question: "How has your day been so far?",
            options: [
                { value: 'amazing', text: "😊 Amazing! Full of energy" },
                { value: 'calm', text: "😌 Calm and peaceful" },
                { value: 'down', text: "😞 A little down or stressed" },
                { value: 'overwhelming', text: "🤯 Overwhelming and chaotic" }
            ]
        },
        {
            id: 'color',
            question: "Which color best represents your mood right now?",
            options: [
                { value: 'yellow', text: "🌞 Yellow – Cheerful and lively" },
                { value: 'blue', text: "🔵 Blue – Calm and introspective" },
                { value: 'red', text: "🔴 Red – Intense or frustrated" },
                { value: 'black', text: "⚫ Black – Serious or low-energy" }
            ]
        },
        {
            id: 'movie',
            question: "If you were in a movie right now, what would it be like?",
            options: [
                { value: 'adventure', text: "🎬 A fun, lighthearted adventure" },
                { value: 'drama', text: "🎭 A deep, emotional drama" },
                { value: 'thriller', text: "🕵️ A suspenseful mystery or thriller" },
                { value: 'scifi', text: "👽 A mind-bending sci-fi story" }
            ]
        },
        {
            id: 'stress',
            question: "How do you usually handle stress?",
            options: [
                { value: 'talking', text: "💬 Talking to friends or family" },
                { value: 'active', text: "🏃 Doing something active" },
                { value: 'watching', text: "🎭 Watching movies or shows" },
                { value: 'thinking', text: "😶 Keeping to myself and thinking" }
            ]
        },
        {
            id: 'weather',
            question: "What type of weather fits your current mood?",
            options: [
                { value: 'sunny', text: "☀️ Sunny – Bright and positive" },
                { value: 'rainy', text: "🌧 Rainy – Thoughtful or nostalgic" },
                { value: 'stormy', text: "🌪 Stormy – Anxious or intense" },
                { value: 'cold', text: "❄️ Cold – Tired or disconnected" }
            ]
        }
    ];
    
    let currentQuestion = 0;
    const answers = {};
    
    // Create quiz
    renderQuestion();
    
    // Handle form submission
    const quizForm = document.getElementById('quiz-form');
    if (quizForm) {
        quizForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Check if an option is selected
            const selectedOption = document.querySelector('.quiz-option.selected');
            if (!selectedOption) {
                showNotification('Please select an option', 'warning');
                return;
            }
            
            // Save answer
            const questionId = questions[currentQuestion].id;
            answers[questionId] = selectedOption.dataset.value;
            
            // Move to next question or submit
            if (currentQuestion < questions.length - 1) {
                currentQuestion++;
                renderQuestion();
            } else {
                submitQuiz();
            }
        });
    }
    
    // Render current question
    function renderQuestion() {
        const questionCard = document.querySelector('.quiz-card');
        const question = questions[currentQuestion];
        
        // Update progress indicator
        const progressIndicator = document.querySelector('.quiz-progress');
        if (progressIndicator) {
            progressIndicator.textContent = `Question ${currentQuestion + 1} of ${questions.length}`;
        }
        
        // Update question text
        const questionElement = document.querySelector('.quiz-question');
        if (questionElement) {
            questionElement.textContent = question.question;
        }
        
        // Update options
        const optionsContainer = document.querySelector('.quiz-options');
        if (optionsContainer) {
            optionsContainer.innerHTML = '';
            
            question.options.forEach(option => {
                const optionElement = document.createElement('div');
                optionElement.className = 'quiz-option';
                optionElement.dataset.value = option.value;
                optionElement.textContent = option.text;
                
                // Add click handler
                optionElement.addEventListener('click', function() {
                    // Remove selected class from all options
                    document.querySelectorAll('.quiz-option').forEach(opt => {
                        opt.classList.remove('selected');
                    });
                    
                    // Add selected class to clicked option
                    this.classList.add('selected');
                });
                
                optionsContainer.appendChild(optionElement);
            });
        }
        
        // Update button text
        const submitButton = document.querySelector('#quiz-submit');
        if (submitButton) {
            submitButton.textContent = currentQuestion < questions.length - 1 ? 'Next Question' : 'Get Recommendations';
        }
        
        // Apply animation
        if (questionCard) {
            questionCard.classList.remove('fade-in');
            void questionCard.offsetWidth; // Trigger reflow
            questionCard.classList.add('fade-in');
        }
    }
    
    // Submit quiz answers
    function submitQuiz() {
        const loaderElement = document.createElement('div');
        loaderElement.className = 'loader';
        loaderElement.innerHTML = '<div class="loader-circle"></div>';
        
        // Replace quiz with loader
        quizContainer.innerHTML = '';
        quizContainer.appendChild(loaderElement);
        
        // Create form data
        const formData = new FormData();
        for (const [key, value] of Object.entries(answers)) {
            formData.append(key, value);
        }
        
        // Submit to backend
        fetch('/quiz/process', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (response.redirected) {
                window.location.href = response.url;
            } else {
                return response.text();
            }
        })
        .then(html => {
            if (html) {
                document.open();
                document.write(html);
                document.close();
            }
        })
        .catch(error => {
            console.error('Error submitting quiz:', error);
            quizContainer.innerHTML = `
                <div class="quiz-card">
                    <h2>Something went wrong</h2>
                    <p>We couldn't process your quiz results. Please try again.</p>
                    <button class="btn btn-primary" onclick="location.reload()">Retry</button>
                </div>
            `;
        });
    }
}

// Initialize quiz progress visualization
function initializeQuizProgress() {
    const progressBar = document.querySelector('.quiz-progress-bar');
    const totalQuestions = 5; // Total number of questions
    
    if (!progressBar) return;
    
    function updateProgress(currentQuestion) {
        const progressPercent = (currentQuestion / totalQuestions) * 100;
        progressBar.style.width = `${progressPercent}%`;
    }
    
    // Initial progress
    updateProgress(0);
    
    // Make function available globally
    window.updateQuizProgress = updateProgress;
}
