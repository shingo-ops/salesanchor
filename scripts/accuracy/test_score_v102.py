import hashlib
import importlib.util
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "score_v102.py")
spec = importlib.util.spec_from_file_location("score_v102", SCRIPT)
sc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sc)

G_HEAD = ["投稿id", "price_line", "lines", "許容する行", "E2_price", "E3_quantity", "A1_product_id",
          "A2_condition", "A3_unit", "A4_status", "A5_ship", "A4根拠", "迷い", "除外", "裁定根拠", "PO確認"]
S_HEAD = ["extraction_item_id", "line_start", "line_end", "source_lines", "raw_price", "raw_quantity",
          "is_current", "product_id", "condition_canonical", "unit_canonical", "status", "ship_ja",
          "price_normalized", "quantity_normalized", "exclusion"]


def grow(**kw):
    d = dict(投稿id="P1", price_line="L2", lines="L1,L2", 許容する行="", E2_price="1,000",
             E3_quantity="2", A1_product_id="10", A2_condition="Sealed box", A3_unit="Box",
             A4_status="在庫あり", A5_ship="無し", 除外="")
    d.update(kw)
    return d


def srow(**kw):
    d = dict(extraction_item_id="i1", line_start="1", line_end="2", source_lines="[1, 2]",
             raw_price="1,000円", raw_quantity="2BOX", is_current="True", product_id="10",
             condition_canonical="Sealed box", unit_canonical="Box", status="In Stock",
             ship_ja="", price_normalized="1000.00", quantity_normalized="2.00", exclusion="")
    d.update(kw)
    return d


def write(path, head, rows):
    with open(path, "w", encoding="utf-8") as f:
        f.write("\t".join(head) + "\n")
        for r in rows:
            f.write("\t".join(r.get(h, "") for h in head) + "\n")


def run_score(gold, snaps, **kw):
    by = {}
    for r in snaps:
        by.setdefault(r.pop("_post", "P1"), []).append(r)
    return sc.score(gold, by, **kw)


def t(T, item, stage):
    x = T[(item, stage)]
    return (x.ok, x.ng, x.na)


def test_e1_judgement():
    g = [grow(lines="L1,L2", 許容する行="L3")]
    for src, expect in (("[1, 2]", "ok"), ("[1, 2, 3]", "ok"), ("[2]", "ng"), ("[1, 2, 4]", "ng")):
        T, *_ = run_score(g, [srow(source_lines=src, line_start="1", line_end="4")])
        assert t(T, "E1", "Gemini")[0 if expect == "ok" else 1] == 1, src


def test_e1_falls_back_to_range():
    T, *_ = run_score([grow()], [srow(source_lines="")])
    assert t(T, "E1", "Gemini") == (1, 0, 0)


def test_matching_overlap_tie_and_once():
    g = [grow(price_line="L2", lines="L1,L2"), grow(price_line="L3", lines="L3")]
    snaps = [srow(extraction_item_id="b", line_start="1", line_end="3", source_lines="[1, 2, 3]"),
             srow(extraction_item_id="a", line_start="2", line_end="3", source_lines="[2, 3]")]
    pairs, extra = sc.match_post(g, snaps)
    # g0: b overlap 2, a overlap 1 -> b。g1: b は使用済み -> a
    assert pairs[0]["extraction_item_id"] == "b" and pairs[1]["extraction_item_id"] == "a"
    assert extra == []
    # 同点は extraction_item_id が小さい方
    g2 = [grow(price_line="L2", lines="L2")]
    s2 = [srow(extraction_item_id="z", source_lines="[2]"), srow(extraction_item_id="m", source_lines="[2]")]
    p, e = sc.match_post(g2, s2)
    assert p[0]["extraction_item_id"] == "m" and [x["extraction_item_id"] for x in e] == ["z"]


def test_missed_and_extra_counts():
    g = [grow(price_line="L2"), grow(price_line="L9", lines="L9")]
    snaps = [srow(), srow(extraction_item_id="x", line_start="20", line_end="21", source_lines="[20, 21]")]
    T, errors, c1, extra, nocur, nofile, table = run_score(g, snaps)
    assert (c1, extra) == (1, 1)


def test_post_without_snapshot_rows_counts_as_missed():
    g = [grow(), grow(price_line="L5", lines="L5")]
    T, errors, c1, extra, nocur, nofile, table = run_score(g, [])
    assert (c1, nocur) == (2, 1)


def test_is_current_false_rows_are_used():
    # is_current が false の行も採点に使う（絞らない）
    T, errors, c1, extra, *_ = run_score([grow()], [srow(is_current="False")])
    assert (c1, extra) == (0, 0)
    assert t(T, "A1", "通し") == (1, 0, 0)


