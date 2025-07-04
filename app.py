from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
import sqlite3
import os
from datetime import datetime, timedelta
import re
import tempfile
import json

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv() # This should be called as early as possible

# Supabase integration
import supabase as sb

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY')

# Supabase configuration - these must be set as environment variables
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_ANON_KEY = os.environ.get('SUPABASE_ANON_KEY')
SUPABASE_SERVICE_ROLE_KEY = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')

# Initialize Supabase client
supabase_client = None
if SUPABASE_URL and SUPABASE_ANON_KEY:
    try:
        supabase_client = sb.create_client(SUPABASE_URL, SUPABASE_ANON_KEY) # Initialize the client
        print("Supabase client initialized successfully.")
    except Exception as e:
        print(f"Error initializing Supabase client: {e}")
else:
    print("Supabase configuration missing. Set SUPABASE_URL and SUPABASE_ANON_KEY environment variables.")



@app.route('/config')
def get_config():
    return jsonify({
        'supabaseUrl': SUPABASE_URL,
        'supabaseAnonKey': SUPABASE_ANON_KEY
    })

# Session configuration for better security
app.config.update(
    SESSION_COOKIE_SECURE=True if os.environ.get('VERCEL') else False,  # HTTPS only in production
    SESSION_COOKIE_HTTPONLY=True,  # Prevent XSS
    SESSION_COOKIE_SAMESITE='Lax',  # CSRF protection
    PERMANENT_SESSION_LIFETIME=timedelta(days=30)  # Session expires in 30 days
)

# Use temporary directory for uploads in serverless environment
app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()

# Register template filter
@app.template_filter('format_date')
def format_date_filter(date_str):
    """Template filter to format datetime strings"""
    return format_datetime(date_str)

@app.template_filter('from_json')
def from_json_filter(json_str):
    """Template filter to parse JSON strings"""
    if not json_str:
        return []
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return []

def get_db_path():
        return 'database.db'

# Database initialization
def init_db():
    """Initialize database - Supabase for production, SQLite for local"""
    if os.environ.get('SUPABASE_URL') and os.environ.get('SUPABASE_ANON_KEY'):
        init_supabase_db()


def init_supabase_db():
    """Initialize Supabase database tables"""
    # Supabase tables should be created via the dashboard or SQL editor
    # We don't need to create them programmatically since we're using REST API
    print("Supabase initialization complete - tables should exist in dashboard")

def get_db_connection():
    """Get database connection - Supabase for production, SQLite for local"""
    supabase_url = os.environ.get('SUPABASE_URL')
    supabase_key = os.environ.get('SUPABASE_ANON_KEY')
    
    print(f"DEBUG: SUPABASE_URL exists: {bool(supabase_url)}")
    print(f"DEBUG: SUPABASE_ANON_KEY exists: {bool(supabase_key)}")
    
    if supabase_url and supabase_key:
        try:
            print("DEBUG: Attempting to use Supabase")
            return SupabaseConnection()
        except Exception as e:
            print(f"DEBUG: Supabase connection failed: {e}")
            print("DEBUG: Falling back to SQLite")
    else:
        print("DEBUG: Using SQLite (no Supabase env vars)")
    


