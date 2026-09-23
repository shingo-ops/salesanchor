# recon: LINE取り込み自動化 3改修

## 対象ファイル調査

### 変更1: フロントエンド already_imported 表示
- `frontend/src/pages/super-admin/TcgLineImportPage.tsx:418-460` — already_imported の警告色バナー
  - `result.status === "already_imported"` 時に `var(--color-warning-border)` / `var(--color-warning-bg)` を使用
  - `t("tcgLineImport.alreadyImported")` キーでタイトル表示

### 変更2: 仕入元自動登録
- `backend/app/services/tcg_line_import_svc.py:215-265` — `resolve_suppliers()`: display_name の完全一致検索、unresolved リストを返す
- `backend/app/services/tcg_line_import_svc.py:475-729` — `import_line_export()`: unresolved_count ≥ 1 で pending_review 分岐
- `backend/app/routers/tcg_line_import.py:482-513` — resolve action='create' の supplier 作成ロジック（参照元）
  - `INSERT INTO public.suppliers RETURNING id` → `SP-{id:05d}` 採番
  - `INSERT INTO tenant_004.supplier_channels (channel='line')`

### 変更3: 解析後自動配信
- `backend/app/tasks/tcg_extraction.py:296-319` — `_run_recorded_extraction()` の step 6: `TCG_AUTO_ANALYZE=1` のみ解析実行
- `backend/app/services/tcg_distribution_svc.py:644-` — `run_distribution()`: async、安全装置 #8/#8b/#8c あり
  - 安全装置 #8b: `extraction_jobs` に pending/running/extracted が残っていれば配信スキップ
  - 引数: `db: AsyncSession`, `target_id: str | None = None`

### 既存テスト
- `backend/tests/test_tcg_line_import.py:918-988` — pending_review フローのテスト3件（変更対象）

## ADR確認
- ADR-027（i18n）: UI文字列は t() 経由、ハードコード日本語禁止
- ADR-072（reset_tenant_context）: write endpoint の db.commit() 直後に必要 — 本 PR は既存エンドポイントを変更せず、新規書き込みは import_line_export 内（サービス層）のため対象外
