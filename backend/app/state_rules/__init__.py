"""State income-tax rule packs (the documented per-state extension point).

State tax is opt-in: a single flat rate cannot honestly model 40+ state systems,
so the engine only computes a state amount when a rule pack is installed for the
taxpayer's ``(state, year)`` or an explicit flat ``state_tax_rate`` is supplied.
Importing this package registers every installed pack with the registry, so
``get_state_pack(state, year)`` can resolve them.

To add a state, see :mod:`app.state_rules.states`.
"""

from app.state_rules.base import (
    BracketStatePack,
    FederalContext,
    FlatStatePack,
    StateResult,
    StateRulePack,
)
from app.state_rules.registry import all_packs, get_state_pack, register
from app.state_rules import states  # noqa: F401  (side-effect: register packs)

__all__ = [
    "BracketStatePack",
    "FederalContext",
    "FlatStatePack",
    "StateResult",
    "StateRulePack",
    "all_packs",
    "get_state_pack",
    "register",
]
