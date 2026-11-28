受領確認: card-bin0b-r9 を読んだ

# 便0-B 9回目 実装報告

| 手順 | 結果 |
|---|---|
| 1 作業場所 | `new-worktree.sh release/ai-assistant-bin0b --claude`（末尾の起動失敗は無視）→ `git switch -C … origin/release/ai-assistant-bin0b`。HEAD = origin = fbc0f0e5f ○ |
| 2 Docker・完成品 | dockerd を起動・digest 固定で取得・`Hermes Agent v0.23.4` ○ |
| 3a 道具（run_bin0.py） | `read_usage`・`USAGE_INNER`・K9 を表で決める（1 回目の読み最大 30 組・DELETE 直前の最後の読み・`k9_main_first/last`・`k9_aux_first/last`・`k9_reads`・`k9_mismatch`）・`--set main`/`k8` の `--container` 必須（無ければ終了コード 2）・probe（`--wait-aux`・`--expect-lead`・終了コード 7/8/9・`fake_lead_lines`・`after_` の 3 つ）・`--set fake-lead`・`control/.gitignore`。8回目の 4 つ（k9_ok の順・起動待ち 180 秒で 6・`--keys-file`・k7count の空行で 2）は残した ○ |
| 3b fake_ai.py | `FAKE_LEAD_FILE`（既定 `/fake/schema_lead.txt`）・無い／空白だけなら `fake_ai=NO_LEAD` で終了コード 1・読めれば `fake_ai=START lead_chars=N`・chat の行に `schema_lead=<1/0>`。usage 11/7 は変えず ○ |
| 3c 試験 | 24 件（14 を直し 19〜24 を足した） ○ |
| 3d README | 「24 件」・6 番に `--container bin0-run`・11 番を r9 の 5 に ○ |
| 3e 試験を流す | `24 passed`（1 回目で通った・raw/r9-3-pytest.txt）○ |
| 4 頼みの文のファイル | 31 行（重複を除いた後。元は 40 行）。raw/r9-4-texts.txt（件数のみ）○ |
| 5a〜5j 最初の対照 | 全部 ○（out/measure-b-r9.md 表 C）。対照①: `usage_main_sum=1`・`usage_aux=title_generation:1:1`・`usage_ok=1`・`fake_lines=2`。対照②: `get_status=200`。対照③: 3 部屋とも終了コード 0・`api_call_count=1`・`fake_lead_lines` は 0/1/1。configcheck 24 行 ok |
| 6 本物の置き場 | `bin0-data` 作成・固定設定（`test_model=0 title_on=0`）・`bin0-run` 起動・`/health` 200・configcheck 24 行 ok ○ |
| 7 ログイン | invoice → coordinator → calendar の順に各 1 回で通った（時間切れなし）。3 部屋に「こんにちは」を 1 回ずつ送り `finish_reason=stop`・消す口 200 ○ |
| 8 起点の数え（K7） | `r9-k7-baseline.tsv`（`hit_lines=0`・568 ファイル） ○ |
| 9 束 | main・k4・k8 とも 1 回目で終了コード 0。K1 69/69・K2 48/48・K3 81/81・K4 15/15・K8 leak 0・K9 69/69（読めない 0・ずれ 0・`k9_reads` 最大 1・`aux` の行の数の食い違い 0）。K5 中央値 4.36 秒・最長 9.53 秒。K6 最大 369.7 MiB（out/measure-b-r9.md 表 4） |
| 10 後始末と K7 | `--set compact` が `compact=DONE`（`stop_to_health_seconds=46.7`）。起点・止めた直後・各部屋の詰め直しの後・起こした後がすべて `hit_lines=0`・`k7=OK` |
| 12 仕上げ | 触ったのは `docs/handoff/ai-assistant/bin0/` の中だけ（`git diff origin/release/ai-assistant-bin0b --name-only` で外が 0 件）。鍵の値とログインの札の値が bin0/ の中に 0 件（8 つの値を確認）。`control/schema_lead.txt` は無い。後片付け: 3 部屋で `hermes auth logout openai-codex`（`Logged out`）→ `bin0-run` 容器・`bin0-data` volume 削除 → `/tmp/bin0-secrets/` の鍵のファイルを 1 つずつ rm して rmdir → `/tmp/bin0-fixed/config.yaml` を rm して rmdir → `/tmp/bin0-texts.txt` を rm |

## 実装での補い（カードに細かい形が無かった所）

- K9 の GET の添えの確かめ（入力・出力が返事の usage と同じで `api_call_count == 1`）は、その会話の 1 回目の読みが成功したとき（GET と表の両方が 1 以上）だけ使った。1 回目の読みが読めない会話は、最後の読みの `main_sum > 1`・`aux` の行だけをずれの根拠にし、そのほかは `-`。
- probe の出力の先頭は、`usage_ok` と `--expect-lead` が両方合えば `probe=OK`、合わなければ `probe=NG`（終了コードは 8 か 9）にした。
- 手順 5b: `state_meta` を作る文が `_schema.py` に無かったため、完成品の中（`/opt/hermes`）を読み取りだけで 1 回追加で探し、`_schema_ddl.py:306-309` で `key TEXT PRIMARY KEY` を確かめた（同じ raw の末尾）。
- 手順 5i: `multiplex_profiles` の数は root では権限で読めず（`Permission denied`）、`-u hermes` で数え直して 0。合否には使っていない。
- 手順 5j: `git status --short bin0/control` は、直した `fake_ai.py` と新しい `.gitignore` を出す。`schema_lead.txt` は出ない。
- 手順 7: 次の部屋の番号を出すとき、前の部屋の「使用済み」の書き換えだけの commit は作らず、次の番号の commit で `login-code.txt` を置き換えた（最後の部屋だけ「使用済み」を書いて push）。
- `--set compact` の `--out-prefix` は、台本を backend から流すため絶対パスで渡した（出力は `out/r9-k7-*.tsv`）。
- 途中で、`git add docs`・`git reset` を含む命令を 1 回送り、自動の確認に止められた（実行されていない）。以後は `login-code.txt` だけを `git add` して commit した。

## 止めた命令・見張りの文面

止められたのは上の 1 回だけ（私の誤りの命令・実行されず）。ほかに止められた命令はない。push のときに「origin/main との分岐点が見つかりません」と出て提出前の入口は使えない状態で通ったが、push は成功した。

DONE
