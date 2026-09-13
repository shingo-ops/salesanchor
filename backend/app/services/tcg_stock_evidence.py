"""Strict, source-preserving validation of the stock evidence v5 envelope."""

import json
import math
from uuid import UUID

_RAW_FIELDS = frozenset({
    "raw_product_name", "raw_quantity", "raw_price", "raw_unit",
    "raw_state", "raw_memo", "raw_work_name",
})
_ITEM_KEYS = _RAW_FIELDS | {
    "resolved_work_id", "field_evidence", "shipping_label", "shipping_evidence", "clauses",
}


class StockEvidenceError(ValueError):
    """Expose only a stable code and item index, never source or response text."""

    def __init__(self, code: str, item_index: int | None = None):
        self.code = code
        self.item_index = item_index
        super().__init__(code)


def _unique_object(pairs: list) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError("nonfinite number")


def _finite_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError("nonfinite number")
    return parsed


def _shape(value: object, keys: set | frozenset, index: int | None) -> dict:
    if not isinstance(value, dict) or value.keys() != keys:
        raise StockEvidenceError("invalid_shape", index)
    return value


def _spans(text: str, spans: object, lines: list[str], index: int) -> list[int]:
    if not isinstance(spans, list):
        raise StockEvidenceError("invalid_shape", index)
    if bool(text) != bool(spans):
        raise StockEvidenceError("invalid_evidence", index)
    fragments = []
    line_numbers = []
    previous = (0, 0)
    for span in spans:
        _shape(span, {"line", "start", "end"}, index)
        if any(type(span[key]) is not int for key in ("line", "start", "end")):
            raise StockEvidenceError("invalid_shape", index)
        line, start, end = span["line"], span["start"], span["end"]
        if not (1 <= line <= len(lines) and 0 <= start < end <= len(lines[line - 1])):
            raise StockEvidenceError("invalid_evidence", index)
        if (line, start) < previous:
            raise StockEvidenceError("invalid_evidence", index)
        previous = (line, end)
        fragments.append(lines[line - 1][start:end])
        line_numbers.append(line)
    if "\n".join(fragments) != text:
        raise StockEvidenceError("invalid_evidence", index)
    return line_numbers


def validate_stock_evidence(
    response_text: str, source_text: str, allowed_work_ids: frozenset[str],
) -> list[dict]:
    """Reject the entire envelope when any item has invalid shape or evidence."""
    parsed = None
    invalid_json = False
    try:
        parsed = json.loads(
            response_text, object_pairs_hook=_unique_object,
            parse_constant=_reject_constant, parse_float=_finite_float,
        )
    except (ValueError, RecursionError):
        invalid_json = True
    # Raise outside the handler so decoder exceptions containing raw text are not chained.
    if invalid_json:
        raise StockEvidenceError("invalid_json")
    parsed = _shape(parsed, {"format_version", "items"}, None)
    if type(parsed["format_version"]) is not int or parsed["format_version"] != 5:
        raise StockEvidenceError("invalid_shape")
    if not isinstance(parsed["items"], list):
        raise StockEvidenceError("invalid_shape")
    lines = source_text.split("\n")
    validated = []
    for index, item in enumerate(parsed["items"]):
        _shape(item, _ITEM_KEYS, index)
        if any(not isinstance(item[key], str) for key in _RAW_FIELDS | {"shipping_label"}):
            raise StockEvidenceError("invalid_shape", index)
        if not item["raw_product_name"]:
            raise StockEvidenceError("invalid_evidence", index)
        work_id = item["resolved_work_id"]
        valid_work = work_id is None
        if isinstance(work_id, str) and work_id in allowed_work_ids:
            try:
                UUID(work_id)
                valid_work = True
            except ValueError:
                pass
        if not valid_work:
            raise StockEvidenceError("invalid_work_id", index)
        _shape(item["field_evidence"], _RAW_FIELDS, index)
        positions = []
        for key in sorted(_RAW_FIELDS):
            positions.extend(_spans(item[key], item["field_evidence"][key], lines, index))
        positions.extend(_spans(item["shipping_label"], item["shipping_evidence"], lines, index))
        if not isinstance(item["clauses"], list):
            raise StockEvidenceError("invalid_shape", index)
        for clause in item["clauses"]:
            _shape(clause, {"text", "spans"}, index)
            if not isinstance(clause["text"], str):
                raise StockEvidenceError("invalid_shape", index)
            positions.extend(_spans(clause["text"], clause["spans"], lines, index))
        validated.append({
            **item,
            "line_start": min(positions),
            "line_end": max(positions),
            "evidence_payload": {
                "format_version": 5,
                "field_evidence": item["field_evidence"],
                "shipping": {"label": item["shipping_label"], "evidence": item["shipping_evidence"]},
                "clauses": item["clauses"],
            },
        })
    return validated
