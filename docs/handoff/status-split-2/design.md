# status 2分割 便2 設計

**対象ADR**: ADR-121
**recon**: docs/handoff/status-split-2/recon.md
**日付**: 2026-07-29
**担当**: Planner

---

## 外部・過去事例の参照と我々への応用

- docs/adr/ADR-109-leads-status-ssot-immutable-codes.md の status SSOT 化パターン → status 追加時のフロント対応は statusPresentation.ts への entry 追加が定跡。同じパターンで lead_out_of_scope / negotiating_out_of_scope を追加。
- 過去事例: `lost` / `out_of_scope` の既存エントリが `danger/lost` バッジを使う実績 → 新2値も同じ bucket/badgeVariant を適用することで UI 一貫性を担保。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| `lead_out_of_scope` のリードにバッジ「対象外（商談化前）」が表示される | statusPresentation.ts の labelKey 参照（`leads.statusCode.lead_out_of_scope`） |
| `negotiating_out_of_scope` のリードにバッジ「対象外（商談化後）」が表示される | statusPresentation.ts の labelKey 参照（`leads.statusCode.negotiating_out_of_scope`） |
| アーカイブタブに2値のリードが表示される | STATUS_TABS の statuses 確認（inbox.types.ts:26） |
| フォローアップフィルターから2値が除外される | FOLLOWUP_EXCLUDED の Set 確認（inbox.types.ts:37） |
| フロントが `out_of_scope` を送ると便1サーバーが振り分ける | leads.py:544-551 の routing 確認 |

---

## 技術 How・KPI

- 変更量: 3ファイル・6行変更（statusPresentation.ts +2エントリ、inbox.types.ts 2行置換）
- `useInboxState.ts` の送信値変更なし: `status: "out_of_scope"` → 便1サーバーが old_status で振り分け
- i18n ラベルは便1で追加済み（`leads.statusCode.lead_out_of_scope` 等）

---

## 弊害・トレードオフ

- `out_of_scope` エントリを statusPresentation.ts に残置: 旧データとの後方互換性のため。便1マージ後も DB には `out_of_scope` が書き込まれないが、移行前の既存値（あれば）への表示担保。
- 便1未マージの状態でこの便2ブランチが先にマージされても: フロント表示は `lead_out_of_scope` / `negotiating_out_of_scope` の entry を持つが、DB にその値が存在しないため何も変わらない（安全）。

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | statusPresentation.ts に2値のバッジ設定追加 | Generator |
| 2 | inbox.types.ts アーカイブタブ・FOLLOWUP_EXCLUDED 更新 | Generator |
| 3 | TypeScript型チェック・ESLint・build確認 | Generator |
| 4 | push → PR作成 → CI全緑 → マージ | Generator |

---

## 維持の仕組み

- 守り手: .github/workflows/frontend-check.yml（TypeScript 型エラー・ESLint 違反を検出）
- 守り手: .github/workflows/ui-governance-gate.yml（PR 本文の宣言と実変更ファイルの一致を強制）
- 対象: 新ステータス追加時に statusPresentation.ts と inbox.types.ts の両方を更新し忘れると、バッジ未定義またはアーカイブタブ未表示が発生する。

---

## 継続

- 便1マージ後: DB に `lead_out_of_scope` / `negotiating_out_of_scope` が書き込まれるようになり、本設定が実際に動作する
- 便3: KPI/analytics の NOT IN リスト更新（別PR）
- 本番 DB 移行: `scripts/migrate_status_split_lead_out_of_scope.py` で `disqualified` → `lead_out_of_scope`（別カード）
