// AI Exchange - Authentication Module

// Supabase client initialization
let supabase = null;
let supabaseInitializationPromise = null;

// Initialize Supabase client
async function initSupabase() {
    if (supabase) return supabase;
    if (supabaseInitializationPromise) return supabaseInitializationPromise;

    supabaseInitializationPromise = (async () => {
        try {
            const response = await fetch('/config');
            if (!response.ok) {
                console.error('Failed to fetch Supabase config:', response.status, await response.text());
                alert('Authentication configuration error. Please contact the administrator.');
                supabaseInitializationPromise = null; // Reset promise on failure
                return null;
            }
            const config = await response.json();
            const supabaseUrl = config.supabaseUrl;
            const supabaseAnonKey = config.supabaseAnonKey;

            if (!supabaseUrl || !supabaseAnonKey || supabaseUrl === '' || supabaseAnonKey === '') {
                console.error('Supabase configuration missing after fetching from /config. Ensure SUPABASE_URL and SUPABASE_ANON_KEY are set in the backend environment.');
                alert('Authentication is not configured correctly. Please contact the administrator.');
                supabaseInitializationPromise = null; // Reset promise on failure
                return null;
            }

            if (window.supabaseJs) {
                supabase = window.supabaseJs.createClient(supabaseUrl, supabaseAnonKey);
                // // console.log('Supabase client created successfully.');
            } else {
                console.error('Supabase JS library not found. Make sure it is loaded.');
                alert('Authentication library not loaded. Please refresh the page.');
                supabaseInitializationPromise = null; // Reset promise on failure
                return null;
            }
        } catch (e) {
            console.error('Error initializing Supabase client:', e);
            alert('Error initializing authentication. Please try again later.');
            supabaseInitializationPromise = null; // Reset promise on failure
            return null;
        }
        return supabase;
    })();
    return supabaseInitializationPromise;
}

// Google Sign-In
async function signInWithGoogle() {
    try {
        const client = await initSupabase();
        if (!client) {
            console.error('Supabase client failed to initialize in signInWithGoogle.');
            return;
        }
        
        // Sign in with Google
        const { data, error } = await client.auth.signInWithOAuth({
            provider: 'google',
            options: {
                redirectTo: window.location.origin + '/login' // Or your dedicated callback handler page
            }
        });
        
        if (error) {
            console.error('Supabase OAuth error:', error);
            if (typeof flashMessage === 'function') {
                flashMessage('Google sign-in failed: ' + error.message, 'error');
            } else {
                alert('Google sign-in failed: ' + error.message);
            }
            throw error; // Re-throw for the calling context in login.html to handle button state
        }
        
        // Redirect happens automatically
        
    } catch (error) {
        console.error('Google sign-in error:', error);
        // flashMessage is preferred if available and works on the current page context
        if (typeof flashMessage === 'function') {
            flashMessage('An unexpected error occurred during Google sign-in. Please try again.', 'error');
        } else {
            alert('An unexpected error occurred during Google sign-in. Please try again.');
        }
        throw error; // Re-throw for the calling context in login.html to handle button state
    }
}

// Sign out
async function signOut() {
    try {
        const client = await initSupabase();
        if (!client) {
            console.error('Supabase client failed to initialize in signOut.');
            return;
        }
        
        const { error } = await client.auth.signOut();
        if (error) {
            console.error('Supabase sign out error:', error);
            alert('Failed to sign out: ' + error.message);
            return;
        }
        
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
        const client = await initSupabase();
        if (!client) {
            console.error('Supabase client failed to initialize in checkAuth.');
            return null;
        }
        
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
        const client = await initSupabase();
        if (!client) {
            console.error('Supabase client failed to initialize in getCurrentUser.');
            return null;
        }
        
        const { data: { user } } = await client.auth.getUser();
        return user;
        
    } catch (error) {
        console.error('Get user error:', error);
        return null;
    }
}

