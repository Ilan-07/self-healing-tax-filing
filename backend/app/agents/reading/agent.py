from __future__ import annotations

import re
from decimal import Decimal
from pathlib import Path
from typing import Any

from app.schemas import AuditEntry, SourceEvidence, TaxpayerData, mask_ssn
from app.services.chroma.service import ChromaService
from app.services.documents.service import DocumentService
from app.services.extraction import LabelAnchoredW2Parser, ParsedW2, W2Extractor
from app.services.extraction.base import BOX_TO_TAXPAYER_FIELD
from app.services.extraction.info_returns import extract_information_returns
from app.services.ocr.service import OCRService
from app.services.ollama.client import OllamaClient


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
        w2_extractor: W2Extractor | None = None,
    ):
        self.documents = documents
        self.ocr = ocr
        self.ollama = ollama
        self.default_state_tax_rate = default_state_tax_rate
        self.memory = memory
        self.w2_extractor = w2_extractor or LabelAnchoredW2Parser()

    # Income fields that are summed when merging multiple uploaded documents.
    _SUM_FIELDS = (
        "taxable_interest",
        "tax_exempt_interest",
        "ordinary_dividends",
        "qualified_dividends",
        "long_term_capital_gain",
        "short_term_capital_gain",
        "self_employment_income",
        "other_income",
        "adjustments",
        "itemized_deductions",
        "estimated_payments",
        "qualified_tuition",
        "retirement_contributions",
        "amt_preference_items",
    )

    def run_many(
        self, paths: list[Path], scale: int = 2
    ) -> tuple[TaxpayerData, str, list[AuditEntry]]:
        """Read several documents and merge them into one taxpayer return.

        W-2s are concatenated (then re-aggregated for the excess-SS credit) and
        income line items are summed, so a taxpayer can upload multiple forms.
        """
        datas: list[TaxpayerData] = []
        texts: list[str] = []
        logs: list[AuditEntry] = []
        for path in paths:
            data, text, page_logs = self.run(path, scale=scale)
            datas.append(data)
            texts.append(text)
            logs.extend(page_logs)
        merged = self._merge(datas)
        if len(datas) > 1:
            logs.append(
                AuditEntry(
                    agent=self.name,
                    action="merge_documents",
                    reason="Combine W-2s and income across uploaded documents",
                    details={
                        "documents": len(datas),
                        "employer_count": merged.employer_count,
                    },
                )
            )
        return merged, "\n".join(texts), logs

    def _merge(self, datas: list[TaxpayerData]) -> TaxpayerData:
        if len(datas) == 1:
            return datas[0]
        merged = datas[0].model_copy(deep=True)
        merged.w2s = [w2 for d in datas for w2 in d.w2s]
        for field in self._SUM_FIELDS:
            merged_value = sum(
                (getattr(d, field) for d in datas[1:]), getattr(merged, field)
            )
            setattr(merged, field, merged_value)
        for d in datas[1:]:
            merged.evidence.extend(d.evidence)
            for key, value in d.field_confidence.items():
                merged.field_confidence[key] = max(
                    merged.field_confidence.get(key, 0.0), value
                )
            # Identity / return-level fields: fill from later docs if missing.
            merged.employee_name = merged.employee_name or d.employee_name
            merged.ssn = merged.ssn or d.ssn
            merged.qualifying_children = max(
                merged.qualifying_children, d.qualifying_children
            )
            merged.other_dependents = max(
                merged.other_dependents, d.other_dependents
            )
            merged.aotc_students = max(merged.aotc_students, d.aotc_students)
        merged.aggregate_w2s()
        return merged

    def run(
        self, path: Path, scale: int = 2
    ) -> tuple[TaxpayerData, str, list[AuditEntry]]:
        pages = self.documents.load(path, scale=scale)
        merged: dict[str, Any] = {}
        all_text: list[str] = []
        evidence: list[SourceEvidence] = []
        confidences: dict[str, float] = {}
        logs: list[AuditEntry] = []
        parsed_w2s: list[ParsedW2] = []
        info_totals: dict[str, tuple[Decimal, float]] = {}

        for page in pages:
            image_ocr = self.ocr.extract(page.image, "")
            ocr_text = image_ocr.text or page.embedded_text
            combined_text = "\n".join(
                value
                for value in (image_ocr.text, page.embedded_text)
                if value.strip()
            )
            all_text.append(combined_text)
            # Parse info returns from the single-source page text (not the
            # OCR+embedded concatenation) so multi-form summing never
            # double-counts the same document.
            for field, (value, conf) in extract_information_returns(ocr_text).items():
                running = info_totals.get(field, (Decimal("0"), conf))
                info_totals[field] = (running[0] + value, conf)
            vision = self.ollama.extract_tax_fields(page.image, combined_text)
            vision_confidence = vision.get("field_confidence", {})
            for key, value in vision.items():
                if key != "field_confidence" and value not in (None, "", {}):
                    merged.setdefault(key, value)
            for field in (
                "employee_name",
                "employer_name",
                "ssn",
                "wages",
                "federal_tax_withheld",
                "state_tax_withheld",
                "taxable_interest",
                "ordinary_dividends",
                "qualified_dividends",
                "long_term_capital_gain",
                "short_term_capital_gain",
                "self_employment_income",
                "other_income",
                "itemized_deductions",
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
            try:
                parsed_w2s.extend(
                    self.w2_extractor.parse(
                        ocr_text=ocr_text or combined_text, image=page.image
                    )
                )
            except NotImplementedError as exc:
                logs.append(
                    AuditEntry(
                        agent=self.name,
                        action="extract_w2",
                        reason="Configured W-2 extractor unavailable",
                        details={"error": str(exc)},
                    )
                )

        # Fold parsed W-2s into the result, collapsing duplicate copies of the
        # same form (Copy B/C/2) so income is not multiplied.
        parsed_w2s = _dedupe_w2s([pw for pw in parsed_w2s if _has_w2_data(pw)])
        if parsed_w2s:
            merged["w2s"] = [pw.w2.model_dump(mode="json") for pw in parsed_w2s]
            for pw in parsed_w2s:
                if pw.ssn:
                    merged.setdefault("ssn", pw.ssn)
                if pw.tax_year:
                    merged.setdefault("tax_year", pw.tax_year)
                if pw.employee_name:
                    merged.setdefault("employee_name", pw.employee_name)
            # Grounding evidence keyed by the taxpayer-level field each box feeds.
            for box, tp_field in BOX_TO_TAXPAYER_FIELD.items():
                hits = [pw for pw in parsed_w2s if box in pw.confidences]
                if hits:
                    conf = max(pw.confidences[box] for pw in hits)
                    evidence = [e for e in evidence if e.field != tp_field]
                    evidence.append(
                        SourceEvidence(
                            field=tp_field,
                            raw_text=str(
                                sum(getattr(pw.w2, box) for pw in hits)
                            ),
                            source=self.w2_extractor.name,
                            confidence=conf,
                        )
                    )
                    confidences[tp_field] = conf
            logs.append(
                AuditEntry(
                    agent=self.name,
                    action="extract_w2",
                    reason=f"W-2 extraction via {self.w2_extractor.name}",
                    details={"w2_count": len(parsed_w2s)},
                )
            )

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
        if not merged.get("ssn"):
            ssn_match = re.search(r"\b(\d{3}-\d{2}-\d{4})\b", raw_text)
            if ssn_match:
                merged["ssn"] = ssn_match.group(1)
                confidences["ssn"] = 0.8
                evidence.append(
                    SourceEvidence(
                        field="ssn",
                        # Store masked: full SSNs must not leak into the audit log.
                        raw_text=mask_ssn(ssn_match.group(1)),
                        source="regex",
                        confidence=0.8,
                    )
                )

        # Typed information returns (1099 family / K-1 / 1098), summed across
        # forms/pages and grounded like the W-2 boxes. Structured values are
        # authoritative over the generic vision pass.
        for field, (value, conf) in info_totals.items():
            merged[field] = value
            confidences[field] = conf
            evidence = [e for e in evidence if e.field != field]
            evidence.append(
                SourceEvidence(
                    field=field,
                    raw_text=str(value),
                    source="info-return",
                    confidence=conf,
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
        # Fold multi-W-2 line items into the scalar wage/withholding totals
        # (and set employer_count, which drives the excess-SS credit).
        data.aggregate_w2s()
        logs.append(
            AuditEntry(
                agent=self.name,
                action="structure_json",
                reason="Validate extracted values against the tax data schema",
                details={
                    "fields": sorted(data.model_dump().keys()),
                    "employer_count": data.employer_count,
                },
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


def _has_w2_data(parsed: ParsedW2) -> bool:
    """Keep only W-2 segments that actually yielded a wage or withholding box."""
    return bool(parsed.confidences) and parsed.w2.box1_wages > Decimal("0")


_W2_BOXES = (
    "box1_wages",
    "box2_federal_withheld",
    "box3_ss_wages",
    "box4_ss_withheld",
    "box5_medicare_wages",
    "box6_medicare_withheld",
    "box17_state_withheld",
)


def _w2_filled(w2) -> int:
    return sum(1 for b in _W2_BOXES if getattr(w2, b) > Decimal("0"))


def _dedupe_w2s(parsed: list[ParsedW2]) -> list[ParsedW2]:
    """Collapse duplicate W-2 copies (Copy B/C/2 of the same form) so income is
    not multiplied. Copies share an employer EIN and box-1 wages; keep the most
    complete copy of each. Distinct employers (different EIN) are preserved.
    """
    best: dict[tuple[str, object], ParsedW2] = {}
    for pw in parsed:
        key = (pw.w2.employer_ein, pw.w2.box1_wages)
        if key not in best or _w2_filled(pw.w2) > _w2_filled(best[key].w2):
            best[key] = pw
    return list(best.values())
