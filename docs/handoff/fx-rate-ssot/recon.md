# recon.md — 為替レート SSOT 調査

> 作成: 2026-06-28 | STANDARD-WORKFLOW Phase ① recon | 担当: Hikky-dev

---

## 1. 既存の FX レート取得実装（SSOT 前）

### 外部API呼び出しサービス（既存・未改変）

`backend/app/services/fx_rate.py:1-40`
- `open.er-api.com/v6/latest/JPY` を httpx で同期呼び出し
- JPY 基準レートを反転して `1外貨 = N円` に変換: `jpy_per_currency = 1.0 / rate`
- 戻り値: `{"currency": "USD", "rate": float, "fetched_at": str}`
- `FX_API_KEY = os.getenv("FX_RATE_API_KEY", "")` — 現在無料プラン（キーなし）

### 請求書での使用（既存・未改変）

`backend/app/routers/invoices.py` 内の `fetch_fx_rate` および `get_fx_rate` 呼び出し:
- 請求書作成時にユーザーが手動入力した FX レートを使用
- SSOT テーブルとは独立した系統。**本PRでは一切変更しない。**

### 既存 SSOT テーブル

**なし。** 為替レートを永続化するテーブルは存在しなかった。

---

## 2. 定期実行インフラ（Celery Beat）

`backend/app/celery_app.py:1-100`
- `celery_app.py` に `beat_schedule` が定義済み（13エントリ）
- `timezone = "Asia/Tokyo"` — crontab の hour は JST
- `include` リストにタスクモジュールを列挙する規約
- 同期タスクのパターン: `backend/app/tasks/maintenance.py`（`SET app.is_operator`）

---

## 3. RLS 書き込みポリシーのパターン

`migrations/20260627_120000_add_tenant_features_table.sql:50-70`（直前 migration）:
- `public` テーブルへの書き込みは `app.is_operator = 'true'` が必要
- Celery タスクでは `session.execute(text("SET app.is_operator = 'true'"))` を UPSERT 前に実行

---

## 4. 既存 ADR 検索結果

`git grep -i "fx.rate\|為替" docs/adr/` → 0件（為替レート専用 ADR なし）

- ADR-021 (`docs/adr/ADR-021-order-management.md`): 請求書・注文管理。FX に言及なし。
- ADR-101 (`docs/adr/ADR-101-sa-quotation-invoice-generation.md`): 見積・請求生成。FX 入力欄は存在するが SSOT 設計言及なし。
- **→ 本機能は新設。専用 ADR なし。**

---

## 5. updated_at トリガーパターン

`migrations/070_add_spreadsheet_phase.sql:1-20`:
- `CREATE OR REPLACE FUNCTION` → `DROP TRIGGER IF EXISTS` → `CREATE TRIGGER` の3ステップ
- 本 migration でも同パターンを踏襲（冪等）
