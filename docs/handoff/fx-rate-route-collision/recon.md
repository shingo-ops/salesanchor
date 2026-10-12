# recon — fx-rate-route-collision

**仕事名**: fx-rate-route-collision
**日付**: 2026-10-01
**対象ADR**: ADR-148
**担当**: Opus（設計）

---

## 事実（本番調査・設計担当・2026-10-01）

- 本番 `app.routes` に GET `/api/v1/fx-rate/{currency}` が2系統登録されている。
  - index 181: `app.routers.invoices.fetch_fx_rate`（`invoices.view` 権限必須、外部APIライブ取得、`{"currency","rate","fetched_at"}` を返す）
  - index 484: `app.routers.fx_rate_admin.get_fx_rate`（ADR-148 SSOT 読み取り、`public.app_fx_rates`、`{currency, rate_jpy, fetched_at, updated_at}` を返す）
- `invoices` ルーターが先に登録されるため全リクエストに応答し、`fx_rate_admin.get_fx_rate` は到達不能。
- 結果: `frontend/src/pages/super-admin/components/LlmUsageSection.tsx`（`/fx-rate/USD` を呼び `rate_jpy` を期待）は本番で USD フォールバック表示になっていた（PO スクリーンショット 2026-10-01 20:02 JST「為替レートを取得できないため、ドルで表示しています」）。`frontend/src/pages/super-admin/FxRatePage.tsx` も同様に `/fx-rate/USD` を呼び `rate_jpy` を期待していた。

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `backend/app/routers/invoices.py:1021` | `@router.get("/fx-rate/{currency}", dependencies=[Depends(require_permission("invoices.view"))])` — ライブ取得、`rate` フィールド |
| `backend/app/routers/fx_rate_admin.py:42` （変更前は `"/fx-rate/{currency}"`、変更後は `"/fx-rates/{currency}"`） | ADR-148 SSOT 読み取り、`rate_jpy` フィールド |
| `backend/app/main.py:54` | `fx_rate_admin` ルーター import コメント（パス記載を更新） |
| `backend/app/main.py:634,636` | `app.include_router(fx_rate_admin.router, prefix="/api/v1", ...)` — invoices ルーターより後に登録されるため衝突で埋もれていた |
| `frontend/src/pages/quote-detail/QuoteDetailPage.tsx:19-22,105` | `interface FxRateResult { rate: number }`、`api.get<FxRateResult>(\`/fx-rate/${quote.currency}\`)` — `invoices.fetch_fx_rate` 呼び出し。**変更対象外**（`rate` を読む） |
| `frontend/src/pages/super-admin/FxRatePage.tsx:20-24,40` | `interface FxRate { rate_jpy: number }`、`api.get<FxRate>("/fx-rate/USD")` → `/fx-rates/USD` に変更 |
| `frontend/src/pages/super-admin/components/LlmUsageSection.tsx:132-137,394` | `interface FxRate { rate_jpy: number }`、`api.get<FxRate>("/fx-rate/USD")` → `/fx-rates/USD` に変更 |
| `frontend/src/pages/super-admin/components/LlmUsageSection.test.tsx:96-101` | `mockApiWithFx` が `url.startsWith("/fx-rate/")` を判定 → `/fx-rates/` に変更 |
| `backend/tests/test_fx_rate_admin_router.py:1-129`（新規） | ルート重複なし検証・パス解決検証・`rate_jpy` 返却検証・404検証 |

---

## 事前チェック（pre-check: 全呼び出し元の洗い出し）

コマンド: `git grep -n -e "fx-rate/" -e "fx-rate\`" -e "/fx-rate" origin/main -- frontend/src backend/app backend/tests`

| 呼び出し元 | 読むフィールド | 判定 |
|-----------|---------------|------|
| `frontend/src/pages/quote-detail/QuoteDetailPage.tsx:105` | `rate`（`FxRateResult`） | 無変更（`invoices.fetch_fx_rate` 宛） |
| `frontend/src/pages/super-admin/FxRatePage.tsx:40` | `rate_jpy`（`FxRate`） | `/fx-rates/USD` に変更 |
| `frontend/src/pages/super-admin/components/LlmUsageSection.tsx:394` | `rate_jpy`（`FxRate`） | `/fx-rates/USD` に変更 |
| `frontend/src/pages/super-admin/components/LlmUsageSection.test.tsx:99` | モック判定文字列 | `/fx-rates/` に変更 |
| `backend/app/routers/invoices.py:1022` | ルート定義自体（`rate` を返す） | 無変更 |

曖昧な呼び出し元なし。全件上記の通り判定。

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | FxRatePage.tsx / QuoteDetailPage.tsx 専用のフロントテストファイルが存在するか | `find frontend/src -iname "*FxRatePage*test*" -o -iname "*QuoteDetail*test*"` | ✅ 解消済み（存在しない。更新対象なし） |
| 2 | backend/tests に fx_rate_admin 既存テストがあるか | `git grep -ln "fx_rate_admin\|fx-rate" origin/main -- backend/tests` | ✅ 解消済み（存在しない。新規作成） |

**未解決ゼロ確認**: 全て解消済み

---

## 補足

- `backend/app/services/fx_rate.py`（外部API呼び出し実装）は本件の対象外。`invoices.fetch_fx_rate` と `fx_rate_admin.refresh_fx_rate` の両方が利用するが、どちらも無変更。
- `POST /api/v1/super-admin/fx-rate/refresh`（`fx_rate_admin.py:78`）はパス変更なし（衝突していないため）。
