# 実装カード: 便0-B 9回目（使った量を明細の表で数える・形の指示が届いた証拠 → 対照 → ログイン → 束 69 件）

- 設計: [design.md](design.md) 第2.10版（審査 APPROVE: [review-architect-v210.md](review-architect-v210.md)）§4 K9・§5「便0-B の最初の対照」（:124-130）。8回目の停止と確認: [bin0/out/opus-check-r8.md](bin0/out/opus-check-r8.md)・[bin0/out/measure-b-r8.md](bin0/out/measure-b-r8.md)。
- 8回目のカード [card-bin0b-r8.md](card-bin0b-r8.md) の手順 1・2・4・6〜10・12 は形を残して使う（下で「8回目の手順 N」と書く）。8回目の 3a・3b（固定設定と部屋の作り方）は枝に入っているので、やり直さない。
- 担当: クラウドの Sonnet。触ってよいのは `docs/handoff/ai-assistant/bin0/` の中だけ。製品コード・DB・本番・CI は触らない。
- 審査の軽い指摘 L1〜L4（review-architect-v210.md §5）は、手順 3a の 2・3a の 3・3c・5g に入れた。

## 守ること（全手順）

- 8回目のカードの「守ること」をそのまま守る。生の出力のファイル名は `r9-` で始める（例 `raw/r9-3-pytest.txt`）。8回目までの `raw/` のファイルは書き換えない。
- 明細の表から読むのは `task` ごとの `api_call_count` の合計と行の数、会話の行の数、墓標の行の数だけ。会話の文・題の文の列は読まない・出さない。state.db を容器の外へ写さない（design.md:126）。
- 形の指示の 1 文の正本は `bin0/run_bin0.py:44` の `SCHEMA_SYSTEM_LEAD` 1 か所。作り物の AI の中に同じ文を書き写さない（design.md:127）。

## やること（この順）

### 1. 作業場所

8回目の手順 1 と同じ。HEAD が origin/release/ai-assistant-bin0b と同じ番号（このカードの commit を含む）であることを確かめる。

### 2. Docker と完成品

8回目の手順 2 と同じ。`hermes --version` が `Hermes Agent v0.23.4` でなければ止まる。

### 3. 道具を直す（ログインの前に）

