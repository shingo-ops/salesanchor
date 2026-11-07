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

---

## 2回目

- 審査役: 設計審査役（Architect・クラウドの定期実行）。読むだけ。コード・SQL・試験・ADR は変えていない
- 対象: `release/channel-master-pr-c` 8e4fb409b の `card-pr-c.md`・`docs/adr/ADR-1069-drop-tenant-channel-masters.md`（・`docs/adr/README.md` の1行）
- 照合先: origin/main 44a6ccce1（1回目と同じ。`git diff --stat 2969725e9 origin/main -- scripts/run_all_migrations.sh migrations/ scripts/migration-guard/ docs/handoff/cloud-case-ai/ .github/ backend/tests/rls_bootstrap.py backend/tests/test_tenant_loop_migration_guard.py backend/tests/test_value_migrations_neutralized.py backend/tests/ops/test_ai_cloud_views.py backend/tests/test_rls_bootstrap_ordering.py backend/tests/test_tcg_work_matching_integration.py backend/tests/test_leads_assignment_opened_at_pg.py scripts/check-process-artifacts.js docs/adr/` は出力なし。カード §1 の行番号はそのまま有効）

### 判定: **REVISE**

1回目の M1〜M3・R1〜R5 は全部カードに入った（下の①）。ただし、直した所に新しく3つの食い違いがある。どれも実装役か Opus が手順どおりに進むと止まるか、確かめが成り立たない。M4〜M6 を直せば APPROVE できる（直し方は数行ずつ）。

### 必須

#### M4. ADR-1069 の索引の状態が「Accepted」になっている（本文は Proposed）
- 【事実】`docs/adr/ADR-1069-drop-tenant-channel-masters.md:5` の状態の欄は「Proposed（…確かめたら Accepted に上げる）」。索引を作る `scripts/generate-adr-index.js:51-52` は表の欄をそのまま取り、`:59` で小文字にして `accept` を含めば Accepted、`:60` の Proposed より先に当てる。だから `docs/adr/README.md:247`（このブランチで足した行）は `Accepted` になっている
- 【事実】`node scripts/generate-adr-index.js --check` は「✅ 最新の状態」（rc=0）。CI「ADR index is up to date」（`.github/workflows/adr-index-check.yml:29-31`）は通るが、索引は間違った状態を正として載せる
- 【事実】他の ADR はこの罠を避けている: ADR-1068 `:5`「採用に上げる」、ADR-1067 `:5`「決定済みへ進める」（どちらも `:59` の語に当たらない）
- 直し方（Opus。実装役は docs/adr を触らない決まり）: `:5` の括弧の中を、`:59` の語（accept・承認・採択・完了・実装済・done）を含まない言い方にする。例「Proposed（PO 本人の「GO #PR番号」でマージし、本番で K1＝会社ごとの表0 を反映2回またいで確かめたら採用に上げる）」。そのあと `node scripts/generate-adr-index.js` を流し、README の行が `Proposed` になることを確かめる
- 確かめた命令: `sed -n '33,60p' scripts/generate-adr-index.js`・`git diff 3c66d4bf6 8e4fb409b -- docs/adr/README.md`・`node scripts/generate-adr-index.js --check`・`head -12 docs/adr/ADR-1068-staff-self-registration.md docs/adr/ADR-1067-public-tenant-config-tables-rls.md`

#### M5. カード §3 の c「CI のログから `test_drop_tenant_channel_masters_pg.py ... PASSED` の行を貼る」は、その行が CI のログに出ない
- 【事実】backend の試験は `.github/workflows/test.yml:253` の `pytest -q --tb=short` で流れ、`backend/pyproject.toml` の addopts（`[tool.pytest.ini_options]` の `-n auto --dist=loadfile …`）で xdist が付く。`-q` で `-v`/`-rA` が無いので、通った試験はファイル名の行を出さない（点だけ）。skip の理由の一覧も出ない
- 【推測】実装役は「該当行が無い＝合格にできない」と読み、§3 の c で止まる（BLOCKED）か、別の流し方を自分で足す
- 直し方（どちらかをカードに書く）:
  - (a) 判定を「`pytest-run` が緑」に替え、理由を一文書く: CI では `GITHUB_ACTIONS=true` なので skipif（カード 2-11 の `pytestmark`）は偽。さらに `pg` 試験部品は環境が無いと assert で落ちる（`backend/tests/test_tcg_work_matching_integration.py:386-391`）ので、CI では「黙って skip」にならない。貼るのはログ末尾の `N passed` の行
  - (b) ファイル名の行が欲しいなら、PR コメントではなく試験の中で確かめる（例: 2回流した後の件数を assert）。ログの形に頼らない
