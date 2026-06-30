"""Structural self-consistency checks for state rule packs.

Run over the whole registry in the test suite to catch transcription errors
(bad rates, non-monotonic brackets, a missing filing status) independently of
whether a pack is marked ``verified``.
"""

from __future__ import annotations

from app.schemas import FilingStatus
from app.state_rules.base import (
    BracketStatePack,
    FlatStatePack,
    StateRulePack,
)
from app.state_rules.registry import all_packs

_REQUIRED_STATUSES = (
    FilingStatus.SINGLE,
    FilingStatus.MARRIED_JOINTLY,
    FilingStatus.MARRIED_SEPARATELY,
    FilingStatus.HEAD_OF_HOUSEHOLD,
)


def validate_pack(p: StateRulePack) -> list[str]:
    issues: list[str] = []
    tag = f"{p.state} {p.year}"

    def note(cond: bool, msg: str) -> None:
        if not cond:
            issues.append(f"[{tag}] {msg}")

    note(len(p.state) == 2 and p.state.isalpha(), "state must be a 2-letter code")
    note(bool(p.source), "pack must cite a source")

    if isinstance(p, FlatStatePack):
        note(0 <= p.rate < 1, f"flat rate {p.rate} must be in [0, 1)")

    if isinstance(p, BracketStatePack):
        for fs in _REQUIRED_STATUSES:
            note(fs in p.brackets, f"brackets missing filing status {fs}")
        for fs, brackets in p.brackets.items():
            note(bool(brackets), f"{fs} has no brackets")
            last_upper = None
            prev_rate = None
            for i, (upper, rate) in enumerate(brackets):
                note(0 <= rate < 1, f"{fs} rate {rate} must be in [0, 1)")
                if i == len(brackets) - 1:
                    note(upper is None, f"{fs} brackets must end with an open band")
                else:
                    note(upper is not None, f"{fs} non-final band missing upper bound")
                    if upper is not None and last_upper is not None:
                        note(upper > last_upper, f"{fs} bracket bounds not increasing")
                    last_upper = upper
                if prev_rate is not None:
                    note(rate >= prev_rate, f"{fs} bracket rates not non-decreasing")
                prev_rate = rate

    return issues


def validate_all() -> list[str]:
    issues: list[str] = []
    for pack in all_packs().values():
        issues.extend(validate_pack(pack))
    return issues
