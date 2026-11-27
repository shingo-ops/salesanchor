# review-architect-1: 試験用テナント（tenant_001）だけに書き込める AI の道（設計審査 第1回）

> 審査役: architect（クラウド、2026-11-27）。読むだけ。製品のコード・DB・本番には触れていない。
> 審査した物: `origin/release/dev-tenant001-writer-design` の `docs/handoff/dev-tenant001-writer/design.md`・`recon.md`（git show で全文）。
> 照らした正本: `origin/main` の ADR-1024・migrations・`backend/app/ops/readonly_query.py`・`docker-compose.ai-reader.yml`・`scripts/run_all_migrations.sh`・`scripts/check-process-artifacts.js`。

## 判定: REVISE

1. 境界（DB の権限で tenant_001 以外に書けない）という骨組みは ADR-1024 の型に沿っており、`SET LOCAL app.tenant_id` で RLS が開く前提も migrations の定義と合う。
2. ただし K5 の測り方が、PostgreSQL の `information_schema.role_table_grants` の定義上、別のロールの権限を数えられず、○×が出ない。比べる「設計の一覧」も設計の中に無い。
3. PUBLIC から受け継ぐ権限・秘密列の拒否の型・危険パスの登録・migration の登録の手順に抜けがあり、このまま便2に渡すと穴か、作れない・壊れる物が出る。

## 1. 行番号と中身の照合（見る点 1）

| 書いてある所 | 実物 | 結果 |
|---|---|---|
| design.md:28 `migrations/20261017_130000_create_ai_reader_role.sql:12` | 同ファイル:12 が `CREATE ROLE ai_reader LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS CONNECTION LIMIT 2;` | 合う |
| recon.md:7 ADR-1001:136 | `docs/adr/ADR-1001-deprecate-tcg-products-unify-to-public.md:136`「対象スキーマ: tenant_004（本番）+ tenant_001（QA）」 | 合う |
| recon.md:8 ADR-1051:19 | `docs/adr/ADR-1051-prod-ui-black-box-check.md:19` tenant_001 に点検専用の人を作った | 合う |
| recon.md:9 ADR-1085:16 | `docs/adr/ADR-1085-browser-operation-delegation.md:16` 部屋 A に「自社アプリの tenant_001 だけの利用者」 | 合う |
| recon.md:47 `backend/app/tasks/discord_own_staff_sync.py:1-4` | 同:1-3 が 5 分ごと・purpose='own' の全テナント | 合う |
| recon.md:48 `backend/app/tasks/google_calendar_sync.py:1-5` | 同:1-5 が Google → アプリの取り込み・15 分おき | 合う |
| recon.md:32 `sync_meta_page_routing()` が SECURITY DEFINER で public.meta_page_routing を書く | `migrations/044_create_meta_page_routing_trigger.sql:37-79`、新テナント用の同じ定義 `backend/app/services/tenant.py:2782-2826` | 合う |
| design.md:56 ロック待ち 1 秒は ADR-1037 と同じ値 | `docs/adr/ADR-1037*:16` は `lock_timeout=1s` | 合う |
| recon.md:25-30 の生出力 q1〜q8.tsv | `/tmp/CC報告ファイル/dev001/` はリポジトリに無く、この審査では確かめられない | 未確認 |

## 2. 権限の穴の確認（見る点 2）

migrations を検索した結果（`origin/main`）:

- SECURITY DEFINER: migrations の中は 2 か所だけ。`migrations/044_create_meta_page_routing_trigger.sql:40`（引き金の関数。設計は表 `tenant_meta_config` を除外して対処済み）と `migrations/20261031_210000_create_ops_case.sql:235`（`ops_case.unmask_fetch`。:485 で `REVOKE ALL ... FROM PUBLIC`、:489 で ai_unmask にだけ EXECUTE。`ops_case` のスキーマも :10 で PUBLIC から外している）。migrations の外に `backend/app/services/tenant.py:2786`（同じ引き金の関数を新テナント作成で作る）がある。
- 引き金の関数は直接呼べない（引き金としてだけ動く）ので、`tenant_001.sync_meta_page_routing()` を書き込み役が呼んで public を書く道は、表の除外で閉じる。
- ALTER DEFAULT PRIVILEGES: `migrations/20260605_030000_create_salesanchor_app_role.sql:21,23`（public、相手は salesanchor_app）と `migrations/20260605_040000_grant_salesanchor_app_tenant_schemas.sql:22,25`（テナントのスキーマ、相手は salesanchor_app）だけ。新しいロールに自動で付く既定の権限は無い。設計 §8「新しい表は自動では書けない」と合う。
- PUBLIC への付与・取り上げ: `migrations` を `TO PUBLIC` で検索して 0 件。`ON SCHEMA public` の取り上げも 0 件（:15 の salesanchor_app への GRANT だけ）。つまり、PostgreSQL が最初から PUBLIC に付ける権限（public スキーマの USAGE、DB の CONNECT・TEMP、関数の EXECUTE。DB の作られ方によっては public スキーマの CREATE も）を、新しいロールもそのまま受け継ぐ。設計はこの点に触れていない（→ R3）。
- 連番: 設計は `USAGE ON ALL SEQUENCES IN SCHEMA tenant_001`。USAGE だけなら `setval` はできない（UPDATE が要る）。除外した表の連番にも USAGE が付くが、番号を進めるだけで行は書けない。穴ではない（→ L6 に記録）。
- 関数の実行権限: 上のとおり、`unmask_fetch` 以外で EXECUTE を PUBLIC から外した関数は migrations に無い。現時点で PUBLIC から呼べる SECURITY DEFINER 関数は引き金の関数だけと読めるが、本番の `pg_proc` は確かめていない（未確認 → R3 の試験で測る）。

