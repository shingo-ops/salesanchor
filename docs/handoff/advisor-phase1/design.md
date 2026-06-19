# design.md — Advisor Phase 1 / PR-4 新規モード 逆算アドバイスAPI

**対象ADR**: ADR-139
**recon**: docs/handoff/advisor-phase1/recon.md
**日付**: 2026-06-20
**担当**: Planner

## 目的

月次の売上目標または成約件数目標から、必要成約数・必要商談数・必要リード数と今週分を read-only で返す。根拠として使った単価、率、稼働日、shift_status を同時に返し、画面はその結果を表示するだけにする。

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| GET /api/v1/analytics/new-goal-advice が返る | pytest backend/tests/test_analytics.py -q -k new_goal_advice --no-cov |
| kgi_type=revenue で unit_price から必要成約数が算出される | pytest backend/tests/test_analytics.py -q -k new_goal_advice --no-cov |
| kgi_type=wins で月次成約件数を起点に必要商談数・必要リード数が算出される | pytest backend/tests/test_analytics.py -q -k new_goal_advice --no-cov |
| submitted / not_submitted の shift_status が正しい | pytest backend/tests/test_analytics.py -q -k new_goal_advice --no-cov |
| data_sufficient=false のとき monthly_required / weekly_required が null になる | pytest backend/tests/test_analytics.py -q -k new_goal_advice --no-cov |
| process-artifacts gate が通る | GitHub Actions の process-artifacts gate |

## 技術方針

- 入力は monthly_kgi, kgi_type, period, scope。
- kgi_type は revenue と wins の 2 種のみ。
- rates_used は表示用の百分率で返す。内部の逆算では 100 で割った比率を使う。
- unit_price は revenue-segments の new.avg_order_amount を使う。
- win_rate は deals の won 件数 / total 件数、deal_rate は leads の converted 件数 / total 件数。
- data_sufficient は rate が 0/null、または revenue モードで unit_price が 0/null のとき false。
- monthly_required は revenue モードなら monthly_kgi / unit_price を起点に、wins → deals → leads の順で逆算する。
- wins モードは monthly_kgi を成約件数として扱い、そのまま deals / leads を逆算する。
- working_days は shifts テーブルの current_user.id を元に計算する。current month に 1 行でもあれば submitted、無ければ not_submitted。
- submitted 時は distinct shift_date を今日以降で数える。not_submitted 時は平日（月〜金）を数える。週次は今日から週末までの範囲で同じルールを使う。
- 祝日は v1 では考慮しない。

## 外部・過去事例の参照と我々への応用

該当なし。今回の PR は既存の revenue-segments、deals、leads、shifts を read-only で組み合わせるだけで、外部ライブラリや追加の過去事例を参照して設計を変える必要はない。

## API

- ルート: /api/v1/analytics/new-goal-advice
- クエリ:
  - monthly_kgi: 必須
  - kgi_type: revenue / wins
  - scope: team / mine
  - period: 1m / 3m / 6m / 12m
- レスポンス:
  - inputs: monthly_kgi, kgi_type, period, scope
  - rates_used: unit_price, win_rate, deal_rate
  - monthly_required: wins, deals, leads
  - weekly_required: wins, deals, leads
  - working_days: remaining_month, remaining_week, shift_status
  - data_sufficient: bool

## 変更範囲

- backend/app/routers/analytics.py: 逆算アドバイス API 追加
- backend/tests/test_analytics.py: tenant_006 の pytest 追加
- docs/handoff/advisor-phase1/: recon / design を PR-4 用に更新

## 検証メモ

- tenant_006 を使う。tenant_4 は使わない。
- DB migration / deploy.yml 変更なし。
- PayPal smoke は必須ではないため、CI 判定から外してよい。
