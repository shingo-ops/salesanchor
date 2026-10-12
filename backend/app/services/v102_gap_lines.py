"""v102 の「間の行」の検知（段1：記録だけ）。純粋な関数だけ。DB も Gemini も呼ばない。

設計: docs/handoff/v102-gap-detect-record/design.md §3 PR②。
- 分類  : 受理された件のどれにも使われていない空でない行を gap / pre / span / trail に分ける。
- T1    : gap の行のうち、価格と数量の形がある行（取りこぼしの疑い）。
- T2/H2 : gap・pre の行を支えにして、商品が決まっていない件（unmatched）の候補を作る。
記録するのは行番号と商品 id だけで、原文は入れない（docs/handoff/v102-no-silent-drop/design.md:31）。
"""
from __future__ import annotations

import json
import re
import unicodedata
from bisect import bisect_right
from collections import defaultdict
from collections.abc import Mapping, Sequence

from app.services.extraction_judgement_svc import product_match_text
from app.services.gemini_raw_copy_v101 import _PRICE_SHAPE_RE, _YEAR_RE, _is_price_shaped
from app.services.gemini_raw_copy_v102_product_first import ProductFirstMasters, match_text_g2

DETAIL_VERSION = 1

CLASS_USED = "used"  # 件の lines・price_line に入っている行
CLASS_PRE = "pre"  # 最初の件より前
CLASS_GAP = "gap"  # 前の件の最終行より後で、次の件の最初の行より前
CLASS_SPAN = "span"  # 件の範囲内の未使用行
CLASS_TRAIL = "trail"  # 最後の件の後

_STATUS_UNMATCHED = "unmatched"
_STATUS_MATCHED = "matched"
_STATUS_AMBIGUOUS = "ambiguous"
_NO_VALUES = frozenset({"none"})

# --- 判定式（measure_gap_detect_v2.py の写し。正規表現は1文字も変えない） -------------------------------
# M: 金額らしい数（カンマ区切り、または4〜6桁の数字。年の形の4桁は除く）
_MONEY_RE = re.compile(r"(?<![\d,])(?:\d{1,3}(?:,\d{3})+|\d{4,6})(?![\d,])")
# Q: 数量らしい形
_Q_TIMES_RE = re.compile(r"[×✕✖*]\s*\d|\d\s*[×✕✖*]|(?<=\d)\s*x\s*(?=\d)", re.I)
_Q_NUM_WORD_RE = re.compile(r"(?<![\d,.])\d{1,4}\s*(?!円)[^\W\d_]{1,8}")
_Q_STOCK_RE = re.compile(r"(?:在庫|数量|残り|残|数)\s*[:：]?\s*\d")
_Q_AT_RE = re.compile(r"\d\s*[^\s@]{0,8}@\s*\d")  # 価格@数量・数量単位@価格（@ の両側に数字）


def has_money(norm: str) -> bool:
    if _PRICE_SHAPE_RE.search(norm):
        return True
    for m in _MONEY_RE.finditer(norm):
        tok = m.group(0)
        if "," not in tok and _YEAR_RE.fullmatch(tok):
            continue
        return True
    return False


def has_q_strict(norm: str) -> bool:
    return bool(_Q_TIMES_RE.search(norm) or _Q_STOCK_RE.search(norm) or _Q_AT_RE.search(norm))


def has_q(norm: str) -> bool:
    return has_q_strict(norm) or bool(_Q_NUM_WORD_RE.search(norm))


def _price_and_qty_shaped(text: str) -> bool:
    """式 F2_price_and_qty。"""
    norm = unicodedata.normalize("NFKC", text).strip()
    return (_is_price_shaped(text) or has_money(norm)) and has_q(norm)


# --- 分類 -------------------------------------------------------------------------------------------


def _first_line(item: Mapping) -> int:
    return min(item["lines"])


def accepted_items(items: Sequence[Mapping]) -> list[Mapping]:
    """受理された件（rejected と、行が空の件を除く）を、最初の行の順に並べる。元の件は変えない。"""
    usable = [it for it in items if "rejected" not in it and it.get("lines")]
    return sorted(usable, key=lambda it: (_first_line(it), it.get("price_line") or 0))


def _item_rows(item: Mapping) -> set[int]:
    rows = set(item["lines"])
    if isinstance(item.get("price_line"), int):
        rows.add(item["price_line"])
    return rows


