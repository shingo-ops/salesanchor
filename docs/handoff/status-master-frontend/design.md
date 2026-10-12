# 設計: status-master-frontend

## 目的

public.tcg_status_master テーブルに tenant_id を追加し、単位マスタ（PR #3588）と同じパターンで
フロントエンド・バックエンドを実装する。

## アーキテクチャ

### tenant_id 方式

- NULL = 共用（LINE 在庫解析用・super admin が管理）
- 数値 = テナント個別（管理センターから管理）

### バックエンド

- `backend/app/routers/super_admin_status_master.py`: WHERE tenant_id IS NULL の GET/POST/PATCH/DELETE
- `backend/app/routers/status_master.py`: WHERE tenant_id = :tenant_id の GET/POST/PATCH/DELETE（ADR-072）
- `backend/app/schemas/central_masters.py`: TcgStatusMasterBase/Create/Update/Response

### フロントエンド

- `frontend/src/pages/super-admin/components/StatusMasterPanel.tsx`: 解析管理サブメニュー内パネル
- `frontend/src/pages/status-master/StatusMasterPage.tsx`: 管理センター テナント用ページ

### カラム設計

| カラム | 型 | 説明 |
|--------|----|------|
| status_id | VARCHAR(50) | ステータス識別子 |
| canonical | TEXT | 正規名 |
| search_pattern | TEXT | 検索パターン |
| exclude_pattern | TEXT | 除外パターン |
| priority | INTEGER | 優先度（0-10000） |
| enabled | BOOLEAN | 有効フラグ（soft delete 用） |
| note | TEXT | 備考 |
| match_type | TEXT | REGEX / LITERAL / DEFAULT |
| effect | TEXT | OUTPUT / EXCLUDE |
| tenant_id | INTEGER | NULL=共用 / 数値=テナント個別 |

## 外部・過去事例の参照と我々への応用

単位マスタ（PR #3588）が 2026-09-20 にマージされた実績があり、同一パターンを踏襲する。
テナント分離方式（tenant_id NULL/数値）は複数の既存マスタ（units, conditions 等）で実績済み。
ADR-072 の reset_tenant_context() パターンも units.py で実証済み。

## 維持の仕組み

守り手: Shingo（PO）・Claude Code（実装担当）

- tcg_status_master への変更は本 handoff doc を更新すること
- tcg_analyzer_svc.py の load_status_master() は tenant_id IS NULL で共用データを参照するため変更不要
- 新しいバリデーション値（match_type / effect）を追加する場合は schemas/central_masters.py の `_VALID_*` セットを更新すること