- (3a) `bin0/run_bin0.py` に足す・直す（どれも鍵と頼みの文を出さない）。
  1. **明細の表を読む** 関数 `read_usage(container, room, sid, mode)` を足す。台本が容器の外から `docker exec -u hermes <container> python3 -c <USAGE_INNER> <room> <sid> <mode>` を呼ぶ（`_docker()` を通す・試験で差し替えられる形）。部屋の名前と番号は引数で渡し、python の文の中に埋め込まない。部屋の名前は `ROOMS` にあるものだけ受ける。`USAGE_INNER` は定数 1 か所で、中身は次のとおり。
     - `sqlite3.connect("file:/opt/data/profiles/" + room + "/state.db?mode=ro", uri=True)` で読み取り専用で開く。
     - mode `usage`: `SELECT task, COALESCE(SUM(api_call_count),0), COUNT(*) FROM session_model_usage WHERE session_id=? GROUP BY task` の各行を `U\t<task>\t<合計>\t<行の数>` で出す。
     - mode `after`: `SELECT COUNT(*) FROM session_model_usage WHERE session_id=?` を `A\t<数>`、`SELECT COUNT(*) FROM sessions WHERE id=?` を `S\t<数>`、`SELECT COUNT(*) FROM state_meta WHERE key=?`（値は `'gateway.retired_session.v1.' + sid`）を `T\t<数>` で出す。
     - 最後に `END` を出す。開けない・SQL が失敗したら `ERR\t<例外の型の名前>` だけを出す（例外の文は出さない）。
     - 戻りは mode `usage` なら `{"main_sum": task 空の合計, "main_rows": task 空の行の数, "aux": {task: (合計, 行の数)}}`、mode `after` なら `{"usage_rows", "session_rows", "tombstone_rows"}`。`END` が無い・`ERR` がある・終了コードが 0 でなければ None。
  2. **K9 を表で決める**（design.md:88。今の `run_hermes_case` の 368-398 行目を直す）。`run_hermes_case` に引数 `container` を足す。使った会話ごとに、
     - **1 回目の読み**: 「`get_session` → `read_usage(usage)`」を 1 組とし、GET の `api_call_count` と表の `main_sum` が両方 1 以上になるまで 1 秒おきに最大 30 組読む。30 組の後に**片方でも** 0 か読めなければ、その会話は読めない（`-`）にする（L1）。
     - 使った会話を全部 1 回目の読みで読んだ後、会話ごとに **DELETE の直前にもう一度だけ** `read_usage(usage)` を読み（**最後の読み**）、その値で判定する（L2）。最後の読みが読めなければ読めない。
     - 会話ごとの判定（8回目の順を保つ: ずれ→0 が読めない→- より先）: 最後の読みの `main_sum` が 1 を超える・`aux` に 1 行でもある・GET の添えの確かめ（返事の usage の入力・出力＝会話の `input_tokens`・`output_tokens`、かつ `api_call_count == 1`）が合わない、のどれかなら ずれ。
     - 行の欄 `k9_ok` は、使った会話の全部で ずれ も 読めない も無ければ 1、ずれが 1 つでもあれば 0、それ以外で読めないがあれば `-`。
     - 行の欄を足す（HEADER の `k9_reasoning` の後ろ）: `k9_main_first`・`k9_main_last`（会話ごとの `main_sum` を `/` でつなぐ）・`k9_aux_first`・`k9_aux_last`（会話ごとの `aux` の行の数の合計を `/` でつなぐ）・`k9_reads`（会話ごとの 1 回目の読みの組の数を `/` でつなぐ）。読めないところは `-`。
     - 集計の行（今の 981 行目）はそのまま `k9=<1 の件数>/<件数> k9_unreadable=N` を出し、`k9_mismatch=N` を足す。
     - `--set main`・`--set k8` の hermes の道は `--container` を必須にする。無ければ標準エラーに出して終了コード 2。
  3. **対照の 1 回送り（probe）を直す**（今の 769-806 行目）。
     - 引数 `--wait-aux TASK` を足す。chat の行を待った後（今のまま）、「`get_session` → `read_usage(usage)`」を 1 秒おきに最大 30 組読む。終わる条件は、`--wait-aux` があれば `main_rows` が 1 以上かつ `aux` に TASK の行がある、無ければ GET の `api_call_count` と `main_sum` が両方 1 以上（③にも design.md:88 の読む順と時刻を使う・L4）。30 組で満たさなければ `probe=USAGE_TIMEOUT reads=30` を出し、DELETE して終了コード 7。
     - 出力に足す: `usage_main_sum`・`usage_main_rows`・`usage_aux=<task>:<合計>:<行の数>`（複数は `,`・無ければ `-`）・`usage_reads`・`usage_ok`。
     - `usage_ok` は、`--wait-aux TASK` のとき `main_sum == 1` かつ `aux` が TASK の 1 行だけで合計 1。無いとき `main_sum == 1` かつ `aux` が空。0 なら DELETE して終了コード 8（design.md:124・:129）。GET の `api_call_count` は記録するだけで `usage_ok` に使わない（design.md:124）。
     - `--container` があれば、送る前と後に `docker exec <container> grep -c "schema_lead=1" /tmp/fake.log` を読み、差を `fake_lead_lines=` で出す。引数 `--expect-lead 0|1` があり、差がその値と違えば DELETE して終了コード 9。
     - DELETE の後に `read_usage(after)` を読み、`after_usage_rows`・`after_session_rows`・`after_tombstone_rows` を 1 行で出す（合否に使わない・design.md:125）。
     - 終了コードの順: 5（chat が届かない・今のまま）→ 7 → 8 → 9。
  4. **形の指示の 1 文を書き出す** `--set fake-lead`: `SCHEMA_SYSTEM_LEAD` を `bin0/control/schema_lead.txt` に書く（改行なし・UTF-8）。標準エラーに `lead_chars=<文字数>` だけを出す（文は出さない）。`bin0/control/.gitignore` を新しく置き、中身は `schema_lead.txt` の 1 行（L3）。
  5. 8回目で足した 4 つ（opus-check-r8.md 2-c）は消さずに残す: `k9_ok` の順・詰め直しの後の起動待ち 180 秒で終了コード 6・probe の `--keys-file`・k7count の頼みの文のファイルが空で終了コード 2。
