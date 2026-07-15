from typing import Any

from fastapi import APIRouter

from services.core.app.clients.ollama import generate, list_models
from services.core.app.schemas import ChatRequest, ChatResponse


router = APIRouter(prefix="/ai", tags=["AI"])


@router.get("/models")
async def models() -> dict[str, Any]:
    return await list_models()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    result = await generate(
        prompt=request.prompt,
        model=request.model,
    )

    return ChatResponse(
        model=result.get("model", request.model or "unknown"),
        response=result.get("response", ""),
        done=result.get("done", False),
    )
