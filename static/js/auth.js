// AI Exchange - Authentication Module

// Supabase client initialization
let supabase = null;

// Initialize Supabase client
function initSupabase() {
    if (supabase) return supabase;
      // Get Supabase URL and Anon Key from meta tags
    const supabaseUrl = document.querySelector('meta[name="supabase-url"]')?.content;
    const supabaseAnonKey = document.querySelector('meta[name="supabase-anon-key"]')?.content;
    
    // console.log('Supabase Config:', { url: supabaseUrl, hasKey: !!supabaseAnonKey });
    
    if (!supabaseUrl || !supabaseAnonKey || supabaseUrl === '' || supabaseAnonKey === '') {
        console.error('Supabase configuration missing. Please set the SUPABASE_URL and SUPABASE_ANON_KEY environment variables.');
        alert('Authentication is not configured. Please contact the administrator.');
        return null;    }
    
    // Create Supabase client - using the global supabase object
    try {
        // The variable supabaseJs was set in layout.html
        if (window.supabaseJs) {
            // console.log('Using global supabase client from window.supabaseJs');
            supabase = window.supabaseJs.createClient(supabaseUrl, supabaseAnonKey);
            // console.log('Supabase client created successfully');
        } else {
            console.error('Supabase JS library not available (window.supabaseJs is undefined)');
            alert('Authentication system error: Supabase library not loaded properly. Try refreshing the page.');
            return null;
        }
    } catch (e) {
        console.error('Error creating Supabase client:', e);
        console.error('Error details:', { message: e.message, url: supabaseUrl, hasKey: !!supabaseAnonKey });
        alert('Error initializing authentication. Please try again later.');
        return null;
    }
    return supabase;
}

// Google Sign-In
async function signInWithGoogle() {
    try {
        // console.log('Initializing Supabase client...');
        const client = initSupabase();
        if (!client) throw new Error('Supabase client not initialized');
        
        // console.log('Supabase client initialized successfully.');
        // Sign in with Google
        const { data, error } = await client.auth.signInWithOAuth({
            provider: 'google',
            options: {
                redirectTo: window.location.origin + '/login' // CHANGED: Redirect to login page
            }
        });
        
        if (error) throw error;
        
        // Redirect happens automatically
        
    } catch (error) {
        console.error('Google sign-in error:', error);
        // flashMessage is preferred if available and works on the current page context
        if (typeof flashMessage === 'function') {
            flashMessage('Failed to sign in with Google. Please try again.', 'danger');
        } else {
            alert('Failed to sign in with Google. Please try again.');
        }
        throw error; // Re-throw for the calling context in login.html to handle button state
    }
}

// Sign out
async function signOut() {
    try {
        const client = initSupabase();
        if (!client) throw new Error('Supabase client not initialized');
        
        const { error } = await client.auth.signOut();
        if (error) throw error;
        
        // Redirect to home page
        window.location.href = '/';
        
    } catch (error) {
        console.error('Sign out error:', error);
        alert('Failed to sign out. Please try again.');
    }
}

// Check if user is authenticated
async function checkAuth() {
    try {
        const client = initSupabase();
        if (!client) return null;
        
        const { data: { session } } = await client.auth.getSession();
        return session;
        
    } catch (error) {
        console.error('Auth check error:', error);
        return null;
    }
}

// Get current user
async function getCurrentUser() {
    try {
        const client = initSupabase();
        if (!client) return null;
        
        const { data: { user } } = await client.auth.getUser();
        return user;
        
    } catch (error) {
        console.error('Get user error:', error);
        return null;
    }
}

// Initialize auth on page load
document.addEventListener('DOMContentLoaded', () => {
    // Initialize Supabase client
    initSupabase();
});

