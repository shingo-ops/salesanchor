# 審査記録: card-pr-c.md（古い会社ごとの名簿 tenant_NNN.channel_masters を消す）

- 審査役: 設計審査役（Architect・クラウドの定期実行）。読むだけ。コード・SQL・試験は変えていない
- 対象: `release/channel-master-pr-c` 7522a4d3b の `docs/handoff/channel-master-shared/card-pr-c.md`
- 照合先: origin/main 44a6ccce1（カードの基準 2969725e9 から10コミット進んでいるが、関係ファイル（`scripts/run_all_migrations.sh`・`migrations/`・`scripts/migration-guard/`・`docs/handoff/cloud-case-ai/`・`.github/`）は変わっていない。`git diff --stat 2969725e9 origin/main -- …` で確かめた。変わったのは backend/tests の discord 系2ファイルだけ）
- 設計の正本: `docs/handoff/channel-master-shared/design.md` §6 の4・§7

## 判定: **REVISE**

カード §1 の事実は、行番号まで全部 origin/main と一致した。変更の中身（2-1〜2-9）は設計 §6 の4 に沿っており、古い表を作る道と頼る試験は全部消える。ただし、CI の見張りと本番の控えについてカードに書かれていない／決まりに合わない点が3つあり、実装役が止まるか決まりを破るおそれがある。下の必須3件を直せば APPROVE できる。

## 必須（直してから実装役に渡す）

### M1. migration-guard のチェック6（DROP TABLE）は PR 本文の `ADR-NNN` が無いと赤になる。カード §4 のままだと実装役が BLOCKED で止まる
- 【事実】`.github/workflows/migration-guard.yml:343-391`: 追加行に `DROP TABLE` があると、PR 本文から `ADR-[0-9]+` を探し、無ければ exit 1。2-1 の `EXECUTE format('DROP TABLE IF EXISTS %I.channel_masters', …)` はコメント行ではないので必ず当たる（`:353-357` の grep はコメント行 `--` だけを外す）
- 【事実】カード §4「migration-guard が…「DROP」を理由に止める → 出力を貼って BLOCKED:」・§3 の g は process-artifacts の赤だけを想定していて、チェック6 には触れていない
- 直し方: カードに「PR 本文（最初の作成時から）に対象 ADR を書く」を足す。設計 §0 が使う ADR-1007（`docs/adr/ADR-1007-migration-structure-only-run-once.md`、design.md に参照あり）または ADR-135/136 を書けばチェック6 は通る。§4 の分岐も「チェック6 は PR 本文の ADR 参照で通す。それでも止まったら BLOCKED」に直す
- 【事実】`backend/AGENTS.md:26-28`「テーブル削除…要PO確認…ADR を起案すること」。tenant の channel_masters を消すことを書いた ADR は無い（`git grep -il 'channel_masters\|チャネル名簿\|channel-master' origin/main -- docs/adr` は0件）。設計 §6 の4 は PO 承認済み（2026-11-06）なので、ADR を新しく起こすか、設計の PO 承認＋ADR-1007 で足りるとするかを、カードに一文で書く（下の「未確認」U1）
- 確かめた命令: `git show origin/main:.github/workflows/migration-guard.yml | sed -n '343,391p'`

### M2. カード §3 の c（使い捨て PostgreSQL で流して表と連番が消えることを確かめる）は、クラウドの実装役には今の書き方では実行できない
- 【事実】クラウドの決まり（SessionStart の「クラウド実行の決まり」）は「SQL を流して確かめるのは pytest の中だけ」。カード c は「クラウドの手元の postgres で…流す」と psql 直流しを指している
- 【事実】カード 2-1 は「連番が消える」を確かめられなければ BLOCKED と書き、2-8 は「新しい migration は試験からは流さない」と書く。c を pytest で行うと 2-8 と食い違い、行わないと 2-1 の BLOCKED に落ちる
- 【事実】CI の migration-test（`.github/workflows/migration-test.yml:1362-1383`「変更 SQL を 1回目/2回目実行」）は冪等は見るが、事前に `tenant_*.channel_masters` を作らないので「表と連番が消える」は確かめない（`git grep -n channel_masters origin/main -- .github` は migration-guard.yml:224 の public 一覧だけ）
- 直し方（どちらかをカードで決める）: (a) 使い捨て DB の pytest（例 `backend/tests/test_drop_tenant_channel_masters_pg.py`。`CREATE DATABASE` で専用 DB を作り、tenant_001・tenant_002 を作って 20260611 → 新 migration を2回流し、`information_schema.tables` と `pg_class` の `channel_masters_id_seq` が0）を足し、`backend/tests/test_tenant_loop_migration_guard.py` の `_REVIEWED` に `own_database` として 20260611 と新 migration の2本で登録する（2-8 の「試験からは流さない」を消す）。残る守りにもなるので (a) を勧める。(b) 手元（PO の端末）で流す人をカードに書く
- 確かめた命令: `git show origin/main:backend/tests/test_tenant_loop_migration_guard.py | sed -n '264,329p'`（own_database は本文に `CREATE DATABASE` が要る `:317-320`）

