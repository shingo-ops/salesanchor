# Design: fix-buyback-schedule

recon: docs/handoff/fix-buyback-schedule/recon.md

## 方針

Celery beat スケジュールを `crontab(minute=0, hour="1,4,13")` に変更。

## 変更前後

| 項目 | 変更前 | 変更後 |
|---|---|---|
| スケジュール | `hour="*/4"`（6回/日） | `hour="1,4,13"`（3回/日） |
| JST実行時刻 | 0/4/8/12/16/20時 | 10/13/22時 |
| データ量 | ~2,700行/日 | ~1,350行/日 |

| 基準 | 検証方法 |
|---|---|
| スケジュール変更が反映 | Celery beat ログで次回実行時刻を確認 |
| 既存データに影響なし | 設定変更のみ（DDL/DML なし） |

守り手: backend/app/celery_app.py（beat_schedule 定義）

## 触るファイル
- backend/app/celery_app.py（スケジュール変更）
- backend/app/tasks/buyback_scraper.py（コメント更新のみ）

## 触らないファイル
- migrations/（変更なし）
- frontend/（変更なし）

## 外部・過去事例の参照と我々への応用
該当なし（内部スケジュール設定の変更のみ）

## 維持の仕組み
スケジュール変更は celery_app.py の beat_schedule で一元管理。変更時はデプロイで自動反映。
守り手: backend/app/celery_app.py（beat_schedule 定義）