// Initialize event listeners or auth state checks
function initAuth() {
    // Setup event listeners for login/register buttons if they exist
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }

    const registerForm = document.getElementById('registerForm');
    if (registerForm) {
        registerForm.addEventListener('submit', handleRegister);
    }

    const googleSignInBtn = document.getElementById('googleSignInBtn');
    if (googleSignInBtn) {
        googleSignInBtn.addEventListener('click', function(event) {
            event.preventDefault();
            signInWithGoogle();
        });
    }
    
    const googleSignUpBtn = document.getElementById('googleSignUpBtn');
    if (googleSignUpBtn) {
        googleSignUpBtn.addEventListener('click', function(event) {
            event.preventDefault();
            signInWithGoogle(); // Same OAuth flow for sign-up
        });
    }

    const logoutButton = document.getElementById('logoutButton'); // Assuming you have a logout button with this ID
    if (logoutButton) {
        logoutButton.addEventListener('click', async (e) => {
            e.preventDefault();
            await signOut();
            window.location.href = '/login'; // Or wherever you redirect after logout
        });
    }
}

// New/Updated handleAuthRedirect and DOMContentLoaded listener:
document.addEventListener('DOMContentLoaded', function() {
    // console.log('[AUTH.JS]DOMContentLoaded: Script loaded. Current path:', window.location.pathname);
    // console.log('[AUTH.JS]DOMContentLoaded: Full URL:', window.location.href);
    // console.log('[AUTH.JS]DOMContentLoaded: URL Hash:', window.location.hash);
    
    // Initialize Supabase client as it's needed by various functions
    initSupabase(); 

    // Always check for OAuth tokens or error in the hash on any page load after potential OAuth redirect.
    if (window.location.hash.includes('access_token') || window.location.hash.includes('error=')) {
        // console.log('[AUTH.JS]DOMContentLoaded: Found OAuth tokens or error in URL hash. Attempting to handle redirect.');
        handleAuthRedirect(); // This function will parse the hash and redirect to the backend
    } else {
        // console.log('[AUTH.JS]DOMContentLoaded: No OAuth tokens or error found in URL hash.');
    }

    // Call initAuth to setup event listeners
    initAuth();
});

async function handleAuthRedirect() {
    // console.log('[AUTH.JS]handleAuthRedirect: Called. Current path:', window.location.pathname);
    // console.log('[AUTH.JS]handleAuthRedirect: Full URL:', window.location.href);
    // console.log('[AUTH.JS]handleAuthRedirect: URL Hash:', window.location.hash);

    if (window.location.hash.includes('access_token')) {
        // console.log('[AUTH.JS]handleAuthRedirect: Found "access_token" in URL hash.');
        const params = new URLSearchParams(window.location.hash.substring(1)); // remove #
        const accessToken = params.get('access_token');
        const refreshToken = params.get('refresh_token');

        if (accessToken) {
            // console.log('[AUTH.JS]handleAuthRedirect: Extracted tokens:', { accessToken: !!accessToken, refreshToken: !!refreshToken });
            
            let backendCallbackUrl = `/auth/callback?access_token=${encodeURIComponent(accessToken)}`;
            if (refreshToken) {
                backendCallbackUrl += `&refresh_token=${encodeURIComponent(refreshToken)}`;
            }
            
            // console.log('[AUTH.JS]handleAuthRedirect: Redirecting to backend:', backendCallbackUrl);
            window.location.replace(backendCallbackUrl); 
        } else {
            console.error('[AUTH.JS]handleAuthRedirect: "access_token" found in hash, but could not parse it.');
            alert('Authentication failed: Could not process authentication tokens.');
            window.location.href = '/login?error=token_parse_failed';
        }
    } else {
        // console.log('[AUTH.JS]handleAuthRedirect: No "access_token" found in URL hash.');
        if (window.location.pathname === '/auth/callback') {
            const errorParams = new URLSearchParams(window.location.hash.substring(1));
            const error = errorParams.get('error');
            const errorDescription = errorParams.get('error_description');

            if (error || errorDescription) {
                console.error('[AUTH.JS]handleAuthRedirect: OAuth Error:', { error, errorDescription: decodeURIComponent(errorDescription || '') });
                alert('Authentication failed: ' + decodeURIComponent(errorDescription || error || 'Unknown error from provider.'));
            } else {
                console.error('[AUTH.JS]handleAuthRedirect: On /auth/callback but no "access_token" in hash and no explicit error. This is unexpected.');
                alert('Authentication callback error. Please try again.');
            }
            window.location.href = '/login?error=callback_error_or_missing_token';
        }
    }
}

