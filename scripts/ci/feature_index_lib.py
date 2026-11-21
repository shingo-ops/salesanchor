"""FEATURE-INDEX.md の読み取りと glob の照らし（標準ライブラリだけ・Python 3.12 で動く）。

設計: docs/handoff/requirement-library/design.md §3 便1。
検査（check_feature_index.py）と、あとの便の見張りが同じ部品を import する。
"""
from __future__ import annotations

import fnmatch
import re

ADR_REF_RE = re.compile(r"ADR-((?:SA-)?\d+)")
_STATUS_WORDS = ("ステータス", "status", "状態")


def normalize_adr_number(raw: str) -> str:
    """先頭の 0 を除いた番号にする（`SA-` つきは `SA-17` の形）。"""
    if raw.startswith("SA-"):
        return "SA-" + str(int(raw[3:]))
    return str(int(raw))


def adr_ids_in(cell: str) -> list[str]:
    """正準 ADR 欄などから ADR 番号を拾う。"""
    return [normalize_adr_number(m) for m in ADR_REF_RE.findall(cell)]


def match_glob(pattern: str, relpath: str) -> bool:
    """`/` で区切った段ごとに照らす。`*`・`?` は1段の中だけ。`**` だけの段は0段以上に当たる。"""
    return _match_segments(pattern.split("/"), relpath.split("/"))


def _match_segments(pats: list[str], segs: list[str]) -> bool:
    if not pats:
        return not segs
    head = pats[0]
    if head == "**":
        rest = pats[1:]
        for i in range(len(segs) + 1):
            if _match_segments(rest, segs[i:]):
                return True
        return False
    if not segs:
        return False
    if not fnmatch.fnmatchcase(segs[0], head):
        return False
    return _match_segments(pats[1:], segs[1:])


def _split_cells(line: str) -> list[str]:
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def _is_separator(cells: list[str]) -> bool:
    return all(re.fullmatch(r":?-{2,}:?", c.replace(" ", "")) for c in cells if c) and any(cells)


def read_index(text: str) -> tuple[list[dict], list[tuple[str, str]]]:
    """(rows, excluded) を返す。

    rows: 見出しの1列目が「機能キーワード」の表の行（5 列）。dict(keyword, adr, spec, code, note, line)
    excluded: 「索引に載せない ADR・設計仕様書」節の表の行 (1列目, 理由)
    「ADR 候補バックログ」など他の表は読まない。
    """
    rows: list[dict] = []
    excluded: list[tuple[str, str]] = []
    mode = None  # None / "feature" / "excluded"
    in_excluded_section = False
    for lineno, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("#"):
            in_excluded_section = "索引に載せない" in stripped
            mode = None
            continue
        if not stripped.startswith("|"):
            mode = None
            continue
        cells = _split_cells(stripped)
        if mode is None:
            # 表の見出し行
            if cells and cells[0] == "機能キーワード":
                mode = "feature"
            elif in_excluded_section:
                mode = "excluded"
            else:
                mode = "other"
            continue
        if _is_separator(cells):
            continue
        if mode == "feature" and len(cells) >= 5:
            rows.append(
                {
                    "keyword": cells[0],
                    "adr": cells[1],
                    "spec": cells[2],
                    "code": cells[3],
                    "note": cells[4],
                    "line": lineno,
                }
            )
        elif mode == "excluded" and len(cells) >= 2:
            excluded.append((cells[0], cells[1]))
    return rows, excluded


def _clean_word(x: str) -> str:
    x = x.strip().strip("*>- \t").strip()
    m = re.match(r"[^\s（(]+", x)
    word = m.group(0) if m else ""
    return word.strip("*").strip()


def _norm_label(s: str) -> str:
    return s.replace("*", "").replace("`", "").strip().casefold()


_COLON_RE = re.compile(
    r"^[\s\-*>]*\**\s*(ステータス|status|状態)\s*\**\s*[:：]\**\s*(.*)$", re.IGNORECASE
)
_HEADING_RE = re.compile(r"^#+\s*(ステータス|status|状態)\s*$", re.IGNORECASE)


def status_word(text: str) -> str | None:
    """ADR の状態の値の先頭の語を返す（見つからなければ None）。"""
    lines = text.splitlines()[:40]
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if re.sub(r"^[#\s]+", "", stripped).startswith("ADR-"):
            continue
        # 表の行
        if stripped.startswith("|"):
            cells = _split_cells(stripped)
            if len(cells) >= 2 and _norm_label(cells[0]) in _STATUS_WORDS:
                return _clean_word(cells[1]) or None
            continue
        # 見出しだけの行
        if _HEADING_RE.match(stripped):
            for nxt in lines[i + 1 :]:
                if nxt.strip():
                    return _clean_word(nxt) or None
            return None
        # `ステータス: X` の形
        m = _COLON_RE.match(stripped)
        if m:
            return _clean_word(m.group(2)) or None
    return None
