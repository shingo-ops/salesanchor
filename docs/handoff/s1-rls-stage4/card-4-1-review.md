# 設計審査 — 便④-1 実装カード（card-4-1.md）

**判定: REVISE**（指摘 5 件。直さないと動かないのは 1 件＝§7 の K5-2。実装そのもの §1〜§6・§8 は進めてよい水準）

- 審査対象: docs/handoff/s1-rls-stage4/card-4-1.md（枝 release/s1-rls-stage4-design、HEAD c354964d4 を確認）
- 照合先: 同ディレクトリの design.md・recon.md、docs/specs/tenant-rls/kgi.md（KGI-4〜6 の行 :35-37 を確認）、origin/main 5574bf327（`git show origin/main:<path>` で確認）
- 審査役は本番・製品コードに触っていない。外部サイトも見ていない。実 PostgreSQL では流していない（下の【未確認】）。

## 指摘

### 1. 【直さないと実行できない】§7 K5-2 の `python -` は台本の 43 行目で落ちる
- 【事実】カードの手順は台本を標準入力で `python -` に渡す。台本は import の直後に `_APP_ROOT = Path(__file__).resolve().parent.parent` を実行する（scripts/export_inventory_for_sheet.py:43、origin/main）。標準入力から流す Python では `__file__` が未定義なので、DB に着く前に NameError で終了コードが 0 にならない。§7 の「両方で終了コード 0・`OK: 0 rows written to /dev/null`」は満たせない。
- 【事実】`/dev/null` への出力自体は通る（write_csv は `output.parent.mkdir(parents=True, exist_ok=True)` のあと `open("w")`、同 write_csv 関数内）。`DATABASE_URL` は入れ物の環境から読む（同 :182）。入れ物の WORKDIR は /app（backend/Dockerfile:4）、入れ物の名前 astro-webapp-backend-1 は run_all_migrations.sh:23 と一致。
- 直し案（【未確認】動作は試していない）: 実行前に `__file__` と `sys.argv` を与える。例 `docker exec -i astro-webapp-backend-1 python -c "import sys; sys.argv=['x','--tenant','1','--since','2000-01-01','--output','/dev/null']; __file__='/app/scripts/export_inventory_for_sheet.py'; exec(compile(sys.stdin.read(), __file__, 'exec'))" < scripts/export_inventory_for_sheet.py`。`sys.path` に /app が入るので app 側の import も通る見込み。入れ物が `/app/scripts` を持たないことはカードの記述（`COPY . .` は backend/ だけ）と整合。Opus が反映の前の 1 回目で動くことを先に確かめる、とカードに書くとよい。

### 2. 【直すとよい】§1 が名指しする `backend/app/ops/tenant_rls_allowlist.py` は origin/main に無い
- 【事実】`git show origin/main:backend/app/ops/tenant_rls_allowlist.py` は「path does not exist」。`git grep tenant_rls_allowlist origin/main` は別の設計文書（docs/handoff/tenant-owner-login-approval/design.md:116 ほか）の予定記述だけ。
- カード §1 は「#5194 の版でも中身は空 `{}`」と書くが、その PR は main に入っていない。【未確認】#5194 の中身は見ていない。
- 影響は小さい（「触らない」指定なので実装は変わらない）。「main に無い。便5 が入った後に一覧の追記が要るかは別途」と直すか、行を削る。

### 3. 【直すとよい】design.md §3 の便④-1 行が `set_config(..., false)` のまま。カード §4 は `true`
- 【事実】design.md:84 は `false`（接続の間ずっと）、card-4-1.md §4 は `true`（取引の間だけ）。カードは理由を書いている（共有 engine の接続の使い回し）。
- 【事実】`true` で足りる根拠は成り立つ。`async with engine.connect()` は最初の `execute` で取引が自動開始し、抜けるときに戻される（SQLAlchemy 2.0）。set_config と SELECT は同じ接続・同じ取引。試験の手本も同じ形（test_users_rls.py:_ctx_conn は `set_config('app.tenant_id', :t, true)`）。要件の sqlalchemy は 2.0 系。
- 食い違いを残すと、後で design を根拠に `false` へ寄せる人が出る。design.md:84 を `true` に直すか、カードに「design §3 を上書き」と一言足す。

