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

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')

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

def get_db_path():
    """Get database path - use /tmp for Vercel persistence"""
    if os.environ.get('VERCEL'):
        # Use /tmp directory on Vercel for better persistence
        db_dir = '/tmp'
        os.makedirs(db_dir, exist_ok=True)
        return os.path.join(db_dir, 'database.db')
    else:
        # Use local directory for development
        return 'database.db'

# Database initialization
def init_db():
    """Initialize database - Supabase for production, SQLite for local"""
    if os.environ.get('SUPABASE_URL') and os.environ.get('SUPABASE_KEY'):
        init_supabase_db()
  

def init_supabase_db():
    """Initialize Supabase database tables"""
    # Supabase tables should be created via the dashboard or SQL editor
    # We don't need to create them programmatically since we're using REST API
    print("Supabase initialization complete - tables should exist in dashboard")

def get_db_connection():
    """Get database connection - Supabase for production, SQLite for local"""
    supabase_url = os.environ.get('SUPABASE_URL')
    supabase_key = os.environ.get('SUPABASE_KEY')
    
    print(f"DEBUG: SUPABASE_URL exists: {bool(supabase_url)}")
    print(f"DEBUG: SUPABASE_KEY exists: {bool(supabase_key)}")
    
    if supabase_url and supabase_key:
        try:
            print("DEBUG: Attempting to use Supabase")
            return SupabaseConnection()
        except Exception as e:
            print(f"DEBUG: Supabase connection failed: {e}")
            print("DEBUG: Falling back to SQLite")
    else:
        print("DEBUG: Using SQLite (no Supabase env vars)")
    
    # Use SQLite for local development or fallback
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