class SupabaseConnection:
    """Supabase database connection using REST API"""
    def __init__(self):
        import requests
        
        self.base_url = os.environ.get('SUPABASE_URL')
        self.api_key = os.environ.get('SUPABASE_ANON_KEY')
        self.headers = {
            'apikey': self.api_key,
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'Prefer': 'return=representation'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self._result = None
        self.lastrowid = None
    
    def cursor(self):
        """Return self to act as cursor (for SQLite compatibility)"""
        return self
    
    def execute(self, sql, params=None):
        """Execute SQL-like operations via Supabase REST API"""
        sql_lower = sql.lower().strip()
        
        try:            # SELECT COUNT(*) queries - handle both 'count(*)' and 'count(*) as count' formats
            if ('select count(*) from tools' in sql_lower or 
                'select count(*) as count from tools' in sql_lower):
                if 'data_import_completed' in sql_lower:
                    response = self.session.get(f"{self.base_url}/rest/v1/tools?name=eq.DATA_IMPORT_COMPLETED&select=id")
                    if response.status_code == 200:
                        data = response.json()
                        self._result = [(len(data),)]
                    else:
                        self._result = [(0,)]
                elif 'where 1=1' in sql_lower:
                    # Handle count query with filters for pagination
                    url = f"{self.base_url}/rest/v1/tools?select=id"
                    filters = []
                    
                    if params:
                        param_idx = 0
                        if 'name like' in sql_lower or 'description like' in sql_lower:
                            search_term = params[param_idx].replace('%', '')
                            filters.append(f"or=(name.ilike.%{search_term}%,description.ilike.%{search_term}%)")
                            param_idx += 2  # Skip both search params
                        
                        if param_idx < len(params) and 'category =' in sql_lower:
                            category = params[param_idx]
                            filters.append(f"category=eq.{category}")
                            param_idx += 1
                        
                        if param_idx < len(params) and 'country_of_origin =' in sql_lower:
                            country = params[param_idx]
                            filters.append(f"country_of_origin=eq.{country}")
                            param_idx += 1
                        
                        if param_idx < len(params) and 'pricing_model =' in sql_lower:
                            price_model = params[param_idx]
                            filters.append(f"pricing_model=eq.{price_model}")
                            param_idx += 1
                    
                    if filters:
                        url += "&" + "&".join(filters)
                    
                    response = self.session.get(url)
                    if response.status_code == 200:
                        data = response.json()
                        self._result = [(len(data),)]
                    else:
                        self._result = [(0,)]
                else:
                    # Use the PostgreSQL function for accurate count
                    try:
                        response = self.session.post(
                            f"{self.base_url}/rest/v1/rpc/get_tools_count",
                            json={}
                        )
                        if response.status_code == 200:
                            count = response.json()
                            print(f"DEBUG: PostgreSQL function returned count: {count}")
                            self._result = [(count,)]
                        else:
                            print(f"DEBUG: PostgreSQL function call failed: {response.status_code} - {response.text}")
                            # Fallback to REST API count
                            response = self.session.get(f"{self.base_url}/rest/v1/tools?select=id")
                            if response.status_code == 200:
                                data = response.json()
                                self._result = [(len(data),)]
                            else:
                                self._result = [(0,)]
                    except Exception as e:
                        print(f"DEBUG: Exception calling PostgreSQL function: {e}")
                        # Fallback to REST API count
                        response = self.session.get(f"{self.base_url}/rest/v1/tools?select=id")
                        if response.status_code == 200:
                            data = response.json()
                            self._result = [(len(data),)]
                        else:
                            self._result = [(0,)]
            
            elif ('select count(*) from comments' in sql_lower or 
                  'select count(*) as count from comments' in sql_lower):
                response = self.session.get(f"{self.base_url}/rest/v1/comments?select=id")
                if response.status_code == 200:
                    data = response.json()
                    self._result = [(len(data),)]
                else:
                    self._result = [(0,)]
            
            elif ('select count(*) from users' in sql_lower or 
                  'select count(*) as count from users' in sql_lower):
                response = self.session.get(f"{self.base_url}/rest/v1/users?select=id")
                if response.status_code == 200:
                    data = response.json()
                    self._result = [(len(data),)]
                else:
                    self._result = [(0,)]
            
            elif ('select count(*) from ratings' in sql_lower or 
                  'select count(*) as count from ratings' in sql_lower):
                if 'where review is not null and review !=' in sql_lower:
                    # Count ratings with non-empty reviews
                    response = self.session.get(f"{self.base_url}/rest/v1/ratings?review=not.is.null&review=neq.&select=id")
                else:
                    # Count all ratings
                    response = self.session.get(f"{self.base_url}/rest/v1/ratings?select=id")
                
                if response.status_code == 200:
                    data = response.json()
                    self._result = [(len(data),)]
                else:
                    self._result = [(0,)]
            
            # USER OPERATIONS
            elif 'insert into users' in sql_lower and params:
                user_data = {}
                
                # Handle OAuth user insertion
                if 'provider' in sql_lower:
                    # Format for OAuth users: (username, email, provider, provider_id, avatar_url)
                    user_data = {
                        'username': params[0],
                        'email': params[1],
                        'provider': params[2],
                        'provider_id': params[3],
                        'avatar_url': params[4] if params[4] else None,
                        'password_hash': None  # Explicitly set password_hash to None for OAuth users
                    }
                else:
                    # Format for regular users: (username, email, password_hash)
                    user_data = {
                        'username': params[0],
                        'email': params[1],
                        'password_hash': params[2]
                    }
                
                response = self.session.post(f"{self.base_url}/rest/v1/users", json=user_data)
                if response.status_code in [200, 201]:
                    self._result = response.json()
                    print(f"User created successfully: {user_data.get('username')}")
                    # If Supabase returns the created user with ID, set lastrowid
                    if self._result and isinstance(self._result, list) and len(self._result) > 0 and 'id' in self._result[0]:
                        self.lastrowid = self._result[0]['id']
                    elif self._result and isinstance(self._result, dict) and 'id' in self._result: # sometimes it's a dict
                        self.lastrowid = self._result['id']
                else:
                    print(f"User insert failed: {response.status_code} - {response.text}")
            
            # Update OAuth user information
            elif 'update users set provider =' in sql_lower and params:
                provider = params[0]
                provider_id = params[1]
                avatar_url = params[2]
                user_id = params[3]
                
                update_data = {
                    'provider': provider,
                    'provider_id': provider_id,
                    'avatar_url': avatar_url if avatar_url else None
                }
                
                response = self.session.patch(f"{self.base_url}/rest/v1/users?id=eq.{user_id}", json=update_data)
                if response.status_code in [200, 201]:
                    self._result = response.json()
                else:
                    print(f"User update failed: {response.status_code} - {response.text}")
                    
            # Regular user operations (existing code)
            elif 'select id from users where username' in sql_lower and params:
                username_or_email = params[0]
                
                # Try username first
                response = self.session.get(f"{self.base_url}/rest/v1/users?username=eq.{username_or_email}&select=*")
                if response.status_code == 200 and response.json():
                    self._result = response.json()
                    return self
                
                # Try email (if username search failed or if it's an email) - this part might be redundant if a specific email handler is added
                # For now, let's assume this is primarily for username.
                # A specific email handler is better.
                self._result = []


            elif 'select * from users where email' in sql_lower and params: # ADDED HANDLER
                email_param = params[0]
                print(f"DEBUG: SupabaseConnection handling 'select * from users where email = {email_param}'")
                response = self.session.get(f"{self.base_url}/rest/v1/users?email=eq.{email_param}&select=*")
                if response.status_code == 200 and response.json():
                    self._result = response.json()
                    print(f"DEBUG: SupabaseConnection found user by email: {self._result}")
                else:
                    self._result = []
                    print(f"DEBUG: SupabaseConnection user not found by email or error: {response.status_code} - {response.text}")
            
            elif 'select xp from users where id' in sql_lower and params:
                user_id = params[0]
                response = self.session.get(f"{self.base_url}/rest/v1/users?id=eq.{user_id}&select=xp")
                if response.status_code == 200 and response.json():
                    self._result = [{'xp': response.json()[0]['xp']}]
                else:
                    self._result = []
            
            elif 'update users set xp' in sql_lower and params:
                xp, rank, user_id = params[:3]
                user_data = {'xp': xp, 'rank': rank}
                response = self.session.patch(f"{self.base_url}/rest/v1/users?id=eq.{user_id}", json=user_data)
                self._result = []
            
            elif 'select username, xp, rank from users' in sql_lower and 'order by xp desc limit 3' in sql_lower:
                response = self.session.get(f"{self.base_url}/rest/v1/users?select=username,xp,rank&order=xp.desc&limit=3")
                self._result = response.json() if response.status_code == 200 else []
            
            elif 'select username, xp, rank from users' in sql_lower and 'order by xp desc limit 50' in sql_lower:
                response = self.session.get(f"{self.base_url}/rest/v1/users?select=username,xp,rank&order=xp.desc&limit=50")
                self._result = response.json() if response.status_code == 200 else []
            
            elif 'select username, xp, rank from users where id' in sql_lower and params:
                user_id = params[0]
                response = self.session.get(f"{self.base_url}/rest/v1/users?id=eq.{user_id}&select=username,xp,rank")
                self._result = response.json() if response.status_code == 200 else []            # TOOL OPERATIONS
            elif 'insert into tools' in sql_lower and params:
                # Handle different insert formats
                if len(params) == 9 and 'is_featured' in sql_lower and 'featured_since' not in sql_lower:
                    # Format: name, description, link, logo_url, category, pricing_model, key_features, gallery_images, is_featured
                    name, description, link, logo_url, category, pricing_model, key_features, gallery_images, is_featured = params
                    tool_data = {
                        'name': name,
                        'description': description,
                        'link': link,
                        'logo_url': logo_url,
                        'category': category,
                        'pricing_model': pricing_model,
                        'key_features': key_features,
                        'gallery_images': gallery_images,
                        'is_featured': is_featured
                    }
                elif len(params) == 9 and 'featured_since' in sql_lower:
                    # Format: name, description, link, logo_url, category, pricing_model, key_features, gallery_images, is_featured (with CURRENT_TIMESTAMP)
                    name, description, link, logo_url, category, pricing_model, key_features, gallery_images, is_featured = params
                    tool_data = {
                        'name': name,
                        'description': description,
                        'link': link,
                        'logo_url': logo_url,
                        'category': category,
                        'pricing_model': pricing_model,
                        'key_features': key_features,
                        'gallery_images': gallery_images,
                        'is_featured': is_featured,
                        'featured_since': datetime.now().isoformat() if is_featured else None
                    }
                else:
                    # Default format for backwards compatibility
                    tool_data = {
                        'name': params[0],
                        'description': params[1],
                        'link': params[2],
                        'logo_url': params[3] if len(params) > 3 else None,
                        'category': params[4] if len(params) > 4 else '',
                        'pricing_model': params[5] if len(params) > 5 else '',
                        'key_features': params[6] if len(params) > 6 else '[]',
                        'gallery_images': params[7] if len(params) > 7 else '[]'
                    }
                
                response = self.session.post(f"{self.base_url}/rest/v1/tools", json=tool_data)
                if response.status_code in [200, 201]:
                    self._result = response.json()
                else:
                    print(f"Tool insert failed: {response.status_code} - {response.text}")
            
            elif ('select *, coalesce(average_rating, 0)' in sql_lower and 
                  'from tools' in sql_lower and 'where is_featured' in sql_lower and 'limit 6' in sql_lower):
                # Homepage featured tools query
                response = self.session.get(f"{self.base_url}/rest/v1/tools?is_featured=eq.true&select=*&order=featured_since.desc.nullslast,average_rating.desc.nullslast&limit=6")
                if response.status_code == 200:
                    data = response.json()
                    for tool in data:
                        tool['average_rating'] = tool.get('average_rating') or 0
                        tool['total_ratings'] = tool.get('total_ratings') or 0
                    self._result = data
                else:
                    self._result = []
            
            elif ('select *, coalesce(average_rating, 0)' in sql_lower and 
                  'from tools' in sql_lower and 'where is_featured' in sql_lower and 'limit 8' in sql_lower):
                # Tools page featured tools query
                response = self.session.get(f"{self.base_url}/rest/v1/tools?is_featured=eq.true&select=*&order=featured_since.desc.nullslast,average_rating.desc.nullslast&limit=8")
                if response.status_code == 200:
                    data = response.json()
                    for tool in data:
                        tool['average_rating'] = tool.get('average_rating') or 0
                        tool['total_ratings'] = tool.get('total_ratings') or 0
                    self._result = data
                else:
                    self._result = []
            
            elif ('select *, coalesce(average_rating, 0)' in sql_lower and 
                  'from tools' in sql_lower and 'where is_featured !=' in sql_lower and 'limit 12' in sql_lower):
                # Homepage regular tools query (excluding featured)
                response = self.session.get(f"{self.base_url}/rest/v1/tools?or=(is_featured.eq.false,is_featured.is.null)&select=*&order=average_rating.desc.nullslast,total_ratings.desc.nullslast&limit=12")
                if response.status_code == 200:
                    data = response.json()
                    for tool in data:
                        tool['average_rating'] = tool.get('average_rating') or 0
                        tool['total_ratings'] = tool.get('total_ratings') or 0
                    self._result = data
                else:
                    self._result = []
            
            elif ('select *, coalesce(average_rating, 0)' in sql_lower and 
                  'from tools' in sql_lower and 'limit 12' in sql_lower):
                # Generic homepage tools query
                response = self.session.get(f"{self.base_url}/rest/v1/tools?select=*&order=average_rating.desc.nullslast,total_ratings.desc.nullslast&limit=12")
                if response.status_code == 200:
                    data = response.json()
                    for tool in data:
                        tool['average_rating'] = tool.get('average_rating') or 0
                        tool['total_ratings'] = tool.get('total_ratings') or 0
                    self._result = data
                else:
                    self._result = []            
            elif ('select *, coalesce(average_rating, 0)' in sql_lower and 
                  'from tools where 1=1' in sql_lower):
                # Tools page query with search/filter
                url = f"{self.base_url}/rest/v1/tools?select=*"
                filters = []
                limit = None
                offset = None
                
                if params:
                    param_idx = 0
                    if 'name like' in sql_lower or 'description like' in sql_lower:
                        search_term = params[param_idx].replace('%', '')
                        filters.append(f"or=(name.ilike.%{search_term}%,description.ilike.%{search_term}%)")
                        param_idx += 2  # Skip both search params
                    
                    if param_idx < len(params) and 'category =' in sql_lower:
                        category = params[param_idx]
                        filters.append(f"category=eq.{category}")
                        param_idx += 1
                    
                    if param_idx < len(params) and 'country_of_origin =' in sql_lower:
                        country = params[param_idx]
                        filters.append(f"country_of_origin=eq.{country}")
                        param_idx += 1
                    
                    if param_idx < len(params) and 'pricing_model =' in sql_lower:
                        price_model = params[param_idx]
                        filters.append(f"pricing_model=eq.{price_model}")
                        param_idx += 1
                    
                    # Handle LIMIT and OFFSET for pagination - they should be the last two parameters
                    if 'limit ? offset ?' in sql_lower and len(params) >= 2:
                        limit = params[-2]  # Second to last parameter
                        offset = params[-1]  # Last parameter
                
                if filters:
                    url += "&" + "&".join(filters)
                
                # Add pagination parameters
                if limit is not None and offset is not None:
                    url += f"&limit={limit}&offset={offset}"
                
                # Handle different sorting options
                if 'order by created_at desc' in sql_lower:
                    url += "&order=created_at.desc.nullslast"
                elif 'order by name asc' in sql_lower:
                    url += "&order=name.asc.nullslast"
                elif 'order by total_ratings desc' in sql_lower:
                    url += "&order=total_ratings.desc.nullslast,average_rating.desc.nullslast"
                else:  # Default rating sort
                    url += "&order=average_rating.desc.nullslast,total_ratings.desc.nullslast"
                
                print(f"DEBUG: Supabase URL for tools query: {url}")
                response = self.session.get(url)
                if response.status_code == 200:
                    data = response.json()
                    print(f"DEBUG: Retrieved {len(data)} tools from Supabase")
                    for tool in data:
                        tool['average_rating'] = tool.get('average_rating') or 0
                        tool['total_ratings'] = tool.get('total_ratings') or 0
                    self._result = data
                else:
                    print(f"DEBUG: Supabase tools query failed: {response.status_code} - {response.text}")
                    self._result = []
            
            elif 'select distinct category from tools' in sql_lower:
                response = self.session.get(f"{self.base_url}/rest/v1/tools?select=category")
                if response.status_code == 200:
                    categories = set()
                    for tool in response.json():
                        if tool.get('category'):
                            categories.add(tool['category'])
                    self._result = [{'category': cat} for cat in sorted(categories)]
                else:
                    self._result = []
            
            elif 'select distinct country_of_origin from tools where country_of_origin is not null' in sql_lower:
                response = self.session.get(f"{self.base_url}/rest/v1/tools?select=country_of_origin&country_of_origin=not.is.null&country_of_origin=neq.Unknown")
                if response.status_code == 200:
                    countries = set()
                    for tool in response.json():
                        if tool.get('country_of_origin') and tool.get('country_of_origin') != 'Unknown':
                            countries.add(tool['country_of_origin'])
                    self._result = [{'country_of_origin': country} for country in sorted(countries)]
                else:
                    print(f"Country query failed: {response.status_code} - {response.text}")
                    self._result = []
                    
            elif 'select distinct pricing_model from tools where pricing_model is not null' in sql_lower:
                response = self.session.get(f"{self.base_url}/rest/v1/tools?select=pricing_model&pricing_model=not.is.null")
                if response.status_code == 200:
                    pricing_models = set()
                    for tool in response.json():
                        if tool.get('pricing_model'):
                            pricing_models.add(tool['pricing_model'])
                    self._result = [{'pricing_model': model} for model in sorted(pricing_models)]
                else:
                    print(f"Pricing model query failed: {response.status_code} - {response.text}")
                    self._result = []
            
            elif ('select *, coalesce(average_rating, 0)' in sql_lower and
                  'from tools where name =' in sql_lower and params): # ADDED for fetching by name
                # Tool detail query by name
                tool_name = params[0]
                response = self.session.get(f"{self.base_url}/rest/v1/tools?name=eq.{tool_name}&select=*") # Query by name
                if response.status_code == 200 and response.json():
                    tool_data = response.json()[0]
                    tool_data['average_rating'] = tool_data.get('average_rating') or 0
                    tool_data['total_ratings'] = tool_data.get('total_ratings') or 0
                    self._result = [tool_data]
                else:
                    self._result = []
            
            elif ('select *, coalesce(average_rating, 0)' in sql_lower and 
                  'from tools where id =' in sql_lower and params):
                # Tool detail query
                tool_id = params[0]
                response = self.session.get(f"{self.base_url}/rest/v1/tools?id=eq.{tool_id}")
                if response.status_code == 200 and response.json():
                    tool = response.json()[0]
                    tool['average_rating'] = tool.get('average_rating') or 0
                    tool['total_ratings'] = tool.get('total_ratings') or 0
                    self._result = [tool]
                else:
                    self._result = []
            
            elif ('select *, coalesce(average_rating, 0)' in sql_lower and 
                  'where category =' in sql_lower and 'and id !=' in sql_lower and params):
                # Related tools query
                category, tool_id = params[:2]
                response = self.session.get(f"{self.base_url}/rest/v1/tools?category=eq.{category}&id=neq.{tool_id}&order=average_rating.desc.nullslast&limit=4")
                if response.status_code == 200:
                    data = response.json()
                    for tool in data:
                        tool['average_rating'] = tool.get('average_rating') or 0
                        tool['total_ratings'] = tool.get('total_ratings') or 0
                    self._result = data
                else:
                    self._result = []
            
            elif 'update tools set' in sql_lower and 'where id =' in sql_lower and params:
                if 'visits = coalesce(visits, 0) + 1' in sql_lower:
                    # Handle visits increment
                    tool_id = params[0]
                    # First get current visits count
                    response = self.session.get(f"{self.base_url}/rest/v1/tools?id=eq.{tool_id}&select=visits")
                    if response.status_code == 200:
                        data = response.json()
                        current_visits = data[0].get('visits', 0) if data else 0
                        new_visits = current_visits + 1
                        
                        # Update with new visits count
                        tool_data = {'visits': new_visits}
                        response = self.session.patch(f"{self.base_url}/rest/v1/tools?id=eq.{tool_id}", json=tool_data)
                        if response.status_code in [200, 204]:
                            self._result = []
                        else:
                            print(f"ERROR updating visits: {response.status_code} - {response.text}")
                            self._result = []
                    else:
                        print(f"ERROR getting current visits: {response.status_code} - {response.text}")
                        self._result = []
                elif 'average_rating' in sql_lower:
                    # Update tool ratings
                    avg_rating, total_ratings, tool_id = params[:3]
                    tool_data = {'average_rating': avg_rating, 'total_ratings': total_ratings}
                    response = self.session.patch(f"{self.base_url}/rest/v1/tools?id=eq.{tool_id}", json=tool_data)                
                else:
                    # Update tool info - handle different parameter counts
                    if len(params) == 11:  # New format with is_featured and featured_since (newly featured)
                        name, description, link, logo_url, category, pricing_model, key_features, gallery_images, is_featured, featured_since, tool_id = params
                        tool_data = {
                            'name': name,
                            'description': description,
                            'link': link,
                            'logo_url': logo_url,
                            'category': category,
                            'pricing_model': pricing_model,
                            'key_features': key_features,
                            'gallery_images': gallery_images,
                            'is_featured': is_featured,
                            'featured_since': featured_since if featured_since != 'CURRENT_TIMESTAMP' else datetime.now().isoformat()
                        }
                    elif len(params) == 10 and ('is_featured' in sql_lower):  # New format with is_featured
                        name, description, link, logo_url, category, pricing_model, key_features, gallery_images, is_featured, tool_id = params
                        tool_data = {
                            'name': name,
                            'description': description,
                            'link': link,
                            'logo_url': logo_url,
                            'category': category,
                            'pricing_model': pricing_model,
                            'key_features': key_features,
                            'gallery_images': gallery_images,
                            'is_featured': is_featured
                        }
                        # If featured_since = NULL is in the query, handle it
                        if 'featured_since = null' in sql_lower.replace(' ', ''):
                            tool_data['featured_since'] = None
                    elif len(params) >= 9:  # New format with key_features and gallery_images
                        name, description, link, logo_url, category, pricing_model, key_features, gallery_images, tool_id = params
                        tool_data = {
                            'name': name,
                            'description': description,
                            'link': link,
                            'logo_url': logo_url,
                            'category': category,
                            'pricing_model': pricing_model,
                            'key_features': key_features,
                            'gallery_images': gallery_images
                        }
                    else:  # Legacy format
                        name, description, link, logo_url, category, pricing_model, tool_id = params
                        tool_data = {
                            'name': name,
                            'description': description,
                            'link': link,
                            'logo_url': logo_url,
                            'category': category,
                            'pricing_model': pricing_model
                        }
                    response = self.session.patch(f"{self.base_url}/rest/v1/tools?id=eq.{tool_id}", json=tool_data)
                self._result = []
            
            # RATINGS OPERATIONS
            elif 'select id from ratings where user_id' in sql_lower and params:
                user_id, tool_id = params[:2]
                response = self.session.get(f"{self.base_url}/rest/v1/ratings?user_id=eq.{user_id}&tool_id=eq.{tool_id}&select=id")
                self._result = response.json() if response.status_code == 200 else []
            
            elif 'insert into ratings' in sql_lower and params:
                user_id, tool_id, rating, review = params[:4]
                rating_data = {
                    'user_id': user_id,
                    'tool_id': tool_id,
                    'rating': rating,
                    'review': review
                }
                response = self.session.post(f"{self.base_url}/rest/v1/ratings", json=rating_data)
                if response.status_code in [200, 201]:
                    self._result = response.json()
                    if self._result:
                        self.lastrowid = self._result[0].get('id')
                else:
                    self._result = []
            
            elif 'update ratings set' in sql_lower and params:
                rating, review, user_id, tool_id = params[:4]
                rating_data = {'rating': rating, 'review': review}
                response = self.session.patch(f"{self.base_url}/rest/v1/ratings?user_id=eq.{user_id}&tool_id=eq.{tool_id}", json=rating_data)
                self._result = []
            
            elif 'select avg(rating)' in sql_lower and 'from ratings where tool_id' in sql_lower and params:
                tool_id = params[0]
                response = self.session.get(f"{self.base_url}/rest/v1/ratings?tool_id=eq.{tool_id}&select=rating")
                if response.status_code == 200:
                    ratings = response.json()
                    if ratings:
                        avg_rating = sum(r['rating'] for r in ratings) / len(ratings)
                        self._result = [{'avg': avg_rating, 'count': len(ratings)}]
                    else:
                        self._result = [{'avg': 0, 'count': 0}]
                else:
                    self._result = [{'avg': 0, 'count': 0}]
            
            elif ('select r.*, u.username, u.rank from ratings r' in sql_lower and 
                  'join users u on r.user_id = u.id' in sql_lower and params):
                # Ratings with user info
                tool_id = params[0]
                response = self.session.get(f"{self.base_url}/rest/v1/ratings?tool_id=eq.{tool_id}&select=*,users(username,rank)&order=created_at.desc")
                if response.status_code == 200:
                    ratings = response.json()
                    # Flatten user data
                    for rating in ratings:
                        if rating.get('users'):
                            rating['username'] = rating['users']['username']
                            rating['rank'] = rating['users']['rank']
                    self._result = ratings
                else:
                    self._result = []
            
            elif 'select * from ratings where user_id' in sql_lower and 'and tool_id' in sql_lower and params:
                user_id, tool_id = params[:2]
                response = self.session.get(f"{self.base_url}/rest/v1/ratings?user_id=eq.{user_id}&tool_id=eq.{tool_id}")
                self._result = response.json() if response.status_code == 200 else []
            
            # SIMPLE SELECT QUERIES
            elif 'select * from tools where id =' in sql_lower and params:
                # Simple tool lookup by ID
                tool_id = params[0]
                response = self.session.get(f"{self.base_url}/rest/v1/tools?id=eq.{tool_id}")
                self._result = response.json() if response.status_code == 200 else []
            
            elif 'select * from users where id =' in sql_lower and params:
                # Simple user lookup by ID
                user_id = params[0]
                response = self.session.get(f"{self.base_url}/rest/v1/users?id=eq.{user_id}")
                self._result = response.json() if response.status_code == 200 else []
            
            elif 'select * from ratings where id =' in sql_lower and params:
                # Simple rating lookup by ID
                rating_id = params[0]
                response = self.session.get(f"{self.base_url}/rest/v1/ratings?id=eq.{rating_id}")
                self._result = response.json() if response.status_code == 200 else []            # COMMENTS
            elif 'insert into comments' in sql_lower and params:
                user_id, tool_id, comment, parent_id = params[:4]
                comment_data = {
                    'user_id': user_id,
                    'tool_id': tool_id,
                    'comment': comment,
                    'parent_id': parent_id if parent_id is not None else None
                }
                response = self.session.post(f"{self.base_url}/rest/v1/comments", json=comment_data)
                if response.status_code in [200, 201]:
                    result = response.json()
                    if result and len(result) > 0:
                        self._result = result
                        self.lastrowid = result[0].get('id')
                        print(f"Comment inserted successfully with ID: {self.lastrowid}")
                    else:
                        self._result = []
                        self.lastrowid = None
                        print("Comment insert returned empty result")
                else:
                    print(f"Comment insert failed: {response.status_code} - {response.text}")
                    self._result = []
                    self.lastrowid = None
            
            elif ('select c.*, u.username, u.rank' in sql_lower and
                  'from comments c' in sql_lower and 'join users u' in sql_lower and
                  'where c.tool_id' in sql_lower and 'and c.parent_id is null' in sql_lower and params):
                # Main comments (not replies)
                user_id_for_reactions, tool_id = params[:2]
                response = self.session.get(f"{self.base_url}/rest/v1/comments?tool_id=eq.{tool_id}&parent_id=is.null&select=*,users(username,rank)&order=created_at.asc")
                if response.status_code == 200:
                    comments = response.json()
                    for comment in comments:
                        if comment.get('users'):
                            comment['username'] = comment['users']['username']
                            comment['rank'] = comment['users']['rank']
                          # Get user's reaction for this comment                        if user_id_for_reactions and user_id_for_reactions != -1:
                            reaction_response = self.session.get(f"{self.base_url}/rest/v1/comment_reactions?user_id=eq.{user_id_for_reactions}&comment_id=eq.{comment['id']}&select=reaction_type")
                            if reaction_response.status_code == 200:
                                reactions = reaction_response.json()
                                comment['user_reaction'] = reactions[0]['reaction_type'] if reactions else ''
                            else:
                                comment['user_reaction'] = ''
                        else:
                            comment['user_reaction'] = ''
                    self._result = comments
                else:
                    self._result = []
            
            elif ('select c.*, u.username, u.rank' in sql_lower and 
                  'where c.parent_id =' in sql_lower and params):
                # Replies to comments
                user_id_for_reactions, parent_id = params[:2]
                response = self.session.get(f"{self.base_url}/rest/v1/comments?parent_id=eq.{parent_id}&select=*,users(username,rank)&order=created_at.asc")
                if response.status_code == 200:
                    replies = response.json()
                    for reply in replies:
                        if reply.get('users'):
                            reply['username'] = reply['users']['username']
                            reply['rank'] = reply['users']['rank']
                          # Get user's reaction for this reply                        if user_id_for_reactions and user_id_for_reactions != -1:
                            reaction_response = self.session.get(f"{self.base_url}/rest/v1/comment_reactions?user_id=eq.{user_id_for_reactions}&comment_id=eq.{reply['id']}&select=reaction_type")
                            if reaction_response.status_code == 200:
                                reactions = reaction_response.json()
                                reply['user_reaction'] = reactions[0]['reaction_type'] if reactions else ''
                            else:
                                reply['user_reaction'] = ''
                        else:
                            reply['user_reaction'] = ''
                    self._result = replies
                else:
                    self._result = []
            
            elif ('select c.*, u.username, u.rank' in sql_lower and 
                  'from comments c' in sql_lower and 
                  'join users u on c.user_id = u.id' in sql_lower and 
                  'where c.id =' in sql_lower and params):
                # Get single comment with user info (broader pattern match)
                comment_id = params[0]
                response = self.session.get(f"{self.base_url}/rest/v1/comments?id=eq.{comment_id}&select=*,users(username,rank)")
                if response.status_code == 200:
                    comments = response.json()
                    if comments and len(comments) > 0:
                        comment = comments[0]
                        # Flatten user data
                        if comment.get('users'):
                            comment['username'] = comment['users']['username']
                            comment['rank'] = comment['users']['rank']
                        self._result = [comment]
                    else:
                        print(f"No comment found with ID: {comment_id}")
                        self._result = []
                else:
                    print(f"Comment fetch failed: {response.status_code} - {response.text}")
                    self._result = []
            
            elif 'select c.*, u.username, u.rank from comments c' in sql_lower and 'where c.id =' in sql_lower and params:
                # Get single comment with user info (legacy pattern)
                comment_id = params[0]
                response = self.session.get(f"{self.base_url}/rest/v1/comments?id=eq.{comment_id}&select=*,users(username,rank)")
                if response.status_code == 200:
                    comments = response.json()
                    if comments and len(comments) > 0:
                        comment = comments[0]
                        # Flatten user data
                        if comment.get('users'):
                            comment['username'] = comment['users']['username']
                            comment['rank'] = comment['users']['rank']
                        self._result = [comment]
                    else:
                        print(f"No comment found with ID: {comment_id}")
                        self._result = []
                else:
                    print(f"Comment fetch failed: {response.status_code} - {response.text}")
                    self._result = []
            
            elif 'select user_id from comments where id' in sql_lower and params:
                # Get comment owner (for edit/delete authorization)
                comment_id = params[0]
                response = self.session.get(f"{self.base_url}/rest/v1/comments?id=eq.{comment_id}&select=user_id")
                if response.status_code == 200:
                    comments = response.json()
                    if comments and len(comments) > 0:
                        self._result = [{'user_id': comments[0]['user_id']}]
                    else:
                        print(f"No comment found with ID: {comment_id}")
                        self._result = []
                else:
                    print(f"Comment owner fetch failed: {response.status_code} - {response.text}")
                    self._result = []
            
            # CONTACT MESSAGES (actual contact form)
            elif 'insert into contact_messages' in sql_lower and len(params) == 3:
                name, email, message = params[:3]
                contact_data = {
                    'name': name,
                    'email': email,
                    'message': message
                }
                response = self.session.post(f"{self.base_url}/rest/v1/contact_messages", json=contact_data)
                self._result = []            
            elif 'select id from comments where parent_id =' in sql_lower and params:
                # Get reply IDs for a parent comment
                parent_id = params[0]
                response = self.session.get(f"{self.base_url}/rest/v1/comments?parent_id=eq.{parent_id}&select=id")
                if response.status_code == 200:
                    replies = response.json()
                    self._result = [{'id': reply['id']} for reply in replies]
                else:
                    print(f"Failed to get replies: {response.status_code} - {response.text}")
                    self._result = []
            
            elif 'delete from comments where parent_id =' in sql_lower and params:
                # Delete all replies of a comment
                parent_id = params[0]
                print(f"Deleting replies for parent comment {parent_id}")
                response = self.session.delete(f"{self.base_url}/rest/v1/comments?parent_id=eq.{parent_id}")
                print(f"Delete replies response: {response.status_code} - {response.text}")
                self._result = []
            
            # COMMENT DELETION            
            elif 'delete from comments where id =' in sql_lower and 'or parent_id =' in sql_lower and params:
                # Delete comment and its replies
                comment_id = params[0]  # Both params should be the same comment_id
                # Delete replies first
                response = self.session.delete(f"{self.base_url}/rest/v1/comments?parent_id=eq.{comment_id}")
                # Delete the main comment
                response = self.session.delete(f"{self.base_url}/rest/v1/comments?id=eq.{comment_id}")
                self._result = []
            elif 'delete from comments where id =' in sql_lower and params and 'or parent_id' not in sql_lower:
                # Delete single comment (CASCADE will handle replies and reactions)
                comment_id = params[0]
                print(f"Attempting to delete comment {comment_id}")
                response = self.session.delete(f"{self.base_url}/rest/v1/comments?id=eq.{comment_id}")
                print(f"Delete comment response: {response.status_code} - {response.text}")
                if response.status_code not in [200, 204]:
                    print(f"Delete failed with status {response.status_code}: {response.text}")
                self._result = []
            
            elif 'delete from comment_reactions where comment_id =' in sql_lower and params:
                # Delete comment reactions
                comment_id = params[0]
                response = self.session.delete(f"{self.base_url}/rest/v1/comment_reactions?comment_id=eq.{comment_id}")
                self._result = []
            
            elif 'update comments set comment =' in sql_lower and params:
                # Update comment content
                new_comment, comment_id = params[:2]
                comment_data = {
                    'comment': new_comment,
                    'is_edited': True
                }
                response = self.session.patch(f"{self.base_url}/rest/v1/comments?id=eq.{comment_id}", json=comment_data)
                if response.status_code in [200, 204]:
                    print(f"Comment {comment_id} updated successfully")
                else:
                    print(f"Comment update failed: {response.status_code} - {response.text}")
                self._result = []            
            # COMMENT REACTIONS (detailed implementation)
            elif 'select reaction_type from comment_reactions' in sql_lower and 'where user_id =' in sql_lower and 'and comment_id =' in sql_lower and params:
                # Get user's reaction on a comment
                user_id, comment_id = params[:2]
                response = self.session.get(f"{self.base_url}/rest/v1/comment_reactions?user_id=eq.{user_id}&comment_id=eq.{comment_id}&select=reaction_type")
                if response.status_code == 200:
                    reactions = response.json()
                    if reactions:
                        self._result = [{'reaction_type': reactions[0]['reaction_type']}]
                    else:
                        self._result = []
                else:
                    self._result = []
            
            elif 'delete from comment_reactions where user_id =' in sql_lower and 'and comment_id =' in sql_lower and params:
                # Delete user's reaction on a comment
                user_id, comment_id = params[:2]
                response = self.session.delete(f"{self.base_url}/rest/v1/comment_reactions?user_id=eq.{user_id}&comment_id=eq.{comment_id}")
                self._result = []
            
            elif 'update comment_reactions set reaction_type =' in sql_lower and params:
                # Update user's reaction type
                reaction_type, user_id, comment_id = params[:3]
                reaction_data = {'reaction_type': reaction_type}
                response = self.session.patch(f"{self.base_url}/rest/v1/comment_reactions?user_id=eq.{user_id}&comment_id=eq.{comment_id}", json=reaction_data)
                self._result = []
            
            elif 'insert into comment_reactions' in sql_lower and params:
                # Insert new reaction
                user_id, comment_id, reaction_type = params[:3]
                reaction_data = {
                    'user_id': user_id,
                    'comment_id': comment_id,
                    'reaction_type': reaction_type
                }
                response = self.session.post(f"{self.base_url}/rest/v1/comment_reactions", json=reaction_data)
                if response.status_code in [200, 201]:
                    print(f"Reaction inserted successfully: user {user_id}, comment {comment_id}, reaction {reaction_type}")
                elif response.status_code == 409:
                    print(f"Reaction already exists for user {user_id} on comment {comment_id}")
                else:
                    print(f"Reaction insert failed: {response.status_code} - {response.text}")
                self._result = []
            
            elif 'select like_count, love_count, angry_count, laugh_count from comments where id =' in sql_lower and params:
                # Get comment reaction counts
                comment_id = params[0]
                response = self.session.get(f"{self.base_url}/rest/v1/comments?id=eq.{comment_id}&select=like_count,love_count,angry_count,laugh_count")
                if response.status_code == 200:
                    comments = response.json()
                    if comments:
                        comment = comments[0]
                        self._result = [{
                            'like_count': comment.get('like_count', 0), 
                            'love_count': comment.get('love_count', 0),
                            'angry_count': comment.get('angry_count', 0),
                            'laugh_count': comment.get('laugh_count', 0)
                        }]
                    else:
                        self._result = []
                else:
                    self._result = []
            
            elif any(f'update comments set {reaction}_count =' in sql_lower for reaction in ['like', 'love', 'angry', 'laugh']):
                # Update comment reaction counts
                comment_id = None
                
                # Extract comment_id from params (usually last parameter)
                if params:
                    comment_id = params[-1]
                
                if comment_id:
                    # First, get current counts
                    response = self.session.get(f"{self.base_url}/rest/v1/comments?id=eq.{comment_id}&select=like_count,love_count,angry_count,laugh_count")
                    if response.status_code == 200:
                        comments = response.json()
                        if comments:
                            current_counts = comments[0]
                              # Determine which reaction count to update and how
                            update_data = {}
                            
                            if 'like_count = like_count + 1' in sql_lower:
                                update_data['like_count'] = current_counts.get('like_count', 0) + 1
                            elif 'like_count = like_count - 1' in sql_lower:
                                update_data['like_count'] = max(0, current_counts.get('like_count', 0) - 1)
                            elif 'love_count = love_count + 1' in sql_lower:
                                update_data['love_count'] = current_counts.get('love_count', 0) + 1
                            elif 'love_count = love_count - 1' in sql_lower:
                                update_data['love_count'] = max(0, current_counts.get('love_count', 0) - 1)
                            elif 'angry_count = angry_count + 1' in sql_lower:
                                update_data['angry_count'] = current_counts.get('angry_count', 0) + 1
                            elif 'angry_count = angry_count - 1' in sql_lower:
                                update_data['angry_count'] = max(0, current_counts.get('angry_count', 0) - 1)
                            elif 'laugh_count = laugh_count + 1' in sql_lower:
                                update_data['laugh_count'] = current_counts.get('laugh_count', 0) + 1
                            elif 'laugh_count = laugh_count - 1' in sql_lower:
                                update_data['laugh_count'] = max(0, current_counts.get('laugh_count', 0) - 1)
                            
                            if update_data:
                                update_response = self.session.patch(f"{self.base_url}/rest/v1/comments?id=eq.{comment_id}", json=update_data)
                                print(f"Reaction count update response: {update_response.status_code}")
                                if update_response.status_code != 204:
                                    print(f"Failed to update reaction count: {update_response.text}")
                
                self._result = []
            
            # ADMIN DASHBOARD QUERIES
            elif ('select t.*,' in sql_lower and 'coalesce(avg(r.rating), 0) as average_rating' in sql_lower and 
                  'count(r.id) as rating_count' in sql_lower and params):
                # Tools with average ratings for admin dashboard
                per_page, offset = params[:2]
                # Get tools
                tools_response = self.session.get(f"{self.base_url}/rest/v1/tools?select=*&name=neq.DATA_IMPORT_COMPLETED&limit={per_page}&offset={offset}&order=created_at.desc")
                if tools_response.status_code == 200:
                    tools = tools_response.json()
                    # For each tool, get its ratings to calculate average
                    for tool in tools:
                        ratings_response = self.session.get(f"{self.base_url}/rest/v1/ratings?tool_id=eq.{tool['id']}&select=rating")
                        if ratings_response.status_code == 200:
                            ratings = ratings_response.json()
                            if ratings:
                                tool['average_rating'] = sum(r['rating'] for r in ratings) / len(ratings)
                                tool['rating_count'] = len(ratings)
                            else:
                                tool['average_rating'] = 0
                                tool['rating_count'] = 0
                        else:
                            tool['average_rating'] = 0
                            tool['rating_count'] = 0
                    self._result = tools
                else:
                    self._result = []
            
            elif ('select id, username, email, xp, rank, created_at' in sql_lower and 
                  'from users order by created_at desc limit' in sql_lower):                # Users for admin dashboard
                response = self.session.get(f"{self.base_url}/rest/v1/users?select=id,username,email,xp,rank,created_at&order=created_at.desc&limit=50")
                self._result = response.json() if response.status_code == 200 else []
            
            elif ('select r.id, r.rating, r.review, r.created_at' in sql_lower and
                  'u.username, t.name' in sql_lower and 'from ratings r' in sql_lower and
                  'join users u' in sql_lower and 'join tools t' in sql_lower):
                # Recent reviews for admin dashboard
                response = self.session.get(f"{self.base_url}/rest/v1/ratings?review=not.is.null&review=neq.&select=id,rating,review,created_at,tool_id,users(username),tools(id,name)&order=created_at.desc&limit=20")
                if response.status_code == 200:
                    reviews = response.json()
                    # Flatten nested user and tool data
                    for review in reviews:
                        if review.get('users'):
                            review['username'] = review['users']['username']
                        if review.get('tools'):
                            review['tool_name'] = review['tools']['name']
                            review['tool_id'] = review['tools']['id']
                        # Also ensure tool_id is available from the rating record itself
                        if not review.get('tool_id') and review.get('tools'):
                            review['tool_id'] = review['tools']['id']
                    self._result = reviews
                else:
                    self._result = []
            
            # COUNT QUERIES FOR STATS
            elif sql_lower == "select count(*) from tools where name != 'data_import_completed'":
                response = self.session.get(f"{self.base_url}/rest/v1/tools?name=neq.DATA_IMPORT_COMPLETED&select=count")
                if response.status_code == 200:
                    data = response.json()
                    count = len(data) if isinstance(data, list) else data.get('count', 0)
                    self._result = [(count,)]
                else:
                    self._result = [(0,)]
            
            elif sql_lower == 'select count(*) from users':
                response = self.session.get(f"{self.base_url}/rest/v1/users?select=count")
                if response.status_code == 200:
                    data = response.json()
                    count = len(data) if isinstance(data, list) else data.get('count', 0)
                    self._result = [(count,)]
                else:
                    self._result = [(0,)]
            
            elif sql_lower == 'select count(*) from ratings':
                response = self.session.get(f"{self.base_url}/rest/v1/ratings?select=count")
                if response.status_code == 200:
                    data = response.json()
                    count = len(data) if isinstance(data, list) else data.get('count', 0)
                    self._result = [(count,)]
                else:
                    self._result = [(0,)]
            
            elif sql_lower == 'select count(*) from comments':
                response = self.session.get(f"{self.base_url}/rest/v1/comments?select=count")
                if response.status_code == 200:
                    data = response.json()
                    count = len(data) if isinstance(data, list) else data.get('count', 0)
                    self._result = [(count,)]
                else:
                    self._result = [(0,)]
            
            elif sql_lower == 'select count(*) from ratings where review is not null and review != ""':
                response = self.session.get(f"{self.base_url}/rest/v1/ratings?review=not.is.null&review=neq.&select=count")
                if response.status_code == 200:
                    data = response.json()
                    count = len(data) if isinstance(data, list) else data.get('count', 0)
                    self._result = [(count,)]
                else:
                    self._result = [(0,)]
            
            elif sql_lower == 'select avg(rating) from ratings':
                response = self.session.get(f"{self.base_url}/rest/v1/ratings?select=rating")
                if response.status_code == 200:
                    ratings = response.json()
                    if ratings:
                        avg_rating = sum(r['rating'] for r in ratings) / len(ratings)
                        self._result = [(avg_rating,)]
                    else:
                        self._result = [(None,)]
                else:
                    self._result = [(None,)]
            
            # TOOLS QUERIES FOR STACK BUILDER
            elif 'select name, description, category, key_features, average_rating, link from tools' in sql_lower:
                response = self.session.get(f"{self.base_url}/rest/v1/tools?select=name,description,category,key_features,average_rating,link")
                if response.status_code == 200:
                    data = response.json()
                    # Convert to dict format expected by the code
                    formatted_data = []
                    for tool in data:
                        # Ensure all required fields exist
                        formatted_tool = {
                            'name': tool.get('name', ''),
                            'description': tool.get('description', ''),
                            'category': tool.get('category', ''),
                            'key_features': tool.get('key_features', '[]'),
                            'average_rating': tool.get('average_rating', 0),
                            'link': tool.get('link', '')
                        }
                        formatted_data.append(formatted_tool)
                    self._result = formatted_data
                else:
                    print(f"Failed to fetch tools: {response.status_code} - {response.text}")
                    self._result = []
            
            # LOGO QUERY HANDLER
            elif 'select name, logo_url from tools where lower(name) = lower(?)' in sql_lower and params:
                tool_name = params[0]
                # Use ilike for case-insensitive search in PostgreSQL
                response = self.session.get(f"{self.base_url}/rest/v1/tools?name=ilike.{tool_name}&select=name,logo_url")
                if response.status_code == 200:
                    self._result = response.json()
                else:
                    print(f"Failed to fetch logo for tool {tool_name}: {response.status_code} - {response.text}")
                    self._result = []
            
            # LEADERBOARD TOOLS QUERY HANDLER
            elif ('select name, logo_url, category, coalesce(visits, 0) as visits' in sql_lower and 
                  'coalesce(average_rating, 0) as average_rating' in sql_lower and
                  'coalesce(total_ratings, 0) as total_ratings' in sql_lower and
                  'from tools' in sql_lower and
                  'order by coalesce(visits, 0) desc' in sql_lower and
                  'limit 5' in sql_lower):
                # Get top 5 tools ordered by visits
                response = self.session.get(f"{self.base_url}/rest/v1/tools?select=name,logo_url,category,visits,average_rating,total_ratings&order=visits.desc.nullslast&limit=5")
                if response.status_code == 200:
                    data = response.json()
                    # Format the data to match expected structure
                    formatted_data = []
                    for tool in data:
                        formatted_tool = {
                            'name': tool.get('name', ''),
                            'logo_url': tool.get('logo_url', ''),
                            'category': tool.get('category', ''),
                            'visits': tool.get('visits', 0) or 0,  # Handle null visits
                            'average_rating': tool.get('average_rating', 0) or 0,
                            'total_ratings': tool.get('total_ratings', 0) or 0
                        }
                        formatted_data.append(formatted_tool)
                    self._result = formatted_data
                else:
                    print(f"Failed to fetch tools for leaderboard: {response.status_code} - {response.text}")
                    self._result = []
            
            else:
                print(f"Unhandled SQL query: {sql_lower[:100]}...")
                self._result = []
                
        except Exception as e:
            print(f"Execute error: {e}")
            self._result = []
        
        return self    
    def fetchall(self):
        """Return all results"""
        return self._result if self._result else []
    
    def fetchone(self):
        """Return first result"""
        if self._result and len(self._result) > 0:
            return self._result[0]
        return None
    
    def commit(self):
        """Commit transaction (auto-committed in Supabase)"""
        pass    
    def insert(self, table, data):
        """Insert data into a table"""
        try:
            response = self.session.post(f"{self.base_url}/rest/v1/{table}", json=data)
            if response.status_code in [200, 201]:
                return {'success': True, 'data': response.json()}
            else:
                print(f"Insert failed: {response.status_code} - {response.text}")
                return {'success': False, 'error': response.text}
        except Exception as e:
            print(f"Insert error: {e}")
            return {'success': False, 'error': str(e)}
    
    def select(self, table, columns='*', condition=''):
        """Select data from a table"""
        try:
            url = f"{self.base_url}/rest/v1/{table}?select={columns}"
            if condition:
                url += f"&{condition}"
            response = self.session.get(url)
            if response.status_code == 200:
                return {'success': True, 'data': response.json()}
            else:
                print(f"Select failed: {response.status_code} - {response.text}")
                return {'success': False, 'data': []}
        except Exception as e:
            print(f"Select error: {e}")
            return {'success': False, 'data': []}
    
    def update(self, table, data, condition):
        """Update data in a table"""
        try:
            # Clean the condition - remove spaces and parentheses
            if "=" in condition and "eq." not in condition:
                # Convert SQL-style condition to Supabase format
                parts = condition.replace(" ", "").split("=")
                if len(parts) == 2:
                    field = parts[0]
                    value = parts[1]
                    condition = f"{field}=eq.{value}"
            
            url = f"{self.base_url}/rest/v1/{table}?{condition}"
            response = self.session.patch(url, json=data)
            if response.status_code in [200, 204]:
                return {'success': True}
            else:
                print(f"Update failed: {response.status_code} - {response.text}")
                return {'success': False, 'error': response.text}
        except Exception as e:
            print(f"Update error: {e}")
            return {'success': False, 'error': str(e)}

    def close(self):
        """Close connection"""
        pass
    
    def delete_tool(self, tool_id):
        """Delete a tool and related data"""
        try:
            # Delete related ratings first
            response = self.session.delete(f"{self.base_url}/rest/v1/ratings?tool_id=eq.{tool_id}")
            print(f"Delete ratings response: {response.status_code}")
            
            # Delete related comments
            response = self.session.delete(f"{self.base_url}/rest/v1/comments?tool_id=eq.{tool_id}")
            print(f"Delete comments response: {response.status_code}")
            
            # Delete the tool
            response = self.session.delete(f"{self.base_url}/rest/v1/tools?id=eq.{tool_id}")
            print(f"Delete tool response: {response.status_code}")
            
            return response.status_code < 300
        except Exception as e:
            print(f"Delete tool error: {e}")
            return False
    
    def get_tool_by_id(self, tool_id):
        """Get tool by ID"""
        try:
            response = self.session.get(f"{self.base_url}/rest/v1/tools?id=eq.{tool_id}")
            if response.status_code == 200 and response.json():
                self._result = response.json()
                return self
            else:
                self._result = []
                return self        
        except Exception as e:
            print(f"Get tool by ID error: {e}")
            self._result = []
            return self
    
    def delete_user(self, user_id):
        """Delete a user and related data"""
        try:
            # Delete related ratings
            self.session.delete(f"{self.base_url}/rest/v1/ratings?user_id=eq.{user_id}")
            # Delete related comments
            self.session.delete(f"{self.base_url}/rest/v1/comments?user_id=eq.{user_id}")
            # Delete the user
            response = self.session.delete(f"{self.base_url}/rest/v1/users?id=eq.{user_id}")
            return response.status_code < 300
        except Exception as e:
            print(f"Delete user error: {e}")
            return False
    
    def delete_review(self, review_id):
        """Delete a review/rating"""
        try:
            response = self.session.delete(f"{self.base_url}/rest/v1/ratings?id=eq.{review_id}")
            return response.status_code < 300
        except Exception as e:
            print(f"Delete review error: {e}")
            return False

def calculate_rank(xp):
    if xp >= 5000:
        return '👑 AI Supreme Leader'
    elif xp >= 4000:
        return '⭐ AI Leader'
    elif xp >= 3000:
        return '🔮 AI Master'
    elif xp >= 2000:
        return '🧠 AI Pro'
    elif xp >= 1000:
        return '🤖 AI Explorer'
    else:
        return '🧩 AI Rookie'

def update_user_xp(user_id, xp_change, conn=None):
    should_close = False
    if conn is None:
        conn = get_db_connection()
        should_close = True
    
    user = conn.execute('SELECT xp FROM users WHERE id = ?', (user_id,)).fetchone()
    if user:
        new_xp = max(0, user['xp'] + xp_change)
        new_rank = calculate_rank(new_xp)
        conn.execute('UPDATE users SET xp = ?, rank = ? WHERE id = ?', 
                    (new_xp, new_rank, user_id))
        if should_close:
            conn.commit()
    
    if should_close:
        conn.close()

def format_datetime(date_str):
    """Convert datetime string to formatted string"""
    if isinstance(date_str, str):
        try:
            # Parse the datetime string from SQLite
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime('%B %d, %Y')
        except:
            return date_str
    elif hasattr(date_str, 'strftime'):
        return date_str.strftime('%B %d, %Y')
    else:
        return str(date_str)

# ============================================================================
# SESSION MANAGEMENT HELPERS
# ============================================================================

def login_required(f):
    """Decorator to require login for protected routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_logged_in():
            if request.is_json:
                return jsonify({'error': 'Authentication required', 'redirect': url_for('login')}), 401
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to require admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_admin():
            if request.is_json:
                return jsonify({'error': 'Admin privileges required'}), 403
            flash('Admin privileges required.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def is_logged_in():
    """Check if user is logged in"""
    return 'user_id' in session and session['user_id'] is not None

def is_admin():
    """Check if current user is admin"""
    return is_logged_in() and session.get('admin', False)

def get_current_user():
    """Get current user info from session"""
    if not is_logged_in():
        return None
    
    return {
        'id': session.get('user_id'),
        'username': session.get('username'),
        'rank': session.get('rank'),
        'xp': session.get('xp', 0),
        'is_admin': session.get('admin', False)
    }

def login_user(user_data):
    """Helper to log in a user and set session data"""
    session.permanent = True  # Make session permanent (respects PERMANENT_SESSION_LIFETIME)
    session['user_id'] = user_data['id']
    session['username'] = user_data['username']
    session['email'] = user_data.get('email', '')
    session['rank'] = user_data.get('rank', 'Beginner')
    session['xp'] = user_data.get('xp', 0)
    session['admin'] = user_data.get('admin', False)
    session['provider'] = user_data.get('provider', 'local')
    session['avatar_url'] = user_data.get('avatar_url', '')
    session['last_activity'] = datetime.now().isoformat()

def logout_user():
    """Helper to log out user and clear session"""
    session.clear()
    flash('You have been logged out successfully.', 'info')

def update_session_activity():
    """Update last activity timestamp"""
    if is_logged_in():
        session['last_activity'] = datetime.now().isoformat()

def check_session_timeout():
    """Check if session has timed out (optional additional security)"""
    if is_logged_in() and 'last_activity' in session:
        last_activity = datetime.fromisoformat(session['last_activity'])
        if datetime.now() - last_activity > timedelta(hours=24):
            logout_user()
            return False
    return True

def update_user_session_data(user_id):
    """Update session data from database (call after XP changes, etc.)"""
    if not is_logged_in() or session['user_id'] != user_id:
        return
    
    conn = get_db_connection()
    user = conn.execute(
        'SELECT username, xp, rank FROM users WHERE id = ?',
        (user_id,)
    ).fetchone()
    
    if user:
        session['username'] = user['username']
        session['xp'] = user['xp']
        session['rank'] = user['rank']
    
    conn.close()

# Template context processor to make user data available in all templates
@app.context_processor
def inject_user():
    """Make current user data available in all templates"""
    return {
        'current_user': get_current_user(),
        'is_logged_in': is_logged_in(),
        'is_admin': is_admin()
    }

# Before request handler to check session and update activity
@app.before_request
def before_request():
    # Security checks and session management
    check_session_timeout()
    update_session_activity()

# After request handler to add security headers
@app.after_request
def after_request(response):
    # Add security headers to prevent clickjacking and other attacks
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    # Content Security Policy to further prevent clickjacking and XSS
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://unpkg.com https://cdnjs.cloudflare.com https://code.jquery.com; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com https://cdnjs.cloudflare.com; "
        "img-src 'self' data: https: http:; "
        "font-src 'self' https://cdn.jsdelivr.net https://unpkg.com https://cdnjs.cloudflare.com; "
        "connect-src 'self' https:; "
        "frame-ancestors 'none'; "
        "frame-src 'none';"
    )
    
    return response

# Before request handler to check session and update activity  
@app.before_request
def before_request():
    """Run before each request to check session validity"""
    if not check_session_timeout():
        return redirect(url_for('login'))
    update_session_activity()

# Routes
@app.route('/')
def index():
    conn = get_db_connection()
    
    # Get featured tools (premium placement)
    featured_tools = conn.execute('''
        SELECT *, COALESCE(average_rating, 0) as average_rating, COALESCE(total_ratings, 0) as total_ratings FROM tools 
        WHERE is_featured = 1 OR is_featured = TRUE
        ORDER BY featured_since DESC, COALESCE(average_rating, 0) DESC 
        LIMIT 6
    ''').fetchall()
    
    # Get regular tools (excluding featured ones for diversity)
    tools = conn.execute('''
        SELECT *, COALESCE(average_rating, 0) as average_rating, COALESCE(total_ratings, 0) as total_ratings FROM tools 
        WHERE is_featured != 1 AND is_featured != TRUE OR is_featured IS NULL
        ORDER BY COALESCE(average_rating, 0) DESC, COALESCE(total_ratings, 0) DESC 
        LIMIT 12
    ''').fetchall()
    
    # Get top 3 users for mini leaderboard
    top_users = conn.execute('''
        SELECT username, xp, rank FROM users 
        ORDER BY xp DESC LIMIT 3
    ''').fetchall()
    
    conn.close()
    return render_template('index.html', tools=tools, featured_tools=featured_tools, top_users=top_users)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        if len(username) < 3:
            flash('Username must be at least 3 characters long', 'error')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long', 'error')
            return render_template('register.html')
        
        conn = get_db_connection()
        print(f"Registration - Using connection type: {type(conn).__name__}")
        
        # Check if user exists
        existing_user = conn.execute(
            'SELECT id FROM users WHERE username = ? OR email = ?', 
            (username, email)
        ).fetchone()
        
        print(f"Registration - Existing user check result: {existing_user}")
        
        if existing_user:
            flash('Username or email already exists', 'error')
            conn.close()
            return render_template('register.html')
        
        # Create user
        password_hash = generate_password_hash(password)
        print(f"Registration - About to insert user: {username}")
        conn.execute(
            'INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
            (username, email, password_hash)
        )
        conn.commit()
        conn.close()
        
        print(f"Registration - User {username} created successfully")
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Check for Supabase session from callback
    access_token = request.args.get('access_token')
    if access_token:
        # Handle in auth_callback route
        return redirect(url_for('auth_callback', access_token=access_token, 
                               refresh_token=request.args.get('refresh_token')))
    
    # Regular login form handling
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute(
            'SELECT * FROM users WHERE username = ? OR email = ?', 
            (username, username)
        ).fetchone()
        conn.close()
        
        # Only check password if user exists and has a password_hash
        # (OAuth users may not have a password set)
        if user and user.get('password_hash') and check_password_hash(user['password_hash'], password):
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials', 'error')
      # Pass Supabase configuration to the template
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    # flash('You have been logged out', 'info')
    return redirect(url_for('index'))

@app.route('/tools')
def tools():
    page = request.args.get('page', 1, type=int)
    PER_PAGE = 20
    search = request.args.get('search', '')
    category = request.args.get('category', '')
    country = request.args.get('country', '')
    pricing_model = request.args.get('price', '')  # Keep parameter as 'price' for backward compatibility
    sort = request.args.get('sort', 'rating')  # Default sort by rating
    conn = get_db_connection()
    
    # Get featured tools (premium placement)
    featured_tools = conn.execute('''
        SELECT *, COALESCE(average_rating, 0) as average_rating, COALESCE(total_ratings, 0) as total_ratings FROM tools 
        WHERE is_featured = 1 OR is_featured = TRUE
        ORDER BY featured_since DESC, COALESCE(average_rating, 0) DESC 
        LIMIT 8
    ''').fetchall()
    
    # Get regular tools with sorting
    query = 'SELECT *, COALESCE(average_rating, 0) as average_rating, COALESCE(total_ratings, 0) as total_ratings FROM tools WHERE 1=1'
    count_query = 'SELECT COUNT(*) as count FROM tools WHERE 1=1'
    params = []
    
    if search:
        query += ' AND (name LIKE ? OR description LIKE ?)'
        count_query += ' AND (name LIKE ? OR description LIKE ?)'
        params.extend([f'%{search}%', f'%{search}%'])
    
    if category:
        query += ' AND category = ?'
        count_query += ' AND category = ?'
        params.append(category)
    
    if country:
        query += ' AND country_of_origin = ?'
        count_query += ' AND country_of_origin = ?'
        params.append(country)
    
    if pricing_model:
        query += ' AND pricing_model = ?'
        count_query += ' AND pricing_model = ?'
        params.append(pricing_model)

    # Get filtered count for pagination
    count_result = conn.execute(count_query, params).fetchone()
    
    if count_result is None:
        filtered_count = 0
    elif isinstance(count_result, tuple):
        filtered_count = count_result[0]
    else:
        filtered_count = count_result['count']

    total_pages = (filtered_count + PER_PAGE - 1) // PER_PAGE

    # Handle sorting
    if sort == 'newest':
        query += ' ORDER BY created_at DESC'
    elif sort == 'name':
        query += ' ORDER BY name ASC'
    elif sort == 'reviews':
        query += ' ORDER BY total_ratings DESC, COALESCE(average_rating, 0) DESC'
    else:     # Default to rating
        query += ' ORDER BY COALESCE(average_rating, 0) DESC, total_ratings DESC'
    
    query += ' LIMIT ? OFFSET ?'
    params.append(PER_PAGE)
    params.append((page - 1) * PER_PAGE)

    tools = conn.execute(query, params).fetchall()
      # Get total count of all tools (without filters for the main count)
    try:
        count_result = conn.execute('SELECT COUNT(*) as count FROM tools').fetchone()
        print(f"DEBUG: Count query result: {count_result}, type: {type(count_result)}")
        
        # Handle different return types (SQLite returns dict-like Row, Supabase returns tuple)
        if count_result is None:
            print("WARNING: Count query returned None")
            total_tools_count = 0
        elif isinstance(count_result, tuple):
            total_tools_count = count_result[0]  # Supabase returns (count,)
            print(f"DEBUG: Supabase tuple result, count: {total_tools_count}")
        else:
            total_tools_count = count_result['count']  # SQLite returns Row object
            print(f"DEBUG: SQLite row result, count: {total_tools_count}")
    except Exception as e:
        print(f"ERROR: Failed to get tools count: {e}")
        total_tools_count = 0
    
    # Get all categories
    categories = conn.execute('SELECT DISTINCT category FROM tools').fetchall()
    
    # Get all countries (only those that have tools)
    countries = conn.execute("SELECT DISTINCT country_of_origin FROM tools WHERE country_of_origin IS NOT NULL AND country_of_origin != 'Unknown' ORDER BY country_of_origin").fetchall()
    
    # Get all pricing models
    pricing_models = conn.execute("SELECT DISTINCT pricing_model FROM tools WHERE pricing_model IS NOT NULL ORDER BY pricing_model").fetchall()
      # Debug: Print available pricing models
    print("Available pricing models:", [model['pricing_model'] for model in pricing_models] if pricing_models else "None found")
    print(f"DEBUG: Final total_tools_count being passed to template: {total_tools_count}")
    print(f"DEBUG: Final filtered_count being passed to template: {filtered_count}")
    conn.close()
    return render_template('tools.html', tools=tools, featured_tools=featured_tools, categories=categories,
                          countries=countries, pricing_models=pricing_models,
                          current_search=search, current_category=category, current_country=country, 
                          current_price=pricing_model, current_sort=sort,
                          total_tools_count=total_tools_count, filtered_count=filtered_count,
                          page=page, total_pages=total_pages)

@app.route('/tool/<string:tool_name>') # Changed from <int:tool_id>
def tool_detail(tool_name): # Changed from tool_id
    conn = get_db_connection()
    
    # Fetch tool by name instead of ID
    tool = conn.execute('SELECT *, COALESCE(average_rating, 0) as average_rating, COALESCE(total_ratings, 0) FROM tools WHERE name = ?', (tool_name,)).fetchone()
    if not tool:
        flash('Tool not found', 'error')
        return redirect(url_for('tools'))
    
    tool_id = tool['id'] # We still need tool_id for other queries
    
    # Track visit - increment visits count
    conn.execute('UPDATE tools SET visits = COALESCE(visits, 0) + 1 WHERE id = ?', (tool_id,))
    conn.commit()
    
    # Get ratings and reviews
    ratings = conn.execute('''
        SELECT r.*, u.username, u.rank FROM ratings r
        JOIN users u ON r.user_id = u.id
        WHERE r.tool_id = ?
        ORDER BY r.created_at DESC
    ''', (tool_id,)).fetchall()      # Get comments with user reactions and replies structure
    comments_query = '''
        SELECT c.*, u.username, u.rank,


               COALESCE(cr.reaction_type, '') as user_reaction
        FROM comments c
        JOIN users u ON c.user_id = u.id
        LEFT JOIN comment_reactions cr ON c.id = cr.comment_id AND cr.user_id = ?
        WHERE c.tool_id = ? AND c.parent_id IS NULL
        ORDER BY c.created_at ASC    '''
    user_id_for_reactions = session.get('user_id', -1)  # Use -1 if not logged in
    comments = conn.execute(comments_query, (user_id_for_reactions, tool_id)).fetchall()
    # Convert comments to list of dictionaries and get replies
    comments_list = []
    for comment in comments:
        comment_dict = dict(comment)
        replies_query = '''
            SELECT c.*, u.username, u.rank,
                   COALESCE(cr.reaction_type, '') as user_reaction
            FROM comments c
            JOIN users u ON c.user_id = u.id
            LEFT JOIN comment_reactions cr ON c.id = cr.comment_id AND cr.user_id = ?
            WHERE c.parent_id = ?
           
            ORDER BY c.created_at ASC
        '''
        replies = conn.execute(replies_query, (user_id_for_reactions, comment_dict['id'])).fetchall()
        comment_dict['replies'] = [dict(reply) for reply in replies]
        comments_list.append(comment_dict)
    
    # Get user's rating if logged in
    user_rating = None
    if 'user_id' in session:
        user_rating = conn.execute(
            'SELECT * FROM ratings WHERE user_id = ? AND tool_id = ?',
            (session['user_id'], tool_id)        ).fetchone()    # Get related tools
    related_tools = conn.execute('''
        SELECT *, COALESCE(average_rating, 0) as average_rating, COALESCE(total_ratings, 0) as total_ratings FROM tools 
        WHERE category = ? AND id != ? 
        ORDER BY COALESCE(average_rating, 0) DESC 
        LIMIT 4
    ''', (tool['category'], tool_id)).fetchall()
    
    conn.close()
    return render_template('tool_detail.html', tool=tool, ratings=ratings, 
                         comments=comments_list, user_rating=user_rating, 
                         related_tools=related_tools)

@app.route('/rate_tool', methods=['POST'])
@login_required
def rate_tool():
    # Only handle JSON requests now
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON data provided'}),  400
    
    tool_id = data.get('tool_id')
    rating = data.get('rating')
    review = data.get('review', '')
    
    if not tool_id or not rating:
        return jsonify({'error': 'Missing tool_id or rating'}), 400
    
    try:
        rating = int(rating)
        tool_id = int(tool_id)
        if rating < 1 or rating > 5:
            return jsonify({'error': 'Rating must be between 1 and 5'}), 400
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid rating format'}), 400
    
    conn = get_db_connection()
    # Check if user already rated this tool
    existing_rating = conn.execute(
        'SELECT id FROM ratings WHERE user_id = ? AND tool_id = ?',
        (session['user_id'], tool_id)
    ).fetchone()
    
    if existing_rating:
        # Update existing rating
        conn.execute(
            'UPDATE ratings SET rating = ?, review = ? WHERE user_id = ? AND tool_id = ?',
            (rating, review, session['user_id'], tool_id)
        )
    else:
        # Insert new rating
        conn.execute(
            'INSERT INTO ratings (user_id, tool_id, rating, review) VALUES (?, ?, ?, ?)',
            (session['user_id'], tool_id, rating, review)
        )
        # Award XP for new rating
        update_user_xp(session['user_id'], 20, conn)
      # Update tool's average rating with safe handling
    avg_rating = conn.execute(
        'SELECT AVG(rating) as avg, COUNT(*) as count FROM ratings WHERE tool_id = ?',
        (tool_id,)
    ).fetchone()
    
    # Safe handling of average rating calculation
    avg_value = round(avg_rating['avg'], 1) if avg_rating['avg'] is not None else 0.0
    count_value = avg_rating['count'] if avg_rating['count'] is not None else 0
    
    conn.execute(
        'UPDATE tools SET average_rating = ?, total_ratings = ? WHERE id = ?',
        (avg_value, count_value, tool_id)
    )
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/add_comment', methods=['POST'])
@login_required
def add_comment():
    tool_id = request.json.get('tool_id')
    comment = request.json.get('comment')
    parent_id = request.json.get('parent_id')  # For replies
    
    # Handle parent_id - convert empty string or undefined to None
    if parent_id == '' or parent_id == 'null':
        parent_id = None
    
    if not tool_id or not comment:
        return jsonify({'error': 'Invalid comment data'}), 400
    
    print(f"Creating comment: tool_id={tool_id}, parent_id={parent_id}, user_id={session['user_id']}")
    
    conn = get_db_connection()
    
    # Insert comment
    cursor = conn.execute(
        'INSERT INTO comments (user_id, tool_id, comment, parent_id) VALUES (?, ?, ?, ?)',
        (session['user_id'], tool_id, comment, parent_id)
    )
    comment_id = cursor.lastrowid
    
    if comment_id is None:
        conn.close()
        return jsonify({'error': 'Failed to create comment'}), 500
    
    print(f"Comment created with ID: {comment_id}")
    
    # Award XP for commenting
    update_user_xp(session['user_id'], 30, conn)
    
    # Get the newly created comment with user info
    new_comment = conn.execute('''
        SELECT c.*, u.username, u.rank 
        FROM comments c
        JOIN users u ON c.user_id = u.id
        WHERE c.id = ?
    ''', (comment_id,)).fetchone()
    
    if new_comment is None:
        conn.close()
        return jsonify({'error': 'Failed to retrieve created comment'}), 500
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'comment': {
            'id': new_comment['id'],
            'username': new_comment['username'],
            'rank': new_comment['rank'],
            'comment': new_comment['comment'],
            'created_at': new_comment['created_at'],            
            'like_count': new_comment['like_count'],
            'love_count': new_comment['love_count'],
            'angry_count': new_comment['angry_count'],
            'laugh_count': new_comment['laugh_count'],
            'parent_id': new_comment['parent_id']
        }
    })

@app.route('/react_comment', methods=['POST'])
@login_required
def react_comment():
    print("=== REACT COMMENT ROUTE CALLED ===")
    
    comment_id = request.json.get('comment_id')
    reaction_type = request.json.get('reaction_type')  # 'like', 'love', 'angry', 'laugh'
    
    print(f"Reaction request: user_id={session['user_id']}, comment_id={comment_id}, reaction_type={reaction_type}")
    
    if not comment_id or reaction_type not in ['like', 'love', 'angry', 'laugh']:
        print("Invalid reaction data")
        return jsonify({'error': 'Invalid reaction data'}), 400
    
    conn = get_db_connection()
    
    try:
        # Check if user already reacted to this comment
        existing_reaction = conn.execute(
            'SELECT reaction_type FROM comment_reactions WHERE user_id = ? AND comment_id = ?',
            (session['user_id'], comment_id)
        ).fetchone()
        
        print(f"Existing reaction: {existing_reaction}")
        
        if existing_reaction:
            if existing_reaction['reaction_type'] == reaction_type:
                print("Removing existing reaction (same type)")
                # Remove reaction if clicking same button
                conn.execute(
                    'DELETE FROM comment_reactions WHERE user_id = ? AND comment_id = ?',
                    (session['user_id'], comment_id)
                )
                
                # Update comment reaction count
                conn.execute(f'UPDATE comments SET {reaction_type}_count = {reaction_type}_count - 1 WHERE id = ?', (comment_id,))
            else:
                print("Changing reaction type")
                # Change reaction type - first decrease old count, then increase new count
                old_reaction = existing_reaction['reaction_type']
                conn.execute(f'UPDATE comments SET {old_reaction}_count = {old_reaction}_count - 1 WHERE id = ?', (comment_id,))
                conn.execute(f'UPDATE comments SET {reaction_type}_count = {reaction_type}_count + 1 WHERE id = ?', (comment_id,))
                
                # Update the reaction
                conn.execute(
                    'UPDATE comment_reactions SET reaction_type = ? WHERE user_id = ? AND comment_id = ?',
                    (reaction_type, session['user_id'], comment_id)
                )
        else:
            print("Adding new reaction")
            # New reaction
            conn.execute(
                'INSERT INTO comment_reactions (user_id, comment_id, reaction_type) VALUES (?, ?, ?)',
                (session['user_id'], comment_id, reaction_type)
            )
            
            # Update comment reaction count
            conn.execute(f'UPDATE comments SET {reaction_type}_count = {reaction_type}_count + 1 WHERE id = ?', (comment_id,))
        
        # Get updated reaction counts
        comment_reactions = conn.execute(
            'SELECT like_count, love_count, angry_count, laugh_count FROM comments WHERE id = ?',
            (comment_id,)
        ).fetchone()
        
        # Get user's current reaction
        user_current_reaction = conn.execute(
            'SELECT reaction_type FROM comment_reactions WHERE user_id = ? AND comment_id = ?',
            (session['user_id'], comment_id)
        ).fetchone()
        
        result = {
            'success': True,
            'like_count': comment_reactions['like_count'] if comment_reactions else 0,
            'love_count': comment_reactions['love_count'] if comment_reactions else 0,
            'angry_count': comment_reactions['angry_count'] if comment_reactions else 0,
            'laugh_count': comment_reactions['laugh_count'] if comment_reactions else 0,
            'user_reaction': user_current_reaction['reaction_type'] if user_current_reaction else None
        }
        
        print(f"Reaction result: {result}")
        return jsonify(result)
        
    except Exception as e:
        print(f"Reaction error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Failed to process reaction'}), 500

@app.route('/edit_comment', methods=['POST'])
@login_required
def edit_comment():
    comment_id = request.json.get('comment_id')
    new_comment = request.json.get('comment')



    if not comment_id or not new_comment:
        return jsonify({'error': 'Invalid comment data'}), 400
    
    conn = get_db_connection()
    
    try:
        # Check if user owns the comment
        comment_owner = conn.execute(
            'SELECT user_id FROM comments WHERE id = ?',
            (comment_id,)
        ).fetchone()
        
        if not comment_owner or comment_owner['user_id'] != session['user_id']:
            return jsonify({'error': 'You can only edit your own comments'}), 403
        
        # Update comment
        conn.execute(
            'UPDATE comments SET comment = ?, updated_at = CURRENT_TIMESTAMP, is_edited = TRUE WHERE id = ?',
            (new_comment, comment_id)
        )
        
        conn.commit()
        print(f"Comment {comment_id} updated successfully: {new_comment[:50]}...")
        
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Edit comment error: {e}")
        return jsonify({'error': 'Failed to update comment'}), 500
    finally:
        conn.close()

@app.route('/delete_comment', methods=['POST'])
@login_required
def delete_comment():
    comment_id = request.json.get('comment_id')    
    if not comment_id:
        return jsonify({'error': 'Invalid comment ID'}), 400
    
    conn = get_db_connection()
    
    # Check if user owns the comment
    comment_owner = conn.execute(
        'SELECT user_id FROM comments WHERE id = ?',
        (comment_id,)
    ).fetchone()
    
    if not comment_owner or comment_owner['user_id'] != session['user_id']:
        conn.close()
        return jsonify({'error': 'You can only delete your own comments'}), 403
      # Delete comment and handle cascading manually
    # First, get all reply IDs
    replies = conn.execute(
        'SELECT id FROM comments WHERE parent_id = ?',
        (comment_id,)
    ).fetchall()
    
    # Delete reactions for the main comment and all replies
    all_comment_ids = [comment_id] + [reply['id'] for reply in replies]
    for cid in all_comment_ids:
        conn.execute('DELETE FROM comment_reactions WHERE comment_id = ?', (cid,))
    
    # Delete all replies
    if replies:
        conn.execute('DELETE FROM comments WHERE parent_id = ?', (comment_id,))
    
    # Delete the main comment
    conn.execute('DELETE FROM comments WHERE id = ?', (comment_id,))
    conn.close()
    
    return jsonify({'success': True})

@app.route('/track-visit', methods=['POST'])
def track_visit():
    """Track a visit to a tool from various sources"""
    try:
        data = request.get_json()
        tool_name = data.get('tool_name')
        source = data.get('source', 'unknown')  # 'visit_button', 'details_button', 'try_now_button'
        
        if not tool_name:
            return jsonify({'error': 'Tool name required'}), 400
        
        conn = get_db_connection()
        
        # Get tool ID from name
        tool = conn.execute('SELECT id FROM tools WHERE name = ?', (tool_name,)).fetchone()
        if not tool:
            conn.close()
            return jsonify({'error': 'Tool not found'}), 404
        
        tool_id = tool['id']
        
        # Increment visits count
        conn.execute('UPDATE tools SET visits = COALESCE(visits, 0) + 1 WHERE id = ?', (tool_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': f'Visit tracked for {tool_name} from {source}'})
        
    except Exception as e:
        print(f"Error tracking visit: {e}")
        return jsonify({'error': 'Failed to track visit'}), 500

@app.route('/leaderboard')
def leaderboard():
    conn = get_db_connection()
    users = conn.execute('''
        SELECT username, xp, rank FROM users 
        ORDER BY xp DESC LIMIT 50
    ''').fetchall()
    
    # Get top 5 most visited tools
    top_tools = conn.execute('''
        SELECT name, logo_url, category, COALESCE(visits, 0) as visits, 
               COALESCE(average_rating, 0) as average_rating, 
               COALESCE(total_ratings, 0) as total_ratings
        FROM tools 
        ORDER BY COALESCE(visits, 0) DESC 
        LIMIT 5
    ''').fetchall()
    
    # Debug: Print the results
    print("DEBUG: Top tools from leaderboard query:")
    for tool in top_tools:
        print(f"  {tool.get('name', 'Unknown')}: {tool.get('visits', 0)} visits")
    
    # Get current user's data if logged in
    current_user = None
    if 'user_id' in session:
        current_user_data = conn.execute('''
            SELECT username, xp, rank FROM users WHERE id = ?
        ''', (session['user_id'],)).fetchone()
        if current_user_data:
            current_user = dict(current_user_data)
    
    conn.close()
    
    return render_template('leaderboard.html', users=users, current_user=current_user, top_tools=top_tools)

@app.route('/support')
def support():
    return render_template('support.html')

@app.route('/advertise')
def advertise():
    return render_template('advertise.html')

# Admin routes
@app.route('/super-admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Enhanced admin credentials - use environment variables in production
        admin_username = os.environ.get('ADMIN_USERNAME', 'admin')
        admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
        
        if username == admin_username and password == admin_password:
            # Set admin session
            session['admin'] = True
            session['username'] = username
            session['user_id'] = -1  # Special ID for admin
            session['rank'] = 'Super Admin'
            session['xp'] = 999999
            session.permanent = True
            flash('Welcome to Admin Dashboard!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid admin credentials', 'error')
            return render_template('admin/login.html')
    
    return render_template('admin/login.html')

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    
    conn = get_db_connection()
    
    # Get tools with pagination
    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page
    
    # Get tools with average ratings
    tools = conn.execute('''
        SELECT t.*, 
               COALESCE(AVG(r.rating), 0) as average_rating,
               COUNT(r.id) as rating_count
        FROM tools t
        LEFT JOIN ratings r ON t.id = r.tool_id
        WHERE t.name != 'DATA_IMPORT_COMPLETED'
        GROUP BY t.id
        ORDER BY t.created_at DESC 
        LIMIT ? OFFSET ?
    ''', (per_page, offset)).fetchall()
    
    # Get users
    users = conn.execute('''SELECT id, username, email, xp, rank, created_at 
                           FROM users ORDER BY created_at DESC LIMIT 50''').fetchall()
    
    # Get recent ratings/reviews
    reviews = conn.execute('''SELECT r.id, r.rating, r.review, r.created_at,
                                    u.username, t.name as tool_name, t.id as tool_id
                             FROM ratings r
                             JOIN users u ON r.user_id = u.id
                             JOIN tools t ON r.tool_id = t.id
                             WHERE r.review IS NOT NULL AND r.review != ''
                             ORDER BY r.created_at DESC LIMIT 20''').fetchall()
      # Get comprehensive stats with safe handling
    stats = {}
    
    # Safe query execution with fallback values
    stats['total_tools'] = conn.execute("SELECT COUNT(*) FROM tools WHERE name != 'DATA_IMPORT_COMPLETED'").fetchone()[0]
    stats['total_users'] = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    stats['total_ratings'] = conn.execute('SELECT COUNT(*) FROM ratings').fetchone()[0]
    stats['total_comments'] = conn.execute('SELECT COUNT(*) FROM comments').fetchone()[0]
    stats['total_reviews'] = conn.execute('SELECT COUNT(*) FROM ratings WHERE review IS NOT NULL AND review != ""').fetchone()[0]
    
    # Safe average rating calculation
    avg_result = conn.execute('SELECT AVG(rating) FROM ratings').fetchone()
    stats['avg_rating'] = round(avg_result[0], 2) if avg_result and avg_result[0] is not None else 0
    
    conn.close()
    return render_template('admin/dashboard.html', 
                         tools=tools, users=users, reviews=reviews, stats=stats, page=page)

@app.route('/admin/add-tool', methods=['GET', 'POST'])
@admin_required
def admin_add_tool():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        link = request.form['website_url']  # Form field is 'website_url'
        logo_url = request.form.get('image_url', '')  # Form field is 'image_url'
        category = request.form['category']
        pricing_model = request.form['pricing_model']
          # Handle dynamic key features
        features = request.form.getlist('features[]')
        key_features = json.dumps([f.strip() for f in features if f.strip()])
        
        # Handle gallery images
        gallery_images = request.form.getlist('gallery_images[]')
        gallery_images_json = json.dumps([img.strip() for img in gallery_images if img.strip()])
        
        # Handle featured status
        is_featured = 'is_featured' in request.form
        featured_since = 'CURRENT_TIMESTAMP' if is_featured else None
        
        conn = get_db_connection()
        if is_featured and featured_since:
            conn.execute('''
                INSERT INTO tools (name, description, link, logo_url, category, pricing_model, key_features, gallery_images, is_featured, featured_since)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (name, description, link, logo_url, category, pricing_model, key_features, gallery_images_json, is_featured))
        else:
            conn.execute('''
                INSERT INTO tools (name, description, link, logo_url, category, pricing_model, key_features, gallery_images, is_featured)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (name, description, link, logo_url, category, pricing_model, key_features, gallery_images_json, is_featured))
        conn.commit()
        conn.close()
        
        flash('Tool added successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('admin/add_tool.html')

@app.route('/admin/logout')
def admin_logout():
    logout_user()
    return redirect(url_for('index'))

# Admin CRUD operations
@app.route('/admin/delete_tool/<int:tool_id>', methods=['POST'])
@admin_required
def admin_delete_tool(tool_id):
    
    try:
        conn = get_db_connection()
          # Handle Supabase differently
        if isinstance(conn, SupabaseConnection):
            # Check if tool exists
            tool_check = conn.get_tool_by_id(tool_id)
            if not tool_check.fetchone():
                return jsonify({'success': False, 'message': 'Tool not found'}), 404
            
            # Delete using Supabase HTTP method
            success = conn.delete_tool(tool_id)
            if not success:
                return jsonify({'success': False, 'message': 'Failed to delete tool'}), 500
        else:
            # SQLite logic
            tool = conn.execute('SELECT * FROM tools WHERE id = ?', (tool_id,)).fetchone()
            if not tool:
                return jsonify({'success': False, 'message': 'Tool not found'}), 404
            
            # Delete related ratings first
            conn.execute('DELETE FROM ratings WHERE tool_id = ?', (tool_id,))
            # Delete related comments
            conn.execute('DELETE FROM comments WHERE tool_id = ?', (tool_id,))
            # Delete the tool
            conn.execute('DELETE FROM tools WHERE id = ?', (tool_id,))
            conn.commit()
        
        conn.close()
        return jsonify({'success': True, 'message': 'Tool deleted successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/edit_tool/<int:tool_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_tool(tool_id):
    
    conn = get_db_connection()
    
    # Handle Supabase differently for getting tool
    if isinstance(conn, SupabaseConnection):
        tool_result = conn.execute('SELECT * FROM tools WHERE id = ?', (tool_id,))
        tool = tool_result.fetchone()
    else:
        tool = conn.execute('SELECT * FROM tools WHERE id = ?', (tool_id,)).fetchone()    
    if not tool:
        flash('Tool not found', 'error')
        conn.close()
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        link = request.form['website_url']
        logo_url = request.form.get('image_url', '')
        category = request.form['category']
        pricing_model = request.form['pricing_model']
        
        # Handle dynamic key features
        features = request.form.getlist('features[]')
        key_features = json.dumps([f.strip() for f in features if f.strip()])
        
        # Handle gallery images
        gallery_images = request.form.getlist('gallery_images[]')
        gallery_images_json = json.dumps([img.strip() for img in gallery_images if img.strip()])
        
        # Handle featured status
        is_featured = 'is_featured' in request.form
        was_featured = tool.get('is_featured', False)
        
        try:
            if is_featured and not was_featured:
                # Newly featured - set featured_since timestamp
                conn.execute('''
                    UPDATE tools 
                    SET name = ?, description = ?, link = ?, logo_url = ?, 
                        category = ?, pricing_model = ?, key_features = ?, gallery_images = ?,
                        is_featured = ?, featured_since = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (name, description, link, logo_url, category, pricing_model, key_features, gallery_images_json, is_featured, tool_id))
            elif not is_featured and was_featured:
                # No longer featured - remove featured_since
                conn.execute('''
                    UPDATE tools 
                    SET name = ?, description = ?, link = ?, logo_url = ?, 
                        category = ?, pricing_model = ?, key_features = ?, gallery_images = ?,
                        is_featured = ?, featured_since = NULL
                    WHERE id = ?
                ''', (name, description, link, logo_url, category, pricing_model, key_features, gallery_images_json, is_featured, tool_id))
            else:
                # No change in featured status
                conn.execute('''
                    UPDATE tools 
                    SET name = ?, description = ?, link = ?, logo_url = ?, 
                        category = ?, pricing_model = ?, key_features = ?, gallery_images = ?,
                        is_featured = ?
                    WHERE id = ?
                ''', (name, description, link, logo_url, category, pricing_model, key_features, gallery_images_json, is_featured, tool_id))
            conn.commit()
            flash('Tool updated successfully!', 'success')
            conn.close()
            return redirect(url_for('admin_dashboard'))
        except Exception as e:
            flash(f'Error updating tool: {str(e)}', 'error')
            conn.close()
    
    conn.close()
    return render_template('admin/edit_tool.html', tool=tool)

@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@admin_required
def admin_delete_user(user_id):
    
    
    try:
        conn = get_db_connection()
        
        # Handle Supabase differently
        if isinstance(conn, SupabaseConnection):
            # Check if user exists
            user_result = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,))
            user = user_result.fetchone()
            if not user:
                conn.close()
                return jsonify({'success': False, 'message': 'User not found'}), 404
            
            # Delete using Supabase method
            success = conn.delete_user(user_id)
            if not success:
                conn.close()
                return jsonify({'success': False, 'message': 'Failed to delete user'}), 500
        else:
            # SQLite logic
            user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
            if not user:
                conn.close()
                return jsonify({'success': False, 'message': 'User not found'}), 404
            
            # Delete related ratings
            conn.execute('DELETE FROM ratings WHERE user_id = ?', (user_id,))
            # Delete related comments
            conn.execute('DELETE FROM comments WHERE user_id = ?', (user_id,))
            # Delete the user
            conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
            conn.commit()
        
        conn.close()
        return jsonify({'success': True, 'message': 'User deleted successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/delete_review/<int:review_id>', methods=['POST'])
@admin_required
def admin_delete_review(review_id):
    
    try:
        conn = get_db_connection()
        
        # Handle Supabase differently
        if isinstance(conn, SupabaseConnection):
            # Check if review exists
            review_result = conn.execute('SELECT * FROM ratings WHERE id = ?', (review_id,))
            review = review_result.fetchone()
            if not review:
                conn.close()
                return jsonify({'success': False, 'message': 'Review not found'}), 404
            
            # Delete using Supabase method
            success = conn.delete_review(review_id)
            if not success:
                conn.close()
                return jsonify({'success': False, 'message': 'Failed to delete review'}), 500
        else:
            # SQLite logic
            review = conn.execute('SELECT * FROM ratings WHERE id = ?', (review_id,)).fetchone()
            if not review:
                conn.close()
                return jsonify({'success': False, 'message': 'Review not found'}), 404
            
            # Delete the review
            conn.execute('DELETE FROM ratings WHERE id = ?', (review_id,))
            conn.commit()
        
        conn.close()
        return jsonify({'success': True, 'message': 'Review deleted successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/toggle_user/<int:user_id>', methods=['POST'])
@admin_required
def admin_toggle_user(user_id):
    
    try:
        conn = get_db_connection()
        
        # Handle Supabase differently
        if isinstance(conn, SupabaseConnection):
            user_result = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,))
            user = user_result.fetchone()
        else:
            user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        
        if not user:
            conn.close()
            return jsonify({'success': False, 'message': 'User not found'}), 404
        
        conn.close()
        # For now, we'll just return success - you can implement user status toggling later
        # This could involve adding an 'active' field to the users table
        return jsonify({'success': True, 'message': 'User status updated'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Static pages
@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        company = request.form.get('company', '').strip()
        subject = request.form.get('subject', '').strip()
        message = request.form.get('message', '').strip()
        newsletter = request.form.get('newsletter') == '1'
        
        # Basic validation
        if not name or not email or not message or not subject:
            flash('Please fill in all required fields.', 'error')
            return render_template('contact.html')
        
        if len(message) < 10:
            flash('Please provide a message with at least 10 characters.', 'error')
            return render_template('contact.html')
        
        try:
            conn = get_db_connection()
            
            # Check if we need to create the contact_messages table with new structure
            if isinstance(conn, SupabaseConnection):
                # For Supabase, we'll use a more complete insert
                conn.execute('''
                    INSERT INTO contact_messages (name, email, company, subject, message, newsletter_subscription, created_at) 
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                ''', (name, email, company, subject, message, newsletter))
            else:
                # For SQLite, create table if not exists and insert
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS contact_messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        email TEXT NOT NULL,
                        company TEXT,
                        subject TEXT NOT NULL,
                        message TEXT NOT NULL,
                        newsletter_subscription BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                conn.execute('''
                    INSERT INTO contact_messages (name, email, company, subject, message, newsletter_subscription) 
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (name, email, company, subject, message, newsletter))
            
            conn.commit()
            conn.close()
            
            # Success message with personalization
            success_msg = f'Thank you, {name}! Your message has been received. '
            if newsletter:
                success_msg += "You've also been subscribed to our newsletter. "
            success_msg += "I'll get back to you within 24-48 hours."
            
            flash(success_msg, 'success')
            return redirect(url_for('contact'))
            
        except Exception as e:
            print(f"Contact form error: {e}")
            flash('Sorry, there was an error sending your message. Please try again or email me directly.', 'error')
            return render_template('contact.html')
    
    return render_template('contact.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/debug')
def debug_info():
    """Debug endpoint to check database connection"""
    import sys
    debug_info = {
        'python_version': sys.version,
        'environment': 'vercel' if os.environ.get('VERCEL') else 'local',
        'supabase_url_exists': bool(os.environ.get('SUPABASE_URL')),
        'supabase_key_exists': bool(os.environ.get('SUPABASE_ANON_KEY')),
        'supabase_url_value': os.environ.get('SUPABASE_URL', 'NOT_SET')[:50] + '...' if os.environ.get('SUPABASE_URL') else 'NOT_SET',
    }
    
    # Test database connection
    try:
        conn = get_db_connection()
        if isinstance(conn, SupabaseConnection):
            debug_info['database_type'] = 'Supabase'
            debug_info['supabase_connection'] = 'SUCCESS'
        else:
            debug_info['database_type'] = 'SQLite'
            debug_info['sqlite_path'] = get_db_path()
        conn.close()
    except Exception as e:
        debug_info['database_connection_error'] = str(e)
      # Test Supabase import
    try:
        import requests
        debug_info['requests_import'] = 'SUCCESS'
    except ImportError as e:
        debug_info['requests_import_error'] = str(e)
    
    return jsonify(debug_info)

# ============================================================================
# Stack Builder Routes
# ============================================================================

from stack_builder import StackBuilder

@app.route('/stack-builder')
def stack_builder():
    """Stack Builder main page"""
    return render_template('stack_builder.html')

@app.route('/generate-stack', methods=['POST'])
def generate_stack():
    """Generate AI workflow stack based on user prompt"""
    try:
        data = request.get_json()
        prompt = data.get('prompt', '').strip()
        
        if not prompt:
            return jsonify({
                'success': False,
                'error': 'no_prompt',
                'message': 'Please describe what kind of AI workflow you want to build.'
            })
          # Initialize Stack Builder
        stack_builder = StackBuilder()
        
        # Get database connection
        conn = get_db_connection()
        
        # Get user ID if logged in
        user_id = session.get('user_id')
        
        # Get client IP for usage tracking
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if client_ip:
            client_ip = client_ip.split(',')[0].strip()  # Handle multiple IPs
        
        # Generate workflow
        result = stack_builder.build_stack_with_limits(
            user_prompt=prompt,
            db_connection=conn,
            user_id=user_id,
            session=session,
            client_ip=client_ip
        )
        
        # Close connection if it's SQLite
        if hasattr(conn, 'close'):
            conn.close()
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error in generate_stack: {e}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'Something went wrong on our end. Please try again.'
        })

@app.route('/save-stack', methods=['POST'])
def save_stack():
    """Save generated stack for logged-in users"""
    if 'user_id' not in session:
        return jsonify({
            'success': False,
            'error': 'not_logged_in',
            'message': 'Please log in to save your AI stacks.'
        })
    
    try:
        data = request.get_json()
        workflow = data.get('workflow')
        original_prompt = data.get('original_prompt', '')
        
        if not workflow:
            return jsonify({
                'success': False,
                'error': 'no_workflow',
                'message': 'No workflow data to save.'
            })
        
        # Initialize Stack Builder
        stack_builder = StackBuilder()
        
        # Get database connection
        conn = get_db_connection()
          # Save stack
        success = stack_builder.save_stack(
            user_id=session['user_id'],
            prompt=original_prompt,
            workflow=workflow,
            db_connection=conn
        )
        
        # Close connection if it's SQLite
        if hasattr(conn, 'close'):
            conn.close()
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Stack saved successfully!'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'save_failed',
                'message': 'Failed to save stack. Please try again.'
            })
            
    except Exception as e:
        print(f"Error in save_stack: {e}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'Something went wrong while saving. Please try again.'
        })

@app.route('/my-stacks')
def my_stacks():
    """View user's saved stacks"""
    if 'user_id' not in session:
        flash('Please log in to view your saved stacks.', 'error')
        return redirect(url_for('login'))
    
    try:
        # Initialize Stack Builder
        stack_builder = StackBuilder()
        
        # Get database connection
        conn = get_db_connection()
        
        # Get user's stacks
        stacks = stack_builder.get_user_stacks(
            user_id=session['user_id'],
            db_connection=conn
        )
        
        # Close connection if it's SQLite
        if hasattr(conn, 'close'):
            conn.close()
        
        return render_template('my_stacks.html', stacks=stacks)
        
    except Exception as e:
        print(f"Error in my_stacks: {e}")
        flash('Error loading your stacks. Please try again.', 'error')
        return redirect(url_for('index'))

@app.route('/check-usage')
def check_usage():
    """Check usage limits for non-logged-in users"""
    if 'user_id' in session:
        return jsonify({
            'logged_in': True,
            'can_use': True,
            'uses_remaining': 'unlimited'
        })
    
    stack_builder = StackBuilder()
    can_use, uses_remaining = stack_builder.track_free_usage(session)
    
    return jsonify({
        'logged_in': False,
        'can_use': can_use,
        'uses_remaining': uses_remaining
    })

@app.route('/delete-stack/<int:stack_id>', methods=['DELETE'])
def delete_stack(stack_id):
    """Delete a user's saved stack"""
    if 'user_id' not in session:
        return jsonify({
            'success': False,
            'error': 'not_logged_in',
            'message': 'Please log in to delete stacks.'
        })
    
    try:
        # Initialize Stack Builder (we'll add a delete method)
        stack_builder = StackBuilder()
        
        # Get database connection
        conn = get_db_connection()
        
        # Delete stack
        success = stack_builder.delete_user_stack(
            stack_id=stack_id,
            user_id=session['user_id'],
            db_connection=conn
        )
        
        # Close connection if it's SQLite
        if hasattr(conn, 'close'):
            conn.close()
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Stack deleted successfully!'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'delete_failed',
                'message': 'Failed to delete stack or stack not found.'
            })
            
    except Exception as e:
        print(f"Error in delete_stack: {e}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'Something went wrong while deleting. Please try again.'
        })

