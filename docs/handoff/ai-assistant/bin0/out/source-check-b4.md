受領確認: 調べの依頼を読んだ

# bin0-B Hermes ログ抑止リハーサル（読み Q9〜Q12 + 作り物の AI を置いた容器内実験）

- 作業枝: `release/ai-assistant-bin0b`。`new-worktree.sh` の直後は main(c42d7ba20) を指していたので `git switch -C release/ai-assistant-bin0b origin/release/ai-assistant-bin0b` で合わせた。HEAD=1ce1a63ed（`git merge-base --is-ancestor 1ce1a63ed HEAD` 成功 = 1ce1a63ed 以降）。
- 作り方は source-check-b2.md・b3.md と同じ: `setup_profiles.sh`（IMAGE は同 digest、`prompt_txt_sha256=913a71d5…53f2e`）、使い捨ての鍵（`openssl rand`・値は出していない）、volume ごとに 3 部屋（coordinator・calendar・invoice）、`gateway run` は README 手順 3 の守り（`--read-only --cap-drop ALL --cap-add SETGID/CHOWN/SETUID/FOWNER`）に `--network none`、ログインの札なし。送信は `docker exec` の `curl` で容器内 `127.0.0.1:8642/p/invoice/v1/chat/completions`。docker デーモンは動いておらず dockerd を自分で起動（pull は 1 回目で成功）。ソースは `/tmp/hsrc/hermes`（`docker create` → `docker cp`、= 容器の `/opt/hermes`）。以下の `ファイル:行` はそこからの相対。
- 目印は MARK7734。数字は `grep -a -c MARK7734`（目印を含む**行数**）。各条件 1 回の実測。「全ファイル」は `/opt/data` 以下の全ファイル（533〜546 ファイル、-wal・バイナリ含む）。
- 生の出力: `out/raw/b12-0-read-excerpts.txt`（読んだ行の写し）・`b12-1-q9-config-reset.txt`・`b12-2-e0-base.txt`・`b12-3-e1-config-warning.txt`・`b12-4-e2-managed.txt`・`b12-5-e3-tmpfs.txt`・`b12-6-chain.txt`
- 見張りに止められた: 2 回。(1) 準備で `/tmp/hsrc` を空にする命令（`rm -rf`）。→ 言い換えず取りやめ（`/tmp/hsrc` は元々無かった）。(2) `_maintenance.py` の VACUUM 周りを探した grep（パターンに危険語を含めたため）。→ 言い換えず、Read で `_maintenance.py:622-670` を開いて読んだ（Q12）。
- 前回 b3 との違い（事実）: 今回は作り物の AI を容器内に置いたので、頼みは AI まで届き、HTTP 200・返事は作り物の文になった（b2・b3 は AI 未接続で失敗応答だった）。

## 作り物の AI と Hermes の設定

- 作り物: 容器内 `127.0.0.1:18765`（空き。`--network none` の容器なので他に使う者なし）で python 標準の `http.server` を動かし、`POST /v1/chat/completions` に `FAKE-REPLY-OK` を返す（`stream: true` には SSE、無しには JSON。`GET /v1/models` にも答える）。頼みの本文に MARK7734 が入っているかだけ容器内 `/tmp/fake.log`（`/opt/data` の外・tmpfs）に残す。
- Hermes の正式な設定（invoice の `profiles/invoice/config.yaml` だけに足した）:
  ```
  model:
    provider: custom
    base_url: http://127.0.0.1:18765/v1
    default: fake-model
    api_key: dummy-key-not-secret
  ```
  出典: `cli-config.yaml.example:78-81`（`model:` と `default:`）・`:107`（「`custom` - Any other OpenAI-compatible endpoint. Set base_url below.」）・`:116`（`api_key` 行）・`:117`（`base_url` 行）。
- 実測（E0・`raw/b12-2`）: HTTP **200**、本文の `choices[0].message.content` は **`FAKE-REPLY-OK`**（作り物の文）、`model` は `hermes-agent`。`fake.log` に `POST /v1/chat/completions stream=True has_MARK=True` と `stream=None has_MARK=True` の 2 行（Hermes が AI 側へ送った頼みに MARK7734 が入っていた。ほかに `GET /v1/models`・`POST /api/show` 等の探りが並ぶ）。

## Q9 b3 E1 で `logging.level: WARNING` が agent.log の INFO を止めなかった理由

