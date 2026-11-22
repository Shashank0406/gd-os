import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class StationAgent(Base):
    """MAC and hardware id for one diskless PC. The mapping lives on the server."""

    __tablename__ = "station_agents"

    station_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("stations.id"), primary_key=True)
    mac_address: Mapped[str] = mapped_column(String(17), unique=True, nullable=False)
    hardware_uuid: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    paired_by_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), nullable=False)
    paired_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