def classify_lines(sorted_items: Sequence[Mapping], lines: Sequence[str]) -> dict[int, tuple[str, int | None]]:
    """空でない行（1 始まりの行番号）→ (分類, 直後の件の位置)。sorted_items は accepted_items の結果。

    直後の件の位置は、sorted_items の中でその行より後に最初の行がある最初の件（trail と used は None）。
    gap は「それより前の件が使った最後の行」より後の行。前の件の最終行は累積最大を先に作って引く（行数に比例）。
    """
    used: set[int] = set()
    reach_before: list[int] = []  # reach_before[k] = 件 0..k-1 が使った最後の行（k=0 は 0）
    running_max = 0
    for it in sorted_items:
        reach_before.append(running_max)
        rows = _item_rows(it)
        used |= rows
        running_max = max(running_max, max(rows))
    firsts = [_first_line(it) for it in sorted_items]  # 昇順（accepted_items の並び）
    classes: dict[int, tuple[str, int | None]] = {}
    for number, text in enumerate(lines, start=1):
        if not text.strip():
            continue
        if number in used:
            classes[number] = (CLASS_USED, None)
            continue
        k = bisect_right(firsts, number)  # 最初の行が number より後の最初の件
        if k == len(firsts):
            classes[number] = (CLASS_TRAIL, None)
        elif k == 0:
            classes[number] = (CLASS_PRE, 0)
        else:
            classes[number] = (CLASS_GAP, k) if number > reach_before[k] else (CLASS_SPAN, k)
    return classes


# --- T1 ---------------------------------------------------------------------------------------------


def gap_price_qty_lines(
    sorted_items: Sequence[Mapping], lines: Sequence[str], classes: Mapping[int, tuple[str, int | None]] | None = None,
) -> list[int]:
    """T1：gap の行（pre は含めない）のうち、どの件の price_line でもなく、式 F2_price_and_qty に当たる行番号。

    classes は classify_lines の結果（渡せば再計算しない。T1 と T2 で1投稿1回だけ計算するため）。
    """
    price_lines = {it["price_line"] for it in sorted_items if isinstance(it.get("price_line"), int)}
    classes = classes if classes is not None else classify_lines(sorted_items, lines)
    return [
        number for number, (kind, _k) in sorted(classes.items())
        if kind == CLASS_GAP and number not in price_lines and _price_and_qty_shaped(lines[number - 1])
    ]


# --- T2 / H2 ----------------------------------------------------------------------------------------


def _has_value(value: object) -> bool:
    return value is not None and str(value).strip() != "" and str(value).strip().lower() not in _NO_VALUES


def _is_target(item: Mapping) -> bool:
    """価格・数量の写しがあり、商品がまだ決まっていない（unmatched）件。"""
    return (
        _has_value(item.get("raw_price")) and _has_value(item.get("raw_quantity"))
        and item.get("match_status") == _STATUS_UNMATCHED
    )


def _candidates(match_result) -> frozenset[int]:
    """照合結果 → 候補の商品 id（matched は1つ・ambiguous は複数・他は空）。"""
    if match_result.status == _STATUS_MATCHED:
        return frozenset([int(match_result.product_id)])
    if match_result.status == _STATUS_AMBIGUOUS:
        return frozenset(int(c) for c in match_result.candidates)
    return frozenset()


def _group_lines(classes: Mapping[int, tuple[str, int | None]]) -> dict[int, list[int]]:
    """gap・pre の行を、直後の件の位置ごとにまとめる。"""
    groups: dict[int, list[int]] = defaultdict(list)
    for number, (kind, k) in sorted(classes.items()):
        if kind in (CLASS_GAP, CLASS_PRE) and k is not None:
            groups[k].append(number)
    return dict(groups)


def _is_support_line(text: str, product_first: ProductFirstMasters) -> bool:
    """その行1行だけを照合して、matched でも ambiguous でもない行（見出しだけで当たる行は支えにしない）。"""
    result = match_text_g2(product_match_text(text, "", None)[0], product_first)
    return result.status not in (_STATUS_MATCHED, _STATUS_AMBIGUOUS)


