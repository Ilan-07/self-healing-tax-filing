"""High-accuracy overrides: delegate selected states to the ``tenforty`` engine.

Imported last by ``app.state_rules.states`` so these registrations overwrite the
hand-encoded reference packs for the same ``(state, year)``. Each keeps its
reference pack as a fallback (used only if tenforty errors or is unavailable).

These are marked ``verified=True``: the state tax is produced by tenforty's
OpenTaxSolver engine and pinned by golden-case tests
(``tests/unit/test_state_rules_tenforty.py``). California is additionally
validated by tenforty against professional tax software; NY/NJ/AZ rely on
tenforty's formula/property testing plus our golden cases.
"""

from app.state_rules.registry import register
from app.state_rules.states import (
    arizona_2025,
    california_2025,
    new_jersey_2025,
    new_york_2025,
)
from app.state_rules.tenforty_backend import (
    TenfortyStatePack,
    nj_income_kwargs,
    ny_pension_exclusion,
)

_SOURCE = "tenforty (OpenTaxSolver) 2025; golden-case verified"
_NY_SOURCE = _SOURCE + "; +NY 612(c)(3-a) $20k pension exclusion (age 59.5+)"
_NJ_SOURCE = _SOURCE + "; +NJ 54A:6-10/6-15 retirement + other-income exclusion"

register(
    TenfortyStatePack(
        state="CA", year=2025, source=_SOURCE, verified=True,
        fallback=california_2025.PACK,
    )
)
register(
    TenfortyStatePack(
        state="NY", year=2025, source=_NY_SOURCE, verified=True,
        fallback=new_york_2025.PACK, pension_exclusion=ny_pension_exclusion,
    )
)
register(
    TenfortyStatePack(
        state="NJ", year=2025, source=_NJ_SOURCE, verified=True,
        fallback=new_jersey_2025.PACK, income_router=nj_income_kwargs,
    )
)
register(
    TenfortyStatePack(
        state="AZ", year=2025, source=_SOURCE, verified=True,
        fallback=arizona_2025.PACK,
    )
)