// Initialize event listeners or auth state checks
function initAuthEventListeners() {
    // Setup event listeners for login/register buttons if they exist
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        // Assuming handleLogin is defined elsewhere or part of a larger auth object
        // loginForm.addEventListener('submit', handleLogin);
    }

    const registerForm = document.getElementById('registerForm');
    if (registerForm) {
        // Assuming handleRegister is defined elsewhere
        // registerForm.addEventListener('submit', handleRegister);
    }

    const googleSignInBtn = document.getElementById('googleSignInBtn');
    if (googleSignInBtn) {
        googleSignInBtn.addEventListener('click', async function(event) {
            event.preventDefault();
            googleSignInBtn.disabled = true;
            googleSignInBtn.classList.add('btn-loading');
            try {
                await signInWithGoogle();
            } catch (error) {
                googleSignInBtn.disabled = false;
                googleSignInBtn.classList.remove('btn-loading');
            }
        });
    }

    const googleSignUpBtn = document.getElementById('googleSignUpBtn');
    if (googleSignUpBtn) {
        googleSignUpBtn.addEventListener('click', async function(event) {
            event.preventDefault();
            googleSignUpBtn.disabled = true;
            googleSignUpBtn.classList.add('btn-loading');
            try {
                await signInWithGoogle(); // Assuming sign-up also uses the same OAuth flow
            } catch (error) {
                googleSignUpBtn.disabled = false;
                googleSignUpBtn.classList.remove('btn-loading');
            }
        });
    }

    const logoutButton = document.getElementById('logoutButton');
    if (logoutButton) {
        logoutButton.addEventListener('click', async (e) => {
            e.preventDefault();
            await signOut();
            // window.location.href = '/login'; // Redirect handled by signOut or backend
        });
    }
}

// This function is intended to be called when the page loads and there's an OAuth redirect hash.
async function handleAuthRedirect() {
    // // console.log('[AUTH.JS]handleAuthRedirect: Called.');

    if (window.location.hash.includes('access_token')) {
        // // console.log('[AUTH.JS]handleAuthRedirect: Found "access_token" in URL hash.');
        const params = new URLSearchParams(window.location.hash.substring(1)); // remove #
        const accessToken = params.get('access_token');
        const refreshToken = params.get('refresh_token');
        const error = params.get('error');
        const errorDescription = params.get('error_description');

        if (error) {
            console.error('OAuth Error from hash (in handleAuthRedirect):', error, errorDescription);
            flashMessage(`Authentication error: ${decodeURIComponent(errorDescription || error)}`, 'danger');
            window.location.hash = ''; // Clear hash
            if (window.location.pathname !== '/login') {
                 window.location.href = '/login?error=' + encodeURIComponent(errorDescription || error);
            }
            return;
        }

        if (accessToken) {
            // // console.log('[AUTH.JS]handleAuthRedirect: Extracted tokens:', { accessToken: !!accessToken, refreshToken: !!refreshToken });
            
            // Clear the hash to prevent re-processing and clean up URL
            history.pushState("", document.title, window.location.pathname + window.location.search);

            // Show a loading indicator if possible
            const googleSignInBtn = document.getElementById('googleSignInBtn');
            if (googleSignInBtn) {
                googleSignInBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status"></span>Finalizing login...';
                googleSignInBtn.disabled = true;
            }

            try {
                // // console.log('[AUTH.JS]handleAuthRedirect: Calling backend /auth/callback with tokens.');
                // IMPORTANT: The backend /auth/callback should handle these tokens, set the session, and then redirect.
                // This fetch is to inform the backend. The backend's response will dictate the final redirect.
                const response = await fetch(`/auth/callback?access_token=${encodeURIComponent(accessToken)}&refresh_token=${encodeURIComponent(refreshToken || '')}`, {
                    method: 'GET', // Ensure your backend /auth/callback accepts GET
                    headers: {
                        'Accept': 'application/json'
                    }
                });
                
                if (!response.ok) {
                    let errorDetails = await response.text(); // Get raw text first
                    let errorData;
                    try {
                        errorData = JSON.parse(errorDetails); // Try to parse as JSON
                    } catch (e) {
                        errorData = { error: 'Unknown error during callback processing.', details: errorDetails };
                    }
                    console.error('Backend /auth/callback error response:', errorData);
                    throw new Error(errorData.error || `Server error: ${response.status}. Details: ${errorData.details}`);
                }

                const result = await response.json();
                // // console.log('[AUTH.JS]handleAuthRedirect: Backend response:', result);

                if (result.success) {
                    // // console.log('[AUTH.JS]handleAuthRedirect: Backend confirmed success. Redirecting based on backend response or to home.');
                    // Backend should ideally dictate the redirect URL in its response or handle it fully.
                    // If backend sends a redirect_url:
                    if (result.redirect_url) {
                        window.location.href = result.redirect_url;
                    } else {
                        // Fallback redirect if backend doesn't specify one
                        const nextUrl = new URLSearchParams(window.location.search).get('next') || '/';
                        window.location.href = nextUrl;
                    }
                } else {
                    console.error('[AUTH.JS]handleAuthRedirect: Backend indicated failure:', result.error);
                    flashMessage(result.error || 'Authentication failed after callback. Please try again.', 'danger');
                    if (googleSignInBtn) {
                        googleSignInBtn.innerHTML = 'Continue with Google'; // Restore button
                        googleSignInBtn.disabled = false;
                    }
                    if (window.location.pathname !== '/login') {
                        window.location.href = '/login?error=backend_callback_failed';
                    }
                }
            } catch (fetchError) {
                console.error('[AUTH.JS]handleAuthRedirect: Error during fetch to /auth/callback:', fetchError);
                flashMessage('An error occurred while finalizing your login. Please try again.', 'danger');
                if (googleSignInBtn) {
                    googleSignInBtn.innerHTML = 'Continue with Google'; // Restore button
                    googleSignInBtn.disabled = false;
                }
                if (window.location.pathname !== '/login') {
                     window.location.href = '/login?error=fetch_callback_failed';
                }
            }
        } else {
            console.error('[AUTH.JS]handleAuthRedirect: "access_token" not found in hash after check.');
            // This case should ideally be caught by the error check above if Google provides an error in hash.
        }
    } else if (window.location.hash.includes('error=')) { // Explicitly check for error if no access_token
        const params = new URLSearchParams(window.location.hash.substring(1));
        const error = params.get('error');
        const errorDescription = params.get('error_description');
        console.error('OAuth Error from hash (direct error check):', error, errorDescription);
        flashMessage(`Authentication error: ${decodeURIComponent(errorDescription || error)}`, 'danger');
        window.location.hash = ''; // Clear hash
        if (window.location.pathname !== '/login') {
            window.location.href = '/login?error=' + encodeURIComponent(errorDescription || error);
        }
    } else {
        // // console.log('[AUTH.JS]handleAuthRedirect: No "access_token" or "error" found in URL hash. No OAuth redirect to handle.');
    }
}

