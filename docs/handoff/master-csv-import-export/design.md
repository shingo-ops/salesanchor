# design: master-csv-import-export

## KGI
- 4マスタテーブル（units, conditions, tcg_status_master, tcg_note_master）にCSVエクスポート/インポート機能を追加
- super-admin および テナント管理者の両方がCSVでマスタを一括管理できる

## KPI（画面で○×を判定できる粒度）

| 基準 | 検証方法 |
|------|---------|
| GET /super-admin/units/export → CSV ファイルがダウンロードされる | ブラウザで export ボタンをクリック → units-export.csv が DL される |
| POST /super-admin/units/import/preview → rows 配列が返る | CSV ファイルを選択して preview ボタンクリック → insert/update 件数が表示される |
| POST /super-admin/units/import/commit → rows が DB に反映される | preview 後 commit ボタン → ページリロードで変更が反映されている |
| tenant 側も同様 | /management-center/units → export/import ボタンが表示される |
| conditions, status_master, note_master も同様 | 各ページで同操作が成功する |
| UI 文字列がすべて翻訳キー経由 | ハードコード日本語が grep で 0 件 |

## 変更設計

### Backend
- SupplierImport パターンをそのまま踏襲（`_compute_digest`, `_read_upload`, `_parse_and_validate` ヘルパー）
- SHA-256 digest: preview レスポンスに含め、commit 時に Form パラメータとして再送・検証
- ADR-072 準拠: テナント側 commit エンドポイントで `await reset_tenant_context(db, tenant_id)`

### Frontend
- SupplierImportPage.tsx と同じ UI パターン（preview → diff 表示 → commit）
- i18n キー: `unitCsv`, `conditionCsv`, `statusMasterCsv`, `noteMasterCsv`
- デザインシステム: `HeaderButton`, `ContentToolbar`, `PageLayout` のみ（ADR-144）
- 新規ルート8件を App.tsx に追加

## 参照ADR
- ADR-027: `docs/adr/ADR-027-ui-internationalization.md`
- ADR-072: `docs/adr/ADR-072-multi-tenant-rls-hardening.md`
- ADR-144: `docs/CC_UI_GOVERNANCE.md`

## 弊害・リスク
- DB migration なし（既存テーブルへの新エンドポイント追加のみ）
- マッチキーの選択: units/conditions=`code`、status_master=`status_id`、note_master=`label_ja` — label_ja は一意であることを前提

## 外部事例
- 社内パターン: super_admin_suppliers.py (既存)

## 設計仕様書
対象外（既存パターンの追加適用）
