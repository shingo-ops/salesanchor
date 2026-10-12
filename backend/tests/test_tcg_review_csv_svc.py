"""要確認 CSV の出力・内容確認・反映。DB・Redis は呼ばない。設計: docs/handoff/review-csv-roundtrip/design.md §4。"""
from __future__ import annotations

import asyncio
import csv
import io
import os
from unittest.mock import AsyncMock, MagicMock

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

import app.routers.item_corrections as item_router  # noqa: E402
import app.services.tcg_review_csv_svc as svc  # noqa: E402
from app.services.tcg_product_roundtrip_svc import RoundtripError  # noqa: E402
from app.services.tcg_review_sheet_svc import REVIEW_SHEET_HEADERS  # noqa: E402
from app.services.v102_human_decisions_svc import JobOfItem  # noqa: E402

ITEM_A = "11111111-0000-0000-0000-00000000000a"
ITEM_B = "11111111-0000-0000-0000-00000000000b"
SOURCE_A = "22222222-0000-0000-0000-00000000000a"
SOURCE_B = "22222222-0000-0000-0000-00000000000b"
JOB = "33333333-0000-0000-0000-000000000001"


def _item(item_id=ITEM_A, source=SOURCE_A, *, ackable=True, codes=("pid_unresolved",), v102=True, product_uuid="") -> dict:
    return {
        "extraction_item_id": item_id, "source_message_id": source, "provider": "A社", "posted_at": None,
        "raw_text": "原文", "is_v102": v102,
        "gemini": {"name": "x", "quantity": "1", "price": "100", "unit": "", "state": "", "memo": "", "span": "L1-1"},
        "system": {"product_title": "=SUM(A1)", "condition": "", "unit": "", "product_uuid": product_uuid},
        "review_reason_details": [{"code": c, "source": "system", "fix_stage": "a", "ackable": ackable} for c in codes],
        "gap_suspect": None,
    }


def _csv(rows: list[list[str]], header=None) -> bytes:
    out = io.StringIO(newline="")
    writer = csv.writer(out, lineterminator="\r\n")
    writer.writerow(header or svc.CSV_COLUMNS)
    writer.writerows(rows)
    return ("﻿" + out.getvalue()).encode("utf-8")


def _row(item: dict, code="", mark="", revision=None) -> list[str]:
    base = [""] * len(REVIEW_SHEET_HEADERS)
    base[-1] = item["extraction_item_id"]
    return [*base, code, mark, revision if revision is not None else svc.item_revision(item)]


class Env:
    def __init__(self):
        self.items: list[dict] = []
        self.codes: dict[str, list[int]] = {}
        self.invalid: list[str] = []
        self.registered = {"pid_unresolved": ("system", "a"), "condition_unknown": ("system", "a")}
        self.saved_products: list[dict] = []
        self.saved_acks: list[dict] = []
        self.enqueued: list[str] = []
        self.job_by_item = {ITEM_A: JOB, ITEM_B: JOB}
        self.source_by_item = {ITEM_A: SOURCE_A, ITEM_B: SOURCE_B}
        self.fail_item: str | None = None


@pytest.fixture
def env(monkeypatch):
    e = Env()

    async def fetch(db):
        return e.items

    async def ids_by_code(db, codes):
        return {c: e.codes[c] for c in codes if c in e.codes}

    async def invalid(db, values):
        return [v for v in values if v in e.invalid]

    async def registered(db):
        return e.registered

    async def find(db, item_id):
        return JobOfItem(e.job_by_item[item_id], "v102:x", e.source_by_item[item_id])

    async def save_corrections(db, **kw):
        if kw["extraction_item_id"] == e.fail_item:
            raise RuntimeError("boom")
        e.saved_products.append(kw)
        return {"saved": 1}

    async def save_ack(db, **kw):
        e.saved_acks.append(kw)
        return 1

    db = MagicMock()
    db.rollback = AsyncMock()
    e.db = db
    monkeypatch.setattr(svc, "_fetch_items", fetch)
    monkeypatch.setattr(svc, "_product_ids_by_code", ids_by_code)
    monkeypatch.setattr(svc, "invalid_product_values", invalid)
    monkeypatch.setattr(svc, "load_review_reason_codes", registered)
    monkeypatch.setattr(svc, "find_job_of_item", find)
    monkeypatch.setattr(svc, "save_corrections", save_corrections)
    monkeypatch.setattr(svc, "save_review_ack", save_ack)
    monkeypatch.setattr(svc, "enqueue_v102_reanalyze", e.enqueued.append)
    return e


