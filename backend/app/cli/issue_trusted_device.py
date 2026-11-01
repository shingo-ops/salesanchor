"""点検専用の人などに、いつもの機械の印を1つ発行する（ADR-1055 D12）。

使い方: python -m app.cli.issue_trusted_device --user-id <id> --label prod-ui-check

印の生の値を標準出力に1行だけ出す（ログには出さない）。GitHub の秘密 SMOKE_E2E_DEVICE_TOKEN へ
画面に出さずに直接流す（値は記録しない）。DB には sha256 だけを置く（created_via='cli'）。
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import secrets
import sys

from sqlalchemy import text

from app.database import AsyncSessionLocal


async def issue(user_id: int, label: str) -> str:
    raw = secrets.token_urlsafe(32)
    async with AsyncSessionLocal() as db:
        exists = (
            await db.execute(text("SELECT 1 FROM public.users WHERE id = :id AND is_active"), {"id": user_id})
        ).first()
        if exists is None:
            raise SystemExit("user not found or inactive")
        await db.execute(
            text(
                "INSERT INTO public.user_trusted_devices (user_id, token_hash, label, created_via, created_at, last_used_at) "
                "VALUES (:uid, :h, :label, 'cli', now(), now())"
            ),
            {"uid": user_id, "h": hashlib.sha256(raw.encode()).digest(), "label": label[:100]},
        )
        await db.commit()
    return raw


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="いつもの機械の印を1つ発行する")
    parser.add_argument("--user-id", type=int, required=True)
    parser.add_argument("--label", default="cli", help="機械の呼び名")
    args = parser.parse_args(argv)
    raw = asyncio.run(issue(args.user_id, args.label))
    sys.stdout.write(raw + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
