-- Create tables in Supabase SQL Editor

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT,
    xp INTEGER DEFAULT 0,
    rank VARCHAR(255) DEFAULT 'AI Rookie',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    provider VARCHAR(50) DEFAULT 'local',
    provider_id TEXT,
    avatar_url TEXT
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
    key_features TEXT, -- JSON array of key features
    gallery_images TEXT, -- JSON array of image URLs
    is_featured BOOLEAN DEFAULT FALSE,
    featured_since TIMESTAMP,
    country_of_origin VARCHAR(255) DEFAULT 'Unknown',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tool submissions table (for pending admin approval)
CREATE TABLE IF NOT EXISTS tool_submissions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    link TEXT NOT NULL,
    logo_url TEXT,
    category VARCHAR(255) NOT NULL,
    pricing_model VARCHAR(255) NOT NULL,
    key_features TEXT, -- JSON array of key features
    gallery_images TEXT, -- JSON array of image URLs
    average_rating DECIMAL(3,2) DEFAULT 0,
    total_ratings INTEGER DEFAULT 0,
    is_featured BOOLEAN DEFAULT FALSE,
    submitter_email VARCHAR(255) NOT NULL,
    country_of_origin VARCHAR(255) NOT NULL DEFAULT 'Unknown',
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add new columns to existing tools table (run these if table already exists)
ALTER TABLE tools ADD COLUMN IF NOT EXISTS key_features TEXT;
ALTER TABLE tools ADD COLUMN IF NOT EXISTS gallery_images TEXT;
ALTER TABLE tools ADD COLUMN IF NOT EXISTS is_featured BOOLEAN DEFAULT FALSE;
ALTER TABLE tools ADD COLUMN IF NOT EXISTS featured_since TIMESTAMP;
ALTER TABLE tools ADD COLUMN IF NOT EXISTS country_of_origin VARCHAR(255) DEFAULT 'Unknown';
ALTER TABLE tools ADD COLUMN IF NOT EXISTS visits INTEGER DEFAULT 0;

-- Add new columns to existing users table for OAuth support
ALTER TABLE users ADD COLUMN IF NOT EXISTS provider VARCHAR(50) DEFAULT 'local';
ALTER TABLE users ADD COLUMN IF NOT EXISTS provider_id TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url TEXT;
ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL;

-- Set default values for existing tools
UPDATE tools SET key_features = '["AI-powered capabilities", "User-friendly interface", "Professional grade quality"]' WHERE key_features IS NULL;
UPDATE tools SET gallery_images = '[]' WHERE gallery_images IS NULL;
UPDATE tools SET is_featured = FALSE WHERE is_featured IS NULL;

-- Set default provider for existing users
UPDATE users SET provider = 'local' WHERE provider IS NULL;

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
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    tool_id INTEGER REFERENCES tools(id) ON DELETE CASCADE,
    parent_id INTEGER REFERENCES comments(id) ON DELETE CASCADE,
    comment TEXT NOT NULL,
    like_count INTEGER DEFAULT 0,
    love_count INTEGER DEFAULT 0,
    angry_count INTEGER DEFAULT 0,
    laugh_count INTEGER DEFAULT 0,
    is_edited BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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

-- User stacks table (for AI Stack Builder feature)
CREATE TABLE IF NOT EXISTS user_stacks (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    prompt TEXT NOT NULL, -- Store the user's original request
    workflow TEXT NOT NULL, -- Store the complete workflow as JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Comment reactions table (replacing comment_votes)
CREATE TABLE IF NOT EXISTS comment_reactions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    comment_id INTEGER REFERENCES comments(id) ON DELETE CASCADE,
    reaction_type VARCHAR(10) NOT NULL CHECK (reaction_type IN ('like', 'love', 'angry', 'laugh')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, comment_id)
);

-- Enable Row Level Security (RLS) for better security
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE tools ENABLE ROW LEVEL SECURITY;
ALTER TABLE ratings ENABLE ROW LEVEL SECURITY;
ALTER TABLE comments ENABLE ROW LEVEL SECURITY;
ALTER TABLE contact_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE comment_reactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_stacks ENABLE ROW LEVEL SECURITY;

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
-- RLS Policies for comment_reactions
CREATE POLICY "Allow all operations on comment_reactions" ON comment_reactions USING (true);
-- RLS Policies for user_stacks
CREATE POLICY "Allow users to read their own stacks" ON user_stacks FOR SELECT USING (auth.uid()::text::integer = user_id);
CREATE POLICY "Allow users to manage their own stacks" ON user_stacks FOR ALL USING (auth.uid()::text::integer = user_id);
