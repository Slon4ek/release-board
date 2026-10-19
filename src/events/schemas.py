from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from src.schemas import ReleaseEnvironment, ReleaseStatus


class EventType(StrEnum):
    RELEASE_CREATED = "release.created"
    RELEASE_STATUS_CHANGED = "release.status_changed"


class EventEnvelope[ET: EventType](BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    event_type: ET
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    schema_version: Literal[1] = 1
    aggregate_id: UUID


class ReleaseCreatedPayload(BaseModel):
    service: str
    version: str
    environment: ReleaseEnvironment
    status: ReleaseStatus


class ReleaseCreated(EventEnvelope[Literal[EventType.RELEASE_CREATED]]):
    payload: ReleaseCreatedPayload


class ReleaseStatusChangedPayload(BaseModel):
    service: str
    version: str
    environment: ReleaseEnvironment
    previous_status: ReleaseStatus
    new_status: ReleaseStatus


class ReleaseStatusChanged(EventEnvelope[Literal[EventType.RELEASE_STATUS_CHANGED]]):
    payload: ReleaseStatusChangedPayload
