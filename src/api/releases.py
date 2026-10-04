import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status

from src.dependencies import db_dep
from src.models import Release
from src.schemas import (
    ReleaseCreate,
    ReleaseEnvironment,
    ReleaseResponse,
    ReleaseStatus,
    ReleaseStatusUpdate,
)
from src.services import releases as release_service

router = APIRouter(prefix="/releases", tags=["releases"])


@router.post("", response_model=ReleaseResponse, status_code=status.HTTP_201_CREATED)
async def create_release(data: ReleaseCreate, db: db_dep) -> Release:
    return await release_service.create_release(
        db,
        service=data.service,
        version=data.version,
        environment=data.environment,
    )


@router.get("", response_model=list[ReleaseResponse])
async def list_releases(
    db: db_dep,
    service: str | None = None,
    environment: ReleaseEnvironment | None = None,
    status_filter: Annotated[ReleaseStatus | None, Query(alias="status")] = None,
) -> list[Release]:
    return await release_service.list_releases(
        db,
        service=service,
        environment=environment,
        status_filter=status_filter,
    )


@router.get("/{release_id}", response_model=ReleaseResponse)
async def get_release(release_id: uuid.UUID, db: db_dep) -> Release:
    return await release_service.get_release(db, release_id)


@router.patch("/{release_id}/status", response_model=ReleaseResponse)
async def update_release_status(release_id: uuid.UUID, data: ReleaseStatusUpdate, db: db_dep) -> Release:
    return await release_service.change_release_status(db, release_id, data.status)


@router.delete("/{release_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_release(release_id: uuid.UUID, db: db_dep) -> None:
    await release_service.delete_release(db, release_id)