### 4. 【直すとよい】§5 `_fresh()` の手順 1: tenants 976・977 の INSERT 列が書かれていない／そもそも必須でない
- 【事実】inventory_movements に tenants への外部キーは無い（migrations/062_create_inventory_movements_and_budget.sql の定義は `tenant_id INTEGER NOT NULL` のみ）。tenants の行が無くても試験は成り立つ。
- 【事実】入れるなら、`_ensure_public_users` が作る tenants は `tenant_code NOT NULL UNIQUE`・`id INTEGER PRIMARY KEY`（identity なし、rls_bootstrap.py:213-225）。test_users_rls.py は `_BOOTSTRAP_EXTRA_DDL` で identity などを足してから `(id, tenant_code, tenant_name, company_name)` を入れている。カードは「最小の土台」としか書かず、実装役が列で迷う。
- 直し案: 「tenants への INSERT は不要（FK なし）。`_ensure_public_users` も不要」と書くか、列を明記する。`_ensure_public_users` なしでも `bootstrap_public_products` は test_suppliers_rls.py:86 が使い捨て DB でそのまま呼んでいる前例がある（【事実】）。

### 5. 【直すとよい】§3 の「末尾の『ここから追加』セクション」は実在しない見出し
- 【事実】`grep -n "ここから追加" scripts/run_all_migrations.sh` は :15 の注意書き 1 件だけ。見出しは無い。最終行は :1237 `run_sql migrations/20261106_210000_add_notification_channels_blueprint_key.sql`（カードの行番号どおり、全 1237 行、末尾が最後の run_sql）。追記位置そのものは正しい。
- 【事実】ai_ro・ai_cloud のビュー作成は EXIT trap で「常に最後」に流れる（run_all_migrations.sh:224-243）ので、末尾追記がビュー作成より後になることはない。
- 直し案: 「ここから追加」の語を消し、「:1237 の次の行」とだけ書く。

## 確かめて一致した点（【事実】）

- (a) §2 の SQL は design §2-1 の型A に `<表>` を inventory_movements で埋めたものと一字一句同じ（ENABLE → FORCE → 各 DROP POLICY IF EXISTS → CREATE POLICY ×4、`NULLIF(..., '')::INTEGER`、`BEGIN;`〜`COMMIT;`）。ENABLE・FORCE・DROP IF EXISTS・CREATE は繰り返し流しても通るので冪等。前例 migrations/20261106_120000_create_discord_server_snapshot_tables.sql:13・:69 も BEGIN/COMMIT 付き。
- (b) 追記位置は :1237 の後で正しい。origin/main の `git ls-tree --name-only origin/main migrations/` の末尾は 20261106_210000 で、20261107_100000 より後の名前は無い。全リモート枝の migrations/ にも 20261107 以降の名前は無い（枝の走査で 0 件）。
- (c) §4 の変更前コードは origin/main の scripts/export_inventory_for_sheet.py:108-109（`async with engine.connect() as conn:` / `rows = (await conn.execute(text(sql), params)).mappings().all()`）と一致。SQL の WHERE tenant_id=:tid ・並びも同じ。
- (d) 会社番号 976・977: `git grep -n -E "\b(976|977)\b" origin/main -- backend/tests` は 0 件。`bootstrap_public_products` は rls_bootstrap.py:327、`_apply_migration` は :149、`_ensure_public_users` は :213 に実在。`_apply_migration` は asyncpg の raw 接続の Simple Query で流すので、移行ファイルの `BEGIN;`〜`COMMIT;` は通る。skipif と `RLS_ADMIN_DATABASE_URL`・`RLS_TEST_DATABASE_URL` は test_users_rls.py:20-36 と同じ構え、CI は test.yml:232-236 でこの 2 つを設定し、jarvis（管理）・salesanchor_app（アプリ）で接続する。
- (d) 試験の組み立て: 算術トリガは 062 の `after_qty = before_qty + delta_qty`（before 100・delta -1・after 99 は満たす）。source_type 'manual_adjust' は CHECK の許容値。operator_id・product_id は NOT NULL で、カードの手順 3・5 が満たす。①〜⑧ の期待（②0 行・③42501・④0 行・⑤運営で両社・⑥0 行かつ 22P02 でない・⑧WITH CHECK で 42501）はポリシーの文面と合う。
- (e)/§8: 戻しの SQL は design §7 の形で、ポリシー 4 本の DROP → NO FORCE → DISABLE の順は正しい。K4-2 のビュー（ai_ro）は持ち主 jarvis が superuser（ADR-1024:31、ADR-1018:16）なので RLS 後も全行を数える、という記述は ADR の記載と合う。
- 触らない範囲: 他に inventory_movements に触る本番コードは無い（`git grep -n -i -E "inventory_movements|InventoryMovement" origin/main -- backend/app` の結果は services/inventory_movements.py の読み取り検証と phase_gate.py のコメントだけ）。カードの「本番コードの書込なし」は合う。ai_cloud の列マスク定義（20261024_100300:123-124）は RLS と無関係。

