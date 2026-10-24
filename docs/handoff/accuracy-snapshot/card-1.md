# カード 便1: fetch_snapshot.py を足す（Sonnet 実装用）

設計: docs/handoff/accuracy-snapshot/design.md（§3 が仕様の正）

## 触るファイル（これ以外は触らない）
1. 新規 scripts/accuracy/fetch_snapshot.py
2. 新規 scripts/accuracy/test_fetch_snapshot.py
3. scripts/accuracy/README.md に節「写しを窓口から作る（fetch_snapshot.py）」を追記（使い方 1 行、出力先はリポジトリの外、写しは社外秘、共有しない、停止の条件の一覧）
4. docs/handoff/accuracy-snapshot/ の design.md・recon.md・card-1.md（Opus が渡したものをそのまま置く）
5. .claude-pipeline/active-work.d/release-accuracy-snapshot-fetch.md（公式の書式）

触らない: score_v102.py、fetch_gold.py、gold_to_sql.py、migrations、.github、backend、frontend

## 実装の決まり
- 標準ライブラリのみ。fetch_gold.py の `post`・`fail_http`・`DEFAULT_URL`・`ROW_LIMIT` は importlib で fetch_gold.py を読み込んで使う（fetch_gold.py が gold_to_sql.py を読む方法 fetch_gold.py:29-34 と同じ型）。コピーしない
- SNAP_COLS は score_v102.py から同じ方法で読み込む（列の正は 1 か所）
- 引数: `--gold-version`（必須、`^[a-z0-9_]+$`）、`--out-dir`（必須）、`--engine`（既定 `v102-f_ct`、`^[A-Za-z0-9_.-]+$`）、`--url`（既定 DEFAULT_URL）、`--batch`（既定 25）
- 関数に分ける（試験しやすく）: `posts_sql(version)`、`count_sql(version)`（post_count を取る）、`snapshot_sql(post_ids, engine)`、`parse_snapshot(body, limit)`（停止条件の検査をして {投稿id: [行]} を返す。違反は ValueError、メッセージに値を入れない）、`main(argv)`
- 問い合わせの先頭行は `-- limit=5000`。列は `i.id as extraction_item_id` 等 14 列＋`j.source_message_id::text as post_id`。表は ai_ro.public__extraction_jobs j / public__extraction_items i / public__analysis_results ar（R §2 の SQL と同じ結合）
- 別名に hash・_token・secret 等を使わない（窓口が値を伏せる、R §3）
- 投稿id は UUID の正規表現で全部検証してから SQL に入れる
- 書く順: 全バッチを読んで検査が全部通ってから書く。DIR に .tsv が 1 つでもあれば最初に停止
- 各ファイルの中身: 1 行目＝SNAP_COLS をタブでつないだもの、2 行目以降＝窓口の本文の該当行から post_id 列を除いたもの（値は変えない）。改行は `\n`
- 画面に投稿id・値・鍵を出さない。最後の 1 行は設計 §3-5 の形

## 試験（test_fetch_snapshot.py、post を偽物に差し替え）
- 正常: 2 バッチ（batch=2、投稿 3 本、うち 1 本は 0 行）→ ファイル 2 個、中身の見出しと行が期待どおり、最後の行の数字
- 停止（それぞれ終了コード 1・.tsv 0 個）: HTTP 400／rc≠0／見出し違い／行数＝limit／値に `\`／値が 10240 文字／post_count と一覧の数が違う／DIR に既存の .tsv／投稿id が UUID でない
- SQL: `snapshot_sql` に `j.source_message_id in (` があり `::text in` が無い、`engine_version = 'v102-f_ct'`、`order by` が設計どおり

## 完了の報告
- `python3 -m pytest scripts/accuracy -q` の生出力をファイルに保存しパスを返す
- commit・push・PR 起票（テンプレ起点、`### 標準ワークフロー確認` 欄、触る/削除するファイル全列挙、pr-body-guard は worktree から実行、gh は shingo-cc 名義）。マージはしない
- 最後の行は DONE / BLOCKED: / NEEDS_DECISION:

## 想定分岐
- fetch_gold.py の読み込みで、fetch_gold.py がさらに gold_to_sql.py を読むため HERE の扱いがずれる → fetch_gold.py の HERE は自分の場所なので問題ないはず。ずれたら BLOCKED で止める
- 既存の pytest が手元で落ちる（Python 3.14 の SSL 等）→ 自分の変更と無関係なら生出力付きで報告し、直さない
- pr-body-guard・review-gate などフックに止められたら、言い換えて回避せず BLOCKED で報告