- 確かめた命令: `sed -n '225,258p' .github/workflows/test.yml`・`sed -n '45,80p' backend/pyproject.toml | grep -n addopts`

#### M6. カード §5 の2 の控えの SELECT と §3 の h（・ADR-1069 の確かめ方）の数え方は、読み取り専用の道では成り立たない
- 【事実】`docs/handoff/ai-readonly-db-path/usage.md:15`「読めるのは `ai_ro` スキーマのビュー…ベース表（`public.users` 等）は読めない（42501）」。カード `card-pr-c.md:153` は `SELECT * FROM tenant_00X.channel_masters`（ベース表）なので 42501 で失敗する
- 【事実】`migrations/20261017_130100_create_ai_ro_views.sql:25-33` は `public` と `tenant\_%` の実在の表から `ai_ro` のビューを作り、`:23` の除外語（password・_token など）に channel_masters の列は当たらない（列は id・tenant_id・platform・display_name・connection_type・is_active・created_at。`migrations/20260611_100000_create_channel_masters.sql:40-50`）。だから `ai_ro.tenant_00X__channel_masters` で全列が読める（カード §1 `:14` もこのビューがあると書く）
- 【事実（PostgreSQL の決まり）】`information_schema.tables` は、呼び手がその表に権限を持つものだけを見せる。reader はベース表に権限が無い（usage.md:15）ので、`card-pr-c.md:139`（§3 の h）・`ADR-1069:39` の数え方は、表が残っていても tenant_* 0 と出て、public も 0 になる（「public 1」が満たせず、tenant_* 0 は表が残っていても出る）
- 直し方（Opus）:
  - §5 の2: `SELECT * FROM ai_ro.tenant_00X__channel_masters ORDER BY id`（5社、1文ずつ）。デプロイ中は ai_ro が約70秒外れる（usage.md §4）ので、反映を始める前に取る
  - §3 の h と ADR-1069 `:39`: 権限で絞られない目録で数える。例 `SELECT n.nspname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE c.relname='channel_masters' AND c.relkind='r' ORDER BY 1`（期待: public だけ）。【推測】reader の役割から `pg_catalog` は読める（既定で PUBLIC に読み権限）。初回に1回流して確かめる
  - 置き場所: usage.md:16 は「出力は `/tmp/CC報告ファイル/` 配下に保存しチャットに貼らない」。カードの `docs/handoff/channel-master-shared/pr-c-backup/`（repo に commit）との関係を一文で決める（中身は連絡手段の名前6行で秘密は無いが、決まりの例外であることを書く）
- 確かめた命令: `git show origin/main:docs/handoff/ai-readonly-db-path/usage.md | sed -n 1,40p`・`sed -n '18,40p' migrations/20261017_130100_create_ai_ro_views.sql`

### 推奨

- R6. 2-11 の手順6（`card-pr-c.md:122`）は、この試験の DB では空の比べになる。【事実】`pg` 試験部品は `provision`・`migrate`（`test_tcg_work_matching_integration.py:406-408`）で TCG 系の表を作るが、`public.channel_masters` を作る `20261106_190000_create_public_channel_masters.sql` は流さない（このファイルの中に channel の文字は supplier_channels だけ）。そして 20261106 は `public.tenants` を参照する（`:15`）。【推測】`to_regclass` は前後とも NULL で、手順6 は何も確かめない。「この DB には public の表が無いので手順6 は省く」と書くか、何を守りたいかを書き直す
- R7. 2-11 の手順1 の片付け（`card-pr-c.md:117`、スキーマを消す文）は要らない。【事実】`pg` 試験部品は試験ごとに専用 DB を作り（`:398`）、終わりに DB ごと消す（`:434`）。片付けの文を試験に書かないほうが、見張りの危険語にも当たらない
- R8. `pg` は3つ組を返す（`test_tcg_work_matching_integration.py:425` `yield connection, engine, url…`）。手本どおり `connection, _, _ = pg`（`backend/tests/test_leads_assignment_opened_at_pg.py:104`）と一文書く
- R9. 試験 DB には部品が作る `tenant_006`・`tenant_902`・`tenant_901`（`:407`・`:35`）もあり、20260611 と新 migration は全 `tenant_\d+` に効く。手順4・5 を2つのスキーマに絞るのは正しいが、手順4・5 の `IN (...)` を外して「全 tenant_ スキーマで0」にすると、ループの範囲も確かめられる（任意）

