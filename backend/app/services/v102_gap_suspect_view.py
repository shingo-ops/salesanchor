"""要確認の画面に出す「取りこぼし疑い」の表示用の値（段2a PR-B）。

記録の形は v102_gap_lines.gap_suspects_by_item だけが読む。ここは候補の商品名を引いて画面の形にする。
商品名は一覧の1回の要求につき、まとめて1回だけ引く（要確認 API の system.product_title と同じ public.products.name）。
"""
from __future__ import annotations

from collections.abc import Mapping

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class GapCandidate(BaseModel):
    product_id: str
    name: str


class GapSuspect(BaseModel):
    """API の応答の型（要確認 API と v102 投稿 API で共有）。"""

    gap_lines: list[int]
    candidates: list[GapCandidate]


_NAMES_SQL = "SELECT id, name FROM public.products WHERE id = ANY(:ids)"


async def with_candidate_names(db: AsyncSession, suspects: Mapping[str, dict]) -> dict[str, dict]:
    """{item_id: {gap_lines, candidates: [id]}} → {item_id: {gap_lines, candidates: [{product_id, name}]}}。

    商品名が引けない id は name を空にして残す。候補が1つも無いときは SQL を実行しない。
    """
    ids = sorted({pid for s in suspects.values() for pid in s["candidates"]})
    names: dict[int, str] = {}
    if ids:
        rows = (await db.execute(text(_NAMES_SQL), {"ids": ids})).fetchall()
        names = {int(r.id): r.name or "" for r in rows}
    return {
        item_id: {
            "gap_lines": list(s["gap_lines"]),
            "candidates": [{"product_id": str(pid), "name": names.get(pid, "")} for pid in s["candidates"]],
        }
        for item_id, s in suspects.items()
    }
