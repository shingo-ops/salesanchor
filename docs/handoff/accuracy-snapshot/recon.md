# 写し(snapshot)を本番から作る道具の recon（読み取りのみ・2026-10-24）
根拠は origin/main（git fetch 後）。生出力: raw-*（同フォルダ）。投稿本文・id実値は書かない。

## 1. score_v102.py の写しの読み方
【事実】
- SNAP_COLS は14列: extraction_item_id, line_start, line_end, source_lines, raw_price, raw_quantity, product_id, condition_canonical, unit_canonical, status, ship_ja, price_normalized, quantity_normalized, exclusion（scripts/accuracy/score_v102.py:18-21）。
- ファイル名は `<投稿id>.tsv`。.tsv だけを sorted で読み、投稿id=ファイル名から ".tsv" を除いたもの（:344-347）。
- 形式: UTF-8・タブ区切り・1行目が見出し。必要列が1つでも無ければ Stop（read_tsv :31-47）。余分な列は読み捨て、列の並び順は不問（見出し名で引く）。空行は飛ばす。列が足りない行は空文字。
- 型: 全部文字列。空値は空文字（NULL と区別しない）。
- 行の絞り込み: 「全行を使う（is_current では絞らない）」（:347）。行の並びは score 側で決める（:119-140）ので不問。
- 投稿のファイルが無い→nocur 扱い（:204-210）。見出しも無い空ファイルは Stop（:36-37）。

## 2. 手元の写しの作り方（実物）
【事実】
- 実物: ~/CC報告ファイル-keep/accuracy-gold-20261020/sample/fetch.sh（コピー raw-fetch.sh）。投稿ごとに SQL を /tmp/q.sh へ流し、AUDIT 等の行を grep -v で除いて snapshot/<id>.tsv に保存。
- SQL 全文: raw-snapshot-select.sql.txt。表 = ai_ro.public__extraction_jobs j JOIN public__extraction_items i (i.extraction_job_id=j.id) JOIN public__analysis_results ar (ar.extraction_item_id=i.id)。
- 絞り込み: j.source_message_id=投稿id かつ ar.engine_version='v102-f_ct' のみ。is_current・tenant・削除除外の条件は無し（手元実測 is_current: True 345 / False 1147）。
- 並び: order by i.line_start, i.gemini_index, ar.computed_at, ar.id。出力は49列（score が使う14列を含む）。
- 対象投稿の決め方: pop.sql / select.sql（raw-pop.sql / raw-select.sql）。受信 2026-10-13〜10-20(UTC) で v102-f_ct の結果がある投稿から、予約語あり40・なし60 を md5(id||'20261020') 順に選ぶ（供給元ごと10件まで）。結果が sample_list.tsv。
- 手元100本: データ行合計 1492（見出し込み 1592）、695,729 バイト、約466バイト/行。1投稿内の extraction_item_id 重複なし（実測）。
【未確認】再解析が走ると同じSQLでも別の写しになる（時点は engine_version 一致でしか固定されない）。

## 3. ai_ro のビューで書けるか
【事実】
- この SQL は既に ai_ro.public__* だけで書かれている。4表 public__extraction_jobs / extraction_items / analysis_results / source_messages は A-ai_ro-tables.txt の 26/25/7/73 行目にある。
- 拒否正規表現（migrations/20261017_130100_create_ai_ro_views.sql:23）= ^password|_encrypted$|_secret|_token|hash|^secret|^api_key|private_key|credential。写しの49列名は全て非該当（実測0）。窓口も出力の列名（別名含む）に同じ正規表現を掛け、当たると値を <redacted> にする（readonly_query.py:42,298,324）。別名に hash/_token 等を入れないこと。
【未確認】public__accuracy_gold_rows のビューの存在（A-ai_ro-tables.txt は金表追加前の取得。ただし fetch_gold.py:42,54 が ai_ro.public__accuracy_gold_* を前提にしている）。

