# Pre-deploy DB backup on migrations only — Recon

**日付**: 2026-10-03
**ブランチ**: release/predeploy-backup-on-migrations
**ベース**: origin/main (eec16c840)
**PO承認**: 2026-10-03「y」— デプロイに DB migration が含まれる場合のみ pre-deploy DB backup を取得する

---

## 1. migration検知ステップ（既存）

`.github/workflows/deploy.yml:33-46`

```yaml
      - name: Detect backend / migration changes
        uses: dorny/paths-filter@v4
        id: changes
        with:
          filters: |
            migrations:
              - 'migrations/**'
              - 'scripts/**'
              - 'backend/**'
              - 'docker-compose.yml'
              - '.github/workflows/deploy.yml'
            nginx:
              - 'nginx/**'
              - 'docker-compose.yml'
```

- ステップID: `changes`
- migration有無のoutput名: `migrations`（`steps.changes.outputs.migrations` が `'true'`/`'false'`）
- 実行順序: `.github/workflows/deploy.yml:33` （`id: changes`）は `.github/workflows/deploy.yml:127`「Pre-deploy DB backup」より前。
  **前提確認: 満たしている（STOPなし）**
- 既存の使用例（本ステップのoutputsを使っている箇所）:
  - `.github/workflows/deploy.yml:383` `if: ${{ success() && steps.changes.outputs.nginx == 'true' }}`
  - `.github/workflows/deploy.yml:464` `if: ${{ success() && steps.changes.outputs.migrations == 'true' }}`
  - `.github/workflows/deploy.yml:485` `if: ${{ success() && steps.changes.outputs.migrations == 'true' }}`
  - `.github/workflows/deploy.yml:565` `if [ "${{ steps.changes.outputs.migrations }}" != "true" ]; then`（Finalizeステップ内のシェル条件）

## 2. Pre-deploy DB backup ステップの既存内容（変更前）

`.github/workflows/deploy.yml:122-161`

- バックアップ本体: `.github/workflows/deploy.yml:154` `bash scripts/backup.sh`
- バックアップファイル特定: `.github/workflows/deploy.yml:155` `LATEST=$(ls -t /home/ubuntu/backups/postgres/salesanchor_db_*.sql.gz 2>/dev/null | head -1)`
- 空き容量チェック（PR #3945, ADR-135/136由来）: `.github/workflows/deploy.yml:140-152` `MIN_FREE_GB=5` ブロック
- このステップに `id:` は設定されていない（確認: `grep -n "id:" .github/workflows/deploy.yml` の結果は `35:        id: changes` のみ）→ **他ステップがこのバックアップステップの `outputs` を参照している箇所はゼロ**。したがって `if` を追加してスキップされても、他ステップの出力参照に関する互換対応は不要。

## 3. ロールバック経路の調査（LATEST / salesanchor_db_ / restore / rollback）

```
$ grep -n -i "LATEST\|salesanchor_db_\|rollback\|restore\|PREV_SHA\|steps.changes" .github/workflows/deploy.yml
155:            LATEST=$(ls -t /home/ubuntu/backups/postgres/salesanchor_db_*.sql.gz 2>/dev/null | head -1)
156:            if [ -z "${LATEST}" ]; then
160:            SIZE=$(du -h "${LATEST}" | cut -f1)
161:            echo "✅ Backup: ${LATEST} (${SIZE})"
189:            echo "Step 0: 自動ロールバック用 PREV_SHA 保存..."
191:            # .deploy_prev_sha は Finalize ステップ（別 SSH セッション）で読み取る
192:            PREV_SHA=$(git rev-parse HEAD 2>/dev/null || echo "")
193:            echo "${PREV_SHA}" > .deploy_prev_sha
194:            echo "  PREV_SHA=${PREV_SHA:0:7}"
196:            echo "Step 1: Pulling latest code from GitHub..."
383:        if: ${{ success() && steps.changes.outputs.nginx == 'true' }}
464:        if: ${{ success() && steps.changes.outputs.migrations == 'true' }}
485:        if: ${{ success() && steps.changes.outputs.migrations == 'true' }}
512:          envs: SALESANCHOR_API_TOKEN,SALESANCHOR_API_URL,ROLLBACK_DISCORD_WEBHOOK,PO_LIVE_OK,FEDEX_SMOKE_ENABLED
528:              _webhook="${ROLLBACK_DISCORD_WEBHOOK:-}"
542:          ROLLBACK_DISCORD_WEBHOOK: ${{ secrets.DISCORD_WEBHOOK_OWNER_PING }}
555:          ROLLBACK_DISCORD_WEBHOOK: ${{ secrets.DISCORD_WEBHOOK_OWNER_PING }}
560:          envs: ROLLBACK_DISCORD_WEBHOOK
565:            if [ "${{ steps.changes.outputs.migrations }}" != "true" ]; then
569:            echo "Step 6: Health check (with auto-rollback)..."
570:            # ADR-115: ヘルスチェック失敗時は PREV_SHA に自動ロールバックする。
585:              echo "❌ Health check failed — starting auto-rollback..."
586:              PREV_SHA=$(cat .deploy_prev_sha 2>/dev/null || echo "")
587:              _rollback_result="failed"
589:              if [ -n "${PREV_SHA}" ]; then
590:                echo "→ Rolling back to ${PREV_SHA:0:7}..."
591:                git reset --hard "${PREV_SHA}"
...
```

