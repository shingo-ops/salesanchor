# 設計審査 — 第2.6版（審査役 architect・クラウド・読み取りだけ）

判定: **REVISE**

1. 第2.6版の主張は、b4・b5 の生の記録とほとんど数が合う。合格の線（基準の文）は変わっていない。ただし「下の鍵は全部、固定設定の 1 か所だけに置く」の「全部」に、部屋ごとの鍵など固定設定に置けない項目が入っている（R1）。
2. K7 の探し方が「grep -r」のままで、二値のファイルを読まない書き方（今の README 手順 8 の `-I`）を除けていない。これでは state.db を見落とし、合格と誤る（R2）。
3. K9 の比べ方は、後ろで回る処理を捕まえられるかを一度も確かめていない。確かめないまま合否に使っている（R3）。ここまで直せば、便0-B のカードは書ける。

対象: origin/release/ai-assistant-bin0b b0ed186bc の `docs/handoff/ai-assistant/design.md`（差分は e964c56b8..b0ed186bc・16 行足して 9 行消した）。行番号は b0ed186bc のもの。同じ会社の AI どうしの審査で、独立した第三者の審査ではない。

## 1. 主張ごとの ○×（行番号は design.md）

| 行 | 主張 | 判定 | 照らした記録 |
|---|---|---|---|
| :81 K2 | 形の指示を role system で係の部屋への頼みに付ける。届く位置は部屋の人格の後ろ | ○ | `docs/handoff/ai-assistant/bin0/out/source-check-b5.md:31-39`（末尾 22 文字・`\n\n` でつながる） |
| :81 K2 | やり直しは新しい会話番号で行う | ○ | `docs/handoff/ai-assistant/bin0/run_bin0.py:280-282`（やり直しのたびに uuid4 で番号を作る） |
| :117 | 7回目は請求書 24 件のうち 4 件しか形を通らなかった | ○ | `docs/handoff/ai-assistant/bin0/out/opus-check-b.md:8` |
| :117 | 今の秘書は `--json-schema` を渡している | ○ | `secretary-agent/server.mjs:17`・`:70` |
| :117 | `response_format`・`json_schema` は読まれない | ○ | `docs/handoff/ai-assistant/bin0/out/source-check-b.md:18`・`:88` |
| :117 | 送り先の行（719-726・2096-2097） | ○ | `docs/handoff/ai-assistant/bin0/out/source-check-b5.md:38` |
| :86 K7 | 後始末の順（消す→止める→別の容器で詰め直す→起こす）と、止めた直後の数を記録すること | ○ | `docs/handoff/ai-assistant/bin0/out/source-check-b5.md:81-97` |
| :86 K7 | 探し方「grep -r」 | × | R2 |
| :88 K9 | 欄の名前（`session.input_tokens`・`output_tokens`・`api_call_count`）が返事の usage と合う | ○ | `docs/handoff/ai-assistant/bin0/out/source-check-b5.md:43-45`・`docs/handoff/ai-assistant/bin0/out/raw/b13-10-q15-detail.txt:5-7` |
| :88 K9 | `/health/detailed` は送信を数えない | ○ | `docs/handoff/ai-assistant/bin0/out/source-check-b5.md:47` |
| :88 K9 | 比べ方が後ろの処理の分を捕まえられる | 未確認 | R3 |
| :101 | 起動する側の config は起動のたびに上書きされる（stage2-hook.sh:438-447） | ○ | `docs/handoff/ai-assistant/bin0/out/source-check-b4.md:30-36` |
| :101 | 固定設定 managed_scope.py の 31 行目 | ○ | `docs/handoff/ai-assistant/bin0/out/source-check-b4.md:51` |
| :101 | 固定設定は 3 部屋に効く | △ | `docs/handoff/ai-assistant/bin0/out/source-check-b5.md:64`。固定設定だけで効くと示せたのは title と logging の 2 つ。残り 4 つは部屋の config にも置いてあった（L2） |
| :101 | 「下の鍵は全部」を固定設定の 1 か所に置く | × | R1 |
| :102 | 頼みの先頭 80 字は INFO（1290 行目）。WARNING にすると目印 0 行 | ○ | `docs/handoff/ai-assistant/bin0/out/source-check-b4.md:64-66`・`:87`。3 部屋でもログの目印は 0（`docs/handoff/ai-assistant/bin0/out/source-check-b5.md:98`） |
| :103 | 題づけは新しい会話の最初の送信だけ。切ると AI への呼び出しは 1 回 | ○ | `docs/handoff/ai-assistant/bin0/out/source-check-b5.md:17-25`・`docs/handoff/ai-assistant/bin0/out/raw/b13-6-q13-recount-final.txt` |
| :114 | 失敗した頼みも保存される | ○ | `docs/handoff/ai-assistant/bin0/out/source-check-b2.md:20` |
| :114 | 止めた直後に目印 27 行。詰め直すと 0 行（1 回） | ○ | `docs/handoff/ai-assistant/bin0/out/source-check-b5.md:93-97` |
| :114 | `--force` は使わない（sessions_cmd.py の 1473 行目） | ○ | `docs/handoff/ai-assistant/bin0/out/source-check-b3.md:54` |
| :115 | 止めてから 200 まで 47.4 秒。b5 は 3 回の後にしか数えていない | ○ | `docs/handoff/ai-assistant/bin0/out/source-check-b5.md:85`・`:104` |
| :118 | `fallback_providers: []` は 3 部屋で表示を確かめた。動きは未確認 | ○ | `docs/handoff/ai-assistant/bin0/out/source-check-b5.md:60`・`:65` |

