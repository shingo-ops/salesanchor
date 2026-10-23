"""gold_to_sql.py の試験。作り物の値だけ(社外秘なし)。"""
import hashlib
import importlib.util
import os
import subprocess
import sys
import uuid

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "gold_to_sql.py")
spec = importlib.util.spec_from_file_location("gold_to_sql", SCRIPT)
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

OUTS = ("01_precheck.sql", "02_apply.sql", "03_verify.sql")


def make_row(pid=None, **kw):
    d = dict.fromkeys(g.HEADER, "")
    d["投稿id"] = pid or str(uuid.uuid4())
    d["A1_product_id"] = "12"
    d.update(kw)
    return [d[h] for h in g.HEADER]


def write_gold(path, rows, head=None):
    lines = ["\t".join(head or g.HEADER)] + ["\t".join(r) for r in rows]
    path.write_bytes(("\n".join(lines) + "\n").encode("utf-8"))


def run(tmp_path, gold, version="gold_t1", out=None, cwd=None):
    out = out or (tmp_path / "out")
    r = subprocess.run([sys.executable, "-I", SCRIPT, "--gold", str(gold), "--version", version,
                        "--note", "試験", "--out-dir", str(out)],
                       capture_output=True, text=True, cwd=cwd or str(tmp_path))
    return r, out


def three_rows():
    p1, p2 = str(uuid.uuid4()), str(uuid.uuid4())
    return [make_row(p1, lines="1,2"), make_row(p1, price_line="2", A1_product_id="x"),
            make_row(p2, 裁定根拠="it's ok")]


def test_ok_outputs_three_files_only(tmp_path):
    gold = tmp_path / "g.tsv"
    write_gold(gold, three_rows())
    r, out = run(tmp_path, gold)
    assert r.returncode == 0, r.stderr
    assert sorted(os.listdir(out)) == sorted(OUTS)
    sha = hashlib.sha256(gold.read_bytes()).hexdigest()
    assert "sha256=" + sha in r.stdout and "rows=3" in r.stdout and "posts=2" in r.stdout
    apply_sql = (out / "02_apply.sql").read_text(encoding="utf-8")
    assert "\\set ON_ERROR_STOP on" in apply_sql and "\\if :{?end}" in apply_sql and "\n:end;" in apply_sql
    assert "SET LOCAL app.is_operator = 'true'" in apply_sql
    assert "'it''s ok'" in apply_sql
    assert "THEN 1 ELSE 1 / 0 END FROM public.accuracy_gold_rows WHERE gold_version = 'gold_t1'" in apply_sql
    pre = (out / "01_precheck.sql").read_text(encoding="utf-8")
    assert "MISSING_POSTS" in pre and "MISSING_PRODUCTS" in pre
    assert "gold_t1" in (out / "03_verify.sql").read_text(encoding="utf-8")


def test_chunking(tmp_path):
    rows = [make_row() for _ in range(501)]
    gold = tmp_path / "g.tsv"
    write_gold(gold, rows)
    r, out = run(tmp_path, gold)
    assert r.returncode == 0, r.stderr
    assert (out / "02_apply.sql").read_text(encoding="utf-8").count("INSERT INTO public.accuracy_gold_rows") == 2


def stop(tmp_path, gold, **kw):
    r, out = run(tmp_path, gold, **kw)
    assert r.returncode == 2, (r.returncode, r.stderr)
    assert r.stderr.startswith("STOP:") and len(r.stderr.strip().splitlines()) == 1
    assert not out.exists() or os.listdir(out) == []
    return r


def test_bad_header(tmp_path):
    gold = tmp_path / "g.tsv"
    write_gold(gold, three_rows(), head=list(reversed(g.HEADER)))
    stop(tmp_path, gold)


def test_bad_column_count(tmp_path):
    gold = tmp_path / "g.tsv"
    rows = three_rows()
    rows[1] = rows[1][:-1]
    write_gold(gold, rows)
    stop(tmp_path, gold)


@pytest.mark.parametrize("bad", ["a\\b", 'a"b', "a\rb"])
def test_bad_chars(tmp_path, bad):
    gold = tmp_path / "g.tsv"
    rows = three_rows()
    rows[2][2] = bad
    write_gold(gold, rows)
    r = stop(tmp_path, gold)
    assert bad not in r.stderr


def test_extra_tab_is_column_mismatch(tmp_path):
    gold = tmp_path / "g.tsv"
    rows = three_rows()
    rows[0][2] = "a\tb"
    write_gold(gold, rows)
    stop(tmp_path, gold)


@pytest.mark.parametrize("bad", ["not-a-uuid", str(uuid.uuid4()).upper()])
def test_bad_uuid(tmp_path, bad):
    gold = tmp_path / "g.tsv"
    rows = three_rows()
    rows[0][0] = bad
    write_gold(gold, rows)
    stop(tmp_path, gold)


@pytest.mark.parametrize("ver", ["Gold_V1", "gold-v1", "gold v1", ""])
def test_bad_version(tmp_path, ver):
    gold = tmp_path / "g.tsv"
    write_gold(gold, three_rows())
    stop(tmp_path, gold, version=ver)


def test_out_dir_in_repo(tmp_path):
    gold = tmp_path / "g.tsv"
    write_gold(gold, three_rows())
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    r, out = run(tmp_path, gold, out=repo / "sub", cwd=str(repo))
    assert r.returncode == 2 and r.stderr.startswith("STOP:")
    assert not (repo / "sub").exists()


def test_out_dir_in_script_repo(tmp_path):
    """gold_to_sql.py のあるリポジトリの中を指しても止まる(実行場所が別でも)。"""
    gold = tmp_path / "g.tsv"
    write_gold(gold, three_rows())
    top = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=HERE, capture_output=True, text=True)
    if top.returncode != 0:
        pytest.skip("git の外で実行されている")
    target = os.path.join(top.stdout.strip(), "tmp_gold_test_should_not_exist")
    r, _ = run(tmp_path, gold, out=target, cwd=str(tmp_path))
    assert r.returncode == 2
    assert not os.path.exists(target)
