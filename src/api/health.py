import logging
import os
import subprocess

from fastapi import APIRouter, Response
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from src.database import async_session_maker_null_pool
from src.schemas import VersionResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])

APP_VERSION = os.getenv("APP_VERSION", "0.1.0")


def _get_git_sha() -> str:
    sha = os.getenv("GIT_SHA")
    if sha:
        return sha[:8]
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        return result.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


@router.get("/live")
async def live() -> dict[str, str]:
    return {"status": "alive"}


@router.get("/ready")
async def ready(response: Response) -> dict[str, str]:
    try:
        async with async_session_maker_null_pool() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "ready"}
    except SQLAlchemyError:
        logger.debug("Database health check failed")
        response.status_code = 503
        return {"status": "unavailable"}


@router.get("/version", response_model=VersionResponse)
async def version() -> VersionResponse:
    return VersionResponse(version=APP_VERSION, git_sha=_get_git_sha())
