"""fetch_gold.py の試験。偽の窓口(http.server)と作り物の値だけ(社外秘なし)。"""
import hashlib
import importlib.util
import os
import re
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "fetch_gold.py")
spec = importlib.util.spec_from_file_location("fetch_gold", SCRIPT)
fg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fg)

# 出典: backend/app/ops/readonly_query.py:55 の _WRITE_RE と同じ正規表現(backend を import できない置き方のため写し)
WRITE_RE = re.compile(r"\b(insert|update|delete|truncate|drop|alter|create|grant)\b", re.I)

BODY = ("\t".join(fg._g.HEADER) + "\n" + "\n".join("\t".join(["id%d" % i] + ["v"] * 15) for i in range(3)) + "\n").encode()


class Fake:
    def __init__(self, ver_reply, rows_reply, ver_rc="0", rows_rc="0", ver_status=200, rows_status=200):
        self.ver_reply, self.rows_reply = ver_reply, rows_reply
        self.ver_rc, self.rows_rc = ver_rc, rows_rc
        self.ver_status, self.rows_status = ver_status, rows_status
        self.seen = []
        outer = self

        class H(BaseHTTPRequestHandler):
            def do_POST(self):
                n = int(self.headers.get("Content-Length", 0))
                sql = self.rfile.read(n).decode("utf-8")
                outer.seen.append((sql, self.headers.get("X-Read-Window-Token"), self.headers.get("Content-Type")))
                if "accuracy_gold_versions" in sql:
                    st, rc, body = outer.ver_status, outer.ver_rc, outer.ver_reply
                else:
                    st, rc, body = outer.rows_status, outer.rows_rc, outer.rows_reply
                self.send_response(st)
                self.send_header("X-Read-Window-Rc", rc)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *a):
                pass

        self.srv = HTTPServer(("127.0.0.1", 0), H)
        self.url = "http://127.0.0.1:%d/q" % self.srv.server_address[1]
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def close(self):
        self.srv.shutdown()
        self.srv.server_close()


def ver_reply(sha, rows):
    return ("file_sha256\trow_count\tpost_count\n%s\t%d\t2\n" % (sha, rows)).encode()


def run(url, out, env_extra=None, version="gold_t1"):
    env = {k: v for k, v in os.environ.items() if k != "READ_WINDOW_TOKEN"}
    env.update(env_extra or {})
    return subprocess.run([sys.executable, "-I", SCRIPT, "--version", version, "--out", str(out), "--url", url],
                          capture_output=True, text=True, env=env)


@pytest.fixture
def fake():
    made = []

    def mk(*a, **k):
        f = Fake(*a, **k)
        made.append(f)
        return f
    yield mk
    for f in made:
        f.close()


def test_match_writes_same_bytes(fake, tmp_path):
    sha = hashlib.sha256(BODY).hexdigest()
    f = fake(ver_reply(sha, 3), BODY)
    out = tmp_path / "o.tsv"
    r = run(f.url, out)
    assert r.returncode == 0, r.stderr
    assert out.read_bytes() == BODY
    assert "sha256=%s rows=3" % sha[:12] in r.stdout
    assert all(t[1] is None for t in f.seen)
    assert all(t[2] == "text/plain; charset=utf-8" for t in f.seen)


def test_token_header_sent_and_not_printed(fake, tmp_path):
    sha = hashlib.sha256(BODY).hexdigest()
    f = fake(ver_reply(sha, 3), BODY)
    r = run(f.url, tmp_path / "o.tsv", {"READ_WINDOW_TOKEN": "dummy-token-value"})
    assert r.returncode == 0
    assert all(t[1] == "dummy-token-value" for t in f.seen)
    assert "dummy-token-value" not in r.stdout + r.stderr


def test_sha_mismatch_no_write(fake, tmp_path):
    f = fake(ver_reply("0" * 64, 3), BODY)
    out = tmp_path / "o.tsv"
    r = run(f.url, out)
    assert r.returncode == 1 and not out.exists()


def test_sha_mismatch_keeps_existing_file(fake, tmp_path):
    f = fake(ver_reply("0" * 64, 3), BODY)
    out = tmp_path / "o.tsv"
    out.write_bytes(b"old")
    r = run(f.url, out)
    assert r.returncode == 1 and out.read_bytes() == b"old"


def test_row_count_mismatch_no_write(fake, tmp_path):
    sha = hashlib.sha256(BODY).hexdigest()
    f = fake(ver_reply(sha, 4), BODY)
    out = tmp_path / "o.tsv"
    r = run(f.url, out)
    assert r.returncode == 1 and not out.exists()


def test_version_missing(fake, tmp_path):
    f = fake(b"file_sha256\trow_count\tpost_count\n", BODY)
    out = tmp_path / "o.tsv"
    r = run(f.url, out)
    assert r.returncode == 1 and not out.exists() and "版がありません" in r.stderr
    assert len(f.seen) == 1


def test_rc_nonzero(fake, tmp_path):
    f = fake(b"rejected: x\n", BODY, ver_rc="2", ver_status=400)
    out = tmp_path / "o.tsv"
    r = run(f.url, out)
    assert r.returncode == 1 and not out.exists()
    assert "http=400" in r.stderr and "rc=2" in r.stderr and "rejected: x" in r.stderr


def test_rc_nonzero_on_rows(fake, tmp_path):
    sha = hashlib.sha256(BODY).hexdigest()
    f = fake(ver_reply(sha, 3), b"db error: X\n", rows_rc="4", rows_status=400)
    out = tmp_path / "o.tsv"
    r = run(f.url, out)
    assert r.returncode == 1 and not out.exists() and "rc=4" in r.stderr


def test_http_200_but_rc_nonzero(fake, tmp_path):
    f = fake(b"x\n", BODY, ver_rc="5")
    r = run(f.url, tmp_path / "o.tsv")
    assert r.returncode == 1


def test_sql_has_no_write_words_and_limit_line():
    for sql in (fg.version_sql("gold_v1"), fg.rows_sql("gold_v1")):
        assert not WRITE_RE.search(sql), sql
    assert fg.rows_sql("gold_v1").split("\n")[0] == "-- limit=5000"
    assert 'as "投稿id"' in fg.rows_sql("gold_v1") and 'as "PO確認"' in fg.rows_sql("gold_v1")
    assert "order by row_no" in fg.rows_sql("gold_v1")


def test_bad_version_rejected():
    for v in ("x'; select 1 --", "Gold", ""):
        with pytest.raises(ValueError):
            fg.rows_sql(v)
