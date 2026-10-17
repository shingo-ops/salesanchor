# 実装カード 便3a: AI 用「本番 DB を読むだけの道」のリポジトリ側の実装

> この文書は何か（専門用語なしの1行）:
> 読むだけのデータベース利用者・秘密を除いたビュー・専用コンテナ・読み取り台本・テスト・レビュー必須設定を、リポジトリに入れる作業の手順書。

## 冒頭（必読）
- この便は危険パス `migrations/` と `scripts/run_all_migrations.sh` を含む。実装の PR は ADR-136 の GO 手順（CLAUDE.md:57）に乗る。マージ前に、チャットで「対象・変更 3 行サマリ・直前バックアップ確認」を PO に提示し、「GO #PR番号」を受領するまでマージ・適用しない。受領後に PR 本文へ `### GO記録` を転記する。
- 本カードは設計の持ち込み（ADR-113 の handoff）。**PO の実装承認は、設計の承認（ADR-1024 の Q0〜Q2）とは別に必要**。実装承認を受領するまで、この便に着手しない。PO の実装承認の原文と日時は、実装 PR の本文に転記する。
- 設計: [design.md](design.md)（K1〜K18、方式 §3）。根拠: [recon.md](recon.md)。ADR: [ADR-1024](../../adr/ADR-1024-ai-readonly-db-path.md)（Status: Proposed。実装 PR で Accepted に改訂するかは PO が決める）。
- 起点: `bash scripts/new-worktree.sh release/<英語で簡潔> --claude`。最初に `./scripts/dev/executor-preflight.sh || exit 1`。
- 守ること: 触ってよいのは各項目の「変更」のファイルだけ。1 便 1 目的。指示にない作業を混ぜない。秘密（パスワード・接続文字列の値）は画面・git・PR・ログに出さない。迷ったら全停止して `NEEDS_DECISION:`。
- 範囲外（便3b・便4）: `ai_reader` のパスワード設定、`.env` への追加、VPS の authorized_keys、Mac の鍵作成、フック修正、CLAUDE.md・メモの修正。この便では一切しない。
- 「未確認・実装担当が最初に確認」と書いた項目は、実物の file:line で確かめてから書く。確かめられなければ止まる。

## 実物点検（最初に。推測で進めない）
1. `scripts/run_all_migrations.sh` の末尾（:963 付近）に追記する形と、`run_sql` が jarvis で流すこと（:25, :61-66）を読む。
2. `scripts/check-migration-registration-exists.sh` と `scripts/check-migration-duplicate-registration.sh` を読み、新しい migration の登録の作法（ファイル名・登録行）を確かめる。
3. `backend/tests/conftest.py` を読み、DB に繋ぐテストの作法（使い捨ての DB を使えるか）を確かめる。**未確認**。使えなければ、ビュー生成のテストは CI の DB を使う形を NEEDS_DECISION: で相談する。
4. `docker-compose.yml` の backend サービス（:63 以降）で、イメージの作り方（`build: ./backend`）とネットワーク名（:551-553 `backnet`）を読み、別の compose ファイルから同じネットワークに繋ぐ書き方を `docker compose config` で確かめる。**未確認（recon U15）**。
5. `backend/app/services/tenant.py:1634` の `create_tenant_schema` を読み、新テナント作成時にビューを作り直す必要があるかを確かめる。**未確認（recon U7）**。当面は「次回デプロイまで読めない」でよい（fail-closed）。

---

## 項目 1: `ai_ro` ビューの生成

### 変更
- 新規: `migrations/<YYYYMMDD_HHMMSS>_create_ai_ro_views.sql`（時刻は実装日の最新にする。`ai_reader` の migration（項目 2）より後の時刻にする）。
- 変更: `scripts/run_all_migrations.sh` の**最後**に、項目 2 の migration の登録行の次に 1 行追加する。ビューは毎回の実行の最後に作り直す。

