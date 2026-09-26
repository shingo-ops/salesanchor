# recon — distui-01 配信先管理 UI（CC_TASK_DISTUI-01）

## 調査範囲

TCG 配信先管理画面の新規実装。既存 BE API（CRUD + preview + run）を FE から操作できる
super-admin 専用ページを追加する。

## BE — ルーター・サービス確認

`backend/app/routers/tcg_distribution.py:1-209`

- `GET /tcg/distribution/targets` — 一覧取得（実在）
- `POST /tcg/distribution/targets` — 新規作成（実在）
- `PUT /tcg/distribution/targets/{id}` — 更新（実在）
- `DELETE /tcg/distribution/targets/{id}` — 論理削除（実在）
- `GET /tcg/distribution/preview` — 配信候補プレビュー（実在）
- `POST /tcg/distribution/run` — 全件配信（実在）
- `POST /tcg/distribution/run/{target_id}` — 個別配信（実在）
- `GET /tcg/distribution/verify-access` — 追加: スプレッドシートアクセス確認

`backend/app/services/tcg_distribution_svc.py:1-762`

- `_build_gspread_client()` — SA 認証クライアント構築（実在）
- `_verify_spreadsheet_id()` — スプレッドシートアクセス確認（実在）
- `verify_spreadsheet_access()` — 追加: 新エンドポイント向け wrapper

## BE — main.py 登録確認

`backend/app/main.py` にて `tcg_distribution.router` 登録済み（新規変更不要）。

## FE — 既存パターン確認

`frontend/src/pages/super-admin/TcgSupplierQualityPage.tsx:1` を参照し、
ページ構成・`useSuperAdmin()` フック・`PageLayout` の使い方を踏襲。

## i18n キー確認

`frontend/src/locales/ja.json` および `frontend/src/locales/en.json` に
`distributionTarget.*` キーを追加（ADR-027 準拠）。

## 制約（変更禁止）

- `analysis_results` テーブル・GAS プロジェクト・`tcg_products` は触らない
- `frontend/src/components/` 共有コンポーネントは変更しない
