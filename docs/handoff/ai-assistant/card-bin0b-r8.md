# 実装カード: 便0-B 8回目（固定設定・形の指示・使った量・残らないの数え直し → ログイン → 束 69 件）

- 設計: [design.md](design.md) 第2.8版（審査 APPROVE: [review-architect-v28.md](review-architect-v28.md)）§4・§5。7回目の結果: [bin0/out/impl-report-b.md](bin0/out/impl-report-b.md)・[bin0/out/measure-b-20261125.md](bin0/out/measure-b-20261125.md)。
- 前のカード [card-bin0b.md](card-bin0b.md) の手順 1・2・4・6・8・10 は形を残して使う（下で「前のカードの手順 N」と書く）。
- 担当: クラウドの Sonnet。触ってよいのは `docs/handoff/ai-assistant/bin0/` の中だけ。製品コード・DB・本番・CI は触らない。
- 審査の軽い指摘 L1〜L5（review-architect-v28.md）は、この下の手順 3c・3d・5・5f・5g に入れた。

## 守ること（全手順）

- 前のカードの「守ること」3 つをそのまま守る（鍵は `/tmp/bin0-secrets/` だけ・頼みの文と答えの中身を出さない・digest 固定・事実には完成品の中の場所:行・生の出力は `bin0/out/raw/` に 1 手順 1 ファイル 200 行まで・ログインの札の中身を出さない・69 件の間に同じ容器で別の頼みを流さない）。
- 生の出力のファイル名は `r8-` で始める（例 `raw/r8-3-pytest.txt`）。7回目までの `raw/` のファイルは書き換えない。
- 同じ設定を 2 か所に書かない。8 つの鍵の正本は `bin0/config.yaml` の 1 つ。使い捨ての置き場に書き出す固定設定は、台本が正本から作る（手で写さない）。

## やること（この順）

### 1. 作業場所

前のカードの手順 1 と同じ（1a〜1d）。

### 2. Docker と完成品

前のカードの手順 2 と同じ。`hermes --version` が `Hermes Agent v0.23.4` でなければ止まる。

### 3. 道具を直す（ログインの前に）

- (3a) `bin0/config.yaml` を管理者の固定設定の形に書き換える（design.md §5「置き場」）。
  - 3 行目の注記を `# 管理者の固定設定。/etc/hermes/config.yaml に読み取り専用で置く（起動に -v <置き場>:/etc/hermes:ro）。部屋の config と /opt/data/config.yaml にはこの鍵を書かない。` に替える。
  - 鍵は次の 8 つ。今ある 6 つは値も注記もそのまま。足すのは 2 つ。
    - `logging.level: WARNING`（注記 `# 頼みの先頭 80 字を書く行は INFO（agent/turn_context.py:1290）。WARNING で agent.log の目印 0 行（out/source-check-b4.md）`）
    - `auxiliary.title_generation.enabled: false`（`auxiliary:` の下、`background_review` の次。注記 `# 新しい会話の最初の送信ごとに題づけの AI 呼び出しが 1 回増える（out/source-check-b5.md Q13）`）
  - 23 行目の `# 未確認: …S8…` は `# 7回目の F5 で、存在しない頭を送っても別の会社に切り替わらないことを確かめた（out/measure-b-20261125.md 表 3）` に替える。
- (3b) `bin0/setup_profiles.sh`:
  - 26 行目（部屋の config.yaml への写し）と 35 行目（/opt/data/config.yaml への写し）を消す。27〜32 行目（部屋の .env の鍵）は 1 文字も変えない。
  - 33 行目の echo の後ろに、部屋の config.yaml に 8 つの鍵の名前（最後の部分: `level`・`memory_enabled`・`user_profile_enabled`・`api_server`・`background_review`・`title_generation`・`fallback_providers`・`multiplex_profiles`）が出る行数を `cfg_key_lines=N` で足す（`grep -c -E` で数だけ。中身は出さない）。