### M3. カード §5 の2「無制限鍵で pg_dump」は AGENTS.md の決まりに合わない
- 【事実】`AGENTS.md`「VPS 直作業禁止」: 本番 DB の読み取りは reader 鍵の道。reader の道は SELECT/WITH/SHOW/EXPLAIN だけ（`docs/handoff/ai-readonly-db-path/usage.md:7`・`:30`）で pg_dump はできない。カードは「Opus が無制限鍵で pg_dump」と読める
- 【事実】本番反映は migration の前に毎回全体の控えを取る（`.github/workflows/deploy.yml:214` `bash scripts/backup.sh deploy`、`:221` で控えのファイル名をログに出す。`scripts/backup.sh:87` 新しい10個を残す）
- 直し方: §5 の2 を「反映の直前に reader 鍵の道で `SELECT * FROM tenant_00X.channel_masters ORDER BY id`（5社）を取り、出力と sha256 を docs/handoff/channel-master-shared/ に保存。加えて Deploy to VPS のログ `✅ Backup:` 行の控えファイル名を PR に記録」に替える。pg_dump が要るなら PO が実行する、と書く
- 確かめた命令: `git show origin/main:.github/workflows/deploy.yml | sed -n '205,222p'`・`git show origin/main:docs/handoff/ai-readonly-db-path/usage.md | grep -n SELECT`

## 推奨

- R1. PR 本文の欄をカードに並べる。`scripts/check-process-artifacts.js:1560-1615`・`:1773`・`:1813` は「### 標準ワークフロー確認」「対象ADR」「recon パス」「設計doc パス」「触るファイル:」「削除するファイル:」を見る。この PR は rls_bootstrap.py・試験2本・run_all_migrations.sh・ai_cloud_views.sql・TSV から行を消すので「削除するファイル:」の宣言漏れで別の赤が出る。§3 の g の「GO 以外の赤は直す」で実装役が直せるが、先に書いておくと往復が減る
- R2. `backend/tests/test_rls_bootstrap_ordering.py:102-117` が `_TENANT_BOOTSTRAP_MIGRATIONS` を引数にし、`[0]` を使う。2-7 の後は sales_form の1本になる。【推測】sales_form のセレクタ（`rls_bootstrap.py:189`）で同じ試験は通る。カード §3 の f の手元の試験にこのファイルを足す
- R3. `docs/handoff/cloud-case-ai/stage1-column-class.tsv` は「同じ内容の控え」ではない。【事実】TSV のデータ行は 1057 行（`wc -l` 1058 − 見出し1）、SQL の分類は 1084 列（`^  ('` 行の ARRAY の要素を数えた）。どの試験も TSV を読まない（`git grep -n stage1-column-class origin/main -- backend scripts .github` は0件）。2-5 は今のままでよいが、カードの表現を「控え（すでに SQL とずれている）」に直す
- R4. §5 の1「PR-B 反映後のエラーが0」をどこで数えるか（どのログ・どの監視）を書く。【事実】PR-B（#5230）のマージは 2026-11-07T11:06:03+09:00＝02:06 UTC（`git log origin/main --merges`）。本番反映の時刻はカードの値を確かめていない
- R5. 2-1 の時刻 20261107_180000 は origin/main にも、取り込んだ全リモート枝にも無い（下の命令）。本線に 170000 が先に入ると末尾の順がずれるだけで害は無い

## 観点ごとの結果

### ① 古い表を作る道・頼る試験が残らないか — 残らない
- 【事実】`git grep -n 'channel_masters' origin/main -- backend scripts migrations .github`（backend/app を除く）で、tenant の表を作る・頼るのは次だけ。全部カードが直す:
  - `scripts/run_all_migrations.sh:569-570`（2-2）
  - `backend/tests/rls_bootstrap.py:38`・`:188`（2-7）
  - `backend/tests/test_tenant_loop_migration_guard.py:42`（2-8）、`:137` は残す（test_value_migrations_neutralized.py:26 が文字として残るため。`_actual()` `:272-282` は試験ファイル中の名前を数えるので、残すのが正しい）
  - `backend/tests/test_value_migrations_neutralized.py:84-88`（2-9）
  - `migrations/20261024_100300_create_ai_cloud_views.sql:357-359`（2-3）
