
import asyncio
from app.core.database import engine

async def test_conn():
    async with engine.connect() as conn:
        print('PostgreSQL Connection Successful!')

asyncio.run(test_conn())