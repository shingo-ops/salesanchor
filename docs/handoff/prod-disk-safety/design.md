<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# 設計 — prod-disk-safety

**対象ADR**: ADR-135, ADR-136, ADR-080
**recon**: docs/handoff/prod-disk-safety/recon.md
**日付**: 2026-10-02
**担当**: Opus（設計）/ Sonnet（実装）

---

## 外部・過去事例の参照と我々への応用

- `docker builder prune --keep-storage`（Docker公式コマンド仕様）: BuildKit の legacy builder cache は無制限に増え続けるため、CI/CDデプロイパイプラインで世代ごとに prune するのが公式に推奨されるパターン。我々への応用: Finalize ステップの `docker image prune -f` の直後に `docker builder prune -f --keep-storage 3GB` を追加し、イメージだけでなくビルドキャッシュも継続的に制限する。
- 該当なし（バックアップ件数ベース保持・pipefail対応について）: 外部OSSの汎用パターンというより、今回の事故固有の設計（cron＋デプロイ前バックアップの重複生成という自前の運用構造）に起因するため、既存の `find -mtime` 日数ベース保持を補完する形で件数ベース保持を自前実装するのが最小リスクと判断した。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| 空き5GB未満でデプロイが backup 前に止まる | `.github/workflows/deploy.yml` の "Pre-deploy DB backup" ステップで `FREE_GB -lt MIN_FREE_GB` の分岐が `exit 1` すること（コードレビュー＋次回低空き容量時の実デプロイログで確認） |
| ローカルの `salesanchor_db_*.sql.gz` が10個以下 | 本番 `/home/ubuntu/backups/postgres/` で `ls salesanchor_db_*.sql.gz \| wc -l` が10以下になること（デプロイ数日後に確認） |
| S3 に翌日分が入る | `aws s3 ls s3://salesanchor-backups/postgres-backups/` で前日日付のオブジェクトが存在すること（デプロイ後の日次バックアップで確認） |
| deploy 後の build cache が 3GB 以下 | Finalize ログの `docker builder prune` 出力、または本番で `docker system df` の BUILD CACHE 行が3GB以下であること |
| `scripts/tests/test-backup-retention.sh` が3テスト全てPASSする | `bash scripts/tests/test-backup-retention.sh`（bash≥4環境、ローカルはbash:5コンテナ） |

*（各行の「検証方法」は空欄不可。process-artifacts gate が照合する）*

---

## 技術 How・KPI

- KPI: 本番 `/` の空き容量が5GB未満の状態でデプロイが完走しない（backup前にexit 1で停止する）。`salesanchor_db_*.sql.gz` のローカル保持数が常に10以下。S3バックアップの欠落日が今後発生しない。
- 技術選択1: `scripts/backup.sh` に件数ベース保持（新しい10件のみ残す）を追加。既存の30日ルール（`scripts/backup.sh:19,36-37`）は変更せず併用（理由: 既存の日数ベースだけでは cron＋デプロイ前バックアップの重複生成に対応できないため、件数での上限キャップを追加する方が確実）。
- 技術選択2: `scripts/backup_to_s3.sh:83` の `ls | head -1` を `ls | awk 'NR==1'` に変更（理由: `head` は最初の1行を読むと早期にパイプを閉じて `ls` に SIGPIPE を送るが、`awk` は標準入力を最後まで読み切るため SIGPIPE が発生しない。`set -o pipefail` 下でのパイプ失敗を根本解消）。対象グロブも `*.gz` → `salesanchor_db_*.sql.gz` に限定し、`tenant_*` 等の無関係ファイルを除外。
- 技術選択3: `.github/workflows/deploy.yml` の "Pre-deploy DB backup" ステップの先頭に `df --output=avail -B1G /` による空き容量チェックを追加し、`MIN_FREE_GB=5` 未満なら named variable のコメント付きで `exit 1`（理由: backup.sh がファイルを書き込む前にデプロイを止めることで、今回のようにバックアップ自体がディスクを使い切る事態を未然に防ぐ）。
- 技術選択4: Finalize ステップの `docker image prune -f`（`.github/workflows/deploy.yml:668` 変更前）の直後に `docker builder prune -f --keep-storage 3GB || true` を追加（理由: イメージpruneだけではBuildKitのビルドキャッシュは減らない。`|| true` でこのステップの失敗がデプロイ全体を失敗させないようにする）。

### 変更詳細

`scripts/backup.sh`（既存の day-based retention の直後に追加）:
```bash
KEEP_COUNT=10
mapfile -t BACKUP_FILES < <(ls -1t "${BACKUP_DIR}"/salesanchor_db_*.sql.gz 2>/dev/null || true)
if [ "${#BACKUP_FILES[@]}" -gt "${KEEP_COUNT}" ]; then
  REMOVED_COUNT=0
  for ((i = KEEP_COUNT; i < ${#BACKUP_FILES[@]}; i++)); do
    rm -f "${BACKUP_FILES[$i]}"
    REMOVED_COUNT=$((REMOVED_COUNT + 1))
  done
  echo "[$(date)] Count-based retention: removed ${REMOVED_COUNT} old backup(s), kept newest ${KEEP_COUNT}" \
    >> "${BACKUP_DIR}/backup.log"
fi
```

