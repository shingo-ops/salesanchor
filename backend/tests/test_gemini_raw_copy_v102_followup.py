# ruff: noqa: F811
"""試作版 v102：分けて届く投稿の商品を、直前の投稿から決める処理（matched_followup）の試験。

原文は社外秘のため使わない。商品名・型番はすべて作り例。純粋関数の試験は DB に触れない。
DB を読む関数（load_followup_reference）の試験は CI の使い捨て PostgreSQL 専用（test_line_analysis_v102_pg.py と同じ書き方）。
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
from app.services import gemini_raw_copy_v102_followup as fu
from app.services.extraction_judgement_svc import ProductEntry
from app.services.gemini_raw_copy_v102_product_first import ProductFirstMasters
from tests.test_gemini_raw_copy_v102_context_work import _MASTERS, _STATUS
from tests.test_tcg_work_matching_integration import SCHEMA
from tests.test_tcg_work_matching_integration import pg as pg  # noqa: F401  fixture


def _p(pid, work, *kws):
    return ProductEntry(id=pid, product_code=None, mark=None, work_id=work, search_keywords=tuple(kws), exclude_keywords=())


# 62・63 は名前で決まる商品。71・72 は「共通ひよこ」を共有する（71 だけ「ひよこ甲」を持つ）
_PRODUCTS = (_p(62, 1, "ふぁいぶ"), _p(63, 1, "ぴよぴよ"), _p(71, 1, "共通ひよこ", "ひよこ甲"), _p(72, 1, "共通ひよこ"))
_KUBUN = {"62": "箱系", "63": "箱系", "71": "箱系", "72": "箱系"}
_MASTER = ProductFirstMasters(product_entries=_PRODUCTS, product_kubun=_KUBUN, condition_unit={"Sealed box": "Box"}, ignore_phrases=())
REF_ID = "ref-message-1"


def _extract(raw: str, ref_text: str | None, plural_words: tuple[str, ...] = ()):
    lines = raw.split("\n")
    items = [{"lines": [i + 1], "price": "1,500円", "quantity": "3"} for i, ln in enumerate(lines) if ln.strip()]
    parsed, errors = v101.parse_v101_response(json.dumps({"items": items}, ensure_ascii=False), raw, status_entries=_STATUS)
    assert errors == []
    ref = None if ref_text is None else (REF_ID, ref_text)
    rows, _flags = v101.extract_v101_items(
        parsed, raw, order=None, reassign=True, v102_fixes=True,
        product_first=dataclasses.replace(_MASTER, followup_plural_words=plural_words), followup_ref=ref, **_MASTERS
    )
    return rows


REF_POST = "ふぁいぶ ABC-123 3@1,500円\nぴよぴよ DEF-456 3@1,500円\nひよこ甲 ZZZ-777 3@1,500円"


def test_no_reference_changes_nothing():
    raw = "ABC-123 追加 3@1,500円"
    assert _extract(raw, None) == _extract(raw, None)
    row = _extract(raw, None)[0]
    assert row["match_status"] == "unmatched" and "product_followup" not in row


def test_code_in_previous_post_decides_one_product():
    row = _extract("ABC-123 追加 3@1,500円", REF_POST)[0]
    assert (row["match_status"], row["product_id"]) == ("matched_followup", 62)
    assert row["product_followup"] == {"ref_message_id": REF_ID, "ref_line": 1, "tokens": ["abc-123"]}


def test_name_of_four_or_more_chars_decides_one_product():
    raw = "ホゲホゲ 追加 3@1,500円"
    ref = "ホゲホゲ ふぁいぶ 3@1,500円"
    row = _extract(raw, ref)[0]
    assert (row["match_status"], row["product_id"]) == ("matched_followup", 62)
    assert row["product_followup"]["tokens"] == ["ほげほげ"]  # 照合用に normalize した語（カタカナはひらがなになる）


def test_three_char_name_does_not_decide():
    row = _extract("ホゲホ 追加 3@1,500円", "ホゲホ ふぁいぶ 3@1,500円")[0]
    assert row["match_status"] == "unmatched" and row["product_id"] is None


def test_two_products_hit_does_not_decide():
    row = _extract("ABC-123 DEF-456 追加 3@1,500円", REF_POST)[0]
    assert row["match_status"] == "unmatched" and row["product_id"] is None


def test_ambiguous_outside_candidates_does_not_decide():
    row = _extract("共通ひよこ ABC-123 3@1,500円", REF_POST)[0]  # 候補は 71・72。ABC-123 は 62 を指す
    assert row["match_status"] == "ambiguous" and row["product_id"] is None


def test_ambiguous_inside_candidates_decides():
    row = _extract("共通ひよこ ZZZ-777 3@1,500円", REF_POST)[0]  # 候補 71・72、ZZZ-777 は 71 を指す
    assert (row["match_status"], row["product_id"]) == ("matched_followup", 71)


def test_already_matched_row_is_untouched():
    raw = "ふぁいぶ DEF-456 3@1,500円"  # 自分で 62 に決まる。参照は 63 を指すが触らない
    row = _extract(raw, REF_POST)[0]
    assert (row["match_status"], row["product_id"]) == ("matched", 62) and "product_followup" not in row
    assert row == _extract(raw, None)[0]


def test_unit_only_word_is_not_a_clue():
    # 「BOX」は単位マスタの語。参照の行に BOX があっても手がかりにしない（語が0になるので決めない）
    row = _extract("BOX 追加 3@1,500円", "ふぁいぶ BOX 3@1,500円")[0]
    assert row["match_status"] == "unmatched" and row["product_id"] is None


def test_digit_only_word_is_not_a_clue():
    row = _extract("12345 追加 3@1,500円", "ふぁいぶ 12345 3@1,500円")[0]
    assert row["match_status"] == "unmatched"


def test_word_missing_from_previous_post_does_not_decide():
    # ABC-123 は 62 の行に当たるが、ホゲホゲ（直前に無い名前）が混ざるので決めない
    row = _extract("ホゲホゲ ABC-123 3@1,500円", REF_POST)[0]
    assert row["match_status"] == "unmatched" and row["product_id"] is None


def test_plural_word_in_list_does_not_decide():
    raw = "ABC-123 両方 3@1,500円"
    assert _extract(raw, REF_POST, ("両方",))[0]["match_status"] == "unmatched"


def test_empty_plural_word_list_does_not_apply():
    row = _extract("ABC-123 両方 3@1,500円", REF_POST, ())[0]
    assert (row["match_status"], row["product_id"]) == ("matched_followup", 62)


def test_unmatched_with_no_chosen_product_is_unchanged_in_resolve_product_first():
    # resolve_product_first を unmatched にも chosen_product_id が効くよう変えたが、chosen=None の結果は今と同じ
    from app.services.gemini_raw_copy_v102_product_first import resolve_product_first  # noqa: PLC0415
    kwargs = dict(
        item={"lines": [1], "price_line": 1, "price": "1,500円", "quantity": "3"}, roles={1: "price"}, lines=["なにもない 3@1,500円"],
        block="なにもない 3@1,500円", name="", aliases=[], unit_alias_to_info=_MASTERS["unit_alias_to_info"],
        cond_entries=_MASTERS["cond_entries"], cond_canonical_to_uuid={}, masters=_MASTER, find_price_alias=lambda _t: None,
    )
    base = resolve_product_first(**kwargs)
    assert base["match_status"] == "unmatched" and base["product_id"] is None
    assert resolve_product_first(**kwargs, chosen_product_id=None) == base
    assert resolve_product_first(**kwargs, chosen_product_id=62)["match_status"] == "matched"


def test_reference_lines_keep_only_lines_with_one_product():
    refs = fu.build_reference_lines("\nふぁいぶ ABC-123\n共通ひよこ 3\nなにもない行", _MASTER)
    assert [(r.number, r.product_id) for r in refs] == [(2, 62)]  # 空行込みの行番号。ambiguous・unmatched の行は参照にしない


# --- 直前の投稿を読む関数（CI の使い捨て PostgreSQL 専用）---------------------------------------

T0 = datetime(2026, 10, 9, 12, 0, tzinfo=timezone.utc)


def _post(connection, channel_id, raw: str, posted_at, *, active: bool = True) -> str:
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
        cur.execute(f"SELECT id FROM {SCHEMA}.supplier_channels LIMIT 1")
        return cur.fetchone()[0]


def _load(pg_fixture, job_id):
    with Session(pg_fixture[1]) as session:
        return svc.load_followup_reference(session, job_id)


def test_reference_within_one_hour_is_returned_even_if_inactive(pg, channel):
    prev = _post(pg[0], channel, "前の投稿", T0 - timedelta(seconds=3600), active=False)
    job = _job(pg[0], _post(pg[0], channel, "今の投稿", T0))
    assert _load(pg, job) == (prev, "前の投稿")


def test_reference_older_than_one_hour_is_none(pg, channel):
    _post(pg[0], channel, "前の投稿", T0 - timedelta(seconds=3601))
    assert _load(pg, _job(pg[0], _post(pg[0], channel, "今の投稿", T0))) is None


def test_more_than_ten_nonempty_lines_is_none(pg, channel):
    _post(pg[0], channel, "前の投稿", T0 - timedelta(minutes=5))
    eleven = "\n".join(f"行{i}" for i in range(11)) + "\n\n   \n"
    assert _load(pg, _job(pg[0], _post(pg[0], channel, eleven, T0))) is None


def test_ten_nonempty_lines_with_blank_lines_is_allowed(pg, channel):
    prev = _post(pg[0], channel, "前の投稿", T0 - timedelta(minutes=5))
    ten = "\n\n".join(f"行{i}" for i in range(10))
    assert _load(pg, _job(pg[0], _post(pg[0], channel, ten, T0))) == (prev, "前の投稿")


def test_no_previous_post_is_none(pg, channel):
    _post(pg[0], channel, "あとの投稿", T0 + timedelta(minutes=1))
    assert _load(pg, _job(pg[0], _post(pg[0], channel, "今の投稿", T0))) is None


def test_nearest_previous_post_is_chosen(pg, channel):
    _post(pg[0], channel, "さらに前", T0 - timedelta(minutes=30))
    near = _post(pg[0], channel, "すぐ前", T0 - timedelta(minutes=10))
    assert _load(pg, _job(pg[0], _post(pg[0], channel, "今の投稿", T0))) == (near, "すぐ前")
