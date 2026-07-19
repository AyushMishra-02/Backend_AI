import os
import time
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

DB_URL = os.getenv("DATABASE_URL")

def main():
    if not DB_URL:
        print("Error: DATABASE_URL not found in .env")
        return

    print("Connecting to database...")
    try:
        conn = psycopg2.connect(DB_URL)
        conn.autocommit = True
        cursor = conn.cursor()
    except Exception as e:
        print(f"Failed to connect: {e}")
        return

    print("Dropping existing index (if any) to show before/after...")
    cursor.execute("DROP INDEX IF EXISTS idx_users_email;")

    print("Seeding table with 10,000 rows. This might take a moment...")
    # Generate 10,000 users
    users = [(f"User {i}", f"user{i}@example.com") for i in range(10000)]
    
    # Insert in batches
    execute_values(
        cursor,
        "INSERT INTO users (name, email) VALUES %s ON CONFLICT (email) DO NOTHING",
        users,
        page_size=1000
    )
    print("Seed complete.")

    target_email = "user9999@example.com"
    query = f"EXPLAIN ANALYZE SELECT * FROM users WHERE email = '{target_email}';"

    print(f"\n--- Running EXPLAIN ANALYZE BEFORE index for email: {target_email} ---")
    cursor.execute(query)
    for row in cursor.fetchall():
        print(row[0])

    print("\nCreating index on email column...")
    cursor.execute("CREATE INDEX idx_users_email ON users(email);")

    print(f"\n--- Running EXPLAIN ANALYZE AFTER index for email: {target_email} ---")
    cursor.execute(query)
    for row in cursor.fetchall():
        print(row[0])

    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()
