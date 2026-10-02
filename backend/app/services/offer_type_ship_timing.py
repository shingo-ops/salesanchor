"""行テキストから (offer_type, ship_timing) を推定する純粋関数（ADR-093 Phase 3b）。

2026-10-02: Discord 在庫取り込み機能（inventory_parser.py）削除に伴い、
extraction_judgement_svc.py が使う `extract_offer_type_ship_timing` を
独立モジュールへ移設した。経緯: docs/handoff/remove-discord-inventory-parse/design.md
"""

from __future__ import annotations

import re

# 予約キーワード（在庫はデフォルト=区分なし）。
OFFER_TYPE_REGEXES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"予\s*約|ご予約|preorder|pre-?order|発売前|入荷前", re.IGNORECASE), "pre_order"),
]
# 発送日（予約品）。順序重要: 「2日前」を「1日前」より先に判定。
SHIP_TIMING_REGEXES: list[tuple[re.Pattern[str], str]] = [
    # 数字境界の負の後読みで「発売12日前」の末尾 "2日前" 等の誤判定を防ぐ（Reviewer PR#1445）。
    (re.compile(r"(?:発売)?\s*(?<![0-9０-９])2\s*日\s*前", re.IGNORECASE), "2day_before"),
    (re.compile(r"(?:発売)?\s*(?<![0-9０-９])1\s*日\s*前|前日\s*発送|前日着", re.IGNORECASE), "1day_before"),
    (re.compile(r"発売日\s*(?:発送|当日)?|当日\s*発送|入荷日\s*発送|発売日着", re.IGNORECASE), "on_release"),
]


def extract_offer_type_ship_timing(line: str) -> tuple[str | None, str | None]:
    """行から (offer_type, ship_timing) を推定（ADR-093 Phase 3b）。

    - offer_type: 予約キーワードがあれば 'pre_order'、無ければ None（=在庫 in_stock 扱い）。
    - ship_timing: 発送日キーワードを検出（予約品のみ）。
    - 発送日だけ取れて予約語が無い場合も、発送日指定は予約の特徴なので pre_order とみなす。
    - 予約だが発送日が特定できない場合は 'other'。
    最終判定は admin が ParseReview / オファー画面で修正できる（自動判定はあくまで初期値）。
    """
    offer_type: str | None = None
    for pat, label in OFFER_TYPE_REGEXES:
        if pat.search(line):
            offer_type = label
            break
    ship_timing: str | None = None
    for pat, label in SHIP_TIMING_REGEXES:
        if pat.search(line):
            ship_timing = label
            break
    if ship_timing is not None and offer_type is None:
        offer_type = "pre_order"
    if offer_type == "pre_order" and ship_timing is None:
        ship_timing = "other"
    return offer_type, ship_timing


__all__ = [
    "OFFER_TYPE_REGEXES",
    "SHIP_TIMING_REGEXES",
    "extract_offer_type_ship_timing",
]