## 2. 合格の線を変えていないか

○。差分で変わったのは K2・K7・K9 の「検証方法」の列だけ。「合格の線」の列は e964c56b8 と同じ文字列（`git diff e964c56b8 b0ed186bc -- docs/handoff/ai-assistant/design.md` の :81・:86・:88 の行）。

## 3. 正本が 1 つか（同じ設定・形の表を 2 か所に置いていないか）

- 形の表: ○。:117 は「`secretary-agent/schema.json` をそのつど読む・写しは作らない」。`docs/handoff/ai-assistant/bin0/run_bin0.py:68-69` も同じ schema.json を読んでいる。
- 設定: ×（R1）。リポジトリに同じ鍵の表が 2 つある。
  - `docs/handoff/ai-assistant/bin0/config.yaml`。:3 に「同じ内容を /opt/data/config.yaml と各部屋の config に置く」とあり、`docs/handoff/ai-assistant/bin0/setup_profiles.sh:26`・`:35` が 4 か所へ写している。
  - `docs/handoff/ai-assistant/bin0/out/raw/b13-files/managed-final-config.yaml`
  - :101 の「部屋の config には書かない」を、今の台本はまだ守っていない。どちらを正本にするかも設計に書かれていない。

## 4. 直す点（R）

### R1 design.md :101 の「下の鍵は全部」を、固定設定に置く鍵の一覧に直す

- 事実:
  - :105 の `API_SERVER_KEY` は部屋ごとに別の値。今は各部屋の .env に置いている（`docs/handoff/ai-assistant/bin0/setup_profiles.sh:27-32`）。1 つのファイルには置けない。
  - :106 は頼みに付ける値で、設定ではない。
  - :104 の `gateway.multiplex_profiles` は b5 の固定設定に入っていない（`docs/handoff/ai-assistant/bin0/out/raw/b13-files/managed-final-config.yaml:1-14`）。固定設定に置いた形はまだ試していない。起動のときに gateway が起動する側の config へ書き込む（`docs/handoff/ai-assistant/bin0/out/source-check-b4.md:36`）。
  - b5 では、作り物の AI へ向ける `model:` を部屋の config に置いていた（`docs/handoff/ai-assistant/bin0/out/source-check-b5.md:8`）。本物を流すときの `model:` の置き場は書かれていない。
- 直し方（design.md :101）:
  - 固定設定に置く鍵を、名前で並べて書く。`logging.level`・`memory.*` の 2 つ・`platform_toolsets.api_server`・`auxiliary.background_review.enabled`・`auxiliary.title_generation.enabled`・`fallback_providers`。
  - 固定設定に置かない物と、その置き場を書く。`API_SERVER_KEY` は各部屋の .env、`multiplex_profiles` と `model:` は置き場を決める。
  - 正本のファイルを 1 つに決める（例: `docs/handoff/ai-assistant/bin0/config.yaml` を固定設定の中身に置き換える）。あわせて、次の便で `docs/handoff/ai-assistant/bin0/setup_profiles.sh:26`・`:35` の写しをやめ、`docs/handoff/ai-assistant/bin0/config.yaml:3` の注記を直す、と書く。

### R2 design.md :86（K7 の検証方法）の探し方を、二値のファイルも読む形に決める

- 事実:
  - 今の README 手順 8 は `grep -rIl`（`docs/handoff/ai-assistant/bin0/README.md:29`）。`-I` を付けると二値のファイルを読み飛ばす。
  - 7回目の実物の記録でも、`-I` 付きの探しは state.db・state.db-wal を 1 件も出さなかった。`-I` 無しでは 6 件出た（`docs/handoff/ai-assistant/bin0/out/raw/b8-k7.txt` の 1〜2 番目の区切り）。
  - b4・b5 の 0 行は `grep -a -c` で数えた（`docs/handoff/ai-assistant/bin0/out/raw/b13-files/count.sh:9`）。
- 直し方（design.md :86）: 「`-I` を付けず `grep -a` で、`/opt/data` 以下の全ファイルを、止めた容器とは別の使い捨て容器で数える。数えるのはファイルごとの行数」と決めて書く。README 手順 8 は次の便のカードで直す。

### R3 design.md :88（K9）に、比べ方が後ろの処理を捕まえられるかの対照を足す

