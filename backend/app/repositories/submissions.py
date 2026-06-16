import json

from sqlalchemy.orm import Session

from app.models.submission import SubmissionRecord
from app.schemas import mask_ssn


def _redact(state: dict) -> dict:
    """Never persist a full SSN: store only the masked form."""
    extracted = state.get("extracted_data")
    if isinstance(extracted, dict) and extracted.get("ssn"):
        state = {**state, "extracted_data": {**extracted, "ssn": mask_ssn(extracted["ssn"])}}
    return state


class SubmissionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, record: SubmissionRecord) -> SubmissionRecord:
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def get(self, submission_id: str) -> SubmissionRecord | None:
        return self.db.get(SubmissionRecord, submission_id)

    def save_result(self, record, state: dict) -> None:
        state = _redact(state)
        record.status = state.get("status", "failed")
        record.result_json = json.dumps(state, default=str)
        record.error = state.get("error")
        self.db.commit()