// Consolidated DOMContentLoaded listener
document.addEventListener('DOMContentLoaded', async () => {
    // // console.log('[AUTH.JS] DOMContentLoaded: Initializing...');
    
    await initSupabase(); // Initialize Supabase client first

    // Check for OAuth redirect hash and handle it
    // This needs to run after Supabase is initialized if it relies on the client,
    // but handleAuthRedirect as written primarily parses the hash and calls the backend.
    if (window.location.hash.includes('access_token') || window.location.hash.includes('error=')) {
        // // console.log('[AUTH.JS] DOMContentLoaded: OAuth redirect detected in URL hash.');
        await handleAuthRedirect(); // Await this if it performs async operations before potential redirect
    } else {
        // // console.log('[AUTH.JS] DOMContentLoaded: No OAuth redirect in URL hash.');
    }

    initAuthEventListeners(); // Setup event listeners for buttons etc.
    
    // Any other auth-related checks or UI updates on page load can go here.
    // For example, updating UI based on authentication state:
    // const session = await checkAuth();
    // if (session) {
    //     // console.log('[AUTH.JS] User is logged in:', session.user.email);
    //     // Update UI accordingly
    // } else {
    //     // console.log('[AUTH.JS] User is not logged in.');
    //     // Update UI accordingly
    // }
});

// Helper function to display flash messages
function flashMessage(message, category = 'info') {
    // This is a placeholder. Implement this based on your app's notification system.
    // For example, creating a div, adding it to the DOM, and then removing it.
    // // console.log(`FLASH (${category}): ${message}`);
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
