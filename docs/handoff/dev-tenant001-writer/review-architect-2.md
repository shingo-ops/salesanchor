# review-architect-2: 試験用テナント（tenant_001）だけに書き込める AI の道（設計審査 第2回）

> 審査役: architect（クラウド、2026-11-27）。読むだけ。製品のコード・DB・本番・secrets には触れていない。
> 審査した物: `origin/release/dev-tenant001-writer-design` の `docs/handoff/dev-tenant001-writer/design.md`（第2版）・`recon.md`・`review-architect-1.md`（git show で全文）。
> 照らした正本（`origin/main`）: `docs/adr/ADR-1024-ai-readonly-db-path.md`、`migrations/20261017_130000_create_ai_reader_role.sql`、`migrations/20261017_130100_create_ai_ro_views.sql`、`migrations/20261127_100000_add_calendar_team_share.sql`、`migrations/014_create_current_tenant_id_function.sql`、`backend/app/ops/readonly_query.py`、`backend/app/services/tenant.py`、`docker-compose.ai-reader.yml`、`scripts/run_all_migrations.sh`、`scripts/check-process-artifacts.js`。
> 以下、`design.md:N` は審査した枝の design.md の行番号。

## 判定: REVISE

1. 第1回の R1〜R5・L1〜L7 は 12 件とも第2版で直っている（§1）。
2. ただし新しい規則A〜E に `tenant_001` スキーマの USAGE が無く、このまま migration を作ると、新しいロールは tenant_001 の表に 1 文も届かない（K1 が × になる）。
3. 台本の語の拒否（`SET`・tenant_001 以外のスキーマ名）が UPDATE と K2・K3(a) の文を DB に届く前に止めるため、K1・K2・K3(a)(b)・K6 が設計どおりに測れない。K5 の数（105/6/1）も、書いてある数え方では 111 枚になり食い違う。

## 1. 第1回の指摘が直ったか（見る点 1）

| 指摘 | 結果 | 第2版の行 | 確かめたこと |
|---|---|---|---|
| R1 K5 の測り方と比べる一覧 | ○ | design.md:86、:37-41 | `information_schema.role_table_grants` をやめ `pg_class.relacl`・`pg_attribute.attacl` を `aclexplode` で数える形に変わった。比べる数を規則A・B から出した（105/6/1）。数え方の細部は新しい R3 |
| R2 compose を危険パスに | ○ | design.md:34、:96 | `^docker-compose\.ai-dev001-writer\.yml$` を足すと明記。台本は `scripts/check-process-artifacts.js:1033` の `^backend\/app\/ops\//` で入る（実物 :1033 と合う） |
| R3 PUBLIC の権限と秘密列の型 | ○ | design.md:39、:46-51、:84 | 型は `migrations/20261017_130100_create_ai_ro_views.sql:23` と 1 文字ずつ同じ。PUBLIC の表（スキーマ・DB・SECURITY DEFINER）を足し、K3(c)(d) を足した |
| R4 migration の作り方と登録 | ○ | design.md:28、:43、:95 | 属性が違えば止める形（`20261017_130000_create_ai_reader_role.sql:10-17` と合う）、無い物は飛ばす（`20261127_100000_add_calendar_team_share.sql:18-27` と合う）、`run_all_migrations.sh` の `mr_report_summary`（実物 :1504）の上に 1 行、書き換え不可（`check_migration_freeze.py`） |
| R5 public の権限を決める順番 | ○ | design.md:44、:94、:85 | 規則E で 0 から始め、便2の pytest で先に測る順番になった。K4 は一覧（今は 0 件）との一致を見る |
| L1 K6 の文の数 | ○ | design.md:87 | K1 3＋K2 3＋K3(a) 6＋K3(b) 1＝13。数は合う |
| L2 K8 の期間 | ○ | design.md:89 | 便3の終わりから 14 日 |
| L3 戻し方 | ○ | design.md:111-113 | `NOLOGIN`＋`pg_terminate_backend`、Mac の免除を戻す行を足した |
| L4 AUDIT の順番 | ○ | design.md:31 | 「流す → AUDIT → 送れたら commit、送れなければ rollback」 |
| L5 `set_config(` | ○ | design.md:31 | `readonly_query.py:49`（`set_config\s*\(`）・`:55`（`pg_catalog\s*\.\s*set_config`）と合う |
| L6 連番の一括の理由 | ○ | design.md:42 | USAGE は番号を進めるだけで `setval` は UPDATE が要る、と書いた |
| L7 使った SQL | ○ | recon.md:62-70 | 表の数・スキーマ・DB・SECURITY DEFINER・秘密列の SQL を書いた。生出力ファイルはリポジトリに無いまま（件数の確かめは SQL を流し直す形になる） |

## 2. 第2版で足した物の確かめ（見る点 2）

