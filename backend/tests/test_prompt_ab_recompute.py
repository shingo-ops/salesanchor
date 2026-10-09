"""prompt_ab_recompute（保存済みの応答から v102 の後処理だけをやり直す道具）の単体試験。

Gemini は呼ばない・費用の台帳に書かない・DB は読むだけ。すべてモックで確かめる。
"""
from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import app.tools.prompt_ab as pab
import app.tools.prompt_ab_recompute as rec
from app.tasks import tcg_extraction as task

_RAW = "商品A\n3BOX@1,000円"
_CTX = task.ExtractionContext(
    raw_text=_RAW, supplier_context={"extraction_order_pattern": '["price","quantity"]'},
    knowledge_links=[], supplier_id=7,
)
_RESPONSE = json.dumps({"items": [{"lines": [1, 2], "price": "1,000円", "quantity": "3"}]}, ensure_ascii=False)


def _row(run_id: str = "r1", **over) -> dict:
    base = {
        "run_id": run_id, "job_id": f"job-{run_id}", "config": "v102", "repeat": 1,
        "prompt_name": "raw_copy_v101_e", "omitted_supplier_fields": ["extraction_notes"],
        "response_text": _RESPONSE,
    }
    return {**base, **over}


def _write(path, rows: list) -> None:
    path.write_text("\n".join(r if isinstance(r, str) else json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
                    encoding="utf-8")


def _read(path) -> list[dict]:
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines()]


@pytest.fixture
def fakes(monkeypatch, tmp_path):
    """DB・マスタを差し替え、Gemini と費用の台帳は「呼ばれたら失敗」の目印を置く。"""
    m = SimpleNamespace(
        gemini=MagicMock(side_effect=AssertionError("Gemini を呼んではいけない")),
        gemini_v7=MagicMock(side_effect=AssertionError("Gemini を呼んではいけない")),
        ledger=MagicMock(side_effect=AssertionError("台帳に書いてはいけない")),
        ctx=MagicMock(return_value=_CTX),
        masters=MagicMock(return_value={
            "cond_entries": [{"id": "c1", "code": "CN0001", "canonical": "Sealed box", "priority": 1,
                              "app_kubun": "", "search_kw": "シュリンク", "exclude_kw": "",
                              "match_type": "contains", "effect": "set"}],
            "cond_canonical_to_uuid": {"Sealed box": "c1"},
            "status_entries": [{"canonical": "Sold out", "search_pattern": "完売", "exclude_pattern": "",
                                "priority": 1, "match_type": "contains", "effect": "set"}],
            "unit_alias_to_info": {"BOX": ("BOX", "箱系")},
        }),
        session=MagicMock(),
        tmp=tmp_path,
    )
    monkeypatch.setattr(pab, "call_gemini_raw_copy_v8", m.gemini)
    monkeypatch.setattr(pab, "call_gemini_raw_copy", m.gemini_v7)
    monkeypatch.setattr(pab, "record_usage_event_sync", m.ledger)
    monkeypatch.setattr(pab, "load_extraction_context", m.ctx)
    monkeypatch.setattr(pab, "_load_v10_masters", m.masters)
    monkeypatch.setattr(pab, "fetch_job_ids", lambda s, ids: {i: f"job-{i}" for i in ids})
    return m


def _run(fakes, rows: list, name: str = "in.jsonl"):
    src = fakes.tmp / name
    _write(src, rows)
    out_dir = fakes.tmp / "out"
    summary = rec.recompute(fakes.session, from_jsonl=src, out_dir=out_dir)
    return summary, out_dir / f"recompute-{src.stem}.jsonl"


def test_response_text_is_reprocessed_without_calling_gemini(fakes):
    # Act
    summary, out = _run(fakes, [_row()])
    # Assert
    row = _read(out)[0]
    assert (summary.read, summary.written, summary.errors) == (1, 1, 0)
    assert row["v102_items"][0]["name"] == "商品A" and row["v102_items"][0]["price_normalized"] == 1000
    assert "v102_flags" in row
    assert fakes.gemini.call_count == 0 and fakes.gemini_v7.call_count == 0 and fakes.ledger.call_count == 0


def test_same_v102_items_as_prompt_ab_row_fields(fakes):
    # Arrange
    expected = json.loads(json.dumps(  # JSONL を通すと整数キーが文字列になるので、同じ往復を通して比べる
        pab._v102_row_fields(_RESPONSE, _CTX, fakes.masters(fakes.session)), ensure_ascii=False, default=str))
    # Act
    _summary, out = _run(fakes, [_row()])
    # Assert
    row = _read(out)[0]
    assert row["v102_items"] == expected["v102_items"] and row["v102_flags"] == expected["v102_flags"]


