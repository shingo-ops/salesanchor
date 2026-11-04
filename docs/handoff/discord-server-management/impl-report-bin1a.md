本報告はカード card-bin1a-purpose-column の実行結果である

## 受領確認

- 受領確認: card-bin1a-purpose-column.md を読んだ
- origin/release/discord-own-server-bin1a の先頭 sha（git rev-parse の生出力）: `e71a7a4b3e886508fd5968312bcc8e22ffabada1`（作業開始時の HEAD も同じ値で一致）
- 触るファイルは 2 つと報告書だけ、と理解した

## preflight の生出力（クラウド実行・rc=1）

```
== executor preflight (identity=shingo-cc, mode=fix) ==
[1/3] network -> api.github.com
  [FAIL] GitHub API に到達不可。Mac回線ではなく実行役サンドボックスの通信OFFが濃厚。
       => Codexをネット有効で起動 (信頼repo内: codex --sandbox danger-full-access / または config の network_access=true)
[2/3] gh auth = shingo-cc
  [warn] gh の active account が shingo-cc でない。gh auth switch で切り替え試行...
  [FAIL] gh auth switch --hostname github.com --user shingo-cc に失敗。gh auth status --active で現状を確認。
[3/3] git config user.name = shingo-cc
  [OK]   git user.name を shingo-cc に設定
[4/4] long-lived branch -> origin/main
  [OK]   origin/main は存在
==============================================
PREFLIGHT FAIL — 上の対策を実施し再実行(深追いしない)
```

カード §0（クラウド）により [1/3][2/3] の FAIL は貼るだけで進み、[3/3][4/4] は OK なので続行した。

## git diff origin/main...HEAD（該当 2 ファイル）

### scripts/run_all_migrations.sh

```
@@ -1215,3 +1215,5 @@ run_sql migrations/20261103_120000_create_ai_job_assignments.sql
 run_sql migrations/20261103_150000_create_user_notices.sql
 # ADR-1059 便2: Google の予定の取り込み（列2つ・一意の部分索引・追加のみ・冪等）
 run_sql migrations/20261103_200000_add_google_calendar_import_sync.sql
+# discord-server-management 便1a: 登録の表に用途 purpose（既定 customer）・決まり・(tenant_id, purpose) の一意を足す（足すだけ・冪等）
+run_sql migrations/20261105_100000_tenant_discord_config_purpose.sql
```

最後の run_sql は、カードに書かれた 20261103_200000 の行のままだった。

### migrations/20261105_100000_tenant_discord_config_purpose.sql

新規 39 行。中身はカード §1 の SQL ブロックと同じ（Write ではなく区切りを引用符で囲んだ heredoc で書いた）。差分の全文は次のコマンドで取れる:
`git diff origin/main...HEAD -- migrations/20261105_100000_tenant_discord_config_purpose.sql`

## 点検の生出力（カード §3）

`bash -n scripts/run_all_migrations.sh`

```
（出力なし・rc=0）
```

`grep -n "20261105_100000_tenant_discord_config_purpose" scripts/run_all_migrations.sh`

```
1219:run_sql migrations/20261105_100000_tenant_discord_config_purpose.sql
```

`git diff --stat origin/main`（末尾 3 行。この枝は設計文書の枝で、origin/main が先へ進んでいるため、docs 等の差も並ぶ。今回の変更は下の 2 ファイルだけ）

```
 ...261105_100000_tenant_discord_config_purpose.sql |  39 +++
 scripts/run_all_migrations.sh                      |   2 +
 16 files changed, 629 insertions(+), 615 deletions(-)
```

### PostgreSQL での冪等の確認

クラウドに PostgreSQL サーバーがあったので、localhost:55432 に使い捨てを立てて流した（本番・外部には接続していない）。

```
CREATE TABLE
INSERT 0 1
== run1
ALTER TABLE
DO
rc=0
== run2
psql:migrations/20261105_100000_tenant_discord_config_purpose.sql:15: NOTICE:  column "purpose" of relation "tenant_discord_config" already exists, skipping
ALTER TABLE
DO
rc=0
 ok | purpose
----+----------
 t  | customer
(1 row)

                           Table "public.tenant_discord_config"
  Column   |         Type          | Collation | Nullable |            Default
-----------+-----------------------+-----------+----------+-------------------------------
 tenant_id | uuid                  |           | not null |
 guild_id  | text                  |           |          |
 purpose   | character varying(16) |           | not null | 'customer'::character varying
Indexes:
    "tenant_discord_config_pkey" PRIMARY KEY, btree (tenant_id)
    "uq_tenant_discord_config_tenant_purpose" UNIQUE CONSTRAINT, btree (tenant_id, purpose)
Check constraints:
    "ck_tenant_discord_config_purpose" CHECK (purpose::text = ANY (ARRAY['customer'::character varying, 'own'::character varying]::text[]))

ERROR:  new row for relation "tenant_discord_config" violates check constraint "ck_tenant_discord_config_purpose"
rc(bad)=1
```

2 回目も rc=0（冪等）。既存行は 'customer' になり、不正な用途 'bad' は決まりで拒否された。確かめに使った表は、本番の表の定義ではなく、tenant_id と guild_id だけの簡易版（実表の全列では未確認。CI の migration-test に任せる）。

後片付け: テスト用 PostgreSQL は停止した。データ領域 /var/tmp/pgd1a の削除（rm -rf）は見張りに止められたので、言い換えず実行していない（使い捨て環境のため残置）。

## git log --oneline -3（コード commit 直後）

```
79dc34d72 feat(db): tenant_discord_config に用途 purpose を足す（discord-server-management 便1a）
e71a7a4b3 docs: 便1a カードにクラウドでの preflight の扱いを足す
aa581a653 Merge branch 'release/discord-own-server-design' into release/discord-own-server-bin1a
```

## 最終 HEAD

コード commit は `79dc34d72`。この報告書を足した commit の sha は報告書自身には書けないため、push 後の `git rev-parse HEAD` の生出力は依頼元への返信に書く。

DONE
