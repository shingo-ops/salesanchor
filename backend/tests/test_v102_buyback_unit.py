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
# 状態マスタ（本番の box・case・pack の群の 11 行。札入り後の形）: (code, id, canonical, value_group, unit_id, condition_def_id, 単位の canonical)
TARGET_ROWS = [
    ("CN0003", 14, "Sealed box", "box", 10, 2, "Box"), ("CN0004", 16, "Damaged sealed box", "box", 10, 3, "Box"),
    ("CN0005", 17, "No shrink box", "box", 10, 4, "Box"), ("CN0006", 18, "Opened box", "box", 10, 5, "Box"),
    ("CN20261008072213", 25, "Searched box", "box", 10, 8, "Box"),
    ("CN0001", 12, "Case", "case", 9, 2, "Case"), ("CN0002", 13, "Damaged case", "case", 9, 3, "Case"),
    ("CN0009", 20, "Opened case", "case", 9, 5, "Case"),
    ("CN0007", 22, "Unsearched pack", "pack", 11, 7, "Pack"), ("CN0010", 21, "Searched pack", "pack", 11, 8, "Pack"),
    ("CN0013", 44, "AR confirmed pack", "pack", 11, None, "Pack"),
]
PACK_SETTINGS = [*GOOD_SETTINGS, ("unit_buyback_pack_max", "0.2")]
UNIT_IDS = {"Box": 10, "Case": 9, "Pack": 11}
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


ALIASES = {"個": ("個", "条件つき"), "パック": ("Pack", "パック系"), "BOX": ("Box", "箱系"), "カートン": ("Case", "箱系大")}


def _item(basis=UNKNOWN_BASIS, alias=None, **extra):
    return {"unit_basis": {"alias": alias}, "condition_basis": basis, "status_effect": "included", **extra}


def _values(price=10000, **extra):
    return {
        "product_id": 1, "pid_resolved": True, "price_normalized": price, "unit_id": None, "unit_canonical": None,
        "unit_resolved": False, "condition_id": 18, "condition_canonical": "Error", "condition_basis": UNKNOWN_BASIS,
        "review_reasons": "unit_unknown,condition_unknown,quantity_unresolved", "needs_review": True, **extra,
    }


def _apply(items, values, session=None):
    return bb.apply_buyback_units(session or _Session(), items, values, UNIT_IDS, ALIASES, POSTED_AT)


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
    assert _apply([_item()], [values], _Session(targets=[r for r in TARGET_ROWS if r[0] != "CN0001"]))[0] == values
    assert bb.apply_buyback_units(_Session(), [_item()], [values], {"Case": 9}, ALIASES, POSTED_AT)[0] == values  # Box の単位 id が引けない


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
    assert bb.apply_buyback_units(session, [_item()], [values], UNIT_IDS, ALIASES, POSTED_AT, frozenset({0}))[0] == values
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


def test_parse_settings_requires_four_valid_keys():  # unit_buyback_pack_max は無くてもよい key（test_pack_max_setting で確かめる）
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
    assert bb.is_candidate(_item(), bundled, {}) is False
    assert bb.is_candidate(_item(), plain, {}) is True


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
    out = svc._buyback_units(session, pairs, [_values()], dict(UNIT_IDS), "job1", {}, {})
    assert out[0]["condition_canonical"] == "Sealed box"
    assert any(p.get("posted_at") == POSTED_AT for _s, p in session.calls)
    assert session.savepoints == ["begin", "release"]


def test_buyback_units_does_nothing_when_posted_at_is_none():
    session = _Session(posted_at=None)
    values = _values()
    out = svc._buyback_units(session, [(_item(), SimpleNamespace(id="row0"))], [values], dict(UNIT_IDS), "job1", {}, {})
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
        out = svc._buyback_units(session, [(_item(), SimpleNamespace(id="row0"))], [values], dict(UNIT_IDS), "job1", {}, {})
    assert out == [values]
    assert session.savepoints == ["begin", "rollback"]  # SAVEPOINT の中で失敗し、保存全体の取引は壊さない
    assert any("buyback_unit" in r.message for r in caplog.records)


# --- 便2：対象を広げる・Pack・状態の写し・理由の外し方（ADR-1036） --------------------------------------------