class SupabaseConnection:
    """Supabase database connection using REST API"""
    def __init__(self):
        import requests
        
        self.base_url = os.environ.get('SUPABASE_URL')
        self.api_key = os.environ.get('SUPABASE_KEY')
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
        
        try:            # SELECT COUNT(*) queries
            if 'select count(*) from tools' in sql_lower:
                if 'data_import_completed' in sql_lower:
                    response = self.session.get(f"{self.base_url}/rest/v1/tools?name=eq.DATA_IMPORT_COMPLETED&select=id")
                else:
                    response = self.session.get(f"{self.base_url}/rest/v1/tools?select=id")
                
                if response.status_code == 200:
                    data = response.json()
                    self._result = [(len(data),)]
                else:                    self._result = [(0,)]
            
            elif 'select count(*) from comments' in sql_lower:
                response = self.session.get(f"{self.base_url}/rest/v1/comments?select=id")
                if response.status_code == 200:
                    data = response.json()
                    self._result = [(len(data),)]
                else:
                    self._result = [(0,)]
            
            elif 'select count(*) from users' in sql_lower:
                response = self.session.get(f"{self.base_url}/rest/v1/users?select=id")
                if response.status_code == 200:
                    data = response.json()
                    self._result = [(len(data),)]
                else:
                    self._result = [(0,)]
            
            elif 'select count(*) from ratings' in sql_lower:
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
                user_data = {
                    'username': params[0],
                    'email': params[1],
                    'password_hash': params[2]
                }
                response = self.session.post(f"{self.base_url}/rest/v1/users", json=user_data)
                if response.status_code in [200, 201]:
                    self._result = response.json()
                    print(f"User created successfully: {user_data['username']}")
                else:
                    print(f"User insert failed: {response.status_code} - {response.text}")
            
            elif 'select id from users where username' in sql_lower and params:
                username_or_email_1 = params[0]
                username_or_email_2 = params[1] if len(params) > 1 else params[0]
                
                # Try username first
                response = self.session.get(f"{self.base_url}/rest/v1/users?username=eq.{username_or_email_1}&select=id")
                if response.status_code == 200 and response.json():
                    self._result = [{'id': response.json()[0]['id']}]
                    return self
                
                # Try email
                response = self.session.get(f"{self.base_url}/rest/v1/users?email=eq.{username_or_email_2}&select=id")
                if response.status_code == 200 and response.json():
                    self._result = [{'id': response.json()[0]['id']}]
                else:
                    self._result = []
            
            elif 'select * from users where username' in sql_lower and params:
                username_or_email = params[0]
                
                # Try username first
                response = self.session.get(f"{self.base_url}/rest/v1/users?username=eq.{username_or_email}")
                if response.status_code == 200 and response.json():
                    self._result = response.json()
                    return self
                
                # Try email
                response = self.session.get(f"{self.base_url}/rest/v1/users?email=eq.{username_or_email}")
                self._result = response.json() if response.status_code == 200 else []
            
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
                self._result = response.json() if response.status_code == 200 else []
            
            # TOOL OPERATIONS
            elif 'insert into tools' in sql_lower and params:
                tool_data = {
                    'name': params[0],
                    'description': params[1],
                    'link': params[2],
                    'logo_url': params[3] if len(params) > 3 else None,
                    'category': params[4] if len(params) > 4 else '',
                    'pricing_model': params[5] if len(params) > 5 else ''
                }
                response = self.session.post(f"{self.base_url}/rest/v1/tools", json=tool_data)
                if response.status_code in [200, 201]:
                    self._result = response.json()
                else:
                    print(f"Tool insert failed: {response.status_code} - {response.text}")
            
            elif ('select *, coalesce(average_rating, 0)' in sql_lower and 
                  'from tools' in sql_lower and 'limit 12' in sql_lower):
                # Homepage tools query
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
                
                if params:
                    param_idx = 0
                    if 'name like' in sql_lower or 'description like' in sql_lower:
                        search_term = params[param_idx].replace('%', '')
                        filters.append(f"or=(name.ilike.%{search_term}%,description.ilike.%{search_term}%)")
                        param_idx += 2  # Skip both search params
                    
                    if param_idx < len(params) and 'category =' in sql_lower:
                        category = params[param_idx]
                        filters.append(f"category=eq.{category}")
                
                if filters:
                    url += "&" + "&".join(filters)
                
                url += "&order=average_rating.desc.nullslast,total_ratings.desc.nullslast"
                
                response = self.session.get(url)
                if response.status_code == 200:
                    data = response.json()
                    for tool in data:
                        tool['average_rating'] = tool.get('average_rating') or 0
                        tool['total_ratings'] = tool.get('total_ratings') or 0
                    self._result = data
                else:
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
                if 'average_rating' in sql_lower:
                    # Update tool ratings
                    avg_rating, total_ratings, tool_id = params[:3]
                    tool_data = {'average_rating': avg_rating, 'total_ratings': total_ratings}
                    response = self.session.patch(f"{self.base_url}/rest/v1/tools?id=eq.{tool_id}", json=tool_data)
                else:
                    # Update tool info
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
            
            # COMMENT DELETION            elif 'delete from comments where id =' in sql_lower and 'or parent_id =' in sql_lower and params:
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
    session['rank'] = user_data.get('rank', 'Beginner')
    session['xp'] = user_data.get('xp', 0)
    session['admin'] = user_data.get('admin', False)
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
    """Run before each request to check session validity"""
    if not check_session_timeout():
        return redirect(url_for('login'))
    update_session_activity()

# Routes
@app.route('/')
def index():
    conn = get_db_connection()
    tools = conn.execute('''
        SELECT *, COALESCE(average_rating, 0) as average_rating, COALESCE(total_ratings, 0) as total_ratings FROM tools 
        ORDER BY COALESCE(average_rating, 0) DESC, COALESCE(total_ratings, 0) DESC 
        LIMIT 12
    ''').fetchall()
    
    # Get top 3 users for mini leaderboard
    top_users = conn.execute('''
        SELECT username, xp, rank FROM users 
        ORDER BY xp DESC LIMIT 3
    ''').fetchall()
    
    conn.close()
    return render_template('index.html', tools=tools, top_users=top_users)

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
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute(
            'SELECT * FROM users WHERE username = ? OR email = ?', 
            (username, username)
        ).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password_hash'], password):
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

