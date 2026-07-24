from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from services.core.app.agent.executor import execute_actions
from services.core.app.agent.planner import build_plan
from services.core.app.agent.store import (
    list_proposals,
    load_proposal,
    save_proposal,
)
from services.core.app.schemas import (
    PlanRequest,
    ProposalRecord,
)


router = APIRouter(
    prefix="/agent",
    tags=["Agent"],
)


@router.post("/plan", response_model=ProposalRecord)
async def create_plan(request: PlanRequest) -> ProposalRecord:
    model_plan = await build_plan(request.prompt)

    proposal = ProposalRecord(
        id=str(uuid4()),
        task=request.prompt,
        summary=model_plan.summary,
        actions=model_plan.actions,
        status="pending",
        created_at=datetime.now(timezone.utc).isoformat(),
    )

    save_proposal(proposal)

    return proposal


@router.get(
    "/proposals",
    response_model=list[ProposalRecord],
)
def proposals() -> list[ProposalRecord]:
    return list_proposals()


@router.get(
    "/proposals/{proposal_id}",
    response_model=ProposalRecord,
)
def proposal(proposal_id: str) -> ProposalRecord:
    return load_proposal(proposal_id)


@router.post(
    "/proposals/{proposal_id}/approve",
    response_model=ProposalRecord,
)
def approve_proposal(
    proposal_id: str,
) -> ProposalRecord:
    proposal_record = load_proposal(proposal_id)

    if proposal_record.status != "pending":
        raise HTTPException(
            status_code=409,
            detail=(
                "Only pending proposals can be approved. "
                f"Current status: {proposal_record.status}"
            ),
        )

    try:
        results = execute_actions(proposal_record.actions)

        proposal_record.status = "executed"
        proposal_record.results = results

    except Exception as exc:
        proposal_record.status = "failed"
        proposal_record.error = str(exc)
        save_proposal(proposal_record)
        raise HTTPException(
            status_code=500,
            detail=f"Proposal execution failed: {exc}",
        ) from exc

    save_proposal(proposal_record)

    return proposal_record


@router.post(
    "/proposals/{proposal_id}/reject",
    response_model=ProposalRecord,
)
def reject_proposal(
    proposal_id: str,
) -> ProposalRecord:
    proposal_record = load_proposal(proposal_id)

    if proposal_record.status != "pending":
        raise HTTPException(
            status_code=409,
            detail=(
                "Only pending proposals can be rejected. "
                f"Current status: {proposal_record.status}"
            ),
        )

    proposal_record.status = "rejected"
    save_proposal(proposal_record)

    return proposal_record
