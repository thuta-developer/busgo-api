import uuid
import math
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, date, time
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trip import Trip
from app.repositories.trip_repository import TripRepository
from app.repositories.route_repository import RouteRepository
from app.repositories.bus_repository import BusRepository
from app.schemas.trip import TripCreate, TripUpdate, TripResponse, TripPriceResponse
from app.schemas.common import PaginatedResponse
from app.services.trip_seat_service import TripSeatService

class TripService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = TripRepository(db)
        self.route_repository = RouteRepository(db)
        self.bus_repository = BusRepository(db)
        

    # ========================================
    # Helper
    # ========================================
    async def _to_response(
        self,
        trip: Trip,
        user_type: str = "local",
        check_date: Optional[datetime | date] = None,
    ) -> TripResponse:
        response = TripResponse.model_validate(trip)
        if trip.route:
            response.route_origin = trip.route.origin
            response.route_destination = trip.route.destination
        if trip.bus:
            response.bus_number = trip.bus.bus_number
            response.bus_type = trip.bus.bus_type
            if trip.bus.company:
                response.company_name = trip.bus.company.name
                response.company_logo_url = trip.bus.company.logo_url

        # Populate the single nested price payload expected by the API
        response.price = self.calculate_price(
            trip,
            user_type=user_type,
            check_date=check_date,
        )
        return response

    def _get_time_range(self, time_of_day: str) -> Optional[tuple]:
        ranges = {
            "morning": (time(6, 0, 0), time(11, 59, 59)),
            "afternoon": (time(12, 0, 0), time(17, 59, 59)),
            "night": (time(18, 0, 0), time(23, 59, 59)),
        }
        return ranges.get(time_of_day.lower())

    def calculate_price(
        self,
        trip: Trip,
        user_type: str = "local",
        check_date: Optional[datetime | date] = None,
    ) -> TripPriceResponse:
        user_type = (user_type or "local").lower()

        if check_date is None:
            check_date = datetime.now(timezone.utc)
        elif isinstance(check_date, date) and not isinstance(check_date, datetime):
            check_date = datetime.combine(check_date, time.min, tzinfo=timezone.utc)
        elif check_date.tzinfo is None:
            check_date = check_date.replace(tzinfo=timezone.utc)

        is_festival = False
        regular_base_price = (
            trip.foreigner_price if user_type == "foreigner" else trip.local_price
        )
        festival_base_price = (
            trip.foreigner_festival_price
            if user_type == "foreigner"
            else trip.local_festival_price
        )
        final_price = regular_base_price
        price_type = "foreigner" if user_type == "foreigner" else "local"

        festival_start = trip.festival_start_date
        festival_end = trip.festival_end_date

        if festival_start and festival_end:
            if festival_start.tzinfo is None:
                festival_start = festival_start.replace(tzinfo=timezone.utc)
            if festival_end.tzinfo is None:
                festival_end = festival_end.replace(tzinfo=timezone.utc)

            if festival_start <= check_date <= festival_end:
                is_festival = True

        if is_festival:
            if festival_base_price is not None:
                final_price = festival_base_price
                price_type = (
                    "festival_foreigner"
                    if user_type == "foreigner"
                    else "festival_local"
                )
            else:
                final_price = regular_base_price
                price_type = "foreigner" if user_type == "foreigner" else "local"

        return TripPriceResponse(
            trip_id=trip.id,
            base_price=regular_base_price,
            final_price=final_price,
            price_type=price_type,
            is_festival=is_festival,
            user_type=user_type,
        )

    async def list_trips(
        self,
        search: Optional[str] = None,
        page: int = 1,
        size: int = 20,
        is_active: Optional[bool] = None,
        route_id: Optional[uuid.UUID] = None,
        bus_id: Optional[uuid.UUID] = None,
        origin: Optional[str] = None,
        destination: Optional[str] = None,
        departure_date: Optional[date] = None,
        user_type: str = "local",
        include_bookable_only: bool = True,
        time_of_day: Optional[str] = None,
    ) -> PaginatedResponse[TripResponse]:
        user_type = (user_type or "local").lower()
        trips, total = await self.repo.get_all(
            search=search,
            page=page,
            size=size,
            is_active=is_active,
            route_id=route_id,
            bus_id=bus_id,
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            include_bookable_only=include_bookable_only,
            time_of_day=time_of_day,
        )

        total_pages = math.ceil(total / size) if total > 0 else 0
        items = [
            await self._to_response(t, user_type=user_type, check_date=departure_date)
            for t in trips
        ]
        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            size=size,
            total_pages=total_pages,
        )

    async def get_trip_by_id(self, trip_id: uuid.UUID) -> TripResponse:
        trip = await self.repo.get_by_id(trip_id)
        if not trip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Trip not found",
            )
        return await self._to_response(trip)

    async def create_trip(self, trip_data: TripCreate) -> TripResponse:
        # Validate route exists
        route = await self.route_repository.get_by_id(trip_data.route_id)
        if not route:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Route not found"
            )

        # Validate bus exists
        bus = await self.bus_repository.get_by_id(trip_data.bus_id)
        if not bus:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Bus not found"
            )

        try:
            trip = await self.repo.create(trip_data)
            trip_seat_service = TripSeatService(self.db)
            await trip_seat_service.initialize_trip_seats(trip.id, trip.bus_id)
            return await self._to_response(trip)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    async def update_trip(
        self,
        trip_id: uuid.UUID,
        update_data: TripUpdate,
    ) -> TripResponse:
        existing = await self.repo.get_by_id(trip_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found"
            )

        # Validate route if being changed
        if update_data.route_id:
            route = await self.route_repository.get_by_id(update_data.route_id)
            if not route:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Route not found"
                )

        # Validate bus if being changed
        if update_data.bus_id:
            bus = await self.bus_repository.get_by_id(update_data.bus_id)
            if not bus:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Bus not found"
                )

        update_dict = update_data.model_dump(exclude_unset=True)
        if not update_dict:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No data provided for update",
            )

        try:
            trip = await self.repo.update(existing, update_data)
            return await self._to_response(trip)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    async def delete_trip(self, trip_id: uuid.UUID) -> dict:
        trip = await self.repo.get_by_id(trip_id)
        if not trip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Trip not found",
            )
        await self.repo.delete(trip)
        return {"message": "Trip deleted successfully"}