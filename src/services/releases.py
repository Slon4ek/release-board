import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.events import EventType, ReleaseCreatedPayload, ReleaseStatusChangedPayload
from src.models import OutboxEvent, Release
from src.schemas import (
    VALID_TRANSITIONS,
    ReleaseEnvironment,
    ReleaseStatus,
)


class ReleaseServiceError(Exception):
    """Базовая ошибка прикладного слоя."""


class ReleaseNotFoundError(ReleaseServiceError):
    def __init__(self, release_id: uuid.UUID) -> None:
        self.release_id = release_id
        super().__init__(f"Release {release_id} not found")


class InvalidStatusTransitionError(ReleaseServiceError):
    def __init__(self, current: ReleaseStatus, target: ReleaseStatus) -> None:
        self.current = current
        self.target = target
        super().__init__(f"Cannot transition from {current.value} to {target.value}")


async def _add_outbox_event(
    db: AsyncSession,
    *,
    aggregate_id: uuid.UUID,
    event_type: EventType,
    payload: ReleaseCreatedPayload | ReleaseStatusChangedPayload,
) -> None:
    db.add(
        OutboxEvent(
            aggregate_id=aggregate_id,
            event_type=event_type.value,
            payload=payload.model_dump(mode="json"),
        )
    )


async def create_release(
    db: AsyncSession,
    *,
    service: str,
    version: str,
    environment: ReleaseEnvironment,
) -> Release:
    release = Release(service=service, version=version, environment=environment)
    db.add(release)
    await _add_outbox_event(
        db,
        aggregate_id=release.id,
        event_type=EventType.RELEASE_CREATED,
        payload=ReleaseCreatedPayload(
            service=service,
            version=version,
            environment=environment,
            status=ReleaseStatus.PLANNED,
        ),
    )
    await db.commit()
    await db.refresh(release)
    return release


async def list_releases(
    db: AsyncSession,
    *,
    service: str | None = None,
    environment: ReleaseEnvironment | None = None,
    status_filter: ReleaseStatus | None = None,
) -> list[Release]:
    stmt = select(Release)
    if service is not None:
        stmt = stmt.where(Release.service == service)
    if environment is not None:
        stmt = stmt.where(Release.environment == environment)
    if status_filter is not None:
        stmt = stmt.where(Release.status == status_filter)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_release(db: AsyncSession, release_id: uuid.UUID):
    release = await db.get(Release, release_id)
    if release is None:
        raise ReleaseNotFoundError(release_id)
    return release


async def change_release_status(
    db: AsyncSession,
    release_id: uuid.UUID,
    target: ReleaseStatus,
):
    release = await get_release(db, release_id)
    current = ReleaseStatus(release.status)
    if target not in VALID_TRANSITIONS.get(current, set()):
        raise InvalidStatusTransitionError(current, target)
    release.status = target
    await _add_outbox_event(
        db,
        aggregate_id=release.id,
        event_type=EventType.RELEASE_STATUS_CHANGED,
        payload=ReleaseStatusChangedPayload(
            service=release.service,
            version=release.version,
            environment=release.environment,
            previous_status=current,
            new_status=target,
        ),
    )
    await db.commit()
    await db.refresh(release)
    return release


async def delete_release(db: AsyncSession, release_id: uuid.UUID) -> None:
    release = await get_release(db, release_id)
    await db.delete(release)
    await db.commit()
