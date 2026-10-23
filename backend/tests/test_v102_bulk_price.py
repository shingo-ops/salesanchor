"""バルク系の価格を1枚の値段にそろえる（g28 便2）の試験。DB なし。原文は合成した文だけ（実際の投稿文ではない）。

設計: docs/handoff/g28-bulk-price/design.md 便2、docs/adr/ADR-1021-bulk-condition-state.md
"""
from decimal import Decimal
from types import SimpleNamespace

import pytest

import app.services.line_analysis_v102_svc as svc
from app.services import review_reason_codes_svc as codes
from app.services.gemini_raw_copy_v102_product_first import PRODUCT_KUBUN_BULK
from app.services.v102_bulk_price_svc import convert
from app.services.v102_human_decisions_svc import Decisions, ValueOverrides
from tests.test_v102_unit_price_check import _MASTERS, _WriteSession

REASON = svc.REASON_BULK_PRICE_BASIS_UNKNOWN


# --- 規則（convert） -----------------------------------------------------------------------------

def test_set_is_converted_to_per_piece_with_note():
    r = convert("ARバルク 100枚セット\n5セット@26,000円", 26000, 5)
    assert (r.decision, r.n, r.unit_price, r.quantity) == ("set", 100, 260, 500)
    assert r.note == "100枚セット単位（1セット26,000円）"


def test_set_of_1000():
    r = convert("SR 1000枚 バルク\n2セット@30,000円", 30000, 2)
    assert (r.decision, r.n, r.unit_price, r.quantity) == ("set", 1000, 30, 2000)
    assert r.note == "1000枚セット単位（1セット30,000円）"


def test_piece_price_times_count_is_kept_as_is():
    r = convert("ARバルク\n250円×700枚", 250, 700)
    assert (r.decision, r.n, r.unit_price, r.quantity, r.note) == ("piece", None, 250, 700, None)


def test_piece_price_at_with_stock_in_maisuu():
    r = convert("ARバルク\n@220 在庫数2000枚", 220, 2000)
    assert (r.decision, r.unit_price, r.quantity) == ("piece", 220, 2000)


def test_fullwidth_is_normalized():
    r = convert("ARバルク　１００枚セット\n５セット＠２６，０００円", 26000, 5)
    assert (r.decision, r.n, r.unit_price) == ("set", 100, 260)


@pytest.mark.parametrize(
    ("block", "price", "qty", "reason"),
    [
        ("ARバルク\n@4,300 在庫数 26", 4300, 26, "R_stock_bare_number_unit_unknown"),  # 在庫の裸の数字
        ("50枚セット 100枚セット\n3セット@10,000円", 10000, 3, "R_multiple_set_sizes"),  # セットの大きさが2つ
        ("30枚セット\n2セット@1,000円", 1000, 2, "R_set_price_not_divisible"),  # 割り切れない
        ("100枚セット\n2セット@26,000円 3セット@27,000円", 26000, 2, "R_price_numbers_2"),  # 価格の数字が2つ
        ("100枚セット\n5セット@26,000円", 25000, 5, "R_price_mismatch"),  # 価格が DB と違う
        ("ARバルク", 100, 3, "R_no_clear_mark"),
        ("", 100, 3, "R_no_clear_mark"),  # 原文ブロックが得られない
    ],
)
def test_undecidable_goes_to_review(block, price, qty, reason):
    r = convert(block, price, qty)
    assert (r.decision, r.reason) == ("review", reason)
    assert r.unit_price is None and r.quantity is None and r.note is None


def test_missing_price_or_qty_is_review():
    assert convert("100枚セット\n5セット@26,000円", None, 5).reason == "R_price_or_qty_missing"
    assert convert("100枚セット\n5セット@26,000円", 26000, None).reason == "R_price_or_qty_missing"


# --- _apply_bulk_price ---------------------------------------------------------------------------

UNIT_IDS = {"Piece": 12, "Set": 13}
SET_BLOCK = "ARバルク 100枚セット\n5セット@26,000円"


def _values(**extra) -> dict:
    base = {
        "product_id": 1, "pid_resolved": True, "unit_id": 13, "unit_canonical": "Set", "unit_resolved": True,
        "quantity_normalized": Decimal(5), "price_normalized": Decimal(26000), "note_ja": None, "price_basis": None,
        "needs_review": False, "review_reasons": None, "status": None,
    }
    return {**base, **extra}


BULK = {"product_category": PRODUCT_KUBUN_BULK}


