# llm_compare — 解析AIを Claude Haiku・Sonnet に替えたときの精度比べの道具

設計: docs/handoff/llm-compare-claude/design.md（§3 条件、§5 道具、§13 実装カード）。試験用の道具だけ。本番には配られず、CI では走らない。
社外秘: 仕入元の文字列・答え・投稿 id はこのフォルダに置かない（置き場は ~/CC報告ファイル-keep/llm-compare-20261030/）。

## ファイル
| ファイル | 役割 | どこで動く |
|---|---|---|
| capture_prompt_ab.py | prompt_ab の `call_gemini_raw_copy_v8`（prompt_ab 側の名前）を包み、成功後だけ渡した文字列を保存 | 本番サーバーの別の箱 |
| vps_run_gemini.sh | 上の起動台本（dry あり。健康診断の上書き・`-e PYTHONPATH=/app`） | PO が ! で |
| vps_convert.sh | 3種の JSONL を1回の起動でまとめて fhd_snapshot.py convert | PO が ! で |
| fetch_results.sh | 取り寄せと照合（成功行数 = 文字列数、repeat 間の同一、指示書 sha256） | PO が ! で |
| run_claude.py | claude CLI（サブスク）で同じ文字列を1件ずつ解く。異常で即停止 | 手元の Mac |
| split_snapshot.py | convert の出力を (tag, repeat) ごと・投稿ごとの TSV に分ける | 手元 |
| summarize.py | score_v102.py の出力・使用量・時間・費用・合否を1枚の表に | 手元 |
| export_schema.py / v102_response_schema.json | V102_RESPONSE_SCHEMA の機械書き出しと一致確認 | 手元 |
| fhd_snapshot.py | 変換器の写し（下の sha256） | 本番サーバーの worker（stdin 渡し） |
| test_llm_compare.py | 単体試験 | 手元 |

## 写しの記録
- fhd_snapshot.py: 元 ~/CC報告ファイル-keep/accuracy-gold-20261020/box-error189/T5T6/heading-fix/test/validate/fhd_snapshot.py をそのまま複製。sha256 = `cd63545e1f5fa8a23420385d57285a60805dfa80fe01e11cef0f5916bfbe6987`
- v102_response_schema.json: `python3 -B scripts/accuracy/llm_compare/export_schema.py` で backend/app/services/gemini_raw_copy_v101.py の V102_RESPONSE_SCHEMA から書き出し。sha256 = `8b89e31ed71860de5878223550d6c4648dd273815441db64333c5daeb3ca9c46`
  - 型の表記の変換: なし。定義が最初から JSON Schema の小文字表記（"type": "object" など）で、そのまま書き出した。`--check` で定義との一致を確かめられる。

## 試験（手元）
`python3 -B -W ignore scripts/accuracy/llm_compare/test_llm_compare.py -v`（リポジトリの根から）
- split / summarize の試験は手元の ~/CC報告ファイル-keep/accuracy-gold-20261020/ の sample/snapshot（f_ct の写し100ファイル）・gold/gold_v1.tsv を読む（無ければ skip）。summarize の突き合わせ先は score/run1-r1/result.tsv。
- claude は偽の命令に差し替える。本物の claude・Gemini・本番には接続しない。

## run_claude.py の決まり
- 対象は JSONL の repeat=1 の成功行。成功行の並び N 番目 = index の通し番号 N。続きの test-id があるときは `--pair JSONL:INDEX` を足す。
- 実施前: ANTHROPIC_API_KEY・ANTHROPIC_AUTH_TOKEN が空であること、`claude --version`・`claude auth status` のログイン種別の欄（loggedIn・authMethod・apiProvider・subscriptionType とサブスクか否か）だけを OUT.preflight.json に記録する。メール等の個人の値は保存しない。
- 異常（rc≠0、is_error≠false、時間切れ 600 秒、modelUsage が指定モデル1種だけでない、呼び出しが1回でない（iterations≠1件）・num_turns が決まりと違う（structured_output ありで2、なしで1）、答えが空、文字列の sha256 不一致）で即停止し OUT.stop.txt に時刻と件数。待って再開しない。続きは人が `--resume`。
- `--bare` は使わない。答えの欄は `--response-field auto`（structured_output があればそれ、なければ result）。実際にどちらに入るかは設計 §6 手順（４）の試しの1件（`--limit 1`）で確かめ、結果を記録する。

## 後片付けと補足
- 試験が終わったら、PO が本番サーバーの `/home/ubuntu/fhd-test/llmcmp/` を消す（社外秘の文字列が残るため）。`!` で実行する。AI は実行しない。削除の一行は、PO が内容を確かめてから自分で書く。
- vps_convert.sh は、動いている worker の中で JSONL を 4 本変換する（参照の台本より 1 本多い）。
- 費用の上限は llmcmp-* 全体で 5.00 USD（test-id ごとではない）。残りが 1.00 USD 未満なら vps_run_gemini.sh は止まる。使い方は `vps_run_gemini.sh <test-id> <runs> run|dry <origin/main の40桁sha>`（第3引数は run か dry のどちらかだけ。それ以外は止まる）。環境変数 RD に読み取り専用鍵の rd.sh を渡す。
- summarize.py の --usage は `LABEL=JSONL:repeat` も受ける（Gemini は repeat ごとに別の列）。
