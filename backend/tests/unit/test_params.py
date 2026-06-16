import app.tax_rules  # noqa: F401  (registers all years)
from app.tax_rules.params import _REGISTRY, get_params
from app.tax_rules.validation import validate_all


def test_all_registered_years_are_structurally_consistent():
    assert validate_all(_REGISTRY) == []


def test_2025_is_marked_verified():
    assert get_params(2025).verified is True
