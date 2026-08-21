import uuid
from typing import Optional, TYPE_CHECKING, Any
from sqlalchemy import String, Integer, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
if TYPE_CHECKING:
    from app.models.bus_company import BusCompany
    from app.models.seat import Seat
    from app.models.trip import Trip

class Bus(BaseModel):
    __tablename__ = "buses"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bus_companies.id", ondelete="CASCADE"), nullable=False
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., Scania VIP-01
    bus_image_url : Mapped[str | None] = mapped_column(String(255), nullable=True)
    bus_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)  # e.g., 3D/8899
    total_seats: Mapped[int] = mapped_column(Integer, nullable=False)
    bus_type: Mapped[str] = mapped_column(String(50), default="VIP")  # e.g., Standard, VIP 2+1
    features: Mapped[dict[str, Any] | list[str] | None] = mapped_column(
        JSONB, nullable=True, default=dict  # သို့မဟုတ် default=list
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    company: Mapped["BusCompany"] = relationship("BusCompany", back_populates="buses")
    seats: Mapped[list["Seat"]] = relationship("Seat", back_populates="bus")
    trips: Mapped[list["Trip"]] = relationship("Trip", back_populates="bus", cascade="all, delete-orphan")