- (3b) `bin0/control/fake_ai.py` を直す（design.md:127）。
  - 起動のとき、環境変数 `FAKE_LEAD_FILE`（既定 `/fake/schema_lead.txt`）を読む。無い・読めない・空白だけなら `/tmp/fake.log` に `fake_ai=NO_LEAD` を 1 行書いて終了コード 1 で終わる。読めたら `fake_ai=START lead_chars=<文字数>` を 1 行書いてから待ち受ける。
  - chat の行に `schema_lead=<1/0>` を足す。受けた messages のどれか（content が配列なら text の部分を合わせたもの）にその 1 文が含まれれば 1。文そのものは書かない。
  - ほかの欄と返す usage（11/7）は変えない。
- (3c) `bin0/test_run_bin0.py` に足す・直す（今の 18 件と合わせて 24 件）:
  - 14 を直す: 表の `main_sum` 1・`aux` 空・GET が合えば `k9_ok=1`。最後の読みで `main_sum` 2 なら 0。最後の読みで `aux` に `title_generation` の 1 行が出たら 0 で、`k9_aux_first=0`・`k9_aux_last=1` が両方残る（L2）。
  - 19. `read_usage`: docker に渡す引数の並びが `exec -u hermes <container> python3 -c <USAGE_INNER> <room> <sid> <mode>` で、`USAGE_INNER` の文に番号が入らず、`mode=ro` を含む。`U`/`A`/`S`/`T`/`END` の出力を読める。`ERR` か `END` 無しなら None。`ROOMS` に無い部屋名は docker を呼ばずに None。
  - 20. 1 回目の読み: 3 組目で両方 1 になれば `k9_reads=3`。30 組とも表が 0 なら `-`。GET が 1・表が 0 のまま 30 組なら `-`（L1）。
  - 21. probe `--wait-aux title_generation`: `title_generation` の行が出るまで読み直す・出なければ終了コード 7・`main_sum` 2 なら終了コード 8・○の形なら 0。DELETE の後に `after_` の 3 つが出る。
  - 22. probe `--expect-lead 1` で `fake_lead_lines` が 0 なら終了コード 9。
  - 23. `--set fake-lead` で書いたファイルの中身が `SCHEMA_SYSTEM_LEAD` と同じ。標準出力・標準エラーにその文が出ない。
  - 24. fake_ai: `FAKE_LEAD_FILE` が無い・空なら終了コード 1 でログに `fake_ai=NO_LEAD`。ある時、その文を含む messages で `schema_lead=1`、含まない messages で `schema_lead=0`、ログにその文が出ない（fake_ai を import して関数を呼ぶ形でよい・待ち受けは立てない）。
  - 試験 9（出力に頼みの文が出ない）は、足した欄も含めて通ること。
- (3d) `bin0/README.md`: 16 行目の「18 件」を「24 件」に。6 番の台本の命令に `--container bin0-run` を足す。「便0-B で流す命令」の 11 番を「最初の対照は手順書 card-bin0b-r9.md の 5」に。
- (3e) 試験を流す（8回目の 3g と同じ命令）。**24 passed** でなければ直して流し直す（3 回まで）。生の出力は `out/raw/r9-3-pytest.txt`。