- (3c) `bin0/run_bin0.py` に足す・直す（どれも鍵と頼みの文を出さない）。依存は `pyyaml==6.0.2` を 1 つ足す（README 6 番の `uv run` に `--with pyyaml==6.0.2`）。
  1. **固定設定を書き出す** `--set fixed-config --out DIR [--test-model FILE] [--title-on]`: 正本 `bin0/config.yaml` を読み、8 つの鍵が全部あるかを確かめる。1 つでも無ければ、無い鍵の名前を標準エラーに出して終了コード 2（L1）。あれば `DIR/config.yaml` に書く。`--test-model` を渡したときだけ、そのファイルの `model:` の塊を足す。`--title-on` のときだけ `auxiliary.title_generation.enabled` を true にする。正本のファイルは書き換えない。標準エラーに `keys=8 test_model=0|1 title_on=0|1` を出す。
  2. **形の指示**: 定数 `SCHEMA_SYSTEM_LEAD = "出力は次の JSON Schema に合う JSON 1 つだけ。"` を 1 か所に置く。係の部屋（calendar・invoice）に送るたび、`secretary-agent/schema.json` をそのつど読んだ全文を `SCHEMA_SYSTEM_LEAD + "\n\n" + 全文` にして、messages の**先頭**に `{"role": "system", ...}` で足す（今の 106 行目の messages は `[user]` だけ）。まとめ役には付けない。`chat()` に引数 `system: str | None = None` を足し、`None` のときは今と同じ本文にする。
  3. **消す前に使った量を読む（K9）** `get_session(client, room, key, sid)`: `GET /p/<部屋>/api/sessions/<番号>`。戻りは状態の数字と、`session` の中の `input_tokens`・`output_tokens`・`api_call_count`・`cache_read_tokens`・`reasoning_tokens`（無い欄は None）。`run_hermes_case` の最後で、使った会話ごとに **DELETE の前に** 読む。行の欄を足す: `get_status`（使った会話の状態の数字を `/` でつなぐ）・`api_calls`（会話ごとの `api_call_count` を `/` でつなぐ）・`k9_ok`（使った会話の全部で「返事の usage の入力・出力＝会話の input_tokens・output_tokens」かつ `api_call_count == 1` なら 1、1 つでも違えば 0、読めなければ `-`）・`k9_cache`・`k9_reasoning`（会話の値の合計）。最後の集計に `k9=<1 の件数>/<件数>` と `k9_unreadable=N` を足す。
  4. **消す口の答えを分ける**: `delete_session` は 200 だけを「消せた」とし、404 は別に数える（今の 136 行目は 404 も消せたにしている）。行の欄 `deleted` は 200 の数、新しい欄 `deleted_404` は 404 の数。集計は `deleted=<200>/<使った数> deleted_404=N`。
  5. **残らないの数え（K7）** `--set k7count --label LABEL --volume VOL --texts FILE`: 台本が容器の外から `docker run --rm --network none --entrypoint sh -u 10000:10000 -v VOL:/opt/data:ro -v FILE:/texts.txt:ro <digest>`（置き場は読むだけ） を呼び、`/opt/data` の下の全ファイルについて `grep -a -c -F -f /texts.txt` の行数を出す（`-I` は付けない）。標準出力は `label\tfile\tlines` を 1 行以上のファイルだけ、標準エラーに `files=<全ファイル数> hit_files=N hit_lines=N`。数えの形は 7回目の調べの道具 `bin0/out/raw/b13-files/count.sh` と同じ（違いは目印の代わりに頼みの文のファイルを使うことだけ）。
  6. **判定** `--set k7judge --base FILE --after FILE`: 2 つの k7count の出力を比べ、起点に無いファイルに 1 行でも出たもの・起点より行が増えたものを出す。1 つでもあれば `k7=NG`、無ければ `k7=OK`（design.md §4 K7）。
  7. **後始末③〜⑤** `--set compact --container NAME --volume VOL --fixed DIR --texts FILE --out-prefix P`: 台本が容器の外から順に呼ぶ。③ `docker stop NAME` → k7count（ラベル `after-stop`）→ ④ 部屋ごとに（coordinator・calendar・invoice の順）`docker run --rm --network none -v DIR:/etc/hermes:ro -v VOL:/opt/data <digest> hermes sessions optimize -p <部屋>` → k7count（ラベル `after-optimize-<部屋>`）→ ⑤ `docker start NAME` → `/health` が 200 になるまで 1 秒おき（最長 180 秒）→ k7count（ラベル `after-start`）。各 k7count は `P-<ラベル>.tsv` に書く。止めてから 200 までの秒を `stop_to_health_seconds=` で出す。ある部屋の optimize の後に、その部屋の `profiles/<部屋>/state.db`・`state.db-wal` の行の合計が、その前の数えより減らなかったら（前が 0 のときは除く）、そこで止めて `compact=STOPPED room=<部屋>` を出し終了コード 3（design.md §5）。optimize の標準出力の `reconcile:` の行はそのまま生の出力に残す。
  8. **設定の読み出し** `--set configcheck --container NAME`: 3 部屋それぞれで `docker exec NAME hermes -p <部屋> config get <鍵>` を 8 つの鍵について呼び、正本の値と比べる（真偽は `true`/`false`、空の一覧は `[]`、文字はそのまま）。`room\tkey\tgot\texpected\tok` を出す。1 つでも違えば終了コード 4。
  9. **対照の 1 回送り** `--set probe --room R --model custom/fake-model --text こんにちは [--container NAME --wait-fake-lines N]`: `chat()` と同じ道で 1 回送る（係の部屋なら形の指示も付く）。台本が作った番号を使う。`--wait-fake-lines` があれば、`docker exec NAME grep -c "/chat/completions" /tmp/fake.log` が N 以上になるまで 1 秒おきに最長 30 秒待つ。届かなければ `probe=TIMEOUT fake_lines=<数>` を出して終了コード 5。そのあと `get_session` を読み、`sid_by_script=1`・`get_status`・`reply_model`（返事の model）・`usage_in`・`usage_out`・`input_tokens`・`output_tokens`・`api_call_count` を出す（L3・L5）。最後に DELETE する。
