from typing import Any

import httpx
import psutil
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from services.core.app.settings import settings


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Local-first AI workstation orchestration service",
)


class ChatRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=20_000)
    model: str | None = None


class ChatResponse(BaseModel):
    model: str
    response: str
    done: bool


@app.get("/")
def root() -> dict[str, str]:
    return {
        "name": "Karen",
        "version": settings.app_version,
        "status": "online",
    }


@app.get("/health")
def health() -> dict[str, Any]:
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


@app.get("/models")
async def models() -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{settings.ollama_base_url}/api/tags")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Ollama is unavailable: {exc}",
        ) from exc


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    selected_model = request.model or settings.ollama_model

    payload = {
        "model": selected_model,
        "prompt": request.prompt,
        "stream": False,
    }

    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(
                f"{settings.ollama_base_url}/api/generate",
                json=payload,
            )
            response.raise_for_status()
            result = response.json()

    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=504,
            detail="The local model took too long to respond.",
        ) from exc

    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Local model request failed: {exc}",
        ) from exc

    return ChatResponse(
        model=result.get("model", selected_model),
        response=result.get("response", ""),
        done=result.get("done", False),
    )
