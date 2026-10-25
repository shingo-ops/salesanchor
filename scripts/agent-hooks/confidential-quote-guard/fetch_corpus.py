#!/usr/bin/env python3
"""見張りの見比べる相手(本番の投稿原文)の写しを、本番から1つだけ取り直す。ADR-1045 / 決定 PO 2026-10-25「1」。

読み取りは ADR-1024 の道だけ(読み取り専用の鍵 + ai_ro の同名ビュー)。manual-only の鍵は使わない。
書くのは社外秘フォルダ(既定 ~/CC報告ファイル-keep/confid-guard)の下の2ファイルだけ:
  source-messages.txt   全行の raw_text(is_active に関係なく)。権限 600。フォルダは 700
  source-messages.meta  件数・文字数の合計・取った日時(本文は入れない)
一時ファイルに書き、件数と文字数が本番の数と一致するのを確かめてから置き換える。
途中で失敗したら前の写しを残し、0 以外で終わる。前回より件数が半分未満に減ったときも置き換えず止める。
このスクリプトにも repo にも、本文・語句は入れない。標準出力は件数と日時だけ。

終了コード: 0 成功 / 1 失敗(前の写しは残る) / 2 件数が大きく減った(前の写しは残る) / 3 別の実行中
環境変数(試験用): CONFID_GUARD_DIR  CONFID_FETCH_CMD(ssh の代わりの実行ファイル。標準入力のSQLを受けTSVを返す)
"""
import datetime
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

HOST = "ubuntu@49.212.137.46"
KEY = os.path.expanduser("~/.ssh/salesanchor-reader")
VIEW = "ai_ro.public__source_messages"
PART = 8000          # 読み取り台本は 1 値 10,240 字で切るので、8,000 字ずつに分けて取る
BATCH = int(os.environ.get("CONFID_FETCH_BATCH", "5000"))  # 読み取り台本の行数の上限(試験では小さくする)
SHRINK_RATIO = 0.5   # 前回の半分未満なら置き換えない
TIMEOUT = 150

D = os.path.expanduser(os.environ.get("CONFID_GUARD_DIR", "~/CC報告ファイル-keep/confid-guard"))
OUT = os.path.join(D, "source-messages.txt")
META = os.path.join(D, "source-messages.meta")


def die(msg, rc=1):
    sys.stderr.write("FETCH_FAILED: %s\n" % msg)
    sys.exit(rc)


def run_sql(sql):
    cmd = os.environ.get("CONFID_FETCH_CMD")
    if cmd:
        argv = [cmd]
    else:
        argv = ["ssh", "-F", "/dev/null", "-i", KEY, "-o", "IdentitiesOnly=yes", "-o", "BatchMode=yes",
                "-o", "ConnectTimeout=20", HOST]
    try:
        p = subprocess.run(argv, input=sql.encode("utf-8"), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                           timeout=TIMEOUT)
    except (OSError, subprocess.TimeoutExpired) as e:
        die("読み取りの道に繋げません (%s)" % type(e).__name__)
    if p.returncode != 0:
        die("読み取りの道が rc=%d" % p.returncode)
    lines = p.stdout.decode("utf-8").split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return lines


ESC = re.compile(r"\\([\\tnr])")
ESC_MAP = {"\\": "\\", "t": "\t", "n": "\n", "r": "\r"}


def unescape(s):
    return ESC.sub(lambda m: ESC_MAP[m.group(1)], s)


def totals():
    sql = "SELECT count(*) AS n, coalesce(sum(length(raw_text)),0) AS chars FROM %s WHERE raw_text IS NOT NULL" % VIEW
    rows = run_sql(sql)
    if len(rows) != 2:
        die("件数の問い合わせの形が違います")
    try:
        n, c = rows[1].split("\t")
        return int(n), int(c)
    except ValueError:
        die("件数の問い合わせの値が読めません")