PRICES = {"Box": 10000, "Case": 120000, "Pack": 1000}  # 物差し 10000 に対する r = 1 / 12 / 0.1
# 状態の種類ごとの「今の状態」（語で決まった行。既定だけは語なし）: (condition_id, canonical, basis)
CURRENT = {
    "default": (28, "Error", UNKNOWN_BASIS),
    "damaged": (16, "Damaged sealed box", "R2:ダメージ"),
    "opened": (18, "Opened box", "R2:開封"),
    "searched": (25, "Searched box", "R2:サーチ済"),
    "noshrink": (17, "No shrink box", "R2:シュリンクなし"),
}
# B の表（design.md）の期待値。None は「決めない（今のまま）」
B_TABLE = {
    ("default", "Box"): "Sealed box", ("default", "Case"): "Case", ("default", "Pack"): "Unsearched pack",
    ("damaged", "Box"): "Damaged sealed box", ("damaged", "Case"): "Damaged case", ("damaged", "Pack"): None,
    ("opened", "Box"): "Opened box", ("opened", "Case"): "Opened case", ("opened", "Pack"): None,
    ("searched", "Box"): "Searched box", ("searched", "Case"): None, ("searched", "Pack"): "Searched pack",
    ("noshrink", "Box"): "No shrink box", ("noshrink", "Case"): None, ("noshrink", "Pack"): None,
}


def _kitem(basis=UNKNOWN_BASIS, alias="個", category="箱系", review=None, **extra):
    item = _item(basis=basis, alias=alias, product_category=category, **extra)
    if review is not None:
        item["review"] = review
    return item


def _kvalues(kind="default", unit="Box", price=10000, reasons="unit_unknown,condition_unknown", **extra):
    cid, canonical, basis = CURRENT[kind]
    return _values(
        price, condition_id=cid, condition_canonical=canonical, condition_basis=basis,
        unit_canonical=unit, unit_id=UNIT_IDS[unit], unit_resolved=True, review_reasons=reasons, needs_review=reasons is not None, **extra,
    )


def _kapply(item, values, settings=PACK_SETTINGS, targets=TARGET_ROWS, **kw):
    return _apply([item], [values], _Session(settings=settings, targets=targets, **kw))[0]


@pytest.mark.parametrize(("kind", "unit"), list(B_TABLE))
def test_b_table_15_combinations(kind, unit):
    expected = B_TABLE[(kind, unit)]
    cid, canonical, basis = CURRENT[kind]
    item = _kitem(basis=basis)
    values = _kvalues(kind, "Box" if unit != "Case" else "Case", PRICES[unit])
    out = _kapply(item, values)
    if expected is None:
        assert out == values
        return
    assert (out["condition_canonical"], out["unit_canonical"], out["unit_id"]) == (expected, unit, UNIT_IDS[unit])
    assert out["review_reasons"] is None and out["needs_review"] is False
    if kind == "default":
        assert out["condition_basis"] == f"BUYBACK:{expected} r={PRICES[unit] / 10000:.2f}"
    else:
        assert out["condition_basis"] == f"{basis}|PRICE:①r={PRICES[unit] / 10000:.2f}"  # 先頭の規則記号は変えない


def test_k1_unit_word_none_or_ko_decides_by_price():
    values = _kvalues("default", "Box", 120000)
    assert _kapply(_kitem(alias=None), values)["unit_canonical"] == "Case"
    assert _kapply(_kitem(alias="個"), values)["unit_canonical"] == "Case"  # 「個」は条件つき
    assert _kapply(_kitem(alias="未登録の語"), values)["unit_canonical"] == "Case"  # 別名が未登録 = 不明


@pytest.mark.parametrize(("code_word", "kind", "expected_case", "expected_box"), [
    ("未開封", "default", "Case", "Sealed box"),
])
def test_k1_unopened_word_is_the_default_kind(code_word, kind, expected_case, expected_box):
    values = _values(120000, condition_id=14, condition_canonical="Sealed box", condition_basis="R2:未開封", unit_canonical="Box", unit_id=10, unit_resolved=True)
    out = _kapply(_kitem(basis="R2:未開封"), values)
    assert (out["condition_canonical"], out["unit_canonical"], out["condition_basis"]) == (expected_case, "Case", "R2:未開封|PRICE:①r=12.00")
    out = _kapply(_kitem(basis="R2:未開封"), {**values, "price_normalized": 1000})
    assert (out["condition_canonical"], out["unit_canonical"]) == ("Unsearched pack", "Pack")  # 未開封 @箱の 1/10 → Unsearched pack
    unsearched = _values(1000, condition_id=22, condition_canonical="Unsearched pack", condition_basis="R2:未サーチ", unit_canonical="Pack", unit_id=11, unit_resolved=True)
    out = _kapply(_kitem(basis="R2:未サーチ"), {**unsearched, "price_normalized": 10000})
    assert (out["condition_canonical"], out["unit_canonical"]) == (expected_box, "Box")