判定: **`setup_logging` より前に出る行でも、別の道でも、multiplex の gateway が別の値で決めているのでもない。起動のたびに `/opt/data/config.yaml` が既定のひな形に置き換わり、足した `logging:` ごと消えていた。**

- 置き換える行: `docker/stage2-hook.sh:438-441`（`seed_one`: `[ ! -f "$HERMES_HOME/$dest" ] && [ -f "$INSTALL_DIR/$src" ]` なら `as_hermes cp` で写す）と `:447`（`seed_one "config.yaml" "cli-config.yaml.example"`）。
- なぜ「無い」と判定されるか（実測 `raw/b12-1`）: `/opt/data` は `drwx------ hermes`。README 手順 3 の守り（`--cap-drop ALL` に SETGID・CHOWN・SETUID・FOWNER だけ足す）では、容器の root が `/opt/data` の中を引けず、`[ -f /opt/data/config.yaml ]` が **false**。`--cap-add DAC_OVERRIDE` を足すと **true**、守りなし（既定の caps）でも true。
- 起動前後の実測（同じ 82 バイトの設定 = `gateway.multiplex_profiles`・`logging.level: WARNING`・`_config_version: 54` を置いて起動）:

  | 起動の守り | 起動後の `config.yaml` | 起動以降の `/opt/data/logs/agent.log` | 同 `gateway.log` INFO |
  |---|---|---|---|
  | README 手順 3 のまま | **133740 バイト・`logging:` 0 行**（ひな形 `cli-config.yaml.example` は 133735 バイト。足した 5 バイトは起動時の `gateway.multiplex_profiles: true` 書き込み = agent.log の `Wrote gateway.multiplex_profiles: true … (was unset)`、`hermes_cli/gateway_multiplex_mode.py:220-221`） | **INFO=130**・WARNING=2 | 8 |
  | ＋`--cap-add DAC_OVERRIDE` | **82 バイトのまま・`logging:` 1 行** | **INFO=0**・WARNING=2 | 0 |

  （`raw/b12-1` の echo の「1170 bytes」は台本の文言の誤り。実際の大きさはその下の `before: 82 bytes`。）
- 補足の事実: 起動の最初の 0.3 秒後の時点（`stage2-hook.sh` が動いている最中）で既に 133735 バイトだった（別の測定。画面にだけ出して raw には残していない）。ひな形と同じ大きさ。ただし `cp` の実行そのものを strace 等で見たわけではない（大きさの一致と上の `-f` の実測からの読み）。
- 部屋側の config（`profiles/<部屋>/config.yaml`）は書き換わっていなかった（invoice の mtime は起動前のまま）。書き換わるのは起動する側 `/opt/data/config.yaml` だけ。
- b3 E1 の INFO 238 行の中身（`hermes_cli.plugins` 203 行・`boot_bootstrap` ほか）は、setup の容器（既定の守り・`logging` を足す前）が先に `agent.log` に書いた分と、起動後に置き換わった既定ひな形（level 未設定 = INFO）の下で出た分。`setup_logging` より前に出たのではない（起動後 INFO=0 の実測が上の表）。
- 読みの訂正: b2 の「起動側の `logging.level` が全部屋に掛かる」（`hermes_logging.py:406`・`:673`・`:734`）は、**起動側の設定が残れば実測でも支持された**（E1・E2 とも invoice の agent.log は目印 0 行・INFO 無し、下）。b3 が支持しなかったのは設定が消えていたため。
- 影響（事実）: README 手順 3 の守りで起動すると、`setup_profiles.sh` が `/opt/data/config.yaml` に置いた設定（`memory` off・`platform_toolsets: api_server: []`・`auxiliary.background_review off`・`fallback_providers: []`）が起動のたびにひな形で消える。部屋ごとの config にも同じ内容を置いているので部屋側は無傷だが、起動する側（default）の設定は効いていない。b2・b3 の default 側の挙動を読むときは注意（未調査: これが過去の数字に影響したか）。

## Q10 agent.log の INFO を止める・agent.log を書かせない別の手（全部）

