# Pre-deploy DB backup — フィルタ絞り込み — Design

**日付**: 2026-10-03
**ブランチ**: release/predeploy-backup-db-filter
**Recon**: [recon.md](recon.md)
**前提PR**: #3953（MERGED）
**PO承認**: 2026-10-03「y」— pre-deploy DB backupは「デプロイが実際にDBスキーマ/データをマイグレーションで変更する場合」のみ実行する
**ADR参照**: ADR-135（不可逆操作・デプロイガバナンス）、ADR-136（危険PRのGO手順）

---

## 1. 目的

PR #3953 は Pre-deploy DB backup を `steps.changes.outputs.migrations == 'true'` の場合のみ実行するよう変更したが、この `migrations` フィルタは `scripts/**`・`backend/**` 全体を含む広い判定（recon.md §1）であり、recon.md §5 の実測で2026-10-02 JSTのマージ25件中16件（64%）が該当する一方、実際に 「migrations/*.sql」 を変更したのは3件（12%）のみだった。backupが不要な52%のデプロイ（backend/scriptsのみの変更）でも毎回 `scripts/backup.sh` を実行しており、recon.md §2 で確認した「実際にDBへ書き込むステップはRun database migrationsのみ」という事実と条件がズレている。本PRで判定条件をDBスキーマ/データを実際に変更するパスのみに絞り込む。

