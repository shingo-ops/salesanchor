"""型番（品番・マーク）の重なり判定 tcg_product_code_collision_svc の単体試験。

DB は fake。SQL の is_active 絞り込みは SQL 文字列の検査と、
PG 実機試験（test_tcg_product_code_collision_pg.py、CI で実行）で守る。
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services import tcg_product_code_collision_svc as svc

pytestmark = pytest.mark.asyncio


def make_db(products, search=None, exclude=None):
    """products: (id, name, product_code, mark, work_name) の一覧。
    search / exclude: {product_id: [keyword, ...]}。"""
    seen_sql: list[str] = []

    async def execute(query, params=None):
        sql = str(query)
        seen_sql.append(sql)
        if "FROM public.products" in sql:
            return SimpleNamespace(fetchall=lambda: list(products))
        table = "search" if "product_search_keywords" in sql else "exclude"
        source = (search if table == "search" else exclude) or {}
        ids = set(params["ids"])
        rows = [(pid, kw) for pid, kws in source.items() if pid in ids for kw in kws]
        return SimpleNamespace(fetchall=lambda: rows)

    db = SimpleNamespace(execute=AsyncMock(side_effect=execute))
    db.seen_sql = seen_sql
    return db


async def find(db, **overrides):
    args = dict(
        product_code="PM0100",
        mark="",
        name="自分の商品",
        search_keywords=[],
        exclude_keywords=[],
    )
    args.update(overrides)
    return await svc.find_code_collisions(db, **args)


async def test_matches_mark_after_normalization():
    db = make_db([(1, "相手の箱", "PM0001", "ST-01", "ワンピース")])

    result = await find(db, mark="st01")

    assert [r["product_id"] for r in result] == ["1"]
    assert result[0]["matched_field"] == "mark"
    assert result[0]["matched_value"] == "ST-01"
    assert result[0]["work_name"] == "ワンピース"
    assert result[0]["name"] == "相手の箱"


async def test_matches_product_code_field_of_other_product():
    db = make_db([(1, "相手", "AB-12", None, "作品")])

    result = await find(db, product_code="ab12")

    assert result[0]["matched_field"] == "product_code"
    assert result[0]["matched_value"] == "AB-12"


async def test_mark_can_match_other_product_code():
    db = make_db([(1, "相手", "ST01", None, "作品")])

    result = await find(db, mark="ST-01")

    assert result[0]["matched_field"] == "product_code"


async def test_collision_across_works_is_returned():
    db = make_db([
        (1, "A箱", "PM0001", "EB01", "ワンピース"),
        (2, "B箱", "PM0002", "EB-01", "ポケモン"),
    ])

    result = await find(db, mark="EB01")

    assert [r["work_name"] for r in result] == ["ワンピース", "ポケモン"]


async def test_excludes_self_by_product_id():
    db = make_db([
        (7, "自分", "PM0007", "ST01", "作品"),
        (8, "相手", "PM0008", "ST01", "作品"),
    ])

    result = await find(db, mark="ST01", exclude_product_id=7)

    assert [r["product_id"] for r in result] == ["8"]


async def test_empty_values_are_ignored_and_never_match_blank_marks():
    db = make_db([(1, "相手", "", None, "作品"), (2, "相手2", "PM0002", "", "作品")])

    result = await find(db, product_code="", mark="")

    assert result == []


async def test_no_match_returns_empty_list():
    db = make_db([(1, "相手", "PM0001", "ST01", "作品")])

    assert await find(db, mark="ST99") == []


async def test_one_entry_per_product_even_if_both_fields_match():
    db = make_db([(1, "相手", "ST01", "ST-01", "作品")])

    result = await find(db, product_code="ST01", mark="ST-01")

    assert len(result) == 1


async def test_only_active_products_are_selected_in_sql_and_read_only():
    db = make_db([])

    await find(db, mark="ST01")

    products_sql = db.seen_sql[0]
    assert "is_active = TRUE" in products_sql
    assert all(sql.lstrip().upper().startswith("SELECT") for sql in db.seen_sql)


async def test_suggest_add_to_this_uses_other_name_and_non_code_keywords():
    db = make_db(
        [(1, "ONE PIECEカードゲーム 公式デッキ", "PM0001", "ST01", "ワンピース")],
        search={1: ["ST-01", "ルフィデッキ", "公式デッキ"]},
    )

    result = await find(db, mark="ST01", name="自分", search_keywords=["自分デッキ"])

    suggested = result[0]["suggest_add_to_this"]
    assert "ONE PIECEカードゲーム 公式デッキ" in suggested
    assert "ルフィデッキ" in suggested
    assert "ST-01" not in suggested  # 相手の型番と同じ語は推奨しない


async def test_suggest_skips_short_words_words_inside_own_text_and_already_excluded():
    db = make_db(
        [(1, "相手の商品", "PM0001", "ST01", "作品")],
        search={1: ["ab", "デッキ", "共通語", "既に除外"]},
    )

    result = await find(
        db,
        mark="ST01",
        name="自分のデッキ",
        search_keywords=["共通語セット"],
        exclude_keywords=["既に除外"],
    )

    suggested = result[0]["suggest_add_to_this"]
    assert "ab" not in suggested  # 正規化後3文字未満
    assert "デッキ" not in suggested  # 自分の名前に含まれる
    assert "共通語" not in suggested  # 自分の検索ワードに含まれる
    assert "既に除外" not in suggested  # 自分の除外ワードに既にある
    assert "相手の商品" in suggested


async def test_suggest_normalizes_katakana_and_width():
    db = make_db(
        [(1, "相手", "PM0001", "ST01", "作品")],
        search={1: ["ルフィ"]},
    )

    result = await find(db, mark="ST01", name="るふぃのデッキ")

    assert "ルフィ" not in result[0]["suggest_add_to_this"]


async def test_suggest_add_to_other_is_the_mirror_image():
    db = make_db(
        [(1, "相手の商品", "PM0001", "ST01", "作品")],
        search={1: ["相手語"]},
        exclude={1: ["既に相手が除外"]},
    )

    result = await find(
        db,
        mark="ST01",
        name="自分の箱",
        search_keywords=["ST-01", "ゾロデッキ", "ab"],
    )

    other = result[0]["suggest_add_to_other"]
    assert "自分の箱" in other
    assert "ゾロデッキ" in other
    assert "ST-01" not in other  # 自分の型番と同じ語
    assert "ab" not in other


async def test_suggest_add_to_other_skips_words_already_excluded_by_other():
    db = make_db(
        [(1, "相手", "PM0001", "ST01", "作品")],
        exclude={1: ["自分の箱"]},
    )

    result = await find(db, mark="ST01", name="自分の箱")

    assert "自分の箱" not in result[0]["suggest_add_to_other"]
    assert result[0]["already_excluded_by_other"] == ["自分の箱"]


async def test_already_excluded_by_this_lists_effective_exclude_words():
    db = make_db(
        [(1, "相手の公式デッキ", "PM0001", "ST01", "作品")],
        search={1: ["ルフィ"]},
    )

    result = await find(
        db, mark="ST01", exclude_keywords=["公式デッキ", "無関係な語"]
    )

    assert result[0]["already_excluded_by_this"] == ["公式デッキ"]


async def test_result_keys_are_fixed():
    db = make_db([(1, "相手", "PM0001", "ST01", "作品")])

    result = await find(db, mark="ST01")

    assert set(result[0]) == {
        "product_id",
        "name",
        "work_name",
        "matched_value",
        "matched_field",
        "suggest_add_to_this",
        "suggest_add_to_other",
        "already_excluded_by_this",
        "already_excluded_by_other",
    }
