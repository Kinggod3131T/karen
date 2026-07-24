import httpx
from fastapi import HTTPException
from pydantic import ValidationError

from services.core.app.schemas import ModelPlan
from services.core.app.settings import settings


SYSTEM_PROMPT = """
You are Karen's safe software-engineering planning component.

Convert the user's task into a small sequence of file operations.

Allowed actions:
1. create_directory
2. write_file

Rules:
- Return only data matching the supplied JSON schema.
- Never propose terminal commands.
- Never propose file deletion.
- Never modify /etc, /usr, /boot, /var, or other system locations.
- Use paths relative to /home/kabeer/Workspace.
- For Karen's own repository, paths should begin with karen/.
- Keep the plan minimal.
- Do not claim an action has already happened.
- Every action must explain why it is necessary.
""".strip()


async def build_plan(task: str) -> ModelPlan:
    payload = {
        "model": settings.ollama_model,
        "system": SYSTEM_PROMPT,
        "prompt": task,
        "stream": False,
        "format": ModelPlan.model_json_schema(),
        "options": {
            "temperature": 0,
            "num_predict": 2048,
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
            detail="The planning model exceeded its timeout.",
        ) from exc

    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"The planning model is unavailable: {exc}",
        ) from exc

    raw_plan = result.get("response", "")

    try:
        return ModelPlan.model_validate_json(raw_plan)

    except ValidationError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "The model returned an invalid plan.",
                "validation_error": str(exc),
                "raw_response": raw_plan,
            },
        ) from exc