# ============================================================================

@app.route('/api/usage-status')
def usage_status():
    """Get usage status for current user/session"""
    try:
        user_id = session.get('user_id')
        
        if user_id:
            # Logged in users have unlimited usage
            return jsonify({
                'user_id': user_id,
                'remaining_uses': 'unlimited',
                'is_logged_in': True
            })
        else:
            # Check free usage for non-logged-in users
            from stack_builder import StackBuilder
            stack_builder = StackBuilder()
            
            # Get client IP
            client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
            if client_ip:
                client_ip = client_ip.split(',')[0].strip()
            
            # Get database connection
            conn = get_db_connection()
            
            # Check usage
            can_use, uses_remaining = stack_builder.track_free_usage_by_ip(conn, client_ip)
            
            # Close connection if it's SQLite
            if hasattr(conn, 'close'):
                conn.close()
            
            return jsonify({
                'user_id': None,
                'remaining_uses': uses_remaining,
                'can_use': can_use,
                'is_logged_in': False
            })
            
    except Exception as e:
        print(f"Error checking usage status: {e}")
        return jsonify({
            'user_id': None,
            'remaining_uses': 1,
            'can_use': True,
            'is_logged_in': False        })

# ============================================================================
# SUBMIT TOOL ROUTES
# ============================================================================

