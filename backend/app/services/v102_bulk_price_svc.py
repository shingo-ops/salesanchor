"""バルク系の価格を「1枚の値段」にそろえる規則（g28 便2。ADR-1021）。純関数。DB・ファイルは読まない。

投稿者の価格は「1枚の値段」の場合と「1セット（N枚）の値段」の場合がある。原文ブロックの書き方から
次のどれかに決める。迷ったら review（値は変えず、要確認にする）。

- piece : 価格は1枚の値段。価格・数量はそのまま。
- set   : 価格は1セット（N枚）の値段。単価 = 価格 ÷ N、数量 = 数量 × N、備考に「N枚セット単位（1セットX円）」。
- review: 決まらない。

規則の正本は検証用の rule.py（リポジトリ外・md5 336a8dbf）。analyze / qty_unit / price_numbers と本体の判定順を
挙動を変えずに移してある。規則を変えるときは先に設計（ADR-1021）を直す。
"""
from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass

DECISION_PIECE = "piece"
DECISION_SET = "set"
DECISION_REVIEW = "review"

_NUM = r"([0-9][0-9,]*)"
_AT = r"[@＠]"
# 被り(無|な)し の語（セットの大きさの印の一部）
_NODUP = r"被り?(?:無|な)し|被りなし|被り無"


@dataclass(frozen=True)
class BulkPrice:
    """判定の結果。review のとき unit_price / quantity / note は None（n は価格の確認で落ちた行にだけ判定した N が残る）。piece のとき n / note は None で、価格・数量は入力のまま。"""

    decision: str
    n: int | None
    unit_price: int | float | None
    quantity: int | float | None
    note: str | None
    reason: str


def _toint(s: str) -> int:
    return int(s.replace(",", ""))


def _rnd(x: float) -> int:
    return int(math.floor(x + 0.5))


def _analyze(t: str) -> tuple[str, int | str, str]:
    """戻り値: (判定, N, 理由)。迷ったら review。N は set のときだけ整数。"""
    t = t.replace("⏎", "\n")
    # --- セットの大きさの印: 「N枚」+ セット/バルク/被りなし が直後に付く形 ---
    set_sizes = set()
    for m in re.finditer(_NUM + r"枚\s*[（(]?\s*(?:セット|バルク|" + _NODUP + r")", t):
        set_sizes.add(_toint(m.group(1)))
    # 注: 「被りなし50枚」(語が前) は「50枚まで」等の在庫上限の意味もあるため、大きさの印にしない
    for m in re.finditer(r"バルク\s*" + _NUM + r"枚", t):
        set_sizes.add(_toint(m.group(1)))
    set_sizes = {n for n in set_sizes if n >= 2}

    has_set_word = "セット" in t or "束" in t or "まとめ" in t
    has_nodup_word = re.search(_NODUP, t) is not None

    # --- 単価の印 ---
    piece_marks = []
    if re.search(_NUM + r"\s*円?\s*[×x]\s*" + _NUM + r"\s*枚?(?!\s*セット)", t) and not re.search(r"[×x]\s*" + _NUM + r"\s*セット", t):
        piece_marks.append("X×N")
    if re.search(_NUM + r"枚\s*[@＠、,]\s*" + _NUM, t):
        piece_marks.append("N枚@X")
    if re.search(r"円\s*[/／]\s*枚", t):
        piece_marks.append("円/枚")
    if re.search(r"(?<![0-9,])1枚\s*[/／@＠]?\s*(?:¥\s*" + _NUM + r"|" + _NUM + r"\s*円)", t):
        piece_marks.append("1枚X円")
    stock = re.findall(_AT + r"\s*" + _NUM + r"\s*円?\s*[/／]?\s*在庫(?:数)?\s*" + _NUM + r"\s*(枚|セット|個)?", t)
    # 数字だけ(単位なし)の「在庫 N」は枚数かセット数か決まらないため単価の印にしない
    stock_piece = [s for s in stock if s[2] == "枚"]
    stock_bare = [s for s in stock if s[2] == ""]

    # --- 読み方が衝突する形 ---
    # 「X円/N枚」(N>=2): N枚が在庫数かセットの大きさか2通り
    ambiguous_per = any(_toint(x) >= 2 for x in re.findall(r"円\s*[/／]\s*" + _NUM + r"枚", t))
    # 在庫語(枚) と セット語が同居: 在庫の単位が不明
    stock_pieces_unit = re.search(r"(?:在庫|残り?)(?:数)?\s*[0-9][0-9,]*\s*枚", t) is not None

    if ambiguous_per:
        return DECISION_REVIEW, "", "R_X円/N枚_2way"
    if len(set_sizes) > 1:
        return DECISION_REVIEW, "", "R_multiple_set_sizes"

    strong_piece = bool(piece_marks)
    stock_mark = bool(stock_piece)

    if set_sizes:
        n = next(iter(set_sizes))
        if strong_piece or stock_mark:
            return DECISION_REVIEW, "", "R_set_size_and_piece_mark"
        if stock_pieces_unit:
            return DECISION_REVIEW, "", "R_set_size_and_stock_in_枚"
        return DECISION_SET, n, "set_size_mark"
    if stock_bare and not strong_piece:
        return DECISION_REVIEW, "", "R_stock_bare_number_unit_unknown"
    if strong_piece or stock_mark:
        if has_set_word:
            return DECISION_REVIEW, "", "R_piece_mark_and_set_word"
        if has_nodup_word:
            return DECISION_REVIEW, "", "R_piece_mark_and_nodup_word"
        return DECISION_PIECE, "", "piece_mark"
    return DECISION_REVIEW, "", "R_no_clear_mark"


