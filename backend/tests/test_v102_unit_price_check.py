"""v102 の「単位と価格が相場と合わない」確認（便UP）の試験。DB なし（合成の相場・合成の session）。

設計: docs/handoff/v102-unit-price-check/card-UP.md
"""
from decimal import Decimal
from types import SimpleNamespace

import pytest

import app.services.line_analysis_v102_svc as svc
from app.services import v102_unit_price_check_svc as check
from app.services.v102_unit_price_check_svc import Candidate, CheckSettings, MarketEntry

SETTINGS = CheckSettings(ratio=Decimal(3), min_posts=3)


def _market(**units: tuple[int, int]) -> dict:
    """商品 1 の相場。units は 単位=(中央値, 別々の投稿の数)。"""
    return {1: {unit: MarketEntry(Decimal(median), posts) for unit, (median, posts) in units.items()}}


def _cand(unit: str, price: int, product_id: int = 1) -> Candidate:
    return Candidate(key=0, product_id=product_id, unit=unit, price=Decimal(price))


def test_flags_when_far_from_own_unit_and_closer_to_another_unit():
    market = _market(Case=(100000, 3), Box=(25000, 3))
    assert check.is_unit_price_mismatch(_cand("Case", 26000), market, SETTINGS) is True


def test_does_not_flag_when_within_the_ratio():
    market = _market(Case=(100000, 3), Box=(25000, 3))
    assert check.is_unit_price_mismatch(_cand("Case", 40000), market, SETTINGS) is False  # 2.5 倍
    assert check.is_unit_price_mismatch(_cand("Case", 33334), market, SETTINGS) is False  # 3 倍未満


def test_ratio_boundary_is_exclusive():
    market = _market(Case=(30000, 3), Box=(10000, 3))
    assert check.is_unit_price_mismatch(_cand("Case", 10000), market, SETTINGS) is False  # own 3.0 倍ちょうどは付けない
    assert check.is_unit_price_mismatch(_cand("Case", 9999), market, SETTINGS) is True  # 3.0003 倍


def test_does_not_flag_when_no_other_unit_has_a_market():
    assert check.is_unit_price_mismatch(_cand("Case", 26000), _market(Case=(100000, 3)), SETTINGS) is False


def test_does_not_flag_when_other_unit_is_not_closer():
    market = _market(Case=(100000, 3), Box=(500000, 3))
    assert check.is_unit_price_mismatch(_cand("Case", 20000), market, SETTINGS) is False  # 5倍ずれたが Box(25倍)の方が遠い


def test_ignores_units_with_too_few_distinct_posts():
    few_other = _market(Case=(100000, 3), Box=(25000, 2))
    assert check.is_unit_price_mismatch(_cand("Case", 26000), few_other, SETTINGS) is False
    few_own = _market(Case=(100000, 2), Box=(25000, 3))
    assert check.is_unit_price_mismatch(_cand("Case", 26000), few_own, SETTINGS) is False


def test_does_nothing_without_own_unit_market_or_product_market_or_price():
    assert check.is_unit_price_mismatch(_cand("Case", 26000), _market(Box=(25000, 3)), SETTINGS) is False
    assert check.is_unit_price_mismatch(_cand("Case", 26000, product_id=2), _market(Case=(100000, 3), Box=(25000, 3)), SETTINGS) is False
    assert check.is_unit_price_mismatch(_cand("Case", 0), _market(Case=(100000, 3), Box=(25000, 3)), SETTINGS) is False


def test_parse_settings_requires_both_valid_keys():
    assert check.parse_settings({"unit_price_check_ratio": "3", "unit_price_check_min_posts": "3"}) == SETTINGS
    assert check.parse_settings({"unit_price_check_ratio": "3"}) is None
    assert check.parse_settings({"unit_price_check_min_posts": "3"}) is None
    for bad in ({"unit_price_check_ratio": "abc", "unit_price_check_min_posts": "3"},
                {"unit_price_check_ratio": "1", "unit_price_check_min_posts": "3"},
                {"unit_price_check_ratio": "3", "unit_price_check_min_posts": "0"},
                {"unit_price_check_ratio": "3", "unit_price_check_min_posts": "x"},
                {"unit_price_check_ratio": "NaN", "unit_price_check_min_posts": "3"}):
        assert check.parse_settings(bad) is None


