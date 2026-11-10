"""replay_words.add_words と diff_any の試験（DB 不要・架空のデータ）。"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import diff_any
import pytest
import replay_words
from app.services.gemini_raw_copy_v102_product_first import ProductFirstMasters


def _entries() -> list[dict]:
    return [
        {"code": "X1", "search_kw": "あい,うえ", "match_type": "KEYWORD"},
        {"code": "X2", "search_kw": "かき", "match_type": "KEYWORD"},
        {"code": "X3", "search_kw": None, "match_type": "KEYWORD"},
    ]


def _masters() -> dict:
    pf = ProductFirstMasters(product_entries=(), product_kubun={}, condition_unit={}, ignore_phrases=())
    return {"cond_entries": _entries(), "product_first": pf}


def test_add_words_changes_only_target_code():
    out = replay_words.add_words(_masters(), {"X1": ["さし"]})
    by = {e["code"]: e for e in out["cond_entries"]}
    assert by["X1"]["search_kw"] == "あい,うえ,さし"
    assert by["X2"]["search_kw"] == "かき"
    assert by["X3"]["search_kw"] is None


def test_add_words_does_not_mutate_original():
    masters = _masters()
    replay_words.add_words(masters, {"X1": ["さし"], "X3": ["すせ"]})
    assert masters["cond_entries"] == _entries()
    assert masters["product_first"].g2_index is None


def test_add_words_no_duplicate():
    out = replay_words.add_words(_masters(), {"X1": ["あい", "さし", "さし"]})
    assert out["cond_entries"][0]["search_kw"] == "あい,うえ,さし"


def test_add_words_fills_empty_search_kw():
    out = replay_words.add_words(_masters(), {"X3": ["すせ"]})
    assert out["cond_entries"][2]["search_kw"] == "すせ"


def test_cond_terms_include_new_word():
    before = replay_words.add_words(_masters(), {})
    after = replay_words.add_words(_masters(), {"X1": ["さし"]})
    assert "さし" not in before["product_first"].g2_index.cond_terms
    assert "さし" in after["product_first"].g2_index.cond_terms


def test_unknown_code_raises():
    with pytest.raises(ValueError):
        replay_words.add_words(_masters(), {"NOPE": ["さし"]})


def test_parse_add():
    assert replay_words.parse_add(["X1=あ,い", "X1=い,う"]) == {"X1": ["あ", "い", "う"]}
    with pytest.raises(ValueError):
        replay_words.parse_add(["X1"])


def _rec(post: str, idx: int, **kw) -> dict:
    base = {c: None for c in diff_any.COLUMNS}
    base.update({"post_id": post, "index": idx, "condition": "新品", "condition_basis": "新品"})
    base.update(kw)
    return base


def _write(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")


def _tsv(path: Path) -> list[list[str]]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.reader(fh, delimiter="\t"))


def test_diff_any_outputs(tmp_path: Path):
    before, after = tmp_path / "b.jsonl", tmp_path / "a.jsonl"
    _write(before, [_rec("p1", 0), _rec("p1", 1), _rec("p2", 0), _rec("p3", 0)])
    _write(after, [
        _rec("p1", 0),
        _rec("p1", 1, condition="未開封", condition_basis="未開封さし", price=100),
        _rec("p2", 0),
        _rec("p2", 1),  # p2 は件が 1 つ増えた
        # p3 は後で 0 件
    ])
    out = tmp_path / "out"
    result = diff_any.diff_any(before, after, out, ["さし"])
    assert result["any_changed"] == 1
    assert result["after_basis_has_words"] == 1

    summary = {r[0]: r[1] for r in _tsv(out / "summary.tsv")[1:]}
    assert summary["condition"] == "1"
    assert summary["price"] == "1"
    assert summary["product"] == "0"
    assert summary["any_changed"] == "1"
    assert summary["only_before"] == "1"
    assert summary["only_after"] == "1"
    assert summary["after_basis_has_words"] == "1"

    changed = _tsv(out / "changed_any.tsv")
    assert len(changed) == 2  # 見出し + 1 件
    assert changed[1][:2] == ["p1", "1"]
    assert set(changed[1][2].split(",")) == {"condition", "condition_basis", "price"}
    detail = json.loads(changed[1][3])
    assert detail["price"] == {"before": None, "after": 100}

    counts = _tsv(out / "post_counts.tsv")[1:]
    assert counts == [["p2", "1", "2"], ["p3", "1", "0"]]


def test_diff_any_identical_is_zero(tmp_path: Path):
    f = tmp_path / "x.jsonl"
    _write(f, [_rec("p1", 0), _rec("p1", 1)])
    out = tmp_path / "out"
    result = diff_any.diff_any(f, f, out, [])
    assert result["any_changed"] == 0
    assert result["posts_count_differs"] == 0
    assert len(_tsv(out / "changed_any.tsv")) == 1
