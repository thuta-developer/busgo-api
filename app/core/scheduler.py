import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core.database import async_session_factory
from app.repositories.trip_seat_repository import TripSeatRepository

logger = logging.getLogger(__name__)

async def cleanup_expired_holds_job():
    """Expired Holds များကို ရှင်းလင်းပေးသော Background Job"""
    try:
        async with async_session_factory() as db:
            repo = TripSeatRepository(db)
            count = await repo.release_expired_holds()
            if count > 0:
                logger.info(f"🧹 Released {count} expired holds.")
            else:
                logger.debug("No expired holds to release.")
    except Exception as e:
        logger.error(f"❌ Error in cleanup_expired_holds_job: {e}", exc_info=True)

# Scheduler Instance
scheduler = AsyncIOScheduler()

def start_scheduler():
    """FastAPI Startup မှာ ဒါကိုခေါ်ပါ"""
    scheduler.add_job(
        cleanup_expired_holds_job,
        trigger=IntervalTrigger(minutes=1),  # ၁ မိနစ်တိုင်း စစ်ဆေးမည်
        id="cleanup_expired_holds",
        replace_existing=True,
        max_instances=1,  # တစ်ခါတည်း အစုံမလုပ်ရ
        coalesce=True,  # နောက်ကျသော job များကို တစ်ခါတည်း merge လုပ်မည်
    )
    scheduler.start()
    logger.info("🚀 Scheduler started. Cleanup job runs every 1 minute.")

def shutdown_scheduler():
    """FastAPI Shutdown မှာ ဒါကိုခေါ်ပါ"""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("🛑 Scheduler shut down.")