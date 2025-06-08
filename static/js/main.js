// AI Exchange - Main JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Generate consistent avatar colors based on username
    function generateAvatarColor(username) {
        let hash = 0;
        for (let i = 0; i < username.length; i++) {
            hash = ((hash << 5) - hash + username.charCodeAt(i)) & 0xffffffff;
        }
        // Use absolute value and modulo to get a number between 1-18
        return Math.abs(hash) % 18 + 1;
    }    // Apply avatar colors to all avatars
    function initializeAvatars() {
        const avatars = document.querySelectorAll('.user-avatar, .user-avatar-large, .user-avatar-enhanced, .avatar-circle');
        avatars.forEach(avatar => {
            // First try data-username attribute
            let username = avatar.getAttribute('data-username');
            
            // If not found, look for username in nearby elements
            if (!username) {
                const usernameElement = avatar.closest('.d-flex, .comment-main')?.querySelector('.username, .comment-author');
                username = usernameElement ? usernameElement.textContent.trim() : null;
            }
            
            if (username && username !== 'User') {
                const colorClass = `color-${generateAvatarColor(username)}`;
                avatar.classList.add(colorClass);
            }
        });
    }

    // Initialize avatars on page load
    initializeAvatars();

    // Re-initialize avatars when new comments are added
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                // Check if new avatars were added
                mutation.addedNodes.forEach(function(node) {                    if (node.nodeType === 1) { // Element node
                        const newAvatars = node.querySelectorAll ? node.querySelectorAll('.user-avatar, .user-avatar-large, .user-avatar-enhanced, .avatar-circle') : [];
                        newAvatars.forEach(avatar => {
                            // First try data-username attribute
                            let username = avatar.getAttribute('data-username');
                            
                            // If not found, look for username in nearby elements
                            if (!username) {
                                const usernameElement = avatar.closest('.d-flex, .comment-main')?.querySelector('.username, .comment-author');
                                username = usernameElement ? usernameElement.textContent.trim() : null;
                            }
                            
                            if (username && username !== 'User') {
                                const colorClass = `color-${generateAvatarColor(username)}`;
                                avatar.classList.add(colorClass);
                            }
                        });
                    }
                });
            }
        });
    });

    // Start observing
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });

    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Add loading states to forms
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function() {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<span class="spinner me-2"></span>Loading...';
            }
        });
    });

    // Search functionality with debounce
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        let searchTimeout;
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                // Auto-submit search form after 500ms of no typing
                if (this.value.length > 2 || this.value.length === 0) {
                    this.closest('form').submit();
                }
            }, 500);
        });    }

    // Only initialize rating system if not on tool detail page
    if (!document.getElementById('ratingModal')) {
        initializeRatingSystem();
    }

    // Comment system
    initializeCommentSystem();

    // Prompt helper
    initializePromptHelper();    // Icon loading verification and fixes
    // Check if Bootstrap Icons font is loaded
    const testIcon = document.createElement('i');
    testIcon.className = 'bi bi-check';
    testIcon.style.cssText = 'position: absolute; left: -9999px; font-size: 16px; visibility: visible; opacity: 1;';
    document.body.appendChild(testIcon);
    
    // Wait a bit for font to load
    setTimeout(() => {
        const iconWidth = testIcon.offsetWidth;
        const iconHeight = testIcon.offsetHeight;
        document.body.removeChild(testIcon);
        
        // If icon dimensions are 0 or very small, font didn't load properly
        if (iconWidth < 10 || iconHeight < 10) {
            console.warn('Bootstrap Icons may not be loading properly, attempting reload...');
            // Try to reload the font with a different source
            const iconLink = document.createElement('link');
            iconLink.rel = 'stylesheet';
            iconLink.href = 'https://cdnjs.cloudflare.com/ajax/libs/bootstrap-icons/1.11.3/font/bootstrap-icons.min.css';
            iconLink.crossOrigin = 'anonymous';
            iconLink.referrerPolicy = 'no-referrer';
            document.head.appendChild(iconLink);
        }
    }, 800);
    
    // Fix any icons that might not be displaying
    const allIcons = document.querySelectorAll('[class*="bi-"], .bi');
    allIcons.forEach(icon => {
        // Ensure icon has proper styles
        icon.style.fontFamily = 'bootstrap-icons, sans-serif';
        icon.style.fontStyle = 'normal';
        icon.style.fontWeight = 'normal';
        icon.style.lineHeight = '1';
        icon.style.display = 'inline-block';
        
        // Force visibility and opacity
        if (getComputedStyle(icon).visibility === 'hidden') {
            icon.style.visibility = 'visible';
        }
        if (getComputedStyle(icon).opacity === '0' || getComputedStyle(icon).opacity < 0.5) {
            icon.style.opacity = '1';
        }
        
        // Ensure proper color inheritance
        if (getComputedStyle(icon).color === 'rgba(0, 0, 0, 0)' || getComputedStyle(icon).color === 'transparent') {
            icon.style.color = 'inherit';
        }
    });
});

