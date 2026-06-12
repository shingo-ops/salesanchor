#!/usr/bin/env python3
"""
SA設計図書サイト — 進捗JSON生成スクリプト（ADR-134）

00-SA-OVERVIEW.md §1 のパイプ区切りテーブルをパースして progress.json に変換する。
変換失敗時は sys.exit(1) でデプロイを停止する（スクリプト失敗 = デプロイ停止）。

Usage:
    python3 scripts/design-site/generate-progress-json.py \
        docs/plans/sa-progress/00-SA-OVERVIEW.md \
        /tmp/design-site-progress.json
"""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

EXPECTED_COLS = ['SA', 'ADR', 'テーマ', '現フェーズ', '進捗', '次のアクション', '担当', '更新日']

# Unicode circled numbers ①〜⑥ → int 1〜6
_CIRCLE_MAP = {chr(0x2460 + i): i + 1 for i in range(6)}


def _parse_phase(phase_raw: str) -> int | None:
    """現フェーズ列から数値フェーズを抽出する。
    - '横断適用' → None
    - '未着手'   → 0
    - '④ ...'   → 4
    """
    stripped = phase_raw.strip()
    if stripped in ('横断適用', '—'):
        return None
    if stripped.startswith('未着手'):
        return 0
    for ch, num in _CIRCLE_MAP.items():
        if stripped.startswith(ch):
            return num
    return 0


def _parse_progress(progress_raw: str) -> int | None:
    """進捗列から整数(0-100)または None を返す。
    - '80%' → 80
    - '0%'  → 0
    - '—'   → None
    """
    stripped = progress_raw.strip().rstrip('%')
    if stripped in ('—', '', '-'):
        return None
    try:
        return int(stripped)
    except ValueError:
        return None


def _normalize_item(raw: dict) -> dict:
    """生の日本語キー辞書を progress.js が期待する英語キー辞書に変換する。"""
    phase = _parse_phase(raw['現フェーズ'])
    return {
        'id': raw['SA'].strip(),
        'adr': raw['ADR'].strip(),
        'theme': raw['テーマ'].strip(),
        'phase': phase,
        'phase_label': raw['現フェーズ'].strip(),
        'progress': _parse_progress(raw['進捗']),
        'next_action': raw['次のアクション'].strip(),
        'owner': raw['担当'].strip(),
        'updated': raw['更新日'].strip(),
    }


def parse_overview_table(md_path: Path) -> list[dict]:
    """00-SA-OVERVIEW.md §1 テーブルをパースして正規化行リストを返す。"""
    text = md_path.read_text(encoding='utf-8')

    table_lines: list[str] = []
    in_table = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('|') and stripped.endswith('|'):
            if re.match(r'^\|[\s\-|:]+\|$', stripped):
                continue
            table_lines.append(stripped)
            in_table = True
        elif in_table:
            break

    if not table_lines:
        raise ValueError(f"テーブルが見つかりません: {md_path}")

    header_raw = [c.strip() for c in table_lines[0].strip('|').split('|')]
    if header_raw != EXPECTED_COLS:
        raise ValueError(
            f"ヘッダーが期待値と一致しません\n期待: {EXPECTED_COLS}\n実際: {header_raw}"
        )

    items = []
    for row_line in table_lines[1:]:
        cells = [c.strip() for c in row_line.strip('|').split('|')]
        if len(cells) != len(EXPECTED_COLS):
            raise ValueError(
                f"列数不一致 (期待 {len(EXPECTED_COLS)}, 実際 {len(cells)}): {row_line}"
            )
        raw = dict(zip(EXPECTED_COLS, cells))
        items.append(_normalize_item(raw))

    return items


def main() -> None:
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <overview.md> <output.json>", file=sys.stderr)
        sys.exit(1)

    md_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2])

    if not md_path.exists():
        print(f"❌ ファイルが見つかりません: {md_path}", file=sys.stderr)
        sys.exit(1)

    try:
        items = parse_overview_table(md_path)
    except (ValueError, OSError) as exc:
        print(f"❌ テーブルパース失敗: {exc}", file=sys.stderr)
        sys.exit(1)

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": str(md_path),
        "item_count": len(items),
        "items": items,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"✅ progress.json 生成完了: {len(items)} 件 → {out_path}")


if __name__ == '__main__':
    main()