from submit_tool import (
    ToolSubmitter, save_tool_submission, get_pending_submissions,
    approve_tool_submission, reject_tool_submission
)

@app.route('/submit-tool')
def submit_tool():
    """Display the submit tool page"""
    return render_template('submit_tool.html')

@app.route('/submit-tool', methods=['POST'])
def submit_tool_post():
    """Handle tool submission"""
    try:
        tool_url = request.form.get('tool_url', '').strip()
        submitter_email = request.form.get('submitter_email', '').strip()
        country_of_origin = request.form.get('country_of_origin', '').strip()
        
        if not tool_url or not submitter_email or not country_of_origin:
            return jsonify({'success': False, 'error': 'Please provide URL, email address, and country of origin'})
        
        # Validate email format
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, submitter_email):
            return jsonify({'success': False, 'error': 'Please provide a valid email address'})
        
        # Initialize tool submitter
        tool_submitter = ToolSubmitter()
        
        # Submit tool with country of origin
        result = tool_submitter.submit_tool(tool_url, submitter_email, country_of_origin)
        
        if result.get('success'):
            # Save to database
            conn = get_db_connection()
            saved = save_tool_submission(result['data'], conn)
            
            # Close connection if it's SQLite
            if hasattr(conn, 'close'):
                conn.close()
            
            if saved:
                return jsonify({
                    'success': True, 
                    'message': 'Tool submitted successfully! We will review it and notify you via email.'
                })
            else:
                return jsonify({'success': False, 'error': 'Failed to save submission to database'})
        else:
            return jsonify({'success': False, 'error': result.get('error', 'Unknown error occurred')})
            
    except Exception as e:
        print(f"Error in submit_tool_post: {e}")
        return jsonify({'success': False, 'error': 'An error occurred while processing your submission'})

