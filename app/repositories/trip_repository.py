import uuid
from datetime import datetime, date, time
from typing import List, Optional, Tuple
from sqlalchemy import select, func, or_, and_, cast, Time as SQLTime
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.trip import Trip
from app.schemas.trip import TripCreate, TripUpdate
from app.models.route import Route
from app.models.bus import Bus
from app.models.bus_company import BusCompany


class TripRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _get_time_range(self, time_of_day: str) -> Optional[tuple]:
        """Get start and end time for a given time of day."""
        ranges = {
            "morning": (time(6, 0, 0), time(11, 59, 59)),
            "afternoon": (time(12, 0, 0), time(17, 59, 59)),
            "night": (time(18, 0, 0), time(23, 59, 59)),
        }
        return ranges.get(time_of_day.lower())

    async def get_by_id(self, trip_id: uuid.UUID) -> Optional[Trip]:
        stmt = (
            select(Trip)
            .where(Trip.id == trip_id)
            .options(
                selectinload(Trip.route),
                selectinload(Trip.bus).selectinload(Bus.company),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        size: int = 20,
        route_id: Optional[uuid.UUID] = None,
        bus_id: Optional[uuid.UUID] = None,
        origin: Optional[str] = None,
        destination: Optional[str] = None,
        departure_date: Optional[date] = None,
        include_bookable_only: bool = True,
        time_of_day: Optional[str] = None,
    ) -> Tuple[List[Trip], int]:
        query = (
            select(Trip)
            .select_from(Trip)
            .join(Route, Trip.route_id == Route.id)
            .join(Bus, Trip.bus_id == Bus.id)
            .join(BusCompany, Bus.company_id == BusCompany.id)
            .options(
                selectinload(Trip.route),
                selectinload(Trip.bus).selectinload(Bus.company),
            )
        )

        # Search by route origin/destination or bus number
        if search:
            search_filter = f"%{search}%"
            query = query.where(
                or_(
                    Route.origin.ilike(search_filter),
                    Route.destination.ilike(search_filter),
                    Bus.bus_number.ilike(search_filter),
                    BusCompany.name.ilike(search_filter),
                )
            )

        if origin:
            query = query.where(Route.origin.ilike(f"%{origin}%"))

        if destination:
            query = query.where(Route.destination.ilike(f"%{destination}%"))

        if include_bookable_only:
            if departure_date:
                # Convert departure_date to datetime range for booking window check
                start_datetime = datetime.combine(departure_date, time.min)
                end_datetime = datetime.combine(departure_date, time.max)
                
                query = query.where(
                    and_(
                        Trip.booking_open_date <= start_datetime,
                        Trip.booking_close_date >= end_datetime,
                        Trip.is_active == True,
                    )
                )
            else:
                now = datetime.now()
                query = query.where(
                    and_(
                        Trip.booking_open_date <= now,
                        Trip.booking_close_date >= now,
                        Trip.is_active == True,
                    )
                )

        if departure_date:
            # Since departure_time is Time only, we need to check if it falls within any time of that date
            # We'll just filter by time range (00:00:00 to 23:59:59) which is always true if departure_date is provided
            # But we need to ensure that the trip is available on that date, which is handled by the booking window above.
            # No additional filter needed because departure_time is time only.
            pass

        if time_of_day:
            time_range = self._get_time_range(time_of_day)
            if time_range:
                start_time, end_time = time_range
                query = query.where(
                    and_(
                        Trip.departure_time >= start_time,
                        Trip.departure_time <= end_time,
                    )
                )

        if route_id:
            query = query.where(Trip.route_id == route_id)

        if bus_id:
            query = query.where(Trip.bus_id == bus_id)

        if is_active is not None:
            query = query.where(Trip.is_active == is_active)

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        offset = (page - 1) * size
        query = query.order_by(Trip.departure_time.asc()).offset(offset).limit(size)

        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def create(self, data: TripCreate) -> Trip:
        trip = Trip(**data.model_dump())
        self.db.add(trip)
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise ValueError(
                "Failed to create trip due to a database constraint violation"
            )
        await self.db.refresh(trip)
        return trip

    async def update(self, trip: Trip, data: TripUpdate) -> Trip:
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(trip, key, value)
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise ValueError(
                "Failed to update trip due to a database constraint violation"
            )
        await self.db.refresh(trip)
        return trip

    async def delete(self, trip: Trip) -> None:
        await self.db.delete(trip)
        await self.db.commit()


    async def soft_delete(self, trip: Trip) -> None:
        trip.is_active = False
        await self.db.commit()