`scripts/backup_to_s3.sh`（旧83行目を置換）:
```bash
LS_ERR_LOG=$(mktemp)
LATEST_BACKUP=$(ls -1t "$LOCAL_BACKUP_DIR"/salesanchor_db_*.sql.gz 2>"${LS_ERR_LOG}" | awk 'NR==1')
if [ -s "${LS_ERR_LOG}" ]; then
  echo "WARN: ls でエラー: $(cat "${LS_ERR_LOG}")"
fi
rm -f "${LS_ERR_LOG}"
```

`.github/workflows/deploy.yml`（"Pre-deploy DB backup" ステップ、`bash scripts/backup.sh` の直前）:
```bash
MIN_FREE_GB=5
FREE_GB=$(df --output=avail -B1G / | tail -1 | tr -d '[:space:]')
echo "Free space on /: ${FREE_GB}GB (threshold: ${MIN_FREE_GB}GB)"
if [ "${FREE_GB}" -lt "${MIN_FREE_GB}" ]; then
  echo "❌ 空き容量不足のためデプロイを中止します: ${FREE_GB}GB < ${MIN_FREE_GB}GB"
  du -sh /home/ubuntu/backups/postgres 2>/dev/null || true
  docker system df || true
  exit 1
fi
```

`.github/workflows/deploy.yml`（Finalize ステップ、`docker image prune -f` の直後）:
```bash
echo "Step 8b: Cleaning up Docker build cache (keep 3GB)..."
docker builder prune -f --keep-storage 3GB || true
```

---

## 弊害・トレードオフ

- 件数ベース保持（新しい10件のみ残す）により、過去30日分のバックアップが実質10件（概ね最新数日分）に縮退する可能性がある → 対策: S3側は90日保持（`scripts/backup_to_s3.sh:78`、変更なし）が本来の長期保全手段であり、ローカルは直近のロールバック用途に限定する設計変更として許容する。ただしSSOTとしてローカル30日保持に依存する運用が他にあれば要確認（今回の recon では確認できず・未確認）。
- `docker builder prune --keep-storage 3GB` のフラグが本番 docker バージョンで未サポートの場合、警告なく `|| true` で握り潰される → 対策: デプロイ後の Finalize ログを初回確認し、エラー出力がないか見る（recon 不明点#4、未確認のまま明記）。
- ディスク空き容量チェックの閾値 `MIN_FREE_GB=5` は固定値であり、将来ディスク増量・バックアップサイズ変化に応じて調整が必要になる可能性がある → 対策: named variable 化してコメントを付けており、調整は1箇所の変更で済む。
- `scripts/tests/test-backup-retention.sh` は `mapfile`（bash≥4）に依存し、macOS標準bash（3.2系）では動かない → 対策: 本テストはローカルでは `docker run --rm -v "$(pwd)":/w -w /w bash:5 bash scripts/tests/test-backup-retention.sh` のように bash:5 コンテナで実行することを前提とする。本番 VPS（Ubuntu）の bash は4系以上のため実運用には影響しない。

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | `scripts/backup.sh` に件数ベース保持ロジックを追加 | Sonnet（実装） |
| 2 | `scripts/backup_to_s3.sh:83` の SIGPIPE 対応（awk化＋グロブ限定） | Sonnet（実装） |
| 3 | `.github/workflows/deploy.yml` に空き容量チェック＋builder prune を追加 | Sonnet（実装） |
| 4 | `scripts/tests/test-backup-retention.sh` を新規作成し動作確認 | Sonnet（実装） |
| 5 | `docs/handoff/prod-disk-safety/recon.md`・`design.md` 作成 | Sonnet（実装） |
| 6 | PR作成（Draft）→ PO確認 → `GO #<PR番号>` 受領後にマージ | PO |
| 7 | デプロイ後、Finalize ログで builder prune のエラー有無を確認 | PO/実行役 |

---

## 継続

- 完了後の監視: デプロイ後の Finalize ログで `docker builder prune` の出力を確認（エラーがあれば recon 不明点#4を解消）。数日後に `/home/ubuntu/backups/postgres/salesanchor_db_*.sql.gz` のファイル数が10以下で安定していることを確認。
- 次フェーズへの引き継ぎ: HighDiskUsage / F2CleanupStale アラートの監視改善（通知が事故の2時間以上前から発火していたにも関わらず対応が遅れた問題）は本PRのスコープ外。別PRでADR-080関連の監視改善として対応する。

---

## 8. 維持の仕組み

守り手: `scripts/tests/test-backup-retention.sh` が件数ベース保持ロジックとS3選定ロジックの回帰をローカル/CIで検知する（bash≥4環境が前提、本番VPSおよびbash:5コンテナで確認済み）。
- 守り手2: `.github/workflows/deploy.yml` の空き容量チェックが、将来誰かがバックアップ処理を変更してディスクを圧迫するコードを追加しても、デプロイ自体を5GB未満で止めるためのセーフティネットとして機能する。
- 未確立（正直な明記）: `docker builder prune --keep-storage` が本番dockerバージョンで実際に効果を発揮しているかは、次回デプロイ後のログ確認まで機械的に保証されていない。