@app.route('/admin/tool-submissions')
@admin_required
def admin_tool_submissions():
    """Display pending tool submissions for admin review"""
    try:
        conn = get_db_connection()
        submissions = get_pending_submissions(conn)
        
        # Close connection if it's SQLite
        if hasattr(conn, 'close'):
            conn.close()
        
        return render_template('admin/tool_submissions.html', submissions=submissions)
        
    except Exception as e:
        print(f"Error in admin_tool_submissions: {e}")
        flash('Error loading tool submissions', 'error')
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/approve-submission/<int:submission_id>', methods=['POST'])
@admin_required
def admin_approve_submission(submission_id):
    """Approve a tool submission"""
    try:
        conn = get_db_connection()
        success = approve_tool_submission(submission_id, conn)
        
        # Close connection if it's SQLite
        if hasattr(conn, 'close'):
            conn.close()
        
        if success:
            return jsonify({'success': True, 'message': 'Tool approved and published successfully'})
        else:
            return jsonify({'success': False, 'error': 'Failed to approve submission. The tool may already exist in the database or there was a conflict. Please check if a tool with the same URL already exists.'})
            
    except Exception as e:
        print(f"Error in admin_approve_submission: {e}")
        return jsonify({'success': False, 'error': 'An error occurred while approving the submission. Please check the server logs for details.'})