def test_source_fields_are_copied_from_the_input_row(fakes):
    _summary, out = _run(fakes, [_row()])
    row = _read(out)[0]
    assert row["run_id"] == "r1" and row["job_id"] == "job-r1" and row["prompt_name"] == "raw_copy_v101_e"
    assert row["omitted_supplier_fields"] == ["extraction_notes"]


def test_masters_are_loaded_once_and_context_per_job(fakes):
    _run(fakes, [_row("r1"), _row("r2"), _row("r1")])
    assert fakes.masters.call_count == 1
    assert fakes.ctx.call_count == 2  # 同じジョブは読み直さない


def test_row_without_response_text_is_recorded_as_error_and_next_row_continues(fakes):
    # Arrange
    bad = _row("r1")
    del bad["response_text"]
    # Act
    summary, out = _run(fakes, [bad, _row("r2")])
    # Assert
    rows = _read(out)
    assert len(rows) == 2 and "response_text" in rows[0]["error"] and "v102_items" not in rows[0]
    assert rows[0]["run_id"] == "r1" and rows[1]["v102_items"][0]["name"] == "商品A"
    assert (summary.read, summary.written, summary.errors) == (2, 1, 1)


def test_broken_json_line_and_empty_response_are_errors_not_fatal(fakes):
    summary, out = _run(fakes, ["{not json", _row("r2", response_text=""), _row("r3")])
    rows = _read(out)
    assert [("error" in r) for r in rows] == [True, True, False]
    assert (summary.read, summary.written, summary.errors) == (3, 1, 2)


def test_run_not_found_is_recorded_as_error(fakes, monkeypatch):
    monkeypatch.setattr(pab, "fetch_job_ids", lambda s, ids: {})
    summary, out = _run(fakes, [_row()])
    assert "run" in _read(out)[0]["error"] and summary.errors == 1


def test_extraction_failure_is_recorded_in_row_like_prompt_ab(fakes, monkeypatch):
    monkeypatch.setattr(pab, "extract_v101_items", MagicMock(side_effect=ValueError("boom")))
    summary, out = _run(fakes, [_row()])
    row = _read(out)[0]
    assert row["v102_items"] == [] and "ValueError" in row["v102_items_error"] and summary.errors == 1


def test_empty_masters_stop_with_error(fakes):
    fakes.masters.side_effect = ValueError("マスタが空です")
    with pytest.raises(ValueError):
        _run(fakes, [_row()])


def test_main_prints_counts_and_returns_nonzero_when_errors(fakes, monkeypatch, capsys):
    src = fakes.tmp / "in.jsonl"
    _write(src, [_row("r1", response_text=""), _row("r2")])
    monkeypatch.setattr(rec, "_get_sync_session", lambda: fakes.session)
    rc = rec.main(["--from-jsonl", str(src), "--out-dir", str(fakes.tmp / "o")])
    assert rc == 1
    assert "read=2 written=1 errors=1" in capsys.readouterr().out


def test_output_file_is_overwritten_not_appended(fakes):
    _run(fakes, [_row()])
    _summary, out = _run(fakes, [_row()])
    assert len(_read(out)) == 1


# ---------------------------------------------------------------------------
# Gemini の要確認（unsure → gemini_review）。設計: docs/handoff/v102-gemini-unsure/design.md
# ---------------------------------------------------------------------------

_RAW2 = "商品A\n3BOX@1,000円\n商品B\n2BOX@2,000円"
_CTX2 = task.ExtractionContext(
    raw_text=_RAW2, supplier_context={"extraction_order_pattern": '["price","quantity"]'},
    knowledge_links=[], supplier_id=7,
)
_ITEMS2 = [{"lines": [1, 2], "price": "1,000円", "quantity": "3"}, {"lines": [4], "price": "2,000円", "quantity": "2"}]


def _resp2(unsure=None) -> str:
    body = {"items": _ITEMS2} if unsure is None else {"items": _ITEMS2, "unsure": unsure}
    return json.dumps(body, ensure_ascii=False)


def _strip_gemini_review(fields: dict) -> dict:
    items = [{k: v for k, v in it.items() if k != "gemini_review"} for it in fields["v102_items"]]
    flags = {k: v for k, v in fields["v102_flags"].items() if k != "gemini_review"}
    return {**fields, "v102_items": items, "v102_flags": flags}