// Handle OAuth callback - THIS FUNCTION WILL BE MODIFIED
async function handleOAuthCallback() {
    // console.log('handleOAuthCallback: Starting');
    const hash = window.location.hash.substring(1);
    const params = new URLSearchParams(hash);
    const accessToken = params.get('access_token');
    const refreshToken = params.get('refresh_token');
    const error = params.get('error');
    const errorDescription = params.get('error_description');

    // console.log('handleOAuthCallback: Parsed params from hash:', { accessToken: !!accessToken, refreshToken: !!refreshToken, error, errorDescription });

    if (error) {
        console.error('OAuth Error from hash:', error, errorDescription);
        flashMessage(`Authentication error: ${errorDescription || error}`, 'danger');
        // Clear the hash to prevent re-processing
        window.location.hash = '';
        // Optionally redirect to login or show error on current page
        if (window.location.pathname !== '/login') {
            // window.location.href = '/login?error=' + encodeURIComponent(errorDescription || error);
        }
        return;
    }

    if (accessToken && refreshToken) {
        // console.log('handleOAuthCallback: Access and Refresh tokens found in hash.');
        // Clear the hash to prevent re-processing and clean up URL
        history.pushState("", document.title, window.location.pathname + window.location.search);


        // Show a loading indicator if possible (e.g., on login page)
        const googleSignInBtn = document.getElementById('googleSignInBtn');
        if (googleSignInBtn) {
            googleSignInBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status"></span>Finalizing login...';
            googleSignInBtn.disabled = true;
        }

        try {
            // console.log('handleOAuthCallback: Calling backend /auth/callback with tokens.');
            const response = await fetch(`/auth/callback?access_token=${encodeURIComponent(accessToken)}&refresh_token=${encodeURIComponent(refreshToken)}`, {
                headers: {
                    'Accept': 'application/json' // Ensure backend knows we expect JSON
                }
            });
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ error: 'Unknown error during callback processing.' }));
                throw new Error(errorData.error || `Server error: ${response.status}`);
            }

            const result = await response.json();
            // console.log('handleOAuthCallback: Backend response:', result);

            if (result.success) {
                // console.log('handleOAuthCallback: Backend confirmed success. Redirecting to home.');
                // Backend has set the session, now redirect to the main page or intended destination
                // Check for a 'next' URL parameter if your app uses it, otherwise default to '/'
                const nextUrl = new URLSearchParams(window.location.search).get('next') || '/';
                window.location.href = nextUrl;
            } else {
                console.error('handleOAuthCallback: Backend indicated failure:', result.error);
                flashMessage(result.error || 'Authentication failed after callback. Please try again.', 'danger');
                if (googleSignInBtn) {
                    // Restore original button text (ensure SVG is complete or use text)
                    googleSignInBtn.innerHTML = '<svg class="me-2" width="20" height="20" viewBox="0 0 24 24"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg> Continue with Google';
                    googleSignInBtn.disabled = false;
                }
                 // Redirect to login page on failure to give user a clear state
                if (window.location.pathname !== '/login') {
                    window.location.href = '/login';
                }
            }
        } catch (fetchError) {
            console.error('handleOAuthCallback: Error during fetch to /auth/callback:', fetchError);
            flashMessage('An error occurred while finalizing your login. Please try again.', 'danger');
            if (googleSignInBtn) {
                 // Restore original button text
                googleSignInBtn.innerHTML = '<svg class="me-2" width="20" height="20" viewBox="0 0 24 24"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg> Continue with Google';
                googleSignInBtn.disabled = false;
            }
            if (window.location.pathname !== '/login') {
                window.location.href = '/login';
            }
        }
    } else if (window.location.pathname.includes('/auth/callback') && (new URLSearchParams(window.location.search)).has('access_token')) {
        // This case is when Supabase redirects directly to /auth/callback with tokens in query string
        // This part of the logic might now be fully handled by the backend,
        // but we keep the console log for clarity.
        // The backend /auth/callback will handle this and redirect.
        // console.log('handleOAuthCallback: Detected direct load of /auth/callback with tokens in query string. Backend will handle.');
    } else {
        // console.log('handleOAuthCallback: No tokens or error in hash. No action needed by this function on this page load.');
    }
}

