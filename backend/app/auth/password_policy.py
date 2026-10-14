"""パスワードの決まり（ADR-1013 便3・design.md:88-97）。

15〜64 文字（文字数）。よく使われるパスワードの一覧（data/common-passwords.txt）に載るものは拒否。
文字の種類の混在は求めない。
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

MIN_LENGTH = 15
MAX_LENGTH = 64

_COMMON_PATH = Path(__file__).parent / "data" / "common-passwords.txt"


@lru_cache(maxsize=1)
def _common_passwords() -> frozenset[str]:
    """一覧は最初の呼び出しで1回だけ読み、小文字の集合で持つ。"""
    words = (line.strip() for line in _COMMON_PATH.read_text(encoding="utf-8").splitlines())
    return frozenset(w.lower() for w in words if w)


def check_password(plain: str) -> str | None:
    """問題なければ None。だめなら理由のコード（password_too_short／password_too_long／password_too_common）。"""
    if len(plain) < MIN_LENGTH:
        return "password_too_short"
    if len(plain) > MAX_LENGTH:
        return "password_too_long"
    if plain.lower() in _common_passwords():
        return "password_too_common"
    return None
