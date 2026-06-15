from __future__ import annotations

import re
from decimal import Decimal
from pathlib import Path
from typing import Any

from app.schemas import AuditEntry, SourceEvidence, TaxpayerData
from app.services.chroma.service import ChromaService
from app.services.documents.service import DocumentService
from app.services.ocr.service import OCRService
from app.services.ollama.client import OllamaClient
from PIL import Image


MONEY_PATTERNS = {
    "wages": [
        r"(?:wages|wages,\s*tips.*?compensation|box\s*1)\D{0,30}([\d,]+\.\d{2})"
    ],
    "federal_tax_withheld": [
        r"(?:federal income tax withheld|box\s*2)\D{0,30}([\d,]+\.\d{2})"
    ],
    "state_tax_withheld": [
        r"(?:state income tax|box\s*17)\D{0,30}([\d,]+\.\d{2})"
    ],
}


class ReadingAgent:
    name = "Reading Agent"

    def __init__(
        self,
        documents: DocumentService,
        ocr: OCRService,
        ollama: OllamaClient,
        default_state_tax_rate: float,
        memory: ChromaService | None = None,
    ):
        self.documents = documents
        self.ocr = ocr
        self.ollama = ollama
        self.default_state_tax_rate = default_state_tax_rate
        self.memory = memory

    def run(self, path: Path) -> tuple[TaxpayerData, str, list[AuditEntry]]:
        pages = self.documents.load(path)
        merged: dict[str, Any] = {}
        all_text: list[str] = []
        evidence: list[SourceEvidence] = []
        confidences: dict[str, float] = {}
        logs: list[AuditEntry] = []

        for page in pages:
            image_ocr = self.ocr.extract(page.image, "")
            ocr_text = image_ocr.text or page.embedded_text
            combined_text = "\n".join(
                value
                for value in (image_ocr.text, page.embedded_text)
                if value.strip()
            )
            all_text.append(combined_text)
            vision = self.ollama.extract_tax_fields(page.image, combined_text)
            vision_confidence = vision.get("field_confidence", {})
            for key, value in vision.items():
                if key != "field_confidence" and value not in (None, "", {}):
                    merged.setdefault(key, value)
            for field in (
                "employee_name",
                "employer_name",
                "wages",
                "federal_tax_withheld",
                "state_tax_withheld",
            ):
                if vision.get(field) not in (None, ""):
                    confidence = self._model_confidence(
                        vision_confidence, field
                    )
                    evidence.append(
                        SourceEvidence(
                            field=field,
                            page=page.number,
                            raw_text=str(vision[field]),
                            source=f"{image_ocr.engine}+ollama",
                            confidence=min(max(confidence, 0), 1),
                        )
                    )
                    confidences[field] = min(max(confidence, 0), 1)
            logs.append(
                AuditEntry(
                    agent=self.name,
                    action="extract_page",
                    reason="OCR and local vision extraction",
                    details={
                        "page": page.number,
                        "ocr_engine": image_ocr.engine,
                        "ocr_confidence": image_ocr.confidence,
                        "vision_fields": sorted(vision.keys()),
                    },
                )
            )
            layout_values, layout_evidence = self._extract_w2_layout(
                page.image,
                ocr_text,
                page.embedded_text,
                page.number,
            )
            for key, value in layout_values.items():
                merged[key] = value
            for item in layout_evidence:
                evidence = [
                    existing
                    for existing in evidence
                    if existing.field != item.field
                ]
                evidence.append(item)
                confidences[item.field] = item.confidence

        raw_text = "\n".join(all_text)
        if self.memory:
            try:
                self.memory.remember(
                    path.stem,
                    raw_text,
                    {"source": path.name, "kind": "uploaded_tax_document"},
                )
            except Exception as exc:
                logs.append(
                    AuditEntry(
                        agent=self.name,
                        action="index_document",
                        reason="ChromaDB indexing was unavailable; processing continued",
                        details={"error": str(exc)},
                    )
                )
        regex_values = self._regex_extract(raw_text)
        for key, value in regex_values.items():
            if merged.get(key) in (None, ""):
                merged[key] = value
                confidences[key] = 0.72
                evidence.append(
                    SourceEvidence(
                        field=key,
                        raw_text=str(value),
                        source="regex",
                        confidence=0.72,
                    )
                )

        merged.setdefault("state_tax_rate", self.default_state_tax_rate)
        merged["evidence"] = evidence
        existing_confidence = merged.get("field_confidence", {})
        if not isinstance(existing_confidence, dict):
            existing_confidence = {}
        merged["field_confidence"] = {**existing_confidence, **confidences}
        data = TaxpayerData.model_validate(merged)
        logs.append(
            AuditEntry(
                agent=self.name,
                action="structure_json",
                reason="Validate extracted values against the tax data schema",
                details={"fields": sorted(data.model_dump().keys())},
            )
        )
        return data, raw_text, logs

    def _regex_extract(self, text: str) -> dict[str, Decimal]:
        values: dict[str, Decimal] = {}
        for field, patterns in MONEY_PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
                if match:
                    values[field] = Decimal(match.group(1).replace(",", ""))
                    break
        return values

    def _extract_w2_layout(
        self,
        image: Image.Image,
        ocr_text: str,
        embedded_text: str,
        page_number: int,
    ) -> tuple[dict[str, Any], list[SourceEvidence]]:
        values: dict[str, Any] = {}
        evidence: list[SourceEvidence] = []
        lines = [line.strip() for line in ocr_text.splitlines() if line.strip()]

        for line in lines:
            if re.search(r"\d{2}-\d{7}", line):
                amounts = re.findall(r"\d[\d,]*\.\s*\d+", line)
                if len(amounts) >= 2:
                    values["wages"] = self._decimal(amounts[0])
                    values["federal_tax_withheld"] = self._decimal(amounts[1])
                    evidence.extend(
                        [
                            self._evidence(
                                "wages",
                                amounts[0],
                                page_number,
                                "w2-box-1-ocr",
                                0.90,
                            ),
                            self._evidence(
                                "federal_tax_withheld",
                                amounts[1],
                                page_number,
                                "w2-box-2-ocr",
                                0.90,
                            ),
                        ]
                    )
                    break

        employer = self._first_clean_line(
            self._crop_text(image, (0.02, 0.345, 0.53, 0.45))
        )
        if employer:
            values["employer_name"] = employer
            evidence.append(
                self._evidence(
                    "employer_name",
                    employer,
                    page_number,
                    "w2-employer-region-ocr",
                    0.96,
                )
            )

        employee = self._first_clean_line(
            self._crop_text(image, (0.02, 0.47, 0.53, 0.60))
        )
        if employee:
            values["employee_name"] = employee
            evidence.append(
                self._evidence(
                    "employee_name",
                    employee,
                    page_number,
                    "w2-employee-region-ocr",
                    0.95,
                )
            )

        state_text = self._crop_text(image, (0.41, 0.58, 0.53, 0.66))
        state_amounts = [
            self._decimal(value)
            for value in re.findall(r"\d[\d,]*\.\s*\d+", state_text)
        ]
        if state_amounts:
            values["state_tax_withheld"] = sum(state_amounts, Decimal("0"))
            evidence.append(
                self._evidence(
                    "state_tax_withheld",
                    " + ".join(str(value) for value in state_amounts),
                    page_number,
                    "w2-box-17-ocr",
                    0.91,
                )
            )

        year_match = re.search(
            r"Form\s+W-?2[\s\S]{0,80}?\b(20\d{2})\b",
            embedded_text,
            flags=re.IGNORECASE,
        )
        if not year_match:
            years = re.findall(r"\b(20\d{2})\b", embedded_text)
            year_match = re.match(r"(20\d{2})", years[-1]) if years else None
        if year_match:
            values["tax_year"] = int(year_match.group(1))
            evidence.append(
                self._evidence(
                    "tax_year",
                    year_match.group(1),
                    page_number,
                    "pdf-text",
                    0.99,
                )
            )
        return values, evidence

    def _crop_text(
        self, image: Image.Image, region: tuple[float, float, float, float]
    ) -> str:
        width, height = image.size
        left, top, right, bottom = region
        crop = image.crop(
            (
                int(width * left),
                int(height * top),
                int(width * right),
                int(height * bottom),
            )
        )
        return self.ocr.extract(crop, "").text

    @staticmethod
    def _first_clean_line(text: str) -> str:
        rejected = (
            "employee's",
            "employer's",
            "address",
            "control number",
            "state",
            "form w-2",
        )
        for line in (item.strip() for item in text.splitlines()):
            lowered = line.lower()
            if (
                line
                and not any(value in lowered for value in rejected)
                and not re.search(r"\d{4,}", line)
                and len(re.findall(r"[A-Za-z]+", line)) >= 2
            ):
                return re.sub(r"\s{2,}", " ", line)
        return ""

    @staticmethod
    def _decimal(value: str) -> Decimal:
        return Decimal(re.sub(r"\s+", "", value).replace(",", ""))

    @staticmethod
    def _evidence(
        field: str,
        raw_text: str,
        page: int,
        source: str,
        confidence: float,
    ) -> SourceEvidence:
        return SourceEvidence(
            field=field,
            page=page,
            raw_text=raw_text,
            source=source,
            confidence=confidence,
        )

    @staticmethod
    def _model_confidence(value: Any, field: str) -> float:
        if isinstance(value, dict):
            candidate = value.get(field, 0.8)
        elif isinstance(value, (int, float, str)):
            candidate = value
        else:
            candidate = 0.8
        try:
            confidence = float(candidate)
        except (TypeError, ValueError):
            confidence = 0.8
        if confidence > 1 and confidence <= 100:
            confidence /= 100
        return min(max(confidence, 0), 1)
