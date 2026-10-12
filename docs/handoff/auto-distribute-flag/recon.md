# TCG_AUTO_DISTRIBUTE 有効化 recon

## 現状
- TCG_AUTO_DISTRIBUTE のコード上の参照: backend/app/tasks/tcg_extraction.py:316
- docker-compose.yml に passthrough 行がないため、.env に設定してもコンテナに渡らない
- 本番の celery-worker で `os.environ.get("TCG_AUTO_DISTRIBUTE")` が空文字を返す

## 配信フィルタの安全性
- tcg_distribution_svc.py の `fetch_output_rows()` WHERE句:
  - `pid_resolved = TRUE`
  - `needs_review IS FALSE`
  - `exclusion IS DISTINCT FROM 'excluded'`（NULL安全）
  - `unit_resolved = TRUE`
  - `price_normalized IS NOT NULL`
  - `canonical NOT LIKE 'FLAG_%'`
- 安全装置: pending/running のジョブが残っていれば配信中止
