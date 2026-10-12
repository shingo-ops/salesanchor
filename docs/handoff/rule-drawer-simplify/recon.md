# recon.md — rule-drawer-simplify

## 変更対象ファイル (file:line)

| ファイル | 行 | 内容 |
|---|---|---|
| `backend/app/schemas/central_masters.py:580-581` | TcgStatusMasterCreate | `status_id: Optional[str] = None` に変更 |
| `backend/app/routers/super_admin_status_master.py:165-175` | create_status_master | status_id 自動採番ロジック追加 |
| `frontend/src/pages/super-admin/components/RuleCreateDrawer.tsx:1-274` | RuleCreateDrawer | フォーム簡略化・テストゲート追加 |
| `frontend/src/locales/ja.json:4488-4511` | ruleManagement.create | キー整理・新規キー追加 |
| `frontend/src/locales/en.json:4488-4511` | ruleManagement.create | キー整理・新規キー追加 |

## 既存 ADR 検索結果

- `docs/adr/ADR-027-ui-internationalization.md` — i18n 強制（全 UI 文字列 t("key") 経由）
- `docs/adr/ADR-144` — UI ガバナンス（金型コンポーネント必須）
- 今回変更に直接関係する ADR 他なし

## 呼び出し元調査

`RuleCreateDrawer` の参照箇所:
- `frontend/src/pages/super-admin/AnalysisRulesPage.tsx` — `<RuleCreateDrawer open={...} onClose={...} onCreated={...} />` として使用（props インターフェース変更なし）

## 利用する既存 API

- `POST /api/v1/super-admin/status-master` — ルール作成（status_id 省略可に変更）
- `POST /api/v1/super-admin/status-master/preview` — パターンマッチプレビュー（既存）
- `GET /api/v1/super-admin/rule-tests/canonicals` — canonical 一覧取得（既存、`backend/app/routers/rule_test.py:183-196`）