- (3d) `bin0/control/fake_ai.py` を新しく置く: `bin0/out/raw/b13-files/fake_ai.py` の写しに、ログの 1 行へ `model=<受けた model の値>` を足すだけ（L5）。`last=`・`sys0=` の欄は消す（頼みの文をログに書かない）。ほかは変えない。調べの記録の `raw/b13-files/` の方は書き換えない。
- (3e) `bin0/test_run_bin0.py` に足す（今の 11 件と合わせて 18 件）:
  - 12. 係の部屋への本文の messages の先頭が system で、`SCHEMA_SYSTEM_LEAD` で始まり schema.json の全文を含む。まとめ役の本文に system が無い。
  - 13. 消す前に GET が呼ばれ、その後に DELETE が呼ばれる（偽の Hermes の道の順）。
  - 14. 返事の usage と会話の数が同じで `api_call_count` 1 なら `k9_ok=1`、`api_call_count` 2 なら 0。
  - 15. DELETE が 404 なら `deleted` に数えず `deleted_404` に数える。
  - 16. fixed-config: 正本から 1 つ鍵を抜いた写しを読ませると終了コード 2 で、抜いた鍵の名前が出る。`--title-on --test-model` で書いたファイルに `title_generation` true と `model:` が入り、正本のファイルは変わらない。
  - 17. k7judge: 起点に無いファイルに 1 行で NG・起点と同じ行数で OK・起点より増えたら NG。
  - 18. compact: docker を呼ぶ部分を差し替えた試しで、呼ぶ順が stop → 数え → optimize coordinator → 数え → optimize calendar → 数え → optimize invoice → 数え → start → 数え になる。ある部屋の後で行が減らないと終了コード 3。
  - 試験 9（出力に頼みの文が出ない）は、足した欄も含めて通ること。
- (3f) `bin0/README.md`:
  - 15 行目の「9 件」を「18 件」に。
  - 2 番の後ろに「固定設定を書き出す: `run_bin0.py --set fixed-config --out /tmp/bin0-fixed`」を足す。
  - 3 番の起動の命令に `-v /tmp/bin0-fixed:/etc/hermes:ro` を足す。クラウドでログインするときだけ要る足し（7回目の手当て）として `-v /root/.ccr/ca-bundle.crt:/etc/ca-proxy.crt:ro -e SSL_CERT_FILE=/etc/ca-proxy.crt -e REQUESTS_CA_BUNDLE=/etc/ca-proxy.crt` を別の行に書く（検証は切らない）。
  - 4 番を「部屋ごと（7回目で確かめた）: `hermes -p <部屋> auth add openai-codex` を 3 部屋に」に直す。
  - 8 番を `--set k7count`（起点・止めた直後・各部屋の詰め直しの後・起こした後）と `--set k7judge` に直す。`grep -rIl` の形は消す（`-I` では state.db を読み飛ばす: out/raw/b8-k7.txt）。
  - 「便0-B で流す命令」の最後に「後始末③〜⑤は `--set compact`」と、「最初の対照は手順書 card-bin0b-r8.md の 5」を足す。