def test_non_bulk_is_returned_unchanged():
    values = _values()
    assert svc._apply_bulk_price(values, {"product_category": "箱系"}, SET_BLOCK, UNIT_IDS) == values
    assert svc._apply_bulk_price(values, {}, SET_BLOCK, UNIT_IDS) == values  # product_category が無い件（_mapping_mismatch_item）
    assert svc._apply_bulk_price(values, svc._mapping_mismatch_item(), SET_BLOCK, UNIT_IDS) == values


def test_unresolved_product_is_returned_unchanged():
    values = _values(pid_resolved=False)
    assert svc._apply_bulk_price(values, BULK, SET_BLOCK, UNIT_IDS) == values


def test_set_row_is_not_converted_but_goes_to_review():
    """set の換算（÷N・×N・備考・V102:bulk:set:N）は ADR-1027 で置き換え。まとめ売りと決まらなかった set は割らずに要確認。"""
    values = _values()
    out = svc._apply_bulk_price(values, BULK, SET_BLOCK, UNIT_IDS)
    assert out["review_reasons"] == REASON and out["needs_review"] is True
    assert {k: v for k, v in out.items() if k not in ("review_reasons", "needs_review")} == {
        k: v for k, v in values.items() if k not in ("review_reasons", "needs_review")
    }


def test_bundled_row_does_not_pass_bulk_price():
    values = _values(bundle_size=100, unit_canonical="Piece", unit_id=12)
    assert svc._apply_bulk_price(values, BULK, SET_BLOCK, UNIT_IDS) == values


def test_piece_row_keeps_price_and_quantity_and_sets_piece_unit():
    values = _values(unit_id=None, unit_canonical=None, unit_resolved=False, quantity_normalized=Decimal(700), price_normalized=Decimal(250))
    out = svc._apply_bulk_price(values, BULK, "ARバルク\n250円×700枚", UNIT_IDS)
    assert (out["price_normalized"], out["quantity_normalized"], out["note_ja"]) == (Decimal(250), Decimal(700), None)
    assert (out["unit_canonical"], out["unit_id"], out["unit_resolved"]) == ("Piece", 12, True)
    assert out["price_basis"] == "V102:bulk:piece"


def test_review_row_keeps_values_and_adds_reason():
    values = _values(review_reasons="unit_unknown", needs_review=True)
    out = svc._apply_bulk_price(values, BULK, "ARバルク", UNIT_IDS)
    assert out["review_reasons"] == f"unit_unknown,{REASON}" and out["needs_review"] is True
    assert {k: v for k, v in out.items() if k not in ("review_reasons", "needs_review")} == {
        k: v for k, v in values.items() if k not in ("review_reasons", "needs_review")
    }
    assert svc._apply_bulk_price(_values(), BULK, "ARバルク", UNIT_IDS)["review_reasons"] == REASON


def test_without_piece_unit_id_is_review_not_guessed():
    values = _values()
    out = svc._apply_bulk_price(values, BULK, SET_BLOCK, {"Set": 13})
    assert out["review_reasons"] == REASON and out["needs_review"] is True
    assert out["price_normalized"] == values["price_normalized"] and out["unit_id"] == 13


# --- _write_results（原文ブロック・人の手直し・引き継ぎ） ------------------------------------------

RAW = "【見出し】\n" + SET_BLOCK  # 1行目は見出し、2〜3行目が件の行


ALIASES_MASTERS = {**_MASTERS, "unit_alias_to_info": {"枚": ("Piece", "枚系"), "パック": ("Pack", "パック系"), "セット": ("Set", "セット系"), "set": ("Set", "セット系")}}


def _write(items, decisions=None, raw_text=RAW, lines=(2, 3), masters=_MASTERS):
    rows = [SimpleNamespace(id=f"row{i}", gemini_index=i, source_lines=list(lines), line_start=min(lines), line_end=max(lines), raw_price=None) for i in range(len(items))]
    numbered = [{"lines": list(lines), "gemini_index": i, **it} for i, it in enumerate(items)]
    session = _WriteSession([], [])
    svc._write_results(session, "job1", {"v102_items": numbered, "v102_flags": {}}, rows, masters, dict(UNIT_IDS, Case=5, Pack=14), decisions, raw_text)
    return [p for sql, p in session.calls if "INSERT INTO public.analysis_results" in sql]


def _item(**extra):
    return {"unit": "Set", "product_id": 1, "match_status": "matched", "condition": "Sealed box", "price_normalized": 26000, "quantity_normalized": 5, **BULK, **extra}


def test_write_results_bundle_keeps_price_and_quantity_and_sets_bundle_size():
    row = _write([_item()], masters=ALIASES_MASTERS)[0]
    assert (row["price_normalized"], row["quantity_normalized"], row["unit_canonical"], row["bundle_size"]) == (26000, 5, "Piece", 100)
    assert row["note_ja"] is None and row["price_basis"] is None and row["review_reasons"] is None


