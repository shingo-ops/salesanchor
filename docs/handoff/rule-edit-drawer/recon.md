# recon: rule-edit-drawer

## 既存 ADR 検索結果

- `docs/adr/ADR-027-ui-internationalization.md` — 全 UI 文字列 t("key") 強制
- ADR-144 — UI 金型コンポーネント強制（生 select / 生 input 禁止）

## 調査ファイル一覧（file:line）

| ファイル | 確認内容 |
|---------|---------|
| `frontend/src/pages/super-admin/components/RuleCreateDrawer.tsx` | 既存の作成専用ドロワー全体構造 |
| `frontend/src/pages/super-admin/components/RuleManagementPanel.tsx` | 既存パネル：ConfirmModal + RuleCreateDrawer 使用箇所 |
| `frontend/src/hooks/useRecordDrawer.ts` | 既存編集ドロワーフック（今回は不採用：型が柔軟すぎて RuleEntry 固定の方が明確） |
| `frontend/src/pages/bots/BotsPage.tsx` | useRecordDrawer 参照実装 |
| `backend/app/routers/super_admin_status_master.py` | PATCH /super-admin/status-master/{id} 実装確認（L162-195） |
| `frontend/src/locales/ja.json` | ruleManagement セクション（L4416） |
| `frontend/src/locales/en.json` | ruleManagement セクション（L4416） |
| `frontend/src/components/Button.tsx` | variant: primary / secondary / ghost / danger / outline / tab を確認 |

## PATCH エンドポイント仕様（事実）

- PATCH /super-admin/status-master/{id} は _UPDATABLE フィールドのみ受け付ける
- _UPDATABLE = {status_id, canonical, search_pattern, exclude_pattern, priority, enabled, note, match_type, effect}
- enabled false→true には backend 側で test gate チェックあり（最新テスト run が passed でなければ 409）
- enabled false は backend の test gate を通らずに設定できる

## 変更スコープ

### 新規追加
- `frontend/src/pages/super-admin/components/RuleDrawer.tsx` — 新規作成・編集兼用ドロワー
- `docs/handoff/rule-edit-drawer/recon.md` — 本ファイル
- `docs/handoff/rule-edit-drawer/design.md` — 設計書

### 変更
- `frontend/src/pages/super-admin/components/RuleManagementPanel.tsx` — ConfirmModal 削除 / RuleCreateDrawer → RuleDrawer 切り替え
- `frontend/src/locales/ja.json` — ruleManagement.edit.* キー追加
- `frontend/src/locales/en.json` — ruleManagement.edit.* キー追加

### 触らないファイル
- backend/ — PATCH エンドポイントは既存のまま
- `frontend/src/pages/super-admin/components/RuleCreateDrawer.tsx` — 残置（削除は別タスク）
- `frontend/src/pages/super-admin/components/RuleTestPanel.tsx` — 変更なし