| 手 | 結果 | 根拠 |
|---|---|---|
| ① 起動する側 `/opt/data/config.yaml` の `logging.level` | **効く（ただし設定が起動で消されない時だけ）**。E1（`--cap-add DAC_OVERRIDE` つき・WARNING）: invoice の `agent.log` は目印 **0 行**・全 1 行（WARNING のみ）、invoice の `gateway.log` はファイル無し。README の守りのままだと Q9 のとおり消える | `hermes_logging.py:408-410`（`level_name = (log_level or cfg_level or "INFO")`）。2 つ目以降の部屋は `:406`（`_adopt_secondary_home`）で level を読まずに返り、ルーターの level を引き継ぐ（`:734`）= 起動した home の値が全部屋に掛かる。全部屋の `gateway.log` の INFO も止まる（root の level が WARNING になる `:449-450`。実測 gateway.log INFO=0） |
| ② 管理者の固定設定 `/etc/hermes/config.yaml`（または環境変数 `HERMES_MANAGED_DIR` が指す所）に `logging.level` | **効く**。E2（README の守りのまま・DAC_OVERRIDE 無し・`-v …/managed:/etc/hermes:ro` で `logging: level: WARNING`）: invoice の `agent.log` 目印 **0 行**・全 1 行。`/opt/data/config.yaml` がひな形に戻されても影響を受けない | `hermes_cli/managed_scope.py:31`（`_DEFAULT_MANAGED_DIR = /etc/hermes`）・`:48-52`（`HERMES_MANAGED_DIR` が優先）・`:114-123`（`load_managed_config`）。読む側: `hermes_logging.py:1051-1068`（`load_user_config_effective` = 管理者の固定設定を重ねる。`:1053-1055` のコメントに「an administrator can pin logging.*」） |
| ③ 環境変数で level を決める | **無い**。`hermes_logging.py` に `environ`・`getenv` の出現 0 件。`HERMES_QUIET`（`gateway/run.py:2128` で常に 1 に設定）は level の指定ではない | `hermes_logging.py` 全体の検索（`HERMES_PLUGIN_HOST_LOG_LEVEL` は別系統で `hermes_cli/plugin_host*.py` のみ） |
| ④ `gateway run` の引数 | **無い**（agent.log の level には効かない）。`-v/-q` は標準エラーに出す handler を足すだけ（`gateway/run_bootstrap.py:162-171`）。`setup_logging` は `mode="gateway"` だけ渡す（`:148`）。検索した範囲（`console_engine.py`・`main.py` の引数定義・`gateway/run*.py`・`hermes_cli/gateway*.py`）に `--log-level` 相当は 0 件 | `hermes_logging.py:375-384`（`log_level` 引数は有るが呼び出し元 `run_bootstrap.py:148`・`main.py:591`・`agent_init.py:619` は渡さない） |
| ⑤ config の別の鍵 | **level 以外は抑止に使えない**。`logging` の鍵は `level`・`max_size_mb`・`backup_count` の 3 つだけ（回すだけで止めない。`max_size_mb: 0` は `or` で 5 に戻る `:409-413`） | `hermes_cli/config_defaults.py:1976-1980`・`hermes_logging.py:410-412` |
| ⑥ logger 名ごとの level | **設定の口は無い**。固定の一覧 `_NOISY_LOGGERS`（第三者の名前）を WARNING に固定するだけ（`hermes_logging.py:247-250`）。目印の行の logger `agent.turn_context` には効かない。agent.log に component の絞りは無い（`:421` の最後が `None`） | `hermes_logging.py:247-250`・`:420-424` |
| ⑦ docker 側で `/opt/data/logs` を tmpfs にする（`--tmpfs /opt/data/logs:uid=10000,gid=10000,mode=755`） | **書かせない手ではない**。E3: invoice の `agent.log` に目印 **1 行**（そのまま書かれる）。ただし RAM 上なので容器を止めると消える（止めた後の確認は今回していない = **未確認**） | `raw/b12-5` |

- 未試験（読みだけ・推測は書かない）: `logging.level: CRITICAL`（`:449-450` の root 設定が errors.log に及ぶか）・`agent.log` を `/dev/null` へのリンクにする・`logs/` を読み取り専用にする。
- どの手でも `errors.log`（WARNING 固定 `:422`）は残る（E1・E2 の invoice errors.log は 1 行 = AI の context 長が取れない WARNING。目印は 0 行）。

## Q11 `agent/turn_context.py:1275-1290` の「頼みの先頭 80 字」の行