class _Session:
    """設定の SQL と相場の SQL に固定の行を返し、SQL と引数を控える。"""

    def __init__(self, settings_rows, market_rows):
        self.settings_rows, self.market_rows = settings_rows, market_rows
        self.calls: list[tuple[str, dict]] = []

    def execute(self, statement, params=None):
        sql = str(statement)
        self.calls.append((sql, params or {}))
        rows = self.settings_rows if "tcg_distribution_settings" in sql else self.market_rows
        return SimpleNamespace(fetchall=lambda: rows)


_GOOD_SETTINGS = [("unit_price_check_ratio", "3"), ("unit_price_check_min_posts", "3")]
_MARKET_ROWS = [(1, "Case", 100000.0, 3), (1, "Box", 25000.0, 3)]


def test_find_mismatches_returns_flagged_keys_with_one_market_query():
    session = _Session(_GOOD_SETTINGS, _MARKET_ROWS)
    candidates = [Candidate(0, 1, "Case", Decimal(26000)), Candidate(1, 1, "Case", Decimal(99000)), Candidate(2, 1, "Box", Decimal(26000))]
    assert check.find_mismatches(session, "public", candidates, "sm-1") == frozenset({0})
    market_calls = [c for c in session.calls if "percentile_cont" in c[0]]
    assert len(market_calls) == 1 and market_calls[0][1]["smid"] == "sm-1" and market_calls[0][1]["pids"] == [1]


def test_market_sql_excludes_bundle_rows():
    """まとめ売り行（bundle_size あり）は1単位の相場に入れない（ADR-1027）。"""
    assert "ar.bundle_size IS NULL" in check._MARKET_SQL


def test_market_sql_keeps_the_agreed_conditions():
    sql = check._MARKET_SQL
    for needle in ("ar.engine_version LIKE", "ar.is_current IS TRUE", "ar.price_normalized IS NOT NULL",
                   "ar.unit_canonical IS NOT NULL", "ej.source_message_id != ", "md5(sm.raw_text) != ", "count(DISTINCT md5(sm.raw_text))",
                   "percentile_cont(0.5)"):
        assert needle in sql
    assert "needs_review" not in sql  # 要確認の行も相場に入れる（付く→外れる→付く の揺れを防ぐ）
    assert check._ENGINE_LIKE == "v102%"


def test_find_mismatches_does_nothing_without_settings_and_does_not_read_the_market(caplog):
    session = _Session([("unit_price_check_ratio", "3")], _MARKET_ROWS)
    with caplog.at_level("WARNING"):
        assert check.find_mismatches(session, "public", [Candidate(0, 1, "Case", Decimal(26000))], "sm-1") == frozenset()
    assert not any("percentile_cont" in c[0] for c in session.calls)
    assert any("unit_price_check" in r.message for r in caplog.records)


def test_find_mismatches_without_candidates_reads_nothing():
    session = _Session(_GOOD_SETTINGS, _MARKET_ROWS)
    assert check.find_mismatches(session, "public", [], "sm-1") == frozenset()
    assert session.calls == []


# --- _write_results への接続（理由が付く・ack で外れる・他の値は変わらない） -------------------------------

class _Savepoint:
    def __init__(self, session):
        self.session = session

    def __enter__(self):
        self.session.savepoints.append("begin")
        return self

    def __exit__(self, exc_type, exc, tb):
        self.session.savepoints.append("rollback" if exc_type else "release")
        return False