// Rating System
function initializeRatingSystem() {
    const ratingForms = document.querySelectorAll('.rating-form');
    
    ratingForms.forEach(form => {
        const stars = form.querySelectorAll('.star');
        const ratingInput = form.querySelector('input[name="rating"]');
        
        stars.forEach((star, index) => {
            star.addEventListener('click', function() {
                const rating = index + 1;
                ratingInput.value = rating;
                
                // Update visual state
                stars.forEach((s, i) => {
                    if (i < rating) {
                        s.classList.add('active');
                    } else {
                        s.classList.remove('active');
                    }
                });
            });
            
            star.addEventListener('mouseenter', function() {
                const rating = index + 1;
                stars.forEach((s, i) => {
                    if (i < rating) {
                        s.style.color = '#fbbf24';
                    } else {
                        s.style.color = '#e5e7eb';
                    }
                });
            });
        });
        
        form.addEventListener('mouseleave', function() {
            const currentRating = parseInt(ratingInput.value) || 0;
            stars.forEach((s, i) => {
                if (i < currentRating) {
                    s.style.color = '#fbbf24';
                } else {
                    s.style.color = '#e5e7eb';
                }
            });
        });
    });
    
    // Handle rating submission
    const ratingSubmitBtns = document.querySelectorAll('.submit-rating');
    ratingSubmitBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const form = this.closest('.rating-form');
            const toolId = form.dataset.toolId;
            const rating = form.querySelector('input[name="rating"]').value;
            const review = form.querySelector('textarea[name="review"]')?.value || '';
            
            if (!rating) {
                showAlert('Please select a rating', 'warning');
                return;
            }
            
            submitRating(toolId, rating, review);
        });
    });
}

function submitRating(toolId, rating, review) {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/rate_tool', true);
    xhr.setRequestHeader('Content-Type', 'application/json');
    
    xhr.onreadystatechange = function() {
        if (xhr.readyState === 4) {
            if (xhr.status === 200) {
                const data = JSON.parse(xhr.responseText);
                if (data.success) {
                    showAlert('Rating submitted successfully!', 'success');
                    setTimeout(() => {
                        location.reload();
                    }, 1500);
                } else {
                    showAlert(data.error || 'Failed to submit rating', 'error');
                }
            } else {
                console.error('Error:', xhr.statusText);
                showAlert('An error occurred. Please try again.', 'error');
            }
        }
    };
    
    const data = JSON.stringify({
        tool_id: toolId,
        rating: parseInt(rating),
        review: review
    });
    
    xhr.send(data);
}

// Comment System
function initializeCommentSystem() {
    const commentForms = document.querySelectorAll('.comment-form');
    
    commentForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const toolId = this.dataset.toolId;
            const comment = this.querySelector('textarea[name="comment"]').value;
            
            if (!comment.trim()) {
                showAlert('Please enter a comment', 'warning');
                return;
            }
            
            submitComment(toolId, comment);
        });
    });
}

function submitComment(toolId, comment) {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/add_comment', true);
    xhr.setRequestHeader('Content-Type', 'application/json');
    
    xhr.onreadystatechange = function() {
        if (xhr.readyState === 4) {
            if (xhr.status === 200) {
                const data = JSON.parse(xhr.responseText);
                if (data.success) {
                    showAlert('Comment added successfully!', 'success');
                    setTimeout(() => {
                        location.reload();
                    }, 1500);
                } else {
                    showAlert(data.error || 'Failed to add comment', 'error');
                }
            } else {
                console.error('Error:', xhr.statusText);
                showAlert('An error occurred. Please try again.', 'error');
            }
        }
    };
    
    const data = JSON.stringify({
        tool_id: toolId,
        comment: comment
    });
    
    xhr.send(data);
}

