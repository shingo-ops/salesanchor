"""Contract examples for source-preserving stock evidence validation."""

import copy
import io
import json
import logging
import traceback
import unittest

from app.services.tcg_stock_evidence import StockEvidenceError, validate_stock_evidence

FIELDS = ("raw_product_name", "raw_quantity", "raw_price", "raw_unit", "raw_state", "raw_memo", "raw_work_name")
WORK_ID = "00000000-0000-0000-0000-000000000001"


def span(line=1, start=0, end=1):
    return {"line": line, "start": start, "end": end}


def item(name="A", spans=None):
    result = {key: "" for key in FIELDS}
    result.update(raw_product_name=name, resolved_work_id=None,
                  field_evidence={key: [] for key in FIELDS},
                  shipping_label="", shipping_evidence=[], clauses=[])
    result["field_evidence"]["raw_product_name"] = [span()] if spans is None else spans
    return result


def encode(items):
    return json.dumps({"format_version": 5, "items": items}, ensure_ascii=False)


class StockEvidenceTests(unittest.TestCase):
    def test_source_evidence(self):
        cases = [("A", item()), ("😀A", item("A", [span(start=1, end=2)])),
                 ("A\r\nB", item("A\r\nB", [span(end=2), span(line=2)]))]
        for source, entry in cases:
            with self.subTest(source=source):
                raw = encode([entry])
                saved = copy.deepcopy(entry)
                result = validate_stock_evidence(raw, source, frozenset())
                self.assertEqual(result[0]["raw_product_name"], entry["raw_product_name"])
                self.assertEqual(result[0]["line_start"], 1)
                self.assertEqual(result[0]["line_end"], len(source.split("\n")))
                self.assertEqual(result[0]["evidence_payload"], {
                    "format_version": 5, "field_evidence": entry["field_evidence"],
                    "shipping": {"label": "", "evidence": []}, "clauses": [],
                })
                self.assertEqual(result, validate_stock_evidence(raw, source, frozenset()))
                self.assertEqual(entry, saved)
        entries = [item(), item()]
        for i, entry in enumerate(entries):
            entry.update(shipping_label="発送分" + "①②"[i], shipping_evidence=[span(i + 2, 0, 4)])
            entry["resolved_work_id"] = WORK_ID
        result = validate_stock_evidence(encode(entries), "A\n発送分①\n発送分②", frozenset({WORK_ID}))
        self.assertEqual([row["line_end"] for row in result], [2, 3])
        self.assertEqual(result[0]["resolved_work_id"], WORK_ID)
        source = "商品A\n3\n100\nBOX\n完売\n追加予定あり\n作品A\n完売、追加予定あり"
        values = source.split("\n")
        entry = item()
        for line, field in enumerate(FIELDS, 1):
            entry[field] = values[line - 1]
            entry["field_evidence"][field] = [span(line, 0, len(values[line - 1]))]
        entry["clauses"] = [{"text": values[7], "spans": [span(8, 0, len(values[7]))]}]
        result = validate_stock_evidence(encode([entry]), source, frozenset())
        for field in FIELDS:
            self.assertEqual(result[0][field], entry[field])
        self.assertEqual(result[0]["evidence_payload"]["clauses"], entry["clauses"])
        self.assertEqual((result[0]["line_start"], result[0]["line_end"]), (1, 8))

    def test_invalid_evidence(self):
        bad = []
        for field, value in [("extra", ""), ("raw_price", 0), ("resolved_work_id", WORK_ID),
                             ("raw_product_name", "B"), ("raw_product_name", "")]:
            entry = item()
            entry[field] = value
            bad.append(entry)
        entry = item()
        del entry["raw_price"]
        bad.append(entry)
        for spans in [[span(line=True)], [span(start=False)], [span(line=0)],
                      [span(start=1, end=0)], [span(end=2)], [span(), span()],
                      [span(line=2), span()], [span(end=2), span(start=1, end=2)], []]:
            bad.append(item(spans=spans))
        entry = item()
        entry["field_evidence"]["raw_memo"] = [span()]
        bad.append(entry)
        entry = item()
        entry["clauses"] = [{"text": "A", "spans": [span()], "extra": True}]
        bad.append(entry)
        for entry in bad:
            with self.subTest(entry=entry):
                with self.assertRaises(StockEvidenceError) as caught:
                    validate_stock_evidence(encode([item(), entry]), "A", frozenset())
                self.assertEqual(caught.exception.item_index, 1)
        for payload in [
            '{"format_version":5,"format_version":5,"items":[]}',
            '{"format_version":5,"items":[],"x":NaN}',
            '{"format_version":5,"items":[],"x":1e999}',
            '{"format_version":5,"items":[]', '```json\n{}\n```',
            '{"format_version":5,"items":[],"extra":0}',
            '{"format_version":true,"items":[]}', '{}',
            encode([item()]).replace('"start": 0', '"start": 0, "start": 0'),
        ]:
            with self.subTest(payload=payload), self.assertRaises(StockEvidenceError):
                validate_stock_evidence(payload, "A", frozenset())

        for source, entry in [
            ("A\nB", item("B\nA", [span(2), span(1)])),
            ("ABC", item("AB\nBC", [span(1, 0, 2), span(1, 1, 3)])),
        ]:
            with self.subTest(source=source), self.assertRaises(StockEvidenceError) as caught:
                validate_stock_evidence(encode([entry]), source, frozenset())
            self.assertEqual(caught.exception.code, "invalid_evidence")
        source = "商品A\n3\n100\nBOX\n完売\n追加予定あり\n作品A\n完売、追加予定あり"
        values = source.split("\n")
        entry = item()
        for line, field in enumerate(FIELDS, 1):
            entry[field] = values[line - 1]
            entry["field_evidence"][field] = [span(line, 0, len(values[line - 1]))]
        entry["clauses"] = [{"text": values[7], "spans": [span(8, 0, len(values[7]))]}]
        for field in (*FIELDS, "clauses"):
            modified = copy.deepcopy(entry)
            if field == "clauses":
                modified[field][0]["text"] += "違"
            else:
                modified[field] += "違"
            with self.subTest(field=field), self.assertRaises(StockEvidenceError) as caught:
                validate_stock_evidence(encode([modified]), source, frozenset())
            self.assertEqual(caught.exception.code, "invalid_evidence")
            self.assertEqual(caught.exception.item_index, 0)

    def test_empty_and_confidentiality(self):
        self.assertEqual(validate_stock_evidence(encode([]), "SECRET_SOURCE", frozenset()), [])
        output = io.StringIO()
        handler = logging.StreamHandler(output)
        logger = logging.getLogger()
        logger.addHandler(handler)
        try:
            for payload in ['SECRET_RESPONSE', encode([item("SECRET_RESPONSE")])]:
                with self.assertRaises(StockEvidenceError) as caught:
                    validate_stock_evidence(payload, "SECRET_SOURCE", frozenset())
                error = caught.exception
                self.assertIn(error.code, {"invalid_json", "invalid_evidence"})
                rendered = str(error) + repr(error) + "".join(traceback.format_exception(error))
                self.assertNotIn("SECRET_SOURCE", rendered)
                self.assertNotIn("SECRET_RESPONSE", rendered)
                self.assertIsNone(error.__context__)
                self.assertIsNone(error.__cause__)
        finally:
            logger.removeHandler(handler)
        self.assertEqual(output.getvalue(), "")