class _WriteSession(_Session):
    savepoints: list

    def __init__(self, settings_rows, market_rows):
        super().__init__(settings_rows, market_rows)
        self.savepoints = []

    def begin_nested(self):
        return _Savepoint(self)

    def execute(self, statement, params=None):
        sql = str(statement)
        if "source_message_id::text" in sql:
            self.calls.append((sql, params or {}))
            return SimpleNamespace(scalar_one=lambda: "sm-1")
        if "INSERT INTO" in sql and "analysis_results" in sql:
            self.calls.append((sql, params or {}))
            return SimpleNamespace(scalar_one=lambda: "result-1")
        if "FROM public.products" in sql:
            self.calls.append((sql, params or {}))
            return SimpleNamespace(fetchall=lambda: [(1, 3)])
        if "FROM public.conditions" in sql or "DELETE FROM" in sql or "INSERT INTO" in sql or "UPDATE" in sql:
            self.calls.append((sql, params or {}))
            return SimpleNamespace(fetchall=lambda: [])
        return super().execute(statement, params)


_MASTERS = {
    "cond_entries": [{"cond_id": 11, "canonical": "Sealed box", "code": "CN0001"}, {"cond_id": 18, "canonical": "FLAG_SINGLE", "code": "CN0008"}],
    "cond_canonical_to_uuid": {"Sealed box": 11, "FLAG_SINGLE": 18},
    "ship_entries": [],
    "status_entries": [],
}


def _write(session, items, decisions=None):
    rows = [SimpleNamespace(id=f"row{i}", gemini_index=i, source_lines=[i + 1]) for i in range(len(items))]
    numbered = [{"lines": [i + 1], "gemini_index": i, **it} for i, it in enumerate(items)]
    svc._write_results(session, "job1", {"v102_items": numbered, "v102_flags": {}}, rows, _MASTERS, {"Case": 5, "Box": 6}, decisions)
    return [p for sql, p in session.calls if "INSERT INTO public.analysis_results" in sql]


def _item(unit="Case", price=26000, **extra):
    return {"unit": unit, "product_id": 1, "match_status": "matched", "condition": "Sealed box", "price_normalized": price, **extra}


def test_write_results_adds_the_reason_and_needs_review_without_changing_other_values():
    flagged = _write(_WriteSession(_GOOD_SETTINGS, _MARKET_ROWS), [_item()])[0]
    unflagged = _write(_WriteSession([], _MARKET_ROWS), [_item()])[0]  # 設定なし = 何もしない
    assert (flagged["review_reasons"], flagged["needs_review"]) == ("unit_price_mismatch", True)
    assert (unflagged["review_reasons"], unflagged["needs_review"]) == (None, False)
    differing = {k for k in flagged if flagged[k] != unflagged[k]} - {"id", "computed_at", "updated_at"}
    assert differing == {"review_reasons", "needs_review"}  # 単位・価格・商品・状態・数量は同じ


def test_write_results_appends_after_existing_reasons_and_keeps_them():
    row = _write(_WriteSession(_GOOD_SETTINGS, _MARKET_ROWS), [_item(review=[{"kind": "unit_unknown"}])])[0]
    assert row["review_reasons"] == "unit_unknown,unit_price_mismatch"


def test_human_ack_removes_the_reason_and_clears_needs_review():
    decisions = {"row0": svc.Decisions(ack_codes=frozenset({"unit_price_mismatch"}))}
    row = _write(_WriteSession(_GOOD_SETTINGS, _MARKET_ROWS), [_item()], decisions)[0]
    assert (row["review_reasons"], row["needs_review"]) == (None, False)
    assert (row["unit_canonical"], row["price_normalized"]) == ("Case", 26000)


def test_items_without_price_or_unit_or_product_are_not_checked():
    session = _WriteSession(_GOOD_SETTINGS, _MARKET_ROWS)
    rows = _write(session, [_item(price=None), _item(unit="none"), {"unit": "Case", "product_id": 1, "match_status": "unmatched", "price_normalized": 26000, "condition": "Sealed box"}])
    assert all(r["review_reasons"] is None or "unit_price_mismatch" not in r["review_reasons"] for r in rows)
    assert not any("percentile_cont" in sql for sql, _ in session.calls)


