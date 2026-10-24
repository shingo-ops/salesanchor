"""fetch_snapshot.py の試験。窓口の post を偽物に差し替え、投稿id・値は明らかな作り物だけ(社外秘なし)。"""
import glob
import importlib.util
import os
import re

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("fetch_snapshot", os.path.join(HERE, "fetch_snapshot.py"))
fs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fs)

P1 = "00000000-0000-4000-8000-000000000001"
P2 = "00000000-0000-4000-8000-000000000002"
P3 = "00000000-0000-4000-8000-000000000003"
HEAD = "\t".join(fs.HEADER)


def row(n, pid, extra=None):
    cols = ["v%d_%d" % (n, i) for i in range(len(fs.SNAP_COLS))]
    if extra:
        cols[extra[0]] = extra[1]
    return "\t".join(cols + [pid])


def body(*lines):
    return ("\n".join(lines) + "\n").encode()


class Win:
    """偽の窓口。問い合わせの種類で応答を返し、送られた SQL を記録する。"""

    def __init__(self, posts=(P1, P2, P3), count=3, snap_rows=None, status=200, rc="0",
                 snap_head=None, snap_status=None, snap_rc=None):
        self.posts, self.count = list(posts), count
        self.snap_rows = snap_rows if snap_rows is not None else {
            P1: [row(1, P1), row(2, P1)], P2: [row(3, P2)], P3: []}
        self.status, self.rc = status, rc
        self.snap_head = snap_head or HEAD
        self.snap_status, self.snap_rc = snap_status, snap_rc
        self.sqls = []

    def __call__(self, url, sql, token=None):
        self.sqls.append(sql)
        if "accuracy_gold_rows" in sql:
            return 200, "0", body("post_id", *self.posts)
        if "accuracy_gold_versions" in sql:
            return 200, "0", body("post_count", str(self.count))
        st = self.snap_status if self.snap_status is not None else self.status
        rc = self.snap_rc if self.snap_rc is not None else self.rc
        want = re.findall(r"'([0-9a-f-]{36})'", sql)
        lines = [r for p in want for r in self.snap_rows.get(p, [])]
        return st, rc, body(self.snap_head, *lines)


def run(monkeypatch, tmp_path, win, *extra):
    monkeypatch.setattr(fs, "post", win)
    return fs.main(["--gold-version", "gold_v1", "--out-dir", str(tmp_path / "out"), *extra])


def tsvs(tmp_path):
    return glob.glob(str(tmp_path / "out" / "*.tsv"))


def test_normal_two_batches(monkeypatch, tmp_path, capsys):
    win = Win()
    assert run(monkeypatch, tmp_path, win, "--batch", "2") == 0
    files = sorted(os.path.basename(f) for f in tsvs(tmp_path))
    assert files == [P1 + ".tsv", P2 + ".tsv"]  # P3 は 0 行 → ファイルなし
    text = open(tmp_path / "out" / (P1 + ".tsv"), encoding="utf-8").read().split("\n")
    assert text[0] == "\t".join(fs.SNAP_COLS)
    assert text[1] == "\t".join("v1_%d" % i for i in range(14))
    assert text[2] == "\t".join("v2_%d" % i for i in range(14))
    assert text[3] == ""
    snap_sqls = [s for s in win.sqls if "extraction_jobs" in s]
    assert len(snap_sqls) == 2
    printed = capsys.readouterr().out
    out = printed.strip().split("\n")
    assert re.fullmatch(r"posts=3 with_rows=2 rows=3 fetched_at=\S+Z engine=v102-f_ct", out[-1])
    assert P1 not in printed


@pytest.mark.parametrize("win", [
    Win(status=400, rc="2"),
    Win(status=200, rc="4"),
    Win(snap_head=HEAD.replace("status", "stat")),
    Win(snap_rows={P1: [row(1, P1, (4, "a\\nb"))], P2: [], P3: []}),
    Win(snap_rows={P1: [row(1, P1, (4, "x" * 10240))], P2: [], P3: []}),
    Win(count=4),
    Win(posts=(P1, "not-a-uuid", P3)),
], ids=["http400", "rc4", "head", "backslash", "toolong", "count", "badid"])
def test_stops_write_nothing(monkeypatch, tmp_path, win):
    assert run(monkeypatch, tmp_path, win) == 1
    assert tsvs(tmp_path) == []


def test_stop_row_count_reaches_limit(monkeypatch, tmp_path):
    monkeypatch.setattr(fs, "ROW_LIMIT", 2)
    win = Win(snap_rows={P1: [row(1, P1), row(2, P1)], P2: [], P3: []})
    assert run(monkeypatch, tmp_path, win) == 1
    assert tsvs(tmp_path) == []


def test_stop_when_existing_tsv(monkeypatch, tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    (out / "old.tsv").write_text("x")
    win = Win()
    assert run(monkeypatch, tmp_path, win) == 1
    assert glob.glob(str(out / "*.tsv")) == [str(out / "old.tsv")]
    assert win.sqls == []  # 窓口に送る前に止まる


def test_stop_second_batch_writes_nothing(monkeypatch, tmp_path):
    win = Win(snap_rows={P1: [row(1, P1)], P2: [row(2, P2, (3, "a\\b"))], P3: []})
    assert run(monkeypatch, tmp_path, win, "--batch", "1") == 1
    assert tsvs(tmp_path) == []


def test_parse_messages_have_no_values():
    with pytest.raises(ValueError) as e:
        fs.parse_snapshot(body(HEAD, row(1, P1, (4, "SECRETVALUE\\x"))), 5000)
    assert "SECRETVALUE" not in str(e.value) and P1 not in str(e.value)
    assert "件数=1" in str(e.value)


def test_snapshot_sql_shape():
    sql = fs.snapshot_sql([P1, P2], "v102-f_ct")
    assert sql.startswith("-- limit=5000\n")
    assert "j.source_message_id in ('%s', '%s')" % (P1, P2) in sql
    assert "::text in" not in sql
    assert "ar.engine_version = 'v102-f_ct'" in sql
    assert "order by i.line_start, i.gemini_index, ar.computed_at, ar.id" in sql
    assert "i.id as extraction_item_id" in sql and "ar.exclusion as exclusion" in sql
    assert "j.source_message_id::text as post_id" in sql
    assert "is_current" not in sql
    for bad in ("hash", "_token", "secret"):
        assert bad not in sql


def test_sql_rejects_bad_input():
    with pytest.raises(ValueError):
        fs.snapshot_sql(["x' or 1=1 --"], "v102-f_ct")
    with pytest.raises(ValueError):
        fs.snapshot_sql([P1], "e'; drop")
    with pytest.raises(ValueError):
        fs.posts_sql("Gold;")
    with pytest.raises(ValueError):
        fs.count_sql("a b")


def test_posts_and_count_sql():
    assert "distinct post_id::text as post_id" in fs.posts_sql("gold_v1")
    assert "order by 1" in fs.posts_sql("gold_v1")
    assert "post_count" in fs.count_sql("gold_v1")
