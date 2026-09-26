# recon — dp-card-selfcheck-output

**仕事名**: dp-card-selfcheck-output  
**日付**: 2026-08-31  
**対象ADR**: ADR-091  
**担当**: architect

---

## 背景

2026-08-31 の Discord 連携便（PR #3169 / #3172 / #3174）で、設計パートナーが発行した
カード計8件に不備が見つかった。8件すべてが `docs/ai-agents/design-partner.md` §5.5 に
既に記載済みの教訓に反していた。項目数の不足ではなく照合の省略が原因であることを実測で確認した。

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `docs/ai-agents/design-partner.md:161` | §5.5「カード発行前チェック」見出し |
| `docs/ai-agents/design-partner.md:165` | 自己照合の説明文（1つでも欠ければカードを送らず直す） |
| `docs/ai-agents/design-partner.md:167` | 追加箇所: 項目 0「照合結果を出力する」 |
| `docs/ai-agents/design-partner.md:170` | 既存の項目 1「記号を壊さない」（追加後の行番号） |
| `docs/ai-agents/lessons.d/20260831-card-design-failures.md:1` | 今回追加の教訓ポスト（8件の不備記録） |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | 照合結果の出力義務が既存の §5.5 項目と重複しないか | `docs/ai-agents/design-partner.md:161-182` を通読して確認 | ✅ 解消済み（重複なし・補完関係） |

**未解決ゼロ確認**: 全て解消済み