### 変更前後
- 変更前: `ai_ro` スキーマはない。`run_all_migrations.sh` の最後は `run_sql migrations/20261017_120000_line_conditions_value_rank.sql`（:963）。
- 変更後: 末尾に次が加わる（コメントと登録行）。
```
# ADR-1024: AI 用の読み取り専用ビュー（秘密列を除く）。毎回最後に作り直す（冪等）
run_sql migrations/<YYYYMMDD_HHMMSS>_create_ai_ro_views.sql
```
- SQL の中身（形。実装担当は書式を整えてよいが、判定の中身は変えない）:
  1. 1 つの取引（`BEGIN` から `COMMIT`）で、`DROP SCHEMA IF EXISTS ai_ro CASCADE;` → `CREATE SCHEMA ai_ro;`。持ち主は実行ユーザー jarvis のまま（`run_sql` が jarvis）。
  2. `DO` ブロックで、`public` と `tenant_%` のスキーマ（`pg_catalog`・`information_schema` は除く）の通常の表（`relkind = 'r'` と `'p'`）を `pg_class` / `pg_attribute` から走査する。
  3. 各表について、次の拒否リストに**当たらない**列だけを選ぶビューを `ai_ro."<スキーマ>__<表>"` として作る（`security_invoker` は付けない）。拒否リスト（小文字化した列名に対する正規表現）: `^password`、`_encrypted$`、`_secret`、`_token`、`hash`、`^secret`、`^api_key`、`private_key`、`credential`。
  4. 列がすべて除かれた表は、ビューを作らない。
  5. `GRANT USAGE ON SCHEMA ai_ro TO ai_reader;` と `GRANT SELECT ON ALL TABLES IN SCHEMA ai_ro TO ai_reader;`。ほかのスキーマには何も付けない。
  6. 最後に、生成したビューの数と、除いた列の数を `RAISE NOTICE` で出す（値は出さない）。
- 注: `hash` を含む列名はすべて除く（sha256 だけのトークン表の列も除かれる）。使い勝手より fail-closed を優先する決定。惜しい列は、後から PO の判断で個別に許可リストへ足す（この便では足さない）。

### 触らない範囲
- 既存の表・RLS ポリシー・既存のロール・`public` スキーマへの権限。`pg_read_all_data` の付与。BYPASSRLS の付与。

### 想定分岐
- `ai_reader` がまだない順番で流れた → 項目 2 の登録行を先にしてあるか確認。順番が逆なら登録行を入れ替える。
- 表の数が多く、実行に時間がかかる → 実測値（秒）を PR 本文に書く。デプロイの時間枠に響くなら NEEDS_DECISION:。
- 列名が拒否リストに当たるが、PO が読みたい列だった → この便では除いたままにする。
- ビューの持ち主の権限で行の制限が外れるか（recon U10）→ 項目 5 のテストで実機に確認する。外れなければ止まる。

### 止まる条件
- ビューの持ち主が jarvis 以外になる、または `run_sql` 以外で流す必要が出た。
- 拒否リストに当たる列が `ai_ro` に 1 本でも残る（項目 5 のテストが落ちる）。
- 既存の表やポリシーに対する変更が 1 行でも必要になった。

---

## 項目 2: `ai_reader` の migration

### 変更
- 新規: `migrations/<YYYYMMDD_HHMMSS>_create_ai_reader_role.sql`（項目 1 より前の時刻）。
- 変更: `scripts/run_all_migrations.sh` の末尾に登録行を 1 行（項目 1 の登録行の前）。

### 変更前後
- 変更前: 読み取り専用の DB ユーザーはない（recon F1-5）。
- 変更後:
  1. `DO` ブロックで `pg_roles` に `ai_reader` がなければ作る: `CREATE ROLE ai_reader LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS CONNECTION LIMIT 2;`（あれば何もしない）。
  2. `ALTER ROLE ai_reader SET log_statement = 'all';`（境界として効く唯一の設定）。
  3. `ALTER ROLE ai_reader SET default_transaction_read_only = on;`・`SET statement_timeout = '60s';`・`SET idle_in_transaction_session_timeout = '60s';`（事故防止。コメントに「境界ではない。利用者が戻せる」と書く）。
  4. パスワードは書かない。パスワードのないロールは scram で入れないので、便3b まで誰もログインできない。
- 付けないもの: `pg_read_all_data`、BYPASSRLS、`ai_ro` 以外への権限。

