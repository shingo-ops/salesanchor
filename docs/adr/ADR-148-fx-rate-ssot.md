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

## 追記（2026-10-03）：履歴テーブル新設（SSOT の UPSERT 方式を履歴方式へ移行）

### なぜ

LLM 使用量ダッシュボード（ADR-1004）では、各 LLM 呼び出し発生時点の USD/JPY レートで JPY 換算したい。しかし現行 `public.app_fx_rates` は `currency` を PRIMARY KEY に UPSERT する設計（`migrations/20260628_170000_add_app_fx_rates.sql`）のため、Celery Beat が1日2回取得するたびに前回のレートが上書きで失われる。本番には現在 USD の1行のみが残っており（`rate_jpy=157.8034`, `fetched_at=2026-10-03 09:00Z`）、これが人為的に取得できる最古のレートである。一方 `llm_usage_events`（ADR-1004）には 2026-09-27 14:12Z からの 1547 件が既に蓄積されており、現行方式のままでは過去分を当時のレートで換算できない。

### 決定

- `public.app_fx_rate_history` を新設する（追記専用・PRIMARY KEY `(currency, fetched_at)`）。既存 `app_fx_rates` とは独立したテーブルとして追加し、既存の読み取り/書き込み経路は本 PR（PR-A）では無改変。
- 書き込み: Celery Beat（`backend/app/tasks/fx_rate_updater.py`）と手動更新 API（`POST /api/v1/super-admin/fx-rate/refresh`）が、取得ごとに `app_fx_rate_history` へ `INSERT ... ON CONFLICT (currency, fetched_at) DO NOTHING` で追記する（PR-B で実装）。
- 読み取り: `GET /api/v1/fx-rates/{currency}` は `app_fx_rate_history` の最新行（`fetched_at` 最大）を返す（PR-B でレスポンス形状は維持したまま実装切替）。
- 換算: LLM 使用量ダッシュボードは各イベントの `occurred_at` 以前で最新の `fetched_at` を持つ履歴行のレートを使う。`occurred_at` が最初の履歴行より古い場合は、取得可能な最古の行（上記の1行）を使い、UI 上はフォールバック使用であることを明示する（PR-B）。
- 移行順序: 本 PR（PR-A）でテーブルのみ新設し、既存 `app_fx_rates` の現在値をシード INSERT で取り込む。PR-B で書き込み/読み取りを `app_fx_rate_history` に切替える。切替完了後は `app_fx_rates` は未使用となるが、**DROP は本 ADR では決定しない**。DROP を行う場合は別途 PO 自身の GO を得て実施する。

### 関連

- `migrations/20261003_100000_create_app_fx_rate_history.sql`
- `docs/handoff/fx-rate-history/recon.md`
- `docs/handoff/fx-rate-history/design.md`
- ADR-1004（LLM 使用量台帳）
- ADR-135 / ADR-136（本番投入・危険PRのGO手順）