### 2-1. 規則A〜E（design.md:37-44）
- 規則A〜C に **`GRANT USAGE ON SCHEMA tenant_001` が無い**。recon.md:65 の本番の値は tenant_001 が `jarvis=UC`・`salesanchor_app=U`・`ai_unmask_owner=U` だけで、PUBLIC に USAGE が無い。PostgreSQL ではスキーマの USAGE が無いと、表の権限があっても中の物を参照できない。→ **R1**。
- 規則B の型の照合は `lower(a.attname) ~ deny`（`20261017_130100_create_ai_ro_views.sql:36-38`）。規則B は小文字にしてから当てることを書いていない（→ L1）。
- 規則B の 6 表 6 列＋`tenant_meta_config` 3 列＝7 表 9 列は recon.md:68 と合う。112＝105＋6＋1 も合う。

### 2-2. 列ごとの GRANT で DELETE を表に付けたとき、秘密の列が漏れないか
- PostgreSQL の権限の決まり: DELETE・UPDATE の WHERE や RETURNING に出てくる列には SELECT が要る。`INSERT ... SELECT` や `UPDATE ... SET a = 秘密の列` も、秘密の列の SELECT が要る。
- よって、規則Bで秘密の列に SELECT を付けなければ、`DELETE ... WHERE 秘密の列 = ...`（値を当てて探る）も `DELETE ... RETURNING *` も権限エラーになる。**DELETE を表に付けても秘密の列は漏れない**と判断する（本番では未実行。便4の K3(b) に `DELETE ... RETURNING *` を 1 文足すと確かめられる → L2）。
- 同じ表の引き金（recon.md:31 の 29 本。updated_at の付け直し・支払い記録の消し止め）は呼んだ人の権限で動く。秘密の列を読み出して返す道は、設計の範囲では見つからない。
- 副作用として、秘密の列が `NOT NULL` かつ既定値が無い表には、INSERT ができない（その列を書けないため）。6 表のどれが当たるかは未確認（→ L3）。

### 2-3. §3-3 PUBLIC の表（design.md:46-51）
- 数（スキーマ・DB・SECURITY DEFINER 6 個）は recon.md:65-67 と合う。
- `tenant_meta_config` の外部キーは `backend/app/services/tenant.py:2184-2185` の `public.users` への `ON DELETE SET NULL` の 1 本だけ（コードの上では）。新しいロールは `public.users` を消せないので、tenant_001 の別の表を消した連鎖で `tenant_meta_config` の引き金（`tenant.py:2822-2824`、AFTER INSERT OR UPDATE OR DELETE）が動く道は無い。本番の `pg_constraint` では未確認（→ L4）。

### 2-4. K3(a)〜(d)・K5・K6
- **K2・K3(a) が台本で止まる**: design.md:31 の台本は「`tenant_001.` 以外のスキーマ名を拒む」。K2（tenant_004）と K3(a)（public）の 9 文は、DB に届く前に台本が拒むので、K2・K3(a) の「権限エラー」が出ない。読むだけの台本は拒否のときも AUDIT を `result=rejected` で送る（`readonly_query.py:266-274`）ので AUDIT 行は出るが、それは DB の境界を測ったことにならない。→ **R2**。
- **UPDATE が台本で止まる**: design.md:31 は `SET` を拒み、`readonly_query.py:49`・`:55` と同じ語を含めるとしている。読むだけの台本の `SET` の拒否は `\bset\s`（`readonly_query.py:50`）で、文のどこにあっても当たる。これを写すと `UPDATE ... SET ...` が全部止まり、K1 の UPDATE・K3(b) が流せない。→ **R2**。
- **K6 の 13 本と失敗の文**: 台本の順番は「流す → AUDIT → commit」だけで、DB エラーのときに AUDIT を送るかを書いていない。K2・K3 の 10 文は失敗する文なので、送らない作りだと 13 本にならない。読むだけの台本は DB エラーでも送る（`readonly_query.py:306-310`）。→ **R2** に含める。
- **K5 の 105 枚が合わない**: 規則B の 6 表は DELETE を表に付けるので、`pg_class.relacl` に ai_dev001_writer の行を持つ表は 105＋6＝111 枚になる。また `pg_class` には連番（relkind 'S'）の USAGE も出る。design.md:86 の書き方（「表ごとの付与 105 枚（各 4 種）・列ごとの付与 6 枚」）では、数える人によって 105 と 111 のどちらにもなり、○×が決まらない。→ **R3**。
- **aclexplode・has_*_privilege を reader 鍵で使えるか**: 読むだけの台本は先頭が SELECT/WITH/SHOW/EXPLAIN なら通し、関数の名前では止めない（`readonly_query.py:47-58`、:154-165）。`aclexplode`・`has_*_privilege` の語は拒否の一覧に無い。`pg_class`・`pg_attribute` は reader 鍵で読めている（recon.md:64・:68）。よって使えると判断する（本番でまだ流していない。未確認）。注意: ai_reader は tenant_001・tenant_004 のスキーマの USAGE を持たない（recon.md:65）。`has_table_privilege('ai_dev001_writer','tenant_001.表','INSERT')` のように名前で表を渡すと、名前を引く段で ai_reader 自身のスキーマ権限で止まる見込みがあるので、表は `pg_class.oid` で渡す（→ L5）。
- K3(c)(d) の式は oid・スキーマ名・DB 名で渡しているので、上の注意に当たらない。

