# recon — fix-analytics-jst

**仕事名**: fix-analytics-jst
**日付**: 2026-09-01
**対象ADR**: ADR-151
**担当**: architect

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `backend/app/services/time.py:30` | `_jst_month_range_utc()` が JST 月次境界を UTC で返す（基準が JST である証拠） |
| `backend/app/routers/analytics.py:37` | `_today_jst()` ヘルパー（JST 基準の今日を返す）が定義済み |
| `backend/app/routers/analytics.py:39` | `return datetime.now(_JST).date()` — 旧 `date.today()` の置換先 |
| `backend/app/routers/analytics.py:271` | ファネル集計で `today = _today_jst()` を使用 |
| `backend/app/routers/goals.py:44` | goals.py にも `_today_jst()` ヘルパーを追加済み |
| `backend/app/routers/goals.py:279` | 月次目標の基準日を `_today_jst()` で取得 |
| `backend/app/routers/quotes.py:191` | 見積有効期限を `datetime.now(_JST).date()` 基準で計算 |
| `backend/app/services/fedex_rates.py:417` | 出荷日 ship_date を `datetime.now(ZoneInfo("Asia/Tokyo")).date()` 基準で計算 |
| `backend/app/tasks/sa02_recon_monitor.py:50` | 日次突合の `today` を `datetime.now(ZoneInfo("Asia/Tokyo")).date()` に変更 |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | FedEx `shipDateStamp` のタイムゾーン解釈 | `origin_cc = "JP"` 固定を確認 → 発送元ローカル日付（JST）が正しい | ✅ 解消済み |
| 2 | `closed_at` の比較基準（テスト） | SQLite/PostgreSQL とも UTC 日付文字列を返すことを確認 → `_today_utc()` で比較 | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み