// Prompt Helper
function initializePromptHelper() {
    const promptForm = document.getElementById('promptForm');
    if (!promptForm) return;
    
    promptForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const prompt = document.getElementById('promptInput').value;
        if (!prompt.trim()) {
            showAlert('Please enter a prompt', 'warning');
            return;
        }
        
        getToolSuggestions(prompt);
    });
}

function getToolSuggestions(prompt) {
    const loadingDiv = document.getElementById('loadingResults');
    const resultsDiv = document.getElementById('promptResults');
    
    loadingDiv.classList.remove('d-none');
    resultsDiv.innerHTML = '';
    
    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/get_tool_suggestions', true);
    xhr.setRequestHeader('Content-Type', 'application/json');
    
    xhr.onreadystatechange = function() {
        if (xhr.readyState === 4) {
            loadingDiv.classList.add('d-none');
            
            if (xhr.status === 200) {
                const data = JSON.parse(xhr.responseText);
                if (data.suggestions && data.roadmap) {
                    displayResults(data.suggestions, data.roadmap);
                } else {
                    showAlert(data.error || 'No suggestions found', 'info');
                }
            } else {
                console.error('Error:', xhr.statusText);
                showAlert('An error occurred. Please try again.', 'error');
            }
        }
    };
    
    const data = JSON.stringify({
        prompt: prompt
    });
    
    xhr.send(data);
}

function displayResults(suggestions, roadmap) {
    const resultsDiv = document.getElementById('promptResults');
      let html = '';
    
    // Display suggested tools
    if (suggestions.length > 0) {
        html += `
            <div class="recommended-tools-section mb-5">
                <div class="section-header mb-4">
                    <div class="section-icon mb-3">
                        <i class="bi bi-lightbulb-fill"></i>
                    </div>
                    <h4 class="fw-bold mb-2 gradient-text">Recommended Tools</h4>
                    <p class="text-muted section-subtitle">Perfect AI tools curated for your specific needs</p>
                    <div class="section-divider mx-auto"></div>
                </div>                <div class="tools-grid row g-4">
        `;
        
        suggestions.forEach((tool, index) => {
            html += `
                <div class="col-md-6 mb-4">
                    <div class="tool-card-enhanced glass-card-enhanced h-100 fade-in-item" style="animation-delay: ${index * 0.15}s">
                        <div class="tool-card-content">
                            <div class="d-flex align-items-start">
                                <div class="tool-logo-enhanced me-3">
                                    ${tool.logo_url ? 
                                        `<img src="${tool.logo_url}" alt="${tool.name}" class="tool-logo-image" loading="lazy">` :
                                        `<img src="/static/images/logo-nobg.png" alt="AI Exchange AI" class="tool-logo-image default-logo" loading="lazy">`
                                    }
                                    <div class="logo-overlay"></div>
                                </div>
                                <div class="tool-info flex-grow-1">
                                    <div class="tool-header">
                                        <h6 class="tool-name">${tool.name}</h6>
                                        <div class="tool-rating">
                                            <div class="rating-stars">
                                                ${generateStars(tool.average_rating)}
                                            </div>
                                            <small class="rating-count">(${tool.total_ratings || 0})</small>
                                        </div>
                                    </div>
                                    <p class="tool-description">${tool.description ? tool.description.substring(0, 130) + '...' : 'Explore this amazing AI tool.'}</p>
                                    <div class="tool-actions">
                                        <a href="/tool/${tool.id}" class="btn btn-primary btn-enhanced btn-sm rounded-pill">
                                            <i class="bi bi-eye me-1"></i>View Details
                                        </a>
                                        ${tool.link ? `
                                            <a href="${tool.link}" target="_blank" class="btn btn-outline-primary btn-sm rounded-pill ms-2">
                                                <i class="bi bi-box-arrow-up-right me-1"></i>Try Now
                                            </a>
                                        ` : ''}
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="tool-card-glow"></div>
                    </div>
                </div>
            `;
        });
        
        html += `
                </div>
            </div>
        `;
    }
      // Display roadmap
    if (roadmap.length > 0) {
        html += `
            <div class="roadmap-section mb-5">
                <div class="section-header mb-4">
                    <div class="d-flex align-items-center mb-2">
                        <div class="section-icon me-3">
                            <i class="bi bi-map text-primary"></i>
                        </div>
                        <h4 class="fw-bold mb-0 gradient-text">Step-by-Step Roadmap</h4>
                    </div>
                    <p class="text-muted section-subtitle">Your personalized path to success</p>
                </div>
                <div class="roadmap-steps">
        `;
        
        roadmap.forEach((step, index) => {
            html += `
                <div class="roadmap-step-enhanced fade-in-item" style="animation-delay: ${(index + 3) * 0.1}s">
                    <div class="step-connector ${index === roadmap.length - 1 ? 'last-step' : ''}"></div>
                    <div class="d-flex align-items-start">
                        <div class="step-number-enhanced me-4">${step.step}</div>
                        <div class="step-content flex-grow-1">
                            <h5 class="step-title fw-bold mb-2">${step.title}</h5>
                            <p class="step-description text-muted mb-3">${step.description}</p>
                            ${step.tools.length > 0 ? `
                                <div class="step-tools row g-3">
                                    ${step.tools.map(tool => `
                                        <div class="col-md-6 mb-2">
                                            <div class="step-tool-card d-flex align-items-center">
                                                <div class="step-tool-logo me-3">
                                                    ${tool.logo_url ? 
                                                        `<img src="${tool.logo_url}" alt="${tool.name}" class="step-tool-image">` :
                                                        `<img src="/static/images/logo-nobg.png" alt="AI Exchange" class="step-tool-image default-logo">`
                                                    }
                                                </div>
                                                <div class="flex-grow-1">
                                                    <div class="step-tool-name fw-semibold">${tool.name}</div>
                                                </div>
                                                <a href="/tool/${tool.id}" class="btn btn-sm btn-outline-primary rounded-pill">
                                                    <i class="bi bi-arrow-right"></i>
                                                </a>
                                            </div>
                                        </div>
                                    `).join('')}
                                </div>
                            ` : ''}
                        </div>
                    </div>
                </div>
            `;
        });
        
        html += `</div>`;
    }
    
    resultsDiv.innerHTML = html;
    resultsDiv.classList.add('fade-in-up');
}

