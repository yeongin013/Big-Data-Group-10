"""Support ratios are converted exactly via Decimal, not rounded binary floats."""
from decimal import Decimal, InvalidOperation, ROUND_CEILING


def validate_min_count(value):
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError("min_count must be a positive integer")


def support_to_count(n_baskets, min_support):
    if isinstance(n_baskets, bool) or not isinstance(n_baskets, int) or n_baskets < 1:
        raise ValueError("A support ratio requires at least one basket")
    try:
        support = Decimal(str(min_support))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("Invalid support ratio") from exc
    if not support.is_finite() or not Decimal(0) < support <= Decimal(1):
        raise ValueError("min_support must be in (0, 1]")
    return int((support * n_baskets).to_integral_value(rounding=ROUND_CEILING))
