import sqlite3
import pandas as pd

# Replace with your actual file paths
CSV_FILE = r"C:\Users\Sayan\Downloads\AI.csv"
DB_FILE =r"C:\Users\Sayan\OneDrive\Desktop\AI\database.db"
TABLE_NAME = 'tools'  # Change if your table name is different

# Read CSV (adjust column names if needed)
df = pd.read_csv(CSV_FILE, encoding='unicode_escape')


# Optional: Rename columns to match DB schema if necessary
df = df.rename(columns={
    'Name': 'name',
    'Description': 'description',
    'Link': 'link',
    'Logo_URL': 'logo_url',
    'Category': 'category',
    'Pricing_Model': 'pricing_model'
})

# Add missing columns with default values if not present
for col in ['average_rating', 'total_ratings', 'created_at']:
    if col not in df.columns:
        df[col] = None

# Connect to SQLite database
conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()


# Insert data
for _, row in df.iterrows():
    cursor.execute(f'''
        INSERT INTO {TABLE_NAME} 
        (name, description, link, logo_url, category, pricing_model, average_rating, total_ratings, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        row['name'],
        row['description'],
        row['link'],
        row['logo_url'],
        row['category'],
        row['pricing_model'],
        row['average_rating'],
        row['total_ratings'],
        row['created_at']
    ))

conn.commit()
conn.close()

print("CSV data successfully pushed to SQLite database.")
