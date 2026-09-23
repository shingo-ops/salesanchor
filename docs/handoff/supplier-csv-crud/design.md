# Phase 3 設計 — 仕入元マスタ CSV エクスポート・インポート

**対象ADR**: ADR-155
**recon**: docs/handoff/supplier-csv-crud/recon.md
**日付**: 2026-09-19（Phase 2 統合後に再設計）
**担当**: Planner

---

## 外部・過去事例の参照と我々への応用

- 内部先例1: 商品マスタCSV（TcgProductImportPanel + tcg_product_import.py）— preview/commit 2段階パターン、SHA-256ダイジェスト検証。そのまま踏襲する
- 内部先例2: supplier_aliases CSV（super_admin_aliases.py）— dry_run フラグ方式、行番号付きエラー。エラー報告フォーマットを踏襲する
- ADR-155: 商品マスタSSOT方針 — CSV+App UIのみ、migrationsは構造変更のみ。仕入元マスタも同方針を適用する

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| 中央管理: CSVエクスポートでtenant_id IS NULLの仕入元のみダウンロードされる | `pytest tests/test_super_admin_suppliers.py::test_export_csv` |
| 中央管理: CSVインポートのプレビューでバリデーション結果が返る | `pytest tests/test_super_admin_suppliers.py::test_import_preview` |
| 中央管理: CSVインポートの確定でtenant_id=NULLのデータが更新される | `pytest tests/test_super_admin_suppliers.py::test_import_commit` |
| テナント用: CSVエクスポートで自テナント(tenant_id=自分)の仕入元のみダウンロードされる | `pytest tests/test_suppliers.py::test_export_csv` |
| テナント用: CSVインポートの確定でtenant_id=自テナントのデータが更新される | `pytest tests/test_suppliers.py::test_import_commit` |
| 不正CSVでバリデーションエラーが行番号付きで返る | `pytest tests/test_super_admin_suppliers.py::test_import_validation_errors` |
| supplier_codeが一致する行は更新、新規はINSERT | `pytest tests/test_super_admin_suppliers.py::test_import_upsert` |
| テナント用インポートで他テナントのデータが見えない・書き換えられない | `pytest tests/test_suppliers.py::test_import_tenant_isolation` |
| UIにExportボタンが表示される（中央管理・テナント両方） | Evaluator（Playwright） |
| UIにImportボタンが表示され、インポートUIに遷移する | Evaluator（Playwright） |
| i18n: supplierCsv.* キーが ja.json と en.json に同一キーで存在する | CI: i18n チェック |
| UI部品: デザインシステムの金型のみ使用（ハードコード禁止） | CI: ui-governance gate |

---

## 技術 How・KPI

### バックエンドエンドポイント

**中央管理用（public.suppliers WHERE tenant_id IS NULL）:**

| メソッド | パス | 機能 |
|---------|------|------|
| GET | /api/v1/super-admin/suppliers/export | CSVエクスポート（tenant_id IS NULLのみ） |
| POST | /api/v1/super-admin/suppliers/import/preview | CSV検証・プレビュー（書き込みなし） |
| POST | /api/v1/super-admin/suppliers/import/commit | CSV確定・書き込み（tenant_id=NULL固定） |

**テナント用（public.suppliers WHERE tenant_id = :tenant_id）:**

| メソッド | パス | 機能 |
|---------|------|------|
| GET | /api/v1/suppliers/export | CSVエクスポート（自テナントのみ） |
| POST | /api/v1/suppliers/import/preview | CSV検証・プレビュー |
| POST | /api/v1/suppliers/import/commit | CSV確定・書き込み（tenant_id=自テナント固定） |

### CSVカラム（エクスポート・インポート共通）