def test_k1_main_example_damaged_word_already_damaged_box_only_drops_the_reason():
    reasons = "condition_multiple_candidates,quantity_unresolved"
    values = _kvalues("damaged", "Box", 10000, reasons=reasons)
    item = _kitem(basis="R2:ダメージ", review=[{"kind": "condition_multiple_candidates", "codes": ["CN0002"]}])  # 別の区分（Damaged case）の語も当たった
    out = _kapply(item, values)
    assert out == {**values, "review_reasons": "quantity_unresolved", "condition_basis": "R2:ダメージ|PRICE:①r=1.00"}
    only = _kapply(item, _kvalues("damaged", "Box", 10000, reasons="condition_multiple_candidates"))
    assert (only["review_reasons"], only["needs_review"], only["condition_canonical"], only["unit_canonical"]) == (None, False, "Damaged sealed box", "Box")


def test_k1_wordless_same_value_with_reason_drops_only_the_reason_and_keeps_basis():
    values = _values(10000, condition_canonical="Sealed box", unit_canonical="Box", condition_basis=WORDLESS_BASIS, review_reasons="unit_unknown,quantity_unresolved")
    out = _kapply(_kitem(basis=WORDLESS_BASIS, alias=None), values)
    assert out == {**values, "review_reasons": "quantity_unresolved"}  # basis は変わらない


def test_k1_other_kubun_word_via_review_codes():
    review = [{"kind": "condition_multiple_candidates", "codes": ["CN0006"]}]
    word_values = lambda unit, price: _kvalues("opened", unit, price, reasons="condition_multiple_candidates")  # noqa: E731
    item = _kitem(basis="R2:開封", review=review)
    out = _kapply(item, word_values("Box", 120000))
    assert (out["condition_canonical"], out["unit_canonical"], out["review_reasons"]) == ("Opened case", "Case", None)
    assert out["condition_basis"] == "R2:開封|PRICE:①r=12.00"
    assert _kapply(item, word_values("Box", 10000))["condition_canonical"] == "Opened box"
    # 今の状態が既定で、別の区分の語（テープカット = Opened case の語）だけ当たった行は、codes の種類（開封）だけで写す
    tape = _kitem(review=[{"kind": "condition_multiple_candidates", "codes": ["CN0009"]}])
    sealed = _values(120000, condition_id=14, condition_canonical="Sealed box", unit_canonical="Box", unit_id=10, unit_resolved=True,
                     condition_basis=WORDLESS_BASIS, review_reasons="condition_multiple_candidates")
    out = _kapply(tape, sealed)
    assert (out["condition_canonical"], out["unit_canonical"], out["review_reasons"]) == ("Opened case", "Case", None)


def test_k1_review_codes_with_two_kinds_or_unknown_code_change_nothing():
    values = _kvalues("opened", "Box", 120000, reasons="condition_multiple_candidates")
    two = _kitem(basis="R2:開封", review=[{"kind": "condition_multiple_candidates", "codes": ["CN0004"]}])  # 開封 + ダメージ
    assert _kapply(two, values) == values
    unknown = _kitem(basis="R2:開封", review=[{"kind": "condition_multiple_candidates", "codes": ["CN0013"]}])  # 札が空
    assert _kapply(unknown, values) == values
    missing = _kitem(basis="R2:開封", review=[{"kind": "condition_multiple_candidates", "codes": ["CN9999"]}])  # 読んだ行に無い
    assert _kapply(missing, values) == values
    no_codes = _kitem(basis="R2:開封", review=[{"kind": "condition_multiple_candidates"}])  # 理由があるのに codes が取れない
    assert _kapply(no_codes, values) == values


