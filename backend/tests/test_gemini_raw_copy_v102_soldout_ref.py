# ruff: noqa: F811
"""試作版 v102：〆（完売）の件の商品を、同じ仕入元の過去48時間の投稿から決める処理（matched_soldout_ref）の試験。

原文は社外秘のため使わない。商品名・型番はすべて作り例。純粋関数の試験は DB に触れない。
DB を読む関数（load_soldout_ref_posts）の試験は CI の使い捨て PostgreSQL 専用（test_gemini_raw_copy_v102_followup.py と同じ書き方）。
"""
from __future__ import annotations

import dataclasses
import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

import app.services.line_analysis_v102_svc as svc
from app.services import gemini_raw_copy_v101 as v101
from app.services import gemini_raw_copy_v102_soldout_ref as sr
from app.services.extraction_judgement_svc import ProductEntry
from app.services.gemini_raw_copy_v102_product_first import ProductFirstMasters, WorkName
from tests.test_gemini_raw_copy_v102_context_work import _MASTERS, _STATUS
from tests.test_tcg_work_matching_integration import MIGRATIONS, SCHEMA
from tests.test_tcg_work_matching_integration import pg as pg  # noqa: F401  fixture

_SOLD_STATUS = [
    {"canonical": "Sold out", "search_pattern": "〆", "exclude_pattern": "", "priority": 1, "match_type": "LITERAL", "effect": "EXCLUDE"},
    {"canonical": "Sold out", "search_pattern": "完売御礼", "exclude_pattern": "", "priority": 2, "match_type": "LITERAL", "effect": "EXCLUDE"},
    *_STATUS,
]
_SOLD_WORDS = ["〆", "完売御礼"]
_MASTERS_SOLD = {**_MASTERS, "status_entries": _SOLD_STATUS}


def _p(pid, work, *kws):
    return ProductEntry(id=pid, product_code=None, mark=None, work_id=work, search_keywords=tuple(kws), exclude_keywords=())


# 62・63 は名前で決まる商品。71・72 は「共通ひよこ」を共有する（71 だけ「ひよこ甲」を持つ）
_PRODUCTS = (_p(62, 1, "ふぁいぶ"), _p(63, 1, "ぴよぴよ"), _p(71, 1, "共通ひよこ", "ひよこ甲"), _p(72, 1, "共通ひよこ"))
_KUBUN = {"62": "箱系", "63": "箱系", "71": "箱系", "72": "箱系"}
_MASTER = ProductFirstMasters(product_entries=_PRODUCTS, product_kubun=_KUBUN, condition_unit={"Sealed box": "Box"}, ignore_phrases=())
T0 = datetime(2026, 10, 9, 12, 0, tzinfo=timezone.utc)

# 作品名の〆の材料: 81・82 は中分類 2、91 は中分類 3。中分類の名前はカタカナ（名前の語は4文字以上のカタカナ・漢字・英字だけ）
_MASTER_W = dataclasses.replace(
    _MASTER,
    product_entries=(*_PRODUCTS, _p(81, 2, "どらごん甲"), _p(82, 2, "どらごん乙"), _p(91, 3, "ぽけもん丙")),
    product_kubun={**_KUBUN, "81": "箱系", "82": "箱系", "91": "箱系"},
    work_names=(WorkName(2, ("ドラゴンアイル",)), WorkName(3, ("ポケモンアイル",))),
)
_PLURAL = ("全て", "両方")
_COND_A, _COND_B = 11, 12


def _post(message_id: str, raw: str, hours_before: float = 1.0, stock_items: tuple = ()) -> sr.SoldoutRefPost:
    return sr.SoldoutRefPost(message_id, T0 - timedelta(hours=hours_before), raw, stock_items)


def _si(lines, product_id: int, condition_id: int = _COND_A) -> sr.StockItem:
    return sr.StockItem(frozenset(lines), product_id, condition_id)


def _targets(row: dict) -> list[tuple[int, int, str, int]]:
    return [(t["product_id"], t["condition_id"], t["ref_message_id"], t["ref_line"]) for t in row.get("soldout_targets", [])]


