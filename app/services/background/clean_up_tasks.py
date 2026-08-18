from app.repositories.trip_seat_repository import TripSeatRepository
from app.core.database import async_session_factory

async def cleanup_expired_holds():
    async with async_session_factory() as db:
        repo = TripSeatRepository(db)
        count = await repo.release_expired_holds()
        print(f"Released {count} expired holds.")