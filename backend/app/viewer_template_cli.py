"""Claude 用の閲覧者向け文面テンプレートの初期値スクリプト（ADR-1019 段11 便1）。

SQL・コマンドを受け取らない。受け取るのは stdin の JSON だけ:
  {"action":"seed","dry_run":true|false}  viewer_bot_texts.py の今の9定数を、無い行だけ入れる（ある行は触らない）
  {"action":"verify"}                     鍵ごとに exists / matches を true/false で返す（本文・名簿は出さない）
便2 で定数と一緒に消す。
"""
import asyncio
import json
import sys

from sqlalchemy import text

from app.database import AsyncSessionLocal
from app.services import viewer_message_templates as vmt


class ViewerTemplateError(Exception):
    """code: invalid_input | invalid_constant"""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _checked_bodies() -> dict[str, str]:
    bodies = vmt.seed_bodies()
    for key, body in bodies.items():
        try:
            vmt.validate(key, body)
        except vmt.TemplateInvalid:
            raise ViewerTemplateError("invalid_constant") from None
    return bodies


async def _existing(db) -> dict[str, str]:
    rows = (await db.execute(text("SELECT key, body FROM public.viewer_message_templates"))).all()
    return {r[0]: r[1] for r in rows}


async def _seed(payload: dict, session_factory) -> dict:
    dry_run = payload.get("dry_run")
    if not isinstance(dry_run, bool):
        raise ViewerTemplateError("invalid_input")
    bodies = _checked_bodies()  # 通らない定数があれば何も書かずにエラー
    async with session_factory() as db:
        existing = await _existing(db)
        would_insert = [k for k in bodies if k not in existing]
        if dry_run:
            return {"dry_run": True, "would_insert": would_insert}
        inserted: list[str] = []
        for key in would_insert:
            res = await db.execute(
                text(
                    "INSERT INTO public.viewer_message_templates (key, body) VALUES (:key, :body) "
                    "ON CONFLICT (key) DO NOTHING"
                ),
                {"key": key, "body": bodies[key]},
            )
            if res.rowcount:
                inserted.append(key)
        await db.commit()
    return {"dry_run": False, "inserted": inserted}


async def _verify(session_factory) -> dict:
    bodies = vmt.seed_bodies()
    async with session_factory() as db:
        existing = await _existing(db)
    return {
        "keys": {
            key: {"exists": key in existing, "matches": existing.get(key) == body}
            for key, body in bodies.items()
        }
    }


async def run(payload: dict, session_factory=AsyncSessionLocal) -> dict:
    if not isinstance(payload, dict):
        raise ViewerTemplateError("invalid_input")
    action = payload.get("action")
    if action == "seed":
        return await _seed(payload, session_factory)
    if action == "verify":
        return await _verify(session_factory)
    raise ViewerTemplateError("invalid_input")


if __name__ == "__main__":
    try:
        print(json.dumps(asyncio.run(run(json.loads(sys.stdin.read(4096))))))
    except ViewerTemplateError as exc:
        print(f"viewer template failed: {exc.code}", file=sys.stderr)
        raise SystemExit(1) from None
    except Exception:
        # 入力値・本文・traceback を出さない
        print("viewer template failed: invalid_input", file=sys.stderr)
        raise SystemExit(1) from None
