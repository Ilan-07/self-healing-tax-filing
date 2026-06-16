from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    UploadFile,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_api_key
from app.api.dependencies.services import get_storage, get_workflow
from app.core.logging import get_logger
from app.db.session import SessionLocal, get_db
from app.models.submission import SubmissionRecord
from app.repositories.submissions import SubmissionRepository
from app.schemas import SubmissionResult
from app.services.documents.service import SUPPORTED_EXTENSIONS
from app.services.storage.service import StorageService

logger = get_logger(__name__)
router = APIRouter(prefix="/submissions", tags=["submissions"])


def _run_workflow(
    submission_id: str,
    original_filename: str,
    upload_paths: list[str],
    report_path: str,
) -> None:
    """Run the agent pipeline off the request path; persist the result."""
    logger.info("processing submission %s (%d docs)", submission_id, len(upload_paths))
    state = get_workflow().run(
        {
            "submission_id": submission_id,
            "original_filename": original_filename,
            "upload_path": upload_paths[0],
            "upload_paths": upload_paths,
            "report_path": report_path,
            "status": "parsing",
            "audit_trail": [],
            "remediation_attempts": 0,
        }
    )
    db = SessionLocal()
    try:
        record = SubmissionRepository(db).get(submission_id)
        if record:
            SubmissionRepository(db).save_result(record, state)
    finally:
        db.close()
    logger.info("submission %s finished: %s", submission_id, state.get("status"))


@router.post("", response_model=SubmissionResult, status_code=202)
async def create_submission(
    background: BackgroundTasks,
    documents: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    storage: StorageService = Depends(get_storage),
    _: None = Depends(require_api_key),
):
    if not documents:
        raise HTTPException(422, "Upload at least one document")
    for doc in documents:
        if Path(doc.filename or "").suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise HTTPException(415, "Upload PDF, PNG, JPG, or JPEG documents")
    submission_id = str(uuid4())
    upload_paths = [
        str(await storage.save_upload(submission_id, doc)) for doc in documents
    ]
    original_filename = ", ".join(
        doc.filename or Path(p).name for doc, p in zip(documents, upload_paths)
    )
    report_path = storage.report_path(submission_id)
    record = SubmissionRepository(db).create(
        SubmissionRecord(
            id=submission_id,
            original_filename=original_filename,
            upload_path=upload_paths[0],
            report_path=str(report_path),
            status="processing",
        )
    )
    # Non-blocking: the pipeline runs after the response; clients poll GET.
    background.add_task(
        _run_workflow, submission_id, original_filename, upload_paths, str(report_path)
    )
    return _to_result(record, {"status": "processing"})


@router.get("/{submission_id}", response_model=SubmissionResult)
def get_submission(
    submission_id: str,
    db: Session = Depends(get_db),
    _: None = Depends(require_api_key),
):
    record = SubmissionRepository(db).get(submission_id)
    if not record:
        raise HTTPException(404, "Submission not found")
    state = json.loads(record.result_json) if record.result_json else {}
    return _to_result(record, state)


@router.get("/{submission_id}/report")
def download_report(
    submission_id: str,
    db: Session = Depends(get_db),
    _: None = Depends(require_api_key),
):
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
