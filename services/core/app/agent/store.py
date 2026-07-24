from pathlib import Path

from fastapi import HTTPException

from services.core.app.schemas import ProposalRecord


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
PROPOSAL_DIRECTORY = REPOSITORY_ROOT / "memory" / "proposals"


def _proposal_path(proposal_id: str) -> Path:
    if not proposal_id.replace("-", "").isalnum():
        raise HTTPException(
            status_code=400,
            detail="Invalid proposal ID.",
        )

    return PROPOSAL_DIRECTORY / f"{proposal_id}.json"


def save_proposal(proposal: ProposalRecord) -> None:
    PROPOSAL_DIRECTORY.mkdir(parents=True, exist_ok=True)

    _proposal_path(proposal.id).write_text(
        proposal.model_dump_json(indent=2),
        encoding="utf-8",
    )


def load_proposal(proposal_id: str) -> ProposalRecord:
    path = _proposal_path(proposal_id)

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail="Proposal not found.",
        )

    return ProposalRecord.model_validate_json(
        path.read_text(encoding="utf-8")
    )


def list_proposals() -> list[ProposalRecord]:
    PROPOSAL_DIRECTORY.mkdir(parents=True, exist_ok=True)

    records: list[ProposalRecord] = []

    for path in PROPOSAL_DIRECTORY.glob("*.json"):
        try:
            record = ProposalRecord.model_validate_json(
                path.read_text(encoding="utf-8")
            )
            records.append(record)
        except (ValueError, OSError):
            continue

    return sorted(
        records,
        key=lambda record: record.created_at,
        reverse=True,
    )
