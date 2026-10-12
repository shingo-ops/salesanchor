# design: note-master-frontend

## 参照 ADR
- ADR-027: i18n 強制
- ADR-072: reset_tenant_context after writes
- ADR-144: UI ガバナンス

## 外部・過去事例の参照と我々への応用
同プロジェクト内のパターン踏襲:
- `backend/app/routers/super_admin_suppliers.py` / `frontend/src/pages/super-admin/components/SupplierMasterPanel.tsx` — super-admin CRUD の実装パターン
- `backend/app/routers/suppliers.py` — tenant CRUD + reset_tenant_context の実装パターン
- `backend/app/schemas/central_masters.py` — Pydantic スキーマ追加パターン
- `frontend/src/pages/units/UnitsPage.tsx` — テナント側管理ページの実装パターン
応用: tcg_note_master の tenant_id 分離ロジック・UI 構造を同パターンで実現する。

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
- `migrations/20260920_060000_note_master_tenant_id.sql` — public.tcg_note_master に tenant_id INTEGER を追加

### バックエンド（新規ファイル）
- `backend/app/routers/super_admin_note_master.py` — tenant_id IS NULL 対象の CRUD
- `backend/app/routers/note_master.py` — GET は NULL + current 両方、POST/PATCH/DELETE はテナント個別のみ

### フロントエンド（新規ファイル）
- `frontend/src/pages/super-admin/components/NoteMasterPanel.tsx` — AnalysisRulesPage のサイドバーパネル（super-admin 向け）
- `frontend/src/pages/note-master/NoteMasterPage.tsx` — 管理センター内テナント向けページ

### フロントエンド（変更ファイル）
- `frontend/src/pages/super-admin/components/AnalysisRulesSidebar.tsx` — "note-master" キーを型ユニオンに追加
- `frontend/src/pages/super-admin/AnalysisRulesPage.tsx` — NoteMasterPanel の条件レンダリング追加
- `frontend/src/pages/management-center/ManagementCenterPage.tsx` — data セクションに note-master エントリ追加
- `frontend/src/App.tsx` — management-center/note-master ルート追加

## 維持の仕組み
守り手: shingo-ops（PO）

同カテゴリの他マスタ（units, status_master, conditions）と同一パターンを踏襲しているため、
将来の変更は同パターンを参照することで一貫性を保てる。

## 弊害・注意事項
- migration ファイル名 20260920_040000 は既存と衝突 → 060000 で回避
- migration-test.yml に tcg_note_master の CREATE TABLE スタブを追加が必要
- 既存の load_note_master() 解析ロジックは変更なし
