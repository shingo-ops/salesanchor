"""名簿の値の直書きが戻らないことを、ファイルを読んで数える試験（design §12・card-pr-b.md §6 の K4・K7）。

- K4: 分析・カルテ・言語判定の3ファイルに、連絡手段の名前の直書きが無い（0件）
- K7: `public.channel_masters` / `public.channel_master_tenant_settings` の文字は
      backend/app/services/channel_masters.py の定数2つにだけ書く
"""
from __future__ import annotations

import re
from pathlib import Path

_APP = Path(__file__).resolve().parents[1] / "app"

_K4_FILES = (
    _APP / "routers" / "analytics.py",
    _APP / "services" / "lead_conversion_factors.py",
    _APP / "services" / "lang_judge.py",
)
_K4_PATTERN = re.compile(
    r"""['"](messenger|instagram|whatsapp|discord|phone|in_person)['"]"""
    r"|CHANNEL_(MESSENGER|INSTAGRAM|WHATSAPP)|META_CHANNELS"
)
_K7_PATTERN = re.compile(r"public\.channel_master(s|_tenant_settings)")
_K7_ALLOWED = _APP / "services" / "channel_masters.py"


def test_k4_no_channel_name_literals_in_analysis_files():
    hits = []
    for path in _K4_FILES:
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if _K4_PATTERN.search(line):
                hits.append(f"{path.name}:{lineno}: {line.strip()}")
    assert hits == [], "連絡手段の名前の直書きが戻っています:\n" + "\n".join(hits)


def test_k7_master_table_names_appear_only_in_channel_masters_service():
    hits = []
    for path in sorted(_APP.rglob("*.py")):
        if path == _K7_ALLOWED:
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if _K7_PATTERN.search(line):
                hits.append(f"{path.relative_to(_APP)}:{lineno}: {line.strip()}")
    assert hits == [], "名簿の表名が channel_masters.py の外にあります:\n" + "\n".join(hits)
