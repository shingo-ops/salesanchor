"""予定の色の一覧の正本（ADR-1081）。

Google カレンダーの予定のラベル 24 色と同じ並び・同じ値。鍵は Google の英語の名を小文字にしたもの。
24 色の鍵と値はこのファイル 1 か所だけに書く。
"""
from __future__ import annotations

EVENT_COLORS: dict[str, str] = {
    "radicchio": "#ad1457", "cherry_blossom": "#d81b60", "flamingo": "#e67c73",
    "tomato": "#d50000", "tangerine": "#f4511e", "pumpkin": "#ef6c00",
    "mango": "#f09300", "banana": "#f6bf26", "citron": "#e4c441",
    "avocado": "#c0ca33", "pistachio": "#7cb342", "basil": "#0b8043",
    "sage": "#33b679", "eucalyptus": "#009688", "peacock": "#039be5",
    "cobalt": "#4285f4", "lavender": "#7986cb", "blueberry": "#3f51b5",
    "wisteria": "#b39ddb", "amethyst": "#9e69af", "grape": "#8e24aa",
    "cocoa": "#795548", "graphite": "#616161", "birch": "#a79b8e",
}
EVENT_COLOR_KEYS: tuple[str, ...] = tuple(EVENT_COLORS)

_HEX_TO_KEY: dict[str, str] = {v: k for k, v in EVENT_COLORS.items()}


def key_for_hex(hex_value: str | None) -> str | None:
    """Google の色の値（大文字小文字・前後の空白を問わない）から鍵を返す。無ければ None。"""
    if not hex_value or not isinstance(hex_value, str):
        return None
    return _HEX_TO_KEY.get(hex_value.strip().lower())