- (3g) 試験を流す（前のカードの 3f と同じ命令に `--with pyyaml==6.0.2` を足す）。**18 passed** でなければ直して流し直す（3 回まで）。生の出力は `out/raw/r8-3-pytest.txt`。

### 4. 頼みの文のファイル

cases.json の 23 件・k4-cases.json・k8-cases.json の文（会社 A の文と決まりも）を 1 行 1 件で、容器の外の `/tmp/bin0-texts.txt`（600）に作る。件数だけを `raw/r8-4-texts.txt` に書く。中身は書かない。

### 5. 最初の対照（作り物の AI・ログインなし・本物の束より前に 1 回・design.md §5「便0-B の最初の対照」）

本物の束とは別の使い捨ての置き場（volume `bin0-ctl`）と容器（`bin0-ctl`）で行う（L2）。結果は `bin0/out/measure-b-r8.md` の表 C に「#／流した命令（鍵は伏せる）／返った数字・名前／○×」で書く。

- (5a) 鍵は README 1 番で作る（未作成なら）。`docker volume create bin0-ctl` → `bash bin0/setup_profiles.sh bin0-ctl`（`cfg_key_lines` を表 C に書く）。
- (5b) 試し専用の固定設定を 2 つ書き出す: `--set fixed-config --out /tmp/bin0-fixed-c1 --test-model bin0/out/raw/b13-files/model.yaml --title-on`（対照①）と `--out /tmp/bin0-fixed-c3 --test-model bin0/out/raw/b13-files/model.yaml`（対照②③）。
- (5c) 起動（L4）: README 3 番の守りの形で、名前 `bin0-ctl`・置き場 `bin0-ctl`・固定設定 `/tmp/bin0-fixed-c1`・`-v <repo>/docs/handoff/ai-assistant/bin0/control:/fake:ro`・`-p 127.0.0.1:8643:8642`（台本が外から送るため。ログインも認証局の足しも付けない）。起こした後 `docker exec -d bin0-ctl python3 /fake/fake_ai.py`（調べの道具 `bin0/out/raw/b13-files/start.sh:7-9` と同じ形）。`/health` が 200 になるまで確かめる。
- (5d) 対照①: `--set probe --base-url http://127.0.0.1:8643 --room invoice --model custom/fake-model --text こんにちは --container bin0-ctl --wait-fake-lines 2`。○ の形: 作り物の AI の chat が 2 行・`api_call_count` が 2（題づけが会話の数に入る）。1 行も届かない／30 秒で 2 行にならない／`api_call_count` が 1 なら **止まる**（`NEEDS_DECISION: 対照①`）。
- (5e) 対照②: (5d) の出力の `sid_by_script=1` と `get_status=200`。404 なら **止まる**。
- (5f) 作り物の AI のログを読む（L4）: 止める前に `docker exec bin0-ctl cat /tmp/fake.log` を `raw/r8-5-fakelog-c1.txt` に。表 C に chat の行数と、受けた `model=` の値と、返事の `reply_model` を並べる（L5）。
- (5g) 対照③: `docker rm -f bin0-ctl` → 同じ置き場で固定設定 `/tmp/bin0-fixed-c3` に替えて (5c) と同じ形で起こし直す → `--set configcheck --container bin0-ctl`（24 行がすべて ok。違えば **止まる**）→ 3 部屋それぞれ `--set probe … --wait-fake-lines <前の行数+1>` で 1 回ずつ送る（3 部屋とも `get_status=200`・`api_call_count=1`・作り物の AI へ 1 回ずつ届く。違えば **止まる**）→ ログを `raw/r8-5-fakelog-c3.txt` に。あわせて `docker exec bin0-ctl grep -c "multiplex_profiles" /opt/data/config.yaml` の数を記録する（合否に使わない）。
- (5h) 対照の後片付け: `docker rm -f bin0-ctl` → `docker volume rm bin0-ctl` → `/tmp/bin0-fixed-c1`・`/tmp/bin0-fixed-c3` の中の config.yaml を 1 つずつ `rm`（`-r` を使わない）→ ディレクトリを `rmdir`。

