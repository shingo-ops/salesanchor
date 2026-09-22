# recon: ルールテストUX改善

## 現状
- RuleTestPanel.tsx (origin/main) — テストケース管理+実行機能あり
- RuleManagementPanel.tsx — ルール有効/無効切替に window.confirm 使用
- テストケース追加フォーム — 技術用語（入力テキスト、期待される判定結果）
- ゲートステータス — 裸の Badge のみ、説明なし
- テストケース初期データなし

## 参照
- frontend/src/pages/super-admin/components/RuleTestPanel.tsx — テストパネル
- frontend/src/pages/super-admin/components/RuleManagementPanel.tsx — ルール管理パネル
- frontend/src/components/Card.tsx — Card 金型
- frontend/src/components/Select.tsx — Select 金型
- frontend/src/components/ConfirmModal.tsx — ConfirmModal 金型
- backend/app/routers/rule_test.py — テスト API
- backend/app/routers/super_admin_status_master.py — ルール SSOT API

## 根拠
- ADR-027: i18n 強制
- ADR-144: 金型のみ使用
- tcg_status_master: 9 ルール（LITERAL 5, REGEX 3, DEFAULT 1）
