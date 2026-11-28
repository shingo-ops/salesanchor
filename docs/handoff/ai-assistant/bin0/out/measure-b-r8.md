# 便0-B 8回目 測りの表（途中で止まった: 対照①）

カード: [../../card-bin0b-r8.md](../../card-bin0b-r8.md)。手順 5 の対照①で止まったため、表 4（K1〜K9）は測っていない（手順 6 以降は未実施）。

## 表 C: 最初の対照（作り物の AI・ログインなし・使い捨ての置き場 bin0-ctl）

| # | 流した命令（鍵は伏せる） | 返った数字・名前 | ○× |
|---|---|---|---|
| 5a | `setup_profiles.sh bin0-ctl` | 3 部屋とも `cfg_key_lines=0`（部屋の config.yaml に 8 つの鍵の名前が 0 行）・`prompt_txt_sha256=913a71d5cbbbf064c5d2e76817062b585da8f90709e18fd91997829c9be53f2e`（raw/r8-5a-setup.txt） | ○ |
| 5b | `--set fixed-config --out /tmp/bin0-fixed-c1 --test-model <model.yaml> --title-on` と `--out /tmp/bin0-fixed-c3 --test-model <model.yaml>` | `keys=8 test_model=1 title_on=1` / `keys=8 test_model=1 title_on=0`（raw/r8-5b-fixed.txt） | ○ |
| 5c | 守りの形で `bin0-ctl` を起動（固定設定 c1・control を `/fake` に ro・`-p 127.0.0.1:8643:8642`）→ 作り物の AI を `docker exec -d` で起動 | `/health` 200 | ○ |
| 5d 対照① | `--set probe --base-url http://127.0.0.1:8643 --room invoice --model custom/fake-model --text こんにちは --container bin0-ctl --wait-fake-lines 2` | 作り物の AI の chat 2 行・**`api_call_count=1`**（`input_tokens=11`・`output_tokens=7`）（raw/r8-5d-probe-c1.txt） | **×**（○の形は api_call_count が 2） |
| 5e 対照② | 5d の出力 | `sid_by_script=1`・`get_status=200` | ○ |
| 5f | `docker exec bin0-ctl cat /tmp/fake.log`（raw/r8-5-fakelog-c1.txt） | chat の行 2（うち `stream=True` が 1・`stream=None` が 1）・どちらも受けた `model=fake-model`・返事の `reply_model=fake-model`・`usage_in=11`・`usage_out=7` | 記録 |
| 5g 対照③ | （未実施） | — | 未実施 |
| 5h | 後片付け | `bin0-ctl` 容器・volume を削除、`/tmp/bin0-fixed-c1`・`-c3` の config.yaml を 1 つずつ rm して rmdir | ○ |

## 読み（事実だけ）

- 題づけを on にした固定設定（c1）で、作り物の AI へ chat が 2 回届いた（1 回は `stream=True`）。つまり題づけの呼び出しは実際に増えた。
- ただし会話の記録（`GET /p/invoice/api/sessions/<番号>`）の `api_call_count` は 1 で、`input_tokens`・`output_tokens` は返事の usage（11・7）と一致した。題づけの呼び出しは会話の `api_call_count` に入らなかった。
- 手順 5d の ○ の形（`api_call_count` が 2）と合わないため、カードの決めどおり止めた。K9 の足し方・題づけの数え方は設計役の判断が要る。
