"""閲覧者の申込コードの正規化とハッシュ（ADR-1019 段4c）。

コードを作る関数は段4b で足す。ここでは Discord の受付が照合に使う2つだけ。
"""
from __future__ import annotations

import hashlib
import re

# Crockford base32（0-9 と A-Z から I・L・O・U を除く）16文字
_CODE_RE = re.compile(r"^[0-9A-HJKMNP-TV-Z]{16}$")


def normalize_signup_code(raw: str) -> str | None:
    """大文字にしてハイフン・空白を除く。16文字の Crockford base32 でなければ None。"""
    if not isinstance(raw, str):
        return None
    cleaned = "".join(raw.upper().replace("-", "").split())
    return cleaned if _CODE_RE.match(cleaned) else None


def signup_code_sha256(normalized: str) -> bytes:
    return hashlib.sha256(normalized.encode("ascii")).digest()
