"""配信先のスプレッドシートの「要確認」タブに、要確認の一覧を出す（段1：出力だけ）。

設計: docs/handoff/review-sheet-export/design.md §3・§4。
- 何を出すか: 画面の要確認一覧と同じ fetch_analysis_results(status_tab="NEEDS_REVIEW") だけ。条件を別に書かない。
- どこに出すか: tcg_distribution_targets.review_sheet_name が設定された配信先だけ（NULL なら出さない）。
- 書き方: 配信と同じ安全装置 #1〜#5（_write_tab_sync）。タブが無ければ止める（作らない）。
- 理由の日本語: backend/app/data/review_reason_labels_ja.json（正本 ja.json の写し。試験で一致を縛る）。
"""
from __future__ import annotations

import json
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.tcg_analysis_review_svc import fetch_analysis_results
from app.services.tcg_distribution_svc import DIST_ROW_LIMIT, _write_tab_sync

REVIEW_SHEET_HEADERS = [
    "投稿日時",
    "仕入先",
    "行",
    "原文",
    "価格",
    "数量",
    "商品",
    "状態",
    "単位",
    "要確認の理由",
    "間の行",
    "候補",
    "件の番号",
]

LABELS_PATH = Path(__file__).resolve().parent.parent / "data" / "review_reason_labels_ja.json"
_JST = ZoneInfo("Asia/Tokyo")
_JOIN = "、"


@lru_cache(maxsize=1)
def load_review_reason_labels() -> dict[str, str]:
    """{理由コード: 日本語}。文字列でない値（source の入れ子など）は除く。"""
    block = json.loads(LABELS_PATH.read_text(encoding="utf-8"))
    return {k: v for k, v in block.items() if isinstance(v, str)}


def _format_posted_at(value: datetime | None) -> str:
    if value is None:
        return ""
    return value.astimezone(_JST).strftime("%Y-%m-%d %H:%M")


def _source_lines(raw_text: str, span: str) -> str:
    """span "Lx-y"（1始まり・両端を含む）の行を、改行でつなぐ。範囲が読めなければ空。"""
    if not span.startswith("L") or "-" not in span:
        return ""
    start_text, _, end_text = span[1:].partition("-")
    if not (start_text.isdigit() and end_text.isdigit()):
        return ""
    start, end = int(start_text), int(end_text)
    return "\n".join(raw_text.split("\n")[start - 1 : end])


def _reason_text(details: list[dict], labels: dict[str, str]) -> str:
    return _JOIN.join(labels.get(d["code"], d["code"]) for d in details)


def _build_row(item: dict, labels: dict[str, str]) -> list[str]:
    gemini = item["gemini"]
    system = item["system"]
    suspect = item.get("gap_suspect") or {}
    return [
        _format_posted_at(item.get("posted_at")),
        item["provider"],
        gemini["span"],
        _source_lines(item["raw_text"], gemini["span"]),
        gemini["price"],
        gemini["quantity"],
        system["product_title"],
        system["condition"],
        system["unit"],
        _reason_text(item.get("review_reason_details", []), labels),
        _JOIN.join(f"L{n}" for n in suspect.get("gap_lines", [])),
        _JOIN.join(c["name"] for c in suspect.get("candidates", [])),
        item["extraction_item_id"],
    ]


def build_review_rows(items: list[dict], labels: dict[str, str]) -> list[list[str]]:
    """fetch_analysis_results の items を、シートの行（REVIEW_SHEET_HEADERS の順・全て文字列）にする。純粋関数。"""
    return [_build_row(item, labels) for item in items]


def write_review_sheet_sync(gc: Any, creds: Any, target: dict, rows: list[list[str]]) -> dict:
    """要確認タブ（target["review_sheet_name"]）へ全置換で書く。安全装置は配信と同じ _write_tab_sync。"""
    tab_name = target.get("review_sheet_name")
    if not tab_name:
        return {"status": "error", "error": "review_sheet_name が未設定です"}
    return _write_tab_sync(gc, creds, target, tab_name, REVIEW_SHEET_HEADERS, rows)


async def collect_review_rows(db: AsyncSession) -> list[list[str]]:
    """要確認の一覧（画面と同じ定義）を取り、シートの行にする。1回の配信で1回だけ呼ぶ。"""
    data = await fetch_analysis_results(db, status_tab="NEEDS_REVIEW", limit=DIST_ROW_LIMIT)
    return build_review_rows(data["items"], load_review_reason_labels())