### 4. 頼みの文のファイル

8回目の手順 4 と同じ。同じ文が 2 行あれば 1 行にまとめる。見込みは **31 行**（8回目は 32 行から 1 つまとめて 31 行・opus-check-r8.md 2-d）。31 行でなければ止まる（`NEEDS_DECISION: 頼みの文の行数`）。件数だけを `raw/r9-4-texts.txt` に書く。

### 5. 最初の対照（作り物の AI・ログインなし・本物の束より前に 1 回・design.md §5）

8回目の 5 と同じ使い捨ての置き場（volume `bin0-ctl`）と容器（`bin0-ctl`）で行う。結果は `bin0/out/measure-b-r9.md` の表 C に「#／流した命令（鍵は伏せる）／返った数字・名前／○×」で書く。

- (5a) 8回目の 5a・5b と同じ（置き場を作る・固定設定 `/tmp/bin0-fixed-c1`（題づけ入り）と `/tmp/bin0-fixed-c3` を書き出す）。
- (5b) **完成品の中の確かめ**（design.md:126・:130）: `docker run --rm --network none --entrypoint sh <digest> -c '<下の命令>'` を 1 回流し、生を `raw/r9-5b-image.txt` に。
  - `find / -path /proc -prune -o \( -path '*/persistence/conversation/usage.py' -o -path '*/persistence/sqlite/conversation/_store/usage.py' -o -path '*/persistence/sqlite/_schema.py' \) -print`。それぞれ 1 つだけ見つからなければ止まる。
  - 見つけた最初の 2 つに `grep -n -E 'session_model_usage|record_auxiliary_usage'`。どちらかに 1 行も無ければ止まる。
  - `_schema.py` に `grep -n -E 'state_meta|session_model_usage'` と、`state_meta` を作る文の後ろ 4 行。`state_meta` の列に `key` が無ければ止まる（3a の 1 の墓標の数えがこの列名を使う）。
  - 止まるときは `NEEDS_DECISION: 完成品の中の確かめ`。
- (5c) `--set fake-lead` を流す（**`docker run` の前**。`/fake` は読み取り専用で付くので容器の中からは書けない・L3）。`lead_chars` を表 C に書く。
- (5d) 起動: 8回目の 5c と同じ形（`/tmp/bin0-fixed-c1`・`-v <repo>/docs/handoff/ai-assistant/bin0/control:/fake:ro`・`-p 127.0.0.1:8643:8642`）。`docker exec -d bin0-ctl python3 /fake/fake_ai.py` の後、1 秒おきに最長 10 秒、`docker exec bin0-ctl grep -c "fake_ai=START" /tmp/fake.log` が 1 になるまで待つ。ならない・`fake_ai=NO_LEAD` があれば止まる。`/health` が 200 になるまで確かめる。
- (5e) **python と読み取り専用の確かめ**（design.md:126）: `docker exec -u hermes bin0-ctl sh -c 'command -v python3'` の出力を表 C に。空なら止まる。続けて 3 部屋それぞれ、番号 `00000000-0000-0000-0000-000000000000` で `read_usage(after)` と同じ命令を 1 回流し、`END` が出て `A 0`・`S 0`・`T 0` なら ○。`ERR` なら止まる（`NEEDS_DECISION: 明細の表を開けない`）。生は `raw/r9-5e-ro.txt`。
- (5f) 対照①: `--set probe --base-url http://127.0.0.1:8643 --room invoice --model custom/fake-model --text こんにちは --container bin0-ctl --wait-fake-lines 2 --wait-aux title_generation`。○ の形: `fake_lines=2`・`usage_main_sum=1`・`usage_aux=title_generation:1:1`・`usage_ok=1`。GET の `api_call_count`（1 の見込み）・`usage_reads`・`fake_lead_lines`・`after_` の 3 つは表 C に記録するだけ。終了コードが 0 でなければ **止まる**（`NEEDS_DECISION: 対照①`）。生は `raw/r9-5f-probe-c1.txt`。
- (5g) 対照②: (5f) の出力の `sid_by_script=1`・`get_status=200`。404 なら **止まる**。
- (5h) 作り物の AI のログ: 止める前に `docker exec bin0-ctl cat /tmp/fake.log` を `raw/r9-5-fakelog-c1.txt` に。表 C に chat の行数・`model=` の値・`schema_lead=` の値・返事の `reply_model` を並べる。
- (5i) 対照③: `docker rm -f bin0-ctl` → `/tmp/fake.log` は容器と一緒に消える → 同じ置き場で `/tmp/bin0-fixed-c3` に替えて (5d) と同じ形で起こし直す（`schema_lead.txt` はそのまま残っている）→ `--set configcheck --container bin0-ctl`（24 行すべて ok。違えば **止まる**）→ coordinator・calendar・invoice の順に `--set probe … --container bin0-ctl --wait-fake-lines <前の行数+1> --expect-lead <0|1>`（coordinator は 0、calendar・invoice は 1）で 1 回ずつ。○ の形: 3 部屋とも終了コード 0（`usage_main_sum=1`・`usage_aux=-`・`usage_ok=1`・`fake_lead_lines` が思った値）・`get_status=200`・`api_call_count=1`。違えば **止まる**。ログを `raw/r9-5-fakelog-c3.txt` に。8回目の 5g と同じく `multiplex_profiles` の数を記録する（合否に使わない）。
- (5j) 対照の後片付け: 8回目の 5h と同じ。加えて `bin0/control/schema_lead.txt` を `rm` し、`git status --short bin0/control` に何も出ないことを確かめる。