### 観点ごとの結果

#### ① 1回目の指摘の直り（origin/main と照合）

| 指摘 | 結果 | 根拠 |
|---|---|---|
| M1 チェック6 | 直った | `card-pr-c.md:8`・`:138`・`:144` に PR 本文の `ADR-1069`・`ADR-1007`。【事実】`.github/workflows/migration-guard.yml:343-391`（origin/main）は本文の `ADR-[0-9]+` があれば exit 0。ADR の中身・状態は見ない |
| M2 使い捨て DB の試験 | 直った（ただし証拠の取り方が M5） | `card-pr-c.md:47`・`:112-124`・`:134`。2-8 の「試験からは流さない」は消え、`_REVIEWED` に own_database で登録（`:88-101`） |
| M3 控え | 一部（reader の道に替えたが、読む表が M6） | `card-pr-c.md:153`。`deploy.yml:214`・`:221` の参照は origin/main と一致 |
| R1 PR 本文の欄 | 直った | `card-pr-c.md:145`。消した行のあるファイル8本を「削除するファイル:」に並べる |
| R2 ordering 試験 | 直った | `card-pr-c.md:137` に `test_rls_bootstrap_ordering.py` |
| R3 TSV の表現 | 直った | `card-pr-c.md:22`（データ行 1057・SQL 1084・試験は読まない） |
| R4 エラーを数える所 | 直った（決めるのは Opus と明記） | `card-pr-c.md:152` |
| R5 時刻の確かめ | 直った | `card-pr-c.md:46`。【事実】今も origin/main・全リモート枝に 20261107_180000 は無い（下の命令、出力なし） |
| （1回目⑥ revert の GO） | 直った | `card-pr-c.md:159` |

#### ② 2-11 の試験が実行できるか — できる（M5・R6〜R8 を除く）
- 【事実】`pg`（`test_tcg_work_matching_integration.py:384-434`）は CI だけで動き（`:386` assert、`:390-391` localhost・jarvis_test_db だけ）、`tcg_work_test_<uuid>` の専用 DB を作り（`:393`・`:398`）、`provision`・`tenant_006`/`tenant_902` のスキーマ作成・`migrate` を済ませて渡す（`:406-408`）。既存の `SCHEMA = "tenant_901"`（`:35`）もこの DB の中だけ。カードの `tenant_9101`・`tenant_9102` は重ならない
- 【事実】20260611（`migrations/20260611_100000_create_channel_masters.sql:24-79`）が要るのは `pg_namespace`・`pg_policies` と `current_setting` だけ。関数・型・他の表を要らない。`SUBSTRING(nspname FROM 8)::INTEGER` は `tenant_9101` → 9101 で通る。seed は無効化済み（`:71-72`）なので行は入らない
- 【事実】このファイルの中に channel_masters の文字は無い（`grep -n channel` は supplier_channels だけ）。部品が先に同名の表や依存（ビュー・外部キー）を作ることは無いので、CASCADE 無しの消す文は通る【推測：provision の中身は全部は読んでいない。channel の文字が無いことで判断】
- 【事実】手順4 の `information_schema.tables` は、ここでは表の持ち主（試験の接続＝jarvis）で数えるので見える。M6 とは別（M6 は reader の場合）
- 【事実】CI の pytest は `RLS_ADMIN_DATABASE_URL`（`.github/workflows/test.yml:236`、jarvis_test_db）を渡すので、部品の条件を満たす。手本の `test_leads_assignment_opened_at_pg.py:36-46` と同じ入口
- 【事実】`check_test_schema_dup.py` は試験の文字列中の新しい表を作る文を拾う。カードは本体の SQL ファイルを読んで流す（`:115`）ので当たらない。`check-process-artifacts.js:967-989` の DROP 検出は migration のパス（`isMigrationPath`）だけを見るので、試験ファイルは対象外

#### ③ 2-8 の `_REVIEWED` と両向きの検査（`test_tenant_loop_migration_guard.py:294-307`・`:310-329`）— 釣り合う
- 【事実】新 migration の `nspname ~ '^tenant_\d+$'` は `_LOOP_RE`（`:19-22`）に当たり、名前は `_MIGRATION_NAME_RE`（`:23`）に合う。だから新しい試験は (新試験, 20260611)・(新試験, 20261107_180000) の2組を「実物」に持つ。カードの登録（`card-pr-c.md:88-101`）はこの2組と一致
- 【事実】2-7 後、rls_bootstrap.py の 20260611 の文字は `:38`・`:188` の2か所だけ（`grep -rn 20260611_100000 backend/tests`）で両方消える。2-8 で `:42` を消すので釣り合う。test_value_migrations_neutralized.py は 2-9 で `:84-88` を消しても `:26` が残るので、`:137` を残すのが正しい
- 【事実】own_database の条件（`:318-320`）は `"test_tcg_work_matching_integration import"` の文字で満たす。カードの import 行 `from tests.test_tcg_work_matching_integration import pg as pg` はこれを含む
- 【推測】新しい試験の説明やコメントに他の全社ループの migration の名前（例 20260614・20261106 以外の loop 物）を書くと、その組も登録が要る。カードに「試験ファイルに書く migration の名前はこの2本だけ」と一言あると安全（任意）

