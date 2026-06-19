# recon: Advisor Phase 1 / PR-4 新規モード 逆算アドバイスAPI

**仕事名**: Advisor Phase 1 / PR-4 新規モード 逆算アドバイスAPI
**日付**: 2026-06-20
**対象ADR**: ADR-139
**担当**: architect

## file:line 引用表

| 引用先 path:line | 確認内容 |
|------------------|---------|
| backend/app/routers/analytics.py:114-145 | 逆算アドバイスの response model（GoalAdviceInputs / GoalAdviceRatesUsed / GoalAdviceRequired / GoalAdviceWorkingDays / GoalAdviceResponse）を追加 |
| backend/app/routers/analytics.py:181-243 | 期間境界、平日カウント、月末・週末、shifts の distinct カウント helper を追加 |
| backend/app/routers/analytics.py:555-648 | revenue-segments が new セグメントの avg_order_amount を返し、unit_price の根拠になる |
| backend/app/routers/analytics.py:651-814 | /analytics/new-goal-advice が monthly_kgi / kgi_type / scope / period を受け、rates_used / monthly_required / weekly_required / working_days / data_sufficient を返す |
| backend/tests/test_analytics.py:193-230 | shifts 行の投入 helper と平日カウント helper を追加 |
| backend/tests/test_analytics.py:958-1177 | revenue / wins / data_sufficient の pytest を追加 |

## 事実メモ

- unit_price は revenue-segments の new.avg_order_amount をそのまま使う。
- win_rate は deals の won 件数 / total 件数、deal_rate は leads の converted 件数 / total 件数で計算する。
- rates_used の win_rate / deal_rate は表示用の百分率値で、内部計算では 100 で割って使う。
- shifts はログイン中ユーザーの current_user.id で数える。current month に1行でもあれば submitted、無ければ not_submitted。
- submitted 時の remaining_month / remaining_week は distinct shift_date を今日以降で数える。not_submitted 時は平日（月〜金）で数える。
- data_sufficient=false のときは monthly_required / weekly_required を null にする。
- tenant_006 のテストを使い、tenant_4 は使っていない。

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | 逆算の rate を百分率で返すか比率で返すか | 百分率で返し、内部計算で 100 分の 1 に変換 | 解消済み |
| 2 | shifts の remaining_month を月内全件にするか今日以降にするか | 今日以降の distinct shift_date に統一 | 解消済み |

**未解決ゼロ確認**: 全て解消済み

## 補足

- read-only の集計 API 追加で、DB migration / deploy.yml 変更は不要。
- scope=mine は rates の集計範囲に適用し、working_days はログイン中ユーザーのシフトで判定する。
- PayPal smoke は本 PR の必須チェックではないため、マージ判定から除外する。
