# Pre-deploy DB backup — フィルタ絞り込み — Recon

**日付**: 2026-10-03
**ブランチ**: release/predeploy-backup-db-filter
**前提PR**: #3953（MERGED・`release/predeploy-backup-on-migrations`）— `steps.changes.outputs.migrations == 'true'` の場合のみ Pre-deploy DB backup を実行するよう変更済み
**ADR参照**: ADR-135（不可逆操作・デプロイガバナンス）、ADR-136（危険PRのGO手順）

---

## 1. deploy.yml の paths-filter 定義（現状）

`/Users/tanizawashingo/worktrees/salesanchor/release-llm-usage-charts/.github/workflows/deploy.yml:33-46`（PR #3953 マージ後の origin/main、`3e9bd0ced`時点）:

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

Pre-deploy DB backup ステップ（`.github/workflows/deploy.yml:162-163`）:

```yaml
      - name: Pre-deploy DB backup
        if: steps.changes.outputs.migrations == 'true'
```

`migrations` フィルタは `scripts/**`・`backend/**` 全体を含むため、DBに一切書き込まないアプリケーションコードの変更（例: フロントAPI呼び出し先の修正、ロギング追加等）でも `true` になり、backup が走る。

---

## 2. deploy.yml 内で本番DBへ書き込むステップの全列挙

`.github/workflows/deploy.yml` 全977行を走査。SSH越しに `psql`／`ALTER`／`INSERT`／`UPDATE`／`DELETE`／マイグレーションスクリプトを実行する箇所は以下の3箇所のみ。