| カラム | エクスポート | インポート必須 | 備考 |
|--------|-----------|-------------|------|
| supplier_code | ○ | ○（更新時の一致キー） | 新規作成時は空欄可（自動生成） |
| name | ○ | ○ | 仕入元名 |
| supplier_type | ○ | - | デフォルト: corporate |
| line_name | ○ | - | LINE照合用名前 |
| contact_name | ○ | - | 連絡先名 |
| email | ○ | - | メール |
| phone | ○ | - | 電話 |
| postal_code | ○ | - | 郵便番号 |
| prefecture | ○ | - | 都道府県 |
| city | ○ | - | 市区町村 |
| address1 | ○ | - | 住所1 |
| address2 | ○ | - | 住所2 |
| notes | ○ | - | 備考 |
| is_active | ○ | - | デフォルト: true |

**CSVに含めないカラム:**
- id — 内部PK（エクスポートのみ参考表示可）
- tenant_id — エンドポイントが自動設定（中央管理=NULL、テナント=自テナント）
- created_at, updated_at — システム自動管理

### テナント隔離（SSOT遵守）
- エクスポート: `WHERE tenant_id = :tenant_id` で自テナントのみ
- インポート: INSERT/UPDATEに `tenant_id = :tenant_id` を強制付与
- UPSERTの一致キー: `supplier_code AND tenant_id` の複合条件（他テナントのsupplier_codeと衝突しない）
- 中央管理: tenant_id IS NULL 固定

### バリデーション（商品マスタCSVと同じ）
- ファイル形式: .csv のみ
- エンコーディング: UTF-8（BOM付きも受け入れ）
- サイズ上限: 2MB
- 必須カラム: name（新規作成時）、supplier_code（更新時）
- 行ごとエラー: L{行番号}: {エラー内容} 形式
- UPSERT: supplier_code + tenant_id の複合一致で判定

### 安全装置
- SHA-256ダイジェスト: preview で返したハッシュを commit で検証（改ざん防止）
- preview は書き込みなし
- 権限チェック: 中央管理は require_super_admin、テナント用は suppliers.create/update 権限
- テナント隔離: tenant_id を強制付与。CSVで指定不可

### フロントエンド

**中央管理（SuppliersAdminTab 内）:**
- ヘッダーに Export ボタン追加（api.getBlob でCSVダウンロード）
- ヘッダーに Import ボタン追加（インポートモーダル or 専用ページへ遷移）
- インポートUI: 商品マスタと同じ2段階（ファイル選択→プレビュー→確定）

**テナント用（SuppliersPage）:**
- 同上（テナント用エンドポイントを呼ぶ）

**i18n:**
- supplierCsv.* 名前空間を ja.json / en.json に追加
- productCsv.* のキー構造を踏襲

---

## 弊害・トレードオフ

- UPSERT のため、supplier_code を誤入力すると意図しないレコード更新 → プレビューで「新規N件・更新M件」を明示、確定前に確認
- CSVの文字コード問題（Shift_JIS等）→ UTF-8 のみ受け入れ、エラーメッセージで案内
- tenant_id をCSVに含めない → テナント間のデータ移行にはCSVを使えない（意図的。移行はPO判断のDB操作で行う）

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| Sprint 1 | Backend: 中央管理用 export + import(preview/commit) + テスト | Generator |
| Sprint 2 | Backend: テナント用 export + import(preview/commit) + テスト（テナント隔離テスト含む） | Generator |
| Sprint 3 | Frontend: 中央管理 SuppliersAdminTab に Export/Import UI + i18n | Generator |
| Sprint 4 | Frontend: テナント用 SuppliersPage に Export/Import UI + i18n | Generator |

---

## 継続

- 完了後の監視: CSVインポートのエラー率（初期は手動確認）
- 次フェーズへの引き継ぎ: 大量インポート対応（1000件超）が必要になれば非同期処理を検討

---

## 維持の仕組み

守り手: CI pytest（バックエンドCSVエンドポイント）+ ui-governance gate（フロントエンド金型遵守）+ i18n チェック（キー同一性）+ .github/workflows/migration-guard.yml チェック9（supplier_channels.supplier_id 保護）

テナント隔離はpytestの専用テスト（test_import_tenant_isolation）で保護。
