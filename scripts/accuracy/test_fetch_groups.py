"""fetch_groups.py の試験。窓口は差し替える(本番には繋がない)。作り物の値だけ。"""
import importlib.util
import os

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("fetch_groups", os.path.join(HERE, "fetch_groups.py"))
fgr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fgr)

U1 = "11111111-1111-1111-1111-111111111111"
U2 = "22222222-2222-2222-2222-222222222222"
U3 = "33333333-3333-3333-3333-333333333333"

ALL_COLS = [(t, c) for t, cs in fgr.NEEDED.items() for c in cs]


def reply(header, rows):
    return ("\t".join(header) + "\n" + "".join("\t".join(r) + "\n" for r in rows)).encode()


class Window:
    def __init__(self, cols=None, sup=None, cat=None):
        self.cols = ALL_COLS if cols is None else cols
        self.sup = sup or {}
        self.cat = cat or {}
        self.seen = []

    def __call__(self, url, sql, token=None):
        self.seen.append(sql)
        if "information_schema" in sql:
            return 200, "0", reply(["table_name", "column_name"], [list(c) for c in self.cols])
        if "public__source_messages" in sql:
            return 200, "0", reply(["id", "supplier_id"], [[m, s] for m, s in self.sup.items() if m in sql])
        return 200, "0", reply(["id", "name_ja"], [[p, n] for p, n in self.cat.items() if p in sql.split("(")[-1]])


def keys_file(tmp_path, rows):
    p = tmp_path / "keys.tsv"
    p.write_text("\n".join(["\t".join(["key", "msg_id", "product_id"])] + ["\t".join(r) for r in rows]) + "\n")
    return str(p)


def test_output_shape_and_no_product(tmp_path, monkeypatch):
    win = Window(sup={U1: "7", U2: "8"}, cat={"10": "カテゴリA"})
    monkeypatch.setattr(fgr.fg, "post", win)
    k = keys_file(tmp_path, [["k1", U1, "10"], ["k2", U2, ""], ["k3", U3, "99"]])
    out = tmp_path / "g.tsv"
    assert fgr.main(["--keys", k, "--out", str(out)]) == 0
    assert out.read_text(encoding="utf-8") == (
        "key\t仕入元\t中分類\nk1\t7\tカテゴリA\nk2\t8\t商品なし\nk3\t不明\t商品なし\n")
    assert all("insert" not in s.lower() and "update" not in s.lower() for s in win.seen)


def test_blocked_when_column_missing(tmp_path, monkeypatch, capsys):
    cols = [c for c in ALL_COLS if c != ("public__products", "work_id")]
    monkeypatch.setattr(fgr.fg, "post", Window(cols=cols))
    k = keys_file(tmp_path, [["k1", U1, "10"]])
    out = tmp_path / "g.tsv"
    assert fgr.main(["--keys", k, "--out", str(out)]) == 1
    assert "BLOCKED: 窓口に public__products.work_id が無い" in capsys.readouterr().err
    assert not out.exists()


@pytest.mark.parametrize("mid,pid", [("x'; drop table t;--", ""), (U1, "1 or 1=1"), (U1, "abc"), ("123", "")])
def test_bad_ids_exit2(tmp_path, monkeypatch, mid, pid):
    win = Window()
    monkeypatch.setattr(fgr.fg, "post", win)
    k = keys_file(tmp_path, [["k1", mid, pid]])
    out = tmp_path / "g.tsv"
    assert fgr.main(["--keys", k, "--out", str(out)]) == 2
    assert not out.exists() and win.seen == []


def test_batches_split(tmp_path, monkeypatch):
    monkeypatch.setattr(fgr, "BATCH", 2)
    win = Window()
    monkeypatch.setattr(fgr.fg, "post", win)
    k = keys_file(tmp_path, [["k1", U1, "1"], ["k2", U2, "2"], ["k3", U3, "3"]])
    assert fgr.main(["--keys", k, "--out", str(tmp_path / "g.tsv")]) == 0
    assert len([s for s in win.seen if "public__source_messages" in s and "information_schema" not in s]) == 2


def test_http_error_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(fgr.fg, "post", lambda u, s, t=None: (500, "", b"boom"))
    k = keys_file(tmp_path, [["k1", U1, ""]])
    out = tmp_path / "g.tsv"
    assert fgr.main(["--keys", k, "--out", str(out)]) == 1
    assert not out.exists()