- 【事実】他の当たりは public の表（`migrations/20261106_190000_create_public_channel_masters.sql`、ai_cloud の public 5行 `:68-72`）、SQLite の conftest（`backend/tests/conftest.py:639` ほか）、`backend/tests/test_channel_type_control.py:56-79`（新しい会社に作らないことの試験）で、tenant の表には頼らない
- 【事実】新しい会社の作成に channel_masters は無い（`git grep -c channel_masters origin/main -- backend/app/services/tenant.py` rc=1）。検索 K1 は0件（rc=1）
- 【事実】`scripts/migration-guard/*.tsv`・`protected-tables.txt`・`*.json` に 20260611_100000 の行は無い（登録を外しても repo モードの「登録されていること」の検査に引っかからない）

### ② DROP migration の毎回の実行での安全さ — 安全（本番の依存は未確認）
- 【事実】`run_all_migrations.sh:220`・`:224` が先頭で `DROP SCHEMA IF EXISTS ai_cloud CASCADE`・`ai_ro CASCADE` を流し、`:236-273` の EXIT trap が最後に作り直す。作り直しは実在の表を `pg_class` から拾う（`migrations/20261017_130100_create_ai_ro_views.sql:25-33`・`migrations/20261024_100000_create_ai_cloud_meta.sql:80-90`）
- 【事実】trap の `ops_case.grant_unmask_owner()`（`migrations/20261031_210000_create_ops_case.sql:374-420`）は `pg_class` と結んで表を選ぶので、消えた表は飛ばされる。失敗しても警告だけ（`run_all_migrations.sh:267-269`）
- 【事実】2-1 は DO の1文で、`IF EXISTS` なので2回目以降は何もしない。`run_sql`（`run_all_migrations.sh:110-135`）は lock_timeout で待ち、ロック衝突だけ再試行する
- 【事実】repo の中に tenant の channel_masters を指す外部キーは無い（REFERENCES は public だけ）
- 【推測】SERIAL の連番は OWNED BY で表と一緒に消える（PostgreSQL の決まり）。カードどおり実 DB で確かめる（M2）
- 【未確認】本番で ai_ro・ai_cloud 以外に依存が無いこと（カード §1 は 2026-11-07 に確認済みと書く。審査役は DB に繋いでいない）。CASCADE 無しなので、想定外の依存があれば反映が失敗して止まり、trap がビューを作り直す（壊れる側でなく止まる側）

### ③ ai_cloud の分類3行・件数・sha・TSV・T10 — 整合
- 【事実】`migrations/20261024_100300_create_ai_cloud_views.sql:3` は「1084 行」、`:357-359` が tenant_* channel_masters の3行（各1列）。ARRAY の要素の合計は 1084（数えた）。3行消すと 1081
- 【事実】`backend/tests/ops/test_ai_cloud_views.py:484` `== n0 == 1084`。ほかに 1084 を見る所は無い（`git grep -n 1084` で backend/app の辞書ファイル以外はこの2か所だけ）
- 【事実】`scripts/migration-guard/reference-allowlist.tsv:7` の sha は今のファイルの sha256 `bb7a4e7b…a1b16` と一致。規則 (2)(3)（`:4-5`）により、2-3 の後は sha を直さないと repo モードが落ちる。カード 2-4 は正しい
- 【事実】T10（`test_ai_cloud_views.py:490-566`）は「実在の列に分類が無い」だけを見て、「分類はあるが表が無い」は見ない。だから足場（rls_bootstrap）と分類を同じ PR で外すカードの判断は正しい。分類だけ外すと T10 が落ちる
- 【事実】TSV `stage1-column-class.tsv:574-576` は3行で一致。ただし TSV 全体は SQL とずれている（R3）

