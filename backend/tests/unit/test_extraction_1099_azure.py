from decimal import Decimal
from types import SimpleNamespace

from app.services.extraction.azure_client import _map_document


def _field(amount=None, content="", confidence=0.95, obj=None):
    ns = SimpleNamespace(content=content, confidence=confidence, value_object=obj)
    ns.value_currency = SimpleNamespace(amount=amount) if amount is not None else None
    return ns


def test_azure_document_mapping():
    doc = SimpleNamespace(
        fields={
            "WagesTipsAndOtherCompensation": _field(amount=85000),
            "FederalIncomeTaxWithheld": _field(amount=11000),
            "Employer": _field(obj={"IdNumber": _field(content="12-3456789")}),
            "Employee": _field(
                obj={"SocialSecurityNumber": _field(content="123-45-6789")}
            ),
            "TaxYear": _field(content="2025"),
        }
    )
    parsed = _map_document(doc)
    assert parsed["box1_wages"] == Decimal("85000")
    assert parsed["box2_federal_withheld"] == Decimal("11000")
    assert parsed["employer_ein"] == "12-3456789"
    assert parsed["ssn"] == "123-45-6789"
    assert parsed["tax_year"] == 2025
