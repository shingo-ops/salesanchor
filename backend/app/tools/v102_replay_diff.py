"""保存済みの件（extraction_items）から v102 の後処理だけをやり直し、前後の差を見る道具（Gemini は呼ばない・DB は読むだけ）。

設計: docs/handoff/v102-heading-and-unit/design-heading.md「試験」
起動:
  python -m app.tools.v102_replay_diff --posts <投稿 id のファイル> --out <JSONL> [--heading-setting <JSON ファイル>]
  python -m app.tools.v102_replay_diff diff <前の JSONL> <後の JSONL> --out-dir <ディレクトリ>

line_analysis_v102_svc.run_v102_analysis の読み取りの部分だけを同じ順で行い、run_v102_pipeline までを呼ぶ。
書き込み・commit・pg_advisory_xact_lock は呼ばない。--heading-setting があれば、マスタの condition_heading だけを差し替える（設定の表は書かない）。
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from dataclasses import replace as dataclass_replace
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services import line_analysis_v102_svc as svc
from app.services.gemini_raw_copy_v102_product_first import validate_condition_heading

logger = logging.getLogger(__name__)

# JSONL の 1 行 = 1 件。差の道具が列ごとに数える列
COLUMNS = (
    "lines", "product", "unit", "unit_kubun", "condition", "condition_basis", "price", "quantity", "status",
    "soldout_targets", "soldout_target_basis",
)
_BASIS_LIMIT = 100  # 保存時に切られる長さ（line_analysis_v102_svc と同じ）
_ITEMS_SQL = """
    SELECT id, gemini_index, source_lines, line_start, line_end, raw_price, raw_quantity FROM {schema}.extraction_items
    WHERE extraction_job_id = :ej ORDER BY gemini_index NULLS LAST, created_at, id
"""
_JOB_SQL = "SELECT gemini_unsure, review_reasons FROM {schema}.extraction_jobs WHERE id = :ej"


def _refuse_gemini(*_args: object, **_kwargs: object) -> dict:
    raise RuntimeError("v102_replay_diff は Gemini を呼びません")


def disable_gemini() -> None:
    """line_analysis_v102_svc._call_gemini を「呼ばれたら RuntimeError」に差し替える（台本の最初に呼ぶ）。"""
    svc._call_gemini = _refuse_gemini  # type: ignore[assignment]


def read_posts(path: Path) -> list[str]:
    """投稿（extraction_job）の id を 1 行 1 件で読む。空行と # で始まる行は飛ばす。"""
    rows = [ln.strip() for ln in Path(path).read_text(encoding="utf-8").splitlines()]
    return [r for r in rows if r and not r.startswith("#")]


def load_heading_setting(path: Path):
    """--heading-setting の JSON ファイルを設定と同じ検査にかける（通らなければ None）。"""
    return validate_condition_heading(Path(path).read_text(encoding="utf-8"))


def item_record(post_id: str, index: int, item: dict) -> dict:
    basis = item.get("condition_basis")
    return {
        "post_id": post_id, "index": index,
        "lines": list(item.get("lines") or []),
        "product": item.get("product_id"),
        "unit": item.get("unit"), "unit_kubun": item.get("unit_kubun"),
        "condition": item.get("condition"),
        "condition_basis": basis, "condition_basis_100": basis[:_BASIS_LIMIT] if isinstance(basis, str) else basis,
        "price": item.get("price_normalized"), "quantity": item.get("quantity_normalized"),
        "status": item.get("status"),
        "soldout_targets": item.get("soldout_targets"), "soldout_target_basis": item.get("soldout_target_basis"),
    }


def replay_post(session: Session, job_id: str, masters: dict) -> list[dict]:
    """1 投稿ぶん。run_v102_analysis の読み取りの部分と同じ順で、run_v102_pipeline まで。"""
    from app.tasks.tcg_extraction import load_extraction_context  # noqa: PLC0415  循環 import を避ける

    schema = svc.analyzer.TCG_SCHEMA
    ctx = load_extraction_context(session, job_id)
    if ctx is None:
        raise ValueError(f"extraction_job が見つかりません: {job_id}")
    job = session.execute(text(_JOB_SQL.format(schema=schema)), {"ej": job_id}).one()
    rows = session.execute(text(_ITEMS_SQL.format(schema=schema)), {"ej": job_id}).fetchall()
    if not rows:
        return []
    response_text = svc._response_from_rows(rows, job.gemini_unsure)
    decisions = svc.load_v102_decisions(session, [str(r.id) for r in rows])
    fixed_products = svc._fixed_products(response_text, ctx, masters, rows, decisions)
    followup_masters = svc.masters_with_followup(
        masters, svc.load_followup_reference(session, job_id), svc.load_soldout_ref_posts(session, job_id),
        svc.load_posted_date(session, job_id),
    )
    pipeline = svc.run_v102_pipeline(response_text, ctx, followup_masters, fixed_products=fixed_products)
    return [item_record(job_id, i, it) for i, it in enumerate(pipeline.get("v102_items") or [])]


