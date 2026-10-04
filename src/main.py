import uvicorn
from fastapi import FastAPI

from src.api import errors, health, releases


def create_app() -> FastAPI:
    app = FastAPI(title="Release Board", version="0.1.0")
    errors.register_exception_handlers(app)
    app.include_router(releases.router)
    app.include_router(health.router)
    return app


app = create_app()

if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
