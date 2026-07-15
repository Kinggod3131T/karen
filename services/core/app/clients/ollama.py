from typing import Any

import httpx
from fastapi import HTTPException

from services.core.app.settings import settings


async def list_models() -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{settings.ollama_base_url}/api/tags"
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Ollama is unavailable: {exc}",
        ) from exc


async def generate(prompt: str, model: str | None = None) -> dict[str, Any]:
    selected_model = model or settings.ollama_model

    payload = {
        "model": selected_model,
        "prompt": prompt,
        "stream": False,
    }

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{settings.ollama_base_url}/api/generate",
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=504,
            detail="The local model exceeded the response timeout.",
        ) from exc

    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Local model request failed: {exc}",
        ) from exc
