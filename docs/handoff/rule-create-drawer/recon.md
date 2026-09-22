# recon — rule-create-drawer

## 対象ファイル

| ファイル | 役割 |
|---------|------|
| `frontend/src/components/Drawer.tsx` | 金型 Drawer コンポーネント（右スライドパネル） |
| `frontend/src/components/TextField.tsx` | 金型 TextField |
| `frontend/src/components/Select.tsx` | 金型 Select |
| `frontend/src/components/Button.tsx` | 金型 Button |
| `frontend/src/components/Badge.tsx` | 金型 Badge |
| `frontend/src/components/Card.tsx` | 金型 Card |
| `frontend/src/components/HeaderButton.tsx` | 金型 HeaderButton（ContentToolbar用） |
| `frontend/src/pages/super-admin/components/RuleManagementPanel.tsx` | 変更対象: 新規作成ボタン追加 + RuleCreateDrawer 組み込み |
| `backend/app/routers/super_admin_status_master.py` | 変更対象: /preview エンドポイント追加 |
| `backend/app/services/tcg_analyzer_svc.py:1077` | SSOT 照合ロジック（_match_status_pattern） |
| `frontend/src/lib/api.ts` | api.post パターン参照 |
| `frontend/src/locales/ja.json` | i18n 追加（ruleManagement.createRule / ruleManagement.create.*） |
| `frontend/src/locales/en.json` | i18n 追加（同上） |

## 既存 ADR 検索結果

- ADR-027: UI i18n 強制 — 適用済み（全文字列 t("key") 経由）
- ADR-144: UIガバナンス — 適用済み（金型コンポーネントのみ使用）

## SSOT 照合ロジック確認

`tcg_analyzer_svc.py:1077` の `_match_status_pattern`:
- DEFAULT → 常に True
- LITERAL → `pattern.lower() in text_val.lower()`（部分一致・大文字小文字無視）
- REGEX → `re.search(pattern, text_val)`（`re.error` は False を返す）

Preview エンドポイントは上記と同一ロジックを使用。
