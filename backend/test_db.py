import asyncio
from sqlalchemy import text
from app.db.session import engine


async def test_db():
    async with engine.connect() as conn:

        result = await conn.execute(
            text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
        )

        tables = result.fetchall()

        print("\nTABLES IN SUPABASE:")
        print("-------------------")

        if not tables:
            print("No tables found.")
        else:
            for table in tables:
                print(table[0])


asyncio.run(test_db())