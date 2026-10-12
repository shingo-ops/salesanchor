---
branch: release/buyback-score-matching
status: IN_PROGRESS
started: 2026-09-24
theme: 買取商品マッチングをスコア式に改善
---

## KGI
- マッチングロジックを1ヒット即確定からスコア合計式に変更
- 除外ワードヒット=即NG（候補から完全除外）
- 同スコア複数の場合のみpending_review（人間確認件数の削減）
