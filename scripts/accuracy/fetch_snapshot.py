#!/usr/bin/env python3
"""システムの答えの写し(snapshot)を、読むだけの窓口(ADR-1042)から作る道具。標準ライブラリのみ。

使い方:
  python3 -I scripts/accuracy/fetch_snapshot.py --gold-version gold_v1 --out-dir DIR [--engine v102-f_ct] [--url U] [--batch 25]

- 正解表(ADR-1043)の投稿ごとに、score_v102.py が読む14列を DIR/<投稿id>.tsv に書く。0行の投稿はファイルを作らない。
- 停止の条件(どれか1つでも当たれば、ファイルを1つも書かず終了コード1): HTTP が 200 でない・rc が 0 でない・
  見出しが想定と違う・返った行数が limit 以上・値に \\ を含む・値が 10240 文字以上・投稿数が版の記録と違う・
  DIR に既に .tsv がある・投稿id が UUID の形でない。
- 写しは社外秘。DIR はリポジトリの外に置く。投稿id・値・鍵は画面に出さない。
- 鍵: fetch_gold.py と同じ(クラウドは自動、手元は環境変数 READ_WINDOW_TOKEN)。
"""
import argparse
import datetime
import glob
import importlib.util
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
VERSION_RE = re.compile(r"^[a-z0-9_]+$")
ENGINE_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
DEFAULT_ENGINE = "v102-f_ct"
DEFAULT_BATCH = 25
MAX_VALUE_LEN = 10240


def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_fg = _load("fetch_gold")
_sc = _load("score_v102")
post = _fg.post
fail_http = _fg.fail_http
DEFAULT_URL = _fg.DEFAULT_URL
ROW_LIMIT = _fg.ROW_LIMIT
SNAP_COLS = list(_sc.SNAP_COLS)
HEADER = SNAP_COLS + ["post_id"]
# 写しの列が、どの表(別名)にあるか。ai_ro の拒否正規表現に当たる別名は使わない
_ITEM_COLS = {"extraction_item_id": "i.id", "line_start": "i.line_start", "line_end": "i.line_end",
              "source_lines": "i.source_lines", "raw_price": "i.raw_price", "raw_quantity": "i.raw_quantity"}


def _check_version(version):
    if not VERSION_RE.fullmatch(version):
        raise ValueError("gold-version は英小文字・数字・_ だけです")


def posts_sql(version):
    """正解表にある投稿の一覧を返す問い合わせ。"""
    _check_version(version)
    return ("-- limit=%d\nselect distinct post_id::text as post_id from ai_ro.public__accuracy_gold_rows "
            "where gold_version = '%s' order by 1" % (ROW_LIMIT, version))


def count_sql(version):
    """版の記録の投稿数(post_count)を返す問い合わせ。"""
    _check_version(version)
    return ("select post_count from ai_ro.public__accuracy_gold_versions where gold_version = '%s'" % version)


def snapshot_sql(post_ids, engine):
    """投稿の写しを返す問い合わせ。投稿id は UUID の形を全部検証してから埋める。"""
    if not ENGINE_RE.fullmatch(engine):
        raise ValueError("engine は英数字・_ . - だけです")
    if not post_ids:
        raise ValueError("投稿がありません")
    for p in post_ids:
        if not UUID_RE.fullmatch(p):
            raise ValueError("投稿id が UUID の形ではありません")
    cols = ["%s as %s" % (_ITEM_COLS.get(c, "ar." + c), c) for c in SNAP_COLS]
    cols.append("j.source_message_id::text as post_id")
    return ("-- limit=%d\nselect %s from ai_ro.public__extraction_jobs j "
            "join ai_ro.public__extraction_items i on i.extraction_job_id = j.id "
            "join ai_ro.public__analysis_results ar on ar.extraction_item_id = i.id "
            "where j.source_message_id in (%s) and ar.engine_version = '%s' "
            "order by i.line_start, i.gemini_index, ar.computed_at, ar.id"
            % (ROW_LIMIT, ", ".join(cols), ", ".join("'%s'" % p for p in post_ids), engine))


def _lines(body):
    lines = body.decode("utf-8").split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return lines


def parse_posts(body, limit=ROW_LIMIT):
    """投稿一覧の応答を投稿idの並びにする。違反は ValueError(値は入れない)。"""
    try:
        lines = _lines(body)
    except UnicodeDecodeError:
        raise ValueError("投稿一覧の応答が UTF-8 ではありません")
    if not lines or lines[0] != "post_id":
        raise ValueError("投稿一覧の見出しが想定と違います")
    ids = lines[1:]
    if len(ids) >= limit:
        raise ValueError("投稿一覧の行数が limit 以上です(打ち切りの疑い)")
    if any(not UUID_RE.fullmatch(p) for p in ids):
        raise ValueError("投稿id が UUID の形ではありません")
    return ids


