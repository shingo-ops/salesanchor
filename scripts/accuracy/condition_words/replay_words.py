"""状態の語を（記憶の中だけで）足して v102 の後処理をやり直す台本（Gemini は呼ばない・DB は読むだけ）。

設計: docs/handoff/condition-shrink-abbr/design.md §8
起動（本番の箱）: PYTHONPATH=/app python replay_words.py --posts F --out JSONL [--add CODE=語,語 ...]
起動（手元）    : PYTHONPATH=backend python scripts/accuracy/condition_words/replay_words.py ...
状態の表（conditions）は書かない。読んだ直後の masters の写しの search_kw に語を足し、除外語用の語も作り直す。
"""
from __future__ import annotations

import argparse
import hashlib
import logging
import sys
from pathlib import Path

from app.services import line_analysis_v102_svc as svc
from app.services.extraction_judgement_svc import build_cond_terms
from app.services.gemini_raw_copy_v102_product_first import with_cond_terms
from app.tools import v102_replay_diff


def add_words(masters: dict, adds: dict[str, list[str]]) -> dict:
    """新しい masters を返す（元は変えない）。adds にある code の行だけ search_kw の末尾に ",語" を足す。"""
    entries = masters["cond_entries"]
    known = {e.get("code") for e in entries}
    missing = sorted(set(adds) - known)
    if missing:
        raise ValueError(f"cond_entries に無い code: {', '.join(missing)}")
    new_entries = []
    for entry in entries:
        words = adds.get(entry.get("code"))
        if not words:
            new_entries.append(entry)
            continue
        kw = entry.get("search_kw") or ""
        have = {w.strip() for w in kw.split(",") if w.strip()}
        for word in words:
            if word not in have:
                kw = f"{kw},{word}" if kw else word
                have.add(word)
        new_entries.append({**entry, "search_kw": kw})
    new_masters = {**masters, "cond_entries": new_entries}
    pf = masters.get("product_first")
    if pf is not None:
        new_masters["product_first"] = with_cond_terms(pf, build_cond_terms(new_entries))
    return new_masters


def parse_add(values: list[str]) -> dict[str, list[str]]:
    """["CN0003=語,語", ...] → {"CN0003": ["語", "語"]}。"""
    adds: dict[str, list[str]] = {}
    for value in values:
        code, sep, words = value.partition("=")
        parsed = [w.strip() for w in words.split(",") if w.strip()]
        if not code.strip() or not sep or not parsed:
            raise ValueError(f"--add は CODE=語,語 の形: {value}")
        bucket = adds.setdefault(code.strip(), [])
        bucket.extend(w for w in parsed if w not in bucket)
    return adds


def kw_digests(masters: dict) -> dict[str, str]:
    """各 code の search_kw の md5（足した後の確認用）。"""
    return {
        str(e.get("code")): hashlib.md5((e.get("search_kw") or "").encode("utf-8")).hexdigest()
        for e in masters["cond_entries"]
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="状態の語を足して v102 の後処理をやり直す（Gemini は呼ばない・DB は読むだけ）")
    p.add_argument("--posts", required=True, type=Path, help="投稿（extraction_job）の id のファイル")
    p.add_argument("--out", required=True, type=Path, help="出力の JSONL")
    p.add_argument("--add", action="append", default=[], help="CODE=語,語（0 回以上）")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    adds = parse_add(args.add)
    from app.tasks.tcg_extraction import _get_sync_session
    from sqlalchemy import text

    original = svc.load_v102_masters
    digests: dict[str, str] = {}

    def patched(session):
        masters, unit_ids = original(session)
        new_masters = add_words(masters, adds)
        digests.update(kw_digests(new_masters))
        return new_masters, unit_ids

    svc.load_v102_masters = patched  # type: ignore[assignment]
    session = _get_sync_session()
    try:
        session.execute(text("SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY"))
        session.commit()  # SET は rollback で取り消されるので、設定だけを確定させる（データは何も書かない）
        stats = v102_replay_diff.replay(session, v102_replay_diff.read_posts(args.posts), args.out)
    finally:
        session.close()
    print(stats)
    print(f"adds={adds}")
    for code in sorted(digests):
        print(f"search_kw_md5 {code} {digests[code]}")
    return 0 if stats["errors"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
