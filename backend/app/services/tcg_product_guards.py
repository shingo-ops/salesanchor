"""Deterministic evidence from a single LINE message; no model calls."""
import re
import unicodedata

# Match standalone rarity/grade notation, not STAR, SARAH, or CHARIZARD.
_SINGLE = re.compile(r"(?<![A-Za-z])(?:SAR|AR|PSA(?:\s*[-:]?\s*\d{1,2}(?:\.\d)?)?)(?![A-Za-z0-9])", re.I)
_SUFFIXES = ("カードゲーム", "カード", "シングルカード", "スペシャルセット",
             "在庫商品", "在庫", "BOX カートン", "BOX", "カートン")


def single_card_marker(*fields: str) -> str | None:
    """Each field is independent: never concatenate pieces into a new marker."""
    for field in fields:
        match = _SINGLE.search(unicodedata.normalize("NFKC", field or ""))
        if match:
            return match[0]
    return None


def _plain_heading(line: str) -> str:
    # Trim decorative symbols only at the edges; retain interior structure.
    text = unicodedata.normalize("NFKC", line).strip()
    while text and not text[0].isalnum():
        text = text[1:].strip()
    while text and not text[-1].isalnum():
        text = text[:-1].strip()
    return " ".join(text.casefold().split())


def work_heading_evidence(raw_text: str, line_start: int, line_end: int,
                          works: list[dict]) -> tuple[str, int] | None:
    """Only explicit, standalone catalog work headings establish scope.

    Every recognized or bracketed unknown section replaces the previous one.
    No price, neighboring product, or model prefix establishes a work.
    """
    lines = raw_text.split("\n")
    if not 1 <= line_start <= line_end <= len(lines):
        return None
    aliases: dict[str, set[str]] = {}
    for work in works:
        if not work.get("is_active", True):
            continue
        for name in (work["display_name"], work.get("alt_name")):
            if name:
                aliases.setdefault(_plain_heading(name), set()).add(str(work["id"]))
        # Observed heading 【ワンピ在庫商品】; bind to catalog One Piece only.
        if _plain_heading(work["display_name"]) == "one piece":
            aliases.setdefault("ワンピ", set()).add(str(work["id"]))
    headings: dict[str, set[str]] = {}
    for alias, ids in aliases.items():
        for suffix in ("", *_SUFFIXES):
            for space in ("", " "):
                headings.setdefault(_plain_heading(alias + space + suffix), set()).update(ids)
    nearest = None
    for number, line in enumerate(lines[:line_start - 1], 1):
        plain = _plain_heading(line)
        ids = headings.get(plain, set())
        if ids:
            nearest = (next(iter(ids)), number) if len(ids) == 1 else None
        elif line.strip() and (
            line.strip().startswith(("【", "[", "■", "━", "🔥"))
            or (not line.strip()[0].isalnum() and not line.strip()[-1].isalnum()
                and not any(ch.isdigit() for ch in line))
            or plain in {"その他", "ヴァイスシュヴァルツ", "ヴァイスシュバルツ", "ヴァイス", "遊戯王", "ガンダム", "デジモン", "ホロライブ"}
            or sum(alias in plain for alias in aliases) > 1
        ):
            # Unknown/compound sections must not inherit the previous work.
            nearest = None
    return nearest
