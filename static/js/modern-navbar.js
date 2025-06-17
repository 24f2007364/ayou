/**
 * Modern Navbar JavaScript
 * Handles mobile menu, dropdown, and scroll effects
 */

class ModernNavbar {
    constructor() {
        this.navbar = document.querySelector('.modern-navbar');
        this.mobileToggle = document.querySelector('.mobile-menu-toggle');
        this.mobileMenu = document.querySelector('.mobile-menu');
        this.userDropdown = document.querySelector('.user-dropdown-modern');
        this.userTrigger = document.querySelector('.user-trigger-modern');
        this.dropdownMenu = document.querySelector('.dropdown-menu-modern');
        this.backdrop = null;
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.handleScroll();
        this.createBackdrop();
    }
    
    bindEvents() {
        // Mobile menu toggle
        if (this.mobileToggle && this.mobileMenu) {
            this.mobileToggle.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleMobileMenu();
            });
        }
        
        // User dropdown toggle
        if (this.userTrigger && this.dropdownMenu) {
            this.userTrigger.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.toggleUserDropdown();
            });
        }
        
        // Close dropdowns when clicking outside
        document.addEventListener('click', (e) => {
            this.handleOutsideClick(e);
        });
        
        // Handle escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeAllMenus();
            }
        });
        
        // Scroll effect
        window.addEventListener('scroll', () => {
            this.handleScroll();
        });
        
        // Handle window resize
        window.addEventListener('resize', () => {
            this.handleResize();
        });
        
        // Close mobile menu when clicking on nav links
        const mobileNavLinks = document.querySelectorAll('.mobile-nav-link');
        mobileNavLinks.forEach(link => {
            link.addEventListener('click', () => {
                this.closeMobileMenu();
            });
        });
    }
    
    createBackdrop() {
        this.backdrop = document.createElement('div');
        this.backdrop.className = 'mobile-backdrop';
        document.body.appendChild(this.backdrop);
        
        this.backdrop.addEventListener('click', () => {
            this.closeAllMenus();
        });
    }
    
    toggleMobileMenu() {
        const isOpen = this.mobileMenu.classList.contains('show');
        
        if (isOpen) {
            this.closeMobileMenu();
        } else {
            this.openMobileMenu();
        }
    }
    
    openMobileMenu() {
        this.mobileMenu.classList.add('show');
        this.mobileToggle.classList.add('active');
        this.backdrop.classList.add('show');
        document.body.style.overflow = 'hidden';
        
        // Close user dropdown if open
        this.closeUserDropdown();
    }
    
    closeMobileMenu() {
        this.mobileMenu.classList.remove('show');
        this.mobileToggle.classList.remove('active');
        this.backdrop.classList.remove('show');
        document.body.style.overflow = '';
    }
    
    toggleUserDropdown() {
        const isOpen = this.userDropdown.classList.contains('show');
        
        if (isOpen) {
            this.closeUserDropdown();
        } else {
            this.openUserDropdown();
        }
    }
    
    openUserDropdown() {
        this.userDropdown.classList.add('show');
        this.dropdownMenu.classList.add('show');
        
        // Close mobile menu if open
        this.closeMobileMenu();
    }
    
    closeUserDropdown() {
        this.userDropdown.classList.remove('show');
        this.dropdownMenu.classList.remove('show');
    }
    
    closeAllMenus() {
        this.closeMobileMenu();
        this.closeUserDropdown();
    }
    
    handleOutsideClick(e) {
        // Close user dropdown if clicking outside
        if (this.userDropdown && !this.userDropdown.contains(e.target)) {
            this.closeUserDropdown();
        }
        
        // Close mobile menu if clicking outside (handled by backdrop)
    }
    
    handleScroll() {
        if (!this.navbar) return;
        
        const scrollY = window.scrollY;
        
        if (scrollY > 50) {
            this.navbar.classList.add('scrolled');
        } else {
            this.navbar.classList.remove('scrolled');
        }
    }
    
    handleResize() {
        // Close mobile menu on resize to desktop
        if (window.innerWidth > 991.98) {
            this.closeMobileMenu();
        }
    }
    
    // Method to highlight active nav item
    setActiveNavItem(path) {
        const navLinks = document.querySelectorAll('.nav-link-modern, .mobile-nav-link');
        
        navLinks.forEach(link => {
            link.classList.remove('active');
            
            // Check if this link's href matches the current path
            const href = link.getAttribute('href');
            if (href && (href === path || (path !== '/' && href.includes(path)))) {
                link.classList.add('active');
            }
        });
    }
    
    // Method to update user avatar background
    static generateAvatarColor(username) {
        if (!username) return 'theme-1';
        
        const themes = [
            'theme-1', 'theme-2', 'theme-3', 'theme-4', 'theme-5',
            'theme-6', 'theme-7', 'theme-8', 'theme-9', 'theme-10'
        ];
        
        let hash = 0;
        for (let i = 0; i < username.length; i++) {
            const char = username.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash; // Convert to 32bit integer
        }
        
        return themes[Math.abs(hash) % themes.length];
    }
    
    // Method to initialize user avatar
    initUserAvatar() {
        const avatar = document.querySelector('.user-avatar-modern');
        if (avatar && avatar.dataset.username) {
            const username = avatar.dataset.username;
            const colorTheme = ModernNavbar.generateAvatarColor(username);
            avatar.classList.add(colorTheme);
        }
    }
}

// Smooth scroll for anchor links
function smoothScrollTo(target) {
    const element = document.querySelector(target);
    if (element) {
        element.scrollIntoView({
            behavior: 'smooth',
            block: 'start'
        });
    }
}

// Initialize navbar when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    const navbar = new ModernNavbar();
    
    // Set active nav item based on current path
    const currentPath = window.location.pathname;
    navbar.setActiveNavItem(currentPath);
    
    // Initialize user avatar colors
    navbar.initUserAvatar();
    
    // Handle smooth scroll for anchor links
    const anchorLinks = document.querySelectorAll('a[href^="#"]');
    anchorLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            const href = link.getAttribute('href');
            if (href !== '#' && href.length > 1) {
                e.preventDefault();
                smoothScrollTo(href);
            }
        });
    });
});

// Utility function to show notifications
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <div class="notification-content">
            <span class="notification-message">${message}</span>
            <button class="notification-close" aria-label="Close">
                <i class="bi bi-x"></i>
            </button>
        </div>
    `;
    
    // Add to page
    document.body.appendChild(notification);
    
    // Show notification
    setTimeout(() => notification.classList.add('show'), 100);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 300);
    }, 5000);
    
    // Handle close button
    const closeBtn = notification.querySelector('.notification-close');
    closeBtn.addEventListener('click', () => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 300);
    });
}

// Export for use in other scripts
window.ModernNavbar = ModernNavbar;
window.showNotification = showNotification;
