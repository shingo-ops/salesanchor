"""v102 の「単位も状態も語が無い件を、買取価格との比で Sealed box / Case に決める」（便BB）の試験。DB なし（合成の session）。

設計: docs/handoff/v102-buyback-unit/card-BB.md
"""
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest

import app.services.line_analysis_v102_svc as svc
from app.services import v102_buyback_unit_svc as bb

GOOD_SETTINGS = [
    ("unit_buyback_box_min", "0.5"), ("unit_buyback_box_max", "2"),
    ("unit_buyback_case_min", "6"), ("unit_buyback_max_age_days", "7"),
]
TARGET_ROWS = [("CN0003", 14, "Sealed box", "Box"), ("CN0001", 12, "Case", "Case")]
UNIT_IDS = {"Box": 10, "Case": 9}
POSTED_AT = datetime(2026, 10, 20, 3, 0, tzinfo=timezone.utc)
WORDLESS_BASIS = "R4c:商品分類既定>R4:単位既定"
UNKNOWN_BASIS = "R4:単位既定:単位不明"


class _Savepoint:
    def __init__(self, session):
        self.session = session

    def __enter__(self):
        self.session.savepoints.append("begin")
        return self

    def __exit__(self, exc_type, exc, tb):
        self.session.savepoints.append("rollback" if exc_type else "release")
        return False


class _Session:
    """設定・買取の中央値・状態の行に固定の行を返し、SQL を控える。"""

    def __init__(self, settings=GOOD_SETTINGS, medians=((1, 10000.0),), targets=TARGET_ROWS, posted_at=POSTED_AT):
        self.settings, self.medians, self.targets, self.posted_at = settings, medians, targets, posted_at
        self.calls: list[tuple[str, dict]] = []
        self.savepoints: list[str] = []

    def begin_nested(self):
        return _Savepoint(self)

    def execute(self, statement, params=None):
        sql = str(statement)
        self.calls.append((sql, params or {}))
        if "line_posted_at" in sql:  # _POSTED_AT_SQL（投稿日時）
            return SimpleNamespace(first=lambda: SimpleNamespace(line_posted_at=self.posted_at))
        rows = (
            self.settings if "tcg_distribution_settings" in sql
            else self.medians if "buyback_shop_products" in sql
            else self.targets if "line_conditions" in sql
            else []
        )
        return SimpleNamespace(fetchall=lambda: rows)


def _item(basis=UNKNOWN_BASIS, alias=None, **extra):
    return {"unit_basis": {"alias": alias}, "condition_basis": basis, "status_effect": "included", **extra}


def _values(price=10000, **extra):
    return {
        "product_id": 1, "pid_resolved": True, "price_normalized": price, "unit_id": None, "unit_canonical": None,
        "unit_resolved": False, "condition_id": 18, "condition_canonical": "Error", "condition_basis": UNKNOWN_BASIS,
        "review_reasons": "unit_unknown,condition_unknown,quantity_unresolved", "needs_review": True, **extra,
    }


def _apply(items, values, session=None):
    return bb.apply_buyback_units(session or _Session(), items, values, UNIT_IDS, POSTED_AT)


@pytest.mark.parametrize(("price", "condition", "unit", "basis"), [
    (10000, "Sealed box", "Box", "BUYBACK:Sealed box r=1.00"),
    (120000, "Case", "Case", "BUYBACK:Case r=12.00"),
])
def test_decides_from_the_ratio_and_records_the_basis(price, condition, unit, basis):
    out = _apply([_item()], [_values(price)])[0]
    assert (out["condition_canonical"], out["unit_canonical"], out["condition_basis"]) == (condition, unit, basis)
    assert out["unit_id"] == UNIT_IDS[unit] and out["unit_resolved"] is True


def test_drops_unit_unknown_and_condition_unknown_but_keeps_other_reasons():
    out = _apply([_item()], [_values()])[0]
    assert (out["review_reasons"], out["needs_review"]) == ("quantity_unresolved", True)
    only = _apply([_item()], [_values(review_reasons="unit_unknown,condition_unknown")])[0]
    assert (only["review_reasons"], only["needs_review"]) == (None, False)


