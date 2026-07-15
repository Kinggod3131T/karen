from fastapi import FastAPI
import psutil

app = FastAPI(
    title="Karen Core",
    version="0.1.0",
    description="Local-first AI workstation orchestration service",
)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "name": "Karen",
        "version": "0.1.0",
        "status": "online",
    }


@app.get("/health")
def health() -> dict[str, object]:
    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()

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
    }
