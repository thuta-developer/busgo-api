import uuid
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
if TYPE_CHECKING:
    from app.models.bus import Bus

class BusCompany(BaseModel):
    __tablename__ = "bus_companies"

    name : Mapped[str] = mapped_column(String(150), unique=True, index=True, nullable=False)
    contact_phone : Mapped[str] = mapped_column(String(20), nullable=False)
    email : Mapped[str] = mapped_column(String(255), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    logo_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    buses: Mapped[List["Bus"]] = relationship("Bus", back_populates="company", cascade="all, delete-orphan")