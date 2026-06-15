from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.dependencies.services import get_storage, get_workflow
from app.db.session import get_db
from app.models.submission import SubmissionRecord
from app.repositories.submissions import SubmissionRepository
from app.schemas import SubmissionResult
from app.services.documents.service import SUPPORTED_EXTENSIONS
from app.services.storage.service import StorageService
from app.workflow.graph import TaxWorkflow


router = APIRouter(prefix="/submissions", tags=["submissions"])


@router.post("", response_model=SubmissionResult)
async def create_submission(
    document: UploadFile = File(...),
    db: Session = Depends(get_db),
    storage: StorageService = Depends(get_storage),
    workflow: TaxWorkflow = Depends(get_workflow),
):
    suffix = Path(document.filename or "").suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(415, "Upload a PDF, PNG, JPG, or JPEG document")
    submission_id = str(uuid4())
    upload_path = await storage.save_upload(submission_id, document)
    report_path = storage.report_path(submission_id)
    repository = SubmissionRepository(db)
    record = repository.create(
        SubmissionRecord(
            id=submission_id,
            original_filename=document.filename or upload_path.name,
            upload_path=str(upload_path),
            report_path=str(report_path),
            status="parsing",
        )
    )
    state = workflow.run(
        {
            "submission_id": submission_id,
            "original_filename": record.original_filename,
            "upload_path": str(upload_path),
            "report_path": str(report_path),
            "status": "parsing",
            "audit_trail": [],
            "remediation_attempts": 0,
        }
    )
    repository.save_result(record, state)
    return _to_result(record, state)


@router.get("/{submission_id}", response_model=SubmissionResult)
def get_submission(submission_id: str, db: Session = Depends(get_db)):
    record = SubmissionRepository(db).get(submission_id)
    if not record:
        raise HTTPException(404, "Submission not found")
    state = json.loads(record.result_json) if record.result_json else {}
    return _to_result(record, state)


@router.get("/{submission_id}/report")
def download_report(submission_id: str, db: Session = Depends(get_db)):
    record = SubmissionRepository(db).get(submission_id)
    if not record or record.status != "completed" or not record.report_path:
        raise HTTPException(404, "Completed report not found")
    path = Path(record.report_path)
    if not path.exists():
        raise HTTPException(404, "Report file not found")
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=f"tax-report-{submission_id}.pdf",
    )


def _to_result(record: SubmissionRecord, state: dict) -> SubmissionResult:
    return SubmissionResult.model_validate(
        {
            "submission_id": record.id,
            "status": state.get("status", record.status),
            "original_filename": record.original_filename,
            "extracted_data": state.get("extracted_data"),
            "calculation": state.get("calculation"),
            "verification": state.get("verification"),
            "audit_trail": state.get("audit_trail", []),
            "receipt": state.get("receipt"),
            "report_url": (
                f"/api/v1/submissions/{record.id}/report"
                if state.get("status") == "completed"
                else None
            ),
            "error": state.get("error"),
        }
    )
