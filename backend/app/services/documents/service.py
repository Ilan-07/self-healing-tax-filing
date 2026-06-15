from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import fitz
from PIL import Image


SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}


@dataclass
class DocumentPage:
    number: int
    image: Image.Image
    embedded_text: str = ""


class DocumentService:
    def load(self, path: Path) -> list[DocumentPage]:
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported document type: {path.suffix}")
        if path.suffix.lower() == ".pdf":
            return self._load_pdf(path)
        image = Image.open(path).convert("RGB")
        return [DocumentPage(number=1, image=image)]

    def _load_pdf(self, path: Path) -> list[DocumentPage]:
        pages: list[DocumentPage] = []
        with fitz.open(path) as document:
            for index, page in enumerate(document):
                pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                image = Image.frombytes(
                    "RGB", (pixmap.width, pixmap.height), pixmap.samples
                )
                pages.append(
                    DocumentPage(
                        number=index + 1,
                        image=image,
                        embedded_text=page.get_text("text"),
                    )
                )
        return pages
