# design.md — 為替レート SSOT 設計

> 作成: 2026-06-28 | STANDARD-WORKFLOW Phase ③ 設計 | 担当: Hikky-dev

---

## KGI（PO が画面・出力で ○× 一義判定できる粒度）

| ID | KGI | 検証方法 |
|----|-----|---------|
| F1 | `public.app_fx_rates` テーブルが本番DBに存在する | `SELECT to_regclass('public.app_fx_rates')` → 非NULL |
| F2 | Celery Beat が JST 6:00 / 18:00 に UPSERT を実行する | `SELECT * FROM public.app_fx_rates;` で `fetched_at` が更新される |
| F3 | 外部API障害時に既存行が壊れない | Celery ワーカーログに warning のみ・テーブル行が消えない |
| F4 | `GET /api/v1/fx-rate/USD` がログイン済みユーザー全員に rate_jpy を返す | curl で 200 / 未取得時 404 |
| F5 | `/super-admin/fx-rate` 画面で is_super_admin ユーザーがレート確認・手動更新できる | ブラウザで確認 |

---

## 設計決定

### テーブル配置: `public.app_fx_rates`（テナントスキーマではない）

- 為替レートは全テナント共通の公開情報
- テナントスキーマに置くと RLS テナント分離の管理コストが発生する
- `public` + `FORCE RLS` + 読み取り全許可ポリシー で適切な分離

### 書き込みは operator コンテキストのみ

- 一般ユーザーが意図せず FX レートを変更できない
- Celery タスク: `SET app.is_operator = 'true'` → UPSERT
- 手動更新 API: `require_super_admin` Depends（FastAPI ルーター）

### 既存 fx_rate.py を再利用・無改変

- `backend/app/services/fx_rate.py` は既に open.er-api.com 呼び出しと JPY 反転を実装済み
- Celery タスク / 手動更新 API ともに `get_fx_rate("USD")` を呼ぶだけ
- invoices.py の既存フローには一切手を加えない（独立系統を維持）

### F3 フォールバック: non-fatal 設計

- `get_fx_rate()` が `None` または例外 → `logger.warning` + `return`（UPSERT しない）
- DB UPSERT 例外 → `session.rollback()` + `logger.warning`（前回行を維持）
- Celery タスクは正常終了（Celery の retry を発火させない）

---

## 検証方法（KPI）

| 基準 | 検証方法 |
|------|---------|
| migration 冪等 | CI「マイグレーション全件ドライラン（実DB）」PASS |
| invoices.py 未接触 | `git diff origin/main...HEAD -- backend/app/routers/invoices.py backend/app/services/fx_rate.py` → 空 |
| RLS 読み取り全許可 | `CREATE POLICY ... FOR SELECT USING (true)` を migration で確認 |
| RLS 書き込み operator のみ | `current_setting('app.is_operator', true) = 'true'` を migration で確認 |

---

## 外部事例欄

- **Stripe / Wise**: FX レートを内部 SSOT テーブルに保持し、ユーザー向け API は SSOT から読む設計が標準
- **Django Money / py-moneyed**: テーブル1行 per 通貨ペア、定期ジョブで UPSERT するパターンを推奨

---

## 触らないファイル

- `backend/app/services/fx_rate.py` — 外部API呼び出し実装（変更なし）
- `backend/app/routers/invoices.py` — 請求書 FX 入力フロー（変更なし）
- 既存 Celery タスク群（`maintenance.py` 等）
