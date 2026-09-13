# recon — lessons-guard 便1（教訓の1便1ファイル化・現在地の事実）

> この文書は何か（専門用語なしの1行）:
> 教訓ノートの衝突実態を実測した、着手前の現在地記録。

- 親: ../../specs/lessons-guard/README.md ／ 設計: ../../specs/lessons-guard/design.md
- 関連ADR: ADR-114

## 実測日・起点
- 2026-07-19 / origin/main = abba9f7f

## 実測の要点（file:line根拠つき）
1. 衝突の主戦場: docs/ai-agents/design-partner.md（30日間の変更45回・全正本中1位。
   2位 docs/ai-agents/evidence-registry.md 28回、3位 docs/STANDARD-WORKFLOW.md 13回）。
2. §6の現構造: docs/ai-agents/design-partner.md:173 に分類別教訓（6-1〜6-5）、
   docs/ai-agents/design-partner.md:178 に出所書式、全329行。
3. 直近14日で§6追記系マージ約20本。マージコンフリクト解消コミット複数を実測。
4. 束ねの型: scripts/ledger-view.sh:13 以降（本体＋.d/連結表示）が流用可能。
   台帳側は G3/G5 実測PASS済み（docs/specs/ledger-guard/design-phase2.md:70 付近の実測記録）。

## 既存ADR検索の結果
- git grep -i "lesson" docs/adr/ 済み。直接の該当ADRなし。
  隣接: ADR-114（消さず残す原則）を archive/ 運用が踏襲。
