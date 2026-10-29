"""by_group.py の試験。作り物のデータだけ(社外秘なし)。"""
import hashlib
import importlib.util
import os

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("by_group", os.path.join(HERE, "by_group.py"))
bg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bg)


def w(path, header, rows):
    path.write_text("\n".join(["\t".join(header)] + ["\t".join(r) for r in rows]) + "\n", encoding="utf-8")
    return str(path)


def verdicts(tmp_path, rows):
    return w(tmp_path / "v.tsv", ["key", "項目", "判定"], rows)


def groups(tmp_path, rows):
    return w(tmp_path / "g.tsv", ["key", "仕入元", "中分類"], rows)


def read(out, name):
    lines = (out / name).read_text(encoding="utf-8").split("\n")
    assert lines[-1] == ""
    return [l.split("\t") for l in lines[:-1]]


def small(tmp_path):
    # 仕入元 1: k1..k3 / 仕入元 2: k4..k5。項目 a, b
    v = []
    for k, a, b in [("k1", "OK", "OK"), ("k2", "NG", "OK"), ("k3", "OK", "NOWORD"),
                    ("k4", "OK", "NG"), ("k5", "NG", "NG")]:
        v += [[k, "a", a], [k, "b", b]]
    g = [["k1", "1", "X"], ["k2", "1", "Y"], ["k3", "1", "X"], ["k4", "2", "Y"], ["k5", "2", "Y"]]
    return verdicts(tmp_path, v), groups(tmp_path, g)


def test_t1_hand_computed(tmp_path):
    v, g = small(tmp_path)
    out = tmp_path / "out"
    assert bg.main(["--verdicts", v, "--groups", g, "--out-dir", str(out)]) == 0
    ov = read(out, "overall.tsv")
    assert ov[0] == bg.OUT_HEADER
    assert ov[1] == ["全体", "a", "3", "2", "0", "60.0", "23.1", "88.2", "参考"]
    assert ov[2][:6] == ["全体", "b", "2", "2", "1", "50.0"]
    sup = {(r[0], r[1]): r for r in read(out, "by_supplier.tsv")[1:]}
    assert sup[("1", "a")][2:6] == ["2", "1", "0", "66.7"]
    assert sup[("2", "b")][2:6] == ["0", "2", "0", "0.0"]
    cat = {(r[0], r[1]): r for r in read(out, "by_category.tsv")[1:]}
    assert cat[("Y", "a")][2:5] == ["1", "2", "0"]
    assert cat[("X", "b")][2:6] == ["1", "0", "1", "100.0"]


def test_t1_wilson_values():
    lo, hi = bg.wilson(9, 10)
    assert ("%.1f" % (lo * 100), "%.1f" % (hi * 100)) == ("59.6", "98.2")
    lo, hi = bg.wilson(18, 20)
    assert ("%.1f" % (lo * 100), "%.1f" % (hi * 100)) == ("69.9", "97.2")


def test_reference_mark_threshold(tmp_path):
    v = [["k%d" % i, "a", "OK"] for i in range(20)] + [["j%d" % i, "a", "OK"] for i in range(19)]
    g = [["k%d" % i, "big", "c"] for i in range(20)] + [["j%d" % i, "small", "c"] for i in range(19)]
    out = tmp_path / "out"
    assert bg.main(["--verdicts", verdicts(tmp_path, v), "--groups", groups(tmp_path, g), "--out-dir", str(out)]) == 0
    rows = {r[0]: r for r in read(out, "by_supplier.tsv")[1:] if r[1] == "a"}
    assert rows["big"][8] == "" and rows["small"][8] == "参考"
    assert rows["big"][5] == "100.0"


def test_zero_denominator(tmp_path):
    v = [["k1", "a", "NOWORD"]]
    g = [["k1", "1", "X"]]
    out = tmp_path / "out"
    assert bg.main(["--verdicts", verdicts(tmp_path, v), "--groups", groups(tmp_path, g), "--out-dir", str(out)]) == 0
    assert read(out, "overall.tsv")[1] == ["全体", "a", "0", "0", "1", "-", "-", "-", "参考"]


