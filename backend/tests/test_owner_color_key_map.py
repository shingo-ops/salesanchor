"""人の色の移行（schedule-settings 便3a）の 24 組と CHECK の鍵が、色の正本と同じであることを文字で照らす（DB は使わない）。

- 移行ファイルの `WHEN '#…' THEN '…'` の 24 組 == backend/app/services/event_colors.py の EVENT_COLORS
- 移行ファイルの CHECK の鍵の並び == ひな形 tenant.py の calendar_events_color_key_check の並び
- ひな形の calendar_owner_settings の CHECK の鍵の並び == 同じ並び
"""
from __future__ import annotations

import re
from pathlib import Path

from app.services.event_colors import EVENT_COLOR_KEYS, EVENT_COLORS

_ROOT = Path(__file__).resolve().parents[2]
_MIGRATION = _ROOT / "migrations" / "20261128_100000_owner_color_key_drop_dead_columns.sql"
_TENANT_PY = _ROOT / "backend" / "app" / "services" / "tenant.py"

_WHEN_RE = re.compile(r"WHEN\s+'(#[0-9a-fA-F]{6})'\s+THEN\s+'([a-z_]+)'")
_CHECK_RE = r"CONSTRAINT\s+{name}\s+CHECK\s+\(color_key IN \(([^)]*)\)\)"
_CHECK_ADD_RE = r"CHECK\s+\(color_key IN \(([^)]*)\)\)"


def _keys_of(group: str) -> list[str]:
    return re.findall(r"'([a-z_]+)'", group)


def test_migration_has_the_same_24_pairs_as_event_colors():
    text = _MIGRATION.read_text("utf-8")
    pairs = _WHEN_RE.findall(text)
    assert len(pairs) == 24
    assert {key: value.lower() for value, key in pairs} == EVENT_COLORS
    assert [key for _value, key in pairs] == list(EVENT_COLOR_KEYS)


def test_migration_check_keys_match_event_colors_order():
    text = _MIGRATION.read_text("utf-8")
    found = re.findall(_CHECK_ADD_RE, text)
    assert len(found) == 1
    assert _keys_of(found[0]) == list(EVENT_COLOR_KEYS)


def test_template_owner_settings_check_matches_calendar_events_check():
    text = _TENANT_PY.read_text("utf-8")
    events = re.findall(_CHECK_RE.format(name="calendar_events_color_key_check"), text)
    owners = re.findall(_CHECK_RE.format(name="calendar_owner_settings_color_key_check"), text)
    assert len(events) == 1 and len(owners) == 1
    assert _keys_of(owners[0]) == _keys_of(events[0]) == list(EVENT_COLOR_KEYS)


def test_template_owner_settings_has_no_dead_columns():
    text = _TENANT_PY.read_text("utf-8")
    start = text.index("{schema}.calendar_owner_settings (")
    block = text[start : text.index(");", start)]
    assert "color_key text" in block
    for old in ("    color character", "is_visible", "share_mode"):
        assert old not in block
