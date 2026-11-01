"""アプリの出どころの確認（auth.py と管理者の口の両方が読む）。ADR-1013・ADR-1055。"""

from __future__ import annotations

from fastapi import HTTPException, Request

from app.auth import self_tokens


def require_app_origin(request: Request) -> None:
    """Origin がアプリの出どころ（AUTH_RP_ORIGIN）と違えば 403。状態を変える口だけで呼ぶ（GET では呼ばない）。"""
    if request.headers.get("origin") != self_tokens.rp_origin():
        raise HTTPException(status_code=403, detail="forbidden_origin")
