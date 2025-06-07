import os
import psycopg2
from psycopg2 import sql
from urllib.parse import urlparse

def get_db_connection():
    """Get database connection - PostgreSQL for Vercel, SQLite for local"""
    if os.environ.get('VERCEL') and os.environ.get('POSTGRES_URL'):
        # Use PostgreSQL on Vercel
        return get_postgres_connection()
    else:
        # Use SQLite for local development
        import sqlite3
        conn = sqlite3.connect('database.db')
        conn.row_factory = sqlite3.Row
        return conn

def get_postgres_connection():
    """Get PostgreSQL connection for Vercel"""
    database_url = os.environ.get('POSTGRES_URL')
    if not database_url:
        raise ValueError("POSTGRES_URL environment variable not set")
    
    # Parse the URL
    parsed = urlparse(database_url)
    
    conn = psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port,
        database=parsed.path[1:],  # Remove leading slash
        user=parsed.username,
        password=parsed.password,
        sslmode='require'
    )
    return conn

def init_postgres_db():
    """Initialize PostgreSQL database with all tables"""
    conn = get_postgres_connection()
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(255) UNIQUE NOT NULL,
        email VARCHAR(255) UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        xp INTEGER DEFAULT 0,
        rank VARCHAR(255) DEFAULT 'AI Rookie',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Tools table
    c.execute('''CREATE TABLE IF NOT EXISTS tools (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        description TEXT NOT NULL,
        link TEXT NOT NULL,
        logo_url TEXT,
        category VARCHAR(255) NOT NULL,
        pricing_model VARCHAR(255) NOT NULL,
        average_rating DECIMAL(3,2) DEFAULT 0,
        total_ratings INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Ratings table
    c.execute('''CREATE TABLE IF NOT EXISTS ratings (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id),
        tool_id INTEGER REFERENCES tools(id),
        rating INTEGER NOT NULL,
        review TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, tool_id)
    )''')
    
    # Comments table
    c.execute('''CREATE TABLE IF NOT EXISTS comments (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id),
        tool_id INTEGER REFERENCES tools(id),
        parent_id INTEGER REFERENCES comments(id),
        comment TEXT NOT NULL,
        upvotes INTEGER DEFAULT 0,
        downvotes INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Contact messages table
    c.execute('''CREATE TABLE IF NOT EXISTS contact_messages (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        email VARCHAR(255) NOT NULL,
        message TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    conn.commit()
    conn.close()

def migrate_to_postgres():
    """Migrate existing SQLite data to PostgreSQL"""
    import sqlite3
    
    # Connect to both databases
    sqlite_conn = sqlite3.connect('database.db')
    postgres_conn = get_postgres_connection()
    
    sqlite_cursor = sqlite_conn.cursor()
    postgres_cursor = postgres_conn.cursor()
    
    # Migrate users
    sqlite_cursor.execute("SELECT username, email, password_hash, xp, rank, created_at FROM users")
    users = sqlite_cursor.fetchall()
    for user in users:
        postgres_cursor.execute(
            "INSERT INTO users (username, email, password_hash, xp, rank, created_at) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (username) DO NOTHING",
            user
        )
    
    # Migrate tools
    sqlite_cursor.execute("SELECT name, description, link, logo_url, category, pricing_model, average_rating, total_ratings, created_at FROM tools")
    tools = sqlite_cursor.fetchall()
    for tool in tools:
        postgres_cursor.execute(
            "INSERT INTO tools (name, description, link, logo_url, category, pricing_model, average_rating, total_ratings, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            tool
        )
    
    # Note: You'll need to handle foreign key relationships for ratings and comments
    # This is a simplified migration script
    
    postgres_conn.commit()
    sqlite_conn.close()
    postgres_conn.close()
    
    print("Migration completed!")
