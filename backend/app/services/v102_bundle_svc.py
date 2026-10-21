"""まとめ売り（N単位セット）の読み取り（純関数・ADR-1027）。

仕入元の本文に「40パックセット」のように書かれた「まとめの数 N」を、原文ブロックから読む。
形は「数 N（1〜5桁）＋単位の語＋まとめの語」だけ。バルク系の行だけ（引数 bulk_shapes）、「まとめの語＋(N＋単位の語)」と、本文に数量の直後のセットがあるときの「まとめの語＋N＋単位の語」も見る（design.md §12）。単位の語は単位の別名マスタから作る（このファイルに単位の語を書かない）。
canonical が Set の別名は単位の語に使わない（「16セット」は16単位のまとめではない）。Set の別名は
「数量の直後に『セット』があるか」の判定にだけ使う。
設計: docs/handoff/bundle-sale/design.md §5-2。判定の参照台本: scripts/dev/bundle_replay.py（このファイルの detect_bundle を import する）。
"""
from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import Decimal
from functools import lru_cache

SET_CANONICAL = "Set"  # 単位マスタで「セット」を表す canonical。この単位の別名は単位の語に使わない
KIND_DECIDED = "decided"  # 決まった（bundle_size=N、単位＝中身の単位）
KIND_UNVERIFIED = "unverified"  # 決まらない（理由 bundle_unverified。値は変えない）

# まとめの語（設計 §5-2 の 3。唯一の置き場所）
BUNDLE_WORDS: tuple[str, ...] = (
    "まとめ売り", "セット", "set", "まとめ", "束", "組", "バルク", "bulk", "被りなし", "被り無し", "かぶりなし", "ランダム",
)

_MAX_DIGITS = 5
_SP = r"[^\S\n]"  # 改行を越えない空白（語の間は同じ行の中だけ）
_AFTER_EXCLUDED = "入"  # 「N単位入」のような中身の説明はまとめではない


@dataclass(frozen=True)
class BundleResult:
    kind: str  # KIND_DECIDED | KIND_UNVERIFIED
    n: int | None  # まとめの数。複数の (N, 単位) が当たって決まらないときは None
    unit: str | None  # 中身の単位の canonical。同上
    reason: str  # 決まらない理由（記録・台本用。保存はしない）


def normalize(text: str) -> str:
    """NFKC・小文字化し、数字に挟まれたカンマを除く。"""
    out = unicodedata.normalize("NFKC", text or "").lower()
    return re.sub(r"(?<=\d),(?=\d)", "", out)


def split_unit_words(alias_to_canonical: Mapping[str, str]) -> tuple[dict[str, str], frozenset[str]]:
    """別名 → canonical を「単位の語（Set を除く）」と「Set の語」に分ける。語は正規化済み。

    同じ語が別の canonical に引かれるときは単位の語から外す（どちらか決められない）。
    """
    words: dict[str, str] = {}
    conflict: set[str] = set()
    set_words: set[str] = set()
    for alias, canonical in alias_to_canonical.items():
        word = normalize(alias).strip()
        if not word:
            continue
        if canonical == SET_CANONICAL:
            set_words.add(word)
            continue
        if word in words and words[word] != canonical:
            conflict.add(word)
        words[word] = canonical
    for word in conflict:
        words.pop(word, None)
    return words, frozenset(set_words)


def _alternations(word_to_canonical: Mapping[str, str]) -> tuple[str, str]:
    """単位の語・まとめの語の正規表現の選択肢（`_patterns` と `_bulk_patterns` で同じ式を使う）。"""
    unit_part = "|".join(re.escape(w) for w in sorted(word_to_canonical, key=len, reverse=True))
    bundle_part = "|".join(re.escape(normalize(w)) for w in sorted(BUNDLE_WORDS, key=lambda w: len(normalize(w)), reverse=True))
    return unit_part, bundle_part


@lru_cache(maxsize=8)
def _patterns(words: tuple[tuple[str, str], ...]) -> tuple[re.Pattern[str] | None, dict[str, str]]:
    word_to_canonical = dict(words)
    if not word_to_canonical:
        return None, word_to_canonical
    unit_part, bundle_part = _alternations(word_to_canonical)
    pattern = re.compile(rf"(?<!\d)(\d{{1,{_MAX_DIGITS}}}){_SP}*({unit_part}){_SP}*({bundle_part})")
    return pattern, word_to_canonical


