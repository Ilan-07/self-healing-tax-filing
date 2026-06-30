"""Azure Document Intelligence ``prebuilt-tax.us.w2`` client.

Returns a ``ClientFn`` (image bytes -> list of W-2 dicts) suitable for
``CloudW2Extractor``. The Azure SDK is imported lazily so the project runs with
no cloud dependency unless this is actually configured.

Install + configure to enable:
    pip install azure-ai-documentintelligence
    AZURE_DI_ENDPOINT=...   AZURE_DI_KEY=...   W2_EXTRACTOR=azure
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any


# Azure W-2 field name -> our W2 box attribute.
_FIELD_MAP = {
    "WagesTipsAndOtherCompensation": "box1_wages",
    "FederalIncomeTaxWithheld": "box2_federal_withheld",
    "SocialSecurityWages": "box3_ss_wages",
    "SocialSecurityTaxWithheld": "box4_ss_withheld",
    "MedicareWagesAndTips": "box5_medicare_wages",
    "MedicareTaxWithheld": "box6_medicare_withheld",
}


def build_azure_w2_client(endpoint: str, key: str):
    """Return a callable mapping image bytes -> list[dict] of W-2 fields."""
    from azure.ai.documentintelligence import DocumentIntelligenceClient
    from azure.core.credentials import AzureKeyCredential

    client = DocumentIntelligenceClient(endpoint, AzureKeyCredential(key))

    def extract(image_bytes: bytes) -> list[dict[str, Any]]:
        poller = client.begin_analyze_document(
            "prebuilt-tax.us.w2", body=image_bytes
        )
        result = poller.result()
        return [_map_document(doc) for doc in (result.documents or [])]

    return extract


def _map_document(doc: Any) -> dict[str, Any]:
    fields = doc.fields or {}
    out: dict[str, Any] = {}
    for azure_name, box in _FIELD_MAP.items():
        value = _amount(fields.get(azure_name))
        if value is not None:
            out[box] = value
            out[f"{box}_confidence"] = _confidence(fields.get(azure_name))

    state_infos = fields.get("StateTaxInfos")
    if state_infos and getattr(state_infos, "value_array", None):
        total = Decimal("0")
        primary_state = ""
        most_tax = Decimal("-1")
        for item in state_infos.value_array:
            obj = item.value_object or {}
            tax = _amount(obj.get("StateIncomeTax"))
            if tax is not None:
                total += tax
                if tax > most_tax:
                    most_tax = tax
                    primary_state = _content(obj.get("State"))
        if total > 0:
            out["box17_state_withheld"] = total
        if primary_state:
            out["box15_state"] = primary_state

    employer = _obj(fields.get("Employer"))
    employee = _obj(fields.get("Employee"))
    out["employer_ein"] = _content(employer.get("IdNumber"))
    out["ssn"] = _content(employee.get("SocialSecurityNumber"))
    out["employee_name"] = _content(employee.get("Name"))
    year = _content(fields.get("TaxYear"))
    if year and year.isdigit():
        out["tax_year"] = int(year)
    return out


def _amount(field: Any) -> Decimal | None:
    if field is None:
        return None
    raw = getattr(field, "value_currency", None)
    if raw is not None and getattr(raw, "amount", None) is not None:
        return Decimal(str(raw.amount))
    content = _content(field)
    try:
        return Decimal(content.replace("$", "").replace(",", "")) if content else None
    except (InvalidOperation, ValueError):
        return None


def _confidence(field: Any) -> float:
    return float(getattr(field, "confidence", 0.0) or 0.0)


def _obj(field: Any) -> dict[str, Any]:
    return getattr(field, "value_object", None) or {}


def _content(field: Any) -> str:
    if field is None:
        return ""
    return str(getattr(field, "content", "") or "")
