"""閲覧者のメールアドレスの正規化（ADR-1019 設計 D1）。"""

from __future__ import annotations

from app.schemas.base import validate_email_loose


def normalize_viewer_email(raw: str) -> str:
    """前後の空白を除く → 小文字にする → validate_email_loose に通す。通らなければ ValueError。この順番を変えない。"""
    value = raw.strip().lower()
    checked = validate_email_loose(value)
    if checked is None:
        raise ValueError("メールアドレスの形式が正しくありません")
    return checked