// Helper function to display flash messages (you might have this already or use a library)
function flashMessage(message, category = 'info') {
    // This is a placeholder. Implement this based on your app's notification system.
    // For example, creating a div, adding it to the DOM, and then removing it.
    // console.log(`FLASH (${category}): ${message}`);
    const flashContainer = document.querySelector('.flash-messages-container'); // Assuming you have a container
    if (flashContainer) {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${category} alert-dismissible fade show`;
        alertDiv.role = 'alert';
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        flashContainer.appendChild(alertDiv);
        // Auto-dismiss after some time
        setTimeout(() => {
            // Check if the alertDiv is still in the DOM before trying to dismiss
            if (alertDiv.parentElement) {
                // Use Bootstrap's alert dismiss method if available, otherwise just remove
                const bsAlert = typeof bootstrap !== 'undefined' && bootstrap.Alert ? bootstrap.Alert.getInstance(alertDiv) : null;
                if (bsAlert) {
                    bsAlert.close();
                } else {
                    alertDiv.remove();
                }
            }
        }, 7000);
    } else {
        alert(message); // Fallback
    }
}


// Ensure initSupabase is called and handleOAuthCallback is run on page load
document.addEventListener('DOMContentLoaded', () => {
    // console.log('DOMContentLoaded: Initializing Supabase and checking for OAuth callback.');
    initSupabase(); // Initialize Supabase client early

    // Check if the URL hash contains OAuth tokens or an error
    if (window.location.hash.includes('access_token') || window.location.hash.includes('error')) {
        // console.log('DOMContentLoaded: Hash contains OAuth info, calling handleOAuthCallback.');
        handleOAuthCallback();
    } else {
        // console.log('DOMContentLoaded: No OAuth info in hash.');
    }

    // Add event listener for Google Sign-In button if it exists on the page
    const googleSignInBtn = document.getElementById('googleSignInBtn');
    if (googleSignInBtn) {
        googleSignInBtn.addEventListener('click', async function() {
            try {
                if (typeof signInWithGoogle === 'undefined') {
                    console.error('signInWithGoogle function not found. Make sure auth.js is loaded and initialized.');
                    flashMessage('Authentication system not ready. Please refresh the page and try again.', 'danger');
                    return;
                }
                
                googleSignInBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status"></span>Redirecting to Google...';
                googleSignInBtn.disabled = true;
                
                await signInWithGoogle();
                // signInWithGoogle initiates OAuth flow, browser will redirect.
                // Button text will be reset if user comes back to this page and flow failed before redirect.
                
            } catch (error) {
                console.error('Error initiating Google Sign-In:', error);
                flashMessage(error.message || 'Error initiating Google Sign-In. Please try again.', 'danger');
                googleSignInBtn.innerHTML = '<svg class="me-2" width="20" height="20" viewBox="0 0 24 24"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg> Continue with Google'; // Reset button text
                googleSignInBtn.disabled = false;
            }
        });
    }
});