def fetch_all():
    """(id, part) の順に分けて取り、id ごとに繋ぐ。戻りは本文のリスト。"""
    msgs, cur_id, cur_parts = [], None, []
    last = None
    while True:
        cond = "" if last is None else "AND (id::text, p) > ('%s', %d)" % last
        sql = (
            "-- limit=%d\n"
            "SELECT id::text AS id, p, substr(raw_text, p * %d + 1, %d) AS t FROM ("
            "SELECT id, raw_text, generate_series(0, GREATEST((length(raw_text) - 1) / %d, 0)) AS p "
            "FROM %s WHERE raw_text IS NOT NULL) x WHERE true %s ORDER BY id::text, p"
        ) % (BATCH, PART, PART, PART, VIEW, cond)
        rows = run_sql(sql)
        if not rows or rows[0].split("\t") != ["id", "p", "t"]:
            die("取り出しの見出しが違います")
        body = rows[1:]
        for ln in body:
            f = ln.split("\t", 2)
            if len(f) != 3:
                die("取り出しの列数が違います")
            rid, p, t = f[0], int(f[1]), unescape(f[2])
            if rid != cur_id:
                if cur_id is not None:
                    msgs.append("".join(cur_parts))
                cur_id, cur_parts = rid, []
            cur_parts.append(t)
            last = (rid, p)
        if len(body) < BATCH:
            break
    if cur_id is not None:
        msgs.append("".join(cur_parts))
    return msgs


def read_meta():
    try:
        with open(META, encoding="utf-8") as f:
            return {k: v for k, v in (ln.rstrip("\n").split("=", 1) for ln in f if "=" in ln)}
    except OSError:
        return {}


def main():
    os.makedirs(D, mode=0o700, exist_ok=True)
    os.chmod(D, 0o700)
    lock = os.path.join(D, ".fetch.lock.d")
    try:
        os.mkdir(lock)
    except FileExistsError:
        try:
            stale = time.time() - os.path.getmtime(lock) > 1800   # 強制終了で残った古いロックは外す
        except OSError:
            stale = False
        if not stale:
            print("別の取り直しが動いています。今回は何もしません。")
            sys.exit(3)
        try:
            os.rmdir(lock)
            os.mkdir(lock)
        except OSError:
            print("別の取り直しが動いています。今回は何もしません。")
            sys.exit(3)
    try:
        for attempt in (1, 2):   # 取り直しの間に本番へ投稿が増えたときの1回だけの再試行
            msgs = fetch_all()
            n, c = totals()
            got_n, got_c = len(msgs), sum(len(m) for m in msgs)
            if (got_n, got_c) == (n, c):
                break
        else:
            die("本番の数と合いません(件数 %d/%d、文字数 %d/%d)" % (got_n, n, got_c, c))
        if got_n == 0:
            die("0 件です")
        prev = read_meta()
        try:
            prev_n = int(prev.get("rows", "0"))
        except ValueError:
            prev_n = 0
        if prev_n and got_n < prev_n * SHRINK_RATIO:
            die("前回 %d 件から %d 件に大きく減りました。置き換えません" % (prev_n, got_n), 2)
        fd, tmp = tempfile.mkstemp(prefix=".source-messages.", dir=D)
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write("\n".join(msgs) + "\n")
            mfd, mtmp = tempfile.mkstemp(prefix=".source-messages.meta.", dir=D)
            now = datetime.datetime.now(datetime.timezone.utc)
            os.fchmod(mfd, 0o600)
            with os.fdopen(mfd, "w", encoding="utf-8") as f:
                f.write("rows=%d\nchars=%d\nprev_rows=%d\nfetched_at=%s\nfetched_epoch=%d\n"
                        % (got_n, got_c, prev_n, now.strftime("%Y-%m-%dT%H:%M:%SZ"), int(now.timestamp())))
            os.replace(tmp, OUT)
            os.replace(mtmp, META)
        except BaseException:
            for p in (tmp, locals().get("mtmp")):
                if p and os.path.exists(p):
                    os.remove(p)
            raise
        print("FETCH_OK rows=%d chars=%d prev_rows=%d at=%s" % (got_n, got_c, prev_n, now.strftime("%Y-%m-%dT%H:%M:%SZ")))
    finally:
        try:
            os.rmdir(lock)
        except OSError:
            pass


if __name__ == "__main__":
    main()
