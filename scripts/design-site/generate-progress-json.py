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


def parse_overview_table(md_path: Path) -> list[dict]:
    """00-SA-OVERVIEW.md §1 テーブルをパースして行リストを返す。"""
    text = md_path.read_text(encoding='utf-8')

    # パイプ区切りテーブル行を抽出（区切り行を除く）
    table_lines = []
    in_table = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('|') and stripped.endswith('|'):
            # 区切り行（|---|---|）はスキップ
            if re.match(r'^\|[\s\-|:]+\|$', stripped):
                continue
            table_lines.append(stripped)
            in_table = True
        elif in_table:
            # テーブルが終わったら停止
            break

    if not table_lines:
        raise ValueError(f"テーブルが見つかりません: {md_path}")

    # ヘッダー行
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
        item = dict(zip(EXPECTED_COLS, cells))
        items.append(item)

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
