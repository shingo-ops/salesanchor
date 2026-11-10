"""2 つの JSONL（replay_words.py の出力）を比べ、どれかの列が変わった件と件の数が違う投稿を全部出す。

app を import しない（手元でも動く）。キーは（post_id, index）。
起動: python diff_any.py BEFORE AFTER --out-dir D --words 語,語
出力: summary.tsv / changed_any.tsv / post_counts.tsv
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

# v102_replay_diff.COLUMNS と同じ（app を import しないので写しを持つ）
COLUMNS = (
    "lines", "product", "unit", "unit_kubun", "condition", "condition_basis", "price", "quantity", "status",
    "soldout_targets", "soldout_target_basis",
)


def read_jsonl(path: Path) -> dict[tuple[str, int], dict]:
    out: dict[tuple[str, int], dict] = {}
    for ln in Path(path).read_text(encoding="utf-8").splitlines():
        if ln.strip():
            row = json.loads(ln)
            out[(str(row["post_id"]), int(row["index"]))] = row
    return out


def split_words(value: str) -> list[str]:
    return [w.strip() for w in value.split(",") if w.strip()]


def diff_any(before: Path, after: Path, out_dir: Path, words: list[str]) -> dict:
    old, new = read_jsonl(before), read_jsonl(after)
    both = sorted(set(old) & set(new))
    counts = {c: 0 for c in COLUMNS}
    changed_rows: list[tuple[str, int, str, str]] = []
    for key in both:
        cols = [c for c in COLUMNS if old[key].get(c) != new[key].get(c)]
        for c in cols:
            counts[c] += 1
        if cols:
            detail = {c: {"before": old[key].get(c), "after": new[key].get(c)} for c in cols}
            changed_rows.append((key[0], key[1], ",".join(cols), json.dumps(detail, ensure_ascii=False, default=str)))
    word_hits = 0
    for key in new:
        basis = new[key].get("condition_basis")
        if isinstance(basis, str) and any(w in basis for w in words):
            word_hits += 1
    old_n = Counter(k[0] for k in old)
    new_n = Counter(k[0] for k in new)
    post_rows = [(p, old_n.get(p, 0), new_n.get(p, 0)) for p in sorted(set(old_n) | set(new_n)) if old_n.get(p, 0) != new_n.get(p, 0)]

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    with (out / "summary.tsv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, delimiter="\t")
        w.writerow(["column", "diff_count"])
        for c in COLUMNS:
            w.writerow([c, counts[c]])
        w.writerow(["any_changed", len(changed_rows)])
        w.writerow(["only_before", len(set(old) - set(new))])
        w.writerow(["only_after", len(set(new) - set(old))])
        w.writerow(["after_basis_has_words", word_hits])
    with (out / "changed_any.tsv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, delimiter="\t")
        w.writerow(["post_id", "index", "changed_columns", "before_after_json"])
        w.writerows(changed_rows)
    with (out / "post_counts.tsv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, delimiter="\t")
        w.writerow(["post_id", "before_count", "after_count"])
        w.writerows(post_rows)
    return {"compared": len(both), "any_changed": len(changed_rows), "posts_count_differs": len(post_rows),
            "after_basis_has_words": word_hits, **counts}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="どれかの列が変わった件・件の数が違う投稿を全部出す")
    p.add_argument("before", type=Path)
    p.add_argument("after", type=Path)
    p.add_argument("--out-dir", required=True, type=Path)
    p.add_argument("--words", default="", help="足した語（カンマ区切り）。後の condition_basis に含む件を数える")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    print(diff_any(args.before, args.after, args.out_dir, split_words(args.words)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
