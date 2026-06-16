"""Federal tax rule sets.

Importing this package registers every installed tax year with the parameter
registry in :mod:`app.tax_rules.params` so ``get_params(year)`` can resolve them.
"""

from app.tax_rules import federal_2018, federal_2025  # noqa: F401  (side-effect: register)
from app.tax_rules.params import TaxYearParams, get_params

__all__ = ["TaxYearParams", "get_params", "federal_2018", "federal_2025"]
