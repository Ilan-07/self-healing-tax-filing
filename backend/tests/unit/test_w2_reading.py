from unittest.mock import Mock

from PIL import Image

from app.agents.reading.agent import ReadingAgent
from app.services.ocr.service import OCRResult


def test_w2_layout_extracts_box_values_and_year():
    ocr = Mock()
    ocr.extract.side_effect = [
        OCRResult("Hernandez PLC LLC", 0.96, "tesseract"),
        OCRResult("Julie Marquez", 0.95, "tesseract"),
        OCRResult("5277.49\n5270.42", 0.91, "tesseract"),
    ]
    agent = ReadingAgent(Mock(), ocr, Mock(), 0.05)
    values, evidence = agent._extract_w2_layout(
        Image.new("RGB", (1224, 1584), "white"),
        "98-5183738 140348.11 17995.3",
        "Form W-2\n2018",
        1,
    )

    assert values["employee_name"] == "Julie Marquez"
    assert values["employer_name"] == "Hernandez PLC LLC"
    assert str(values["wages"]) == "140348.11"
    assert str(values["federal_tax_withheld"]) == "17995.3"
    assert str(values["state_tax_withheld"]) == "10547.91"
    assert values["tax_year"] == 2018
    assert {item.field for item in evidence} >= {
        "employee_name",
        "employer_name",
        "wages",
        "federal_tax_withheld",
        "state_tax_withheld",
        "tax_year",
    }


def test_scalar_model_confidence_is_normalized():
    assert ReadingAgent._model_confidence(95, "wages") == 0.95
    assert ReadingAgent._model_confidence(1, "wages") == 1
    assert ReadingAgent._model_confidence(
        {"wages": "0.87"}, "wages"
    ) == 0.87
    assert ReadingAgent._model_confidence("invalid", "wages") == 0.8
