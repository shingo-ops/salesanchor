# 実装カード: 便1a 登録の表に用途 purpose を足す（移行だけ・プログラムは変えない）

- 設計: docs/handoff/discord-server-management/design.md §4-1 改訂1・§5（Architect 自己審査 APPROVE）
- PO 承認: 「1」（2026-11-04、この設計で承認し、自社用サーバーの登録から作り始める）
- ブランチ: release/discord-own-server-bin1a（origin/main 7d56ab771 に設計の文書を足したもの。実際の先頭は Opus が依頼文で伝える）
- 触ってよいファイル（この 2 つと報告書 docs/handoff/discord-server-management/impl-report-bin1a.md だけ）:
  - migrations/20261105_100000_tenant_discord_config_purpose.sql（新規）
  - scripts/run_all_migrations.sh（末尾に 2 行足すだけ）
- 触らない: backend・frontend・i18n・openapi.json・ほかの migrations・.github・deploy.yml・本番

## 読んだ節（guards/）

- docs/handoff/design-partner-card-ops/guards/00-common.md：報告は生出力・推測で埋めない → 報告書に生出力を貼る形にした
- docs/handoff/design-partner-card-ops/guards/03-file.md：触るファイルを列挙 → 上の 2 つと報告書だけ
- docs/handoff/design-partner-card-ops/guards/05-pr.md：PR は Opus が作る → 実行役は push まで
- docs/handoff/design-partner-card-ops/guards/07-migration.md：置くだけでは MIGRATION GUARD が落ちる → run_all_migrations.sh の末尾に登録する。採番は直近を実測（origin/main の最後は 20261103_200000）。migrations は CODEOWNERS 承認と GO の両方が要る（マージは Opus と PO 側）
- docs/handoff/design-partner-card-ops/guards/10-executor.md：作業前に preflight → 下の §0

## 受領確認

作業を始める前に、報告書の先頭に次の 3 行を書く:
- 受領確認: card-bin1a-purpose-column.md を読んだ
- origin/release/discord-own-server-bin1a の先頭 sha（git rev-parse の生出力）
- 触るファイルは 2 つと報告書だけ、と理解した

## §0 準備

- リポジトリの根で `./scripts/dev/executor-preflight.sh` を流し、生出力を報告書に貼る。失敗したら停止して BLOCKED で報告
- `git fetch origin` のあと `release/discord-own-server-bin1a` を取り出す（新しく作らない）

## §1 migrations/20261105_100000_tenant_discord_config_purpose.sql（新規）

中身はこのとおり（1 文字も変えない）:

```sql
-- discord-server-management 便1a: 登録の表に用途 purpose を足す（足すだけ・冪等）
--
-- 設計: docs/handoff/discord-server-management/design.md §4-1 改訂1
-- 目的: 1 社が顧客用と自社用の 2 つのサーバーを登録できるようにする前段。
--       今の行はすべて既定値 'customer' になり、今のプログラムはこの列を知らなくても動く。
--       主キー (tenant_id) は便1b で (tenant_id, purpose) に替える。
-- ロック待ち: run_all_migrations.sh の run_sql が PGOPTIONS で lock_timeout を付ける（既定 1s・ADR-1037）。
--
-- ロールバック（この順）:
--   ALTER TABLE public.tenant_discord_config DROP CONSTRAINT IF EXISTS uq_tenant_discord_config_tenant_purpose;
--   ALTER TABLE public.tenant_discord_config DROP CONSTRAINT IF EXISTS ck_tenant_discord_config_purpose;
--   ALTER TABLE public.tenant_discord_config DROP COLUMN IF EXISTS purpose;

ALTER TABLE public.tenant_discord_config
    ADD COLUMN IF NOT EXISTS purpose VARCHAR(16) NOT NULL DEFAULT 'customer';

DO $tdc_purpose$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM   pg_constraint
        WHERE  conname = 'ck_tenant_discord_config_purpose'
          AND  conrelid = 'public.tenant_discord_config'::regclass
    ) THEN
        ALTER TABLE public.tenant_discord_config
            ADD CONSTRAINT ck_tenant_discord_config_purpose CHECK (purpose IN ('customer', 'own'));
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM   pg_constraint
        WHERE  conname = 'uq_tenant_discord_config_tenant_purpose'
          AND  conrelid = 'public.tenant_discord_config'::regclass
    ) THEN
        ALTER TABLE public.tenant_discord_config
            ADD CONSTRAINT uq_tenant_discord_config_tenant_purpose UNIQUE (tenant_id, purpose);
    END IF;
END
$tdc_purpose$;
```

## §2 scripts/run_all_migrations.sh

ファイルの最後の `run_sql` の行は今これ（origin/main で実測）:

```
run_sql migrations/20261103_200000_add_google_calendar_import_sync.sql
```

この行のすぐ次に 2 行足す（ほかは 1 文字も変えない）:

```
# discord-server-management 便1a: 登録の表に用途 purpose（既定 customer）・決まり・(tenant_id, purpose) の一意を足す（足すだけ・冪等）
run_sql migrations/20261105_100000_tenant_discord_config_purpose.sql
```

最後の run_sql がこの行でなかったら（ほかの PR が先に足していたら）、その最後の run_sql の次に足し、報告書にその行を書く。

## §3 確かめ

- `bash -n scripts/run_all_migrations.sh` の生出力（何も出なければ「出力なし」と書く）
- `grep -n "20261105_100000_tenant_discord_config_purpose" scripts/run_all_migrations.sh` の生出力（1 行だけのはず）
- `git diff --stat origin/main` の生出力
- 手元に PostgreSQL があれば、空の表に流して 2 回目も失敗しない（冪等）ことを確かめ、生出力を貼る。無ければ「PostgreSQL なし・CI の migration-test に任せる」と書く

## §4 保存

- commit の文: `feat(db): tenant_discord_config に用途 purpose を足す（discord-server-management 便1a）`
- commit のあと `git log --oneline -3` の生出力を報告書に貼る
- `git push origin release/discord-own-server-bin1a`（単独で流す）。PR は作らない（Opus が作る）
- 報告書の最後に、push 後の `git rev-parse HEAD` の生出力

## 想定分岐（停止の条件）

- preflight が失敗した → 停止。BLOCKED: と生出力
- migrations/ に 20261105_100000 で始まるファイルが既にある → 停止。BLOCKED: とファイル名
- run_all_migrations.sh の末尾の形が「run_sql migrations/…」の並びでない → 停止。BLOCKED: と末尾 20 行
- 触ってよいファイル以外を変えたくなった → 変えずに停止。NEEDS_DECISION: と理由
- push が拒否された → 言い換えて再試行しない。停止して BLOCKED: と生出力

報告の最後の行は DONE / BLOCKED: 理由 / NEEDS_DECISION: 理由 のどれか 1 つ。

END OF CARD