@pytest.mark.parametrize("price", [30000, 1000, 59999, 5000 - 1])
def test_does_not_change_when_the_ratio_is_in_the_gap_or_far_below(price):
    values = _values(price)
    assert _apply([_item()], [values])[0] == values


def test_ratio_boundaries():
    assert _apply([_item()], [_values(5000)])[0]["condition_canonical"] == "Sealed box"  # r=0.5 を含む
    assert _apply([_item()], [_values(20000)])[0] == _values(20000)  # r=2 は含まない
    assert _apply([_item()], [_values(60000)])[0]["condition_canonical"] == "Case"  # r=6 を含む


def test_unit_word_or_condition_word_means_no_change():
    values = _values()
    assert _apply([_item(alias="箱")], [values])[0] == values  # 単位の語がある
    assert _apply([_item(basis="R2:難あり")], [values])[0] == values  # 状態の語がある
    assert _apply([_item(basis="R4c:商品分類既定>R2:難あり")], [values])[0] == values
    assert _apply([_item(basis="単品語あり・要確認(バラ),R4:単位既定:単位不明")], [values])[0] == values
    assert _apply([{"condition_basis": UNKNOWN_BASIS}], [values])[0] == values  # unit_basis が無い


def test_same_condition_and_unit_writes_nothing():
    same_box = _values(10000, condition_canonical="Sealed box", unit_canonical="Box", condition_basis=WORDLESS_BASIS, review_reasons="quantity_unresolved")
    assert _apply([_item(basis=WORDLESS_BASIS)], [same_box])[0] == same_box  # basis も理由も変えない
    same_case = _values(120000, condition_canonical="Case", unit_canonical="Case", condition_basis="R4:単位既定", review_reasons=None, needs_review=False)
    assert _apply([_item(basis="R4:単位既定")], [same_case])[0] == same_case


def test_buyback_basis_is_not_a_word_decision_for_soldout_inherit():
    from app.services.gemini_raw_copy_v102_soldout_ref import condition_decided_by_word  # noqa: PLC0415

    assert condition_decided_by_word("BUYBACK:Case r=12.49") is False


def test_box_product_default_basis_is_also_wordless():
    out = _apply([_item(basis=WORDLESS_BASIS)], [_values(120000)])[0]
    assert out["condition_canonical"] == "Case"


def test_excluded_or_unresolved_or_priceless_items_are_not_touched():
    session = _Session()
    values = [_values(), _values(pid_resolved=False), _values(price=None)]
    items = [_item(status_effect="excluded"), _item(), _item()]
    assert _apply(items, values, session) == values
    assert session.calls == []  # 対象が無ければ DB を読まない


def test_no_or_old_buyback_changes_nothing():
    values = _values()
    assert _apply([_item()], [values], _Session(medians=()))[0] == values  # SQL が条件で 0 行を返した場合


def test_missing_or_invalid_settings_change_nothing_and_warn(caplog):
    values = _values()
    for settings in (GOOD_SETTINGS[:3], [*GOOD_SETTINGS[:3], ("unit_buyback_max_age_days", "0")],
                     [("unit_buyback_box_min", "3"), *GOOD_SETTINGS[1:]], [("unit_buyback_box_min", "x"), *GOOD_SETTINGS[1:]]):
        session = _Session(settings=settings)
        with caplog.at_level("WARNING"):
            assert _apply([_item()], [values], session)[0] == values
        assert not any("buyback_shop_products" in c[0] for c in session.calls)
    assert any("buyback_unit" in r.message for r in caplog.records)


def test_missing_target_condition_or_unit_id_changes_nothing():
    values = _values()
    assert _apply([_item()], [values], _Session(targets=TARGET_ROWS[:1]))[0] == values
    assert bb.apply_buyback_units(_Session(), [_item()], [values], {"Case": 9}, POSTED_AT)[0] == values  # Box の単位 id が引けない