function generateStars(rating) {
    const safeRating = rating || 0;
    const fullStars = Math.floor(safeRating);
    const hasHalfStar = (safeRating % 1) >= 0.5;
    let stars = '';
    
    // Full stars
    for (let i = 0; i < fullStars; i++) {
        stars += '<i class="bi bi-star-fill"></i>';
    }
    
    // Half star
    if (hasHalfStar && fullStars < 5) {
        stars += '<i class="bi bi-star-half"></i>';
    }
    
    // Empty stars
    const totalFilled = fullStars + (hasHalfStar ? 1 : 0);
    const emptyStars = 5 - totalFilled;
    for (let i = 0; i < emptyStars; i++) {
        stars += '<i class="bi bi-star text-muted opacity-50"></i>';
    }
    
    return stars;
}

// Utility function to show alerts
function showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show glass-effect`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // Insert at top of main content
    const mainContent = document.querySelector('.main-content');
    if (mainContent) {
        mainContent.insertBefore(alertDiv, mainContent.firstChild);
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 5000);
    }
}

// Scroll to top functionality
const scrollToTopBtn = document.createElement('button');
scrollToTopBtn.className = 'scroll-to-top-btn';
scrollToTopBtn.style.display = 'none';
scrollToTopBtn.innerHTML = '<i class="bi bi-arrow-up"></i>';
scrollToTopBtn.setAttribute('aria-label', 'Scroll to top');
document.body.appendChild(scrollToTopBtn);

window.addEventListener('scroll', function() {
    if (window.pageYOffset > 300) {
        scrollToTopBtn.style.display = 'block';
    } else {
        scrollToTopBtn.style.display = 'none';
    }
});

scrollToTopBtn.addEventListener('click', function() {
    window.scrollTo({
        top: 0,
        behavior: 'smooth'
    });
});

// Add fade-in animation to cards on scroll
const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
};

const observer = new IntersectionObserver(function(entries) {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('fade-in-up');
        }
    });
}, observerOptions);

// Observe all cards
document.querySelectorAll('.tool-card, .glass-card, .stats-card').forEach(card => {
    observer.observe(card);
});