### 6. 本物の置き場を作って起こす

8回目の手順 6 と同じ（6a〜6d）。

### 7. ログイン（PO が別の画面で打つ）

8回目の手順 7 と同じ。

### 8. 起点の数え（K7）

8回目の手順 8 と同じ。出力は `out/r9-k7-baseline.tsv`。

### 9. 束を流す

- (9a)〜(9d) 8回目の 9a〜9d と同じ。ただし `--set main`・`--set k8` に `--container bin0-run` を付け、ファイル名は `r9-`。
- (9e) 8回目の 9e と同じ。加えて、`k9_ok` が `-` の件が 1 件でもあれば、束は最後まで流す（K1〜K8 は K9 と別に測れる）が K9 は判定しない。表 4 の K9 は「読めない N 件・設計役に戻す」と書き、最後の返事は `NEEDS_DECISION: K9 読めない`。

### 10. 後始末と K7

8回目の手順 10 と同じ。ファイル名は `r9-`。

### 11. 結果の表

8回目の手順 11 と同じ形で `bin0/out/measure-b-r9.md` の表 4 に書く。K9 には次の 3 つを書く。
- 「対照は題づけだけで確かめた。表に書かれない後ろの処理（会話の番号が渡っていない糸・使った量の無い返事・stream の返事・moa）は、本物の束ではこの方法では見えない」（design.md:88）。
- 1 回目の読みと最後の読みの `aux` の行の数が違った件の数（L2）。
- `k9_reads` の最大。
K7 には「消した会話の番号は墓標（`state_meta` の 1 行）に残る。文は入らない」と、対照①の `after_` の 3 つの値を書く（design.md:125）。

### 12. 仕上げと後片付け

8回目の手順 12 と同じ。ただし題は `docs(ai-assistant): 便0-B 9回目 束 69 件の測り（Hermes の側）`。commit の前に `bin0/control/schema_lead.txt` が無いことを確かめる。

## 止まるとき・終わるとき

8回目のカードと同じ。報告のファイル名は `bin0/out/impl-report-b-r9.md`。最後の返事の 1 行は `DONE: <sha>` か、報告と同じ `BLOCKED:`・`NEEDS_DECISION:` の行。

END OF CARD
