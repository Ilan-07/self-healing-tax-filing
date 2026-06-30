"""Registry of installed state rule packs, keyed by ``(state, year)``.

Unlike the federal registry, a missing key is the normal case (most of the 40+
states are not installed), so :func:`get_state_pack` returns ``None`` rather than
raising -- the engine falls back to the flat ``state_tax_rate``.
"""

from __future__ import annotations

from app.state_rules.base import StateRulePack

_REGISTRY: dict[tuple[str, int], StateRulePack] = {}


def register(pack: StateRulePack) -> StateRulePack:
    _REGISTRY[(pack.state.upper(), pack.year)] = pack
    return pack


def get_state_pack(state: str, year: int) -> StateRulePack | None:
    if not state:
        return None
    return _REGISTRY.get((state.upper(), year))


def all_packs() -> dict[tuple[str, int], StateRulePack]:
    return dict(_REGISTRY)