@pytest.mark.parametrize("code", ["unit_price_mismatch"])
def test_reason_code_is_ackable(code):
    from app.services.review_reason_codes_svc import NON_ACKABLE_REASON_CODES

    assert code not in NON_ACKABLE_REASON_CODES
    assert svc.REASON_UNIT_PRICE_MISMATCH == code


# --- 規則B: 比べる別単位の相場が無いときは、単独の倍率（unit_price_check_single_ratio）以上で疑う ----------------

SINGLE5 = CheckSettings(ratio=Decimal(3), min_posts=3, single_ratio=Decimal(5))


def test_rule_b_flags_the_expensive_side_when_no_other_unit_market():
    market = _market(Box=(10000, 3))
    assert check.is_unit_price_mismatch(_cand("Box", 50000), market, SINGLE5) is True  # ちょうど5倍は含む
    assert check.is_unit_price_mismatch(_cand("Box", 49999), market, SINGLE5) is False


def test_rule_b_does_not_flag_the_cheap_side():
    market = _market(Box=(10000, 3))
    assert check.is_unit_price_mismatch(_cand("Box", 2000), market, SINGLE5) is False  # 相場の1/5でも付けない
    assert check.is_unit_price_mismatch(_cand("Box", 100), market, SINGLE5) is False


def test_rule_b_does_nothing_without_the_single_ratio_setting():
    market = _market(Box=(10000, 3))
    assert check.is_unit_price_mismatch(_cand("Box", 138000), market, SETTINGS) is False  # key なし = 規則Bは働かない


def test_rule_b_needs_a_usable_own_market():
    assert check.is_unit_price_mismatch(_cand("Box", 138000), _market(Box=(10000, 2)), SINGLE5) is False
    assert check.is_unit_price_mismatch(_cand("Pack", 138000), _market(Box=(10000, 3)), SINGLE5) is False


def test_rule_b_ignores_other_units_with_too_few_posts_but_rule_a_wins_when_a_usable_other_exists():
    assert check.is_unit_price_mismatch(_cand("Box", 138000), _market(Box=(10000, 3), Case=(100000, 2)), SINGLE5) is True  # 比べる相場が無い扱い
    # 別単位の相場があるなら規則Aだけ（別単位の方が遠ければ付けない）
    assert check.is_unit_price_mismatch(_cand("Box", 138000), _market(Box=(10000, 3), Case=(5000000, 3)), SINGLE5) is False


def test_single_ratio_setting_parsing():
    base = {"unit_price_check_ratio": "3", "unit_price_check_min_posts": "3"}
    assert check.parse_settings({**base, "unit_price_check_single_ratio": "8"}).single_ratio == Decimal(8)
    assert check.parse_settings(base).single_ratio is None
    for bad in ("abc", "1", "0.5", "NaN"):
        parsed = check.parse_settings({**base, "unit_price_check_single_ratio": bad})
        assert parsed is not None and parsed.single_ratio is None  # 規則Bだけ止まり、規則Aは働く


def test_failing_market_query_does_not_break_the_save_and_adds_no_reason(caplog):
    class _Failing(_WriteSession):
        def execute(self, statement, params=None):
            if "percentile_cont" in str(statement):
                raise RuntimeError("market boom")
            return super().execute(statement, params)

    session = _Failing(_GOOD_SETTINGS, _MARKET_ROWS)
    with caplog.at_level("WARNING"):
        rows = _write(session, [_item()])
    assert len(rows) == 1  # 保存は最後まで進む
    assert (rows[0]["review_reasons"], rows[0]["needs_review"]) == (None, False)
    assert (rows[0]["unit_canonical"], rows[0]["price_normalized"]) == ("Case", 26000)
    assert session.savepoints == ["begin", "rollback"]  # SAVEPOINT の中で失敗した
    assert any("job=job1" in r.message and "market boom" in r.message for r in caplog.records)