def test_candidate_items_get_gemini_review_and_others_get_empty_list(fakes):
    # Arrange
    masters = fakes.masters(fakes.session)
    # Act
    fields = pab._v102_row_fields(_resp2([{"line": 3, "candidates": [2, 4]}]), _CTX2, masters)
    # Assert
    assert [it["gemini_review"] for it in fields["v102_items"]] == [
        [{"kind": "gemini_unsure", "line": 3}], [{"kind": "gemini_unsure", "line": 3}],
    ]
    assert fields["v102_flags"]["gemini_review"] == [{"kind": "gemini_unsure", "line": 3, "candidates": [2, 4]}]


def test_gemini_review_is_only_given_to_the_item_whose_price_line_is_a_candidate(fakes):
    # Arrange: 候補が 2 と 4 以外（候補の件が1つだけになる形は不正なので、3件目を足して確かめる）
    masters = fakes.masters(fakes.session)
    raw = "商品A\n3BOX@1,000円\n商品B\n2BOX@2,000円\n商品C\n1BOX@3,000円"
    ctx = task.ExtractionContext(raw_text=raw, supplier_context=_CTX2.supplier_context, knowledge_links=[], supplier_id=7)
    items = [*_ITEMS2, {"lines": [5, 6], "price": "3,000円", "quantity": "1"}]
    response = json.dumps({"items": items, "unsure": [{"line": 3, "candidates": [2, 4]}]}, ensure_ascii=False)
    # Act
    fields = pab._v102_row_fields(response, ctx, masters)
    # Assert
    assert [bool(it["gemini_review"]) for it in fields["v102_items"]] == [True, True, False]
    assert fields["v102_items"][2]["gemini_review"] == []


def test_without_unsure_output_is_unchanged_except_empty_gemini_review(fakes):
    # Arrange
    masters = fakes.masters(fakes.session)
    with_empty = pab._v102_row_fields(_resp2(), _CTX2, masters)
    explicit_empty = pab._v102_row_fields(_resp2([]), _CTX2, masters)
    # Assert
    assert with_empty == explicit_empty
    assert with_empty["v102_flags"]["gemini_review"] == []
    assert all(it["gemini_review"] == [] for it in with_empty["v102_items"])
    assert {"possible_missing_item", "quantity_no_number", "possible_footer_line", "post_review"} <= set(with_empty["v102_flags"])


def test_unsure_does_not_change_existing_review_or_flags(fakes):
    # Arrange
    masters = fakes.masters(fakes.session)
    plain = _strip_gemini_review(pab._v102_row_fields(_resp2(), _CTX2, masters))
    with_unsure = _strip_gemini_review(
        pab._v102_row_fields(_resp2([{"line": 3, "candidates": [2, 4]}]), _CTX2, masters))
    # Assert
    assert plain == with_unsure


def test_invalid_unsure_is_kept_in_flags_and_marks_no_item(fakes):
    masters = fakes.masters(fakes.session)
    fields = pab._v102_row_fields(_resp2([{"line": 3, "candidates": [2, 3]}]), _CTX2, masters)
    assert fields["v102_flags"]["gemini_review"][0]["kind"] == "gemini_unsure_invalid"
    assert all(it["gemini_review"] == [] for it in fields["v102_items"])


def test_unreadable_response_gives_empty_gemini_review_next_to_response_unreadable(fakes):
    fields = pab._v102_row_fields("not json", _CTX2, fakes.masters(fakes.session))
    assert fields["v102_flags"]["gemini_review"] == []
    assert fields["v102_flags"]["post_review"][0]["kind"] == "response_unreadable"


def test_extract_exception_keeps_gemini_review_key(fakes, monkeypatch):
    monkeypatch.setattr(pab, "extract_v101_items", MagicMock(side_effect=ValueError("boom")))
    fields = pab._v102_row_fields(_resp2(), _CTX2, fakes.masters(fakes.session))
    assert fields["v102_flags"]["gemini_review"] == []
    assert fields["v102_flags"]["post_review"][0]["kind"] == "extract_exception"


def test_recompute_route_also_adds_gemini_review(fakes):
    # Arrange
    fakes.ctx.return_value = _CTX2
    row = _row(response_text=_resp2([{"line": 3, "candidates": [2, 4]}]))
    # Act
    _summary, out = _run(fakes, [row])
    # Assert
    result = _read(out)[0]
    assert result["v102_flags"]["gemini_review"] == [{"kind": "gemini_unsure", "line": 3, "candidates": [2, 4]}]
    assert [it["gemini_review"] for it in result["v102_items"]] == [[{"kind": "gemini_unsure", "line": 3}]] * 2
