# recon: Redis の接続ログのパスワード（2026-10-17）

## 既存 ADR の検索
- `git grep -il "redis" docs/adr/` と docs/adr/FEATURE-INDEX.md を見た。ログに接続先を出す決まりを定めた ADR は無い。S3（例外の中身を応答に出さない）と同じ考え方（秘密を外へ出さない）で直す。

## 事実
- `backend/app/cache.py:29`（修正前）`logger.info("Redis接続成功: %s", REDIS_URL)`。REDIS_URL はパスワード入り。
- 本番 2026-10-17 02:12Z、discord-gateway のログに上の行が1行出た（#4430 で gateway が init_redis を呼ぶようになったため）。backend・celery-worker のログには0行（docker compose logs を grep。生出力は伏せ字で /tmp/CC報告ファイル/viewer_stage4/impl_4c/prod/）。
- backend/app の中で接続先 URL をログに出すのは cache.py:29 だけ（/tmp/CC報告ファイル/redis_log_mask/grep.txt）。
