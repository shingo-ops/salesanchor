# ADR-148: 為替レート SSOT（public.app_fx_rates）

| 項目 | 内容 |
|------|------|
| **状態** | Accepted |
| **日付** | 2026-06-28 |
| **担当** | Hikky-dev |

---

## 背景

請求書 UI では USD/JPY 為替レートをユーザーが手動入力していた。将来的に1日2回の自動取得・全テナント共通参照を実現するために SSOT テーブルが必要になった。

## 決定

- `public.app_fx_rates` テーブルを新設し、Celery Beat が JST 6:00 / 18:00 に自動 UPSERT する
- 全テナント共通情報のため public スキーマに配置し、RLS で読み取り全許可・書き込み operator 限定とする
- 外部API呼び出し実装は既存の `backend/app/services/fx_rate.py` を再利用・無改変とする
- 既存の請求書 FX 入力フローは独立系統のまま維持する（本 ADR の対象外）

## 結果

- Celery Beat スケジュールに2エントリ追加（JST 6:00 / 18:00）
- `GET /api/v1/fx-rate/{currency}` でログイン済み全ユーザーが参照可能
- `POST /api/v1/super-admin/fx-rate/refresh` で is_super_admin が手動更新可能
- super-admin メニューに `/super-admin/fx-rate` ページを追加

## 関連

- `docs/handoff/fx-rate-ssot/recon.md`
- `docs/handoff/fx-rate-ssot/design.md`
- ADR-072（RLS operator コンテキスト）

## 追記（2026-10-01）：読み取り API の住所変更

本番調査（設計担当・2026-10-01）で、本番 `app.routes` に `GET /api/v1/fx-rate/{currency}` が2系統登録されていることが判明した（index 181: `app.routers.invoices.fetch_fx_rate`、index 484: `app.routers.fx_rate_admin.get_fx_rate`、いずれも `backend/app/main.py` 経由で同一パス）。`invoices.fetch_fx_rate` が先に登録されるため全リクエストに応答し、本 ADR の SSOT 読み取りエンドポイント（`fx_rate_admin.get_fx_rate`）は到達不能だった。

結果として `frontend/src/pages/super-admin/components/LlmUsageSection.tsx` と `frontend/src/pages/super-admin/FxRatePage.tsx` は常に `invoices.fetch_fx_rate` のレスポンス（`rate` フィールドのみ、`rate_jpy` を含まない）を受け取り、使用量タブは為替未取得として USD フォールバック表示になっていた（PO 確認スクリーンショット 2026-10-01 20:02 JST）。

対応として、本 ADR の SSOT 読み取りエンドポイントのパスを `GET /api/v1/fx-rate/{currency}` から `GET /api/v1/fx-rates/{currency}`（複数形）に変更した。`app.routers.invoices.fetch_fx_rate`（`GET /api/v1/fx-rate/{currency}`、ライブ取得・`invoices.view` 権限）は無変更のまま別系統として維持する。`POST /api/v1/super-admin/fx-rate/refresh` もパス変更なし。

- `backend/app/routers/fx_rate_admin.py`
- `backend/app/main.py`
- `frontend/src/pages/super-admin/FxRatePage.tsx`
- `frontend/src/pages/super-admin/components/LlmUsageSection.tsx`
- `docs/handoff/fx-rate-route-collision/recon.md`
- `docs/handoff/fx-rate-route-collision/design.md`
- ADR-1004
