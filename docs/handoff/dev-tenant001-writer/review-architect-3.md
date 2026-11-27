# review-architect-3: 試験用テナント（tenant_001）だけに書き込める AI の道（設計審査 第3回）

> 審査役: architect（クラウド、2026-11-27）。読むだけ。製品のコード・DB・本番・secrets には触れていない。
> 審査した物: `origin/release/dev-tenant001-writer-design`（79aa019f）の `docs/handoff/dev-tenant001-writer/design.md`（第3版）・`recon.md`・`review-architect-2.md`、`docs/adr/ADR-1093-ai-dev-tenant001-writer.md`（git show で全文）。
> 照らした正本（`origin/main`。第2回と同じ）: `docs/adr/ADR-1024-ai-readonly-db-path.md`、`migrations/20261017_130000_create_ai_reader_role.sql`、`migrations/20261017_130100_create_ai_ro_views.sql`、`migrations/20261127_100000_add_calendar_team_share.sql`、`migrations/014_create_current_tenant_id_function.sql`、`backend/app/ops/readonly_query.py`、`backend/app/services/tenant.py`、`docker-compose.ai-reader.yml`、`scripts/run_all_migrations.sh`、`scripts/check-process-artifacts.js`。
> 以下、`design.md:N`・`recon.md:N`・`ADR-1093:N` は審査した枝のファイルの行番号。本番 DB は読んでいない（recon の数は recon の記録どおりとして扱う）。

## 判定: APPROVE

1. 第2回の R1〜R3・L1〜L7 は 10 件とも第3版で直っている（§1）。
2. 第3版で変えた物（規則A0・語の拒否・AUDIT・K5 の数 426/111/207/74・K6 の 14 本）の数は互いに合い、正本の行とも合う。作れない・壊れる穴は見つからない（§2）。
3. ADR-1093 は design.md と食い違う所が無い（書き漏れだけ。§3）。便2のカードは書ける粒度で、軽い指摘 L1〜L7 をカードに書けば迷わない（§4）。

## 1. 第2回の指摘が直ったか（見る点 1）

| 指摘 | 結果 | 第3版の行 | 確かめたこと |
|---|---|---|---|
| R1 tenant_001 スキーマの USAGE | ○ | design.md:21、:39、:91(i) | 対象の表に 1 行、規則 A0（CREATE なし、public は付けない）、K5 (i) `pg_namespace.nspacl` で 1 行だけ。第2回の案どおり |
| R2 台本の語の拒否と K のかみ合わせ | ○ | design.md:32、:88-89、:92 | SET・RESET は先頭の語だけで拒む（`\bset\s` は写さないと明記。正本 `readonly_query.py:50`）。`set_config(`・`pg_catalog.set_config` は残す（正本 :49・:55 と同じ）。スキーマ名では拒まない → K2・K3(a)(b) は DB の権限エラーで測る形（第2回の案 (2)）。拒否・DB エラーでも AUDIT を送る（正本 :266-274・:306-310）。K6 に result ごとの本数 |
| R3 K5 の数え方を 1 通りに | ○ | design.md:44、:91 | relkind を 'r','p' と 'S' に分け、(i)〜(v) の 5 つに分けた。秘密でない列の数を表ごとに実数で書いた（recon.md:73） |
| L1 小文字にしてから当てる | ○ | design.md:41 | 正本 `20261017_130100_create_ai_ro_views.sql:36-38` の `lower(a.attname)` と合う |
| L2 `DELETE ... RETURNING *` | ○ | design.md:45、:89 | K3(b) が 2 文になり、K6 も 1 本増えた |
| L3 INSERT できない表 | ○ | design.md:46、recon.md:74 | 本番で 3 表（bots・discord_channel_webhooks・tenant_invoice_payment_bank）。便2の pytest で 6 表を試すと書いた |
| L4 `tenant_meta_config` の外部キー | ○ | recon.md:76 | 本番の `pg_constraint` で 1 本（→ public.users）、参照される側 0 本。コードの上の `tenant.py:2184-2185` と合う |
| L5 oid で渡す | ○ | design.md:89(d)、:90 | K3(d)・K4 は oid。`::regclass` が権限エラーになる実測も書いた（recon.md:77）。K5 は `aclexplode` なので名前を引かない |
| L6 `idle_in_transaction_session_timeout` | ○ | design.md:29 | 正本 `20261017_130000_create_ai_reader_role.sql:27` の `'60s'` と同じ値 |
| L7 AUDIT の名乗りと pytest の tenant_001 | ○ | design.md:32、:92、:100 | 名乗り `ai-dev001-writer-audit`（正本 `readonly_query.py:37` の `ai-reader-audit` と別）。K6 はその名前で数える。pytest の tenant_001 は `tenant.py` のテナント作成で作る |