### 6. 本物の置き場を作って起こす

- (6a) 新しい置き場: `docker volume create bin0-data` → `bash bin0/setup_profiles.sh bin0-data`（`prompt_txt_sha256` と `cfg_key_lines` を表 2 に）。
- (6b) `--set fixed-config --out /tmp/bin0-fixed`（`test_model=0 title_on=0` であること）。
- (6c) README 3 番の命令（`-v /tmp/bin0-fixed:/etc/hermes:ro` とクラウドの認証局の足しを付ける）で `bin0-run` を起こし、`/health` 200。
- (6d) `--set configcheck --container bin0-run`。24 行すべて ok でなければ **止まる**。

### 7. ログイン（PO が別の画面で打つ）

前のカードの手順 6 の 6a〜6f を、部屋ごとに invoice → coordinator → calendar の順で行う（`docker exec -u hermes bin0-run hermes -p <部屋> auth add openai-codex`。7回目にこの形で 3 部屋とも通った）。番号は部屋ごとに `login-code.txt` 1 ファイルだけ commit・push。ある部屋が 2 回とも時間切れなら `BLOCKED: ログインが通らない（部屋名）` で止まる。終わったら 3 部屋に `--model openai-codex/gpt-5.6-terra` で「こんにちは」を 1 回ずつ送って `finish_reason=stop` を確かめ、使った会話を消す（中身は書かない）。

### 8. 起点の数え（K7）

ログインの確かめの会話を消した後、束の前に: `docker stop bin0-run` は**しない**。`--set k7count --label baseline --volume bin0-data --texts /tmp/bin0-texts.txt > out/r8-k7-baseline.tsv`。動かしたままの置き場を別の容器が読むが、k7count は置き場を読むだけで差し込む（3c の 5）。

### 9. 束を流す

- (9a) K6: 前のカードの 8a と同じ（生は `raw/r8-9-mem.txt`）。
- (9b) `--set main`（3 回・69 件・`--tool-runs-shape data`）→ `out/r8-main.tsv`・`out/r8-main.err`。
- (9c) `--set k4`（`--tool-runs-shape data`）→ `out/r8-k4.tsv`・`.err`。`--set k8` → `out/r8-k8.tsv`・`.err`。
- (9d) 終了コードが 0 でなければ、その組を 1 回だけ流し直す。2 回とも駄目なら止まる。
- (9e) K9 で、返事の `prompt_tokens` と会話の `input_tokens` が違う件があっても止めない。`k9_cache`・`k9_reasoning` を残し、K9 は表 4 に「設計役が足し方を決めてから判定」と書く（design.md §4 K9）。

### 10. 後始末と K7

- (10a) `--set compact --container bin0-run --volume bin0-data --fixed /tmp/bin0-fixed --texts /tmp/bin0-texts.txt --out-prefix out/r8-k7`。生の出力は `raw/r8-10-compact.txt`。終了コード 3 なら、その時点の数えを残して止まる。
- (10b) `--set k7judge --base out/r8-k7-baseline.tsv --after out/r8-k7-after-start.tsv`。あわせて止めた直後・各部屋の後も起点と比べ、表 4 に全部並べる。

### 11. 結果の表

`bin0/out/measure-b-r8.md` の表 4 に K1〜K9 を「基準／測った値／合格の線（design.md §4）／○×・未確認」で書く。K5 は秒の中央値・最長だけ（合否は Opus が今の秘書と並べて決める）。K6 は MiB と GB。K7 は「起点からファイルごとに増えた行」の表。K9 は「対照は題づけだけで確かめた」と書く。消す口は 200 と 404 を別に。

### 12. 仕上げと後片付け

前のカードの手順 10（10a〜10d）と同じ。ただし題は `docs(ai-assistant): 便0-B 8回目 束 69 件の測り（Hermes の側）`、後片付けで `/tmp/bin0-fixed/config.yaml` と `/tmp/bin0-texts.txt` も 1 つずつ `rm` する。

## 止まるとき・終わるとき

前のカードの「止まるとき・終わるとき」と同じ。報告のファイル名は `bin0/out/impl-report-b-r8.md`。最後の返事の 1 行は `DONE: <sha>` か、報告と同じ `BLOCKED:`・`NEEDS_DECISION:` の行。

END OF CARD
