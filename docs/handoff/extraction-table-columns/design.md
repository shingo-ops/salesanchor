# design: 抽出テーブル列改善

## 対象 ADR

- ADR-027: `docs/adr/ADR-027-ui-internationalization.md`（UI 文字列は全て `t("key")` 経由・`ja.json`/`en.json` 同一キー必須）
- ADR-067: `docs/adr/ADR-067-design-tokens.md`（CSS 変数・デザイントークン使用必須）
- ADR-144: `docs/CC_UI_GOVERNANCE.md`（UI 部品新設時は `components/` 金型確認・生 select/input/色直値禁止）

## recon 参照

- `docs/handoff/extraction-table-columns/recon.md`

## KGI

| 基準 | 検証方法 |
|------|----------|
| 抽出タブの直近ジョブテーブルで提供者名（suppliers.name）が表示される | ブラウザで抽出タブを開き、提供者列に channel 名ではなく実際の提供者名が表示されること |
| 解決・未解決・要確認カウントが表示される | 各ジョブ行に数値が表示されること（analysis_results 集計） |
| 既存インポートタブに影響なし | インポートタブの表示が変わらないこと |

## 設計

### バックエンド変更

`recent_extraction_jobs` SQL クエリを拡張する。

既存パターン踏襲: `backend/app/services/tcg_analysis_dashboard_svc.py` の get_supplier_pipeline() 内の JOIN 構造を参考にする。

```
extraction_jobs ej
  LEFT JOIN extraction_items ei ON ei.extraction_job_id = ej.id
  LEFT JOIN analysis_results ar ON ar.extraction_item_id = ei.id   # 追加
  LEFT JOIN source_messages sm ON sm.id = ej.source_message_id
  LEFT JOIN supplier_channels sc ON sc.id = sm.supplier_channel_id
  LEFT JOIN suppliers s ON s.id = sc.supplier_id                   # 追加
GROUP BY ej.id, ej.status, ej.created_at, s.name
```

集計:
- `COUNT(ar.id) FILTER (WHERE ar.pid_resolved = true)::int AS resolved_count`
- `COUNT(ar.id) FILTER (WHERE ar.pid_resolved = false)::int AS unresolved_count`
- `COUNT(ar.id) FILTER (WHERE ar.needs_review = true)::int AS needs_review_count`
- `s.name AS supplier_name`

### フロントエンド変更

変更対象:
- `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx`
- `frontend/src/locales/ja.json`
- `frontend/src/locales/en.json`

`RecentExtractionJob` 型: `channel_name` を `supplier_name` に変更、4フィールド追加
`recentJobColumns`: 4列 → 7列（supplier/items/resolved/unresolved/needs_review/status/date）
i18n: `extractionJobChannel` → `extractionJobSupplier` + 3新規キー

## 外部・過去事例の参照と我々への応用

既存 `backend/app/services/tcg_analysis_dashboard_svc.py` の `get_supplier_pipeline()` 関数（行402-444）で同一の JOIN パターン（`LEFT JOIN suppliers s ON s.id = sc.supplier_id`）が稼働中。同ファイルの `analysis_results` JOIN パターン（行477）も稼働中。今回は同パターンを `get_pipeline_summary()` の recent_extraction_jobs セクションに適用する。

## 維持の仕組み

守り手: backend/app/services/tcg_analysis_dashboard_svc.py

バックエンドとフロントエンドの型定義が一致している限り動作する。`RecentExtractionJobItem`（Pydantic）と `RecentExtractionJob`（TypeScript）が同じフィールドを持つことが維持条件。

## 影響範囲

- 呼び出し元: `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx` のみ
- API変更: フィールド追加（既存フィールド削除なし→後方互換）
- DBへの書き込み: なし（SELECT 変更のみ）

## 弊害

なし（SELECT クエリの拡張のみ、既存機能に影響なし）

## 戻し方

```bash
git revert HEAD
git push origin release/extraction-table-columns
```

## 測り方

1. ブラウザで `/super-admin` → 抽出タブを開く
2. 直近ジョブテーブルを確認（提供者名・各カウントが表示されていること）
3. インポートタブが正常に表示されていること