## 2. 第3版で変えた物の確かめ（見る点 2）

### 2-1. 規則 A0（design.md:39）
- recon.md:65 の本番の値で tenant_001 の PUBLIC に USAGE が無いため、A0 が要る。CREATE を付けないので表は作れない。public の USAGE は PUBLIC から受け継ぐ（design.md:54、recon.md:65 `=U/pg_database_owner`）。穴は無い。
- K5 (i) の「1 行」は、grantor が 1 人（migration を流すロール）のときの数。`aclexplode` は grantor ごとに行を出すので、同じ GRANT を別のロールで重ねて流すと 2 行になる（→ L5 にまとめる）。

### 2-2. 台本の語の拒否（design.md:32）
- 先頭の語の許し: INSERT・UPDATE・DELETE・SELECT・WITH。`WITH x AS (DELETE ...)` も通るが、境界は DB の権限（design.md:61-62）なので穴ではない。
- スキーマ名で拒まない形にしたことで、K2（tenant_004）は「スキーマ tenant_004 の USAGE が無い」権限エラー、K3(a) の public は「表の権限が無い」権限エラー、`tenant_meta_config` は表の権限エラーになる見込み（どれも PostgreSQL の InsufficientPrivilege。本番では未実行）。DB に届くので、K2・K3 が DB の境界を測れる。
- 台本自身が `SET LOCAL app.tenant_id`・`SET LOCAL search_path` を流すのは、利用者の文の拒否とは別（design.md:31）。食い違いは無い。

### 2-3. AUDIT の名乗りと失敗時の送り（design.md:32、:92）
- 拒否 → AUDIT（rejected）、DB エラー → AUDIT（db_error）、成功 → AUDIT → commit。K6 の 14 本は ok 3・db_error 11 で、拒否は 0 本（K1〜K3 の文は全部台本を通る形になったため）。数は合う。
- 正本の結果の書き方は `db_error` ではなく `db_error:<種類>`（`readonly_query.py:310` の `f"db_error:{kind}"`、AUDIT の行の形は :206 `result={result}`）。写すと K6 の「result=db_error 11 本」を完全一致で数えると 0 本になる（→ L1）。
- DB エラーのときの順番（AUDIT の後に rollback）と、AUDIT を送れなかったときの終了コードは、成功の場合（終了コード 3）しか書いていない。正本は拒否・DB エラーで送れなければ 5（`readonly_query.py:270`・:274・:310）（→ L2）。

### 2-4. K5 の数（design.md:91）
- (ii) 105×4＋6×1＝426 行、表 111＝105＋6。規則A・B（design.md:40-43）と合う。`tenant_meta_config` 0 行で合計 112（recon.md:64）。
- (iii) 13＋5＋18＋10＋11＋12＝69 列（design.md:44・recon.md:73 と合う）。69×3＝207 行。
- (iv) 74（recon.md:75 と合う）。規則 C は連番に USAGE だけなので 1 本 1 行。
- (v) public は規則 E で 0（K4 の「今は 0 件」と合う）。
- 数えの前提: 列は `attnum > 0 AND NOT attisdropped` だけを数える（正本 `20261017_130100_create_ai_ro_views.sql:41` と同じ）。recon.md:73 の q20 にこの絞りが書かれていない。migration で消した列（`........pg.dropped.N`）に GRANT を書くと止まるので、migration と数えの両方に要る（→ L3）。