## 3. `SET LOCAL app.tenant_id` で RLS が開く前提（見る点 3）

- `public.current_tenant_id()` の定義は `migrations/014_create_current_tenant_id_function.sql:15-21`: `LANGUAGE SQL STABLE`、中身は `SELECT current_setting('app.tenant_id', true)::INTEGER`。SECURITY DEFINER ではない。
- 方針のもう一つの形も同じ値を見る（例 `backend/app/services/tenant.py:2761`・`:2765` の `current_setting('app.tenant_id', true)::INTEGER`）。
- この関数の EXECUTE を PUBLIC から外す migration は無い（§2）ので、新しいロールも呼べる。
- → `SET LOCAL app.tenant_id = '1'` で 64 枚の RLS が開くという design.md:30 の前提は、定義と合う。RLS は境界ではない（tenant_004 の表には権限が無いので、値を変えても書けない）という design.md:37-38 の整理も正しい。

## 4. 外部キーの確かめと public の権限（見る点 4）

- recon.md:33・design.md:53 は「参照先の public の表に SELECT が要るかは未確認 → K4 で測る」としている。未確認として扱っていることは正しい。
- 問題は順番。public に付ける権限は便2の migration に書く。一方 K4 は便4で測る（design.md:72-74）。測る前に付ける物を決めることになり、「最小」を決める手順が無い（→ R5）。

## 5. K1〜K8 が○×で判定できるか（見る点 5）

| # | 判定できるか | 理由 |
|---|---|---|
| K1 | できる | 件数と止まりの回数で決まる |
| K2 | できる | 3 件のエラー |
| K3 | 一部 | 既にある表への書き込みだけを試す。public への CREATE などの「新しい物を作る」道を試していない（→ R3） |
| K4 | 一部 | 「一覧どおり」の一覧が設計に無い（→ R5） |
| K5 | できない | `information_schema.role_table_grants` は「付けた側か付けられた側が、今の利用者で有効なロール」の行だけを出す（PostgreSQL 公式の定義）。reader 鍵（ai_reader）で読むと、ai_dev001_writer の権限は出ない。比べる「設計の表」も design.md に無い（→ R1） |
| K6 | 数が合わない | 「K1〜K3 の 9 文」とあるが、K1 3 文＋K2 3 文＋K3（public と tenant_meta_config の各 3 種なら 6 文）で 12 文になる（→ L1） |
| K7 | できる | |
| K8 | 期間がずれる | 測る期間 11/28〜12/11 は、道ができる便3の前から始まる（→ L2） |

## 6. 戻し方（見る点 6）

- 「authorized_keys の 1 行を消す」で、新しい接続は止まる（ADR-1024 戻し方 1 と同じ）。
- 「ロールを無効にする migration」は、入れ替え（deploy）を待つので遅い。今つながっている接続も切れない（→ L3）。
- 止まる道としては成り立つので R にはしない。

## 7. migration の登録の手順（見る点 7）

- 登録の正本は `scripts/run_all_migrations.sh`（:5-7「このファイルに追記する」）。新しい手順は `mr_report_summary`（:1504）の上に足す（:1503 の注記）。deploy.yml は変えなくてよい。
- 流れは「記録済みでチェックサムが同じなら流さない」（:49-50）。流した後のファイルは `scripts/check_migration_freeze.py`（:1-27）が書き換えを止める。→ 権限の一覧を後で直すときは、新しい migration を足す形になる。design.md:77 の「要るときに migration で足す」と合うが、明記が無い。
- ロールの作成は、既にあるとき属性が違えば止める形（`migrations/20261017_130000_create_ai_reader_role.sql:10-17`）にそろえる必要がある。設計に書いていない。
- テナントの表は migrations ではなくアプリ（`backend/app/services/tenant.py`）が作る。試験用の DB・CI の新しい DB では `tenant_001` や表が無いことがある。無い表を名前で GRANT すると、その migration が止まり、入れ替え全体が止まる。既存の migration は無いスキーマ・表を飛ばす形にしている（例 `migrations/20261127_100000_add_calendar_team_share.sql:18-27`）。設計に書いていない（→ R4）。
- 危険パス: `scripts/check-process-artifacts.js:1033` の `^backend\/app\/ops\//` で台本 `backend/app/ops/dev001_write.py` は入る。compose は `:1034-1035` に `docker-compose.ai-reader.yml`・`docker-compose.ai-reader-http.yml` しか無く、`docker-compose.ai-dev001-writer.yml` は入らない（→ R2）。