## 4. 窓口の制約
【事実】
- POST /api/v1/ops/read-window/query、本文=SQL（text/plain）、ヘッダ X-Read-Window-Token（read_window_http.py:28,61-65,87）。
- SQL は1文のみ（readonly_query.py:112-150）。先頭語は select/with/show/explain（:44,153）。WITH・JOIN・IN(...)・サブクエリ可。パラメータ渡しは無く、SQL文字列に値を埋める（投稿idは UUID 形式を検証してから埋める）。
- 禁止語: set_config( / \bset\s / copy / pg_read_file / pg_sleep / lo_ と、書き込み系の語（:45-55,160。文字列リテラル内も対象）。updated_at・extracted_at 等は単語境界で当たらない。
- 上限: SQL 64KB（:29、http 413）、行数 既定200・最大5000（先頭行 `-- limit=N` :30-31,56,165-173）、1値 10240 文字で切り詰め（:32,178-180）、実行 60秒（:33,292）、同時1本・2本目は429（http:31,71-72）、クライアント待ち TIMEOUT=90秒（fetch_gold.py:23）。
- 応答: 成功は 200・text/tab-separated-values・ヘッダ X-Read-Window-Rc: 0（http:78-79）。1行目が見出し。型情報なし（全て文字列、NULL=空文字）。値の \ タブ 改行 CR は `\\` `\t` `\n` `\r` に置換（:176-182）。拒否/DBエラーは 400（rc 2/4）、AUDIT 不可は 503。
- 注意【事実】: この置換は score_v102.py の read_tsv で元に戻されない（csv で読むだけ :32-46）。値に改行や \ を含む列は手元の写しとの差になりうる。【未確認】手元の写しを作った /tmp/q.sh が同じ置換を掛けたか、score が使う14列で実際に該当する値があるか。
- 流用できる fetch_gold.py の部品: post(url, sql, token) (:58-70, 戻り=(HTTP番号, rc, 本文bytes))、fail_http (:77)、first_line (:73)、DEFAULT_URL/TIMEOUT/ROW_LIMIT (:22-25)、`-- limit=` 付きSQLの組み立て型 (rows_sql :46-55)、sha256＋行数の突き合わせ (:129-134)。標準ライブラリのみ。

## 5. 100投稿ぶんの量と分割
【事実】手元100本=1492行・695,729バイト。窓口上限（5000行・SQL 64KB・60秒）に対し、全体を1回（IN句に UUID100個≒3.7KB、`-- limit=5000`）で取れる計算。
推奨: 余裕を見て 25投稿/回×4回（1回約370行・約170KB）、窓口は同時1本なので直列。列を score が使う14列＋監査用数列に絞れば応答は約1/3。
注意【事実】: 行数上限超過の打ち切り通知は stderr のみで HTTP 本文に出ない（readonly_query.py:302、http は err の rejected:/db error: 行しか返さない :41-44,78-84）。取りこぼしに気付けないため、回ごとに「返った行数 < limit」を検査する。
【未確認】Cloudflare/プロキシ側の応答サイズ上限。

## 6. 対象投稿を正解表から決められるか
【事実】
- public.accuracy_gold_rows(gold_version, row_no, post_id UUID, …)、索引 (gold_version, post_id)（migrations/20261023_180000_create_accuracy_gold.sql:18-42）。版の記録 accuracy_gold_versions に post_count あり（:4-16）。
- 手元の gold_v1 は 1494 行・100 投稿（実測）で、写しの100本と数が一致。
- `select distinct post_id::text from ai_ro.public__accuracy_gold_rows where gold_version='gold_v1' order by 1` で一覧を取れる。または1本のSQL内に `j.source_message_id in (select post_id ...)` として組み込める（【未確認】source_messages.id / extraction_jobs.source_message_id の型が uuid か。型違いなら ::text で揃える）。
- 設計案: fetch_snapshot.py は --gold-version を取り、正解表の post_id 集合 = 写しを作る投稿集合とする。取得できた投稿数・行数を gold の post_count と突き合わせ、0行の投稿は報告する。

## 設計への示唆（実装はしない）
- 投稿ごとに snapshot/<post_id>.tsv へ書き分け。0行の投稿はファイルを作らない（見出しだけのファイルは問題ないが、空ファイルは Stop）。
- 取得時刻・engine_version・投稿数・行数を記録に残す（時点固定のため）。