def test_main_ignores_is_current_column(tmp_path):
    gold = tmp_path / "g.tsv"
    snap = tmp_path / "snap"
    snap.mkdir()
    write(str(gold), G_HEAD, [grow()])
    head = [h for h in S_HEAD if h != "is_current"]  # 列が無くても動く
    write(str(snap / "P1.tsv"), head, [srow()])
    r = subprocess.run([sys.executable, "-I", SCRIPT, "--gold", str(gold), "--snapshot-dir", str(snap),
                        "--out-dir", str(tmp_path / "out")], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_all_excluded_gold_is_matched_not_scored_nor_extra():
    g = [grow(除外="ALL", A1_product_id="(除外)")]
    T, errors, c1, extra, *_ = run_score(g, [srow()])
    assert (c1, extra) == (0, 0)          # 余分に数えない・読み落としでもない
    assert ("E1", "Gemini") not in T  # 採点しない
    assert errors == []


def test_unexpected_system_values_are_wrong_not_na():
    for bad in ("Error", "FLAG_SINGLE", ""):
        T, errors, *_ = run_score([grow()], [srow(condition_canonical=bad, unit_canonical=bad)])
        assert t(T, "A2", "通し") == (0, 1, 0), bad
        assert t(T, "A3", "通し") == (0, 1, 0), bad
        assert t(T, "A2", "システム") == (0, 1, 0), bad


def test_exclusions():
    g = [grow(除外="ALL", A1_product_id="(除外)"),
         grow(price_line="L5", lines="L5", 除外="A1", A1_product_id="(除外)"),
         grow(price_line="L8", lines="L8", 除外="A2A3", A2_condition="(除外)", A3_unit="(除外)"),
         grow(price_line="L11", lines="L11", A2_condition="対象外")]
    snaps = [srow(),
             srow(extraction_item_id="j", line_start="5", line_end="5", source_lines="[5]", product_id="zzz"),
             srow(extraction_item_id="k", line_start="8", line_end="8", source_lines="[8]", condition_canonical="Error"),
             srow(extraction_item_id="m", line_start="11", line_end="11", source_lines="[11]")]
    T, errors, c1, extra, *_ = run_score(g, snaps)
    assert extra == 0 and c1 == 0
    assert t(T, "E1", "Gemini")[0] == 3            # ALL は採点しない
    assert sum(t(T, "A1", "通し")) == 2             # A1 除外の件は A1 を採点しない
    assert sum(t(T, "A2", "通し")) == 2 and t(T, "A2", "通し")[2] == 1  # A2A3 除外は採点せず、対象外は答え無し
    assert sum(t(T, "A3", "通し")) == 2


def test_a4_unknown_stops():
    with pytest.raises(sc.Stop):
        run_score([grow()], [srow(status="Backorder")])
    with pytest.raises(sc.Stop):
        run_score([grow(A4_status="保留")], [srow()])


def test_a4_none_stops_without_extra_arg():
    with pytest.raises(sc.Stop):
        run_score([grow()], [srow(status="none")])


def test_a4_extra_system_none_counts_as_ng():
    T, errors, *_ = run_score([grow()], [srow(status="none")], a4_extra_system=["none"])
    assert t(T, "A4", "通し") == (0, 1, 0)
    assert t(T, "A4", "システム") == (0, 1, 0)
    assert any(e[2] == "A4" and e[5] == "none" for e in errors)
    assert sc.a4_extra_counts({"P1": [srow(status="none"), srow(status="none")]}, ["none"]) == {"none": 2}


def test_unexpected_exclusion_stops():
    with pytest.raises(sc.Stop):
        run_score([grow(除外="A9")], [srow()])


def test_spelling_mismatch_stops():
    with pytest.raises(sc.Stop):
        run_score([grow()], [srow(condition_canonical="Sealed Box")])


def test_missing_column_stops(tmp_path):
    gold = tmp_path / "g.tsv"
    snap = tmp_path / "snap"
    snap.mkdir()
    write(str(gold), [h for h in G_HEAD if h != "A5_ship"], [grow()])
    write(str(snap / "P1.tsv"), S_HEAD, [srow()])
    r = subprocess.run([sys.executable, "-I", SCRIPT, "--gold", str(gold), "--snapshot-dir", str(snap),
                        "--out-dir", str(tmp_path / "out")], capture_output=True, text=True)
    assert r.returncode == 2 and "STOP" in r.stderr


def test_out_dir_inside_repo_stops():
    with pytest.raises(sc.Stop):
        sc.check_out_dir(os.path.join(HERE, "outx"))


def test_deterministic_outputs(tmp_path):
    gold = tmp_path / "g.tsv"
    snap = tmp_path / "snap"
    snap.mkdir()
    write(str(gold), G_HEAD, [grow(), grow(price_line="L5", lines="L5", A2_condition="Case")])
    write(str(snap / "P1.tsv"), S_HEAD, [srow(), srow(extraction_item_id="q", line_start="5", line_end="5", source_lines="[5]")])
    hs = []
    for n in ("o1", "o2"):
        out = tmp_path / n
        r = subprocess.run([sys.executable, "-I", SCRIPT, "--gold", str(gold), "--snapshot-dir", str(snap),
                            "--out-dir", str(out)], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        hs.append({f: hashlib.sha256((out / f).read_bytes()).hexdigest()
                   for f in ("result.tsv", "errors.tsv", "inputs.sha256")})
    assert hs[0] == hs[1]
    assert len((tmp_path / "o1" / "result.tsv").read_text().splitlines()) == 19
