"""まとめ売りの読み取り（v102_bundle_svc.detect_bundle）を、本番の全行に当て直す再現の台本（ADR-1027・読み取り専用）。

使い方:
    python3 -I scripts/dev/bundle_replay.py ALL_ROWS.tsv UNITS_Q3.tsv ALIASES_Q4.tsv OUT_DIR

  ALL_ROWS.tsv  列 item_id・job_id・md5_8・product_id・kubun_type・unit_canonical・price_normalized・quantity_normalized・
                price_basis・needs_review・review_reasons・condition_canonical・note_ja・body のタブ区切り
                （body の行の区切りは " / "）
  UNITS_Q3.tsv  単位マスタ（列 id・code・canonical・kubun・is_active）
  ALIASES_Q4.tsv 単位の別名マスタ（列 unit_id・alias_text・lang）
  OUT_DIR       rows.tsv と summary.txt を書く

通信・DB 書き込みはしない。データ（本番の本文）はリポジトリに置かない。判定の作りは v102_bundle_svc に 1 か所だけ（ここでは持たない）。
"""
from __future__ import annotations

import collections
import csv
import hashlib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from app.services.v102_bundle_svc import (  # noqa: E402
    BUNDLE_WORDS,
    KIND_DECIDED,
    KIND_UNVERIFIED,
    detect_bundle,
    normalize,
    split_unit_words,
)

_BODY_SEPARATOR = " / "
_SET_PRICE_BASIS = re.compile(r"V102:bulk:set:(\d+)")
_VERDICT = {KIND_DECIDED: "decided", KIND_UNVERIFIED: "unverified", None: "none"}


def read_tsv(path: str) -> list[dict[str, str]]:
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE))


def alias_to_canonical(units: list[dict[str, str]], aliases: list[dict[str, str]]) -> dict[str, str]:
    canonical_by_id = {r["id"]: r["canonical"] for r in units}
    return {r["alias_text"]: canonical_by_id[r["unit_id"]] for r in aliases if r["unit_id"] in canonical_by_id}


def read_quantity(row: dict[str, str]) -> str:
    """保存の数量。price_basis が V102:bulk:set:N（換算済み・数量×N）の行は ÷N して換算前（Gemini の読み）に戻す。"""
    quantity = (row["quantity_normalized"] or "").strip()
    if not quantity:
        return ""
    m = _SET_PRICE_BASIS.match((row["price_basis"] or "").strip())
    if not m:
        return quantity
    return str(float(quantity) / int(m.group(1)))


def unknown_word_pattern(unit_words: dict[str, str], set_words: frozenset[str]) -> re.Pattern[str]:
    bundle = "|".join(re.escape(normalize(w)) for w in sorted(BUNDLE_WORDS, key=len, reverse=True))
    return re.compile(rf"(?<!\d)(\d{{1,5}})[^\S\n]*([^\d\s/]{{1,8}}?)[^\S\n]*({bundle})")


def count_unknown_words(rows: list[dict[str, str]], unit_words: dict[str, str], set_words: frozenset[str]) -> collections.Counter:
    """参考: 「N＋別名に無い語＋まとめの語」の当たりの語の数え（判定には使わない。新しい書き方を人が見つけるため）。"""
    pattern = unknown_word_pattern(unit_words, set_words)
    counter: collections.Counter = collections.Counter()
    for r in rows:
        text = normalize(r["body"].replace(_BODY_SEPARATOR, "\n"))
        for m in pattern.finditer(text):
            if int(m.group(1)) < 2 or text[m.end():m.end() + 1] == "入":
                continue
            word = m.group(2)
            if word not in unit_words and word not in set_words:
                counter[word] += 1
                break
    return counter


def main(argv: list[str]) -> int:
    if len(argv) != 5:
        print(__doc__)
        return 2
    all_rows, units_path, aliases_path, out_dir = argv[1:]
    rows = read_tsv(all_rows)
    unit_words, set_words = split_unit_words(alias_to_canonical(read_tsv(units_path), read_tsv(aliases_path)))
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    results = []
    for r in rows:
        block = r["body"].replace(_BODY_SEPARATOR, "\n")
        res = detect_bundle(block, unit_words, set_words, (r["price_normalized"] or "").strip() or None, read_quantity(r) or None)
        results.append((r, res, hashlib.md5(r["body"].encode("utf-8")).hexdigest()[:8]))
    with open(out / "rows.tsv", "w", encoding="utf-8") as f:
        f.write("item_id\tjob_id\tmd5_8\t判定\tN\t単位canonical\t理由\tbody_md5\n")
        for r, res, md5 in results:
            kind = _VERDICT[res.kind if res else None]
            n = "" if res is None or res.n is None else str(res.n)
            unit = "" if res is None or res.unit is None else res.unit
            f.write("\t".join([r["item_id"], r["job_id"], r["md5_8"], kind, n, unit, res.reason if res else "当たりなし", md5]) + "\n")
    lines = ["# bundle_replay summary", "", "入力: %d 行" % len(rows),
             "単位の語（Set を除く）: %d 語。Set の語: %s" % (len(unit_words), sorted(set_words)), "",
             "## 判定ごとの件数", "|判定|行数|本文md5の種数|job数|", "|---|---|---|---|"]
    for kind in ("decided", "unverified", "none"):
        picked = [x for x in results if _VERDICT[x[1].kind if x[1] else None] == kind]
        lines.append("|%s|%d|%d|%d|" % (kind, len(picked), len({x[2] for x in picked}), len({x[0]["job_id"] for x in picked})))
    lines += ["", "## 参考: N＋別名に無い語＋まとめの語（判定には使わない・新しい書き方は人が見る）"]
    unknown = count_unknown_words(rows, unit_words, set_words)
    lines.append("合計 %d 行" % sum(unknown.values()))
    lines += ["- %s: %d" % (w, n) for w, n in unknown.most_common()]
    (out / "summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("rows=%d decided=%d unverified=%d none=%d" % (len(results), *(sum(1 for x in results if _VERDICT[x[1].kind if x[1] else None] == k) for k in ("decided", "unverified", "none"))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