def parse_count(body):
    """版の記録の投稿数(整数)。"""
    try:
        lines = _lines(body)
        if len(lines) != 2 or lines[0] != "post_count":
            raise ValueError
        return int(lines[1])
    except (ValueError, UnicodeDecodeError):
        raise ValueError("版の記録の応答が想定と違います")


def parse_snapshot(body, limit):
    """写しの応答を {投稿id: [行(post_id 列を除いた14列を tab でつないだもの)]} にする。違反は ValueError。"""
    try:
        lines = _lines(body)
    except UnicodeDecodeError:
        raise ValueError("写しの応答が UTF-8 ではありません")
    if not lines or lines[0].split("\t") != HEADER:
        raise ValueError("写しの見出しが想定の %d 列と違います" % len(HEADER))
    rows = lines[1:]
    if len(rows) >= limit:
        raise ValueError("返った行数が limit 以上です(打ち切りの疑い)")
    out = {}
    bad_bs = {}
    for line in rows:
        cols = line.split("\t")
        if len(cols) != len(HEADER):
            raise ValueError("写しの行の列数が想定と違います")
        for name, v in zip(HEADER, cols):
            if len(v) >= MAX_VALUE_LEN:
                raise ValueError("値の長さが %d 文字以上です(窓口の切り詰めの疑い。列=%s)" % (MAX_VALUE_LEN, name))
            if "\\" in v:
                bad_bs[name] = bad_bs.get(name, 0) + 1
        pid = cols[-1]
        if not UUID_RE.fullmatch(pid):
            raise ValueError("投稿id が UUID の形ではありません")
        out.setdefault(pid, []).append("\t".join(cols[:-1]))
    if bad_bs:
        raise ValueError("値に \\ を含みます(窓口が改行・タブ・\\ を置き換えた印)。件数=%d 列=%s"
                         % (sum(bad_bs.values()), ",".join(sorted(bad_bs))))
    return out


def _stop(msg):
    sys.stderr.write("STOP: %s\n" % msg)
    return 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--gold-version", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--engine", default=DEFAULT_ENGINE)
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--batch", type=int, default=DEFAULT_BATCH)
    a = ap.parse_args(argv)
    token = os.environ.get("READ_WINDOW_TOKEN") or None
    if a.batch < 1:
        return _stop("batch は 1 以上です")
    if glob.glob(os.path.join(a.out_dir, "*.tsv")):
        return _stop("出力先に既に .tsv があります(混ざらないよう停止)")
    try:
        psql = posts_sql(a.gold_version)
        csql = count_sql(a.gold_version)
        snapshot_sql(["00000000-0000-4000-8000-000000000000"], a.engine)  # engine の形の検査
    except ValueError as e:
        return _stop(e)

    status, rc, body = post(a.url, psql, token)
    if status != 200 or rc != "0":
        return fail_http(status, rc, body)
    try:
        ids = parse_posts(body)
    except ValueError as e:
        return _stop(e)
    status, rc, body = post(a.url, csql, token)
    if status != 200 or rc != "0":
        return fail_http(status, rc, body)
    try:
        want = parse_count(body)
    except ValueError as e:
        return _stop(e)
    if want != len(ids) or len(set(ids)) != len(ids):
        return _stop("投稿数が版の記録と違います(一覧=%d 記録=%d)" % (len(ids), want))

    result = {}
    for k in range(0, len(ids), a.batch):
        chunk = ids[k:k + a.batch]
        try:
            sql = snapshot_sql(chunk, a.engine)
        except ValueError as e:
            return _stop(e)
        status, rc, body = post(a.url, sql, token)
        if status != 200 or rc != "0":
            return fail_http(status, rc, body)
        try:
            got = parse_snapshot(body, ROW_LIMIT)
        except ValueError as e:
            return _stop(e)
        if not set(got) <= set(chunk):
            return _stop("要求していない投稿の行が返りました")
        result.update(got)

    os.makedirs(a.out_dir, exist_ok=True)
    head = "\t".join(SNAP_COLS) + "\n"
    for pid, rows in result.items():
        with open(os.path.join(a.out_dir, pid + ".tsv"), "w", encoding="utf-8", newline="") as f:
            f.write(head + "".join(r + "\n" for r in rows))
    print("posts=%d with_rows=%d rows=%d fetched_at=%s engine=%s" % (
        len(ids), len(result), sum(len(r) for r in result.values()),
        datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), a.engine))
    return 0


if __name__ == "__main__":
    sys.exit(main())
