# Recon: fix-buyback-schedule

## 観測事実

- 現行: `crontab(minute=0, hour="*/4")` — 4時間ごと6回/日（backend/app/celery_app.py:166）
- PO要望: サイト更新頻度に合わせ、夜間除外で1日3回（JST 10:00 / 13:00 / 22:00）
- サーバーはUTC: JST 10:00=UTC 01:00, JST 13:00=UTC 04:00, JST 22:00=UTC 13:00
