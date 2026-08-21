import math
import uuid
from typing import List
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.seat import Seat, BusType, SeatPosition
from app.repositories.seat_repository import SeatRepository
from app.schemas.seat import BusSeatResponse, GenerateSeatsRequest


class SeatService:
    def __init__(self, db: AsyncSession):
        self.repo = SeatRepository(db)

    async def generate_bus_seats(
        self, bus_id: uuid.UUID, payload: GenerateSeatsRequest
    ) -> List[BusSeatResponse]:
        """
        Bus တစ်ခုအတွက် 2:1 (VIP) or 2:2 (Standard) Seat Map ကို Auto Generate ပြုလုပ်ပေးခြင်း
        """

        bus = await self.repo.get_bus_by_id(bus_id)
        if not bus:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bus not found",
            )

        # Booking များ ရှိနေပါက Seat များကို ဖျက်၍ မရပါ
        has_bookings = await self.repo.has_bookings_for_bus(bus_id)
        if has_bookings:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot regenerate seats. This bus has existing bookings. Please create a new bus instead.",
            )

        await self.repo.delete_seats_by_bus_id(bus_id)

        new_seats: List[Seat] = []
        create_count = 0

        # VIP (2:1 Layout) Logic 
        if payload.layout_type == BusType.VIP_2_1:
            rows = math.ceil(payload.total_seats/ 3)

            for r in range(rows):
                row_letter = chr(65 + r)
                row_number = r + 1

                col_configs = [
                    (f"{row_letter}1", 1, SeatPosition.RIGHT_WINDOW),
                    (f"{row_letter}2", 2, SeatPosition.LEFT_AISLE),
                    (f"{row_letter}3", 3, SeatPosition.LEFT_WINDOW),
                ]

                for seat_num, col_idx , pos , in col_configs:
                    if create_count >= payload.total_seats:
                        break

                    seat = Seat(
                        bus_id=bus_id,
                        seat_number=seat_num,
                        row_number=row_number,
                        column_number=col_idx,
                        position=pos,
                    )
                    new_seats.append(seat)
                    create_count += 1

        # Standard (2:2 Layout) Logic
        elif payload.layout_type == BusType.STANDARD_2_2:
            rows = math.ceil(payload.total_seats / 4)

            for r in range(rows):
                row_number = r + 1

                col_positions = [
                    (1, SeatPosition.LEFT_WINDOW),
                    (2, SeatPosition.LEFT_AISLE),
                    (3, SeatPosition.RIGHT_AISLE),
                    (4, SeatPosition.RIGHT_WINDOW),
                ]

                for col_idx, pos in col_positions:
                    if create_count >= payload.total_seats:
                        break

                    current_seat_num = create_count + 1

                    seat = Seat(
                        bus_id=bus_id,
                        seat_number=str(current_seat_num),
                        row_number=row_number,
                        column_number=col_idx,
                        position=pos,
                    )
                    new_seats.append(seat)
                    create_count += 1

        await self.repo.create_seats(new_seats)

        await self.repo.update_bus_total_seats(bus, payload.total_seats)

        seats = await self.repo.get_seats_by_bus_id(bus_id)
        return [BusSeatResponse.model_validate(s) for s in seats]

    async def get_bus_seats(self, bus_id: uuid.UUID) -> List[BusSeatResponse]:
        bus = await self.repo.get_bus_by_id(bus_id)

        if not bus:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bus not found",
            )

        seats = await self.repo.get_seats_by_bus_id(bus_id)
        return [BusSeatResponse.model_validate(s) for s in seats]