"""閲覧者の申込コードの正規化とハッシュ（ADR-1019 段4c）。

コードを作る関数（申込 API が使う）と、Discord の受付が照合に使う正規化・ハッシュを置く。
"""
from __future__ import annotations

import hashlib
import re
import secrets

# Crockford base32（0-9 と A-Z から I・L・O・U を除く）16文字
SIGNUP_CODE_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_CODE_RE = re.compile(r"^[0-9A-HJKMNP-TV-Z]{16}$")


def normalize_signup_code(raw: str) -> str | None:
    """大文字にしてハイフン・空白を除く。16文字の Crockford base32 でなければ None。"""
    if not isinstance(raw, str):
        return None
    cleaned = "".join(raw.upper().replace("-", "").split())
    return cleaned if _CODE_RE.match(cleaned) else None


def signup_code_sha256(normalized: str) -> bytes:
    return hashlib.sha256(normalized.encode("ascii")).digest()


def generate_signup_code() -> str:
    """申込コードを作る。正規化済みの形（大文字・ハイフンなし・16文字・80ビット）。"""
    return "".join(secrets.choice(SIGNUP_CODE_ALPHABET) for _ in range(16))


def format_signup_code(normalized: str) -> str:
    """画面に出す形。4文字ずつハイフンで区切る。"""
    return "-".join(normalized[i : i + 4] for i in range(0, len(normalized), 4))
