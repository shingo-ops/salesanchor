# Phase 3 設計 — fx-rate-route-collision

**対象ADR**: ADR-148, ADR-1004
**recon**: docs/handoff/fx-rate-route-collision/recon.md
**日付**: 2026-10-01
**担当**: Opus（設計）

---

## 問題

本番 `app.routes` に GET `/api/v1/fx-rate/{currency}` が `app.routers.invoices.fetch_fx_rate`（index 181）と `app.routers.fx_rate_admin.get_fx_rate`（index 484, ADR-148 SSOT）の2系統で同一パス登録されており、先に登録される `invoices` 側が常に応答する。結果、`frontend/src/pages/super-admin/components/LlmUsageSection.tsx`（使用量タブの円換算表示）と `frontend/src/pages/super-admin/FxRatePage.tsx`（為替レート管理画面）が期待する `rate_jpy` フィールドを含むレスポンスを受け取れず、使用量タブは USD フォールバック表示のままになっていた（PO スクリーンショット 2026-10-01 20:02 JST）。

## 変更

- `backend/app/routers/fx_rate_admin.py:42` の ADR-148 SSOT 読み取りルートのパスを `/fx-rate/{currency}` から `/fx-rates/{currency}`（複数形）に変更。認証（`get_current_user`）・レスポンスモデル（`FxRateResponse`）・ロジック（`public.app_fx_rates` からの SELECT）は無変更。
- `backend/app/main.py:54,634` のコメントを新パスに合わせて更新（ルーター登録自体は無変更）。
- `frontend/src/pages/super-admin/FxRatePage.tsx:40` と `frontend/src/pages/super-admin/components/LlmUsageSection.tsx:394` の呼び出し先を `/fx-rates/USD` に変更。
- `frontend/src/pages/super-admin/components/LlmUsageSection.test.tsx:99` のモック判定文字列を `/fx-rates/` に変更。
- `backend/tests/test_fx_rate_admin_router.py`（新規）: ルート重複検証・パス解決検証・`rate_jpy` 返却検証・404検証を追加。
- `docs/adr/ADR-148-fx-rate-ssot.md` に追記セクションを追加（決定本文は無変更）。

## 触らない範囲（スコープ外）

- `backend/app/routers/invoices.py` の `fetch_fx_rate`（`GET /api/v1/fx-rate/{currency}`、単数形のまま）: ライブ取得・`rate` フィールド・`invoices.view` 権限、すべて無変更。
- `frontend/src/pages/quote-detail/QuoteDetailPage.tsx:105`: `invoices.fetch_fx_rate` 宛の呼び出しのため `rate` フィールドのまま、パス変更なし。
- `POST /api/v1/super-admin/fx-rate/refresh`（`fx_rate_admin.py:78`）: 衝突していないためパス変更なし。
- `backend/app/services/fx_rate.py`（外部API呼び出し実装）: 無変更。
- ADR-148 の決定本文（背景・決定・結果セクション）: 無変更、追記のみ。

---

## 外部・過去事例の参照と我々への応用

該当なし：同一パスへの複数ルート登録というフレームワーク（FastAPI/Starlette）レベルの既知挙動（先勝ち）であり、外部事例の参照を要する設計判断ではない。社内では ADR-072（RLS operator コンテキスト）等と同様、まず事実確認（本番 `app.routes` のダンプ）を優先する方針を踏襲した。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| `app.routes` に `fx-rate` を含む (method, path) の重複が無い | `pytest backend/tests/test_fx_rate_admin_router.py::TestRouteCollision::test_no_duplicate_method_path_among_fx_rate_routes -v` |
| GET `/api/v1/fx-rates/{currency}` が `fx_rate_admin.get_fx_rate` に解決される | `pytest backend/tests/test_fx_rate_admin_router.py::TestRouteCollision::test_fx_rates_path_resolves_to_fx_rate_admin_get_fx_rate -v` |
| GET `/api/v1/fx-rate/{currency}`（単数形）は引き続き `invoices.fetch_fx_rate` に解決される | `pytest backend/tests/test_fx_rate_admin_router.py::TestRouteCollision::test_invoices_fx_rate_path_unchanged -v` |
| `public.app_fx_rates` に行があれば `rate_jpy` を含むレスポンスを返す | `pytest backend/tests/test_fx_rate_admin_router.py::TestGetFxRate::test_returns_rate_jpy_from_app_fx_rates -v` |
| 本番で `GET /api/v1/fx-rates/USD` が `rate_jpy` を返す | デプロイ後、PO が本番 `curl`（または super-admin UI）で確認（本PRのスコープ外・PO 確認事項） |
| 使用量タブ（LlmUsageSection）が円表示になる | デプロイ後、PO が `/super-admin` 使用量タブで「ドルで表示しています」の注記が消えることを確認（本PRのスコープ外・PO 確認事項） |
| フロントの型・lintが壊れない | `npx tsc --noEmit` / `npx eslint ... --max-warnings=0` / `npm run check:i18n-missing-keys` |
| 既存コンポーネントテストが壊れない | `npx vitest run src/pages/super-admin/components/LlmUsageSection.test.tsx` |
| ADR index が最新 | `node scripts/generate-adr-index.js --check` |