## R（直さないと作れない・壊れる・穴が残る物）

- **R1 K5 の測り方と比べる一覧**（design.md:65、§3 の表 :29）
  - 測り方を、別のロールでも読める形に変える。例: `pg_class.relacl` を `aclexplode` で開き、相手が ai_dev001_writer の行を数える。または表ごとに `has_table_privilege('ai_dev001_writer', <表>, 'INSERT')` 等を見る。`information_schema.role_table_grants` は使わない。
  - 比べる一覧を設計に足す。tenant_001 の表のうち付ける表・付けない表（理由つき）の一覧を付録にするか、一覧を決める規則（下の R3 の除外の型と `tenant_meta_config`）と、その規則で出した表の数を書く。
- **R2 compose を危険パスに入れる**（design.md:32、§7 便2 :72）
  - 便2の作業に「`scripts/check-process-artifacts.js` の DANGEROUS_PATTERNS（:1023-1041）に `^docker-compose\.ai-dev001-writer\.yml$` を足す」を入れる。ADR-1024 Decision 7（`docs/adr/ADR-1024-ai-readonly-db-path.md:36`）と同じ理由（固定コマンドの中身を GO 記録なしに変えさせない）。
- **R3 PUBLIC から受け継ぐ権限と、秘密列の除外の型**（design.md:21、:29、:63）
  - 除外の型を ADR-1024 の拒否リスト `migrations/20261017_130100_create_ai_ro_views.sql:23`（`^password|_encrypted$|_secret|_token|hash|^secret|^api_key|private_key|credential|account_number|^iban$`）と同じにする。今の `*_encrypted`・`*_token*` だけでは、たとえば `tenant_001.bots.api_key_hash`（`backend/app/services/tenant.py:676`）に当たらず、読み書きできる。
  - PUBLIC が持つ権限への扱いを決めて書く。K3 に次を足す（reader 鍵で測る）: `has_schema_privilege('ai_dev001_writer','public','CREATE')` が false、`has_database_privilege('ai_dev001_writer', current_database(), 'CREATE')` が false、tenant_001・public の SECURITY DEFINER の関数（`pg_proc.prosecdef`）のうち新しいロールが EXECUTE できる物が引き金の関数だけ。true の物があれば、migration でそのロールを外す手当てを足す（PUBLIC からの取り上げは他のロールに効くので、するなら別の判断にする）。
- **R4 migration の作り方と登録**（§7 便2 :72）
  - 便2の作業に次を書く。`scripts/run_all_migrations.sh` の `mr_report_summary`（:1504）の上に `run_sql` を 1 行足す。ロールの作成は `20261017_130000_create_ai_reader_role.sql:10-17` と同じ形（属性が違えば止める）。tenant_001・各表が無いときは飛ばす（`20261127_100000_add_calendar_team_share.sql:18-27` の形）。一度流すと書き換えできない（`check_migration_freeze.py`）ので、直すときは新しい migration を足す。
- **R5 public の権限を決める順番**（design.md:29、:64、§7 :72-74）
  - 「public の権限は 0 から始める」と決め、便2の pytest（クラウドの使い捨て PostgreSQL）で、public を参照する外部キーのある表に 1 行足せるかを先に測る。足りなければ、付ける表と権限を設計に書き足してから migration を書く。K4 はその一覧と本番の実測が同じかを見る試験にする。

## L（軽い指摘）

- **L1** design.md:66 の「9 文」を、K1〜K3 の実際の文の数（今の書き方では 12）に直す。
- **L2** design.md:68 の K8 の期間を「便3が終わった日から 2 週間」にする。
- **L3** design.md:85-87 の戻し方に、PO の `!` ですぐ効く `ALTER ROLE ai_dev001_writer NOLOGIN` と、今つながっている接続を切る手順を足す。あわせて ADR-1024 戻し方 4（`docs/adr/ADR-1024-ai-readonly-db-path.md:81`）と同じく、Mac の見張りの免除を元に戻す行を足す。
- **L4** design.md:31 の AUDIT。読むだけの台本は結果を取った後に AUDIT を送る（`backend/app/ops/readonly_query.py:322`）。書き込みでは、AUDIT を commit の前に送り、送れなければ rollback する順番を書く（K6 の「全部記録に残る」のため）。サーバーの `log_statement=all` は別にある。
- **L5** design.md:31 の語の拒否に、読むだけの台本と同じ `set_config(`（`backend/app/ops/readonly_query.py:49`・`:55`）を足す。境界ではないが、事故よけとして `SET` だけでは足りない。
- **L6** design.md:29 の連番は `ALL SEQUENCES` の一括付与で、§5（:52「一括付与しない」）と書き方がそろわない。連番は USAGE だけで行を書けないので害は無いが、一括でよい理由を一言書く。
- **L7** recon.md:25-30・:32 の生出力（`/tmp/CC報告ファイル/dev001/q*.tsv`）はリポジトリに無い。件数（表 112・RLS 64・外部キー 31/72・引き金 30）を後から確かめられるよう、使った SQL を recon に書く。