### 2-5. K6 の 14 文と内訳（design.md:92）
- K1 3（:87）＋K2 3（:88）＋K3(a) 6（:89）＋K3(b) 2（:89）＝14。ok は K1 の 3、db_error は 3＋6＋2＝11。合う。
- K4 の INSERT 1 文（:90）も新しい鍵で流すので AUDIT が 1 本出るが、K6 は K1〜K3(a)(b) に限ると書いてあるので数は食い違わない。Loki で数える時間の幅を決めないと 15 本になりうる（→ L6）。

### 2-6. 新しく気づいた点（作れなくはならない）
- `SET LOCAL search_path = tenant_001`（design.md:31）で public が外れる。tenant_001 の引き金の関数の本文が public の物を名前だけで呼んでいると、K1 の INSERT・UPDATE が引き金の中で失敗する見込みがある。アプリ側の search_path の既定は `database.py:44` の `RESET ALL` で初期値へ戻す形で、初期値の中身は未確認。public を足しても public に書く権限は付かない（規則 E）ので境界は変わらない（→ L4）。

## 3. ADR-1093 と design.md（見る点 3）
- 食い違いは無い。Decision 1〜5（ADR-1093:24-28）は design.md §3 の要約になっている。
- 書き漏れ（食い違いではない）: Decision 1 に `idle_in_transaction_session_timeout=60s`（design.md:29）が無い。Decision 2 にスキーマの USAGE と連番の USAGE（design.md:20-21）が無い。「設計・根拠」（ADR-1093:10）に review-architect-2.md が無い（→ L7）。
- `docs/adr/README.md` の目次に ADR-1093 の 1 行が足され、総数 248 → 249（枝の差分で確かめた）。

## 4. 便2のカードを書ける粒度か（見る点 4）
- 作る物（migration 1 本・台本と試験・compose・危険パス 1 行・`run_all_migrations.sh` 1 行）と先に測る物（規則 E・6 表の INSERT）が design.md:98-102 に揃っている。
- 参照の行は正本と合う: `run_all_migrations.sh:1504` `mr_report_summary`、`check-process-artifacts.js:1033-1035`、`docker-compose.ai-reader.yml:15-29`（環境変数 1 つ・read_only・cap_drop・no-new-privileges・mem_limit 256m・/dev/log）、`014_create_current_tenant_id_function.sql:15-21`、`20261127_100000_add_calendar_team_share.sql:18-27`、`20261017_130000_create_ai_reader_role.sql:10-17`・:27。
- pytest の順番（テナントを作ってから migration を流す）はカードに書くと迷わない（design.md:100 は作り方だけ）。

## R（直さないと作れない・壊れる物）
- なし。

## L（軽い指摘。便2のカードに書けばよい）
- **L1** design.md:92 K6 の数え方を「`result=db_error` で始まる行」と書く（正本 `readonly_query.py:310` は `db_error:<種類>`）。または台本の結果を `db_error` だけにすると書く。
- **L2** design.md:32 に、DB エラーのときは AUDIT の後に必ず rollback、拒否・DB エラーで AUDIT を送れなかったときの終了コード（正本は 5、`readonly_query.py:270`・:274・:310）を書く。
- **L3** design.md:41・:48 規則 B・D と K5 (iii) に「列は `attnum > 0 AND NOT attisdropped`」（正本 `20261017_130100_create_ai_ro_views.sql:41`）を書く。recon.md:73 の q20 の SQL にもこの絞りがあったかを書く。
- **L4** design.md:31 の search_path を `tenant_001, public` にするか、`tenant_001` だけのまま便2の pytest で K1 の 3 文が引き金ごと通るかを確かめると書く（初期値の中身は未確認）。
- **L5** design.md:91 K5 (i)〜(iv) の数は「grantor が migration を流すロール 1 人」のときの数だと書く（`aclexplode` は grantor ごとに行を出す）。
- **L6** design.md:92 K6 の Loki の数えの時間の幅（K4 の INSERT を入れない幅、または K4 を含め 15 本）を書く。K3(a) で使う public の表の名前も決めて書く。
- **L7** ADR-1093:24 Decision 1 に `idle_in_transaction_session_timeout=60s`、:25 Decision 2 にスキーマと連番の USAGE、:10 に review-architect-2.md（と本書）を足す。