def test_does_not_mutate_the_input_and_reads_with_one_query_each():
    values, session = _values(), _Session()
    original = dict(values)
    _apply([_item(), _item()], [values, _values(120000)], session)
    assert values == original
    sqls = [c[0] for c in session.calls]
    assert sum("buyback_shop_products" in s for s in sqls) == 1 and sum("line_conditions" in s for s in sqls) == 1
    assert session.calls[1][1] == {"pids": [1], "types": ["BOX", "BOX_SHRINK"], "statuses": ["auto", "manual"], "days": 7, "posted_at": POSTED_AT}


def test_skip_positions_are_not_decided_and_not_queried():
    values, session = _values(), _Session()
    assert bb.apply_buyback_units(session, [_item()], [values], UNIT_IDS, POSTED_AT, frozenset({0}))[0] == values
    assert session.calls == []


def test_write_results_does_not_decide_when_a_human_decided_the_condition():
    decisions = {"row0": svc.Decisions(condition_id=14)}
    session = _WriteSession()
    rows = [SimpleNamespace(id="row0", gemini_index=0, source_lines=[1])]
    svc._write_results(session, "job1", {"v102_items": [{"lines": [1], "gemini_index": 0, **_v102_item()}], "v102_flags": {}}, rows, _MASTERS, dict(UNIT_IDS), decisions)
    assert not any("buyback_shop_products" in sql for sql, _ in session.calls)


def test_median_sql_keeps_the_agreed_conditions():
    sql = bb._MEDIAN_SQL
    for needle in ("sp.product_type = ANY", "sp.match_status = ANY", "l.fetched_at <= :posted_at", ":posted_at - make_interval(days => :days)", "ORDER BY l.fetched_at DESC", "percentile_cont(0.5)", "lp.price_s > 0"):
        assert needle in sql
    assert "sp.last_seen_at" not in sql  # 物差しの時点は投稿日時。「今から N 日に見えた店」は使わない


def test_parse_settings_requires_four_valid_keys():
    raw = dict(GOOD_SETTINGS)
    assert bb.parse_settings(raw) == bb.BuybackSettings(Decimal("0.5"), Decimal(2), Decimal(6), 7)
    for key in raw:
        assert bb.parse_settings({k: v for k, v in raw.items() if k != key}) is None
    for bad in ({"unit_buyback_box_max": "0.4"}, {"unit_buyback_case_min": "1.5"}, {"unit_buyback_box_min": "NaN"},
                {"unit_buyback_box_min": "0"}, {"unit_buyback_max_age_days": "1.5"}):
        assert bb.parse_settings({**raw, **bad}) is None


# --- _write_results への接続（便UP の前に走る・他の値は変わらない・失敗は飛ばす） -------------------------------

class _WriteSession(_Session):
    def execute(self, statement, params=None):
        sql = str(statement)
        if "INSERT INTO" in sql and "analysis_results" in sql:
            self.calls.append((sql, params or {}))
            return SimpleNamespace(scalar_one=lambda: "result-1")
        if "FROM public.products" in sql or "FROM public.conditions" in sql or "DELETE FROM" in sql or "INSERT INTO" in sql:
            self.calls.append((sql, params or {}))
            return SimpleNamespace(fetchall=lambda: [])
        return super().execute(statement, params)


_MASTERS = {
    "cond_entries": [{"cond_id": 18, "canonical": "FLAG_SINGLE", "code": "CN0008"}],
    "cond_canonical_to_uuid": {"FLAG_SINGLE": 18},
    "ship_entries": [],
    "status_entries": [],
}


def _write(session, items):
    rows = [SimpleNamespace(id=f"row{i}", gemini_index=i, source_lines=[i + 1]) for i in range(len(items))]
    numbered = [{"lines": [i + 1], "gemini_index": i, **it} for i, it in enumerate(items)]
    svc._write_results(session, "job1", {"v102_items": numbered, "v102_flags": {}}, rows, _MASTERS, dict(UNIT_IDS), None)
    return [p for sql, p in session.calls if "INSERT INTO public.analysis_results" in sql]


