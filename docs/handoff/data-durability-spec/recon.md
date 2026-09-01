# recon — data-durability-spec

この文書は何か（専門用語なしの1行）: いま実際にバックアップがどうなっているかを、目で見て確かめた記録。

親（仕様書）: [../../specs/data-durability/README.md](../../specs/data-durability/README.md)

**仕事名**: data-durability-spec
**日付**: 2026-09-01
**対象ADR**: ADR-153
**担当**: 設計パートナー（実測は実装役が実行）

---

## 既存ADR検索の結果

docs/adr/ をファイル名で backup / restore / recover / disaster / s3 / durab で検索し、該当0件。
docs/adr/FEATURE-INDEX.md 全文にもデータ保全の行は無し。
よって既存設計なし（grep 済・該当なし）。本 recon に伴い ADR-153 を新規起案した。

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `scripts/backup_to_s3.sh:51` | 転送先バケット名が salesanchor-backups で定義されている |
| `scripts/backup_to_s3.sh:53` | 転送元がサーバー上の /home/ubuntu/backups/postgres である |
| `scripts/backup_to_s3.sh:54` | S3 上の保持日数が90日で定義されている |
| `scripts/backup_to_s3.sh:71` | aws コマンドを呼ぶ行。prod1 ではこの行で command not found となる |
| `docs/B-09_restore_test_procedure.md:11` | 月次リストアテストの実施タイミングが毎月第1月曜と定義されている |

行番号なしの参照（表示時に行番号の重複が確認されたため行番号を用いない）:
- scripts/aws-setup/README.md — S3バケット作成手順・cron登録手順・DR復旧手順が記載されている
- docs/handoff/prod1-auto-cleanup/recon.md — 2026-06-29 時点の prod1 crontab に backup.sh と backup_to_s3.sh の2本が登録済みであることが記録されている

## サーバー実測（2026-09-01 20:36 JST・prod1 / prod2）

| 観測点 | 結果 |
|---|---|
| prod1 crontab | backup.sh 3:00 / backup_to_s3.sh 3:30 / f2-cleanup 日曜4:00 の3本 |
| prod1 aws コマンド | command not found |
| prod1 ~/.aws/ | config と credentials が存在（2026-05-26 付） |
| prod1 s3_backup.log 末尾40行 | 2026-08-23 から 09-01 まで10日連続で command not found により失敗 |
| prod1 バックアップ実体 | /home/ubuntu/backups/postgres/ に存在。2026-09-01 だけで10本以上 |
| prod1 データベース容量 | 56 MB |
| prod1 archive_mode | off（wal_level は replica） |
| prod1 ディスク | 50G 中 20G 使用・28G 空き |
| prod2 crontab | no crontab for ubuntu |
| prod2 /opt/backup-target/ | 存在しない |
| prod2 aws コマンド | command not found |
| prod2 ディスク | 197G 中 22G 使用・166G 空き |
| prod1 の所在 | 49.212.137.46 / AS9371 SAKURA Internet Inc. / Osaka |
| prod2 の所在 | 49.212.160.98 / AS9371 SAKURA Internet Inc. / Osaka |

## 現在値（KGIに対する測定）

| KGI | 現在値 |
|---|---|
| 3 コピーが3つある | 1 |
| 4 離れた場所に1つある | 0 |
| 5 全データが対象に入っている | 1/3（データベース本体のみ。添付画像と環境設定は未確認） |

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | S3転送がいつから失敗しているか | s3_backup.log 全体を読む | 未解消（末尾40行のみ確認） |
| 2 | ~/.aws/credentials の鍵が今も有効か | AWS CLI 導入後に sts get-caller-identity | 未解消 |
| 3 | バケット salesanchor-backups が実在するか | AWS CLI 導入後に s3 ls | 未解消 |
| 4 | 3:00 以外の時刻のバックアップの出所 | deploy.yml の該当箇所を読む | 未解消 |
| 5 | 添付画像の保存先の現況 | attachment-storage テーマの進行状況を確認 | 未解消 |
| 6 | 環境設定と鍵のサーバー上の実体 | prod1 の .env 等を確認 | 未解消 |
| 7 | prod1 と prod2 が同一建物か | さくらインターネットの提供情報を確認 | 未解消 |
| 8 | バックアップ失敗の通知が誰かに届いているか | DISCORD_WEBHOOK_OPS の設定を確認 | 未解消 |

**未解決ゼロ確認**: 未解消8件。本 recon は起票段階のものであり、design に進む前に別便で解消する。

## 補足

本 recon は「テーマを立てるに足る現在地」を固定するためのもので、design 着手の条件を満たすものではない。
上記8件の解消を経てから design に入る。
