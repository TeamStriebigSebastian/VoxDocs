import asyncio
from sqlalchemy import text
from app.core.database import async_session_maker

async def migrate():
    async with async_session_maker() as db:
        print("Starting migration...")
        
        # 1. Add preferred_language to users
        try:
            await db.execute(text("ALTER TABLE users ADD COLUMN preferred_language VARCHAR(10) DEFAULT 'de'"))
            print("Added preferred_language to users.")
        except Exception as e:
            if "duplicate column" in str(e):
                print("Column preferred_language already exists in users.")
            else:
                print(f"Error adding preferred_language: {e}")

        # 2. Add default_language to tenants
        try:
            await db.execute(text("ALTER TABLE tenants ADD COLUMN default_language VARCHAR(10) DEFAULT 'de'"))
            print("Added default_language to tenants.")
        except Exception as e:
            if "duplicate column" in str(e):
                print("Column default_language already exists in tenants.")
            else:
                print(f"Error adding default_language: {e}")

        # 3. Create entry_translations table
        try:
            await db.execute(text("""
                CREATE TABLE IF NOT EXISTS entry_translations (
                    id SERIAL PRIMARY KEY,
                    entry_id INTEGER NOT NULL,
                    language_code VARCHAR(10) NOT NULL,
                    translated_text TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (entry_id) REFERENCES entries (id) ON DELETE CASCADE
                )
            """))
            print("Created entry_translations table.")
        except Exception as e:
            print(f"Error creating entry_translations table: {e}")
            
        await db.commit()
        print("Migration complete.")

if __name__ == "__main__":
    asyncio.run(migrate())
