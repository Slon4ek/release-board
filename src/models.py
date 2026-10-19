import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import DateTime, Integer, String, Uuid, func
from sqlalchemy.dialects.postgresql import ENUM, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.schemas import ReleaseEnvironment, ReleaseStatus


def _enum_values(e: type[StrEnum]) -> list[str]:
    return [m.value for m in e]


class Release(Base):
    __tablename__ = "releases"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        init=False,
        default_factory=uuid.uuid4,
        primary_key=True,
    )

    service: Mapped[str] = mapped_column(String(255), nullable=False)

    version: Mapped[str] = mapped_column(String(50), nullable=False)

    environment: Mapped[ReleaseEnvironment] = mapped_column(
        ENUM(
            ReleaseEnvironment,
            name="release_environment",
            create_type=False,
            values_callable=_enum_values,
        ),
        nullable=False,
    )

    status: Mapped[ReleaseStatus] = mapped_column(
        ENUM(
            ReleaseStatus,
            name="release_status",
            create_type=False,
            values_callable=_enum_values,
        ),
        nullable=False,
        default=ReleaseStatus.PLANNED,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        init=False,
        default_factory=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )


class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        init=False,
        default_factory=uuid.uuid4,
        primary_key=True,
    )

    aggregate_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)

    event_type: Mapped[str] = mapped_column(String(100), nullable=False)

    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)

    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, init=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        init=False,
        default_factory=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )


class ProcessedEvent(Base):
    __tablename__ = "processed_events"

    event_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)

    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        init=False,
        default_factory=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )
