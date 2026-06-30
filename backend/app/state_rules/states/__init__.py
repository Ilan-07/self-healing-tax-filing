"""Installed state rule packs.

Each module registers its pack with the registry by side effect on import. To
add a state, drop a ``<state>_<year>.py`` module here (use ``FlatStatePack`` or
``BracketStatePack`` from ``app.state_rules.base``, or a custom class for an
unusual base) and add it to the imports below.

Every pack currently ships ``verified=False``: the rates/brackets are
transcribed from the cited statutes/DOR tables but have not been reconciled
against the published 2025 returns in this environment. States with no income
tax (AK, FL, NV, SD, TX, WY, TN, WA) are intentionally absent -- ``get_state_pack``
returns ``None`` and the engine yields zero state tax.
"""

from app.state_rules.states import (  # noqa: F401  (side-effect: register)
    alabama_2025,
    arizona_2025,
    arkansas_2025,
    california_2025,
    colorado_2025,
    connecticut_2025,
    delaware_2025,
    district_of_columbia_2025,
    georgia_2025,
    hawaii_2025,
    idaho_2025,
    illinois_2025,
    indiana_2025,
    iowa_2025,
    kansas_2025,
    kentucky_2025,
    louisiana_2025,
    maine_2025,
    maryland_2025,
    massachusetts_2025,
    michigan_2025,
    minnesota_2025,
    mississippi_2025,
    missouri_2025,
    montana_2025,
    nebraska_2025,
    new_hampshire_2025,
    new_jersey_2025,
    new_mexico_2025,
    new_york_2025,
    north_carolina_2025,
    north_dakota_2025,
    ohio_2025,
    oklahoma_2025,
    oregon_2025,
    pennsylvania_2025,
    rhode_island_2025,
    south_carolina_2025,
    utah_2025,
    vermont_2025,
    virginia_2025,
    west_virginia_2025,
    wisconsin_2025,
)

# Imported last: overrides selected states with high-accuracy tenforty-backed
# packs (overwrites the reference registrations above).
from app.state_rules.states import _tenforty_overrides  # noqa: E402,F401

__all__ = [
    "alabama_2025",
    "arizona_2025",
    "arkansas_2025",
    "california_2025",
    "colorado_2025",
    "connecticut_2025",
    "delaware_2025",
    "district_of_columbia_2025",
    "georgia_2025",
    "hawaii_2025",
    "idaho_2025",
    "illinois_2025",
    "indiana_2025",
    "iowa_2025",
    "kansas_2025",
    "kentucky_2025",
    "louisiana_2025",
    "maine_2025",
    "maryland_2025",
    "massachusetts_2025",
    "michigan_2025",
    "minnesota_2025",
    "mississippi_2025",
    "missouri_2025",
    "montana_2025",
    "nebraska_2025",
    "new_hampshire_2025",
    "new_jersey_2025",
    "new_mexico_2025",
    "new_york_2025",
    "north_carolina_2025",
    "north_dakota_2025",
    "ohio_2025",
    "oklahoma_2025",
    "oregon_2025",
    "pennsylvania_2025",
    "rhode_island_2025",
    "south_carolina_2025",
    "utah_2025",
    "vermont_2025",
    "virginia_2025",
    "west_virginia_2025",
    "wisconsin_2025",
]