判定:
- 行: `:1290` の `logger.info(_turn_fmt, *_turn_args)`。文面は `conversation turn: session=%s model=%s provider=%s platform=%s history=%d msg=%r`（`:1277-1279`）。
- **logger 名: `agent.turn_context`**（`:43` `logger = logging.getLogger(__name__)`）。実測の行（E0・invoice の agent.log）: `INFO [api-b7c8f1e808160e4d] agent.turn_context: conversation turn: session=api-b7c8f1e808160e4d model=fake-model provider=custom platform=api_server history=0 msg='MARK7734'`。
- **level: INFO**。
- 書く条件: 行自体に `if` は無い（`:1287-1289` の `_turn_origin` は末尾に ` origin=…` を足すだけ）。**会話の 1 ターンが始まるたび、毎回**（`_reset_per_turn_agent_state(agent)` `:1273` の後）。頼みの文は `summarize_user_message_for_log(user_message)`（`:1275`）の先頭 80 字（超えたら `...`・改行は空白）を `%r` で書く（`:1276・:1283`）。
- 書かれる先: その部屋の `agent.log`（実測 invoice の agent.log に 1 行）。`gateway.log` には出ない（実測 invoice の `gateway.log` は 2 行・目印 0。agent の logger は gateway の component の絞り `hermes_logging.py:330-` に入らない）。`errors.log` にも出ない（INFO のため）。
- 前回 b2・b3 で目印が agent.log に出なかったのは、AI が無く失敗がこの行より手前だったため（今回 AI を置いたら出た）。

## Q12 `admin.vacuum()`（`persistence/sqlite/admin/_maintenance.py:626-654`）を動いている別の書き手がいるときに

Read で `:622-670` を開いて読んだ（grep は止められたので使わず）。

- **`vacuum_blockers`（`:682-689`）は `vacuum()` の中で使っていない**。`vacuum()` の本体は: `self._writer("vacuum")`（`:634`）→ 壊れた DB なら例外（`:635`）→ FTS の `'optimize'`（`_optimize_fts`、失敗は WARNING を書いて続行 `:637-640`）→ `holder._lock` の中で PASSIVE の checkpoint（`:647`）→ `VACUUM`（`:648`）→ 後ろの WAL を縮める checkpoint（`:650`）→ ファイルの同一性を記録し直す（`:653`）。**他の持ち主を数える・待つ行は無い**。docstring の「Takes an exclusive lock: callers must ensure no other writers are active」（`:628`）が、確認を呼び出し側（`sessions_cmd.py:1522-1528` の `held_refusal`。`--force` で飛ばせる）に任せている印。
- 動いている別の書き手（gateway）がいて `--force` で通した場合に起きること（ソースからの読み）: ①`VACUUM` は書き込みの排他が要るので、**他の書き手の書き込みはその間待たされる**。gateway 側の書き込みが待つ上限は `_WRITE_PATIENCE_S, _TRANSCRIPT_WRITE_PATIENCE_S, _ACTIVITY_WRITE_PATIENCE_S = 20.0, 60.0, 0.5`（`persistence/sqlite/_holder.py:243`）。VACUUM がそれより長引けば gateway の書き込みが「database is locked」系で失敗しうる（**実測していない**）。②`vacuum()` 自身が錠を取れなければ例外になり、CLI は `Error: optimization failed: …` を出して終了番号 1（`hermes_cli/sessions_cmd.py:1062-1066`）。③後ろの checkpoint の失敗は WARNING だけで続行（`_try_checkpoint` の第 3 引数の文面 `:647・:650`）。④`vacuum()` の書き込み接続の busy 待ち時間の値は **未確認**（接続を作る行を特定していない）。
- 実測（b3 E2 で実施済み・今回は再実施せず）: 会話 1 件の小さな DB では、gateway 稼働中に `--force` つきで optimize しても終了 0・gateway は落ちず・直後の送信は 200。長い VACUUM との競合は未確認。

## 実験: 目印 MARK7734 を 1 回送る（各条件 1 回・新しい volume。README 手順 3 の守り。①だけ DAC_OVERRIDE を足した）

HTTP と返事はどれも **HTTP 200・`FAKE-REPLY-OK`**。

| 条件（volume） | default の agent.log・gateway.log・errors.log の目印行 | invoice の agent.log・gateway.log・errors.log の目印行 | 全ファイルの目印の合計行（ファイル数） |
|---|---|---|---|
| E0 何もしない（b12-e0） | 0・0・0 | **1**・0・0 | **12**（534）= invoice agent.log 1 + `state.db-wal` 11 |
| E1 起動側 config に `logging.level: WARNING`＋DAC_OVERRIDE（b12-e1） | 0・0・0 | **0**・（ファイル無し）・0 | **11**（537）= `state.db-wal` 11 |
| E2 管理者の固定設定 `/etc/hermes/config.yaml` に WARNING（b12-e2） | 0・0・0 | **0**・（ファイル無し）・0 | **11**（533）= `state.db-wal` 11 |
| E3 `/opt/data/logs` を tmpfs（b12-e3） | 0・0・0 | **1**・0・0 | **15**（533）= invoice agent.log 1 + `state.db-wal` 14 |