def replay(session: Session, posts: list[str], out_path: Path, heading_setting: Path | None = None) -> dict:
    """posts の各投稿をやり直して out_path（JSONL）に書く。1 投稿の失敗は記録して次へ進む。"""
    disable_gemini()
    masters, _unit_ids = svc.load_v102_masters(session)  # 1 回だけ読む
    if heading_setting is not None and masters.get("product_first") is not None:
        rule = load_heading_setting(heading_setting)
        masters = {**masters, "product_first": dataclass_replace(masters["product_first"], condition_heading=rule)}
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).unlink(missing_ok=True)
    stats = {"posts": 0, "items": 0, "errors": 0}
    with Path(out_path).open("a", encoding="utf-8") as fh:
        for job_id in posts:
            stats["posts"] += 1
            try:
                records = replay_post(session, job_id, masters)
            except Exception as exc:  # noqa: BLE001
                stats["errors"] += 1
                logger.error("[v102_replay_diff] job=%s: %s", job_id, type(exc).__name__)
                continue
            finally:
                session.rollback()  # 読み取りだけ。何も書かない
            for rec in records:
                fh.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
            stats["items"] += len(records)
    return stats


# ---------------------------------------------------------------------------
# 差の道具
# ---------------------------------------------------------------------------


def _read_jsonl(path: Path) -> dict[tuple[str, int], dict]:
    out: dict[tuple[str, int], dict] = {}
    for ln in Path(path).read_text(encoding="utf-8").splitlines():
        if ln.strip():
            row = json.loads(ln)
            out[(str(row["post_id"]), int(row["index"]))] = row
    return out


def diff_files(before: Path, after: Path, out_dir: Path) -> dict:
    """2 つの JSONL を 投稿 id＋件の位置 で突き合わせ、summary.tsv（列ごとの差の件数）と changed.tsv（状態が変わった件）を書く。"""
    old, new = _read_jsonl(before), _read_jsonl(after)
    both = sorted(set(old) & set(new))
    counts = {c: 0 for c in COLUMNS}
    changed: list[tuple] = []
    for key in both:
        for c in COLUMNS:
            if old[key].get(c) != new[key].get(c):
                counts[c] += 1
        if old[key].get("condition") != new[key].get("condition"):
            changed.append((
                key[0], key[1], json.dumps(new[key].get("lines")),
                old[key].get("condition"), new[key].get("condition"),
                old[key].get("condition_basis"), new[key].get("condition_basis"),
            ))
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    with (out / "summary.tsv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, delimiter="\t")
        w.writerow(["column", "diff_count"])
        for c in COLUMNS:
            w.writerow([c, counts[c]])
        w.writerow(["only_before", len(set(old) - set(new))])
        w.writerow(["only_after", len(set(new) - set(old))])
    with (out / "changed.tsv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, delimiter="\t")
        w.writerow(["post_id", "index", "lines", "condition_before", "condition_after", "basis_before", "basis_after"])
        w.writerows(changed)
    return {"compared": len(both), "changed": len(changed), **counts}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="保存済みの件から v102 の後処理をやり直す／前後の差を見る（Gemini は呼ばない）")
    sub = p.add_subparsers(dest="cmd")
    d = sub.add_parser("diff", help="2 つの JSONL の差")
    d.add_argument("before", type=Path)
    d.add_argument("after", type=Path)
    d.add_argument("--out-dir", required=True, type=Path)
    p.add_argument("--posts", type=Path, help="投稿（extraction_job）の id のファイル")
    p.add_argument("--out", type=Path, help="出力の JSONL")
    p.add_argument("--heading-setting", type=Path, help="v102_condition_heading と同じ形の JSON ファイル（任意）")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if args.cmd == "diff":
        print(diff_files(args.before, args.after, args.out_dir))
        return 0
    if args.posts is None or args.out is None:
        print("--posts と --out が要ります", file=sys.stderr)
        return 2
    from app.tasks.tcg_extraction import _get_sync_session  # noqa: PLC0415

    session = _get_sync_session()
    try:
        stats = replay(session, read_posts(args.posts), args.out, args.heading_setting)
    finally:
        session.close()
    print(stats)
    return 0 if stats["errors"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