def _extract(raw: str, posts, plural_words: tuple[str, ...] = (), fixed_products: dict[int, int] | None = None, master=_MASTER):
    """posts は新しい順。今の投稿の行に価格が無ければ「 3@1,500円」を足す。"""
    raw = "\n".join(ln if "1,500円" in ln or not ln.strip() else f"{ln} 3@1,500円" for ln in raw.split("\n"))
    lines = raw.split("\n")
    items = [{"lines": [i + 1], "price": "1,500円", "quantity": "3"} for i, ln in enumerate(lines) if ln.strip()]
    parsed, errors = v101.parse_v101_response(json.dumps({"items": items}, ensure_ascii=False), raw, status_entries=_SOLD_STATUS)
    assert errors == []
    rows, _flags = v101.extract_v101_items(
        parsed, raw, order=None, reassign=True, v102_fixes=True,
        product_first=dataclasses.replace(master, followup_plural_words=plural_words),
        soldout_posts=posts, fixed_products=fixed_products, **_MASTERS_SOLD,
    )
    return rows


STOCK = "ふぁいぶ ABC-123 3@1,500円\nぴよぴよ DEF-456 3@1,500円"


def test_no_posts_changes_nothing():
    raw = "ABC-123 〆"
    for posts in (None, ()):
        row = _extract(raw, posts)[0]
        assert row["status_effect"] == "excluded"
        assert row["match_status"] == "unmatched" and "product_soldout_ref" not in row


def test_soldout_row_is_decided_by_the_stock_row_of_an_earlier_post():
    row = _extract("ABC-123 〆", (_post("p1", STOCK),))[0]
    assert (row["match_status"], row["product_id"]) == ("matched_soldout_ref", 62)
    assert row["product_soldout_ref"] == {"ref_message_id": "p1", "ref_line": 1, "tokens": ["abc-123"]}
    assert row["status_effect"] == "excluded"


def test_row_that_is_not_soldout_is_not_a_target():
    row = _extract("ABC-123 追加 3@1,500円", (_post("p1", STOCK),))[0]
    assert row["match_status"] == "unmatched" and "product_soldout_ref" not in row


def test_already_matched_soldout_row_is_untouched():
    raw = "ふぁいぶ DEF-456 〆"  # 自分で 62 に決まる。参照は 63 を指すが触らない
    row = _extract(raw, (_post("p1", STOCK),))[0]
    assert (row["match_status"], row["product_id"]) == ("matched", 62) and "product_soldout_ref" not in row


def test_stops_at_the_newest_post_that_hits():
    newer = _post("new", "ぴよぴよ ABC-123 3@1,500円", 1)
    older = _post("old", "ふぁいぶ ABC-123 3@1,500円", 5)
    row = _extract("ABC-123 〆", (newer, older))[0]
    assert (row["product_id"], row["product_soldout_ref"]["ref_message_id"]) == (63, "new")


def test_newest_hit_post_with_only_sold_rows_does_not_fall_back_to_older_posts():
    newer = _post("new", "ふぁいぶ ABC-123 〆", 1)  # 当たりは〆の行だけ → 0 → 決めない
    older = _post("old", "ふぁいぶ ABC-123 3@1,500円", 5)
    row = _extract("ABC-123 〆", (newer, older))[0]
    assert row["match_status"] == "unmatched" and row["product_id"] is None


def test_older_post_than_the_hit_is_not_consulted_for_a_different_product():
    newer = _post("new", "ふぁいぶ ABC-123 3@1,500円", 1)
    older = _post("old", "ぴよぴよ ABC-123 3@1,500円", 5)
    assert _extract("ABC-123 〆", (newer, older))[0]["product_id"] == 62


def test_stock_row_already_sold_by_a_later_post_does_not_decide():
    later = _post("later", "ふぁいぶ 〆", 1)
    earlier = _post("earlier", "ふぁいぶ ABC-123 3@1,500円", 5)
    row = _extract("ABC-123 〆", (later, earlier))[0]
    assert row["match_status"] == "unmatched" and row["product_id"] is None


def test_stock_row_already_sold_by_a_later_line_of_the_same_post_does_not_decide():
    row = _extract("ABC-123 〆", (_post("p1", "ふぁいぶ ABC-123 3@1,500円\nふぁいぶ 〆"),))[0]
    assert row["match_status"] == "unmatched"


def test_sold_row_before_the_stock_row_does_not_cancel_it():
    earlier = _post("earlier", "ふぁいぶ 〆", 5)
    later = _post("later", "ふぁいぶ ABC-123 3@1,500円", 1)
    assert _extract("ABC-123 〆", (later, earlier))[0]["product_id"] == 62


