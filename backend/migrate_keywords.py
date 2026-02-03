
import asyncio
import sys
import os
from sqlalchemy import text

# Add current directory to path so imports work
sys.path.append(os.getcwd())

from app.core.database import async_session_maker

async def migrate_db():
    print("Connecting to database for migration...")
    async with async_session_maker() as session:
        # Check if column exists by inspecting results safely
        try:
            # Try to select the column
            await session.execute(text("SELECT keywords FROM category_definitions LIMIT 1"))
            print("Column 'keywords' already exists.")
        except Exception:
            # If selection fails, the transaction is poisoned. Rollback to clear state.
            await session.rollback()
            print("Column 'keywords' missing. Adding it...")
            
            # Start a new transaction for the alteration
            await session.execute(text("ALTER TABLE category_definitions ADD COLUMN keywords VARCHAR"))
            await session.commit()
            print("Successfully added 'keywords' column.")

if __name__ == "__main__":
    asyncio.run(migrate_db())
