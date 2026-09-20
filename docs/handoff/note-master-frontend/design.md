# design: note-master-frontend

## 参照 ADR
- ADR-027: i18n 強制
- ADR-072: reset_tenant_context after writes
- ADR-144: UI ガバナンス

## 外部事例
- 同プロジェクト: `super_admin_suppliers.py` / `SupplierMasterPanel.tsx` パターンを踏襲
- 同プロジェクト: `super_admin_status_master.py` / `StatusMasterPanel.tsx` パターンも参照

## KGI / KPI

| 基準 | 検証方法 |
|---|---|
| super-admin が note-master CRUD できる | GET/POST/PATCH/DELETE /api/v1/super-admin/note-master が 200/201/204 を返す |
| テナントが tenant-specific エントリを CRUD できる | GET/POST/PATCH/DELETE /api/v1/note-master が正常動作する |
| shared エントリはテナントが削除できない | DELETE で tenant_id != current → 404 を返す |
| i18n 違反なし | grep hardcoded Japanese = 0 件 |
| TypeScript エラーなし | tsc --noEmit 通過 |

## 設計概要

### DB マイグレーション
- `public.tcg_note_master` に `tenant_id INTEGER` を追加（NULL = 共用）
- インデックス `idx_tcg_note_master_tenant` を追加

### バックエンド
- `super_admin_note_master.py`: tenant_id IS NULL 対象の CRUD
- `note_master.py`: GET は NULL + current 両方、POST/PATCH/DELETE はテナント個別のみ
- ADR-072: POST/PATCH/DELETE 後に `reset_tenant_context(db, tenant_id)` を呼出

### フロントエンド
- `NoteMasterPanel.tsx`: AnalysisRulesPage のサイドバーパネル（super-admin 向け）
- `NoteMasterPage.tsx`: 管理センター内テナント向けページ
- `AnalysisRulesSidebar.tsx`: `"note-master"` キーを型ユニオンに追加
- `AnalysisRulesPage.tsx`: `<NoteMasterPanel />` を条件レンダリング
- `ManagementCenterPage.tsx`: data セクションに `note-master` エントリ追加
- `App.tsx`: management-center/note-master ルート追加

### i18n
- `analysisRules.sidebar.noteMaster` キーを追加
- `analysisRules.noteMaster.*` セクションを追加
- `nav.noteMaster` キーを追加

## 弊害・注意事項
- migration ファイル名 `20260920_040000` は既存と衝突 → `060000` で回避
- migration-test.yml に tcg_note_master の CREATE TABLE スタブを追加が必要
- 既存の `load_note_master()` 解析ロジックは変更なし
