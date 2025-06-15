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
    });    // Add loading states to forms (except submit tool form which has its own handler)
    const forms = document.querySelectorAll('form:not(#submitForm)');
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

    // Comment system    initializeCommentSystem();// Icon loading verification and fixes
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
            // console.warn('Bootstrap Icons may not be loading properly, attempting reload...');
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