def _v102_item(**extra):
    return {
        "unit": "none", "product_id": 1, "match_status": "matched", "condition": "FLAG_SINGLE", "price_normalized": 10000,
        "unit_basis": {"alias": None}, "condition_basis": UNKNOWN_BASIS, "status_effect": "included",
        "review": [{"kind": "unit_unknown"}, {"kind": "condition_unknown"}], **extra,
    }


def test_write_results_applies_the_decision_and_changes_only_the_expected_columns():
    decided = _write(_WriteSession(), [_v102_item()])[0]
    untouched = _write(_WriteSession(medians=()), [_v102_item()])[0]
    assert (decided["condition_canonical"], decided["unit_canonical"], decided["review_reasons"]) == ("Sealed box", "Box", None)
    differing = {k for k in decided if decided[k] != untouched[k]} - {"id", "computed_at", "updated_at"}
    assert differing == {
        "condition_id", "condition_canonical", "condition_basis", "unit_id", "unit_canonical", "unit_resolved",
        "review_reasons", "needs_review",
    }


def test_write_results_skips_the_decision_when_the_buyback_query_fails(caplog):
    class _Failing(_WriteSession):
        def execute(self, statement, params=None):
            if "buyback_shop_products" in str(statement):
                raise RuntimeError("boom")
            return super().execute(statement, params)

    session = _Failing()
    with caplog.at_level("WARNING"):
        row = _write(session, [_v102_item()])[0]
    assert (row["condition_canonical"], row["unit_canonical"]) == ("FLAG_SINGLE", None)
    assert "rollback" in session.savepoints


def test_bundle_rows_are_not_buyback_candidates():
    """まとめ売り行（bundle_size あり）は買取価格との比で単位を決めない（ADR-1027）。"""
    bundled = _values(bundle_size=40)
    plain = _values(bundle_size=None)
    assert bb.is_candidate(_item(), bundled) is False
    assert bb.is_candidate(_item(), plain) is True


# --- 物差しの時点は投稿日時（便1） ---------------------------------------------------------------------------

def test_median_query_receives_the_posted_at_and_age_window():
    """投稿日時より後の値・days より前の値は、SQL の条件（fetched_at <= :posted_at・>= :posted_at - days）で外れる。"""
    session = _Session()
    bb.load_medians(session, [1], 30, POSTED_AT)
    sql, params = session.calls[0]
    assert params["posted_at"] == POSTED_AT and params["days"] == 30
    assert "l.fetched_at <= :posted_at AND l.fetched_at >= :posted_at - make_interval(days => :days)" in sql
    assert sql.index("l.fetched_at <= :posted_at") < sql.index("ORDER BY l.fetched_at DESC")  # 最新の値を選ぶ前に絞る


def test_buyback_units_passes_the_posted_at_to_the_ruler():
    session = _Session()
    pairs = [(_item(), SimpleNamespace(id="row0"))]
    out = svc._buyback_units(session, pairs, [_values()], dict(UNIT_IDS), "job1", {})
    assert out[0]["condition_canonical"] == "Sealed box"
    assert any(p.get("posted_at") == POSTED_AT for _s, p in session.calls)
    assert session.savepoints == ["begin", "release"]


def test_buyback_units_does_nothing_when_posted_at_is_none():
    session = _Session(posted_at=None)
    values = _values()
    out = svc._buyback_units(session, [(_item(), SimpleNamespace(id="row0"))], [values], dict(UNIT_IDS), "job1", {})
    assert out == [values]
    assert not any("buyback_shop_products" in s for s, _ in session.calls)


def test_buyback_units_skips_this_post_when_loading_posted_at_fails(caplog):
    class _Failing(_Session):
        def execute(self, statement, params=None):
            if "line_posted_at" in str(statement):
                raise RuntimeError("boom")
            return super().execute(statement, params)

    session = _Failing()
    values = _values()
    with caplog.at_level("WARNING"):
        out = svc._buyback_units(session, [(_item(), SimpleNamespace(id="row0"))], [values], dict(UNIT_IDS), "job1", {})
    assert out == [values]
    assert session.savepoints == ["begin", "rollback"]  # SAVEPOINT の中で失敗し、保存全体の取引は壊さない
    assert any("buyback_unit" in r.message for r in caplog.records)
