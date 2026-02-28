#!/usr/bin/env python3
"""
Database initialization script for Litterboxd MySQL setup.
This script creates the necessary database tables and can be run with:
    python init_db.py

Before running this, ensure:
1. Your .env file is configured with DigitalOcean credentials
2. Your DigitalOcean MySQL database is accessible
"""

import asyncio
import os
import sys
from dotenv import load_dotenv
from database import engine, init_db, async_session
from models import Base, BathroomModel, ReviewModel, StallModel, WebhookModel, FavoriteModel


async def main():
    """Initialize database and create all tables"""

    load_dotenv()

    print("🔄 Initializing Litterboxd Database...")
    print(f"Database: {os.getenv('MYSQL_DB', 'defaultdb')}")
    print(f"Host: {os.getenv('MYSQL_HOST')}")

    try:
        # Create all tables
        await init_db()
        print("✅ Database tables created successfully!")

        # Test connection
        from sqlalchemy import text
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
            print("✅ Database connection test passed!")

        print("\n📊 Tables created:")
        print("  - bathrooms (stores bathroom metadata, ratings)")
        print("  - reviews (stores student reviews and ratings)")
        print("  - stalls (stores real-time stall occupancy)")
        print("  - webhooks (stores facility coordinator webhooks)")
        print("  - favorites (stores user favorite bathrooms)")

        print("\n✨ Database initialization complete!")
        print("\nYou can now start the API with:")
        print("  uvicorn main:app --reload")
        
        print("\n🔗 API Documentation will be available at:")
        print("  http://localhost:8000/docs (Swagger UI)")
        print("  http://localhost:8000/redoc (ReDoc)")

        # Dispose engine to ensure all DB connections are closed cleanly
        try:
            await engine.dispose()
        except Exception:
            # If dispose fails, ignore to avoid masking earlier success
            pass

    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())

