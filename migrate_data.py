#!/usr/bin/env python3
"""
Data Migration Script for Ayou Platform
Migrates data from SQLite to PostgreSQL for Vercel deployment
"""

import os
import sqlite3
from database_postgres import get_postgres_connection

def migrate_data():
    """Migrate data from SQLite to PostgreSQL"""
    print("🚀 Starting data migration from SQLite to PostgreSQL...")
    
    # Check if PostgreSQL URL is set
    if not os.environ.get('POSTGRES_URL'):
        print("❌ POSTGRES_URL environment variable not set!")
        print("Please set your PostgreSQL connection string first.")
        return False
    
    try:
        # Connect to SQLite database
        print("📂 Connecting to SQLite database...")
        sqlite_conn = sqlite3.connect('database.db')
        sqlite_conn.row_factory = sqlite3.Row
        sqlite_cursor = sqlite_conn.cursor()
        
        # Connect to PostgreSQL database
        print("🐘 Connecting to PostgreSQL database...")
        postgres_conn = get_postgres_connection()
        postgres_cursor = postgres_conn.cursor()
        
        # Migrate users
        print("👥 Migrating users...")
        sqlite_cursor.execute("SELECT username, email, password_hash, xp, rank, created_at FROM users")
        users = sqlite_cursor.fetchall()
        user_count = 0
        
        for user in users:
            try:
                postgres_cursor.execute(
                    """INSERT INTO users (username, email, password_hash, xp, rank, created_at) 
                       VALUES (%s, %s, %s, %s, %s, %s) 
                       ON CONFLICT (username) DO NOTHING""",
                    (user['username'], user['email'], user['password_hash'], 
                     user['xp'], user['rank'], user['created_at'])
                )
                user_count += 1
            except Exception as e:
                print(f"⚠️ Error migrating user {user['username']}: {e}")
        
        print(f"✅ Migrated {user_count} users")
        
        # Migrate tools
        print("🛠️ Migrating tools...")
        sqlite_cursor.execute("""SELECT name, description, link, logo_url, category, 
                                        pricing_model, average_rating, total_ratings, created_at 
                                 FROM tools""")
        tools = sqlite_cursor.fetchall()
        tool_count = 0
        
        for tool in tools:
            try:
                postgres_cursor.execute(
                    """INSERT INTO tools (name, description, link, logo_url, category, 
                                         pricing_model, average_rating, total_ratings, created_at) 
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (tool['name'], tool['description'], tool['link'], tool['logo_url'],
                     tool['category'], tool['pricing_model'], tool['average_rating'],
                     tool['total_ratings'], tool['created_at'])
                )
                tool_count += 1
            except Exception as e:
                print(f"⚠️ Error migrating tool {tool['name']}: {e}")
        
        print(f"✅ Migrated {tool_count} tools")
        
        # Migrate ratings (if any)
        print("⭐ Migrating ratings...")
        try:
            sqlite_cursor.execute("""SELECT u.username, t.name, r.rating, r.review, r.created_at 
                                     FROM ratings r 
                                     JOIN users u ON r.user_id = u.id 
                                     JOIN tools t ON r.tool_id = t.id""")
            ratings = sqlite_cursor.fetchall()
            rating_count = 0
            
            for rating in ratings:
                try:
                    # Get user and tool IDs from PostgreSQL
                    postgres_cursor.execute("SELECT id FROM users WHERE username = %s", (rating['username'],))
                    user_result = postgres_cursor.fetchone()
                    
                    postgres_cursor.execute("SELECT id FROM tools WHERE name = %s", (rating['name'],))
                    tool_result = postgres_cursor.fetchone()
                    
                    if user_result and tool_result:
                        postgres_cursor.execute(
                            """INSERT INTO ratings (user_id, tool_id, rating, review, created_at) 
                               VALUES (%s, %s, %s, %s, %s) 
                               ON CONFLICT (user_id, tool_id) DO NOTHING""",
                            (user_result[0], tool_result[0], rating['rating'], 
                             rating['review'], rating['created_at'])
                        )
                        rating_count += 1
                except Exception as e:
                    print(f"⚠️ Error migrating rating: {e}")
            
            print(f"✅ Migrated {rating_count} ratings")
        except Exception as e:
            print(f"⚠️ Ratings table might not exist: {e}")
        
        # Migrate contact messages (if any)
        print("📧 Migrating contact messages...")
        try:
            sqlite_cursor.execute("SELECT name, email, message, created_at FROM contact_messages")
            messages = sqlite_cursor.fetchall()
            message_count = 0
            
            for message in messages:
                try:
                    postgres_cursor.execute(
                        """INSERT INTO contact_messages (name, email, message, created_at) 
                           VALUES (%s, %s, %s, %s)""",
                        (message['name'], message['email'], message['message'], message['created_at'])
                    )
                    message_count += 1
                except Exception as e:
                    print(f"⚠️ Error migrating contact message: {e}")
            
            print(f"✅ Migrated {message_count} contact messages")
        except Exception as e:
            print(f"⚠️ Contact messages table might not exist: {e}")
        
        # Commit all changes
        postgres_conn.commit()
        
        # Close connections
        sqlite_conn.close()
        postgres_conn.close()
        
        print("\n🎉 Migration completed successfully!")
        print("Your data has been migrated to PostgreSQL and should now persist on Vercel.")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

def check_migration():
    """Check if migration was successful by comparing record counts"""
    print("\n🔍 Checking migration results...")
    
    try:
        # SQLite counts
        sqlite_conn = sqlite3.connect('database.db')
        sqlite_cursor = sqlite_conn.cursor()
        
        sqlite_cursor.execute("SELECT COUNT(*) FROM users")
        sqlite_users = sqlite_cursor.fetchone()[0]
        
        sqlite_cursor.execute("SELECT COUNT(*) FROM tools")
        sqlite_tools = sqlite_cursor.fetchone()[0]
        
        sqlite_conn.close()
        
        # PostgreSQL counts
        postgres_conn = get_postgres_connection()
        postgres_cursor = postgres_conn.cursor()
        
        postgres_cursor.execute("SELECT COUNT(*) FROM users")
        postgres_users = postgres_cursor.fetchone()[0]
        
        postgres_cursor.execute("SELECT COUNT(*) FROM tools")
        postgres_tools = postgres_cursor.fetchone()[0]
        
        postgres_conn.close()
        
        print(f"📊 Migration Summary:")
        print(f"   Users: SQLite({sqlite_users}) → PostgreSQL({postgres_users})")
        print(f"   Tools: SQLite({sqlite_tools}) → PostgreSQL({postgres_tools})")
        
        if sqlite_users == postgres_users and sqlite_tools == postgres_tools:
            print("✅ Migration verification successful!")
        else:
            print("⚠️ Some data might not have been migrated completely.")
            
    except Exception as e:
        print(f"❌ Could not verify migration: {e}")

if __name__ == "__main__":
    print("🔧 Ayou Platform Data Migration Tool")
    print("=====================================")
    
    # Check if SQLite database exists
    if not os.path.exists('database.db'):
        print("❌ No SQLite database found (database.db)")
        print("Nothing to migrate.")
        exit(1)
    
    # Check if PostgreSQL URL is configured
    if not os.environ.get('POSTGRES_URL'):
        print("❌ PostgreSQL connection not configured!")
        print("Please set the POSTGRES_URL environment variable.")
        print("Example: export POSTGRES_URL='postgresql://username:password@host:port/database'")
        exit(1)
    
    # Run migration
    if migrate_data():
        check_migration()
        print("\n🚀 You can now deploy to Vercel with persistent database!")
    else:
        print("\n❌ Migration failed. Please check the errors above.")
        exit(1)
