# ADR-151: バックエンド全域で「今日」の基準を JST に統一

- **Status**: Accepted
- **Date**: 2026-09-01
- **Deciders**: shingo-ops（PO）, Hikky-dev（Dev）

## Context

`_jst_month_range_utc()` が JST 月次境界を UTC に変換して返す（`backend/app/services/time.py:30`）のに対し、
「今月」の year/month を決める `today` が `date.today()`（UTC）で取得されていた。

毎月1日 **00:00〜09:00 JST**（= UTC 前月末 15:00〜00:00）の間、
UTC の `date.today()` が前月のまま → JST 月次範囲と不一致 → 当月データがゼロになる。

この不整合が analytics ダッシュボードで毎月1日深夜に前月表示を引き起こし、
見積有効期限で1日誤差、FedEx 出荷日計算で発送元ローカル日付ズレを生じさせていた。

## Decision

バックエンド全体で「今日」の取得を `datetime.now(ZoneInfo("Asia/Tokyo")).date()` に統一する。

対象:
- `backend/app/routers/analytics.py` — `_today_jst()` ヘルパー（10箇所置換）
- `backend/app/routers/goals.py` — 週番号・月判定（2箇所）
- `backend/app/routers/quotes.py` — 見積有効期限基準日
- `backend/app/services/fedex_rates.py` — 出荷日 ship_date（`origin_cc = "JP"` 固定のため JST が正）
- `backend/app/tasks/sa02_recon_monitor.py` — 日次突合の「当日」判定

## Consequences

- JST 月末深夜（00:00〜09:00）での日付ズレが解消される
- FedEx `shipDateStamp`（タイムゾーン情報なし）が発送元ローカル日付（JST）として正しく送信される
- DB スキーマ変更なし。アプリケーションコードのバグ修正のみ
- テスト内の delivery 計算も `_today_jst()` ベースに統一（案X採用）
