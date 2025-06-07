from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3
import os
from datetime import datetime
import re
import tempfile
import json

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')

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
    """Initialize database - file-based SQLite that persists in /tmp on Vercel"""
    init_sqlite_db()

def init_sqlite_db():
    """Initialize SQLite database"""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        xp INTEGER DEFAULT 0,
        rank TEXT DEFAULT 'AI Rookie',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Tools table
    c.execute('''CREATE TABLE IF NOT EXISTS tools (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT NOT NULL,
        link TEXT NOT NULL,
        logo_url TEXT,
        category TEXT NOT NULL,
        pricing_model TEXT NOT NULL,
        average_rating REAL DEFAULT 0,
        total_ratings INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Ratings table
    c.execute('''CREATE TABLE IF NOT EXISTS ratings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        tool_id INTEGER,
        rating INTEGER NOT NULL,
        review TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (tool_id) REFERENCES tools (id),
        UNIQUE(user_id, tool_id)
    )''')
    
    # Comments table (original structure)
    c.execute('''CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        tool_id INTEGER,
        comment TEXT NOT NULL,
        upvotes INTEGER DEFAULT 0,
        downvotes INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (tool_id) REFERENCES tools (id)    )''')
    
    # Run migrations
    migrate_database(c)
    
    # Contact messages table
    c.execute('''CREATE TABLE IF NOT EXISTS contact_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        message TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
      # Add sample data for demo purposes (only if no tools exist)
    c.execute("SELECT COUNT(*) FROM tools")
    if c.fetchone()[0] == 0:
        sample_tools = [
            ('ChatGPT', 'Advanced AI chatbot for conversations and assistance', 'https://chat.openai.com', '', 'Chatbots', 'Freemium', 4.5, 1000),
            ('Claude', 'AI assistant by Anthropic for various tasks', 'https://claude.ai', '', 'Chatbots', 'Freemium', 4.4, 800),
            ('Midjourney', 'AI image generation tool', 'https://midjourney.com', '', 'Image Generation', 'Paid', 4.6, 1200),
            ('GitHub Copilot', 'AI code completion tool', 'https://github.com/features/copilot', '', 'Code Generation', 'Paid', 4.3, 900),
            ('Notion AI', 'AI-powered writing and productivity assistant', 'https://notion.so', '', 'Productivity', 'Freemium', 4.2, 600),
            ('Jasper', 'AI content generation platform', 'https://jasper.ai', '', 'Content Creation', 'Paid', 4.1, 500)
        ]
        
        for tool in sample_tools:
            c.execute('''INSERT INTO tools (name, description, link, logo_url, category, pricing_model, average_rating, total_ratings) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', tool)
    
    conn.commit()
    conn.close()
    
    # Try to import JSON data if available (for Vercel deployment with exported data)
    if os.environ.get('VERCEL'):
        import_json_data()

def migrate_database(cursor):
    """Apply database migrations"""
    # Check if new columns exist and add them if they don't
    try:        # Check for parent_id column
        cursor.execute("PRAGMA table_info(comments)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'parent_id' not in columns:
            cursor.execute('ALTER TABLE comments ADD COLUMN parent_id INTEGER DEFAULT NULL')
        if 'updated_at' not in columns:
            cursor.execute('ALTER TABLE comments ADD COLUMN updated_at TIMESTAMP')
        if 'is_edited' not in columns:
            cursor.execute('ALTER TABLE comments ADD COLUMN is_edited BOOLEAN DEFAULT 0')
            
        # Create new tables
        cursor.execute('''CREATE TABLE IF NOT EXISTS comment_votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            comment_id INTEGER,
            vote_type TEXT CHECK(vote_type IN ('upvote', 'downvote')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (comment_id) REFERENCES comments (id),
            UNIQUE(user_id, comment_id)
        )''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS comment_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            comment_id INTEGER,
            reason TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (comment_id) REFERENCES comments (id),
            UNIQUE(user_id, comment_id)
        )''')
        
    except Exception as e:
        print(f"Migration error: {e}")

def get_db_connection():
    """Get database connection - uses persistent file path"""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def calculate_rank(xp):
    if xp >= 5000:
        return '🚀 AI Supreme Leader'
    elif xp >= 4000:
        return '🧠 AI Leader'
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

def import_json_data():
    """Import data from JSON files if they exist (for Vercel deployment)"""
    data_dir = 'data_export'
    if not os.path.exists(data_dir):
        return False
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if data already imported
        cursor.execute("SELECT COUNT(*) FROM tools")
        existing_tools = cursor.fetchone()[0]
        
        # Only import if we have very few tools (just sample data)
        if existing_tools > 10:
            return False
        
        print("📦 Importing data from JSON files...")
        
        # Import users
        users_file = os.path.join(data_dir, 'users.json')
        if os.path.exists(users_file):
            with open(users_file, 'r') as f:
                users = json.load(f)
            
            for user in users:
                try:
                    cursor.execute('''INSERT OR IGNORE INTO users 
                                    (username, email, password_hash, xp, rank, created_at) 
                                    VALUES (?, ?, ?, ?, ?, ?)''',
                                 (user['username'], user['email'], user['password_hash'],
                                  user['xp'], user['rank'], user['created_at']))
                except Exception as e:
                    print(f"Error importing user {user.get('username', 'unknown')}: {e}")
            
            print(f"✅ Imported {len(users)} users")
        
        # Import tools
        tools_file = os.path.join(data_dir, 'tools.json')
        if os.path.exists(tools_file):
            with open(tools_file, 'r') as f:
                tools = json.load(f)
            
            # Clear sample data first
            cursor.execute("DELETE FROM tools WHERE name IN ('ChatGPT', 'Claude', 'Midjourney', 'GitHub Copilot', 'Notion AI', 'Jasper')")
            
            for tool in tools:
                try:
                    cursor.execute('''INSERT OR IGNORE INTO tools 
                                    (name, description, link, logo_url, category, pricing_model, 
                                     average_rating, total_ratings, created_at) 
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                                 (tool['name'], tool['description'], tool['link'], tool['logo_url'],
                                  tool['category'], tool['pricing_model'], tool['average_rating'],
                                  tool['total_ratings'], tool['created_at']))
                except Exception as e:
                    print(f"Error importing tool {tool.get('name', 'unknown')}: {e}")
            
            print(f"✅ Imported {len(tools)} tools")
        
        # Import ratings
        ratings_file = os.path.join(data_dir, 'ratings.json')
        if os.path.exists(ratings_file):
            with open(ratings_file, 'r') as f:
                ratings = json.load(f)
            
            for rating in ratings:
                try:
                    cursor.execute('''INSERT OR IGNORE INTO ratings 
                                    (user_id, tool_id, rating, review, created_at) 
                                    VALUES (?, ?, ?, ?, ?)''',
                                 (rating['user_id'], rating['tool_id'], rating['rating'],
                                  rating['review'], rating['created_at']))
                except Exception as e:
                    print(f"Error importing rating: {e}")
            
            print(f"✅ Imported {len(ratings)} ratings")
        
        # Import comments  
        comments_file = os.path.join(data_dir, 'comments.json')
        if os.path.exists(comments_file):
            with open(comments_file, 'r') as f:
                comments = json.load(f)
            
            for comment in comments:
                try:
                    cursor.execute('''INSERT OR IGNORE INTO comments 
                                    (user_id, tool_id, parent_id, comment, upvotes, downvotes, created_at) 
                                    VALUES (?, ?, ?, ?, ?, ?, ?)''',
                                 (comment['user_id'], comment['tool_id'], comment.get('parent_id'),
                                  comment['comment'], comment['upvotes'], comment['downvotes'], 
                                  comment['created_at']))
                except Exception as e:
                    print(f"Error importing comment: {e}")
            
            print(f"✅ Imported {len(comments)} comments")
        
        conn.commit()
        print("🎉 Data import completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error during import: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

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
        
        # Check if user exists
        existing_user = conn.execute(
            'SELECT id FROM users WHERE username = ? OR email = ?', 
            (username, email)
        ).fetchone()
        
        if existing_user:
            flash('Username or email already exists', 'error')
            conn.close()
            return render_template('register.html')
        
        # Create user
        password_hash = generate_password_hash(password)
        conn.execute(
            'INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
            (username, email, password_hash)
        )
        conn.commit()
        conn.close()
        
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
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['rank'] = user['rank']
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
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
    ''', (tool_id,)).fetchall()
      # Get comments with user votes and replies structure
    comments_query = '''
        SELECT c.*, u.username, u.rank,
               COALESCE(cv.vote_type, '') as user_vote
        FROM comments c
        JOIN users u ON c.user_id = u.id
        LEFT JOIN comment_votes cv ON c.id = cv.comment_id AND cv.user_id = ?
        WHERE c.tool_id = ? AND c.parent_id IS NULL
        ORDER BY c.created_at ASC
    '''
    
    user_id_for_votes = session.get('user_id', -1)  # Use -1 if not logged in
    comments = conn.execute(comments_query, (user_id_for_votes, tool_id)).fetchall()
      # Convert comments to list of dictionaries and get replies
    comments_list = []
    for comment in comments:
        comment_dict = dict(comment)
        replies_query = '''
            SELECT c.*, u.username, u.rank,
                   COALESCE(cv.vote_type, '') as user_vote
            FROM comments c
            JOIN users u ON c.user_id = u.id
            LEFT JOIN comment_votes cv ON c.id = cv.comment_id AND cv.user_id = ?
            WHERE c.parent_id = ?
            ORDER BY c.created_at ASC
        '''
        replies = conn.execute(replies_query, (user_id_for_votes, comment_dict['id'])).fetchall()
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
def rate_tool():
    if 'user_id' not in session:
        return jsonify({'error': 'Please log in to rate tools'}), 401
    
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
def add_comment():
    if 'user_id' not in session:
        return jsonify({'error': 'Please log in to comment'}), 401
    
    tool_id = request.json.get('tool_id')
    comment = request.json.get('comment')
    parent_id = request.json.get('parent_id')  # For replies
    
    if not tool_id or not comment:
        return jsonify({'error': 'Invalid comment data'}), 400
    
    conn = get_db_connection()
    
    # Insert comment
    cursor = conn.execute(
        'INSERT INTO comments (user_id, tool_id, comment, parent_id) VALUES (?, ?, ?, ?)',
        (session['user_id'], tool_id, comment, parent_id)
    )
    comment_id = cursor.lastrowid
    
    # Award XP for commenting
    update_user_xp(session['user_id'], 30, conn)
    
    # Get the newly created comment with user info
    new_comment = conn.execute('''
        SELECT c.*, u.username, u.rank 
        FROM comments c
        JOIN users u ON c.user_id = u.id
        WHERE c.id = ?
    ''', (comment_id,)).fetchone()
    
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
            'upvotes': new_comment['upvotes'],
            'downvotes': new_comment['downvotes'],
            'parent_id': new_comment['parent_id']
        }
    })

@app.route('/vote_comment', methods=['POST'])
def vote_comment():
    if 'user_id' not in session:
        return jsonify({'error': 'Please log in to vote'}), 401
    
    comment_id = request.json.get('comment_id')
    vote_type = request.json.get('vote_type')  # 'upvote' or 'downvote'
    
    if not comment_id or vote_type not in ['upvote', 'downvote']:
        return jsonify({'error': 'Invalid vote data'}), 400
    
    conn = get_db_connection()
    
    # Check if user already voted on this comment
    existing_vote = conn.execute(
        'SELECT vote_type FROM comment_votes WHERE user_id = ? AND comment_id = ?',
        (session['user_id'], comment_id)
    ).fetchone()
    
    if existing_vote:
        if existing_vote['vote_type'] == vote_type:
            # Remove vote if clicking same button
            conn.execute(
                'DELETE FROM comment_votes WHERE user_id = ? AND comment_id = ?',
                (session['user_id'], comment_id)
            )
            
            # Update comment vote count
            if vote_type == 'upvote':
                conn.execute('UPDATE comments SET upvotes = upvotes - 1 WHERE id = ?', (comment_id,))
            else:
                conn.execute('UPDATE comments SET downvotes = downvotes - 1 WHERE id = ?', (comment_id,))
        else:
            # Change vote type
            conn.execute(
                'UPDATE comment_votes SET vote_type = ? WHERE user_id = ? AND comment_id = ?',
                (vote_type, session['user_id'], comment_id)
            )
            
            # Update comment vote counts
            if vote_type == 'upvote':
                conn.execute('UPDATE comments SET upvotes = upvotes + 1, downvotes = downvotes - 1 WHERE id = ?', (comment_id,))
            else:
                conn.execute('UPDATE comments SET downvotes = downvotes + 1, upvotes = upvotes - 1 WHERE id = ?', (comment_id,))
    else:
        # New vote
        conn.execute(
            'INSERT INTO comment_votes (user_id, comment_id, vote_type) VALUES (?, ?, ?)',
            (session['user_id'], comment_id, vote_type)
        )
        
        # Update comment vote count
        if vote_type == 'upvote':
            conn.execute('UPDATE comments SET upvotes = upvotes + 1 WHERE id = ?', (comment_id,))
        else:
            conn.execute('UPDATE comments SET downvotes = downvotes + 1 WHERE id = ?', (comment_id,))
      # Get updated vote counts and user's current vote
    comment_votes = conn.execute(
        'SELECT upvotes, downvotes FROM comments WHERE id = ?',
        (comment_id,)
    ).fetchone()
    
    # Get user's current vote
    user_current_vote = conn.execute(
        'SELECT vote_type FROM comment_votes WHERE user_id = ? AND comment_id = ?',
        (session['user_id'], comment_id)
    ).fetchone()
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'upvotes': comment_votes['upvotes'],
        'downvotes': comment_votes['downvotes'],
        'user_vote': user_current_vote['vote_type'] if user_current_vote else None
    })

@app.route('/edit_comment', methods=['POST'])
def edit_comment():
    if 'user_id' not in session:
        return jsonify({'error': 'Please log in to edit comments'}), 401
    
    comment_id = request.json.get('comment_id')
    new_comment = request.json.get('comment')
    
    if not comment_id or not new_comment:
        return jsonify({'error': 'Invalid comment data'}), 400
    
    conn = get_db_connection()
    
    # Check if user owns the comment
    comment_owner = conn.execute(
        'SELECT user_id FROM comments WHERE id = ?',
        (comment_id,)
    ).fetchone()
    
    if not comment_owner or comment_owner['user_id'] != session['user_id']:
        conn.close()
        return jsonify({'error': 'You can only edit your own comments'}), 403
    
    # Update comment
    conn.execute(
        'UPDATE comments SET comment = ?, updated_at = CURRENT_TIMESTAMP, is_edited = TRUE WHERE id = ?',
        (new_comment, comment_id)
    )
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/delete_comment', methods=['POST'])
def delete_comment():
    if 'user_id' not in session:
        return jsonify({'error': 'Please log in to delete comments'}), 401
    
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
    
    # Delete comment (this will also delete replies due to cascade)
    conn.execute('DELETE FROM comments WHERE id = ? OR parent_id = ?', (comment_id, comment_id))
    conn.execute('DELETE FROM comment_votes WHERE comment_id = ?', (comment_id,))
    
    conn.commit()
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
    conn.close()
    
    return render_template('leaderboard.html', users=users)

@app.route('/support')
def support():
    return render_template('support.html')

# Admin routes
@app.route('/super-admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # In production, use environment variable or more secure method
        if username == 'admin' and password == 'admin123':
            session['admin'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid admin credentials', 'error')
            return render_template('admin/login.html')
    
    return render_template('admin/login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    
    conn = get_db_connection()
    tools = conn.execute('SELECT * FROM tools ORDER BY created_at DESC').fetchall()
    
    # Get some stats
    stats = {
        'total_tools': conn.execute('SELECT COUNT(*) FROM tools').fetchone()[0],
        'total_users': conn.execute('SELECT COUNT(*) FROM users').fetchone()[0],
        'total_ratings': conn.execute('SELECT COUNT(*) FROM ratings').fetchone()[0],
        'total_comments': conn.execute('SELECT COUNT(*) FROM comments').fetchone()[0]
    }
    
    conn.close()
    return render_template('admin/dashboard.html', tools=tools, stats=stats)

@app.route('/admin/add-tool', methods=['GET', 'POST'])
def admin_add_tool():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
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
    session.pop('admin', None)
    return redirect(url_for('index'))

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

    # Import data from JSON files if they exist (for Vercel deployment)
    import_json_data()
