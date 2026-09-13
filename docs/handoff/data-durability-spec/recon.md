# recon — data-durability-spec

この文書は何か（専門用語なしの1行）: いま実際にバックアップがどうなっているかを、目で見て確かめた記録。

親（仕様書）: [../../specs/data-durability/README.md](../../specs/data-durability/README.md)

**仕事名**: data-durability-spec
**日付**: 2026-09-01（初版）／ 2026-09-02 更新
**対象ADR**: ADR-153
**担当**: 設計パートナー（実測は実装役が実行）

---

## 更新履歴

初版では S3 転送の失敗期間を「2026-08-23 から 09-01 まで10日連続」と記載したが、これはログ末尾40行のみを根拠とした誤りだった。ログ全体（256行）の先頭を読み、実際の失敗開始は 2026-05-28 であることを確認したため訂正する。

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
| `.github/workflows/deploy.yml:127` | デプロイ前にDBバックアップを取る手順が定義されている |
| `docker-compose.yml:113` | 添付ファイル用ボリュームが /data/attachments にマウントされている |
| `docker-compose.yml:411` | 添付ファイル用ボリューム attachments_data が定義されている |
| `docs/B-09_restore_test_procedure.md:11` | 月次リストアテストの実施タイミングが毎月第1月曜と定義されている |

行番号なしの参照（表示時に行番号の重複が確認されたため行番号を用いない）:
- scripts/aws-setup/README.md — S3バケット作成手順・cron登録手順・DR復旧手順が記載されている
- scripts/backup.sh — pg_dump をgzip圧縮して /home/ubuntu/backups/postgres に保存し、RETENTION_DAYS=30 を超えたものを削除する
- docs/handoff/prod1-auto-cleanup/recon.md — 2026-06-29 時点の prod1 crontab に backup.sh と backup_to_s3.sh の2本が登録済みであることが記録されている

## サーバー実測（prod1 / prod2）

2026-09-01 20:36 JST 実測:

| 観測点 | 結果 |
|---|---|
| prod1 crontab | backup.sh 3:00 / backup_to_s3.sh 3:30 / f2-cleanup 日曜4:00 の3本 |
| prod1 aws コマンド | command not found |
| prod1 ~/.aws/ | config（region・output）と credentials（aws_access_key_id・aws_secret_access_key）が存在 |
| prod1 archive_mode | off（wal_level は replica） |
| prod1 データベース容量 | 56 MB |
| prod1 ディスク | 50G 中 20G 使用・28G 空き |
| prod2 crontab | no crontab for ubuntu |
| prod2 /opt/backup-target/ | 存在しない |
| prod2 aws コマンド | command not found |
| prod2 ディスク | 197G 中 22G 使用・166G 空き |
| prod1 の所在 | 49.212.137.46 / AS9371 SAKURA Internet Inc. / Osaka |
| prod2 の所在 | 49.212.160.98 / AS9371 SAKURA Internet Inc. / Osaka |

2026-09-01 23:50 JST 実測:

| 観測点 | 結果 |
|---|---|
| s3_backup.log 総行数 | 256行 |
| 転送成功の回数 | 2回（「サイズ一致」が4行目と10行目のみ） |
| 転送成功の日付 | 2026-05-26 と 2026-05-27 |
| 最初の失敗 | 2026-05-28（ログ16行目、aws: command not found） |
| 最後の失敗 | 2026-09-01 |
| .env 内の DISCORD_WEBHOOK_OPS | 0件 |
| crontab 内の DISCORD_WEBHOOK_OPS | 0件 |
| prod1 .env | 実在（GitHub追跡下は .env.example のみ）。POSTGRES_PASSWORD・METADATA_FERNET_KEY・各種APIトークンを含む約55の鍵名 |
| /home/ubuntu/backups/postgres/ のファイル数 | 77 |
| 3:00 以外のバックアップの出所 | deploy.yml の Pre-deploy DB backup（デプロイのたびに backup.sh が走る） |
| ローカルバックアップの保持 | backup.sh の RETENTION_DAYS=30 |
| 添付ファイル用ボリューム | docker-compose.yml に attachments_data が定義済み。backup.sh は pg_dump のみのためバックアップ対象外 |
| apt での awscli 入手 | apt-cache policy awscli が Candidate: (none) |
| snap の有無 | which snap が空 |
| botocore | python3 -c "import botocore" がエラーなく通る |

## 現在値（KGIに対する測定）

| KGI | 現在値 | 根拠 |
|---|---|---|
| 1 障害の10分前まで戻せる | 不可 | archive_mode = off により時点復旧の土台が無い |
| 2 半日以内に戻せる | 未測定 | 復旧演習を実施していない |
| 3 コピーが3つある | 1 | prod1 ローカルのみ。prod2 に無く、S3 は 2026-05-28 以降 成功0回 |
| 4 離れた場所に1つある | 0 | prod1・prod2 とも AS9371 SAKURA Internet Inc.・Osaka |
| 5 全データが対象に入っている | 1/3 | 層1（DB）のみ。層2（添付画像）と層3（環境設定・鍵）は対象外 |
| 6 失敗が届く | 0 | DISCORD_WEBHOOK_OPS が未設定のため、約3か月の失敗が通知されなかった |
| 7 復旧を1度やって見せる | 0 | 実施記録が無い |
| 8 演習が続く | 0 | 同上 |

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | S3転送がいつから失敗しているか | s3_backup.log 全体を読む | 解消（2026-05-28 から） |
| 2 | ~/.aws/credentials の鍵が今も有効か | AWS CLI 導入後に sts get-caller-identity | 未解消 |
| 3 | バケット salesanchor-backups が実在するか | AWS CLI 導入後に s3 ls | 未解消 |
| 4 | 3:00 以外の時刻のバックアップの出所 | deploy.yml の該当箇所を読む | 解消（Pre-deploy DB backup） |
| 5 | 添付画像の保存先の現況 | docker-compose.yml を読む | 解消（attachments_data・バックアップ対象外） |
| 6 | 環境設定と鍵のサーバー上の実体 | prod1 の .env を確認 | 解消（実在・GitHub外・復号鍵を含む） |
| 7 | prod1 と prod2 が同一建物か | さくらインターネットの提供情報を確認 | 未解消 |
| 8 | バックアップ失敗の通知が誰かに届いているか | DISCORD_WEBHOOK_OPS の設定を確認 | 解消（未設定・届いていない） |

**未解決ゼロ確認**: 未解消3件（#2・#3・#7）。#2 と #3 は prod1 への AWS CLI 導入を伴うため、本 recon では解消しない。#7 は外部情報の確認による。

## 補足

層3（環境設定・鍵）には METADATA_FERNET_KEY が含まれる。この鍵が失われた場合、データベースを復元しても暗号化済みの値を復号できない可能性がある。層3をバックアップ対象に含める必要性はここに由来する。

design では、未解消3件の扱いを含めて手段を比較する。