---

## 技術 How・KPI

- KPI: 本番デプロイ後、`GET /api/v1/fx-rates/USD` が 200 + `rate_jpy` を返すこと（0% → 100%、PO 確認）。
- 技術選択: パスを単数形→複数形に変更するだけの最小差分（新規テーブル・新規マイグレーション不要。`backend/app/routers/invoices.py` 側は無改変でリスクを局所化）。

---

## 弊害・トレードオフ

- パス変更により、デプロイのタイミングで backend が新パス・frontend が旧パスの組み合わせ（またはその逆）が一瞬発生しうる → 対策: backend と frontend は同一 PR・同一デプロイで反映されるため、デプロイ手順が「backend 先行・frontend 追従」でも旧パスは `invoices.fetch_fx_rate` に当たるだけで 404 にはならず、フロントの catch (`.catch(() => null)`) で安全にフォールバックする（`frontend/src/pages/super-admin/components/LlmUsageSection.tsx:394`）。`frontend/src/pages/super-admin/FxRatePage.tsx` も try/catch で 404 相当を「未取得」表示に倒す設計のまま。
- 外部クライアント（本リポジトリ外）が旧パス `/api/v1/fx-rate/{currency}` の SSOT レスポンス形（`rate_jpy`）を直接叩いている場合は影響を受ける → 対策: 本調査の pre-check（`docs/handoff/fx-rate-route-collision/recon.md`）で確認した通り、リポジトリ内に該当呼び出しは無い。外部連携の有無は未確認のため、守り手が追跡する。

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | pre-check（全呼び出し元の洗い出し・フィールド確認） | Sonnet（実装） |
| 2 | `backend/app/routers/fx_rate_admin.py` のパス変更 | Sonnet（実装） |
| 3 | フロント2箇所（FxRatePage.tsx, LlmUsageSection.tsx）のパス変更 | Sonnet（実装） |
| 4 | backend/frontend テスト追加・更新 | Sonnet（実装） |
| 5 | ADR-148 追記、ADR index 再生成 | Sonnet（実装） |
| 6 | recon/design/台帳作成 | Sonnet（実装） |
| 7 | PR 起票（GO 待ち） | Sonnet（実装） |
| 8 | 本番デプロイ後の確認（`/api/v1/fx-rates/USD` 200・使用量タブ円表示） | PO |

---

## 維持の仕組み

- 同一パスへの複数ルート登録を防ぐ恒久対策（例: 起動時アサーション、CI での `app.routes` 重複検査）は本 PR のスコープ外。`backend/tests/test_fx_rate_admin_router.py::TestRouteCollision::test_no_duplicate_method_path_among_fx_rate_routes` は `fx-rate` を含むパスのみを対象にした局所的な回帰防止であり、リポジトリ全体の恒久ガードではない。
- 守り手: `backend/app/routers/fx_rate_admin.py`, `backend/app/routers/invoices.py`, `backend/app/main.py` を変更する担当者が、変更時に `backend/tests/test_fx_rate_admin_router.py` を実行して確認する。

## 継続

- 完了後の監視: PO が本番確認後、「使用量タブが円表示になった」ことをチャットで一言報告してクローズとする。
- 次フェーズへの引き継ぎ: リポジトリ全体での `app.routes` 重複検査の恒久化（CI組み込み）は別タスクとして PO 判断待ち。本 PR では着手しない。
