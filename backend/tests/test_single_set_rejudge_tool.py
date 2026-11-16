"""便3 の解析し直しの道具の判定だけを確かめる（DB には触らない）。道具: docs/handoff/single-set-category/data/bin3/rejudge_single_set.py"""
from __future__ import annotations

import importlib.util
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_TOOL = _REPO / "docs" / "handoff" / "single-set-category" / "data" / "bin3" / "rejudge_single_set.py"


def _tool():
    spec = importlib.util.spec_from_file_location("rejudge_single_set", _TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # `if __name__ == "__main__"` のため main は走らない
    return module


def _row(**kw):
    base = {"product_id": 466062, "unit_canonical": "Set", "condition_canonical": "Single", "value_group": "single",
            "bundle_size": None, "condition_basis": "R7:単品既定", "is_current": True}
    return {**base, **kw}


def test_constants():
    t = _tool()
    assert len(t.PIDS) == 13 and len(set(t.PIDS)) == 13
    assert t.SINGLE_SET_CATEGORY == 15
    assert t.STRICT[-1] == "bundle_size" and "value_group" not in t.STRICT
    assert set(t.SOLDOUT_BASES) == {"SOLDOUT_REF", "SOLDOUT_INHERIT"}
    assert t.LOCK_TIMEOUT == "1s"


def test_exclusion_reasons():
    t = _tool()
    ok = {"corr": 0, "prompt_version": "v102:abc", "status": "done"}
    assert t.exclusion_reasons(ok) == []
    assert len(t.exclusion_reasons({**ok, "corr": 2})) == 1
    assert t.exclusion_reasons({**ok, "prompt_version": "v101:abc"}) == ["v102 でない"]
    assert t.exclusion_reasons({**ok, "status": "failed"}) == ["status=failed"]


def test_classify_ok():
    t = _tool()
    assert t.classify_target(_row(unit_canonical="Piece"), _row())[0] == "OK"


def test_classify_ng_cases():
    t = _tool()
    before = _row(condition_canonical="Sealed box", value_group="box")
    assert t.classify_target(before, None) == ("NG", "行が無い")
    assert t.classify_target(before, _row(unit_canonical="Piece"))[0] == "NG"
    assert t.classify_target(before, _row(unit_canonical=None))[0] == "NG"
    assert t.classify_target(before, _row(bundle_size="12"))[0] == "NG"
    assert t.classify_target(before, _row(condition_canonical="Sealed box", value_group="box"))[0] == "NG"
    assert t.classify_target(before, _row(condition_canonical="Error", value_group=None))[0] == "NG"
    assert t.classify_target(before, _row(product_id=1))[0] == "NG"


def test_classify_soldout_is_separate():
    t = _tool()
    for basis in ("SOLDOUT_REF", "SOLDOUT_INHERIT"):
        after = _row(condition_canonical="Sealed box", value_group="box", condition_basis=basis)
        assert t.classify_target(_row(), after)[0] == "SOLDOUT"


def test_classify_soldout_still_checks_unit_and_bundle():
    t = _tool()
    assert t.classify_target(_row(), _row(condition_basis="SOLDOUT_REF", unit_canonical="Piece"))[0] == "NG"
    assert t.classify_target(_row(), _row(condition_basis="SOLDOUT_REF", bundle_size="3"))[0] == "NG"
    assert t.classify_target(_row(), _row(condition_basis="SOLDOUT_REF"))[0] == "OK"


def test_classify_row_that_moved_in_or_out():
    t = _tool()
    assert t.classify_target(_row(product_id=1), _row())[0] == "OK"
    assert t.classify_target(_row(), _row(product_id=1))[0] == "NG"
    assert t.classify_target(_row(), _row(product_id=466031))[0] == "NG"


def test_classify_key_shows_shape():
    t = _tool()
    label, key = t.classify_target(_row(), _row(bundle_size="5", is_current=False))
    assert label == "NG" and key == "466062/Set/Single/single/bundle=5/cur=False"
