import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

from app.models.database import SessionLocal
from sqlalchemy import text

def check_db():
    print("Attempting to connect to database...")
    try:
        db = SessionLocal()
        # Try a simple query
        db.execute(text("SELECT 1"))
        print("✅ Database connection successful!")
        db.close()
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

if __name__ == "__main__":
    check_db()
