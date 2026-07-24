import json

import httpx
from pydantic import ValidationError

from services.core.app.settings import settings
from services.core.app.workflow.schemas import (
    CodingPlan,
    ReviewResult,
    VerificationResult,
)


async def review_changes(
    task: str,
    plan: CodingPlan,
    diff: str,
    verification: list[VerificationResult],
    model: str,
) -> ReviewResult:
    verification_json = json.dumps(
        [
            result.model_dump()
            for result in verification
        ],
        indent=2,
    )

    prompt = f"""
Review the following code changes.

TASK:
{task}

PLAN:
{plan.model_dump_json(indent=2)}

VERIFICATION:
{verification_json}

GIT DIFF:
{diff[:15_000]}

Return an approved verdict only when:
- the changes appear relevant to the task,
- no obvious unsafe changes exist,
- and every verification step passed.

Otherwise return changes_requested with concrete reasons.
""".strip()

    payload = {
        "model": model or settings.ollama_model,
        "prompt": prompt,
        "stream": False,
        "format": ReviewResult.model_json_schema(),
        "options": {
            "temperature": 0,
            "num_predict": 1_200,
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

        return ReviewResult.model_validate_json(
            result.get("response", "")
        )

    except (
        httpx.HTTPError,
        ValidationError,
        ValueError,
    ):
        return ReviewResult(
            verdict="changes_requested",
            summary=(
                "Karen could not produce a reliable structured review."
            ),
            risks=[
                "The generated changes require manual review."
            ],
            suggested_fixes=[
                "Inspect the Git diff and verification output manually."
            ],
        )
