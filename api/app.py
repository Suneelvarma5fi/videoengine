"""
FastAPI application factory.
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.routes.upload import router as upload_router
from api.routes.jobs import router as jobs_router
from api.routes.presets import router as presets_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="VideoEngine",
        description="Unified subtitle creation & video export platform",
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API routes
    app.include_router(upload_router, prefix="/api")
    app.include_router(jobs_router, prefix="/api")
    app.include_router(presets_router, prefix="/api")

    # Serve frontend from static/
    static_dir = Path(__file__).parent.parent / "static"
    if static_dir.exists():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

    return app


app = create_app()