- 事実:
  - 会話ごとの量を読んだのは b13-r3（final の固定設定・題づけを切った状態）だけ（`docs/handoff/ai-assistant/bin0/out/raw/b13-6-q13-recount-final.txt:1`・`docs/handoff/ai-assistant/bin0/out/raw/b13-10-q15-detail.txt`）。
  - 題づけの呼び出しが実際に起きた b13-4（base の固定設定）では、会話の量を読んでいない（`docs/handoff/ai-assistant/bin0/out/source-check-b5.md:19-21`）。
  - したがって、後ろの処理の呼び出しが `input_tokens`・`api_call_count` に入るかは記録に無い。入らない作りなら、K9 はいつでも○になり、合格の線「後ろで回る処理の分が 0」を測れない。
  - b5 の会話番号は、頼みの中身から作られた番号だった（`api-…`）。台本は頼みごとに自分で作った uuid を `X-Hermes-Session-Id` で渡す（`docs/handoff/ai-assistant/bin0/run_bin0.py:107`）。その番号で `GET …/api/sessions/<番号>` が 200 になるかも試していない。
- 直し方（design.md :88 か §5 の便0 の最初に確かめる項目）:
  - 便0-B の最初に、作り物の AI を使った対照を 1 回入れる。題づけを入れた固定設定で 1 回送り、作り物の AI に届いた回数と会話の `api_call_count`・量を比べる。
  - 後ろの処理の分が会話の数に入らなければ、K9 をこの方法では測らずに止め、設計役に戻す。
  - 台本が渡した uuid の番号で GET が 200 になることも同じ回に確かめる。404 なら止める。

## 5. 軽い指摘（L）

- L1 :115: `optimize -p <部屋>` の出力は 3 回とも `reconcile: profile=invoice` だった（`docs/handoff/ai-assistant/bin0/out/raw/b13-13-e2e-delete-stop-optimize-start.txt`）。部屋ごとに効くかは未確認のまま（`docs/handoff/ai-assistant/bin0/out/source-check-b5.md:104`）。各回の後に数えたとき、その部屋の行が減らなかったら止める、と書き足す。
- L2 :101: R1 で部屋の config から鍵を抜くと、memory・toolsets・background_review・fallback は固定設定だけで効くことになる。これはまだ実測していない（`docs/handoff/ai-assistant/bin0/out/source-check-b5.md:64-65`）。:101 の「流す前に `config get` で確かめ、違えば止める」がその守りになるので残す。動いているときに効くか（記録への書き込みや、余計な呼び出しが無いか）も、K9 の対照（R3）と一緒に見るとよい。
- L3 :88: 本物の AI で何を「一致」とするかが決まっていない。会話には `cache_read_tokens`・`reasoning_tokens` の欄もある（`docs/handoff/ai-assistant/bin0/out/source-check-b5.md:43`）。返事の `prompt_tokens` と `input_tokens` を比べるとき、キャッシュの分を足すかどうかを決めておく。作り物の AI ではどちらも 0 だった。
- L4: `docs/handoff/ai-assistant/bin0/run_bin0.py:136` は 404 も「消せた」と数える。一方、`docs/handoff/ai-assistant/bin0/out/opus-check-b.md:25` は「200 を返した 146/146」と書いている。R3 の GET を消す前に入れれば、番号の違いは 404 で見える。それでも記録の言い方は「200 か 404」にそろえるとよい。
- L5 :117: 決まった 1 文をどこに置くか（台本の定数 1 か所）と、`docs/handoff/ai-assistant/bin0/run_bin0.py:106` の本文に system を足すのは、カードで書けば足りる。まとめ役の頼みには付けないことも、カードに繰り返して書く。

## 6. 便0-B カード（run_bin0.py と起動の台本の直し）を書ける粒度か

R1〜R3 を直せば書ける。今のままで足りない手順は次のとおり。

1. 固定設定のファイルをどれにし、何を入れるか（R1）
2. setup_profiles.sh の写しをやめること（R1）
3. 起動に `-v <固定設定>:/etc/hermes:ro` を足すこと（`docs/handoff/ai-assistant/bin0/out/raw/b13-files/start.sh:6-8` の形。README 手順 3 には無い）
4. K7 の数え方（R2）
5. K9 の対照と、GET を消す前に行う順（R3）
6. 後始末を台本でやるか人がやるか（:115 の③〜⑤は、今の run_bin0.py に無い）

台本の側で足りない物は次の 3 つ。

- 消す前に会話の量を読む処理（`docs/handoff/ai-assistant/bin0/run_bin0.py:310-316` の前）
- 係の頼みに system を足す処理（`:106`）
- K7 の数えを止める前と後の 2 回とること

まだ確かめていないのに合否に使っている物は、R3（K9 の比べ方）だけ。L1（部屋ごとの詰め直し）と L2（固定設定だけで効くか）は止めどころを書けば足りる。
