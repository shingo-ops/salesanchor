受領確認: card-bin0b-r8 を読んだ

# 便0-B 8回目 実装報告

| 手順 | 結果 |
|---|---|
| 1 作業場所 | `new-worktree.sh release/ai-assistant-bin0b --claude`（末尾の起動失敗は無視）→ `git switch -C … origin/release/ai-assistant-bin0b`。HEAD = origin = 2b7c88080 ○ |
| 2 Docker・完成品 | dockerd 起動・digest 固定で取得・`Hermes Agent v0.23.4` ○ |
| 3a〜3f 道具を直す | config.yaml（8 つの鍵）・setup_profiles.sh（部屋の config への写しを消し `cfg_key_lines`）・run_bin0.py（fixed-config・形の指示・K9・200/404 分け・k7count・k7judge・compact・configcheck・probe）・control/fake_ai.py・試験 18 件・README ○ |
| 3g 試験 | `18 passed`（out/raw/r8-3-pytest.txt）。1 回目は試験 18 の自作データの誤りで 1 件落ち、試験側を直して 2 回目で通った ○ |
| 4 頼みの文のファイル | `/tmp/bin0-texts.txt`（600）に 31 行（重複を除く。cases 23・k4 15・k8 の会社 A の文と決まり 2）。件数だけ raw/r8-4-texts.txt ○ |
| 5a〜5c | 鍵を README 1 番で作成・bin0-ctl の置き場・固定設定 c1/c3 を書き出し・起動・`/health` 200 ○（`cfg_key_lines=0` 3 部屋） |
| 5d 対照① | 作り物の AI の chat は 2 行届いたが、**`api_call_count` が 1**（○の形は 2）。**カードの決めで止まる** ×（out/measure-b-r8.md 表 C・raw/r8-5d-probe-c1.txt・raw/r8-5-fakelog-c1.txt） |
| 5e 対照② | `sid_by_script=1`・`get_status=200` ○ |
| 5g 対照③・6 以降 | 未実施（5d で止まったため） |
| 5h・後片付け | bin0-ctl 容器・volume・`/tmp/bin0-fixed-c1`/`-c3` の config.yaml と dir・`/tmp/bin0-secrets/` の鍵のファイル・`/tmp/bin0-texts.txt` を削除。bin0-run・bin0-data は作っていない（ログインは未実施・login-code.txt は触っていない） |

## 実装での補い（カードに細かい形が無かった所）

- `k9_ok`: 1 つでも違えば 0・違いが無く読めない会話があれば `-`・全部合えば 1 の順で決めた。
- `compact` の `/health` が 180 秒で 200 にならないときは `compact=HEALTH_TIMEOUT`・終了コード 6（カードに終了コードの定めが無かった）。
- `probe` の引数に `--keys-file` を足した（鍵の渡し方がカードに無かった）。
- k7count は `--texts` に空行があると全行に当たるため、空行がある・空なら終了コード 2。

## 止めた理由

対照①: 題づけを on にした固定設定で、作り物の AI への chat は 2 回届いた（`stream=True` が 1・`stream=None` が 1）。しかし会話の記録の `api_call_count` は 1 で、`input_tokens`・`output_tokens` は返事の usage と一致した。題づけの呼び出しは `api_call_count` に入らない。カード 5d の「`api_call_count` が 1 なら止まる」に当たった。

NEEDS_DECISION: 対照①（題づけの呼び出しは作り物の AI に 2 回届くが api_call_count は 1。K9 の足し方と題づけの数え方を設計役が決める）
