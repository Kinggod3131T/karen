from fastapi import FastAPI

from services.core.app.routes import ai, files, system
from services.core.app.settings import settings


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Local-first AI workstation orchestration service with "
        "controlled workspace tools."
    ),
)

app.include_router(system.router)
app.include_router(ai.router)
app.include_router(files.router)