@lru_cache(maxsize=8)
def _bulk_patterns(words: tuple[tuple[str, str], ...]) -> tuple[re.Pattern[str], re.Pattern[str]] | None:
    """バルク系だけの形。P1: まとめの語＋(N＋単位の語)。P2: まとめの語＋N＋単位の語（設計 §12-3）。"""
    word_to_canonical = dict(words)
    if not word_to_canonical:
        return None
    unit_part, bundle_part = _alternations(word_to_canonical)
    p1 = re.compile(rf"({bundle_part}){_SP}*\((\d{{1,{_MAX_DIGITS}}}){_SP}*({unit_part})\)")
    p2 = re.compile(rf"({bundle_part}){_SP}*(?<!\d)(\d{{1,{_MAX_DIGITS}}}){_SP}*({unit_part})")
    return p1, p2


def _strip_parens(block: str) -> str:
    """括弧 () の中を空白にする。閉じない括弧は、その行（改行まで）の終わりまでを中とみなす。"""
    out: list[str] = []
    for line in block.split("\n"):
        previous = None
        while previous != line:
            previous = line
            line = re.sub(r"\([^()]*\)", " ", line)
        out.append(re.sub(r"\(.*$", " ", line))
    return "\n".join(out)


def _find_candidates(text: str, pattern: re.Pattern[str], word_to_canonical: Mapping[str, str]) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    for m in pattern.finditer(text):
        if text[m.end():m.end() + 1] == _AFTER_EXCLUDED:
            continue
        n = int(m.group(1))
        if n < 2:
            continue
        found.append((n, word_to_canonical[m.group(2)]))
    return found


def _bulk_matches(text: str, pattern: re.Pattern[str], word_to_canonical: Mapping[str, str]) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    for m in pattern.finditer(text):
        if text[m.end():m.end() + 1] == _AFTER_EXCLUDED:
            continue
        n = int(m.group(2))
        if n < 2:
            continue
        found.append((n, word_to_canonical[m.group(3)]))
    return found


def _find_bulk_candidates(
    full: str, word_to_canonical: Mapping[str, str], set_words: Iterable[str], quantity: object,
) -> list[tuple[int, str]]:
    """バルク系だけの追加の形（P1・P2）の候補。P1 は括弧を除く前の本文に、P2 は括弧を除いた本文に当てる。"""
    patterns = _bulk_patterns(tuple(sorted(word_to_canonical.items())))
    if patterns is None:
        return []
    p1, p2 = patterns
    found = _bulk_matches(full, p1, word_to_canonical)  # P1 は数量に関係なく当てる
    if quantity is None or (isinstance(quantity, str) and not quantity.strip()):
        return found
    q = Decimal(str(quantity))
    if q == q.to_integral_value() and _has_set_after_quantity(full, int(q), set_words):
        found += _bulk_matches(_strip_parens(full), p2, word_to_canonical)
    return found


def _has_set_after_quantity(full: str, quantity: int, set_words: Iterable[str]) -> bool:
    words = sorted(set_words, key=len, reverse=True)
    if not words:
        return False
    alternatives = "|".join(re.escape(w) for w in words)
    return re.search(rf"(?<![\d.]){quantity}(?!\d|\.\d){_SP}*(?:{alternatives})", full) is not None


def detect_bundle(
    block: str,
    alias_to_canonical: Mapping[str, str],
    set_words: Iterable[str],
    price: object,
    quantity: object,
    bulk_shapes: bool = False,
) -> BundleResult | None:
    """原文ブロックからまとめ売りを読む。当たりなしは None。

    alias_to_canonical は split_unit_words が返した単位の語（Set を除く・正規化済み）、
    set_words は Set の語（同上）。price・quantity は Gemini の読み（換算前の数量）。
    """
    pattern, word_to_canonical = _patterns(tuple(sorted(alias_to_canonical.items())))
    if pattern is None:
        return None
    full = normalize(block)
    found = _find_candidates(_strip_parens(full), pattern, word_to_canonical)
    if bulk_shapes:  # バルク系だけ（設計 bundle-sale §12: P1・P2）
        found += _find_bulk_candidates(full, word_to_canonical, set_words, quantity)
    if not found:
        return None
    distinct = sorted(set(found))
    if len(distinct) >= 2:
        return BundleResult(KIND_UNVERIFIED, None, None, "違う(N,単位)が%d種" % len(distinct))
    n, unit = distinct[0]
    if price is None or (isinstance(price, str) and not price.strip()):
        return BundleResult(KIND_UNVERIFIED, n, unit, "値段なし")
    if quantity is not None and not (isinstance(quantity, str) and not quantity.strip()):
        q = Decimal(str(quantity))
        if q == q.to_integral_value():
            qi = int(q)
            if qi % n == 0 and not _has_set_after_quantity(full, qi, set_words):
                return BundleResult(KIND_UNVERIFIED, n, unit, "数量が割り切れ・数量直後にセット無し")
    return BundleResult(KIND_DECIDED, n, unit, "")