#### ④ ADR-1069 の書式・CI・番号
- 書式: 【事実】見出し・項目表（ステータス・備考・起案日・方針の決定者・関連・設計・根拠）・`---` の形は ADR-1067・ADR-1068 と同じ。参照先の ADR-1007・135・136・1003・1024・145 はどれも docs/adr に実在（`ls docs/adr | grep`）
- 索引: CI は通るが状態が間違って載る（M4）
- 番号: 【事実】`git ls-tree origin/main docs/adr/` に ADR-1069 は無い。fetch した全リモート枝で ADR-1069 のファイルを持つのはこの枝だけ。開いている PR（91件）を `is:pr is:open ADR-1069` で検索して 0件。重なりは無い
- 【未確認】リモート枝として fetch されていない PR の head（フォーク等）は見ていない

#### ⑤ ほかに実装役が止まる点
- M5（ログの行が出ない）が一番止まりやすい
- 【事実】チェック6 は本文の最初の `ADR-` を見るだけで、状態を見ない（`:369-375`）。M4 の直しは CI には影響しない
- 【推測】2-11 の試験は `pg` 部品の provision・migrate を丸ごと流すので、1本でも数秒〜十数秒かかる。`--dist=loadfile` なので他の試験とは並ぶ。問題にはならない見込み

### 未確認

- U5. 試験は流していない（読むだけの役。PostgreSQL を立てていない）。②③は静的な読み
- U6. reader の役割で `pg_catalog`（pg_class・pg_namespace）が読めるか（M6 の直し方の前提）。本番に繋いでいない
- U7. `pg` 部品の `provision`（`test_tcg_work_matching_integration.py:51-`）の中身は全部は読んでいない
- U8. 見張り（クラウドの PreToolUse フック）が、読むだけの grep 1本を、検索語に DB を消す語が入っていたことで止めた。言い換えて流し直してはいない。その grep で取ろうとした行番号（`pg` 部品の yield・DB を消す行）は、先に読んだ `sed -n '370,460p'` の出力から数えた（`:425`・`:434`）

### 確かめた命令（2回目）

```bash
git -C ~/w-prc2 log --oneline -3                     # 8e4fb409b
git diff 3c66d4bf6 8e4fb409b --stat                  # ADR-1069・README・card の3本
git rev-parse --short origin/main                    # 44a6ccce1
sed -n '33,60p' scripts/generate-adr-index.js; node scripts/generate-adr-index.js --check   # ✅ rc=0
for b in $(git branch -r --format='%(refname:short)'); do git ls-tree --name-only $b docs/adr/ | grep -q ADR-1069 && echo $b; done   # この枝だけ
gh api -X GET search/issues -f q='repo:shingo-ops/salesanchor is:pr is:open ADR-1069' --jq .total_count   # 0（open 全体 91）
for b in $(git branch -r --format='%(refname:short)'); do git ls-tree --name-only $b migrations/ | grep -q 20261107_180000 && echo $b; done   # 出力なし
git show origin/main:backend/tests/test_tcg_work_matching_integration.py | sed -n '370,460p'
git show origin/main:migrations/20260611_100000_create_channel_masters.sql | cat -n
grep -n '_REVIEWED\|_EXTRA_TEXT_ONLY\|20260611\|test_leads_assignment_opened_at_pg\|^def ' backend/tests/test_tenant_loop_migration_guard.py
grep -rn '20260611_100000' backend/tests
sed -n '225,258p' .github/workflows/test.yml; grep -n addopts backend/pyproject.toml
git show origin/main:docs/handoff/ai-readonly-db-path/usage.md | sed -n 1,40p
sed -n '18,40p' migrations/20261017_130100_create_ai_ro_views.sql
git show origin/main:.github/workflows/migration-guard.yml | sed -n '343,391p'
sed -n '955,1000p' scripts/check-process-artifacts.js
```