def _qty_unit(t: str, qty: float) -> tuple[str, str]:
    """数量の単位を原文の語で決める。戻り値: ('piece'|'set'|'unknown', 理由)。
    セットの大きさの印(N枚セット / N枚バルク / バルクN枚)は数量ではないので除く。"""
    q = int(round(qty))
    units = set()
    for m in re.finditer(r"(?<![0-9,.])" + _NUM + r"\s*(枚|セット|個)", t):
        if _toint(m.group(1)) != q:
            continue
        u = m.group(2)
        # 価格の単位を示す「1+単位語」(1セット/¥X, 1枚@X, 1セット X円, X円/1枚)は数量の根拠にしない
        if _toint(m.group(1)) == 1:
            after = t[m.end():m.end() + 12]
            before = t[max(0, m.start() - 4):m.start()]
            if re.match(r"\s*(?:[/／@＠]|[¥￥]|[0-9][0-9,]*\s*円)", after) or re.search(r"円\s*[/／@＠]\s*$", before):
                continue
        if u == "枚":
            after = t[m.end():m.end() + 6]
            before = t[max(0, m.start() - 4):m.start()]
            if re.match(r"\s*[（(]?\s*(?:セット|バルク|" + _NODUP + r")", after) or re.search(r"バルク\s*$", before):
                continue
        units.add(u)
    if units == {"枚"}:
        return "piece", "qty_unit_枚"
    if units == {"セット"}:
        return "set", "qty_unit_セット"
    if not units:
        return "unknown", "R_qty_unit_not_found"
    return "unknown", "R_qty_unit_mixed"


def _price_numbers(t: str) -> set[int]:
    """価格らしい数字の集合(>=10)。ラベル(PSA10, AR230)や枚数・在庫は除外。"""
    t = t.replace("⏎", "\n")
    res = set()
    for m in re.finditer(r"(?<![A-Za-z0-9,.])" + _NUM + r"(?![0-9])(?!\s*(?:枚|種|セット|個|名|点))", t):
        pre = t[max(0, m.start() - 4):m.start()]
        if re.search(r"(?:在庫|在庫数|残り|残)\s*$", pre):
            continue
        n = _toint(m.group(1))
        if n >= 10:
            res.add(n)
    return res


def _review(reason: str, n: int | str = "") -> BulkPrice:
    """review の結果。n は規則の正本と同じく、価格の確認で落ちた行には判定した N を残す（値としては使わない）。"""
    return BulkPrice(DECISION_REVIEW, int(n) if n != "" else None, None, None, None, reason)


def convert(block: str, price: float | None, qty: float | None) -> BulkPrice:
    """原文ブロック（行は改行でつなぐ）と、解析が読んだ価格・数量から、1枚単価への換算を決める。

    block は NFKC に正規化してから判定する（正規化済みを渡しても同じ）。
    """
    t = unicodedata.normalize("NFKC", block or "")
    dec, n, reason = _analyze(t)
    if dec == DECISION_REVIEW:
        return _review(reason)
    # 価格が1つに定まり、DBの価格と一致することを確認。そうでなければ要確認。
    pn = _price_numbers(t)
    if price is None or price <= 0 or qty is None:
        return _review("R_price_or_qty_missing", n)
    if len(pn) != 1:
        return _review("R_price_numbers_%d" % len(pn), n)
    if next(iter(pn)) != int(round(price)):
        return _review("R_price_mismatch", n)
    qu, qreason = _qty_unit(t, qty)
    if dec == DECISION_PIECE and qu != "piece":
        return _review("R_piece_" + qreason)
    if dec == DECISION_SET and qu != "set":
        return _review("R_set_" + qreason)
    if dec == DECISION_PIECE:
        return BulkPrice(DECISION_PIECE, None, price, qty, None, reason)
    size = int(n)
    if abs(price / size - round(price / size)) > 1e-9:
        return _review("R_set_price_not_divisible")
    note = f"{size}枚セット単位（1セット{_rnd(price):,}円）"
    return BulkPrice(DECISION_SET, size, _rnd(price / size), _rnd(qty * size), note, reason)