## 【未確認】

- 実 PostgreSQL で §5 の `_fresh()`（`bootstrap_public_products` を使い捨て DB へ → products に name・stock_quantity だけで INSERT）が通るか。前例は test_suppliers_rls.py:86（同関数）と test_inventory_sprint1_migrations.py:313-316（同じ INSERT、共有 DB）。組み合わせは見ていない。カード §5・§9 に「通らなければ止まって Opus に戻す」があるので手当ては済み。
- 指摘 1 の直し案コマンドの実動作。
- CI の Backend Tests が §5 の新規試験を skip せず走らせるか（test.yml の環境変数は確認済みだが、実走は見ていない）。
- 本番の `docker exec ... astro-webapp-backend-1` が blue-green の後も同名か（scripts/blue-green-cutover.sh:27 の記述のみ確認）。カードは先に名前を読む手順を入れている。

## 2回目

**判定: APPROVE**（1回目の 5 件はすべて §11 の表どおりに処理済み。直しで新しく出た食い違いは 0 件。軽い注記 1 件のみで、直さなくても進めてよい）

- 審査対象: 枝 release/s1-rls-stage4-design の HEAD 60cf823d0（`git rev-parse origin/release/s1-rls-stage4-design` で確認）。差分は `git diff b2ae0dd1d 60cf823d0`（card-4-1.md と design.md の 2 ファイルのみ）。
- 照合先: origin/main 5574bf327（`git rev-parse origin/main` で確認。`git show origin/main:<path>` で照合）。
- 審査役は本番・製品コードに触っていない。外部サイトも見ていない。実 PostgreSQL は使っていない。

### 指摘 1（退けた件）— 退けた理由は成り立つ。重さ: 解消（問題なし）

- 【事実】実測: `echo 'print(repr(__file__))' | python3.12 -` の出力は `'<stdin>'`（Python 3.12.3、このクラウドの実行環境）。`python3`（3.11.18）でも同じ `'<stdin>'`。1回目の「`__file__` は未定義で NameError」は誤りだった。
- 【事実】引数つきでも確認: `printf 'import sys\nprint(repr(__file__), sys.argv)\n' | python3.12 - --tenant 1 --since 2000-01-01` は `'<stdin>' ['-', '--tenant', '1', '--since', '2000-01-01']`。argparse が読む `sys.argv[1:]` はカードの流し方で渡る。
- 【事実】scripts/export_inventory_for_sheet.py:43-45（origin/main）は `Path(__file__).resolve().parent.parent` を sys.path に足すだけ。`'<stdin>'` では実行ディレクトリ基準の `/` になり、足されても無害。import は :47-48 の sqlalchemy のみ（app 側の import なし）。:205 `if __name__ == "__main__":` は標準入力でも真。入れ物は backend/Dockerfile:1 `python:3.12-slim`、本実測と同じ系統。
- 【事実】card-4-1.md §7 K5-2（`:124-128` 付近）に、実測の記述と「1回目で終了コード 0 でない・`OK:` 行が出ないときは合流せず止まる」が足されている。1回目の私の指摘の趣旨（動かない手順で進めない）は、この保険で満たされる。
- 【未確認】本番の入れ物（astro-webapp-backend-1）の中での実走。カードも「反映の前の 1 回目が手順の試しを兼ねる」と明記している。

