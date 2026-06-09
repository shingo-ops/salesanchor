# ADR-120: ステータス → 見た目の SSoT（決定レイヤー① 中央対応表）

- **Status**: Accepted
- **Date**: 2026-06-09
- **Deciders**: shingo-ops（PO）, Hikky-dev（Dev）

## Context

ステータス値 → バッジ色 / CSS クラスの決定ロジックが 29サイト（10ドメイン・約44分岐）に散在していた（recon: `docs/handoff/decision-layer-01/recon.md`）。

主要な問題:
1. **同一概念が3色に分裂**: LeadStatus "negotiating" が画面ごとに `--lead-contact-bg`（オレンジ）/ `--warning-bg`（黄）/ `--info-bg`（青）の3色で表示される
2. **ロジック複製**: InvoicesPage と InvoiceDetailPage に同一 inline ternary が copy-paste
3. **DB値 = CSSクラス名の前提**: DealsPage が `badge-${d.status}` で直注入。中間マッピング層がない

## Decision

すべてのステータス → 見た目の決定を `frontend/src/utils/statusPresentation.ts` の **中央対応表（SSoT）** に集約する。

### 構造

```typescript
// (domain, status) → { bucket, badgeVariant, labelKey }
getStatusPresentation("lead", lead.status)
// → { bucket: "info", badgeVariant: "negotiating", labelKey: "leads.statusCode.negotiating" }
```

### バケット5分類

| bucket | 色 | 性質 |
|--------|----|------|
| success | 緑 | 完了 / 成功 / 有効 |
| danger | 赤 | 失敗 / 失注 / 期限超過 |
| warning | 黄 | 要対応 / 保留 |
| info | 青 | 進行中 / 交渉中 |
| neutral | 灰 | 新規 / 下書き / 不明 |

### 衝突解消

1. `negotiating` → `info` に統一（3色 → 1色）
2. Invoice 重複 ternary → 補助関数1ヶ所
3. DealsPage 直注入 → 補助関数経由

### 安全フォールバック

未知のステータス値は `neutral` を返し、開発環境では `console.warn` を出力する。クラッシュしない。

## Consequences

### Good
- ステータス → 見た目の決定が1ファイルに集約される（変更箇所が明確）
- 同一ステータスが全画面で同一色になる（ユーザー混乱の解消）
- 未知ステータスでもクラッシュしない（安全失敗）
- 直書き検知 lint でリグレッション防止

### Bad / Tradeoff
- 実画面 29サイトの置換が必要（Step 2 で実施）
- DealsPage の視覚変更を伴う（現行と異なる可能性）
- staff.pending / bot.maintenance の色変更（danger → warning）はユーザーへの視覚変更

### Migration Plan
- Step 1: 中央対応表 + 補助関数 + プレビュー + lint(warn) を追加（追加のみ・この ADR）
- Step 2: 24インライン + 集約5 を補助関数へ置換（各 PR でロールバック可）
- Step 3: lint を warn → error へ昇格（止血完了）

## References
- recon: `docs/handoff/decision-layer-01/recon.md`
- design: `docs/handoff/decision-layer-01/design.md`
- 実装: `frontend/src/utils/statusPresentation.ts`
- preview: `frontend/src/pages/design-preview/sections/StatusSection.tsx`
- lint: `frontend/scripts/check-status-direct-writes.js`
- 関連: ADR-109（LeadStatus SSOT・不変コード）