def test_k1_state_with_no_label_or_not_in_master_changes_nothing():
    ar = _values(1000, condition_id=44, condition_canonical="AR confirmed pack", condition_basis="R2:AR", unit_canonical="Pack", unit_id=11, unit_resolved=True)
    assert _kapply(_kitem(basis="R2:AR"), ar) == ar  # 札が空
    gone = _values(10000, condition_id=999, condition_canonical="X", condition_basis="R2:x")
    assert _kapply(_kitem(basis="R2:x"), gone) == gone  # 読んだ行に無い


def test_ratio_bands_decide_the_unit_and_gaps_change_nothing():
    for price, unit in ((10000, "Box"), (120000, "Case"), (1000, "Pack"), (2000, "Pack"), (5000, "Box"), (60000, "Case")):
        assert _kapply(_kitem(), _kvalues("default", "Box", price))["unit_canonical"] == unit
    for price in (2001, 4999, 20000, 59999):  # 隙間（0.2 < r < 0.5、2 <= r < 6）
        values = _kvalues("default", "Box", price)
        assert _kapply(_kitem(), values) == values


def test_rows_with_unit_word_or_flag_single_or_set_or_non_box_are_not_changed():
    values = _kvalues("default", "Box", 120000)
    assert _kapply(_kitem(alias="BOX"), values) == values  # 単位の語（箱系）
    assert _kapply(_kitem(alias="パック"), values) == values
    assert _kapply(_kitem(alias="カートン"), values) == values
    flagged = _kitem(basis="単品語あり・要確認(バラ),R4:単位既定:単位不明")
    assert _kapply(flagged, values) == values  # 単品語の印
    assert _kapply(_kitem(category="セット系"), values) == values
    assert _kapply(_kitem(category="シングル系"), values) == values
    assert _apply([_kitem()], [values], _Session(settings=PACK_SETTINGS))[0]["unit_canonical"] == "Case"  # 対照: 箱系は決まる
    # 人が直した行（skip）
    session = _Session(settings=PACK_SETTINGS)
    assert bb.apply_buyback_units(session, [_kitem()], [values], UNIT_IDS, ALIASES, POSTED_AT, frozenset({0}))[0] == values
    assert session.calls == []


def test_pack_is_decided_only_for_box_category_rows():
    old_path_item = _item()  # 単位も状態も語が無い古い対象（product_category 無し）
    values = _values(1000)
    assert _kapply(old_path_item, values) == values  # Pack と出ても箱系の分類でなければ何もしない
    assert _kapply(_kitem(), _kvalues("default", "Box", 1000))["unit_canonical"] == "Pack"


def test_pack_max_setting():
    assert bb.parse_settings(dict(PACK_SETTINGS)).pack_max == Decimal("0.2")
    assert bb.parse_settings(dict(GOOD_SETTINGS)).pack_max is None
    for bad in ("0", "-1", "0.5", "0.6", "x", "NaN", "Infinity"):  # 0 < pack_max < box_min でない
        assert bb.parse_settings({**dict(GOOD_SETTINGS), "unit_buyback_pack_max": bad}) is None
    values = _kvalues("default", "Box", 1000)
    assert _kapply(_kitem(), values, settings=GOOD_SETTINGS) == values  # key が無ければ Pack を決めない
    assert _kapply(_kitem(), values, settings=[*GOOD_SETTINGS, ("unit_buyback_pack_max", "0.5")]) == values  # 不正 = 設定全体が None


def test_labels_not_yet_written_stops_everything():
    unlabeled = [(c, i, n, g, u, (None if c in {"CN0003", "CN0001"} else d), uc) for c, i, n, g, u, d, uc in TARGET_ROWS]
    values = _kvalues("default", "Box", 10000)
    assert _kapply(_kitem(), values, targets=unlabeled) == values  # 札を入れる前の形 = 便全体で何もしない
    assert _kapply(_item(), _values(10000), targets=unlabeled) == _values(10000)