### 指摘 2 — 反映済み。重さ: 解消
- 【事実】card-4-1.md:22 の「触らない」が「`backend/app/ops/tenant_rls_allowlist.py`。origin/main 5574bf327 には無い＝便5 の PR #5194 が未合流。本便では作らない・触らない」に直っている。`git show origin/main:backend/app/ops/tenant_rls_allowlist.py` は「path does not exist」で、記述と一致。
- 【未確認】#5194 の中身。1回目と同じ。カードの記述は「無い」とだけ言っていて、中身には踏み込んでいない。

### 指摘 3 — 反映済み。重さ: 解消
- 【事実】design.md:84 が `set_config('app.tenant_id', <会社>, true)` に直り、理由の参照先（card-4-1.md §4）が書かれた。card-4-1.md:70 の実装コードも `true` で、2 文書は一致。

### 指摘 4 — 反映済み。重さ: 解消
- 【事実】card-4-1.md:84 が「tenants・users の土台は作らない（`_ensure_public_users` も呼ばない・tenants に INSERT しない）」に直っている。根拠の「外部キーは products・suppliers だけ」は origin/main の migrations/062_create_inventory_movements_and_budget.sql:91（products）・:97（suppliers）と一致（:50 は別の表の列。tenants・users への REFERENCES は inventory_movements にない）。前例 backend/tests/test_suppliers_rls.py:86 は `await bootstrap_public_products(admin_engine)` を直接呼んでおり一致。rls_bootstrap.py:327 に関数が実在。
- 【事実】この直しで §5 の ①〜⑨ や手順 3（products へ name・stock_quantity のみ INSERT、前例 test_inventory_sprint1_migrations.py:313-316 と同形）に矛盾は出ていない。

### 指摘 5 — 反映済み。重さ: 解消
- 【事実】card-4-1.md:13 が「:1237 `run_sql migrations/20261106_210000_add_notification_channels_blueprint_key.sql` の次の行。区切りの見出しは無い」に直っている。origin/main の scripts/run_all_migrations.sh は 1237 行で、末尾がその `run_sql`。`git ls-tree --name-only origin/main migrations/` の末尾は 20261106_210000 で、20261107_100000 より後の名前は無い。976・977 は `git grep -n -E "\b(976|977)\b" origin/main -- backend/tests` で 0 件。

### 直しで新しく出た食い違い（0 件）と注記（1 件・直さなくてよい）
- 【事実】新しい食い違いは見つからなかった。§11 の表の「どこを直したか」の参照先は、実際の変更箇所と一致する（§1・§5・§7・design.md §3）。
- 注記: §7 K5-2 の「手元の Python 3.12.8」は、私の実測（3.12.3 と 3.11.18）と版が違うが、結果（`'<stdin>'`）は同じ。Opus が 3.12.8 で流した事実の裏取りはしていない。【未確認】。結論には影響しないので直し不要。

### 【未確認】（1回目から変わらない分）
- 実 PostgreSQL での §5 `_fresh()` の通り方。CI の Backend Tests が §5 の新規試験を skip せず走らせるか。本番の blue-green 後の入れ物名。いずれもカードに「通らなければ止まって Opus に戻す」「先に名前を読む」の手当てがある。

### 結び
- 【事実】`migrations/`・`scripts/` を含む実装の PR は、カード §10 のとおり危険 PR（ADR-135・ADR-136）。マージの前に別途の審査・CI 全緑・GO が要る。本審査は設計カードの審査で、実装の審査ではない。
