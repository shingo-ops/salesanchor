"""GET・HEAD の口は出どころ（Origin）の確認を呼ばない。

ブラウザは同じサイトあての GET・HEAD に Origin を付けないので、確認を付けると本物のブラウザから
必ず 403 になる（パスキー案内の口で実際に起きた）。新しい GET の口が確認を付けた時点で赤になる。
"""
from __future__ import annotations

import inspect

from fastapi.routing import APIRoute


def test_get_and_head_routes_do_not_check_origin():
    # 遅延 import: 収集時に app.main を読むと conftest の権限モックより前に束縛されるため
    from app.main import app

    violations = []
    for r in app.routes:
        if not isinstance(r, APIRoute):
            continue
        for m in sorted(r.methods & {"GET", "HEAD"}):
            src = inspect.getsource(r.endpoint)
            if "_require_app_origin(" in src or 'headers.get("origin")' in src:
                violations.append((m, r.path))
    assert not violations, f"GET/HEAD の口が Origin を確認している: {violations}"