@app.route('/admin/reject-submission/<int:submission_id>', methods=['POST'])
@admin_required
def admin_reject_submission(submission_id):
    """Reject a tool submission"""
    try:
        conn = get_db_connection()
        success = reject_tool_submission(submission_id, conn)
        
        # Close connection if it's SQLite
        if hasattr(conn, 'close'):
            conn.close()
        
        if success:
            return jsonify({'success': True, 'message': 'Tool submission rejected'})
        else:
            return jsonify({'success': False, 'error': 'Failed to reject submission'})
            
    except Exception as e:
        print(f"Error in admin_reject_submission: {e}")
        return jsonify({'success': False, 'error': 'An error occurred while rejecting the submission'})

@app.route('/admin/edit-submission/<int:submission_id>', methods=['POST'])
@admin_required
def admin_edit_submission(submission_id):
    """Edit a tool submission"""
    try:
        data = request.json
        
        # Prepare update data
        update_data = {
            'name': data.get('name'),
            'description': data.get('description'),
            'link': data.get('link'),
            'logo_url': data.get('logo_url'),
            'category': data.get('category'),
            'pricing_model': data.get('pricing_model'),
            'key_features': data.get('key_features')
        }
        
        # Remove None values
        update_data = {k: v for k, v in update_data.items() if v is not None}
        
        conn = get_db_connection()
          # Update submission
        if hasattr(conn, 'session'):  # Check if it's SupabaseConnection
            result = conn.update('tool_submissions', update_data, f"id=eq.{submission_id}")
            success = result.get('success', False)
        else:
            cursor = conn.cursor()
            set_clause = ', '.join([f"{k} = ?" for k in update_data.keys()])
            values = list(update_data.values())
            values.append(submission_id)
            
            cursor.execute(f"UPDATE tool_submissions SET {set_clause} WHERE id = ?", values)
            conn.commit()
            success = True
        
        # Close connection if it's SQLite
        if hasattr(conn, 'close'):
            conn.close()
        
        if success:
            return jsonify({'success': True, 'message': 'Tool submission updated successfully'})
        else:
            return jsonify({'success': False, 'error': 'Failed to update submission'})
            
    except Exception as e:
        print(f"Error in admin_edit_submission: {e}")
        return jsonify({'success': False, 'error': 'An error occurred while updating the submission'})