def test_write_results_set_without_bundle_goes_to_review_not_converted():
    row = _write([_item()])[0]  # 別名マスタが無い = まとめ売りと決まらない。set は割らない
    assert (row["price_normalized"], row["quantity_normalized"], row["bundle_size"]) == (26000, 5, None)
    assert row["review_reasons"] == REASON and row["needs_review"] is True and row["price_basis"] is None


def test_write_results_without_raw_text_is_review():
    row = _write([_item()], raw_text=None)[0]
    assert row["review_reasons"] == REASON and row["needs_review"] is True and row["price_normalized"] == 26000


def test_write_results_non_bulk_is_untouched_without_bundle_words():
    row = _write([_item(product_category="箱系")])[0]
    assert (row["price_normalized"], row["quantity_normalized"], row["unit_canonical"], row["note_ja"]) == (26000, 5, "Set", None)


def test_write_results_non_bulk_bundle_applies_to_all_categories():
    """ADR-1027：区分を問わず全ての行に当てる。本文「100枚セット / 5セット@26,000円」は 100枚のまとめ。"""
    row = _write([_item(product_category="箱系")], masters=ALIASES_MASTERS)[0]
    assert (row["price_normalized"], row["quantity_normalized"], row["unit_canonical"], row["bundle_size"]) == (26000, 5, "Piece", 100)


def test_write_results_bundle_unverified_adds_reason_and_keeps_values():
    row = _write([_item(product_category="箱系", price_normalized=None)], masters=ALIASES_MASTERS)[0]  # 値段なし = 決まらない
    assert row["bundle_size"] is None and row["unit_canonical"] == "Set" and row["quantity_normalized"] == 5
    assert row["review_reasons"] == "bundle_unverified" and row["needs_review"] is True


RAW_PAREN = "【見出し】\n✅RR バルク(100枚)\n@3000 在庫数 26セット"


def test_write_results_bulk_parenthesized_bundle_is_decided():
    """設計 bundle-sale §12: バルク系だけ「まとめの語＋(N＋単位の語)」を読む。"""
    row = _write([_item(price_normalized=3000, quantity_normalized=26)], raw_text=RAW_PAREN, lines=(2, 3), masters=ALIASES_MASTERS)[0]
    assert (row["bundle_size"], row["unit_canonical"], row["price_normalized"], row["quantity_normalized"]) == (100, "Piece", 3000, 26)
    assert row["review_reasons"] is None and row["needs_review"] is False


def test_write_results_non_bulk_parenthesized_bundle_is_not_read():
    row = _write([_item(price_normalized=3000, quantity_normalized=26, product_category="箱系")], raw_text=RAW_PAREN, lines=(2, 3), masters=ALIASES_MASTERS)[0]
    assert row["bundle_size"] is None


def _decision(**values) -> dict:
    return {"row0": Decisions(values=ValueOverrides(**values))}


def test_human_price_edit_removes_the_reason():
    row = _write([_item()], decisions=_decision(price=Decimal(300)), raw_text="ARバルク")[0]
    assert row["price_normalized"] == 300 and row["review_reasons"] is None and row["needs_review"] is False


def test_human_quantity_edit_removes_the_reason_but_keeps_others():
    row = _write([_item(review=[{"kind": "unit_unknown"}])], decisions=_decision(quantity=Decimal(9)), raw_text="ARバルク")[0]
    assert row["review_reasons"] == "unit_unknown" and row["needs_review"] is True


def test_human_note_only_edit_keeps_the_reason():
    row = _write([_item()], decisions=_decision(note="メモ"), raw_text="ARバルク")[0]
    assert row["review_reasons"] == REASON and row["needs_review"] is True and row["note_ja"] == "メモ"


# --- _inherit_price ------------------------------------------------------------------------------

def test_inherit_price_does_not_read_for_bulk():
    values = _values(price_normalized=None, condition_id=11, status="In stock")
    session = _InheritSession()
    assert svc._inherit_price(session, "job1", SimpleNamespace(id="row0", raw_price=None), values, True) is values
    assert session.calls == []


class _InheritSession:
    def __init__(self):
        self.calls = []

    def begin_nested(self):
        self.calls.append("begin")
        raise AssertionError("読まない")

    def execute(self, *args, **kwargs):
        self.calls.append("execute")
        raise AssertionError("読まない")


# --- NON_ACKABLE ---------------------------------------------------------------------------------

def test_reason_is_non_ackable():
    assert REASON in codes.NON_ACKABLE_REASON_CODES