def test_sold_out_cancels_per_product_not_per_post():
    post = _post("p1", "ふぁいぶ ABC-123 3@1,500円\nぴよぴよ ABC-123 3@1,500円\nふぁいぶ 〆")
    assert _extract("ABC-123 〆", (post,))[0]["product_id"] == 63  # 62 はすでに〆、残るのは 63 だけ


def test_two_products_hit_does_not_decide():
    row = _extract("ABC-123 〆", (_post("p1", "ふぁいぶ ABC-123 3@1,500円\nぴよぴよ ABC-123 3@1,500円"),))[0]
    assert row["match_status"] == "unmatched" and row["product_id"] is None


def test_all_tokens_must_hit_one_reference_row():
    row = _extract("ABC-123 DEF-456 〆", (_post("p1", STOCK),))[0]  # 2語は別々の行に当たる
    assert row["match_status"] == "unmatched" and row["product_id"] is None


def test_no_token_does_not_decide():
    for raw in ("〆", "BOX 〆"):  # 語が残らない／単位の語だけ
        row = _extract(raw, (_post("p1", "ふぁいぶ BOX 3@1,500円"),))[0]
        assert row["match_status"] == "unmatched" and row["product_id"] is None


def test_plural_word_does_not_decide_when_a_stock_row_has_no_counterpart():
    # 書き換えた理由: 便1では「複数語があれば常に決めない」だったが、規則8で複数語の〆も対象になった。
    # 今は「複数語で、相手（stock_items）が無い在庫の行があれば決めない」（規則11）。STOCK の投稿には stock_items が無い。
    row = _extract("ABC-123 両方 〆", (_post("p1", STOCK),), plural_words=("両方",))[0]
    assert row["match_status"] == "unmatched" and row["product_id"] is None and "soldout_targets" not in row


def test_plural_word_decides_when_every_stock_row_has_a_counterpart():
    post = _post("p1", STOCK, stock_items=(_si([1], 62),))
    row = _extract("ABC-123 両方 〆", (post,), plural_words=("両方",))[0]
    assert (row["match_status"], row["product_id"]) == ("matched_soldout_ref", 62)
    assert _targets(row) == [(62, _COND_A, "p1", 1)]
    assert row["product_soldout_ref"]["tokens"] == ["abc-123"]  # 複数語は手がかりの語から外れている


def test_plural_word_decides_several_products_of_the_same_token():
    post = _post("p1", "ふぁいぶ ABC-123 3@1,500円\nぴよぴよ ABC-123 3@1,500円", stock_items=(_si([1], 62), _si([2], 63, _COND_B)))
    row = _extract("ABC-123 両方 〆", (post,), plural_words=_PLURAL)[0]
    assert (row["match_status"], row["product_id"]) == ("matched_soldout_ref", 62)  # product_id は targets[0]
    assert _targets(row) == [(62, _COND_A, "p1", 1), (63, _COND_B, "p1", 2)]


def test_one_product_with_two_conditions_gives_two_targets():
    post = _post("p1", "ふぁいぶ ABC-123 3@1,500円", stock_items=(_si([1], 62, _COND_A), _si([1], 62, _COND_B)))
    row = _extract("ABC-123 全て〆", (post,), plural_words=_PLURAL)[0]
    assert _targets(row) == [(62, _COND_A, "p1", 1), (62, _COND_B, "p1", 1)]


def test_duplicate_counterparts_are_kept_once():
    post = _post("p1", "ふぁいぶ ABC-123 3@1,500円\nふぁいぶ ABC-123 5@1,500円", stock_items=(_si([1], 62), _si([2], 62)))
    row = _extract("ABC-123 全て〆", (post,), plural_words=_PLURAL)[0]
    assert _targets(row) == [(62, _COND_A, "p1", 1)]


def test_plural_word_does_not_decide_when_a_clue_line_has_no_product():
    # 2行目は語が当たるのに商品が決まらない（「30th 両方〆」で片方だけ完売にしない）
    post = _post("p1", "ふぁいぶ ABC-123 3@1,500円\nなぞ ABC-123 3@1,500円", stock_items=(_si([1], 62),))
    row = _extract("ABC-123 両方 〆", (post,), plural_words=_PLURAL)[0]
    assert row["match_status"] == "unmatched" and row["product_id"] is None


