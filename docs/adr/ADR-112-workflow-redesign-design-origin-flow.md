# ADR-112: ワークフロー再編 — 設計起点フロー v2

**Amends**: ADR-012 (What/How分離), ADR-042 (4エージェント体制)  
**Status**: Accepted  
**Date**: 2026-06-05  
**Deciders**: Shingo (PO), Web Claude (Planner)

---

## What

設計起点フロー v2 を標準実装プロセスとして採用する。

1. **ADR は決定ログ**（What/Why のみ）。パイプラインを発火させない。
2. **実装トリガー = 設計ハンドオフ**（Terminal CC が設計 doc を受け取り architect → Generator を起動）。
3. **4-Phase フロー**を標準とする:

   | Phase | 担当 | 役割 |
   |-------|------|------|
   | 1設計 | Planner | 設計レベルHow（視覚参照/データ形/API契約）＋ADR起案 |
   | 2事前 | architect | コードベース照合・ルール整合・衝突/リスク審査 |
   | 3実装 | Generator | レビュー済み設計から実装・PR作成 |
   | 4検証 | Reviewer+Evaluator | コード+UI差分・二者APPROVE→develop |

4. **ドメイン別の重み**:
   - フロント視覚: Planner の参照が権威。ゲート = Evaluator ビジュアル差分。
   - バックエンド/インフラ: Planner 設計は強い提案。architect が検証し Generator が実体調整。

---

## Why

- Planner が産んだ精密設計（特に視覚・寸法・API 契約）を ADR の What に薄めて Generator に再導出させると、意図が失われる（カルテ崩れの根因）。
- 見た目・寸法は散文の命題で記述できず ADR に不向き。真実の種類ごとに正しい器とゲートを当てるべき。
- 「決定の記録（ADR）」と「実装の起動（パイプライン）」は別物。分離により過剰な儀式と偽の精度を排除し、意図の反映効率を上げる。

---

## Scope / 制約

- VPS 直接操作は引き続き禁止。repo に入るものは PR ＋ゲート経由を維持。
- ADR は廃止しない（決定軸での価値 = 意図/実装分離・理由の記録は保持）。
- `claude-pipeline.yml` のトリガー構造は変更しない（既に workflow_dispatch で手動起動）。
- 自律クラフト（バグ修正・CI 修復・リファクタ）は architect/ADR 不要・Generator 自律のまま。

---

## 非交渉条件

1. 事前レビューは **コードベース認識のある主体**（architect agent または Terminal CC）が行う。
2. 確実性は **検証ゲート**（テスト / ビジュアル差分 / ステージング）に置く。レビュー単独では担保しない。

---

## トレーサビリティ

ADR（What/Why）と設計 doc（How）を両方保管する。設計 doc または参照コンポーネントを repo に置き、ADR からリンクする。PR は ADR ＋ 設計を紐づけること。
