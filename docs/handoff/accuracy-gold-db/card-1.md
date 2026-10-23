# card-1: 正解表の表 2 つと、投入・取り出しの道具（便1 実装）

状態: カード発行（Opus、2026-10-23）。根拠: design.md（方針 PO 2026-10-23「1」、方式は Opus 委任）、ADR-1043、recon.md。
担当: Sonnet。触ってよいのは下の「触るファイル」だけ。本番 DB・VPS・GitHub secret には触らない。正解表の実物（~/CC報告ファイル-keep/accuracy-gold-20261020/）は**読まない・開かない**（試験は作った値だけで行う）。

## 0. 実装前点検（結果を報告に書く。外れたら実装せず BLOCKED で止まる）
- P1 アプリが本番 DB に接続する役割名と、それが superuser でないこと。読む場所: docker-compose.yml の backend の DATABASE_URL の組み立て、backend/app の DB 接続設定、migrations の役割作成。値（パスワード等）は表示しない。superuser なら BLOCKED（design §12）。
- P2 scripts/accuracy/test_score_v102.py の走らせ方（CI の workflow に出てくるか、出てくるならどのコマンドか）。出てこないなら、どう走らせたかを報告に書く。
- P3 `scripts/run_all_migrations.sh` の最後の `run_sql migrations/` 行が :1132 の `20261022_110000_product_formats_drop_type_master_id.sql` のままか。違えば最後の行の後に足す。
- P4 `migrations/` に 20261023_180000 より後の名前が無いこと。あれば BLOCKED。

## 1. 触るファイル
1. migrations/20261023_180000_create_accuracy_gold.sql（新規）
2. scripts/run_all_migrations.sh（run_sql を 1 行）
3. scripts/accuracy/gold_to_sql.py（新規）
4. scripts/accuracy/fetch_gold.py（新規）
5. scripts/accuracy/test_gold_to_sql.py・scripts/accuracy/test_fetch_gold.py（新規）
6. scripts/accuracy/README.md（節を 1 つ追加）
7. docs/handoff/accuracy-gold-db/（このカード・design.md・recon.md。中身は変えない）、docs/adr/ADR-1043-accuracy-gold-in-db.md、docs/adr/README.md（`node scripts/generate-adr-index.js` で再生成）
8. .claude-pipeline/active-work.d/release-accuracy-gold-db.md
触らない: scripts/accuracy/score_v102.py・test_score_v102.py、backend/、frontend/、migrations の既存ファイル、窓口（ADR-1042）の全ファイル。

## 2. 変更の中身
### 2-1. migration
design.md §3-1 のとおり。書き方は migrations/20261018_100000_create_product_packagings.sql を手本にする。
- 1 行目: `-- ADR-1043 便1: 精度測定の正解表。空の表を作るだけ。値は書かない（ADR-1007）。冪等。`
- 2 行目: `-- ロールバック: docs/handoff/accuracy-gold-db/design.md §7（表ごと消す文はそこに書く。不可逆のため PO 確認）`
  - 2026-10-23 Opus 変更: 初版は消す文そのものをこの行に書く指示だったが、担当の作成コマンドが不可逆操作の見張りに止められた（BLOCKED）。コメントの文面のために許可を出すのは不釣り合いなので、戻し方の正本を design.md §7 の 1 か所にし、migration からは参照だけにする。
- versions を先に作る。CHECK: `gold_version ~ '^[a-z0-9_]+$'`、`file_sha256 ~ '^[0-9a-f]{64}$'`、`row_count > 0`、`post_count > 0`。
- rows: 列の順は design §3-1 の並び。制約名は `accuracy_gold_rows_version_row_key UNIQUE (gold_version, row_no)`。索引 `CREATE INDEX IF NOT EXISTS accuracy_gold_rows_version_post_idx ON public.accuracy_gold_rows (gold_version, post_id);`
- 列名・制約名・索引名に `hash`・`token`・`secret`・`password`・`credential` を含めない。
- RLS は両表とも ENABLE＋FORCE、ポリシーは 1 つずつ: `<表名>_operator FOR ALL USING (current_setting('app.is_operator', true) = 'true') WITH CHECK (同じ)`。SELECT を true にするポリシーは**作らない**（product_packagings と違う点）。各 `DROP POLICY IF EXISTS` を前に置く。
- COMMENT ON TABLE を両表に（ADR-1043 と 1 行の意味）。

### 2-2. gold_to_sql.py
design §3-2 のとおり。標準ライブラリのみ。`python3 scripts/accuracy/gold_to_sql.py --gold G --version V --note N --out-dir D`。
- 期待する見出し（この順・この字）: `投稿id price_line lines 許容する行 E2_price E3_quantity A1_product_id A2_condition A3_unit A4_status A5_ship A4根拠 迷い 除外 裁定根拠 PO確認`。DB 列との対応は design §3-1 の並び順どおり（post_id … po_check）。
- 点検のどれかが外れたら、ファイルを 1 つも書かず、理由を標準エラーに 1 行出して終了コード 2。理由の文に値そのものを入れない（何行目・何列目だけ）。
- `--out-dir` が `git rev-parse --show-toplevel`（実行時のカレントで取れたとき）の中、または gold_to_sql.py のあるリポジトリの中なら止める。
- sha256 は入力ファイルのバイト列そのもの。row_count はデータ行数、post_count は投稿id の種類数。
- 出力 3 本（01〜03）は design §3-2。戻し用のファイルは作らない（2026-10-23 Opus 変更。理由は design §3-2）。02 は bin2/02_apply.sql の冒頭（`\set ON_ERROR_STOP on`・`\if :{?end}`）を写す。INSERT は 1 文に多数の VALUES でよい（500 行ずつ区切る）。件数の点検は `SELECT CASE WHEN count(*) = <N> THEN 1 ELSE 1 / 0 END FROM public.accuracy_gold_rows WHERE gold_version = '<V>';` の形。
- 01 の存在確認: 投稿id は `VALUES` の一覧と `public.source_messages.id` を突き合わせ、無い数を `MISSING_POSTS <数>` と出し、0 でなければ 1/0。a1_product_id は数字だけのものを `public.products.id` と突き合わせ、`MISSING_PRODUCTS <数>`、0 でなければ 1/0。版が既にあれば 1/0。
- 標準出力には書いたファイルのパス・sha256・行数・投稿数だけ。