### ④ 試験の足場の直しで他の試験が落ちないか — 落ちない見込み
- 【事実】`_TENANT_BOOTSTRAP_MIGRATIONS` を使うのは `rls_bootstrap.py:206`・`:392`、`test_rls_bootstrap_ordering.py:102-117`、`test_tenant_loop_migration_guard.py:311`
- 【事実】`test_tenant_loop_migration_guard.py` の `test_every_tenant_loop_migration_reference_is_classified`（`:294-307`）は両向き（足りない・古い）を見る。2-7 で rls_bootstrap.py から名前が消え、2-8 で `:42` を消すので釣り合う。`:137` は test_value_migrations_neutralized.py:26 が残るので残すのが正しい
- 【事実】`_scope_tenant_migration` の selectors（`rls_bootstrap.py:187-190`）から 20260611 を消しても、他の呼び手（`test_discord_role_link_ddl.py:144`・`test_roles_system_key_ddl.py:110`）は `_TENANT_LOOP_MIGRATIONS` 側の別ファイルを使う
- 【推測】`test_rls_bootstrap_ordering.py` は sales_form の1本で通る（R2）。試験は流していない（読むだけの役のため）

### ⑤ CI の見張り
- migration-guard: 登録の確認（`:119-139`）は 2-2 の run_sql で通る。`{schema}` なし（`:171-183`）。REFERENCES なし（`:219-250`）。時刻の重複なし（`:287-`、R5）。**チェック6（DROP）は PR 本文の ADR 参照が要る（M1）**。チェック7/8（`check-migration-value-writes.py`）は新ファイルに値の書き込みも保護表の参照も無いので通る【推測：保護表一覧 `protected-tables.txt` に channel が無いことは確かめた】。7b repo は 2-4 の sha 更新で通る
- check-process-artifacts: `:569`・`:887` の DROP 検出で PO 本人の GO が要る扱いになり、GO 記録が無い間は赤（カード §3 の g のとおり）。ほかに PR 本文の欄の検査がある（R1）
- migration-test: 変更 SQL（2-1・ai_cloud_views）の1回目・2回目の実行（`:1362-1383`）、全件ドライラン（`:1385-`）。全件ドライランは登録順に流すので、20260611 を外しても後ろの migration に tenant channel_masters を使うものは無い（①の grep）

### ⑥ 戻し方と本番の控え
- 戻し方（§6）: 【事実】revert で 20260611 の行が戻り、seed は無効化済み（`migrations/20260611_100000_create_channel_masters.sql:70-71`）なので空の表ができる。アプリは読まない（K1 0件）ので中身を戻さなくても動く。revert も migrations を含む PR なので GO が要る点をカードに一言足すとよい
- 控え（§5 の2）: 決まりに合わない（M3）

## 未確認

- U1. 表を消すことに ADR が要るか（`backend/AGENTS.md:28`）。設計 §6 の4 の PO 承認で足りるかは PO/Opus の判断。審査役は決めない
- U2. 本番の依存がビューだけであること・5社の中身が6行で同じこと（カード §1 の本番の事実。DB に繋いでいない）
- U3. PR-B の本番反映の時刻（マージ 02:06 UTC は確かめた。Deploy の成功時刻は見ていない）
- U4. 試験は流していない（読むだけの役）。①④の結論は静的な読みによる

## 確かめた命令（主なもの）

```bash
git show origin/main:scripts/run_all_migrations.sh | cat -n | sed -n '205,280p;560,575p'; git show origin/main:scripts/run_all_migrations.sh | wc -l   # 1251
git grep -nE 'tenant_table_ref\(db, tenant_id, "channel_masters"\)|\{schema(_name)?\}\.channel_masters' origin/main -- backend/app   # rc=1
git grep -n 'channel_masters' origin/main -- backend scripts migrations .github
git show origin/main:migrations/20261024_100300_create_ai_cloud_views.sql | sha256sum   # bb7a4e7b...a1b16
git show origin/main:scripts/migration-guard/reference-allowlist.tsv | sed -n 7p
git show origin/main:docs/handoff/cloud-case-ai/stage1-column-class.tsv | sed -n '574,576p'
git show origin/main:backend/tests/ops/test_ai_cloud_views.py | sed -n '484p;490-566p'
git show origin/main:backend/tests/rls_bootstrap.py | sed -n '36,40p;187,199p'
git show origin/main:backend/tests/test_tenant_loop_migration_guard.py | sed -n '42p;137p;294-329p'
git show origin/main:backend/tests/test_value_migrations_neutralized.py | sed -n '26p;84-88p'
git show origin/main:.github/workflows/migration-guard.yml | sed -n '343,391p'
git ls-tree --name-only origin/main migrations/ | grep 20261107   # 180000 は無い
for b in $(git branch -r --format='%(refname:short)'); do git ls-tree --name-only $b migrations/ | grep -q 20261107_180000 && echo $b; done   # 出力なし
git log origin/main --merges --format='%h %cI %s' --since=2026-11-06 | grep channel-master   # #5230 2026-11-07T11:06:03+09:00
```
