# 便0-B 9回目 測りの表（Hermes の側）

カード: [../../card-bin0b-r9.md](../../card-bin0b-r9.md)。設計: [../../design.md](../../design.md) 第2.10版。完成品は `Hermes Agent v0.23.4`（digest 固定）。
頼みの文・答えの中身はどこにも書いていない（数と状態だけ）。

## 表 2: 部屋の用意

| 項目 | 値 |
|---|---|
| `prompt_txt_sha256` | `913a71d5cbbbf064c5d2e76817062b585da8f90709e18fd91997829c9be53f2e`（raw/r9-6a-setup.txt） |
| `cfg_key_lines`（部屋の config.yaml に 8 つの鍵の名前が出る行数） | 3 部屋とも 0 |
| 固定設定（`--set fixed-config --out /tmp/bin0-fixed`） | `keys=8 test_model=0 title_on=0`（raw/r9-6b-fixed.txt） |
| `--set configcheck --container bin0-run` | 24 行すべて ok（raw/r9-6d-configcheck.txt） |

## 表 C: 最初の対照（作り物の AI・ログインなし・使い捨ての置き場 bin0-ctl）

| # | 流した命令（鍵は伏せる） | 返った数字・名前 | ○× |
|---|---|---|---|
| 3e | 試験（`pytest ../docs/handoff/ai-assistant/bin0/test_run_bin0.py`） | `24 passed`（1 回目で通った・raw/r9-3-pytest.txt） | ○ |
| 4 | 頼みの文のファイル（容器の外 `/tmp/bin0-texts.txt`・600） | 31 行（重複を除いた後。raw/r9-4-texts.txt） | ○ |
| 5a | `setup_profiles.sh bin0-ctl` | 3 部屋とも `cfg_key_lines=0`・`prompt_txt_sha256` は表 2 と同じ | ○ |
| 5b | `docker run --rm --network none --entrypoint sh <digest> -c '<find と grep>'`（raw/r9-5b-image.txt） | `persistence/conversation/usage.py`・`persistence/sqlite/conversation/_store/usage.py`・`persistence/sqlite/_schema.py` がそれぞれ 1 つだけ。`_store/usage.py` に `session_model_usage`・`record_auxiliary_usage` が 8 行（51・114・156・214〜245・296 行目）、`conversation/usage.py:140` に `record_auxiliary_usage`。`_schema.py` に `state_meta`・`session_model_usage` の行あり（56-57・189・1050 行目ほか）。`state_meta` を作る文は `_schema.py` に無く、`_schema_ddl.py:306-309` の `CREATE TABLE IF NOT EXISTS state_meta (key TEXT PRIMARY KEY, value TEXT)`（追加で 1 回だけ読んだ・同じ raw の末尾）。列に `key` あり | ○ |
| 5c | `--set fake-lead` | `lead_chars=33`（`control/schema_lead.txt` に書いた・`docker run` の前） | ○ |
| 5d | 守りの形で `bin0-ctl` を起動（固定設定 c1・`control` を `/fake` に ro・`-p 127.0.0.1:8643:8642`）→ `docker exec -d bin0-ctl python3 /fake/fake_ai.py` | `fake_ai=START` 1 行（1 秒目）・`fake_ai=NO_LEAD` 0 行・`/health` 200 | ○ |
| 5e | `docker exec -u hermes bin0-ctl sh -c 'command -v python3'` と、3 部屋で `read_usage(after)` と同じ命令（番号 `0000…0000`）（raw/r9-5e-ro.txt） | `/opt/hermes/.venv/bin/python3`。3 部屋とも `END` が出て `A 0`・`S 0`・`T 0` | ○ |
| 5f 対照① | `--set probe --base-url http://127.0.0.1:8643 --room invoice --model custom/fake-model --text こんにちは --container bin0-ctl --wait-fake-lines 2 --wait-aux title_generation`（raw/r9-5f-probe-c1.txt） | 終了コード 0・`fake_lines=2`・`usage_main_sum=1`・`usage_main_rows=1`・`usage_aux=title_generation:1:1`・`usage_ok=1`。記録だけ: GET の `api_call_count=1`（`input_tokens=11`・`output_tokens=7`＝返事の usage）・`usage_reads=1`・`fake_lead_lines=1`・`after_usage_rows=0 after_session_rows=0 after_tombstone_rows=1` | ○ |
| 5g 対照② | 5f の出力 | `sid_by_script=1`・`get_status=200` | ○ |
| 5h | `docker exec bin0-ctl cat /tmp/fake.log`（raw/r9-5-fakelog-c1.txt） | chat の行 2（`stream=True` が 1・`stream=None` が 1）・どちらも `model=fake-model`・`schema_lead=` は 1 行目が 1・2 行目が 0・返事の `reply_model=fake-model` | ○ |
| 5i 対照③ | `docker rm -f bin0-ctl` → 固定設定 c3 で起こし直し → `--set configcheck --container bin0-ctl`（raw/r9-5i-configcheck.txt）→ coordinator（`--wait-fake-lines 1 --expect-lead 0`）・calendar（`2`・`1`）・invoice（`3`・`1`）（raw/r9-5i-probe-<部屋>.txt） | configcheck 24 行すべて ok。3 部屋とも終了コード 0・`usage_main_sum=1`・`usage_aux=-`・`usage_ok=1`・`get_status=200`・`api_call_count=1`・`fake_lead_lines` は coordinator 0・calendar 1・invoice 1。chat の行は計 3（raw/r9-5-fakelog-c3.txt）。`multiplex_profiles` の数（合否に使わない）: 0（`-u hermes` で数えた。root では権限で読めなかった） | ○ |
| 5j | 後片付け | `bin0-ctl` 容器・volume を削除。`/tmp/bin0-fixed-c1`・`-c3` の config.yaml を 1 つずつ rm して rmdir。`control/schema_lead.txt` を rm。`git status --short bin0/control` に `schema_lead.txt` は出ない（出るのは直した `fake_ai.py` と新しい `.gitignore` だけ） | ○ |