def test_duplicate_label_in_a_group_skips_only_that_kind_and_warns(caplog):
    rows = [*TARGET_ROWS, ("CN9001", 90, "Damaged sealed box 2", "box", 10, 3, "Box")]
    values = _kvalues("damaged", "Box", 10000)
    with caplog.at_level("WARNING"):
        assert _kapply(_kitem(basis="R2:ダメージ"), values, targets=rows) == values  # 札 3 が箱の群に 2 行
    assert any("札 3" in r.message and "CN0004" in r.message and "CN9001" in r.message for r in caplog.records)  # (a)
    assert _kapply(_kitem(), _kvalues("default", "Box", 10000), targets=rows)["condition_canonical"] == "Sealed box"  # 他の種類は決まる


def test_label_less_unit_mixed_in_pack_group_stops_only_pack_and_warns(caplog):
    rows = [(c, i, n, g, (12 if g == "pack" and c == "CN0010" else u), d, uc) for c, i, n, g, u, d, uc in TARGET_ROWS]
    values = _kvalues("default", "Box", 1000)
    with caplog.at_level("WARNING"):
        assert _kapply(_kitem(), values, targets=rows) == values  # Pack は決めない
        assert _kapply(_kitem(), _kvalues("default", "Box", 120000), targets=rows)["unit_canonical"] == "Case"  # Box・Case は決まる
        assert _kapply(_kitem(), _kvalues("default", "Box", 10000), targets=rows)["unit_canonical"] == "Box"
    assert any("群 pack" in r.message and "unit_id" in r.message for r in caplog.records)  # (c)


def test_pack_group_without_default_row_warns_but_box_and_case_still_decide(caplog):
    rows = [r for r in TARGET_ROWS if r[0] != "CN0007"]
    with caplog.at_level("WARNING"):
        values = _kvalues("default", "Box", 1000)
        assert _kapply(_kitem(), values, targets=rows) == values  # 既定の Pack 行が無いので Pack の既定は決まらない
        assert _kapply(_kitem(), _kvalues("default", "Box", 10000), targets=rows)["unit_canonical"] == "Box"
        searched = _kapply(_kitem(basis="R2:サーチ済"), _kvalues("searched", "Box", 1000), targets=rows)
        assert searched["condition_canonical"] == "Searched pack"
    assert any("群 pack" in r.message and "既定" in r.message for r in caplog.records)  # (b)


def test_box_or_case_group_without_exactly_one_default_stops_everything():
    no_case_default = [r for r in TARGET_ROWS if r[0] != "CN0001"]
    two_box_defaults = [*TARGET_ROWS, ("CN9002", 91, "Sealed box 2", "box", 10, 7, "Box")]
    values = _kvalues("default", "Box", 10000)
    assert _kapply(_kitem(), values, targets=no_case_default) == values
    assert _kapply(_kitem(), values, targets=two_box_defaults) == values


def test_does_not_mutate_input_in_the_new_paths():
    values = _kvalues("damaged", "Box", 10000, reasons="condition_multiple_candidates")
    original = dict(values)
    _kapply(_kitem(basis="R2:ダメージ"), values)
    assert values == original


def test_basis_is_cut_at_100_chars():
    long_basis = "R2:" + "あ" * 95
    values = _kvalues("damaged", "Box", 120000)
    out = _kapply(_kitem(basis=long_basis), {**values, "condition_basis": long_basis})
    assert len(out["condition_basis"]) == 100 and out["condition_basis"].startswith("R2:")


# --- 原文に単位の語が書いてあれば原文が優先される（PO 2026-10-21） ---------------------------------------------

@pytest.mark.parametrize(("line", "alias"), [
    ("ポケモンカード テラスタル サーチ済みパック @300", "パック"),
    ("ポケモンカード テラスタル サーチ済みBOX @300", "BOX"),
    ("ポケモンカード テラスタル 未開封カートン @300", "カートン"),
])
def test_unit_word_in_a_glued_line_wins_over_price(line, alias):
    from app.services import gemini_raw_copy_v102_product_first as pf  # noqa: PLC0415

    item = {"lines": [1], "price_line": 1, "gemini_index": 0}
    found, basis = pf.find_unit_product_first(
        item, {1: "price"}, [line], list(ALIASES), SimpleNamespace(matched_keywords={}), [], lambda _line: None, ALIASES,
    )
    assert found == alias and basis["alias"] == alias
    candidate = _kitem(alias=found)
    assert bb.is_candidate(candidate, _values(), ALIASES) is False  # 単位の語で決まった行は値段では決めない
