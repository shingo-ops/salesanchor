"""Parse a single evidenced stock quantity without normalizing other fields."""

import re
from decimal import Decimal

_TRANSLATION = str.maketrans("０１２３４５６７８９．，", "0123456789.,")
_NUMBER = re.compile(r"(?:[0-9]+|[0-9]{1,3}(?:,[0-9]{3})+)(?:\.[0-9]{1,2})?")
_LIMIT = Decimal("999999999999.99")


def parse_stock_quantity(raw: str, known_unit_aliases: frozenset[str]) -> dict:
    """Return absent, an exact nonnegative value, or a review requirement."""
    if "" in known_unit_aliases:
        raise ValueError("empty unit alias")
    text = raw.strip()
    result = {"presence": "review", "value": None, "unit_alias": None, "review_reason": "unsupported_quantity"}
    if not text:
        return {"presence": "absent", "value": None, "unit_alias": None, "review_reason": None}
    unit = None
    for alias in sorted(known_unit_aliases, key=lambda value: (-len(value), value)):
        if text.endswith(alias):
            unit = alias
            text = text[:-len(alias)].rstrip()
            break
    if text.startswith("残り"):
        text = text[2:].lstrip()
    elif text.startswith("残"):
        text = text[1:].lstrip()
    number = text.translate(_TRANSLATION)
    if len(number) == 1 and "①" <= number <= "⑳":
        value = Decimal(ord(number) - ord("①") + 1)
    elif _NUMBER.fullmatch(number):
        value = Decimal(number.replace(",", ""))
    else:
        return result
    if value > _LIMIT:
        return result
    return {"presence": "value", "value": value, "unit_alias": unit, "review_reason": None}