## 3. 便2のカードを書ける粒度か（見る点 3）

- 作る物（migration 1 本・台本と試験・compose・危険パス 1 行・`run_all_migrations.sh` 1 行）と、先に測る物（規則E）は揃っている（design.md:94-96）。
- 足りない物は R1〜R3 の 3 点だけ。直せば便2のカードを書ける。
- カードに書くと迷わない物（軽い指摘）: L6・L7。

## R（直さないと作れない・壊れる物）

- **R1 tenant_001 スキーマの USAGE**（design.md:19-20 §2 の対象、:37-43 規則A〜D、:86 K5）
  - 規則A の前に「規則A0: `GRANT USAGE ON SCHEMA tenant_001 TO ai_dev001_writer`（CREATE は付けない）」を足す。§2 の対象の表に 1 行足す。
  - K5 に「`pg_namespace.nspacl` を `aclexplode` で開き、相手が ai_dev001_writer の行が tenant_001 の USAGE 1 行だけ（public・ほかのテナントは 0 行。public の USAGE は PUBLIC から受け継ぐのでここには出ない）」を足す。
- **R2 台本の語の拒否と K1・K2・K3・K6 をかみ合わせる**（design.md:31 台本、:82-84 K1〜K3、:87 K6）
  - `SET` の拒否は「文の先頭の語が SET・RESET」に限ると書く（`readonly_query.py:50` の `\bset\s` は写さない。`set_config(` の拒否は残す）。
  - 「`tenant_001.` 以外のスキーマ名を拒む」を残すなら、K2・K3(a) は台本の拒否では DB の境界を測れないので、測り方を書き換える。案: (1) K2・K3(a) は reader 鍵で `has_table_privilege('ai_dev001_writer', oid, 'INSERT'|'UPDATE'|'DELETE')` が全部 false であることを数える形にし、新しい鍵では「台本が拒否する（AUDIT result=rejected）」を別に確かめる。または (2) 台本の拒否を外し、DB の権限エラーで測る。どちらかを選んで書く。
  - 台本の順番に「拒否・DB エラーのときも AUDIT を送る（`readonly_query.py:266-274`・`:306-310` と同じ）。送れなければ終了コードで知らせる」を足す。K6 の 13 本が、どの result（ok／rejected／db_error）で何本かを書く。
- **R3 K5 の数え方を 1 通りにする**（design.md:41、:86）
  - 例: `pg_class.relacl`（relkind 'r','p' だけ）で、相手が ai_dev001_writer の行 = 105 表×4 種＋6 表×DELETE＝426 行、表の数 111。`pg_attribute.attacl` で、6 表の秘密でない列×3 種（SELECT・INSERT・UPDATE）、秘密の 6 列は 0 行、`tenant_meta_config` は 0 行。連番（relkind 'S'）は別に数える（tenant_001 の連番の数と同じ）。tenant_001 以外の pg_class・pg_attribute は 0 行。
  - 6 表の「秘密でない列の数」は本番の pg_attribute で出して書くか、「列の数 − 1」を式で書く。

## L（軽い指摘）

- **L1** design.md:39 規則B に「列名を小文字にしてから当てる」（`20261017_130100_create_ai_ro_views.sql:36-38` の `lower(a.attname)`）と書く。
- **L2** design.md:84 K3(b) に、規則B の表への `DELETE ... RETURNING *` 1 文（権限エラーになる）を足すと、§2-2 の「DELETE を表に付けても漏れない」を実測で示せる（K6 の数も 1 増える）。
- **L3** 規則B の 6 表で、秘密の列が `NOT NULL` かつ既定値なしなら、その表には INSERT できない。便2の pytest で 6 表それぞれに INSERT を試し、できない表を設計に書く（できなくても境界は崩れない）。
- **L4** recon に、本番の `pg_constraint` で `tenant_meta_config` を参照先・参照元とする外部キーの一覧（とくに tenant_001 の表からの連鎖）を足す。コードの上では `tenant.py:2184-2185` の 1 本だけ。
- **L5** design.md:85-86 の K4・K5 で `has_*_privilege` に表を渡すときは `pg_class.oid` で渡すと書く（ai_reader は tenant_001・tenant_004 の USAGE を持たないため、名前で渡すと引けない見込み。本番では未確認）。
- **L6** design.md:28 のロールの設定に、読むだけの道と同じ `idle_in_transaction_session_timeout = '60s'`（`20261017_130000_create_ai_reader_role.sql:27`）を足すか、足さない理由を書く。書き込みの道では、つかんだロックを持ったまま止まるのを切るのに要る。
- **L7** 台本の AUDIT の名乗り（読むだけの道は `ai-reader-audit`、`readonly_query.py:37`）を別の名前にすると書き、K6 で Loki をその名前で数えると書く。あわせて、便2の pytest で tenant_001 の表をどう作るか（`backend/app/services/tenant.py` のテナント作成を使う等）をカードに書く。使い捨ての PostgreSQL には tenant_001 が無いため（design.md:43 規則D の「無い物は飛ばす」だけでは試験にならない）。
