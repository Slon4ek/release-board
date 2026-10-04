import uuid
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import DateTime, String, Uuid, func
from sqlalchemy.dialects.postgresql import ENUM
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