| # | ステップ名 | 行番号 | `if:` 条件 | 書き込み内容 | backupで保護すべきか |
|---|-----------|--------|-----------|--------------|---------------------|
| 1 | Bootstrap salesanchor_app role (idempotent) | `.github/workflows/deploy.yml:423-483` | `${{ success() }}`（毎回実行） | `ALTER ROLE salesanchor_app PASSWORD '...'`（`.github/workflows/deploy.yml:439-442`）。パスワードを現在のSecret値に冪等に再設定するだけで、スキーマ・データは変更しない。コメント（`.github/workflows/deploy.yml:424-427`）にも「全デプロイで実行（冪等・副作用なし）」と明記。 | **不要**。ロール名/権限を破壊しない冪等操作であり、ロールバック対象になるデータ変更が発生しない。 |
| 2 | Run database migrations | `.github/workflows/deploy.yml:485-503` | `${{ success() && steps.changes.outputs.migrations == 'true' }}` | `bash scripts/run_all_migrations.sh` を実行（下記§3で詳述）。「migrations/*.sql」 の `run_sql` 実行、「scripts/migrate_*.py」 の `run_py` 実行により DDL/DML を適用。 | **必要**。スキーマ変更・データ変換が実際に起こる唯一のステップ。 |
| 3 | Verify deployment（ADR-045検証） | `.github/workflows/deploy.yml:717-794` | `${{ success() }}` | `DO $$ ... RAISE WARNING/EXCEPTION ... END $$` ブロック（`.github/workflows/deploy.yml:737-794`）。`SELECT COUNT(*)` と `information_schema` 参照のみで `INSERT`/`UPDATE`/`ALTER` は一切含まない。読み取り専用の検証。 | **不要**。書き込みなし。 |

結論: 本番DBのスキーマ/データを実際に変更するのは **ステップ#2（Run database migrations）のみ**。ステップ#1は冪等なロールパスワード再設定、ステップ#3は読み取り専用検証であり、いずれもバックアップで保護すべき対象ではない。

---

## 3. scripts/run_all_migrations.sh — 実行経路の確認

`/Users/tanizawashingo/worktrees/salesanchor/release-llm-usage-charts/scripts/run_all_migrations.sh:1-18`（ヘッダーコメント）:

```
# run_all_migrations.sh — 全DBマイグレーションを1本で実行する統合ランナー
#
# 目的:
#   deploy.yml の migration ステップ（旧 part 1 / part 2）を統合し、
#   「新マイグレーション追加時は deploy.yml ではなくこのファイルに追記する」を
#   唯一のルール（SSoT）にする。
# ...
#   - 全マイグレーションは冪等設計（何度実行しても安全）
#   - 新マイグレーションは末尾の「ここから追加」セクションに追加すること
```

実行関数（`scripts/run_all_migrations.sh:49-66`）:
- `run_py "$script"` → `docker exec ... python "${script}"`（「scripts/migrate_*.py」 を実行）
- `run_sql "$file"` → `docker exec -i ... psql ... < "${file}"`（「migrations/*.sql」 を実行）

実測（`grep -nE '^run_(sql|py)[[:space:]]' scripts/run_all_migrations.sh`、316件）: `run_sql` の対象は全て 「migrations/*.sql」（直下、サブディレクトリなし）。`run_py` の対象は全て 「scripts/migrate_*.py」（直下、サブディレクトリなし、例: `scripts/migrate_meta.py`, `scripts/migrate_adr109_status_codes.py` 等28件）。

→ **確認**: マイグレーションは 「migrations/*.sql」（`run_sql`）と 「scripts/migrate_*.py」（`run_py`）に登録されたものだけが適用される。両者とも `scripts/run_all_migrations.sh` 内に明示的に列挙されており、新規マイグレーション追加時は必ず `scripts/run_all_migrations.sh` への追記を伴う（SSoTコメントの通り）。

---

## 4. 他ステップが `migrations` output を参照している箇所（新規output追加の影響確認）

`grep -n "outputs\.migrations\|outputs\.nginx\|steps\.changes" .github/workflows/deploy.yml`:

```
160:      # （steps.changes.outputs.migrations が 'true' の場合のみ）。
163:        if: steps.changes.outputs.migrations == 'true'
405:        if: ${{ success() && steps.changes.outputs.nginx == 'true' }}
486:        if: ${{ success() && steps.changes.outputs.migrations == 'true' }}
507:        if: ${{ success() && steps.changes.outputs.migrations == 'true' }}
587:            if [ "${{ steps.changes.outputs.migrations }}" != "true" ]; then
```

全ての参照は `migrations` または `nginx` という既存output名を指定しており、`dorny/paths-filter` の新規output（`db_migrations`）を追加しても既存の `migrations`/`nginx` outputは変更されないため、上記6箇所はいずれも無影響（dorny/paths-filterは `filters:` に列挙した各トップレベルキーを個別のoutputとして出力する仕様であり、キー追加は既存outputに影響しない）。

→ **確認**: 新規output `db_migrations` を追加しても既存消費箇所（163行目を除く）は破壊されない。163行目（Pre-deploy DB backupのif条件）のみ本PRで `migrations` → `db_migrations` に変更する。

---

## 5. 2026-10-02 JST マージの実測（旧 `migrations` フィルタ vs 新 `db_migrations` フィルタ）

対象: `origin/main` 上の first-parent merge commit、2026-10-02T00:00+09:00〜2026-10-03T00:00+09:00（UTC: `2026-10-01T15:00:00Z`〜`2026-10-02T15:00:00Z`）。

```
git log origin/main --first-parent --merges --since="2026-10-01T15:00:00Z" --until="2026-10-02T15:00:00Z" --format='%H|%ad|%s' --date=iso-strict
```
→ 25件（#3945, #3946, #3944, #3939, #3941, #3937, #3940, #3934, #3938, #3936, #3935, #3927, #3933, #3930, #3932, #3929, #3928, #3912, #3926, #3925, #3923, #3924, #3922, #3921, #3920）。

各 `<sha>` について `git diff --name-only <sha>^1 <sha>` を取得し、2種のフィルタと照合。

**旧 `migrations` フィルタ**（`migrations/**` `scripts/**` `backend/**` `docker-compose.yml` `.github/workflows/deploy.yml`）: **16/25** が一致。

**新 `db_migrations` フィルタ**（`migrations/**` `scripts/run_all_migrations.sh` 「scripts/migrate_*.py」）: **3/25** が一致。

```
MATCH 287968fb26577fe3989a356d1bdbf7c653825fbe (#3941):
    migrations/20261002_180000_comment_payment_fee_settings_columns.sql
    scripts/run_all_migrations.sh
MATCH 114364cf2a045777972b126c01ca8be96600955d (#3937):
    migrations/20261002_170000_drop_discord_inventory_tables.sql
    scripts/run_all_migrations.sh
MATCH 6aa85e4209d3c702e24f58defd256ebc79d352d0 (#3930):
    migrations/20261002_160000_create_payment_fee_settings.sql
    scripts/run_all_migrations.sh
TOTAL MATCHES: 3 / 25
```

→ 新フィルタで一致した3件はいずれも実際に 「migrations/*.sql」 を追加しており、`scripts/run_all_migrations.sh` への追記（新規マイグレーションの登録）を伴っている。これは §3 で確認したSSoT構造と一致する。

### 訂正: PR #3953 本文の見積もり「1/8」について

PR #3953 の本文に記載された見積もり（検索語「1/8」相当の表現、該当PRのdraft時点メモ）は、実際にmigrations/を含む件数を過小/粗い抽出で見積もったものであり、本recon §5 の悉皆調査（25件全件を `git diff --name-only` で突合）とは手法が異なる。本recon の確定値は **25件中 旧フィルタ一致16件・実際にmigrations/を含むもの3件** であり、今回の `db_migrations` フィルタはこの3件を正確に再現する。

---

## 6. 対象外の確認

- `.github/workflows/workflow-lint.yml`: 変更しない（CLAUDE.md 不可逆操作リストに該当）。
- `scripts/check-migration-registration-exists.sh`（migrations実行前のpreflight検証、`scripts/run_all_migrations.sh:67-72` で呼び出し）: DBへの書き込みなし（登録済みファイルの存在確認のみ）。`db_migrations` フィルタに含める必要なし。
- `docker-compose.yml`: postgresサービス定義（`docker-compose.yml:425-430`）を含むが、`.github/workflows/deploy.yml` の「Deploy to VPS」ステップ（`.github/workflows/deploy.yml:197-388`）はpostgresコンテナを明示的に再作成しない（`docker compose up -d` の対象は frontend/celery-worker/celery-beat/discord-gateway/gemini-egress/node-exporter/promtail のみ、`.github/workflows/deploy.yml:379-381`）。したがって `docker-compose.yml` 変更だけではデプロイ時にpostgres設定が自動適用されず、`db_migrations` フィルタに含める根拠がない。
