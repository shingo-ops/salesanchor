"""予定ごとの色（ADR-1081）: 画面のトークン・色の一覧・画面の文字が裏側の正本と一致することを照らす。"""
from __future__ import annotations

import json
import re
from pathlib import Path

from app.services.event_colors import EVENT_COLOR_KEYS, EVENT_COLORS

FRONTEND = Path(__file__).resolve().parents[2] / "frontend"
_TOKEN_RE = re.compile(r"--event-color-([a-z0-9-]+):\s*(#[0-9a-fA-F]+);")


def _block(text: str, start_marker: str) -> str:
    """start_marker の行から、最初の行頭の } までの塊を返す。"""
    start = text.index(start_marker)
    end = text.index("\n}", start)
    return text[start:end]


def _event_tokens(block: str) -> dict[str, str]:
    return {name.replace("-", "_"): value.lower() for name, value in _TOKEN_RE.findall(block)}


def test_tokens_css_values_match_backend():
    text = (FRONTEND / "src" / "tokens.css").read_text("utf-8")
    tokens = _event_tokens(_block(text, ":root {"))
    assert len(tokens) == 24
    assert tokens == EVENT_COLORS


def test_index_css_has_no_event_colors():
    text = (FRONTEND / "src" / "index.css").read_text("utf-8")
    assert "--gcal-event-" not in text
    assert "--event-color-" not in text


def test_frontend_key_list_matches_backend_order():
    text = (FRONTEND / "src" / "pages" / "schedule" / "eventColors.ts").read_text("utf-8")
    body = text[text.index("EVENT_COLOR_KEYS = [") : text.index("] as const")]
    keys = re.findall(r'"([a-z_]+)"', body)
    assert tuple(keys) == EVENT_COLOR_KEYS


def test_locales_have_all_color_labels():
    for lang in ("ja", "en"):
        data = json.loads((FRONTEND / "src" / "locales" / f"{lang}.json").read_text("utf-8"))
        colors = data["schedule"]["eventColors"]
        assert set(colors) == set(EVENT_COLOR_KEYS) | {"default"}, lang
        assert data["schedule"]["eventColor"], lang
