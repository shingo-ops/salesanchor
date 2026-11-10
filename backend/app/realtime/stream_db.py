"""流し続ける口（SSE）の認証用の短い DB セッション（ADR-1016 追記）。

yield 依存の get_db は流れを送り終えるまで閉じないので、流し続ける口では依存にしない。
認証はこの入口で開いたセッションで済ませ、流し始める前に閉じる。後始末は get_db と同じ。
"""
from contextlib import asynccontextmanager

from app.database import get_db


def short_db_scope():
    return asynccontextmanager(get_db)()
