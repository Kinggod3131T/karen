from typing import Any

import psutil
from fastapi import APIRouter

from services.core.app.settings import settings


router = APIRouter(tags=["System"])


@router.get("/")
def root() -> dict[str, str]:
    return {
        "name": "Karen",
        "version": settings.app_version,
        "status": "online",
    }


@router.get("/health")
def health() -> dict[str, Any]:
    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()
    disk = psutil.disk_usage("/")

    return {
        "status": "healthy",
        "memory": {
            "total_gib": round(memory.total / 1024**3, 2),
            "available_gib": round(memory.available / 1024**3, 2),
            "used_percent": memory.percent,
        },
        "swap": {
            "total_gib": round(swap.total / 1024**3, 2),
            "used_gib": round(swap.used / 1024**3, 2),
            "used_percent": swap.percent,
        },
        "disk": {
            "total_gib": round(disk.total / 1024**3, 2),
            "free_gib": round(disk.free / 1024**3, 2),
            "used_percent": disk.percent,
        },
    }