def test_clue_line_without_product_is_ignored_when_it_contains_a_sold_word():
    post = _post("p1", "ふぁいぶ ABC-123 3@1,500円\nなぞ ABC-123 〆", stock_items=(_si([1], 62),))
    assert _extract("ABC-123 両方 〆", (post,), plural_words=_PLURAL)[0]["product_id"] == 62


def test_single_product_without_plural_word_keeps_the_stock_condition_when_it_is_known():
    row = _extract("ABC-123 〆", (_post("p1", STOCK, stock_items=(_si([1], 62, _COND_B),)),))[0]
    assert (row["match_status"], row["product_id"]) == ("matched_soldout_ref", 62)
    assert _targets(row) == [(62, _COND_B, "p1", 1)]


def test_single_product_without_plural_word_decides_the_product_only_when_no_counterpart():
    row = _extract("ABC-123 〆", (_post("p1", STOCK),))[0]
    assert (row["match_status"], row["product_id"]) == ("matched_soldout_ref", 62) and "soldout_targets" not in row


def test_single_product_without_plural_word_has_no_target_when_one_stock_row_lacks_a_counterpart():
    post = _post("p1", "ふぁいぶ ABC-123 3@1,500円\nふぁいぶ ABC-123 5@1,500円", stock_items=(_si([1], 62),))
    row = _extract("ABC-123 〆", (post,))[0]
    assert (row["match_status"], row["product_id"]) == ("matched_soldout_ref", 62) and "soldout_targets" not in row


def test_plural_ambiguous_with_a_product_outside_the_candidates_does_not_decide():
    post = _post("p1", "ひよこ甲 ZZZ-777 3@1,500円\nぴよぴよ ZZZ-777 3@1,500円", stock_items=(_si([1], 71), _si([2], 63)))
    row = _extract("共通ひよこ ZZZ-777 両方 〆", (post,), plural_words=_PLURAL)[0]  # 候補は 71・72。63 は候補外
    assert row["match_status"] == "ambiguous" and row["product_id"] is None


def test_plural_word_does_not_make_an_already_sold_stock_row_a_target():
    later = _post("later", "ふぁいぶ 〆", 1)
    earlier = _post("earlier", "ふぁいぶ ABC-123 3@1,500円\nぴよぴよ ABC-123 3@1,500円", 5, (_si([1], 62), _si([2], 63)))
    row = _extract("ABC-123 全て〆", (later, earlier), plural_words=_PLURAL)[0]
    assert (row["product_id"], _targets(row)) == (63, [(63, _COND_A, "earlier", 2)])


def test_plural_word_stops_at_the_newest_post_that_hits():
    newer = _post("new", "ぴよぴよ ABC-123 3@1,500円", 1, (_si([1], 63),))
    older = _post("old", "ふぁいぶ ABC-123 3@1,500円", 5, (_si([1], 62),))
    row = _extract("ABC-123 全て〆", (newer, older), plural_words=_PLURAL)[0]
    assert _targets(row) == [(63, _COND_A, "new", 1)]


# --- 作品名の〆（規則9）-------------------------------------------------------------------------

_WORK_POST_RAW = "どらごん甲 3@1,500円\nどらごん乙 3@1,500円\nぽけもん丙 3@1,500円"
_WORK_STOCK = (_si([1], 81), _si([2], 82, _COND_B), _si([3], 91))


def test_work_name_soldout_decides_every_product_of_that_work():
    row = _extract("ドラゴンアイル 全て〆", (_post("p1", _WORK_POST_RAW, stock_items=_WORK_STOCK),), _PLURAL, master=_MASTER_W)[0]
    assert (row["match_status"], row["product_id"]) == ("matched_soldout_ref", 81)
    assert _targets(row) == [(81, _COND_A, "p1", 1), (82, _COND_B, "p1", 2)]  # 中分類 3 の 91 は入らない
    assert row["product_soldout_ref"]["tokens"] == []  # 作品名の語は手がかりから外れる


def test_work_name_is_not_used_without_a_plural_word():
    row = _extract("ドラゴンアイル 〆", (_post("p1", _WORK_POST_RAW, stock_items=_WORK_STOCK),), _PLURAL, master=_MASTER_W)[0]
    assert row["match_status"] == "unmatched" and row["product_id"] is None


