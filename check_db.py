import sqlite3
import os

def get_db_path():
    if os.environ.get('VERCEL'):
        return '/tmp/database.db'
    return 'database.db'

db_path = get_db_path()
print(f'Database path: {db_path}')
print(f'Database exists: {os.path.exists(db_path)}')

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    
    # Check tools count
    tools_count = conn.execute('SELECT COUNT(*) FROM tools').fetchone()[0]
    print(f'Total tools: {tools_count}')
    
    # Check if DATA_IMPORT_COMPLETED exists
    import_flag = conn.execute("SELECT COUNT(*) FROM tools WHERE name = 'DATA_IMPORT_COMPLETED'").fetchone()[0]
    print(f'Import flag exists: {import_flag > 0}')
    
    # Show first few tools
    tools = conn.execute('SELECT id, name FROM tools LIMIT 5').fetchall()
    print('First 5 tools:')
    for tool in tools:
        print(f'  {tool[0]}: {tool[1]}')
    
    # Check users count
    users_count = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    print(f'Total users: {users_count}')
    
    # Check reviews count
    reviews_count = conn.execute('SELECT COUNT(*) FROM ratings WHERE review IS NOT NULL').fetchone()[0]
    print(f'Total reviews: {reviews_count}')
    
    conn.close()
else:
    print('Database file not found!')
