import httpx
from fastapi import HTTPException
from pydantic import ValidationError

from services.core.app.project.context import (
    select_project_context,
)
from services.core.app.project.schemas import (
    ProjectContextRequest,
)
from services.core.app.settings import settings
from services.core.app.workflow.schemas import (
    CodingPlan,
    CodingTaskRequest,
)


async def build_coding_plan(
    request: CodingTaskRequest,
) -> tuple[CodingPlan, list[str], str]:
    context = select_project_context(
        ProjectContextRequest(
            path=request.path,
            task=request.task,
            max_files=request.max_context_files,
            max_chars_per_file=4_000,
            max_total_chars=20_000,
        )
    )

    context_sections: list[str] = []

    for file in context.selected_files:
        context_sections.append(
            "\n".join(
                [
                    f"--- FILE: {file.path}",
                    f"LANGUAGE: {file.language}",
                    f"KIND: {file.kind}",
                    file.content,
                    f"--- END FILE: {file.path}",
                ]
            )
        )

    project_prefix = request.path.rstrip("/")
    selected_model = request.model or settings.ollama_model

    system_prompt = f"""
You are Karen's software-engineering planning component.

Create a minimal implementation plan for the requested task.

Allowed actions:
- create_directory
- write_file

Security rules:
- Every path must stay inside project {project_prefix}.
- Every action path must begin with {project_prefix}/.
- Never access or modify .git, .venv, .karen, logs or secrets.
- Never modify .env files, private keys or credentials.
- Never propose deletion.
- Never propose terminal commands.
- Do not claim that an operation has already happened.
- For an existing file, write_file content must be the complete
  replacement file, not a partial fragment.
- Keep the plan small and focused.
- Return only JSON matching the supplied schema.
""".strip()

    prompt = f"""
TASK:
{request.task}

PROJECT CONTEXT:
{chr(10).join(context_sections)}
""".strip()

    payload = {
        "model": selected_model,
        "system": system_prompt,
        "prompt": prompt,
        "stream": False,
        "format": CodingPlan.model_json_schema(),
        "options": {
            "temperature": 0,
            "num_predict": 3_000,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{settings.ollama_base_url}/api/generate",
                json=payload,
            )
            response.raise_for_status()
            result = response.json()

    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=504,
            detail="The coding planner exceeded its timeout.",
        ) from exc

    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"The coding planner is unavailable: {exc}",
        ) from exc

    raw_plan = result.get("response", "")

    try:
        plan = CodingPlan.model_validate_json(raw_plan)
    except ValidationError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "The model produced an invalid coding plan.",
                "validation_error": str(exc),
                "raw_response": raw_plan,
            },
        ) from exc

    return (
        plan,
        [file.path for file in context.selected_files],
        selected_model,
    )
