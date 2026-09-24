# recon: rule-edit-drawer

## 既存 ADR 検索結果

- `docs/adr/ADR-027-ui-internationalization.md` — 全 UI 文字列 t("key") 強制
- `docs/adr/ADR-144` — UI 金型コンポーネント強制（生 select / 生 input 禁止）

## 調査ファイル一覧（file:line）

| ファイル | 確認内容 |
|---------|---------|
| `frontend/src/pages/super-admin/components/RuleCreateDrawer.tsx:1` | 既存の作成専用ドロワー全体構造 |
| `frontend/src/pages/super-admin/components/RuleManagementPanel.tsx:1` | 既存パネル：ConfirmModal + RuleCreateDrawer 使用箇所 |
| `frontend/src/pages/super-admin/components/RuleManagementPanel.tsx:88-105` | handleRowClick → setToggleTarget / handleToggleConfirm（削除対象） |
| `frontend/src/pages/super-admin/components/RuleManagementPanel.tsx:208-220` | ConfirmModal + RuleCreateDrawer レンダー（削除対象） |
| `frontend/src/hooks/useRecordDrawer.ts:1` | 既存編集ドロワーフック（今回は不採用：型が柔軟すぎて RuleEntry 固定の方が明確） |
| `frontend/src/pages/bots/BotsPage.tsx:1` | useRecordDrawer 参照実装 |
| `backend/app/routers/super_admin_status_master.py:1` | PATCH /super-admin/status-master/{id} 実装確認 |
| `backend/app/routers/super_admin_status_master.py:162-195` | PATCH エンドポイント：enabled false→true に test gate あり |
| `frontend/src/locales/ja.json:4416` | ruleManagement セクション |
| `frontend/src/locales/en.json:4416` | ruleManagement セクション |
| `frontend/src/components/Button.tsx:1` | variant: primary / secondary / ghost / danger / outline / tab を確認 |

## PATCH エンドポイント仕様（事実）

- `PATCH /super-admin/status-master/{id}` は `_UPDATABLE` フィールドのみ受け付ける
- `_UPDATABLE = {"status_id", "canonical", "search_pattern", "exclude_pattern", "priority", "enabled", "note", "match_type", "effect"}`
- `enabled false→true` には backend 側で test gate チェックあり（最新テスト run が passed でなければ 409）
- `enabled false` は backend の test gate を通らずに設定できる

## 変更スコープ

### 新規追加
- `frontend/src/pages/super-admin/components/RuleDrawer.tsx` — 新規作成・編集兼用ドロワー

### 変更
- `frontend/src/pages/super-admin/components/RuleManagementPanel.tsx` — ConfirmModal 削除 / RuleCreateDrawer → RuleDrawer 切り替え
- `frontend/src/locales/ja.json` — `ruleManagement.edit.*` キー追加
- `frontend/src/locales/en.json` — `ruleManagement.edit.*` キー追加

### 触らないファイル
- `backend/` — PATCH エンドポイントは既存のまま
- `frontend/src/pages/super-admin/components/RuleCreateDrawer.tsx` — 残置（既存の import を壊さないため）
- `frontend/src/pages/super-admin/components/RuleTestPanel.tsx` — 変更なし
