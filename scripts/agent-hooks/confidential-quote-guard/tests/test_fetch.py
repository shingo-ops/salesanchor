#!/usr/bin/env python3
"""fetch_corpus.py の試験。本番には繋がない(CONFID_FETCH_CMD に偽の読み取り口を差す)。本文は作り物だけ。
使い方: python3 tests/test_fetch.py [fetch_corpus.py のパス]"""
import os
import shutil
import stat
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
FETCH = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(HERE, "..", "fetch_corpus.py")
T = tempfile.mkdtemp(prefix="fetchtest-")
D = os.path.join(T, "g")
FAKE = os.path.join(T, "fake_ssh.py")
DATA = os.path.join(T, "data.txt")      # 偽の本番: 1 行 = id<TAB>本文(\\n と \\t は文字として書く)
results = []

FAKE_SRC = r'''#!/usr/bin/env python3
import os, re, sys
sql = sys.stdin.read()
if os.environ.get("FAKE_FAIL"):
    sys.exit(4)
rows = []
for ln in open(os.environ["FAKE_DATA"], encoding="utf-8").read().split("\n"):
    if ln:
        i, t = ln.split("\t", 1)
        rows.append((i, t.replace("\\n", "\n").replace("\\t", "\t").replace("\\\\", "\\")))
def esc(s):
    return s.replace("\\", "\\\\").replace("\t", "\\t").replace("\n", "\\n").replace("\r", "\\r")
if "count(*)" in sql:
    print("n\tchars"); print("%d\t%d" % (len(rows), sum(len(t) for _, t in rows))); sys.exit(0)
lim = int(re.match(r"-- limit=(\d+)", sql).group(1))
part = int(re.search(r"p \* (\d+) \+ 1", sql).group(1))
m = re.search(r"\(id::text, p\) > \('([^']*)', (\d+)\)", sql)
last = (m.group(1), int(m.group(2))) if m else None
out = []
for i, t in sorted(rows):
    for p in range(max((len(t) - 1) // part, 0) + 1):
        if last is None or (i, p) > last:
            out.append((i, p, t[p * part:(p + 1) * part]))
print("id\tp\tt")
for i, p, t in out[:lim]:
    print("%s\t%d\t%s" % (i, p, esc(t)))
'''


def put(rows):
    with open(DATA, "w", encoding="utf-8") as f:
        for i, t in rows:
            f.write("%s\t%s\n" % (i, t))


def fetch(**env):
    e = dict(os.environ, CONFID_GUARD_DIR=D, CONFID_FETCH_CMD=FAKE, FAKE_DATA=DATA, CONFID_FETCH_BATCH="3",
             PYTHONDONTWRITEBYTECODE="1")
    e.update(env)
    return subprocess.run([sys.executable, FETCH], capture_output=True, text=True, env=e)


def check(name, ok):
    results.append(bool(ok))
    print("%s %s" % ("PASS" if ok else "FAIL", name))


def main():
    with open(FAKE, "w") as f:
        f.write(FAKE_SRC)
    os.chmod(FAKE, 0o755)
    long_t = "あ" * 20050 + "終"       # 8000 字ごとに 3 つに割れる
    rows = [("a%02d" % k, "本文%d\\n二行目\\t字下げ\\\\" % k) for k in range(7)] + [("b00", long_t), ("c00", "")]
    put(rows)
    r = fetch()
    out = os.path.join(D, "source-messages.txt")
    meta = os.path.join(D, "source-messages.meta")
    check("F1 初回: rc=0 で FETCH_OK", r.returncode == 0 and r.stdout.startswith("FETCH_OK rows=9 "))
    txt = open(out, encoding="utf-8").read() if os.path.exists(out) else ""
    check("F2 長い本文(3分割)が1つに繋がる", long_t in txt)
    check("F3 改行・タブ・バックスラッシュが元に戻る", "本文3\n二行目\t字下げ\\" in txt)
    check("F4 権限: ファイル 600・フォルダ 700",
          stat.S_IMODE(os.stat(out).st_mode) == 0o600 and stat.S_IMODE(os.stat(meta).st_mode) == 0o600
          and stat.S_IMODE(os.stat(D).st_mode) == 0o700)
    m = open(meta, encoding="utf-8").read()
    check("F5 meta に件数・文字数・日時があり本文が無い", "rows=9" in m and "chars=" in m and "fetched_at=" in m and "本文" not in m)
    before = open(out, encoding="utf-8").read()
    put(rows[:3])
    r = fetch()
    check("F6 件数が半分未満に減る -> rc=2 で前の写しを残す",
          r.returncode == 2 and open(out, encoding="utf-8").read() == before)
    put(rows)
    r = fetch(FAKE_FAIL="1")
    check("F7 読み取りの道が失敗 -> rc!=0 で前の写しを残す",
          r.returncode != 0 and open(out, encoding="utf-8").read() == before)
    left = [f for f in os.listdir(D) if f.startswith(".source-messages.")]
    check("F8 失敗しても一時ファイルとロックが残らない", not left and not os.path.exists(os.path.join(D, ".fetch.lock.d")))
    os.mkdir(os.path.join(D, ".fetch.lock.d"))
    r = fetch()
    check("F9 別の取り直しが動いている -> rc=3 で何もしない", r.returncode == 3)
    os.rmdir(os.path.join(D, ".fetch.lock.d"))
    put(rows + [("d00", "追加")])
    r = fetch()
    check("F10 件数が増えれば置き換わる", r.returncode == 0 and "rows=10" in r.stdout)
    n_ok = sum(results)
    print("PASS %d / FAIL %d" % (n_ok, len(results) - n_ok))
    return 0 if n_ok == len(results) else 1


if __name__ == "__main__":
    try:
        rc = main()
    finally:
        shutil.rmtree(T, ignore_errors=True)
    sys.exit(rc)