### 触らない範囲
- 既存のロール（jarvis・salesanchor_app・qa_tenant006_rw）。`.github/workflows/deploy.yml`（`ALTER ROLE … PASSWORD` の流儀は参考にするだけで、触らない）。pg_hba。

### 想定分岐
- 同名のロールが既にある → 何もしない（冪等）。属性が違う場合は止まって報告（勝手に ALTER しない）。
- `log_statement` の設定が `ALTER ROLE` で通らない → NEEDS_DECISION:（実行ユーザーが superuser でない可能性）。

### 止まる条件
- migration にパスワード・接続文字列の値を書く必要が出た。
- 実行ユーザーが jarvis でないことが分かった（recon U4 が崩れた）。

---

## 項目 3: `ai-reader` コンテナの compose 定義

### 変更
- 新規: `docker-compose.ai-reader.yml`（リポジトリ直下）。本体の `docker-compose.yml` は変えない（CODEOWNERS で個別に守るため、別ファイルにする）。

### 変更前後
- 変更前: 読み取り専用の実行場所はない。調査は backend コンテナ（`astro-webapp-backend-1`）に任意の Python を送る形だった。
- 変更後: サービス `ai-reader` を 1 つ定義する。
  - イメージは backend と同じ（`build: ./backend` と同じ Dockerfile。タグの揃え方は実物点検 4 で確定。**未確認**）。
  - `command: ["python", "-m", "app.ops.readonly_query"]`
  - `environment` は `AI_READER_DATABASE_URL=${AI_READER_DATABASE_URL}` の**1 つだけ**。`env_file` は使わない。`DATABASE_URL`・`ADMIN_DATABASE_URL`・`METADATA_FERNET_KEY` を渡さない。
  - `volumes` なし、`read_only: true`、`cap_drop: [ALL]`、`security_opt: [no-new-privileges:true]`、`tmpfs` なし、`mem_limit` は小さく（実測で決める）、`restart: "no"`。
  - ネットワークは本体の `backnet` だけ（外部ネットワークとして参照。名前の確定は実物点検 4）。`ports` なし。
  - 固定コマンド（便3b で authorized_keys に入れる）は `docker compose -f <絶対パス>/docker-compose.ai-reader.yml run --rm -T --no-deps ai-reader`。標準入力が通ること（recon U12）を、この便のテストの範囲で確かめられる所まで確かめ、本番での確認は便3b の K テストに送る。

### 触らない範囲
- `docker-compose.yml` 全体（backend・postgres・nginx 等の定義）。`docker-compose.monitoring.yml`。blue-green の切替スクリプト。

### 想定分岐
- 別ファイルから `backnet` に繋げない → NEEDS_DECISION:（`docker-compose.yml` に最小のサービスを足す案は PO に確認。CODEOWNERS に `docker-compose.yml` を足す影響が広い）。
- `read_only: true` で Python が動かない（キャッシュの書き込み）→ 書き込み先を `tmpfs` で最小限に足す。足した理由を PR に書く。
- `AI_READER_DATABASE_URL` が未設定のとき、compose が空文字で起動してしまう → `${AI_READER_DATABASE_URL:?}` の形で失敗させる。

### 止まる条件
- 他の環境変数・ボリューム・ネットワークを足さないと動かない。
- コンテナが書き込み可能になる、または capability が必要になる。

---

## 項目 4: `backend/app/ops/readonly_query.py`

### 変更
- 新規: `backend/app/ops/__init__.py`（空）、`backend/app/ops/readonly_query.py`。`python -m app.ops.readonly_query` で動く。`backend/app/ops/` は origin/main に存在しない（recon F8-4）。