def gap_name_candidates(
    sorted_items: Sequence[Mapping], lines: Sequence[str], product_first: ProductFirstMasters,
    classes: Mapping[int, tuple[str, int | None]] | None = None,
) -> list[dict]:
    """T2（規則 H2）：件ごとに {gemini_index, gap_lines, support_lines, candidates}。件は gemini_index で示す。

    gap・pre の行のまとまりの効く範囲は、直後の件から次のまとまりの直前の件まで。範囲の件のうち、
    価格と数量の写しがあり unmatched の件だけが対象。支えの行ごとに「支えの行＋件の各行」を照合し、
    候補の和集合を candidates にする（空なら候補なし）。support_lines は候補を出した支えの行。
    gap_lines はその件に効くまとまりの間の行すべて（支えに使わなかった行も含む。候補なしでも行番号が残る）。
    """
    groups = _group_lines(classes if classes is not None else classify_lines(sorted_items, lines))
    starts = sorted(groups)
    results: list[dict] = []
    for position, start in enumerate(starts):
        end = starts[position + 1] if position + 1 < len(starts) else len(sorted_items)
        targets = [item for item in sorted_items[start:end] if _is_target(item)]
        if not targets:
            continue  # 対象の件が無いまとまりでは、支えの行を照合しない
        support = [n for n in groups[start] if _is_support_line(lines[n - 1], product_first)]  # まとまりごとに1回
        for item in targets:
            block = [lines[n - 1] for n in item["lines"]]
            per_line = {
                n: _candidates(match_text_g2(product_match_text("\n".join([lines[n - 1], *block]), "", item.get("name"))[0], product_first))
                for n in support
            }
            union = frozenset().union(*per_line.values()) if per_line else frozenset()
            results.append({
                "gemini_index": item.get("gemini_index"),
                "gap_lines": list(groups[start]),
                "support_lines": [n for n, found in per_line.items() if found],
                "candidates": sorted(union),
            })
    return results


# --- 書く値 -----------------------------------------------------------------------------------------


def _post_review_lines(post_review: Sequence[Mapping]) -> list[dict]:
    """post_review のうち line を持つ要素の写し（kind と line だけ。原文・エラー文は入れない）。"""
    return [
        {"kind": element.get("kind"), "line": element["line"]}
        for element in post_review
        if isinstance(element, Mapping) and isinstance(element.get("line"), int) and not isinstance(element["line"], bool)
    ]


def build_gap_detail(
    items: Sequence[Mapping], lines: Sequence[str], product_first: ProductFirstMasters | None, post_review: Sequence[Mapping],
) -> dict:
    """run_v102_pipeline の v102_gap_detail。件は gemini_index で示す（保存前に to_stored_detail で item の id に置き換える）。

    product_first が None（商品のマスタが無い）のときは商品を照合できないので、gap_name は空にする。
    """
    ordered = accepted_items(items)
    classes = classify_lines(ordered, lines)  # 1投稿で1回だけ。T1 と T2 で使い回す
    return {
        "post_review": _post_review_lines(post_review),
        "gap_price_qty": [{"line": n} for n in gap_price_qty_lines(ordered, lines, classes)],
        "gap_name": gap_name_candidates(ordered, lines, product_first, classes) if product_first is not None else [],
    }


def to_stored_detail(detail: Mapping, item_id_by_index: Mapping[int, str]) -> dict:
    """extraction_jobs.system_review_detail に書く値（版 1）。対応が付かない件は書かず、その数を unmapped に入れる。"""
    mapped: list[dict] = []
    unmapped = 0
    for entry in detail["gap_name"]:
        item_id = item_id_by_index.get(entry["gemini_index"])
        if item_id is None:
            unmapped += 1
            continue
        mapped.append({
            "extraction_item_id": str(item_id), "gap_lines": list(entry["gap_lines"]),
            "support_lines": list(entry["support_lines"]),
            "candidates": list(entry["candidates"]),
        })
    return {
        "v": DETAIL_VERSION,
        "post_review": list(detail["post_review"]),
        "gap_price_qty": list(detail["gap_price_qty"]),
        "gap_name": mapped,
        "unmapped": unmapped,
    }


def gap_suspects_by_item(stored: object) -> dict[str, dict]:
    """extraction_jobs.system_review_detail（版 1）→ {extraction_item_id: {"gap_lines": [int], "candidates": [int]}}。

    記録の形を読むのはこの関数だけ（SSOT）。None・版違い・形違い・JSON でない文字列は空の辞書。
    JSONB が文字列で返る場合（asyncpg + text()）はここで JSON として読む。
    """
    if isinstance(stored, str):
        try:
            stored = json.loads(stored)
        except json.JSONDecodeError:
            return {}
    if not isinstance(stored, Mapping) or stored.get("v") != DETAIL_VERSION:
        return {}
    entries = stored.get("gap_name")
    if not isinstance(entries, list):
        return {}
    result: dict[str, dict] = {}
    for entry in entries:
        if not isinstance(entry, Mapping):
            continue
        item_id, gap_lines, candidates = entry.get("extraction_item_id"), entry.get("gap_lines"), entry.get("candidates")
        if not isinstance(item_id, str) or not _is_int_list(gap_lines) or not _is_int_list(candidates):
            continue
        result[item_id] = {"gap_lines": list(gap_lines), "candidates": list(candidates)}
    return result


def _is_int_list(value: object) -> bool:
    return isinstance(value, list) and all(isinstance(n, int) and not isinstance(n, bool) for n in value)
