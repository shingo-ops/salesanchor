# 答え合わせ表（正解表）を本番 DB に置く: 現状調査

状態: 調査済み（Opus＋Sonnet、2026-10-23）。根拠は origin/main 5cb04e081（git fetch 後）。
生の調査記録（リポジトリ外）: `/tmp/CC報告ファイル/cloud-gold-db-recon-20261023/recon.md`、`/tmp/CC報告ファイル/cloud-stage34-recon-20261023/recon.md`。
正解表の実物は `~/CC報告ファイル-keep/accuracy-gold-20261020/gold/gold_v1.tsv`（社外秘。値はこの文書に書かない。数えた件数だけ書く）。

## 0. 既存 ADR の検索
- `git grep -i -E 'accuracy|正答率|gold' docs/adr/` で本文に当たるのは ADR-154 のみ（TCG 移行の別件）。精度測定の正解表を扱う ADR は無い。
- 関連: ADR-1042（クラウドから本番を読む窓口）、ADR-1024（AI の本番読み取りの道・ai_ro）、ADR-1007（migration に値を書かない）、ADR-1037（入れ替え時のロック待ち）、ADR-1003（GO 委任）。

## 1. 正解表の形（Opus が 2026-10-23 に数えた）
- 288096 バイト、改行 1495 個（見出し 1 行＋データ 1494 行）、末尾は改行。sha256 の先頭 12 字 `b77fa1059994`（`gold_v1.sha256` と一致）。
- 全行 16 列。値の中の `"`・`\`・CR は 0 個。前後に空白のある値 0 個。最長の値 200 字。
- 投稿id は 1494 行すべて 36 字の小文字 uuid 形。100 種。投稿id = source_messages.id（調査記録 §1）。
- **(投稿id, price_line) は一意ではない**。1 つの組が 3 行ある（データ行 803〜805。lines は 3 行とも同じで、ほかの列が違う）。採点は行の順番で区別している（`scripts/accuracy/score_v102.py:119` `order = sorted(range(len(golds)), key=lambda i: (pline_num(golds[i]), i))`）。→ DB では行の順番（row_no）を持ち、一意の鍵は (版, row_no) にする。
- tenant を表す列は無い。母集団は public の source_messages / analysis_results（調査記録 §1）。

## 2. 採点の読み方
- `scripts/accuracy/score_v102.py:15-16` GOLD_COLS は 12 列を列名で読む。`:31-45` read_tsv は csv.reader（区切りはタブ）。`:336` 引数 `--gold`、`:342` 読み込み、`:354-357` 入力ファイルの sha256 を inputs.sha256 に記録。標準ライブラリのみで DB に接続しない（`scripts/accuracy/README.md:3`）。
- 読まない 4 列: A4根拠・迷い・裁定根拠・PO確認。

## 3. ai_ro（AI が読むためのビュー）
- `migrations/20261017_130100_create_ai_ro_views.sql:25-33` public と tenant_% の全表を自動で写す。`:23` の正規表現 `^password|_encrypted$|_secret|_token|hash|^secret|^api_key|private_key|credential` に当たる列は落ちる。ビュー名は `<スキーマ>__<表名>`（:52）。持ち主は superuser で RLS を受けない。
- `scripts/run_all_migrations.sh:185` で先頭に消し、`:192-215` の EXIT trap で毎回作り直す。→ public に表を作れば、次のデプロイで `ai_ro.public__<表名>` が自動で出る。

## 4. 窓口（ADR-1042）の出力
- `backend/app/ops/readonly_query.py:30-32` 既定 200 行・上限 5000 行（`-- limit=N` の行で指定、:56）、値 1 つ 10240 字まで。
- `:176-182` `_escape`: None は空文字、`\`・タブ・LF・CR は `\\`・`\t`・`\n`・`\r` に置き換える。
- `:322-325` 1 行目は列名（別名）、以降は値をタブでつなぎ、行ごとに LF。
- `:55` 文の中に insert/update/delete/truncate/drop/alter/create/grant の語があると拒否。`:42` 出力列名が拒否語に当たると `<redacted>`。
- → 正解表は `"`・`\`・CR・タブ・改行を値に含まないので、行の順に並べ、列の別名を元の見出しにすれば、**窓口の応答はファイルと 1 バイトも違わない形になる**（K3 で実測する）。

## 5. migration とデータ投入の決まり
- 命名 YYYYMMDD_HHMMSS_*.sql。最新は `migrations/20261022_110000_product_formats_drop_type_master_id.sql`。登録は `scripts/run_all_migrations.sh:1132` の後に `run_sql` を 1 行。
- 共用表の RLS の前例: `migrations/20261018_100000_create_product_packagings.sql:69-81`（ENABLE＋FORCE、書き込みは `current_setting('app.is_operator', true) = 'true'` のときだけ）。先頭にロールバックのコメント、`CREATE TABLE IF NOT EXISTS` で冪等。
- 値の投入の前例: `docs/handoff/condition-unit-booklet/data/bin2/`（01_precheck → 02_apply を `-v end=ROLLBACK` で試し → `-v end=COMMIT` → 03_verify、件数が違えば `SELECT 1 / 0`）。`bin2/README.md:3`「本番に流すのは Opus（担当は流さない）」。

## 6. 未確認
- [?] アプリが本番 DB に接続するときの役割名と、それが superuser でないこと（superuser なら RLS を受けないので K5 が成り立たない）。→ カードの実装前点検で Sonnet が確かめる。
- [?] scripts/accuracy/test_score_v102.py が CI で走っているか、走らせ方。→ 同上。