def test_work_name_soldout_with_two_work_names_does_not_decide():
    row = _extract("ドラゴンアイル ポケモンアイル 全て〆", (_post("p1", _WORK_POST_RAW, stock_items=_WORK_STOCK),), _PLURAL, master=_MASTER_W)[0]
    assert row["match_status"] == "unmatched" and row["product_id"] is None


def test_work_name_soldout_requires_the_remaining_tokens_to_hit_too():
    raw = "どらごん甲 ZZZ-111 3@1,500円\nどらごん乙 3@1,500円"
    row = _extract("ドラゴンアイル ZZZ-111 全て〆", (_post("p1", raw, stock_items=(_si([1], 81), _si([2], 82))),), _PLURAL, master=_MASTER_W)[0]
    assert _targets(row) == [(81, _COND_A, "p1", 1)]


def test_work_name_soldout_ignores_a_clue_line_without_product():
    raw = "どらごん甲 3@1,500円\nなぞの行 3@1,500円"
    row = _extract("ドラゴンアイル 全て〆", (_post("p1", raw, stock_items=(_si([1], 81),)),), _PLURAL, master=_MASTER_W)[0]
    assert (row["product_id"], _targets(row)) == (81, [(81, _COND_A, "p1", 1)])


def test_work_name_soldout_with_a_stock_row_without_counterpart_does_not_decide():
    row = _extract("ドラゴンアイル 全て〆", (_post("p1", _WORK_POST_RAW, stock_items=(_si([1], 81),)),), _PLURAL, master=_MASTER_W)[0]
    assert row["match_status"] == "unmatched" and row["product_id"] is None


def test_work_name_soldout_with_no_stock_row_of_that_work_does_not_decide():
    row = _extract("ポケモンアイル 全て〆", (_post("p1", "どらごん甲 3@1,500円", stock_items=(_si([1], 81),)),), _PLURAL, master=_MASTER_W)[0]
    assert row["match_status"] == "unmatched" and row["product_id"] is None


def test_human_decided_row_gets_no_targets():
    post = _post("p1", STOCK, stock_items=(_si([1], 62),))
    row = _extract("ABC-123 〆", (post,), fixed_products={0: 63})[0]
    assert (row["match_status"], row["product_id"]) == ("matched", 63) and "soldout_targets" not in row


def test_sold_out_words_are_removed_before_taking_tokens():
    # 「完売御礼」は漢字4文字で、取り除かないと名前の語になり、参照行に当たらず決まらない
    row = _extract("ABC-123 完売御礼", (_post("p1", STOCK),))[0]
    assert (row["match_status"], row["product_id"]) == ("matched_soldout_ref", 62)
    assert row["product_soldout_ref"]["tokens"] == ["abc-123"]


def test_sold_out_word_in_a_reference_line_makes_it_a_sold_row():
    row = _extract("ABC-123 〆", (_post("p1", "ふぁいぶ ABC-123 完売御礼"),))[0]
    assert row["match_status"] == "unmatched"


def test_ambiguous_outside_candidates_does_not_decide():
    row = _extract("共通ひよこ ABC-123 〆", (_post("p1", STOCK),))[0]  # 候補は 71・72。ABC-123 は 62 を指す
    assert row["match_status"] == "ambiguous" and row["product_id"] is None


def test_ambiguous_inside_candidates_decides():
    row = _extract("共通ひよこ ZZZ-777 〆", (_post("p1", "ひよこ甲 ZZZ-777 3@1,500円"),))[0]
    assert (row["match_status"], row["product_id"]) == ("matched_soldout_ref", 71)


def test_human_decided_row_is_not_overwritten():
    raw = "ABC-123 〆"
    assert _extract(raw, (_post("p1", STOCK),))[0]["match_status"] == "matched_soldout_ref"
    row = _extract(raw, (_post("p1", STOCK),), fixed_products={0: 63})[0]
    assert (row["match_status"], row["product_id"]) == ("matched", 63) and "product_soldout_ref" not in row


def test_reference_rows_are_not_built_when_there_is_no_target(monkeypatch):
    def boom(*_a, **_k):
        raise AssertionError("対象の件が無いのに参照行を作ってはいけない")

    monkeypatch.setattr(v101, "build_ref_rows", boom)
    row = _extract("ABC-123 追加 3@1,500円", (_post("p1", STOCK),))[0]
    assert row["match_status"] == "unmatched"


