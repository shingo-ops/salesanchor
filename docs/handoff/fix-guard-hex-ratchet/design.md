# design: guard-hex-increase 誤検知修正

## 変更箇所

`scripts/check-design-token-ratchet.sh:25`（1 行変更）

### Before
```bash
matches=$(git show "${ref}:${file}" 2>/dev/null | grep -oE '#[0-9a-fA-F]{3,8}\b' || true)
```

### After
```bash
matches=$(git show "${ref}:${file}" 2>/dev/null | sed -E 's/\(#[0-9]+\)//g' | grep -oE '#[0-9a-fA-F]{3,8}\b' || true)
```

## 設計判断

### なぜ `-P` lookbehind ではなく `sed` 前処理か
既存 grep オプションが `-E`（ERE）のため lookbehind は使えない。
`sed` で `(#十進数字)` を除去してから同じ grep を適用することで、
grep ロジックを変更せずに誤検知を排除できる。

### なぜ `(#[0-9a-fA-F]+)` ではなく `(#[0-9]+)` か
`sed -E 's/\(#[0-9a-fA-F]+\)//g'` では index.css 等に存在する
CSS コメント内の色値参照 `(#2e7d32)` `(#e53e3e)` 等も除去してしまい、
count が旧: 187 → 新: 182 と変化してしまう（偽陰性・既存ベースライン破壊）。

PR 番号は常に十進数字のみ（a-f を含まない）。
CSS 色値参照は必ず a-f を含む（本プロジェクト実測・index.css 全 5 件確認済み）。
→ `[0-9]+`（十進のみ）で区別できる。

## 検算結果

| テストケース | 旧パイプライン | 新パイプライン | 期待 |
|---|---|---|---|
| `(#3285)` | `#3285` 検出 | 空 | 空 ✓ |
| `(#3165)` | `#3165` 検出 | 空 | 空 ✓ |
| `color: #fff` | `#fff` | `#fff` | `#fff` ✓ |
| `color: #1a2b3c` | `#1a2b3c` | `#1a2b3c` | `#1a2b3c` ✓ |
| `/* (#2e7d32) */` | `#2e7d32` | `#2e7d32` | `#2e7d32` ✓ |
| `#fff; /* (#3285) */` | `#fff` + `#3285` | `#fff` | `#fff` ✓ |
| index.css count | 187 | 187 | 187（差 0）✓ |

## KGI / KPI

| 基準 | 検証方法 |
|---|---|
| PR #3285 の guard-hex-increase が PASS | CI 通過確認 |
| index.css count が修正前後で変化しない | 187 = 187 実測済み |
| 実際の hex 色増加は引き続き検出される | テストケース [3][4] 実測済み |

## 影響範囲
- 変更: `scripts/check-design-token-ratchet.sh` 1 行
- 影響: guard-hex-increase ジョブのみ
- 戻し方: `sed` ステップを削除して元の 1 行に戻す（可逆）

## 外部事例
なし（既存スクリプトの regex 修正）

## 対象 ADR
- ADR-067（デザイントークン強制・ratchet の根拠）
- ADR-144（ui-allow 書式要件・誤検知の発生源）
