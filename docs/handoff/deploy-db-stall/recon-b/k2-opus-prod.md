# 段2 K2-5〜K2-7 の確かめ（Opus・2026-11-18 JST 00:2x・読み取りのみ）

段4a（§17）を本番に出す前提（§17-9 (3)、§3 の順番）として、段2の受け入れ基準 K2-5〜K2-7（§16-7）を本番の記録で確かめた。

## K2-5 本番反映3回で控えと移行の段が success・片付けの行
- 数え方: `gh api repos/shingo-ops/salesanchor/actions/workflows/deploy.yml/runs?per_page=100&created=>=2026-10-30 --paginate` で 685 回を並べ、各回の jobs の段の結論を読んだ（記録は作業メモ）。2026-10-30 以降、控え（Pre-deploy DB backup）と移行（Run database migrations）が両方 success の回は 74 回。
- 古い順の最初の3回:

| run | 開始 (UTC) | 控え | 移行 | 失敗のときの段 | 片付けの行 |
|---|---|---|---|---|---|
| 40993814455 | 2026-10-30 02:48 | success | success | skipped | 控えの段 `skipped: script not present (old checkout)`／移行の段 `scripts=0 backends=0 remaining=0` |
| 41037743481 | 2026-10-30 10:02 | success | success | skipped | 2つの段とも `scripts=0 backends=0 remaining=0` |
| 41108395785 | 2026-10-30 18:36 | success | success | skipped | 2つの段とも `scripts=0 backends=0 remaining=0` |

- 判定: 合格（3/3）。行は `gh run view <id> --log` から `grep -a` で取った。

## K2-6 prod1 の残り・名前・ai_ro
- 3回の直後の観測は記録が無い。代わりに 2026-11-18 00:28 JST に観測した（3回の後で、その後の本番反映も含む）。
  - prod1 の `ps -eo pid,etimes,args` で `backup.sh deploy`・`run_all_migrations.sh` に当たる行: 0。
  - reader 鍵の道で pg_stat_activity の application_name が salesanchor_migration・salesanchor_backup_deploy の接続: 0（全体 29 本、2026-11-17 15:29:18Z）。
  - reader 鍵の道で information_schema.views の ai_ro のビュー: 589。
- 判定: 合格（観測の時刻は基準の「3回の後」に当たる。直後ではない）。

## K2-7 翌朝3時の控え
- prod1 の `/home/ubuntu/backups/postgres/backup.log`（読み取りのみ）:
  - `[Sat Oct 31 03:02:00 JST 2026] Backup completed: salesanchor_db_20261031_030001.sql.gz (561M)`
- 判定: 合格。

## 結論
- K2-5〜K2-7 はそろった。段4a（§17）の「本番に出す前提」は満たされた。
- 参考: 2026-10-30 以降、移行の段が failure の回が 10 回ある（11/2・11/7・11/9 に8回）。K2 の判定には入らない。§19-1 の 11/13 の失敗は、最後の回の結論が success のため、この数には出ない（§19-1 の「一覧は最後の回の結論しか出さない」）。