# ============================================================================

# Google OAuth Routes
@app.route('/auth/callback')
def auth_callback():
    print("Auth Callback - Route Hit")
    access_token = request.args.get('access_token')
    refresh_token = request.args.get('refresh_token')
    
    print(f"Auth Callback - Received tokens: access={bool(access_token)}, refresh={bool(refresh_token)}")
    if request.args:
        # Log only a subset of args if they are too long, especially tokens
        loggable_args = {k: (v[:20] + '...' if isinstance(v, str) and len(v) > 20 else v) for k, v in request.args.items()}
        print(f"Auth Callback - All args (truncated): {loggable_args}")


    if not supabase_client:
        print("Auth Callback - Supabase client not initialized.")
        # flash('Authentication service is currently unavailable. Please try again later.', 'danger') # Flash is for HTML responses
        if request.headers.get('Accept') == 'application/json':
            return jsonify(success=False, error='Authentication service unavailable.'), 500
        flash('Authentication service is currently unavailable. Please try again later.', 'danger')
        return redirect(url_for('login'))

    if not access_token:
        print("Auth Callback - No access token received.")
        if request.headers.get('Accept') == 'application/json':
            return jsonify(success=False, error='No access token received.'), 400
        flash('Authentication failed: No access token received. Please try again.', 'danger')
        return redirect(url_for('login'))

    try:
        print(f"Creating Supabase client with URL: {SUPABASE_URL[:10] if SUPABASE_URL else 'N/A'}...") # Log only part of URL
        # Use the global supabase_client initialized at startup

        print("Setting session with tokens...")
        # Corrected: Use the set_session method of the global client's auth interface
        supabase_client.auth.set_session(access_token, refresh_token)
        print("Session set. Getting user data...")
        
        user_response = supabase_client.auth.get_user()
        print(f"User response received: {bool(user_response)}")

        if not user_response or not user_response.user:
            print("Auth Callback - Failed to get user data from Supabase.")
            if request.headers.get('Accept') == 'application/json':
                return jsonify(success=False, error='Failed to retrieve user data from Supabase.'), 500
            flash('Authentication failed: Could not retrieve user data. Please try again.', 'danger')
            return redirect(url_for('login'))

        user = user_response.user
        print(f"User data extracted: {bool(user)}")
        
        user_email = user.email
        # Prefer 'name' from user_metadata if 'full_name' is not present
        user_name = user.user_metadata.get('full_name') or user.user_metadata.get('name') or user_email.split('@')[0]
        user_avatar_url = user.user_metadata.get('avatar_url')
        # Supabase user ID is user.id. This is the unique ID for the user in Supabase.
        user_provider_id = user.id 
        # If Google provides a specific 'provider_id' in user_metadata, you might prefer that for 'provider_id' column
        # e.g., user_provider_id = user.user_metadata.get('provider_id', user.id)


        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if user exists by email
        print(f"Checking if user exists: {user_email}")
        cursor.execute("SELECT * FROM users WHERE email = ?", (user_email,))
        db_user = cursor.fetchone()

        if db_user:
            print(f"User {user_email} found in DB (ID: {db_user['id']}). Logging in.")
            # User exists, log them in
            session['user_id'] = db_user['id']
            session['username'] = db_user['username']
            # Update avatar and provider info if it has changed or if they logged in via Google
            session['avatar_url'] = user_avatar_url or db_user['avatar_url'] # Prefer new Google avatar
            session['provider'] = 'google' # If they are here, they used Google

            if db_user['provider'] != 'google' or db_user['avatar_url'] != user_avatar_url or db_user['provider_id'] != user_provider_id:
                try:
                    print(f"Updating user {db_user['id']} OAuth info: provider_id={user_provider_id}, avatar_url={bool(user_avatar_url)}")
                    cursor.execute("""
                        UPDATE users SET provider = ?, provider_id = ?, avatar_url = ?
                        WHERE id = ?
                    """, ('google', user_provider_id, user_avatar_url, db_user['id']))
                    conn.commit()
                    print(f"User {db_user['id']} OAuth info updated successfully.")
                except Exception as e_update:
                    print(f"Error updating user's OAuth info for ID {db_user['id']}: {e_update}")
                    # Continue login even if update fails for now

        else:
            print(f"User {user_email} not found. Creating new user.")
            # New user, register them
            try:
                # Ensure username is unique
                base_username = re.sub(r'[^a-zA-Z0-9_]', '', user_name).lower()
                if not base_username: # Handle cases where name might be all special chars
                    base_username = user_email.split('@')[0].lower()
                
                username_to_insert = base_username
                counter = 1
                while True:
                    cursor.execute("SELECT id FROM users WHERE username = ?", (username_to_insert,))
                    if not cursor.fetchone():
                        break
                    username_to_insert = f"{base_username}{counter}"
                    counter += 1
                
                print(f"Creating new user: {username_to_insert}, {user_email}, provider_id={user_provider_id}")
                cursor.execute("""
                    INSERT INTO users (username, email, password_hash, provider, provider_id, avatar_url)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (username_to_insert, user_email, None, 'google', user_provider_id, user_avatar_url))
                conn.commit()
                
                new_user_id = cursor.lastrowid
                if not new_user_id and isinstance(conn, SupabaseConnection): 
                    print("Attempting to retrieve new user ID from Supabase after insert...")
                    cursor.execute("SELECT * FROM users WHERE email = ?", (user_email,)) # Re-fetch by email
                    newly_created_user = cursor.fetchone()
                    if newly_created_user:
                        new_user_id = newly_created_user['id']
                        print(f"Retrieved new user ID {new_user_id} for {user_email} from Supabase.")
                    else:
                        print(f"CRITICAL ERROR: Failed to retrieve newly created user {user_email} from Supabase after insert.")
                        if request.headers.get('Accept') == 'application/json':
                            return jsonify(success=False, error='Critical error during user registration (DB consistency).'), 500
                        flash('Critical error during user registration. Please contact support.', 'danger')
                        return redirect(url_for('login'))
                
                if new_user_id:
                    session['user_id'] = new_user_id
                    session['username'] = username_to_insert
                    session['avatar_url'] = user_avatar_url
                    session['provider'] = 'google'
                    print(f"New user {username_to_insert} created with ID {new_user_id} and logged in.")
                else:
                    # This should ideally not be reached if DB operations are correct
                    print(f"ERROR: Failed to get new_user_id after insert for {user_email}.")
                    if request.headers.get('Accept') == 'application/json':
                        return jsonify(success=False, error='Error creating user account (no ID).'), 500
                    flash('Error creating user account. Please try again.', 'danger')
                    return redirect(url_for('login'))

            except Exception as e_insert:
                print(f"Error inserting new OAuth user ({user_email}): {e_insert}")
                import traceback
                traceback.print_exc()
                if request.headers.get('Accept') == 'application/json':
                    return jsonify(success=False, error=f'Error registering user: {str(e_insert)}'), 500
                flash('An error occurred while registering your account. Please try again.', 'danger')
                return redirect(url_for('login'))
        
        if isinstance(conn, sqlite3.Connection): # Only close if it's SQLite
            conn.close()
        
        print("Auth Callback - Success. User logged in/registered.")
        # flash('Successfully logged in with Google!', 'success') # Flash is for HTML responses
        
        if request.headers.get('Accept') == 'application/json':
            return jsonify(success=True, username=session.get('username'), user_id=session.get('user_id'))

        # This redirect is for when Supabase redirects directly to /auth/callback
        # For JS fetch, the JS will handle the redirect based on JSON response
        flash('Successfully logged in with Google!', 'success')
        next_url = request.args.get('next') or url_for('index')
        return redirect(next_url)

    except Exception as e:
        print(f"Auth Callback - General Exception: {e}")
        import traceback
        traceback.print_exc()
        error_message = f'An unexpected error occurred during Google sign-in: {str(e)}'
        if request.headers.get('Accept') == 'application/json':
            return jsonify(success=False, error=error_message), 500
        flash(error_message, 'danger')
        return redirect(url_for('login'))

if __name__ == '__main__':
    # Initialize database
    init_db()
    if not os.path.exists('static/uploads'):
        os.makedirs('static/uploads')
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