**判定（事実）**: `deploy.yml` 内の自動ロールバック（ADR-115, `.github/workflows/deploy.yml:570-646`）は `git reset --hard "${PREV_SHA}"`（`.github/workflows/deploy.yml:591`）によるコードのロールバックのみで、DBをpre-deploy backupから復元する処理は存在しない。`scripts/` 配下にもDB復元を伴う rollback スクリプトは見つからなかった（`grep -rn -i "restore\|rollback" scripts/` で `scripts/backup.sh` 自身と `deploy.yml` 以外のDB復元ロジックなし、下記参照）。

```
$ grep -rln -i "restore\|rollback" scripts/
scripts/backup.sh
```

```
$ grep -n -i "restore\|rollback" scripts/backup.sh
```
（backup.sh内に restore/rollback の文字列ヒットなし = バックアップ取得専用スクリプトで、復元処理は同スクリプト内に存在しない）

補足: `scripts/restore.sh`（`scripts/backup.sh:7` のコメントで言及）は存在するが、`.github/workflows/*.yml` のいずれからも呼び出されていない（`grep -n "restore.sh" .github/workflows/*.yml` はヒットなし）。手動実行専用で、deploy.yml の自動フローには組み込まれていない。`scripts/test_rollback_simulation.sh` は `.github/workflows/test-rollback.yml:39` から呼ばれるが、これはSA-18 Phase2のDATABASE_URLフォールバック検証用であり、DBデータのバックアップ復元とは無関係。

**結論: migrationsなしデプロイでDBをpre-deploy backupから復元する自動ロールバック経路はゼロ件。STOP条件に該当しない。**

## 4. 空き容量チェック（PR #3945由来）の毎回実行要件

`.github/workflows/deploy.yml:140-152`（変更前、backupステップ内）の `MIN_FREE_GB=5` ブロックは2026-10-02のprod1ディスクフル事故対応で追加された。本設計の変更範囲:このブロックをbackupステップから分離し、常時実行の新規ステップ「Check free disk space」に移設する（migrationsの有無に関わらず毎回実行、backupステップのみ条件付きスキップ）。

## 5. 2026-10-02 のデプロイ件数・migration有無の実測

`origin/main` の2026-10-02 00:00〜2026-10-03 00:00 (JST想定, gitのコミット日時ベース) の `--first-parent --merges` 件数:

```
$ git log --since="2026-10-02 00:00" --until="2026-10-03 00:00" --first-parent origin/main --merges --oneline | wc -l
25
```

このうち `migrations/` 配下に変更があったマージ（`git diff <merge>^1..<merge> --name-only` で判定、`--merges --name-only` は first-parent diffが空になるため不使用）:

```
287968fb2 Merge pull request #3941 from shingo-ops/release/payment-fee-column-docs   → migrations_changed=1
114364cf2 Merge pull request #3937 from shingo-ops/release/drop-discord-inventory-tables → migrations_changed=1
6aa85e420 Merge pull request #3930 from shingo-ops/release/payment-fee-settings      → migrations_changed=1
```

**事実**: 2026-10-02の全マージ25件中、`migrations/` に変更があったのは3件（12%）。PO発言「20+ deploys, few with migrations」と整合（本リポジトリでの「デプロイ」はmainへのマージ=push契機であり、マージ件数25 ≈ デプロイ発火回数）。

## 6. ADR参照

- ADR-135: 不可逆操作・デプロイガバナンス（本番Docker volume削除等の最終判断）
- ADR-136: 危険PRのGO手順（番号付きGO必須）
