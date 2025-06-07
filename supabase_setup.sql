-- Create tables in Supabase SQL Editor

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    xp INTEGER DEFAULT 0,
    rank VARCHAR(255) DEFAULT 'AI Rookie',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tools table
CREATE TABLE IF NOT EXISTS tools (
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
);

-- Ratings table
CREATE TABLE IF NOT EXISTS ratings (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    tool_id INTEGER REFERENCES tools(id),
    rating INTEGER NOT NULL,
    review TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, tool_id)
);

-- Comments table
CREATE TABLE IF NOT EXISTS comments (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    tool_id INTEGER REFERENCES tools(id),
    parent_id INTEGER REFERENCES comments(id),
    comment TEXT NOT NULL,
    upvotes INTEGER DEFAULT 0,
    downvotes INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Contact messages table
CREATE TABLE IF NOT EXISTS contact_messages (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Comment votes table
CREATE TABLE IF NOT EXISTS comment_votes (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    comment_id INTEGER REFERENCES comments(id),
    vote INTEGER NOT NULL CHECK (vote IN (-1, 1)),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, comment_id)
);

-- Enable Row Level Security (RLS) for better security
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE tools ENABLE ROW LEVEL SECURITY;
ALTER TABLE ratings ENABLE ROW LEVEL SECURITY;
ALTER TABLE comments ENABLE ROW LEVEL SECURITY;
ALTER TABLE contact_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE comment_votes ENABLE ROW LEVEL SECURITY;

-- Create policies for public read access (adjust as needed)
CREATE POLICY "Allow public read access on tools" ON tools FOR SELECT USING (true);
CREATE POLICY "Allow public read access on ratings" ON ratings FOR SELECT USING (true);
CREATE POLICY "Allow public read access on comments" ON comments FOR SELECT USING (true);
CREATE POLICY "Allow public read access on users" ON users FOR SELECT USING (true);

-- Create policies for authenticated operations (you'll need to adjust these based on your auth setup)
CREATE POLICY "Allow all operations on tools" ON tools USING (true);
CREATE POLICY "Allow all operations on ratings" ON ratings USING (true);
CREATE POLICY "Allow all operations on comments" ON comments USING (true);
CREATE POLICY "Allow all operations on users" ON users USING (true);
CREATE POLICY "Allow all operations on contact_messages" ON contact_messages USING (true);
CREATE POLICY "Allow all operations on comment_votes" ON comment_votes USING (true);