**利用者に見える変化**: なし（本番アプリの挙動に影響しない、CI内部処理のみ）。
**開発者に見える変化**: `migrations/**`・`scripts/run_all_migrations.sh`・「scripts/migrate_*.py」 以外の変更（backend/**のアプリコードのみ等）では「Pre-deploy DB backup」がskippedになる。「Run database migrations」ステップの実行条件（`migrations` フィルタ）は変更しない。

---

## 2. 対象と対象外

### 対象
- `.github/workflows/deploy.yml:33-57`: `dorny/paths-filter` の `filters:` に新規output `db_migrations` を追加（`migrations/**`、`scripts/run_all_migrations.sh`、「scripts/migrate_*.py」）
- `.github/workflows/deploy.yml:163`（旧行、PR #3953基準）: 「Pre-deploy DB backup」ステップの `if:` を `steps.changes.outputs.migrations == 'true'` → `steps.changes.outputs.db_migrations == 'true'` に変更

### 対象外（recon.md で確認済み・変更しない）
- 既存 `migrations` フィルタ自体、および「Run database migrations」ステップ（`.github/workflows/deploy.yml:486`）・「Post-deploy smoke tests」ステップ（`.github/workflows/deploy.yml:507`）・Finalizeステップ内の判定（`.github/workflows/deploy.yml:587`）: いずれも `migrations` output を引き続き参照する。recon.md §4 で確認した通り、新規output追加はこれらに無影響。
- 「Check free disk space」ステップ（PR #3945由来、`.github/workflows/deploy.yml:128-153`）: 変更なし、全デプロイで常時実行を維持。
- 「Bootstrap salesanchor_app role (idempotent)」ステップ（`.github/workflows/deploy.yml:423-483`）: recon.md §2 #1 で確認した通り冪等なロールパスワード再設定のみで、backup保護対象ではないため変更しない。
- `.github/workflows/workflow-lint.yml`: 変更しない（CLAUDE.md不可逆操作リストに該当）。
- `scripts/check-migration-registration-exists.sh`: DB書き込みがないためフィルタに含めない（recon.md §6）。

---

## 3. 変更内容

### 3-1. 新規filter output追加（`.github/workflows/deploy.yml`）

既存の `migrations:` / `nginx:` ブロックに加え、`db_migrations:` ブロックを追加:

```yaml
            db_migrations:
              - 'migrations/**'
              - 'scripts/run_all_migrations.sh'
              - 'scripts/migrate_*.py'
```

根拠（recon.md §2-3）:
- `migrations/**`: `run_sql` が直接実行する 「.sql」 ファイル本体。
- `scripts/run_all_migrations.sh`: マイグレーション実行の唯一の経路（SSoT、ファイル先頭コメントに明記）。新規マイグレーション追加は必ずこのファイルへの追記を伴う。
- 「scripts/migrate_*.py」: `run_py` が実行する個別マイグレーションスクリプト本体。既存マイグレーションの内容修正（新規登録行を追加せず既存「.py」だけを直す場合）を捕捉するため、「run_all_migrations.sh」 単独では不十分であり本パターンを追加する。

### 3-2. Pre-deploy DB backupステップのif条件変更

```yaml
      - name: Pre-deploy DB backup
        if: steps.changes.outputs.db_migrations == 'true'
```

バックアップ本体（`bash scripts/backup.sh` 以降）は変更なし。

---

## 4. 検証

| 基準 | 検証方法 |
|------|---------|
| 1) `migrations/` を含まない backend/** のみの変更を含むデプロイで、Pre-deploy DB backup ステップが skipped、Check free disk space ステップは実行される | 次回 backend/** のみ変更するPRがmainにマージされた際、Actions実行ログで「Check free disk space」が実行済み・「Pre-deploy DB backup」が `skipped` と表示されることを確認 |
| 2) `migrations/` を含むデプロイで Pre-deploy DB backup が実行される | 次回 「migrations/*.sql」 を含むPRがmainにマージされた際、Actions実行ログで両ステップとも実行済み・`✅ Backup: ...` ログが出力されることを確認 |
| 3) 「scripts/migrate_*.py」 のみ（migrations/*.sqlなし）を変更するデプロイでも backup が実行される | 次回該当パターンのPRがマージされた際に実測（現時点では該当PRなし・今後の観測待ち） |
| 4) actionlint / YAML loadが通る | 本PR作成時に `actionlint .github/workflows/deploy.yml` および `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/deploy.yml'))"` で確認済み（両方exit 0 / "YAML OK"） |
| 5) 2026-10-02 JST実測の再現性 | `git diff --name-only <sha>^1 <sha>` を25件のfirst-parent mergeに対して新フィルタのパターンで突合し、3/25が一致することを確認済み（recon.md §5） |

### 外部・過去事例

該当なし。理由: 本変更は自社CI（GitHub Actions + dorny/paths-filter + 自前SSHスクリプト）特有のフィルタパス定義の絞り込みであり、一般的なCIパターン（「複数output・複数フィルタで条件を細分化する」こと自体はdorny/paths-filterの標準機能）の範囲内。PR #3953で導入したmigrationsゲーティングパターンを、同じツール内でパスのスコープだけ絞り込むものであり、個別の外部事例調査は不要と判断。

---

## 5. リスクと戻し方

### リスク
- 「scripts/migrate_*.py」 のglobパターンはサブディレクトリを含まない（「scripts/migrate_*.py」 は `scripts/` 直下のみ一致）。recon.md §3 の実測で 「run_all_migrations.sh」 が参照する全 `run_py` 対象（28件）が `scripts/` 直下に平坦に配置されていることを確認済みのため、現状は問題ないが、将来 `scripts/migrations/` 等のサブディレクトリにマイグレーションスクリプトが追加された場合はこのパターンから漏れる。
  - 緩和: 新規マイグレーション追加は必ず `scripts/run_all_migrations.sh` への追記を伴う（SSoT）ため、`scripts/run_all_migrations.sh` 自体の変更で `db_migrations` は `true` になる。純粋な新規追加では漏れない。リスクが残るのは「既存の 「.py」 を将来サブディレクトリに移動し、同時に内容も変更する」複合変更のみ。
- 判定ロジックのバグにより `db_migrations` が実際はtrueであるべきなのにfalseになった場合、backupなしでmigrationsが適用されるリスクがある。
  - 緩和: 「Run database migrations」ステップ自体の実行条件（`migrations` output）は本PRで変更しない。`migrations` フィルタは `backend/**`・`scripts/**` 全体を含む広い判定を維持しており（ADR-082の「判定不能時は安全側=実行」設計）、migrations実行自体がskipされるリスクは本PRで増加しない。backupの判定が厳格化されるだけで、migrations実行自体の安全側設計は変わらない。

### 戻し方
- `git revert <本PRのマージコミット>` で `db_migrations` output と `if` 条件変更を元に戻せば、PR #3953時点の挙動（`migrations` フィルタで判定）に即復帰する。

---

## 6. 維持の仕組み

- `db_migrations` フィルタのパスリストは `scripts/run_all_migrations.sh` のSSoT構造（新規マイグレーション追加は必ずこのファイルへの追記を伴う）に依存しており、運用ルールが変わらない限り追従する。
- 守り手: `.github/workflows/deploy.yml`（本ファイル自体の変更はPR作成者が必ず目視する対象であり、`migrations` フィルタに `.github/workflows/deploy.yml` 自体が含まれているため、deploy.yml変更時は「Run database migrations」の実行条件は引き続き `true` になりCIで検証される。`db_migrations` フィルタ自体は `.github/workflows/deploy.yml` を含まないため、deploy.yml変更のみではbackupは走らないが、これは意図通り（deploy.yml変更自体はDBスキーマ/データを変更しない）。
- 将来 `scripts/` 配下のマイグレーションスクリプト配置規約が変わる場合（例: サブディレクトリ化）は、本designのリスク§5を踏まえ `db_migrations` フィルタのパターンも合わせて見直す必要がある。

---

## 7. ロールアウト

- 本PRはCI（actionlint, yaml load）確認済みの上でDraftとして起票。
- マージにはPO本人の「GO #<PR番号>」が必要（CLAUDE.md ADR-136手順）。GO未受領の間はDraft維持。
