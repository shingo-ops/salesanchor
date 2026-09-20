# design: master-csv-import-export

**recon**: docs/handoff/master-csv-import-export/recon.md

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
- ADR-072: `docs/adr/ADR-072-tenant-schema-prefix-enforcement.md`
- ADR-144: `docs/adr/ADR-144-ui-component-governance.md`

## 弊害・リスク
- DB migration なし（既存テーブルへの新エンドポイント追加のみ）
- マッチキーの選択: units/conditions=`code`、status_master=`status_id`、note_master=`label_ja` — label_ja は一意であることを前提

## 外部・過去事例の参照と我々への応用
- 社内事例: `backend/app/routers/super_admin_suppliers.py` — SHA-256 digest preview/commit パターン。同じ構造を4テーブルに適用。
- 社内事例: `frontend/src/pages/super-admin/SupplierImportPage.tsx` — preview→diff表示→commit フロー。同パターンを8ページに複製。

## 維持の仕組み
- 守り手: .github/workflows/test.yml（Backend Tests / pytest-run が毎 PR で suppliers_csv パターン互換性を検査）
- ruff CI: Python コードの品質チェック（毎PR）
- i18n キーパリティ: ja.json / en.json のキー数一致チェック（CI）
- ADR-072 準拠: backend/app/routers に write エンドポイントを追加する際は reset_tenant_context 必須（このファイルとチェックリストで継続担保）

## 設計仕様書
対象外（既存パターンの追加適用）