def run(coro):
    return asyncio.run(coro)


def _errors(result) -> list[str]:
    return [e["code"] for e in result["errors"]]


# --- export -------------------------------------------------------------------------------------------


def test_export_has_13_plus_3_columns_and_one_row_per_item(env):
    env.items = [_item(), _item(ITEM_B, SOURCE_B)]
    raw = run(svc.export_csv(env.db))
    assert raw.startswith("﻿".encode("utf-8"))
    rows = list(csv.reader(io.StringIO(raw.decode("utf-8-sig"), newline="")))
    assert rows[0] == [*REVIEW_SHEET_HEADERS, "正しい商品の番号", "このままで良い", "版"]
    assert len(rows) == 3 and all(len(r) == 16 for r in rows)
    assert rows[1][12] == ITEM_A and rows[1][13] == "" and rows[1][14] == ""
    assert rows[1][15] == svc.item_revision(env.items[0])


def test_export_escapes_formula_cells(env):
    env.items = [_item()]
    rows = list(csv.reader(io.StringIO(run(svc.export_csv(env.db)).decode("utf-8-sig"), newline="")))
    assert rows[1][6] == "'=SUM(A1)"


def test_revision_changes_when_reasons_or_product_change():
    base = svc.item_revision(_item())
    assert svc.item_revision(_item(codes=("pid_unresolved", "condition_unknown"))) != base
    assert svc.item_revision(_item(product_uuid="7")) != base
    assert svc.item_revision(_item()) == base


# --- preview: ファイル全体のエラー ------------------------------------------------------------------------


def test_preview_rejects_too_large_file(env):
    with pytest.raises(RoundtripError) as exc:
        run(svc.preview(env.db, b"x" * (2 * 1024 * 1024 + 1)))
    assert exc.value.status == 413


def test_preview_rejects_header_mismatch(env):
    with pytest.raises(RoundtripError) as exc:
        run(svc.preview(env.db, _csv([], header=["a", "b"])))
    assert str(exc.value) == svc.FILE_HEADER


def test_preview_rejects_non_utf8(env):
    with pytest.raises(RoundtripError):
        run(svc.preview(env.db, b"\xff\xfe\x00"))


# --- preview: 行のエラーと成功 ----------------------------------------------------------------------------


def test_preview_skips_rows_without_input(env):
    env.items = [_item()]
    result = run(svc.preview(env.db, _csv([_row(env.items[0])])))
    assert result["applies"] == [] and result["errors"] == []


def test_preview_item_no_longer_needs_review(env):
    env.items = []
    result = run(svc.preview(env.db, _csv([_row(_item(), mark="○")])))
    assert _errors(result) == [svc.ERR_NOT_NEEDS_REVIEW]


def test_preview_stale_revision(env):
    env.items = [_item()]
    result = run(svc.preview(env.db, _csv([_row(env.items[0], mark="○", revision="0" * 64)])))
    assert _errors(result) == [svc.ERR_STALE]


def test_preview_both_inputs(env):
    env.items = [_item()]
    result = run(svc.preview(env.db, _csv([_row(env.items[0], code="PM-00001", mark="○")])))
    assert _errors(result) == [svc.ERR_BOTH]


def test_preview_bad_ack_mark(env):
    env.items = [_item()]
    result = run(svc.preview(env.db, _csv([_row(env.items[0], mark="x")])))
    assert _errors(result) == [svc.ERR_BAD_MARK]


def test_preview_product_code_unknown(env):
    env.items = [_item()]
    result = run(svc.preview(env.db, _csv([_row(env.items[0], code="PM-99999")])))
    assert _errors(result) == [svc.ERR_CODE_NOT_FOUND]


def test_preview_product_code_ambiguous(env):
    env.items = [_item()]
    env.codes = {"PM-00001": [1, 2]}
    result = run(svc.preview(env.db, _csv([_row(env.items[0], code="PM-00001")])))
    assert _errors(result) == [svc.ERR_CODE_AMBIGUOUS]


def test_preview_inactive_product_is_rejected_with_router_message(env):
    env.items = [_item()]
    env.codes = {"PM-00001": [5]}
    env.invalid = ["5"]
    result = run(svc.preview(env.db, _csv([_row(env.items[0], code="PM-00001")])))
    assert _errors(result) == [svc.ERR_REJECTED]
    assert result["errors"][0]["detail"] == "Product is not an active product: 5"


def test_preview_ack_without_ackable_reason(env):
    env.items = [_item(ackable=False, codes=("condition_unknown",))]
    result = run(svc.preview(env.db, _csv([_row(env.items[0], mark="○")])))
    assert _errors(result) == [svc.ERR_NO_ACKABLE]


