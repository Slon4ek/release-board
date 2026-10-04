from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from src.services.releases import InvalidStatusTransitionError, ReleaseNotFoundError


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ReleaseNotFoundError)
    async def handle_release_not_found(request: Request, exc: ReleaseNotFoundError) -> JSONResponse:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": "Release not found"})

    @app.exception_handler(InvalidStatusTransitionError)
    async def handle_invalid_transition(request: Request, exc: InvalidStatusTransitionError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": f"Cannot transition from {exc.current.value} to {exc.target.value}"},
        )