## 表 4: K1〜K9

束: `--set main`（3 回・69 件・`--tool-runs-shape data`・`--container bin0-run`）→ out/r9-main.tsv・.err。続けて `--set k4`・`--set k8`。3 組とも 1 回目で終了コード 0（流し直しなし）。モデル `openai-codex/gpt-5.6-terra`・決まり帳なし（`rules_count=0`）。

| 基準 | 測った値 | 合格の線（design.md §4） | ○×・未確認 |
|---|---|---|---|
| K1 正しい係に振られる | 69/69 | 69/69 | ○ |
| K2 下書きが今の形で返る | 48/48（やり直し `retried=0`） | 69 件のうち係に振った分すべてが検査を通る | ○ |
| K3 中身の当たり | 81/81（欄の数 81） | 同じ日の今の秘書以上 | Hermes 側 81/81。今の秘書との比べは Opus（今の秘書の測りは別） |
| K4 道具が無い | 15/15（`k4_progress=0`・`k4_tool_runs=0`・15 件とも状態 200・消せた 15/15） | 15/15 実行されない | ○ |
| K5 速さ | 中央値 4.36 秒・最長 9.53 秒（`seconds_median`・`seconds_max`） | 今の秘書（決まり帳つき）の 2 倍以下 | 合否は Opus が今の秘書と並べて決める |
| K6 メモリ | 最大 369.7 MiB（約 0.36 GB・784 点・最小 356.4 MiB・raw/r9-9-mem.txt）。置き場（bin0-data）は約 15 MiB（約 0.015 GB） | 記録のみ | 記録 |
| K7 残らない | 流した頼みの文（31 行）が置き場全体で 0 件。起点 `hit_lines=0`・止めた直後・各部屋の詰め直しの後・起こした後すべて `hit_lines=0`・`k7judge` はすべて `k7=OK`（raw/r9-10-compact.txt・raw/r9-10-k7judge.txt）。起点からファイルごとに増えた行: なし。全ファイル数 568（起点）→ 569（起こした後）。`stop_to_health_seconds=46.7`。消した会話の番号は墓標（`state_meta` の 1 行）に残る。文は入らない。対照①の `after_usage_rows=0`・`after_session_rows=0`・`after_tombstone_rows=1` | 0 件 | ○ |
| K8 会社の混ざり | `k8_leak=0`（10 件とも `leak=0`・消せた 2/2 ずつ） | 0 | ○ |
| K9 使った量 | 69/69（`k9_unreadable=0`・`k9_mismatch=0`）。使った会話 117 本すべてで、表の `main_sum` が 1 回目の読みも最後の読みも 1・`aux` の行 0・GET の `api_call_count=1`・入力・出力が返事の usage と一致。`aux` の行の数が 1 回目の読みと最後の読みで違った件: 0 件。`k9_reads` の最大: 1。参考: `k9_cache=0`・`k9_reasoning=596` | 69/69 | ○ |

K9 の注意: 対照は題づけだけで確かめた。表に書かれない後ろの処理（会話の番号が渡っていない糸・使った量の無い返事・stream の返事・moa）は、本物の束ではこの方法では見えない（design.md:88）。

消す口: `deleted=117/117 deleted_404=0`（main）・k4 は 15/15・404 なし。

## ログイン

invoice → coordinator → calendar の順に各 1 回で通った（時間切れなし）。3 部屋に `--model openai-codex/gpt-5.6-terra` で「こんにちは」を 1 回ずつ送り、3 部屋とも状態 200・`finish_reason=stop`・消す口 200（raw/r9-7-hello.txt）。
