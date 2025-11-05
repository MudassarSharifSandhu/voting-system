"""
Database initialization script

Run this to create the database tables:
    python init_db.py
"""

from database import init_db

if __name__ == "__main__":
    print("Creating database tables...")
    init_db()
    print("Database tables created successfully!")
