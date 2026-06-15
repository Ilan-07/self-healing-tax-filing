from decimal import Decimal

from app.schemas import FilingStatus


STANDARD_DEDUCTIONS = {
    FilingStatus.SINGLE: Decimal("12000"),
    FilingStatus.MARRIED_JOINTLY: Decimal("24000"),
    FilingStatus.MARRIED_SEPARATELY: Decimal("12000"),
    FilingStatus.HEAD_OF_HOUSEHOLD: Decimal("18000"),
}

BRACKETS = {
    FilingStatus.SINGLE: [
        (Decimal("9525"), Decimal("0.10")),
        (Decimal("38700"), Decimal("0.12")),
        (Decimal("82500"), Decimal("0.22")),
        (Decimal("157500"), Decimal("0.24")),
        (Decimal("200000"), Decimal("0.32")),
        (Decimal("500000"), Decimal("0.35")),
        (None, Decimal("0.37")),
    ],
    FilingStatus.MARRIED_JOINTLY: [
        (Decimal("19050"), Decimal("0.10")),
        (Decimal("77400"), Decimal("0.12")),
        (Decimal("165000"), Decimal("0.22")),
        (Decimal("315000"), Decimal("0.24")),
        (Decimal("400000"), Decimal("0.32")),
        (Decimal("600000"), Decimal("0.35")),
        (None, Decimal("0.37")),
    ],
    FilingStatus.MARRIED_SEPARATELY: [
        (Decimal("9525"), Decimal("0.10")),
        (Decimal("38700"), Decimal("0.12")),
        (Decimal("82500"), Decimal("0.22")),
        (Decimal("157500"), Decimal("0.24")),
        (Decimal("200000"), Decimal("0.32")),
        (Decimal("300000"), Decimal("0.35")),
        (None, Decimal("0.37")),
    ],
    FilingStatus.HEAD_OF_HOUSEHOLD: [
        (Decimal("13600"), Decimal("0.10")),
        (Decimal("51800"), Decimal("0.12")),
        (Decimal("82500"), Decimal("0.22")),
        (Decimal("157500"), Decimal("0.24")),
        (Decimal("200000"), Decimal("0.32")),
        (Decimal("500000"), Decimal("0.35")),
        (None, Decimal("0.37")),
    ],
}
