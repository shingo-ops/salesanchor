<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# recon — prod-disk-safety

**仕事名**: prod-disk-safety
**日付**: 2026-10-02
**対象ADR**: ADR-135, ADR-136, ADR-080
**担当**: Opus（設計）/ Sonnet（実装）

---

## 事故タイムライン（prod1、2026-10-02、UTC）

- HighDiskUsage アラートが 09:00 以前から発火していた（Prometheus ALERTS、09:00〜11:20 UTC 継続）
- F2CleanupStale アラートは 2026-09-21 から発火し続けていた（未対応のまま放置）
- 11:03 JST: `scripts/backup.sh` によるバックアップ生成（281MB）
- 11:08:37: ディスク使用率100%によりPANIC（DB書き込み不可）
- 11:20: PO が手動で `docker builder prune` 相当の操作を実行し build cache 4.5GB を解放
- 11:21: バックエンド API が 200 を返すまで復旧
- その後 PO が手動クリーンアップを行い、空き27GBまで復元

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `.github/workflows/deploy.yml:127-146`（変更前） | "Pre-deploy DB backup" ステップが `cd /home/ubuntu/salesanchor && bash scripts/backup.sh` を実行。ステップ順: 127 backup → 160 deploy（git pull/build/cutover） → 367 nginx → 448 migrations → 534 Finalize（668 `docker image prune -f`）。ディスク空き容量チェック・build cache prune はどこにも存在しなかった |
| `scripts/backup.sh:14-29`（変更前） | `/home/ubuntu/backups/postgres/salesanchor_db_YYYYMMDD_HHMMSS.sql.gz` に `pg_dump \| gzip` で書き込む |
| `scripts/backup.sh:19,34-37`（変更前） | 保持ルールは `find ... -mtime +30 -delete` のみ（日数ベース）。日次cron（毎日3:00）＋デプロイ前バックアップが重なると1日20〜34ファイル生成 → 156ファイル・約27GBに到達しディスクを食い尽くした |
| `scripts/backup_to_s3.sh:40` | `set -euo pipefail` が有効 |
| `scripts/backup_to_s3.sh:83`（変更前） | `LATEST_BACKUP=$(ls -t "$LOCAL_BACKUP_DIR"/*.gz 2>/dev/null \| head -1)` — ファイル数が多いと `head` が最初の1行を読んで早期にパイプを閉じ、`ls` が SIGPIPE を受けて非0終了。`set -o pipefail` 下ではパイプライン全体が失敗扱いとなり `trap 'notify_failure' ERR`（`scripts/backup_to_s3.sh:72`）に飛んでS3アップロードがスキップされる |
| `scripts/backup_to_s3.sh:72` | `trap 'notify_failure' ERR` — 上記の SIGPIPE 失敗を拾ってしまう箇所 |
| （Opus 設計時のローカル再現実測） | 10ファイル時: 50回中0回失敗。156ファイル時: 50回中48回失敗。この結果、S3に欠落した日: 9/19〜23, 9/25〜27, 10/2 |
| `scripts/backup_to_s3.sh:78` | S3側保持は90日（`RETENTION_DAYS=90`、`monthly-archives/` は対象外） |

*（引用先は実在するファイルと行番号を記載すること。process-artifacts gate が自動照合する）*

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | `docker builder prune --keep-storage` のフラグ名・単位指定（`3GB` 等の文字列を受け付けるか） | ローカル docker 29.8.0 で `docker builder prune --help` 実施＋実際に `docker builder prune -f --keep-storage 3GB` を実行して exit 0 を確認 | ✅ 解消済み（本番 docker バージョンは別途確認要・未確認） |
| 2 | 件数ベース保持ロジックが `set -euo pipefail` 下でも安全に動くか（0件・10件以下・15件超のケース） | `scripts/tests/test-backup-retention.sh` を作成し bash:5 コンテナで実行、3テスト全PASS | ✅ 解消済み |
| 3 | `backup_to_s3.sh` の `LATEST_BACKUP` 選定を awk 化した場合、多数ファイルでも SIGPIPE が発生しないか | 同テストスクリプトのテスト3（50回ループ、`salesanchor_db_*` ファイル存在下）で50/50成功を確認 | ✅ 解消済み |
| 4 | 本番 VPS の docker バージョンが `--keep-storage` フラグをサポートしているか | 未確認（ローカル確認のみ）。本番デプロイ後の Finalize ログで `docker builder prune` 行のエラー有無を確認する必要あり | ⚠️ 未確認（デプロイ後に確認が必要・リスクは `\|\| true` で吸収し deploy を失敗させない設計にしている） |

**未解決ゼロ確認**: 上記 #4 は「未確認」のまま明記。他は解消済み。

---

## 補足

- `scripts/tests/test-backup-retention.sh` は `mapfile`（bash ≥4 の組み込みコマンド）を使用する。macOS 標準の `/bin/bash` は 3.2 系で `mapfile` が無いため、ローカル実行時は `docker run --rm -v "$(pwd)":/w -w /w bash:5 bash scripts/tests/test-backup-retention.sh` で bash 5 コンテナ内で実行した。本番 VPS（Ubuntu）の bash は通常 4 系以上のため実運用上の問題はない（`scripts/backfill-active-work-done.sh:44` で既に `mapfile` を使用している前例あり）。
- 監視アラート（HighDiskUsage, F2CleanupStale）自体の改善は本PRのスコープ外（別PRで対応、ADR-080関連）。
