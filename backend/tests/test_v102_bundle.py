"""まとめ売り（N単位セット）の読み取りの検査（ADR-1027）。例文は検査用に自作した短いもの。"""
from __future__ import annotations

import importlib.util
from pathlib import Path

from app.services import v102_bundle_svc as svc
from app.services import line_analysis_v102_svc as line_svc
from app.services import tcg_distribution_svc as dist
from app.services.gemini_raw_copy_v102_product_first import PRODUCT_KUBUN_BULK

ALIASES = {"パック": "Pack", "pack": "Pack", "枚": "Piece", "個": "Item", "カートン": "Case", "セット": "Set", "set": "Set"}
WORDS, SET_WORDS = svc.split_unit_words(ALIASES)


def _d(block, price=26000, quantity=5):
    return svc.detect_bundle(block, WORDS, SET_WORDS, price, quantity)


def test_split_unit_words_excludes_set_canonical():
    assert "セット" not in WORDS and "set" not in WORDS
    assert SET_WORDS == frozenset({"セット", "set"})
    assert WORDS["パック"] == "Pack"


def test_split_unit_words_drops_conflicting_word():
    words, _ = svc.split_unit_words({"x": "Pack", "X": "Box"})
    assert "x" not in words


def test_b1_decided():
    r = _d("ABC 40パックセット 5セット 26000円", quantity=5)
    assert (r.kind, r.n, r.unit) == (svc.KIND_DECIDED, 40, "Pack")


def test_no_hit_returns_none():
    assert _d("ABC 5セット 26000円") is None
    assert _d("ABC 40パック 26000円") is None


def test_parenthesized_is_excluded():
    assert _d("ABC (40パックセット) 5セット 26000円") is None


def test_unclosed_parenthesis_runs_to_end_of_line():
    assert _d("ABC (40パックセット 5セット 26000円") is None
    r = _d("(メモ\n40パックセット 5セット 26000円")
    assert r is not None and r.kind == svc.KIND_DECIDED


def test_iri_after_is_excluded():
    assert _d("ABC 40パックセット入 5セット 26000円") is None


def test_n_of_one_is_excluded():
    assert _d("ABC 1パックセット 3セット 26000円", quantity=3) is None


def test_two_different_pairs_unverified():
    r = _d("40パックセット 100枚セット 26000円")
    assert r.kind == svc.KIND_UNVERIFIED and r.n is None


def test_same_pair_twice_is_one():
    assert _d("40パックセット / 40パックセット 5セット 26000円").kind == svc.KIND_DECIDED


def test_no_price_unverified():
    assert _d("40パックセット 5セット", price=None).kind == svc.KIND_UNVERIFIED


def test_quantity_divisible_without_set_is_unverified():
    assert _d("40パックセット 80 26000円", quantity=80).kind == svc.KIND_UNVERIFIED


def test_quantity_divisible_with_set_right_after_is_decided():
    assert _d("40パックセット 80セット 26000円", quantity=80).kind == svc.KIND_DECIDED


def test_set_alias_is_not_a_unit_word():
    assert _d("16セットまとめ 5セット 26000円") is None


def test_word_does_not_match_across_lines():
    assert _d("40パック\nセット 5セット 26000円") is None


def test_comma_in_number_is_removed():
    assert svc.normalize("1,000パック") == "1000パック"


def test_source_has_no_unit_words():
    src = Path(svc.__file__).read_text(encoding="utf-8")
    code = "\n".join(line for line in src.splitlines() if not line.lstrip().startswith("#"))
    body = code.split('"""', 2)[-1]  # モジュール説明文の後ろだけ見る
    for word in ("パック", "枚", "個", "カートン", '"pack"', '"piece"', '"box"'):
        assert word not in body.lower()


def test_bundle_title_sql_two_columns_and_gkey():
    ja, en = dist.bundle_title_sql()
    assert "ar.bundle_size" in ja and "ar.bundle_size" in en
    assert "セット" in ja and " Set" in en
    assert "name_ja" in ja and "name_en" in en


def _values(**kw):
    base = {"price_normalized": 26000, "quantity_normalized": 5, "unit_canonical": "Set", "unit_id": 13,
            "unit_resolved": True, "bundle_size": None, "review_reasons": None, "needs_review": False}
    return {**base, **kw}


def test_apply_bundle_unit_id_not_found_is_unverified():
    out = line_svc._apply_bundle(_values(), "40パックセット 5セット", WORDS, SET_WORDS, {"Piece": 12})
    assert out["bundle_size"] is None and out["unit_canonical"] == "Set"
    assert out["review_reasons"] == "bundle_unverified" and out["needs_review"] is True


