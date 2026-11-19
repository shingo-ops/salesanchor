"""予定の色の一覧の正本（ADR-1081 便1）の試験。ネットには出ない。"""
from __future__ import annotations

import json
import re
from pathlib import Path

import googleapiclient

from app.services.event_colors import EVENT_COLOR_KEYS, EVENT_COLORS, key_for_hex


def test_event_colors_has_24_keys_and_lowercase_six_digit_values():
    assert len(EVENT_COLORS) == 24
    assert len(set(EVENT_COLORS.values())) == 24
    assert EVENT_COLOR_KEYS == tuple(EVENT_COLORS)
    for key, value in EVENT_COLORS.items():
        assert re.fullmatch(r"[a-z_]+", key), key
        assert re.fullmatch(r"#[0-9a-f]{6}", value), (key, value)


def test_key_for_hex_accepts_upper_case_and_spaces():
    assert key_for_hex("#AD1457") == "radicchio"
    assert key_for_hex("  #Ad1457 ") == "radicchio"
    assert key_for_hex("#a79b8e") == "birch"
    for key, value in EVENT_COLORS.items():
        assert key_for_hex(value) == key
        assert key_for_hex(value.upper()) == key


def test_key_for_hex_returns_none_for_unknown_or_empty():
    assert key_for_hex("#123456") is None
    assert key_for_hex("") is None
    assert key_for_hex(None) is None


def test_u1_bundled_calendar_api_accepts_event_label_version():
    """U1: 手元の部品に入っている API 説明で、events.insert・events.patch が eventLabelVersion を受ける。"""
    doc_path = Path(googleapiclient.__file__).parent / "discovery_cache" / "documents" / "calendar.v3.json"
    doc = json.loads(doc_path.read_text(encoding="utf-8"))
    methods = doc["resources"]["events"]["methods"]
    for name in ("insert", "patch"):
        assert "eventLabelVersion" in methods[name]["parameters"], name