### 変更前後
- 変更前: 読み取り台本はない。
- 変更後（型。判断の余地を残さないために、規則を全部書く）:
  1. 標準入力から SQL を読む。64KB を超えたら終了コード 2。
  2. 環境変数は `AI_READER_DATABASE_URL` **だけ**を読む（`os.environ.get` を他の名前に使わない）。未設定なら終了コード 3。`DATABASE_URL` に切り替えて代わりに使うことは禁止。この値は画面・ログ・エラー文に出さない（接続エラーの文面にも出さない）。
  3. 拒否（終了コード 2、理由を 1 行 stderr）: 先頭（コメントと空白を除く）が `\`／`;` で区切った 2 文以上／先頭語が SELECT・WITH・SHOW・EXPLAIN（ANALYZE なし）以外／本文（コメントを除く、大文字小文字を区別しない）に `set_config(`・`SET `（先頭語以外の位置を含む）・`COPY`・`pg_read_file`・`pg_sleep`・`lo_`・`pg_catalog.set_config` のいずれかを含む。この判定は使いやすさと二重目であり、守りの本体は DB の権限。
  4. 接続: psycopg2 で `AI_READER_DATABASE_URL` に接続。直後に `BEGIN READ ONLY` 相当（`conn.set_session(readonly=True)`）と `SET LOCAL statement_timeout = '60s'` を**台本自身が**発行する。
  5. 行数: 既定 200。上限 5000。SQL の先頭行に `-- limit=N` があるときだけ N（5000 まで）を使う。上限を超える指定は 5000 に切る。取得は `fetchmany` で上限+1 行までにし、超えたら stderr に「打ち切り」と書く。
  6. 出力: 1 行目に列名、以降を TSV で stdout。値の中のタブと改行はエスケープ。念のための二重目として、列名が拒否リスト（項目 1 の正規表現と同じ）に当たる場合は値を `<redacted>` に置換する。
  7. 最後に必ず rollback して閉じる。
  8. 記録: 1 回ごとに stderr へ 1 行（時刻・SQL の sha256 先頭 12 桁・SQL 本文の先頭 500 文字・行数・所要 ms・結果）。接続文字列の値は含めない。
  9. 終了コード: 0 成功／2 拒否／3 環境変数が未設定／4 DB エラー（理由の種類のみ、秘密は出さない）。
  10. `SSH_ORIGINAL_COMMAND` を読まない。`os.system`・`subprocess` を使わない。

### 触らない範囲
- 既存の `backend/app/` のコード全部（`db.py` などの共通部品を import しない。`DATABASE_URL` に触れる可能性があるため）。`backend/requirements.txt`（`psycopg2-binary==2.9.10` が既にある。recon F8-3）。

### 想定分岐
- 標準ライブラリだけで書けるか → psycopg2 以外の新しい部品は足さない。足したくなったら止まる。
- `EXPLAIN` の中の書き込み文（`EXPLAIN INSERT …`）→ 先頭語の判定とは別に、本文に書き込み系の語（INSERT・UPDATE・DELETE・TRUNCATE・DROP・ALTER・CREATE・GRANT）を含む EXPLAIN も拒否。迷ったら拒否側に倒す。
- 行の値が非常に大きい → 1 値 10KB で切って stderr に注記。

### 止まる条件
- `DATABASE_URL`・`ADMIN_DATABASE_URL`・`METADATA_FERNET_KEY` を読まないと動かない。
- 秘密の値が出力・ログ・例外文のどこかに出る形でしか書けない。

---

## 項目 5: テスト

### 変更
- 新規: `backend/tests/ops/test_readonly_query.py`（台本の単体テスト。DB 不要）。
- 新規: `backend/tests/ops/test_ai_ro_views.py`（ビュー生成のテスト。DB が要る。置き場所と作法は実物点検 3。**未確認**）。

### 変更前後
- 変更前: なし。
- 変更後（最低限の中身。K テストの番号は design.md §2）:
  1. 拒否する文字列（K2・K18）: `\c jarvis`、`\! ls`、`SELECT 1; SELECT 2`、`DELETE FROM x`、`INSERT …`、`UPDATE …`、`DROP …`、`WITH x AS (DELETE …) SELECT …`、`SELECT set_config('statement_timeout','0',false)`、`SET statement_timeout=0`、`SELECT pg_sleep(100)`、`COPY … TO PROGRAM`、`SELECT pg_read_file('/etc/passwd')`、`SELECT lo_import('/etc/passwd')`、`EXPLAIN ANALYZE SELECT …`。すべて終了コード 2。
  2. 通す文字列: `SELECT 1`、`WITH a AS (SELECT 1) SELECT * FROM a`、`SHOW server_version`、`EXPLAIN SELECT 1`。
  3. 環境変数が未設定のとき（K13）: `AI_READER_DATABASE_URL` を外し、`DATABASE_URL` を設定したままでも、終了コード 3 になり、`DATABASE_URL` の値で接続しない（接続関数を差し替えて呼ばれないことを確かめる）。
  4. 出力に接続文字列の値が出ない（エラー時も）。
  5. 行数: 既定 200、`-- limit=10000` が 5000 に切られる。
  6. 拒否リストに当たる列が `ai_ro` に 0 本（K6）: 生成後に `information_schema.columns` を `ai_ro` で引き、項目 1 の正規表現に当たる列名の数が 0。
  7. `ai_ro` のビューが、全テナント（tenant_001/003/004/005/006 と public）の代表を 1 本ずつ持つ（K8）。
  8. 新しい表を足してビュー生成の前は、`ai_reader` で読めない（K9）。
  9. `ai_reader` で `public.users` を直接 SELECT すると権限エラー（K6）。
- テストの後始末: 作ったロール・スキーマ・表を消す。本番に繋がない。

### 触らない範囲
- 既存のテストと `conftest.py`（共通の fixture を足す必要が出たら止まる）。

### 想定分岐
- DB が要るテストを CI で動かせない → 単体テスト（1〜5）だけをこの便に入れ、6〜9 は便3b の K テスト（本番、読み取りのみ）に移す。移した旨を PR 本文に明記し、NEEDS_DECISION: で PO/Opus に確認する。
- 使い捨ての DB が `BYPASSRLS` / superuser を使えない → ビューの持ち主の確認（K8）ができないので止まる。

### 止まる条件
- テストが本番の接続情報を必要とする。
- 拒否する文字列が 1 本でも通ってしまい、規則の変更が必要になった（項目 4 の設計に戻る）。

---

## 項目 6: CODEOWNERS

### 変更
- 変更: `.github/CODEOWNERS` の末尾に追加（既存の行は触らない）。

### 変更前後
- 変更前: `migrations/` と `scripts/` が @shingo-ops（.github/CODEOWNERS:21, 23）。`backend/app/ops/` と ai-reader の compose 定義は入っていない。
- 変更後: 次を追加する。
```
# ADR-1024: AI 用の読み取り専用の道。台本・compose 定義は PO の必須レビュー
backend/app/ops/                           @shingo-ops
docker-compose.ai-reader.yml               @shingo-ops
migrations/*ai_reader*                     @shingo-ops
migrations/*ai_ro*                         @shingo-ops
backend/tests/ops/                         @shingo-ops
```

### 触らない範囲
- 既存の行。Branch Protection の設定（`gh api` で変更しない。不可逆操作リスト）。

### 想定分岐
- CODEOWNERS の構文エラー → GitHub の「CODEOWNERS errors」で確認し直す。
- Branch Protection で Code Owners 必須が無効（recon U14）→ この便では変えない。PR 本文に「無効の可能性。PO が GUI で確認」と書く。

### 止まる条件
- `.github/workflows/` の変更が必要になった（`workflow-lint.yml` は変更禁止）。

---

## 完了の確認（この便）
1. 単体テスト（項目 5 の 1〜5）が合格。DB が要るテスト（6〜9）が CI で合格、または移した旨が PR 本文にある。
2. `git diff main...HEAD --name-only` を PR 本文に貼る。`migrations/` の混入が本テーマだけであることを確認（1 リリース 1 テーマ）。
3. PR 本文に `### 標準ワークフロー確認`、`### GO記録` の欄（GO 受領後に転記）、K テストのうち便3a で測れたものの結果。
4. 本番反映は、GO 受領後のマージ → deploy が `run_all_migrations.sh` を流す。**この時点では `ai_reader` にパスワードがなく、誰もログインできない**（便3b まで）。
5. 完了報告は DONE / BLOCKED: / NEEDS_DECISION: で始め、生出力の保存パスを添える。指示の全項目の消化○×を添える。