### 2-3. fetch_gold.py
design §3-4 のとおり。`python3 scripts/accuracy/fetch_gold.py --version V --out F [--url U]`。
- urllib.request で POST、本文は SQL（UTF-8）、Content-Type `text/plain; charset=utf-8`、タイムアウト 90 秒。環境変数 `READ_WINDOW_TOKEN` があるときだけヘッダ `X-Read-Window-Token` を付ける。鍵は表示もログもしない。
- 版の行の応答は見出し行＋1 行であること。0 行なら「版がありません」で終了 1。
- 取り出した本文は `bytes` のまま sha256 を取り、版の file_sha256 と比べる。行数（LF の数 − 1）も row_count と比べる。違えば `--out` を書かずに終了 1（既にあるファイルは消さない・上書きしない）。一致したら書いて `sha256=<先頭12字> rows=<N>` を表示。
- HTTP がエラー、または `X-Read-Window-Rc` が 0 でないときは、HTTP の番号と rc と応答本文の 1 行目（200 字まで）を出して終了 1。
- 送る SQL を作る関数を分け、試験から呼べるようにする。

### 2-4. 試験
- test_gold_to_sql.py: 一時フォルダに作った 3 行の偽の正解表（uuid は uuid4 で作る）で、出力 3 本ができ、それ以外のファイルができないこと・02 に `\set ON_ERROR_STOP on` と `:end` があること・`'` を含む値が `''` になること。止まる条件それぞれ（見出し違い・列数違い・タブ/`\`/`"` 入り・uuid でない・版名違反・出力先がリポジトリ内）で終了 2 かつファイル 0。
- test_fetch_gold.py: http.server を一時ポートで立て、見出し＋行を返す偽の窓口で、sha256 一致→ファイルが元と同じバイト列、不一致→ファイルを書かない、rc≠0→終了 1。送る SQL に readonly_query.py の `_WRITE_RE` の語が無いこと（backend/app/ops/readonly_query.py の `_WRITE_RE` を import して当てる。import できない置き方なら同じ正規表現を写して出典の行番号をコメントに書く）、先頭行が `-- limit=5000` であること。
- 走らせ方は P2 で見つけた方法に合わせる。

### 2-5. README.md
`## クラウドで測る（ADR-1043）` の節を足す: 1 行目 `python3 scripts/accuracy/fetch_gold.py --version gold_v1 --out /tmp/gold_v1.tsv`、2 行目 score_v102 の既存の例の `--gold` をそのファイルにしたもの、止まったときの読み方（sha256 が違う＝取り出しが壊れた／版が無い＝投入前）。投入は Opus が行うことを 1 行。

## 3. 確かめてから報告すること
- 新しい試験と既存の test_score_v102.py が全部通る（生出力をファイルに保存してパスを書く）。
- `git diff origin/main...HEAD --name-only` が §1 の範囲だけ。
- 差分に `.tsv`・`.sql` の投入ファイルが無い（migration を除く）。
- `node scripts/generate-adr-index.js` 実行後の差分。
- commit・push・PR 起票は shingo-cc 名義で、PR は `--draft`、本文に `### 標準ワークフロー確認` と触るファイル全部。マージはしない。

## 4. 想定される分岐
- P1 で superuser だった → 実装せず BLOCKED（K5 が成り立たない）。
- P2 で CI に scripts/accuracy の試験が無い → 手元で `python3 -m unittest` 等で走らせ、その方法を報告。CI の変更はしない。
- 試験で偽の窓口が立てられない（ポート使用不可等）→ 送る関数を差し替える形の試験にし、そう報告。
- 迷ったら止まって NEEDS_DECISION で Opus に戻す。

## 5. 追補（2026-10-23 Opus、CI の結果を受けて）
CI（HEAD 2bd54e601）で次の 3 つが落ちた。生ログ: /tmp/CC報告ファイル/accuracy-gold-db-impl/fail-*.txt
- `migration-guard`（チェック4）: `REFERENCES public.accuracy_gold_versions` の参照先が `.github/workflows/migration-guard.yml` の `PUBLIC_TABLES` に無い。→ 同ファイルの `PUBLIC_TABLES` の末尾に ` accuracy_gold_versions accuracy_gold_rows` を足す（前例 5249aad99「public 表リストに誤り報告の表3つを追加」）。触るファイルにこの 1 ファイルを加える。この行以外は変えない。
- `guard-authoring/evaluation` が error: `scripts/run-guard-evaluation.js:24-25` の `merge-base --is-ancestor base head` が外れる（ブランチが古い main 起点）。→ `git merge origin/main`（merge commit。rebase・force push はしない）。衝突したら止まって NEEDS_DECISION。
- `process-artifacts gate`: PR 本文の `### GO記録` が無い。→ GO 発行時に Opus が書く。担当は触らない。
