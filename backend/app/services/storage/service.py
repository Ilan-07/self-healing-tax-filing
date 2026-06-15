from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile


class StorageService:
    def __init__(self, root: Path):
        self.root = root.resolve()
        for name in ("uploads", "previews", "generated", "chroma"):
            (self.root / name).mkdir(parents=True, exist_ok=True)

    async def save_upload(self, submission_id: str, upload: UploadFile) -> Path:
        suffix = Path(upload.filename or "document").suffix.lower()
        target_dir = self.root / "uploads" / submission_id
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / f"{uuid4().hex}{suffix}"
        target.write_bytes(await upload.read())
        return target

    def report_path(self, submission_id: str) -> Path:
        target = self.root / "generated" / submission_id
        target.mkdir(parents=True, exist_ok=True)
        return target / "tax_filing_report.pdf"