- どの条件でも `state.db-wal`（会話の保存）には目印が入る。ログを止める手でも会話は保存される（前回 Q6 と同じ）。行数が 11/14 とばらつくのは 1 回の送信で作り物の AI へ 2 回送られ（stream と非 stream）、保存・FTS・題名づくり等で複数行に入るため（内訳は未調査）。
- E1・E2 の default 側 `/opt/data/logs/agent.log` が 94 行あるのは、setup の容器（`logging` 設定前）が書いた分（目印 0）。

## 最後に 1 つの手（E2 = 管理者の固定設定）で DELETE → docker stop → 別の使い捨て容器で optimize → start

volume `b12-e2`（目印は E2 で 1 回送信済み）。`raw/b12-6`。

1. gateway を再起動（固定設定つき）→ 全ファイルの目印: `profiles/invoice/state.db` に **2 行**（545 ファイル。前の stop で -wal が本体に入った分）。
2. `DELETE /p/invoice/api/sessions/api-b7c8f1e808160e4d` → HTTP **200**。数え直すと `state.db` 2 行 + `state.db-wal` 2 行 = **4 行**（消えていない）。
3. `docker stop`（10 秒）。
4. 別の使い捨て容器: `docker run --rm --network none -v <固定設定>:/etc/hermes:ro -v b12-e2:/opt/data <IMAGE> hermes sessions optimize -p invoice` → `Optimized 2 FTS index(es).`・`Database size: 0.4 MB -> 0.4 MB (reclaimed 0.0 MB)`（`--force` 無しで断られず）。
5. `docker run -d …`（start）→ `/health` 200 → **全ファイルの目印: 合計 0 行（545 ファイル）**。ログ 3 種（default・invoice とも）も 0。
- 参考（`raw/b12-6` の 1 回目）: この前に、セッション id の取り出しを誤って **DELETE が実行されないまま** stop → optimize → start した。その結果は `state.db` に **2 行残った**（合計 2 行）。つまり DELETE 無しでは optimize でも消えなかった。
- 切り分けていないこと（**未確認**）: 0 行が optimize の VACUUM の効果か、DELETE 後の -wal の整理（stop）だけの効果か（stop 後・optimize 前の数えを今回は取っていない）。b3 E3 と同じ留保。

## まとめ（事実のみ）

| 問い | 結果 |
|---|---|
| Q9 | 設定が効かなかった理由 = README 手順 3 の守りでは `/opt/data/config.yaml` が起動のたびにひな形で上書きされる（`stage2-hook.sh:438-447`・実測 133740 バイト・`logging:` 0 行・INFO=130）。`--cap-add DAC_OVERRIDE` で残り INFO=0 |
| Q10 | 抑止できる手: ①起動側 config（設定が残る時）・②`/etc/hermes/config.yaml` の管理者固定（README の守りのままで効く）。環境変数・`gateway run` の引数・logger 名ごとの level・level 以外の config の鍵は無い。tmpfs は書かせない手ではない（RAM 上に書く） |
| Q11 | logger `agent.turn_context`・INFO・ターンの開始ごとに無条件（`turn_context.py:1290`）。invoice の agent.log にだけ出る |
| Q12 | `vacuum()` は他の持ち主を数えも待ちもしない（`vacuum_blockers` 不使用）。確認は呼び出し側。競合時の失敗の形は読みだけ（実測は小さな DB のみ） |
| 実験 | 作り物の AI へ向けた invoice は HTTP 200・`FAKE-REPLY-OK`。E1・E2 は invoice agent.log の目印 0 行、E0・E3 は 1 行。会話の保存（-wal）には全条件で入る。E2 で DELETE → stop → optimize（別容器）→ start の後は全ファイル 0 行 |

後片付け: 試しの容器・volume（`b12-*`）・`/tmp/hsrc`・使い捨ての鍵・dockerd は push の後に片付ける（結果は最後の返事ではなく作業の記録として）。

DONE
