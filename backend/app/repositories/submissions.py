import json

from sqlalchemy.orm import Session

from app.models.submission import SubmissionRecord


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
        record.status = state.get("status", "failed")
        record.result_json = json.dumps(state, default=str)
        record.error = state.get("error")
        self.db.commit()