def test_build_ref_rows_marks_sold_rows_and_orders_oldest_first():
    newer = _post("new", "\nぴよぴよ 〆", 1)
    older = _post("old", "ふぁいぶ ABC-123\nなにもない行", 5)
    rows = sr.build_ref_rows((newer, older), _MASTER, _SOLD_WORDS)
    assert [(r.message_id, r.line_no, r.product_id, r.is_sold, r.post_index) for r in rows] == [
        ("old", 1, 62, False, 1), ("new", 2, 63, True, 0),
    ]
    assert rows[0].order < rows[1].order


# --- 参照する投稿を読む関数（CI の使い捨て PostgreSQL 専用）-------------------------------------


def _insert(connection, channel_id, raw: str, posted_at, *, active: bool = True) -> str:
    message_id = str(uuid4())
    with connection.cursor() as cur:
        cur.execute(
            f"""INSERT INTO {SCHEMA}.source_messages (id,supplier_channel_id,raw_text,raw_sha256,is_active,received_at,line_posted_at)
                VALUES (%s,%s,%s,%s,%s,now(),%s)""",
            (message_id, channel_id, raw, uuid4().hex, active, posted_at),
        )
    return message_id


def _job(connection, message_id: str) -> str:
    job_id = str(uuid4())
    with connection.cursor() as cur:
        cur.execute(f"INSERT INTO {SCHEMA}.extraction_jobs(id,source_message_id,status) VALUES (%s,%s,'pending')", (job_id, message_id))
    return job_id


@pytest.fixture
def channel(pg):  # noqa: F811
    with pg[0].cursor() as cur:
        # 在庫の件（source_lines など）を読むので、v102 の列を足す（test_line_analysis_v102_pg.py の v102 fixture と同じ置換）
        sql = (MIGRATIONS / "20261009_180000_v102_engine_columns.sql").read_text(encoding="utf-8")
        cur.execute(sql.replace("public.extraction_", f"{SCHEMA}.extraction_"))
        cur.execute(f"SELECT id FROM {SCHEMA}.supplier_channels LIMIT 1")
        return cur.fetchone()[0]


def _load(pg_fixture, job_id):
    with Session(pg_fixture[1]) as session:
        return svc.load_soldout_ref_posts(session, job_id)


def test_posts_within_48_hours_are_returned_newest_first_even_if_inactive(pg, channel):
    old = _insert(pg[0], channel, "古い", T0 - timedelta(hours=47), active=False)
    new = _insert(pg[0], channel, "新しい", T0 - timedelta(hours=2))
    job = _job(pg[0], _insert(pg[0], channel, "今", T0))
    assert [(p.message_id, p.raw_text) for p in _load(pg, job)] == [(new, "新しい"), (old, "古い")]


def test_post_exactly_48_hours_before_is_included_and_one_second_more_is_not(pg, channel):
    edge = _insert(pg[0], channel, "ちょうど", T0 - timedelta(seconds=svc.SOLDOUT_REF_MAX_GAP_SECONDS))
    _insert(pg[0], channel, "超過", T0 - timedelta(seconds=svc.SOLDOUT_REF_MAX_GAP_SECONDS + 1))
    job = _job(pg[0], _insert(pg[0], channel, "今", T0))
    assert [p.message_id for p in _load(pg, job)] == [edge]


def test_later_posts_and_same_time_posts_are_not_returned(pg, channel):
    _insert(pg[0], channel, "あと", T0 + timedelta(minutes=1))
    _insert(pg[0], channel, "同時刻", T0)
    job = _job(pg[0], _insert(pg[0], channel, "今", T0))
    assert _load(pg, job) == ()


def test_other_channel_posts_are_not_returned(pg, channel):
    with pg[0].cursor() as cur:
        cur.execute(f"SELECT id FROM {SCHEMA}.supplier_channels WHERE id <> %s LIMIT 1", (channel,))
        other = cur.fetchone()
    if other is None:
        pytest.skip("チャンネルが1つしかない")
    _insert(pg[0], other[0], "別の仕入元", T0 - timedelta(hours=1))
    job = _job(pg[0], _insert(pg[0], channel, "今", T0))
    assert _load(pg, job) == ()


def test_unknown_job_returns_empty(pg):
    assert _load(pg, str(uuid4())) == ()
