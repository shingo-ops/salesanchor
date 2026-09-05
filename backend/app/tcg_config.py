"""
TCG スキーマ設定。

TCG_SCHEMA 環境変数からスキーマ名を読み取る。
未設定の場合は "tenant_004" を既定値として使用する。

値の検証: tenant_NNN 形式（数字3桁）のみ受け付ける。
  任意の文字列を受け入れると SQL 文字列に直接埋め込まれるため
  インジェクションリスクがある。

使用例:
    from app.tcg_config import TCG_SCHEMA
    sql = f"SELECT * FROM {TCG_SCHEMA}.tcg_suppliers"
"""
from __future__ import annotations

import os
import re

_RAW: str = os.getenv("TCG_SCHEMA", "tenant_004")
_VALID = re.compile(r"^tenant_\d{3}$")

if not _VALID.match(_RAW):
    raise RuntimeError(
        f"TCG_SCHEMA='{_RAW}' は無効です。"
        f"'tenant_NNN'（数字3桁）形式でなければなりません（例: tenant_004）。"
    )

TCG_SCHEMA: str = _RAW