def test_apply_bundle_decided_sets_unit():
    out = line_svc._apply_bundle(_values(), "40パックセット 5セット", WORDS, SET_WORDS, {"Pack": 14})
    assert (out["bundle_size"], out["unit_canonical"], out["unit_id"]) == (40, "Pack", 14)
    assert out["price_normalized"] == 26000 and out["quantity_normalized"] == 5


def test_gkey_includes_bundle_size_so_bundle_and_plain_rows_do_not_merge():
    """配信の同一投稿まとめの鍵 gkey に bundle_size が入る（有る行と無い行で鍵が違う）。"""
    sql = dist.distribution_rows_sql(include_flag_single=False, age_condition=" AND x = :y", merge_same_post=True)
    head = sql[: sql.index("AS gkey")]
    gkey_expr = head[head.rindex("concat_ws(") :]
    assert "COALESCE(ar.bundle_size::text, '')" in gkey_expr
    assert "COALESCE(ar.ship_ja, '')" in gkey_expr  # 既存の鍵の部品と同じ式の中にある


def test_word_not_in_alias_master_is_not_a_unit_word():
    """別名マスタに無い語（例「9種セット」の「種」）は単位の語にならず、当たらない側になる。"""
    assert "種" not in WORDS
    assert _d("ABC 9種セット 5セット 26000円") is None
    assert _d("ABC 9種セット 5セット", price=None) is None


def test_line_units_migration_adds_both_display_name_columns():
    """試験 DB には line_units が無く本番の migration を当てられない（migrate() は public.units のみ作る）ため、SQL の中身を直接確かめる。"""
    path = Path(__file__).resolve().parents[2] / "migrations" / "20261017_220100_add_line_units_display_names.sql"
    sql = path.read_text(encoding="utf-8")
    assert "ALTER TABLE public.line_units" in sql
    assert "ADD COLUMN IF NOT EXISTS name_ja text" in sql
    assert "ADD COLUMN IF NOT EXISTS name_en text" in sql


# --- バルク系だけの追加の形 P1・P2（設計 bundle-sale §12。例文は自作） -----------------------------------

def _b(block, price=10000, quantity=12, bulk_shapes=True):
    return svc.detect_bundle(block, WORDS, SET_WORDS, price, quantity, bulk_shapes=bulk_shapes)


def test_bulk_p1_parenthesized_bundle_is_decided_only_with_bulk_shapes():
    block = "✅RR バルク(100枚)\n@10000 在庫数 12セット"
    r = _b(block)
    assert (r.kind, r.n, r.unit) == (svc.KIND_DECIDED, 100, "Piece")
    assert _b(block, bulk_shapes=False) is None
    assert _d(block, price=10000, quantity=12) is None  # 既定（引数なし）は今まで通り


def test_bulk_p1_space_just_inside_parens_is_not_read():
    assert _b("✅RR バルク( 100枚 )\n@10000 在庫数 12セット") is None


def test_bulk_p2_needs_set_right_after_quantity():
    block = "まとめ 100枚\n@24000 在庫数18セット"
    r = _b(block, price=24000, quantity=18)
    assert (r.kind, r.n, r.unit) == (svc.KIND_DECIDED, 100, "Piece")
    assert _b("まとめ 100枚\n@24000 在庫 20", price=24000, quantity=20) is None
    assert _b(block, price=24000, quantity=None) is None
    assert _b(block, price=24000, quantity=18, bulk_shapes=False) is None


def test_bulk_shapes_do_not_read_contents_description():
    assert _b("バルク(100枚入)\n@10000 在庫数 12セット") is None
    assert _b("まとめ 100枚入\n@3000 在庫 5セット", price=3000, quantity=5) is None


def test_bulk_shapes_mixed_sizes_are_unverified():
    r = _b("50枚セット\nバルク(100枚)\n@5000 在庫 3セット", price=5000, quantity=3)
    assert r.kind == svc.KIND_UNVERIFIED


def test_bulk_shapes_past_mistake_shapes_stay_none():
    for flag in (True, False):
        assert _b("シングル 10000円(合計34枚セット)", price=10000, quantity=1, bulk_shapes=flag) is None
        assert _b("BULK 200枚 ¥4300", price=4300, quantity=None, bulk_shapes=flag) is None


def test_replay_script_bulk_constant_matches_product_first():
    path = Path(svc.__file__).resolve().parents[3] / "scripts" / "dev" / "bundle_replay.py"
    spec = importlib.util.spec_from_file_location("bundle_replay_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # `if __name__ == "__main__"` のため main は走らない
    assert module._BULK_KUBUN == PRODUCT_KUBUN_BULK
