from typing import Any

from fastapi import APIRouter

from services.core.app.clients.ollama import (
    generate,
    list_models,
)
from services.core.app.project.context import (
    select_project_context,
)
from services.core.app.project.schemas import (
    ProjectChatRequest,
    ProjectChatResponse,
    ProjectContextRequest,
)
from services.core.app.schemas import (
    ChatRequest,
    ChatResponse,
)


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
        model=result.get(
            "model",
            request.model or "unknown",
        ),
        response=result.get("response", ""),
        done=result.get("done", False),
    )


@router.post(
    "/project-chat",
    response_model=ProjectChatResponse,
)
async def project_chat(
    request: ProjectChatRequest,
) -> ProjectChatResponse:
    context = select_project_context(
        ProjectContextRequest(
            path=request.path,
            task=request.task,
            max_files=request.max_files,
            max_chars_per_file=request.max_chars_per_file,
            max_total_chars=request.max_total_chars,
        )
    )

    file_sections: list[str] = []

    for file in context.selected_files:
        file_sections.append(
            "\n".join(
                [
                    f"--- FILE: {file.path}",
                    f"LANGUAGE: {file.language}",
                    f"KIND: {file.kind}",
                    "CONTENT:",
                    file.content,
                    f"--- END FILE: {file.path}",
                ]
            )
        )

    assembled_context = "\n\n".join(file_sections)

    prompt = f"""
You are Karen, a careful local coding assistant.

Use only the supplied project context when making claims about
the existing repository. Clearly state when more files are needed.

Do not claim that you changed files or ran commands.
Return:
1. Your analysis.
2. The recommended implementation.
3. Files that should be edited.
4. Tests or verification commands.

TASK:
{request.task}

PROJECT CONTEXT:
{assembled_context}
""".strip()

    result = await generate(
        prompt=prompt,
        model=request.model,
    )

    return ProjectChatResponse(
        model=result.get(
            "model",
            request.model or "unknown",
        ),
        response=result.get("response", ""),
        done=result.get("done", False),
        index_id=context.index_id,
        context_files=[
            file.path
            for file in context.selected_files
        ],
        context_characters=context.total_characters,
    )
