# Pre-deploy DB backup on migrations only — Design

**日付**: 2026-10-03
**ブランチ**: release/predeploy-backup-on-migrations
**Recon**: [recon.md](recon.md)
**PO承認**: 2026-10-03「y」— デプロイに DB migration が含まれる場合のみ pre-deploy DB backup を取得する
**ADR参照**: ADR-135（不可逆操作・デプロイガバナンス）、ADR-136（危険PRのGO手順）

---

## 1. 目的

`.github/workflows/deploy.yml` の「Pre-deploy DB backup」ステップ（`.github/workflows/deploy.yml:127` 旧行）は、DBマイグレーションを含まないデプロイ（フロントのみ・ドキュメントのみ等）でも毎回 `scripts/backup.sh` を実行していた。recon.md §5の実測で2026-10-02のマージ25件中migration変更ありは3件（12%）のみであり、残り88%は不要なバックアップ処理（ディスクI/O・容量消費）を毎回行っていた。PO承認（2026-10-03「y」）に基づき、バックアップ取得をmigrationsを含むデプロイに限定する。

**利用者に見える変化**: なし（本番アプリの挙動に影響しない、CI内部の処理のみ）。
**開発者に見える変化**: migrationsなしのデプロイでは「Pre-deploy DB backup」ステップがskippedとして表示される。空き容量チェックは新規ステップ「Check free disk space」として独立し、全デプロイで引き続き実行される。

---

## 2. 対象と対象外

### 対象
- `.github/workflows/deploy.yml`: 「Pre-deploy DB backup」ステップに `if: steps.changes.outputs.migrations == 'true'` を追加
- `.github/workflows/deploy.yml`: 空き容量チェック（`MIN_FREE_GB=5` ブロック、PR #3945由来）をbackupステップから分離し、常時実行の新規ステップ「Check free disk space」に移設

### 対象外
- 日次バックアップ（cron 3:00、`scripts/backup.sh` 自体）とS3転送: 変更なし（recon.md §4で確認した通り、deploy.yml内の処理のみが対象）
- `.github/workflows/workflow-lint.yml`: 変更しない（CLAUDE.md不可逆操作リストに該当するため）
- 自動ロールバック（ADR-115, `.github/workflows/deploy.yml:570-646`）: 変更なし。recon.md §3で確認した通り、この経路はDBをbackupから復元しない（`git reset --hard` によるコードロールバックのみ）ため、本変更の影響範囲外。

---

## 3. 変更内容

### 3-1. ステップ分離・条件追加（`.github/workflows/deploy.yml`）

- 新規ステップ「Check free disk space」を「Pre-deploy DB backup」の直前に追加し、`MIN_FREE_GB=5` の空き容量チェックブロックをそのまま移設（ロジック変更なし・毎回実行）。
- 「Pre-deploy DB backup」ステップに `if: steps.changes.outputs.migrations == 'true'` を追加（`steps.changes` は recon.md §1 で確認した既存の `id: changes` ステップ、`migrations` は同ステップの既存output名）。
- バックアップ本体（`bash scripts/backup.sh` 以降、LATEST特定・サイズ表示）は変更なし。

### 3-2. 他ステップへの影響

recon.md §1-2 で確認した通り、「Pre-deploy DB backup」ステップには `id:` が設定されておらず、他のどのステップもこのステップの `outputs` を参照していない。したがって `if` 追加によるスキップに対する互換対応（outputs不在への耐性）は不要。

---

## 4. リスクと戻し方

### リスク
- migrationsなしのデプロイでbackupがskipされるため、「migrationsの判定ロジック自体にバグがあり、実際はmigrationsを含むのに `migrations` output が `false` になる」場合、バックアップなしでmigrationsが適用されるリスクがある。
  - 緩和: `migrations` フィルタは `backend/**` 全体・`scripts/**` 全体・`docker-compose.yml`・`.github/workflows/deploy.yml` 自体も対象にしており（recon.md §1）、判定不能時は安全側（実行）に倒す既存ADR-082設計を継続利用。新規リスクの追加ではない。

### 戻し方
- `git revert <本PRのマージコミット>` で `if` 条件とステップ分離を元に戻せば、全デプロイで毎回backupを取る旧挙動に即復帰する。
- 空き容量チェックは独立ステップとして残るため、revert後も「Check free disk space」→「Pre-deploy DB backup（条件なし）」の順に実行され、チェック自体が失われることはない。

---

## 5. 検証方法

| 基準 | 検証方法 |
|------|---------|
| 1) migrationsなしのdeployでbackupステップがskipされ、free-spaceステップは実行される | 次回migrationsを含まないPRがmainにマージされた際、Actions実行ログで「Check free disk space」が実行済み・「Pre-deploy DB backup」が `skipped` と表示されることを確認 |
| 2) migrationsありのdeployでbackupが実行される | 次回migrationsを含むPRがmainにマージされた際、Actions実行ログで両ステップとも実行済み・`✅ Backup: ...` ログが出力されることを確認 |
| 3) ローカルのバックアップファイル件数が10件以下を維持 | `ssh salesanchor-claude <VPS_HOST> "ls /home/ubuntu/backups/postgres/salesanchor_db_*.sql.gz | wc -l"` で定期確認（日次cronの `RETENTION_DAYS=30` ローテーションと合わせ、deploy起因の積み増し頻度が下がることを確認） |

### 外部・過去事例

該当なし。理由: 本変更は自社CI（GitHub Actions + 自前SSHスクリプト）特有の構成に対する条件分岐追加であり、一般的なパターン（「migration検出で後続ステップをスキップする」こと自体はdorny/paths-filterの標準的な使い方）のため、個別の外部事例調査は不要と判断（ADR-082で同種のmigrationsゲーティングパターンが既に採用されており、今回はそのパターンをbackupステップに拡張するのみ）。

---

## 6. 維持の仕組み

- 本変更はYAMLの `if:` 条件のみで、新たな環境変数・Secretは追加しない。既存の `steps.changes.outputs.migrations` を再利用するため、ADR-082のmigration検知ロジックが変わらない限り本変更は自動的に追従する。
- 空き容量チェック（ADR-135/136由来、PR #3945）を独立ステップに分離したことで、今後backupステップの条件がさらに変わっても空き容量チェックが連動して失われるリスクを構造的に排除した。
- 守り手: `.github/workflows/deploy.yml`（本ファイル自体がmigrationsフィルタ対象に含まれているため、deploy.yml変更時は必ずmigrations判定が`true`になりCIで検証される）

---

## 7. ロールアウト

- 本PRはCI（actionlint, yaml load）確認済みの上でDraftとして起票。
- マージにはPO本人の「GO #<PR番号>」が必要（CLAUDE.md ADR-136手順）。GO未受領の間はDraft維持。
