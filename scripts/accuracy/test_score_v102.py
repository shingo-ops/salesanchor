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


# ---- 行ごとの判定を書き出す --verdicts-out（T1〜T5） ----

# T1: 変更前の本線の道具で、test_deterministic_outputs と同じ入力を流したときの sha256
BASELINE_SHA = {
    "result.tsv": "90d00af78d66b479c92b325f45f138868da208943c495e6e1f18e0a9b2f6adad",
    "errors.tsv": "3c83de0c0a82e7ae3e024ab90494de0842aca1fd2d19fb48b69e199ce2c5659b",
    "inputs.sha256": "ae43232c0fa7874b33975c303791a4a4c2fb2015628301826fd0319356b29adf",
}

ITEMS = ["C1", "E1", "E2", "E3", "A1", "A2", "A3", "A4", "A5"]


def _run_main(gold, snap, out, extra=()):
    return subprocess.run([sys.executable, "-I", SCRIPT, "--gold", str(gold), "--snapshot-dir", str(snap),
                           "--out-dir", str(out), *extra], capture_output=True, text=True)


def _make_verdict_inputs(tmp_path):
    gold = tmp_path / "g.tsv"
    snap = tmp_path / "snap"
    snap.mkdir()
    write(str(gold), G_HEAD, [
        grow(),                                                                      # key1 全部合う
        grow(price_line="L5", lines="L5", 除外="ALL", A1_product_id="(除外)"),        # key2 除外 ALL
        grow(price_line="L8", lines="L8", 除外="A1", A1_product_id="(除外)"),         # key3 A1 の除外
        grow(price_line="L11", lines="L11"),                                          # key4 E1 が違う
        grow(投稿id="P2"),                                                            # key5 読み落とし
    ])
    write(str(snap / "P1.tsv"), S_HEAD, [
        srow(),
        srow(extraction_item_id="b", line_start="5", line_end="5", source_lines="[5]"),
        srow(extraction_item_id="c", line_start="8", line_end="8", source_lines="[8]", product_id="zzz"),
        srow(extraction_item_id="d", line_start="11", line_end="12", source_lines="[11, 12]"),
    ])
    write(str(snap / "P2.tsv"), S_HEAD, [])
    return gold, snap


def _expected_verdicts():
    rows = []
    for item in ITEMS:
        rows.append((1, item, "OK"))
    rows += [(3, i, "SKIP" if i == "A1" else "OK") for i in ITEMS]
    rows += [(4, i, "NG" if i == "E1" else "SKIP" if i in ("E2", "E3") else "OK") for i in ITEMS]
    rows.append((5, "C1", "NG"))
    return "key\t項目\t判定\n" + "".join("%d\t%s\t%s\n" % r for r in rows)


def test_t1_without_flag_output_unchanged(tmp_path):
    gold = tmp_path / "g.tsv"
    snap = tmp_path / "snap"
    snap.mkdir()
    write(str(gold), G_HEAD, [grow(), grow(price_line="L5", lines="L5", A2_condition="Case")])
    write(str(snap / "P1.tsv"), S_HEAD, [srow(), srow(extraction_item_id="q", line_start="5", line_end="5", source_lines="[5]")])
    r = _run_main(gold, snap, tmp_path / "out")
    assert r.returncode == 0, r.stderr
    got = {f: hashlib.sha256((tmp_path / "out" / f).read_bytes()).hexdigest() for f in BASELINE_SHA}
    assert got == BASELINE_SHA


def test_t2_verdicts_rows(tmp_path):
    gold, snap = _make_verdict_inputs(tmp_path)
    v = tmp_path / "v" / "V.tsv"
    r = _run_main(gold, snap, tmp_path / "out", ["--verdicts-out", str(v)])
    assert r.returncode == 0, r.stderr
    assert v.read_bytes().decode("utf-8") == _expected_verdicts()


def test_t3_verdicts_match_result(tmp_path):
    gold, snap = _make_verdict_inputs(tmp_path)
    v = tmp_path / "V.tsv"
    r = _run_main(gold, snap, tmp_path / "out", ["--verdicts-out", str(v)])
    assert r.returncode == 0, r.stderr
    cnt = {}
    for line in v.read_text(encoding="utf-8").splitlines()[1:]:
        _, item, verdict = line.split("\t")
        cnt[(item, verdict)] = cnt.get((item, verdict), 0) + 1
    res = {}
    for line in (tmp_path / "out" / "result.tsv").read_text(encoding="utf-8").splitlines()[1:]:
        c = line.split("\t")
        res[(c[0], c[1])] = c
    for item, stage in (("E1", "Gemini"), ("E2", "システム"), ("E3", "システム"), ("A1", "通し"),
                        ("A2", "通し"), ("A3", "通し"), ("A4", "通し"), ("A5", "通し")):
        c = res[(item, stage)]
        assert (cnt.get((item, "OK"), 0), cnt.get((item, "NG"), 0), cnt.get((item, "NOWORD"), 0)) == \
            (int(c[2]), int(c[3]), int(c[4])), item
    assert cnt.get(("C1", "NG"), 0) == int(res[("C1読み落とし", "件数")][3])


def test_t3_mismatch_stops_without_verdicts(tmp_path, monkeypatch):
    gold, snap = _make_verdict_inputs(tmp_path)
    monkeypatch.setattr(sc, "check_verdicts", lambda T, c1, vs: ["E1"])
    v = tmp_path / "V.tsv"
    rc = sc.main(["--gold", str(gold), "--snapshot-dir", str(snap), "--out-dir", str(tmp_path / "out"),
                  "--verdicts-out", str(v)])
    assert rc == 2
    assert not v.exists()
    assert (tmp_path / "out" / "result.tsv").exists()


def test_t4_verdicts_inside_repo_stops(tmp_path):
    gold, snap = _make_verdict_inputs(tmp_path)
    v = os.path.join(HERE, "V_should_not_exist.tsv")
    r = _run_main(gold, snap, tmp_path / "out", ["--verdicts-out", v])
    assert r.returncode == 2 and "STOP" in r.stderr
    assert not os.path.exists(v)
    assert not (tmp_path / "out").exists()


def test_t5_verdicts_deterministic(tmp_path):
    gold, snap = _make_verdict_inputs(tmp_path)
    hs = []
    for n in ("a", "b"):
        v = tmp_path / n / "V.tsv"
        r = _run_main(gold, snap, tmp_path / ("o" + n), ["--verdicts-out", str(v)])
        assert r.returncode == 0, r.stderr
        hs.append(hashlib.sha256(v.read_bytes()).hexdigest())
    assert hs[0] == hs[1]