@app.route('/tools')
def tools():
    search = request.args.get('search', '')
    category = request.args.get('category', '')
    conn = get_db_connection()
    query = 'SELECT *, COALESCE(average_rating, 0) as average_rating, COALESCE(total_ratings, 0) as total_ratings FROM tools WHERE 1=1'
    params = []
    
    if search:
        query += ' AND (name LIKE ? OR description LIKE ?)'
        params.extend([f'%{search}%', f'%{search}%'])
    
    if category:
        query += ' AND category = ?'
        params.append(category)
    
    query += ' ORDER BY COALESCE(average_rating, 0) DESC, total_ratings DESC'
    
    tools = conn.execute(query, params).fetchall()
    
    # Get all categories
    categories = conn.execute('SELECT DISTINCT category FROM tools').fetchall()
    
    conn.close()
    return render_template('tools.html', tools=tools, categories=categories, 
                         current_search=search, current_category=category)

@app.route('/tool/<int:tool_id>')
def tool_detail(tool_id):
    conn = get_db_connection()
    
    tool = conn.execute('SELECT *, COALESCE(average_rating, 0) as average_rating, COALESCE(total_ratings, 0) as total_ratings FROM tools WHERE id = ?', (tool_id,)).fetchone()
    if not tool:
        flash('Tool not found', 'error')
        return redirect(url_for('tools'))
    
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
        return jsonify({'error': 'No JSON data provided'}), 400
    
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
    
    # Update tool's average rating
    avg_rating = conn.execute(
        'SELECT AVG(rating) as avg, COUNT(*) as count FROM ratings WHERE tool_id = ?',
        (tool_id,)
    ).fetchone()
    
    conn.execute(
        'UPDATE tools SET average_rating = ?, total_ratings = ? WHERE id = ?',        (round(avg_rating['avg'], 1), avg_rating['count'], tool_id)
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
            'created_at': new_comment['created_at'],            'like_count': new_comment['like_count'],
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

@app.route('/prompt-helper')
def prompt_helper():
    return render_template('prompt_helper.html')

@app.route('/get_tool_suggestions', methods=['POST'])
def get_tool_suggestions():
    prompt = request.json.get('prompt', '').lower()
    
    if not prompt:
        return jsonify({'error': 'Please enter a prompt'}), 400
    
    conn = get_db_connection()
    
    # Simple keyword matching for tool suggestions
    # In production, you'd use more sophisticated NLP/AI matching
    suggestions = []
    tools = conn.execute('SELECT *, COALESCE(average_rating, 0) as average_rating, COALESCE(total_ratings, 0) as total_ratings FROM tools ORDER BY COALESCE(average_rating, 0) DESC').fetchall()
    
    keywords = {
        'pdf': ['document', 'pdf', 'text', 'read'],
        'image': ['image', 'photo', 'picture', 'visual', 'design'],
        'video': ['video', 'movie', 'clip', 'stream'],
        'text': ['text', 'write', 'content', 'blog', 'article'],
        'code': ['code', 'programming', 'developer', 'github'],
        'data': ['data', 'analytics', 'chart', 'visualization'],
        'audio': ['audio', 'sound', 'music', 'voice'],
        'chat': ['chat', 'conversation', 'talk', 'assistant']
    }
    
    relevant_tools = []
    for tool in tools:
        tool_text = (tool['name'] + ' ' + tool['description'] + ' ' + tool['category']).lower()
        relevance_score = 0
        
        for keyword in prompt.split():
            if keyword in tool_text:
                relevance_score += 2
        
        for category, category_keywords in keywords.items():
            if any(keyword in prompt for keyword in category_keywords):
                if category in tool['category'].lower():
                    relevance_score += 3
        
        if relevance_score > 0:
            relevant_tools.append({
                'tool': dict(tool),
                'score': relevance_score
            })
    
    # Sort by relevance and take top 5
    relevant_tools.sort(key=lambda x: x['score'], reverse=True)
    top_tools = [item['tool'] for item in relevant_tools[:5]]
    
    # Generate simple roadmap
    roadmap = [
        {
            'step': 1,
            'title': 'Identify Your Needs',
            'description': f'Based on your prompt "{prompt[:50]}...", you need tools that can help with this specific task.',
            'tools': top_tools[:2] if top_tools else []
        },
        {
            'step': 2,
            'title': 'Choose the Right Tool',
            'description': 'Select from the recommended tools based on your budget and feature requirements.',
            'tools': top_tools[2:4] if len(top_tools) > 2 else []
        },
        {
            'step': 3,
            'title': 'Execute and Optimize',
            'description': 'Use the selected tool and optimize your workflow for best results.',
            'tools': top_tools[4:] if len(top_tools) > 4 else []
        }
    ]
    
    conn.close()
    
    return jsonify({
        'suggestions': [dict(tool) for tool in top_tools],
        'roadmap': roadmap
    })

@app.route('/leaderboard')
def leaderboard():
    conn = get_db_connection()
    users = conn.execute('''
        SELECT username, xp, rank FROM users 
        ORDER BY xp DESC LIMIT 50
    ''').fetchall()
    
    # Get current user's data if logged in
    current_user = None
    if 'user_id' in session:
        current_user_data = conn.execute('''
            SELECT username, xp, rank FROM users WHERE id = ?
        ''', (session['user_id'],)).fetchone()
        if current_user_data:
            current_user = dict(current_user_data)
    
    conn.close()
    
    return render_template('leaderboard.html', users=users, current_user=current_user)

@app.route('/support')
def support():
    return render_template('support.html')

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
    
    # Get comprehensive stats
    stats = {
        'total_tools': conn.execute("SELECT COUNT(*) FROM tools WHERE name != 'DATA_IMPORT_COMPLETED'").fetchone()[0],
        'total_users': conn.execute('SELECT COUNT(*) FROM users').fetchone()[0],
        'total_ratings': conn.execute('SELECT COUNT(*) FROM ratings').fetchone()[0],
        'total_comments': conn.execute('SELECT COUNT(*) FROM comments').fetchone()[0],
        'total_reviews': conn.execute('SELECT COUNT(*) FROM ratings WHERE review IS NOT NULL AND review != ""').fetchone()[0],
        'avg_rating': conn.execute('SELECT AVG(rating) FROM ratings').fetchone()[0] or 0
    }
    
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
        
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO tools (name, description, link, logo_url, category, pricing_model)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, description, link, logo_url, category, pricing_model))
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
        
        try:
            conn.execute('''
                UPDATE tools 
                SET name = ?, description = ?, link = ?, logo_url = ?, 
                    category = ?, pricing_model = ?
                WHERE id = ?
            ''', (name, description, link, logo_url, category, pricing_model, tool_id))
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
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']
        
        conn = get_db_connection()
        conn.execute(
            'INSERT INTO contact_messages (name, email, message) VALUES (?, ?, ?)',
            (name, email, message)
        )
        conn.commit()
        conn.close()
        
        flash('Thank you for your message! We\'ll get back to you soon.', 'success')
        return redirect(url_for('contact'))
    
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
        'supabase_key_exists': bool(os.environ.get('SUPABASE_KEY')),
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

if __name__ == '__main__':
    # Initialize database
    init_db()
    if not os.path.exists('static/uploads'):
        os.makedirs('static/uploads')
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

# Initialize database on import for Vercel
if os.environ.get('VERCEL'):
    init_db()

# Initialize database on module import for Vercel
if os.environ.get('VERCEL'):
    # Ensure upload directory exists in temp
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ============================================================================