def test_preview_ack_unregistered_code_is_rejected(env):
    env.items = [_item(codes=("not_a_code",))]
    result = run(svc.preview(env.db, _csv([_row(env.items[0], mark="○")])))
    assert _errors(result) == [svc.ERR_REJECTED]
    assert "Unregistered" in result["errors"][0]["detail"]


def test_preview_non_v102_item_is_rejected(env):
    env.items = [_item(v102=False)]
    result = run(svc.preview(env.db, _csv([_row(env.items[0], mark="○")])))
    assert _errors(result) == [svc.ERR_NOT_V102]


def test_preview_duplicate_item_rows(env):
    env.items = [_item()]
    row = _row(env.items[0], mark="○")
    result = run(svc.preview(env.db, _csv([row, row])))
    assert _errors(result) == [svc.ERR_DUPLICATE] and len(result["applies"]) == 1


def test_preview_lists_applies_and_digest_without_writing(env):
    env.items = [_item(), _item(ITEM_B, SOURCE_B)]
    env.codes = {"PM-00001": [5]}
    result = run(svc.preview(env.db, _csv([_row(env.items[0], code=" PM-00001 "), _row(env.items[1], mark="○")])))
    assert [a["kind"] for a in result["applies"]] == ["product", "ack"]
    assert result["errors"] == [] and len(result["digest"]) == 64
    assert env.saved_products == [] and env.saved_acks == [] and env.enqueued == []


# --- commit -------------------------------------------------------------------------------------------


def _two_item_file(env) -> bytes:
    item_b = _item(ITEM_B, SOURCE_B)
    item_b["review_reason_details"].append({"code": "condition_unknown", "source": "system", "fix_stage": "a", "ackable": False})
    env.items = [_item(), item_b]
    env.codes = {"PM-00001": [5]}
    return _csv([_row(env.items[0], code="PM-00001"), _row(env.items[1], mark="○")])


def test_commit_digest_mismatch_is_409_and_writes_nothing(env):
    raw = _two_item_file(env)
    with pytest.raises(RoundtripError) as exc:
        run(svc.commit(env.db, raw, "0" * 64, "me@example.com"))
    assert exc.value.status == 409
    assert env.saved_products == [] and env.saved_acks == [] and env.enqueued == []


def test_commit_saves_with_existing_functions_and_reanalyzes_once_per_job(env):
    raw = _two_item_file(env)
    digest = run(svc.preview(env.db, raw))["digest"]
    result = run(svc.commit(env.db, raw, digest, "me@example.com"))
    assert result["saved"] == 2 and result["failed"] == []
    assert env.saved_products == [{
        "extraction_item_id": ITEM_A, "source_message_id": SOURCE_A, "corrected_by": "me@example.com",
        "fields": [{"field_name": "product_id", "system_value": "", "human_value": "5"}],
    }]
    assert env.saved_acks == [{
        "extraction_item_id": ITEM_B, "source_message_id": SOURCE_B, "codes": ["pid_unresolved"],
        "corrected_by": "me@example.com",
    }]
    assert env.enqueued == [JOB]


def test_commit_ack_drops_every_ackable_reason_even_when_unackable_remains(env):
    env.items = [_item(codes=("pid_unresolved",))]
    env.items[0]["review_reason_details"].append(
        {"code": "condition_unknown", "source": "system", "fix_stage": "a", "ackable": False}
    )
    raw = _csv([_row(env.items[0], mark="○")])
    digest = run(svc.preview(env.db, raw))["digest"]
    run(svc.commit(env.db, raw, digest, "me@example.com"))
    assert env.saved_acks[0]["codes"] == ["pid_unresolved"]


def test_commit_one_failure_does_not_stop_the_rest(env):
    raw = _two_item_file(env)
    digest = run(svc.preview(env.db, raw))["digest"]
    env.fail_item = ITEM_A
    result = run(svc.commit(env.db, raw, digest, "me@example.com"))
    assert result["saved"] == 1 and [f["extraction_item_id"] for f in result["failed"]] == [ITEM_A]
    assert env.enqueued == [JOB]


# --- router と CSV が同じ検査の関数を使う ----------------------------------------------------------------


def test_router_and_csv_share_the_same_decision_checks():
    from app.services import v102_human_decisions_svc as decisions

    assert item_router.review_ack_rejection is decisions.review_ack_rejection is svc.review_ack_rejection
    assert item_router.product_rejection is decisions.product_rejection is svc.product_rejection
