"""
キーワード品質検査（R1〜R7）。

設計: docs/handoff/tcg-keyword-quality/design.md
recon: docs/handoff/tcg-keyword-quality/recon.md
対象ADR: ADR-154（照合ロジックは変えない。既存の純関数を呼ぶだけ）

DB 接続不要。入力は load_product_keywords が返すのと同じ辞書2つと、
有効商品コードの集合。照合は tcg_analyzer_svc の既存関数を import して使う。
"""
from __future__ import annotations

import re
from typing import Iterable

from app.services.tcg_analyzer_svc import (
    collapse_product_spaces,
    match_one_kw,
    match_product_name_space,
    normalize_en,
)

# 純ASCII語（英数記号のみ）の判定。日本語混じりはこれに当たらない。
_RE_PURE_ASCII = re.compile(r"^[\x20-\x7e]+$")

# 判定の区分
STOP = "STOP"
WARN = "WARN"
INFO = "INFO"


def _tokens(kw: str) -> list[str]:
    """空白で分割したトークン（token_and_match と同じ切り方）。"""
    return [t for t in re.split(r"\s+", normalize_en(kw)) if t]


def _is_ascii_kw(kw: str) -> bool:
    return bool(_RE_PURE_ASCII.match(kw))


def check_r1_empty_search(active_codes: Iterable[str], search_kw: dict) -> list[str]:
    """R1: 有効商品に検索語が1つも無い。"""
    return sorted(c for c in active_codes if not search_kw.get(c))


def check_r2_short_tokens(search_kw: dict) -> tuple[list[str], list[str]]:
    """R2: 日本語混じり語のトークン長。(1文字=停止, 2文字=警告) を返す。"""
    stop: list[str] = []
    warn: list[str] = []
    for code in sorted(search_kw):
        for kw in search_kw[code]:
            if _is_ascii_kw(kw):
                continue
            for t in _tokens(kw):
                if len(t) == 1:
                    stop.append(f"{code}:{kw}")
                elif len(t) == 2:
                    warn.append(f"{code}:{kw}")
    return stop, warn


def check_r3_shared_kw(search_kw: dict) -> list[str]:
    """R3: 同じ語（正規化後）が2商品以上に登録されている。"""
    owners: dict[str, set[str]] = {}
    for code, kws in search_kw.items():
        for kw in kws:
            owners.setdefault(collapse_product_spaces(normalize_en(kw)), set()).add(code)
    return sorted(
        f"{k} -> {','.join(sorted(v))}" for k, v in owners.items() if len(v) > 1
    )


def check_r4_self_kill(search_kw: dict, exclude_kw: dict) -> list[str]:
    """R4: 除外語が自商品の検索語に当たる（自分で自分を消している）。"""
    out: list[str] = []
    for code in sorted(exclude_kw):
        for ex in exclude_kw[code]:
            for sk in search_kw.get(code, []):
                if match_one_kw(collapse_product_spaces(ex), collapse_product_spaces(normalize_en(sk))):
                    out.append(f"{code}: '{ex}' kills '{sk}'")
    return out


def check_r5_piggyback(search_kw: dict, exclude_kw: dict) -> list[str]:
    """R5: Aの語がBの語に当たり、Aの除外語がBのその語に当たらない（相乗り）。"""
    out: list[str] = []
    for a_code in sorted(search_kw):
        for a_kw in search_kw[a_code]:
            for b_code in sorted(search_kw):
                if b_code == a_code:
                    continue
                for b_kw in search_kw[b_code]:
                    if collapse_product_spaces(normalize_en(a_kw)) == collapse_product_spaces(normalize_en(b_kw)):
                        continue
                    b_norm = normalize_en(b_kw)
                    if not (match_one_kw(collapse_product_spaces(a_kw), collapse_product_spaces(b_norm))
                            or match_product_name_space(a_kw, b_norm)):
                        continue
                    guarded = any(
                        match_one_kw(collapse_product_spaces(ex), collapse_product_spaces(b_norm)) for ex in exclude_kw.get(a_code, [])
                    )
                    if not guarded:
                        out.append(f"{a_code}:'{a_kw}' rides {b_code}:'{b_kw}'")
    return out


def check_r6_dup_in_product(search_kw: dict) -> list[str]:
    """R6: 同一商品内で正規化後に同じ語が2つ以上。"""
    out: list[str] = []
    for code in sorted(search_kw):
        seen: dict[str, str] = {}
        for kw in search_kw[code]:
            n = collapse_product_spaces(normalize_en(kw))
            if n in seen:
                out.append(f"{code}: '{seen[n]}' / '{kw}'")
            else:
                seen[n] = kw
    return out


def check_r7_spaced_ja(search_kw: dict) -> list[str]:
    """R7: 空白を含む日本語混じり語（AND 分解される・情報）。"""
    return sorted(
        f"{code}:{kw}"
        for code in search_kw
        for kw in search_kw[code]
        if not _is_ascii_kw(kw) and len(_tokens(kw)) > 1
    )


def run_all(active_codes: Iterable[str], search_kw: dict, exclude_kw: dict) -> dict:
    """全規則を実行し、{規則: (区分, 件数, 一覧)} と終了コードを返す。"""
    codes = list(active_codes)
    r2_stop, r2_warn = check_r2_short_tokens(search_kw)
    findings = {
        "R1": (STOP, check_r1_empty_search(codes, search_kw)),
        "R2-stop": (STOP, r2_stop),
        "R2-warn": (WARN, r2_warn),
        "R3": (STOP, check_r3_shared_kw(search_kw)),
        "R4": (STOP, check_r4_self_kill(search_kw, exclude_kw)),
        "R5": (WARN, check_r5_piggyback(search_kw, exclude_kw)),
        "R6": (STOP, check_r6_dup_in_product(search_kw)),
        "R7": (INFO, check_r7_spaced_ja(search_kw)),
    }
    stop_rules = [k for k, (lvl, items) in findings.items() if lvl == STOP and items]
    return {"findings": findings, "stop_rules": stop_rules, "exit_code": 1 if stop_rules else 0}
