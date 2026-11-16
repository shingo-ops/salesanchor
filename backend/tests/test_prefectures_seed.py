"""都道府県47行の正本ファイルの形を確かめる（ADR-1061 便2-2b。design.md §3-4・A30 の一部。DB は使わない）。

正本は docs/handoff/viewer-contract-stage/data/prefectures.sql の1ファイル。画面のコードに都道府県名を書かない。
"""

from __future__ import annotations

import re
from pathlib import Path

from tests.seed_data import prefectures_seed_sql

_ROOT = Path(__file__).resolve().parents[2]
_SEED = _ROOT / "docs" / "handoff" / "viewer-contract-stage" / "data" / "prefectures.sql"
_ROW_RE = re.compile(r"^\s*\('(\d{2})',\s*'([^']+)',\s*'([^']+)',\s*(\d+)\),?$", re.M)
_FRONT_SUFFIXES = {".ts", ".tsx", ".js", ".jsx", ".json"}


def test_seed_file_has_47_rows_in_code_order():
    text = _SEED.read_text("utf-8")
    rows = _ROW_RE.findall(text)
    assert len(rows) == 47
    assert [r[0] for r in rows] == [f"{i:02d}" for i in range(1, 48)]
    assert all(int(r[3]) == int(r[0]) for r in rows)
    assert all(r[1].strip() and r[2].strip() for r in rows)
    assert text.count("INSERT INTO public.prefectures (code, name_ja, name_en, sort_order) VALUES") == 1
    assert "ON CONFLICT (code) DO NOTHING;" in text


def test_loader_reads_the_seed_file_as_is():
    assert prefectures_seed_sql() == _SEED.read_text("utf-8")


def test_frontend_source_has_no_prefecture_name():
    src = _ROOT / "frontend" / "src"
    assert src.is_dir()
    hits = [
        str(p.relative_to(_ROOT))
        for p in src.rglob("*")
        if p.is_file() and p.suffix in _FRONT_SUFFIXES and "北海道" in p.read_text("utf-8", errors="ignore")
    ]
    assert hits == []
