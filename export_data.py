#!/usr/bin/env python3
"""
Export SQLite data to JSON for Vercel deployment
This script exports your local database to JSON files that can be imported on Vercel
"""

import sqlite3
import json
import os
from datetime import datetime

def export_database_to_json():
    """Export all database tables to JSON files"""
    print("🔄 Exporting database to JSON files...")
    
    # Connect to local database
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Create data directory
    os.makedirs('data_export', exist_ok=True)
    
    # Export users
    print("👥 Exporting users...")
    cursor.execute("SELECT * FROM users")
    users = [dict(row) for row in cursor.fetchall()]
    with open('data_export/users.json', 'w') as f:
        json.dump(users, f, indent=2, default=str)
    print(f"   ✅ Exported {len(users)} users")
    
    # Export tools
    print("🛠️ Exporting tools...")
    cursor.execute("SELECT * FROM tools")
    tools = [dict(row) for row in cursor.fetchall()]
    with open('data_export/tools.json', 'w') as f:
        json.dump(tools, f, indent=2, default=str)
    print(f"   ✅ Exported {len(tools)} tools")
    
    # Export ratings
    print("⭐ Exporting ratings...")
    try:
        cursor.execute("SELECT * FROM ratings")
        ratings = [dict(row) for row in cursor.fetchall()]
        with open('data_export/ratings.json', 'w') as f:
            json.dump(ratings, f, indent=2, default=str)
        print(f"   ✅ Exported {len(ratings)} ratings")
    except:
        print("   ⚠️ No ratings table found")
        ratings = []
    
    # Export comments
    print("💬 Exporting comments...")
    try:
        cursor.execute("SELECT * FROM comments")
        comments = [dict(row) for row in cursor.fetchall()]
        with open('data_export/comments.json', 'w') as f:
            json.dump(comments, f, indent=2, default=str)
        print(f"   ✅ Exported {len(comments)} comments")
    except:
        print("   ⚠️ No comments table found")
        comments = []
    
    # Export contact messages
    print("📧 Exporting contact messages...")
    try:
        cursor.execute("SELECT * FROM contact_messages")
        messages = [dict(row) for row in cursor.fetchall()]
        with open('data_export/contact_messages.json', 'w') as f:
            json.dump(messages, f, indent=2, default=str)
        print(f"   ✅ Exported {len(messages)} contact messages")
    except:
        print("   ⚠️ No contact messages table found")
        messages = []
    
    conn.close()
    
    # Create summary
    summary = {
        'export_date': datetime.now().isoformat(),
        'total_users': len(users),
        'total_tools': len(tools),
        'total_ratings': len(ratings),
        'total_comments': len(comments),
        'total_messages': len(messages)
    }
    
    with open('data_export/export_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n🎉 Export completed!")
    print(f"📊 Summary:")
    print(f"   Users: {len(users)}")
    print(f"   Tools: {len(tools)}")
    print(f"   Ratings: {len(ratings)}")
    print(f"   Comments: {len(comments)}")
    print(f"   Messages: {len(messages)}")
    print(f"\n📁 Files created in 'data_export/' directory")

if __name__ == "__main__":
    if not os.path.exists('database.db'):
        print("❌ No database.db found!")
        exit(1)
    
    export_database_to_json()
    print("\n🚀 Next steps:")
    print("1. The JSON files will be included in your deployment")
    print("2. Your app will automatically import this data on Vercel")
    print("3. Deploy with: git add . && git commit -m 'Add data export' && git push && vercel --prod")