def test_t2_sum_mismatch_exit3_writes_nothing(tmp_path, monkeypatch):
    v, g = small(tmp_path)
    orig = bg.count_by

    def bad(data, items, label_of):
        r = orig(data, items, label_of)
        if label_of("k1") not in ("全体",):
            next(iter(r.values()))["a"][0] += 1  # 区分の側だけ数をずらす
        return r

    monkeypatch.setattr(bg, "count_by", bad)
    out = tmp_path / "out"
    assert bg.main(["--verdicts", v, "--groups", g, "--out-dir", str(out)]) == 3
    assert not out.exists()


def test_t3_deterministic(tmp_path):
    v, g = small(tmp_path)
    hs = []
    for n in ("o1", "o2"):
        out = tmp_path / n
        assert bg.main(["--verdicts", v, "--groups", g, "--out-dir", str(out)]) == 0
        hs.append([hashlib.sha256((out / f).read_bytes()).hexdigest()
                   for f in ("overall.tsv", "by_supplier.tsv", "by_category.tsv")])
    assert hs[0] == hs[1]


def test_t4_bad_inputs_exit2(tmp_path):
    out = tmp_path / "out"
    g = groups(tmp_path, [["k1", "1", "X"]])
    bad_v = verdicts(tmp_path, [["k1", "a", "MAYBE"]])
    assert bg.main(["--verdicts", bad_v, "--groups", g, "--out-dir", str(out)]) == 2
    dup_v = verdicts(tmp_path, [["k1", "a", "OK"], ["k1", "a", "NG"]])
    assert bg.main(["--verdicts", dup_v, "--groups", g, "--out-dir", str(out)]) == 2
    ok_v = verdicts(tmp_path, [["k1", "a", "OK"]])
    dup_g = groups(tmp_path, [["k1", "1", "X"], ["k1", "2", "Y"]])
    assert bg.main(["--verdicts", ok_v, "--groups", dup_g, "--out-dir", str(out)]) == 2
    assert not out.exists()
    inside = os.path.join(os.path.dirname(HERE), "_by_group_test_out")
    try:
        assert bg.main(["--verdicts", ok_v, "--groups", g, "--out-dir", inside]) == 2
        assert not os.path.exists(inside)
    finally:
        if os.path.isdir(inside):
            os.rmdir(inside)


def test_t5_unknown_group_last(tmp_path, capsys):
    v = verdicts(tmp_path, [["k1", "a", "OK"], ["k2", "a", "OK"], ["k3", "a", "NG"]])
    g = groups(tmp_path, [["k1", "9", "Z"], ["k2", "", ""]])  # k3 は対応表に無い
    out = tmp_path / "out"
    assert bg.main(["--verdicts", v, "--groups", g, "--out-dir", str(out)]) == 0
    assert "1 件" in capsys.readouterr().err
    for name in ("by_supplier.tsv", "by_category.tsv"):
        labels = []
        for r in read(out, name)[1:]:
            if r[0] not in labels:
                labels.append(r[0])
        assert labels[-1] == "不明"
    sup = {(r[0], r[1]): r for r in read(out, "by_supplier.tsv")[1:]}
    assert sup[("不明", "a")][2:5] == ["1", "1", "0"]


def test_t6_all_items_row(tmp_path):
    v = verdicts(tmp_path, [["k1", "a", "OK"], ["k1", "b", "OK"],
                            ["k2", "a", "OK"], ["k2", "b", "NG"],
                            ["k3", "a", "NOWORD"], ["k3", "b", "NOWORD"]])
    g = groups(tmp_path, [["k1", "1", "X"], ["k2", "1", "X"], ["k3", "1", "X"]])
    out = tmp_path / "out"
    assert bg.main(["--verdicts", v, "--groups", g, "--out-dir", str(out)]) == 0
    rows = read(out, "overall.tsv")
    assert rows[-1][:5] == ["全体", "全項目", "2", "1", "0"]  # k3 は NG が無いので正しい側
