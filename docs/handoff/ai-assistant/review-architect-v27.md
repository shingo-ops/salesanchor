# 設計審査 — 第2.7版（審査役 architect・クラウド・読み取りだけ）

判定: **REVISE**

1. 前回の R1〜R3・L1〜L5 は 8 件とも直っている。合格の線（基準の文）は変わっていない（K1〜K9 の「基準」「合格の線」の 2 列は b0ed186bc と 6a947ec4a で同じ文字列）。
2. ただし、R3 の直しで足した「便0-B の最初の対照」の③は、作り物の AI へ頼みが届く道が書かれていない。作り物の AI へ向ける `model:` を固定設定に置く形は、まだ一度も試していない（R1）。
3. K7 の探しを全ファイルの `grep -a` に決めたことで、何も流す前から完成品の部品のファイルに束の短い文が 1 件当たる。このままでは K7 はいつも×になる（R2）。この 2 つを直せば、便0-B のカードは書ける。

対象: origin/release/ai-assistant-bin0b 6a947ec4a の `docs/handoff/ai-assistant/design.md`（第2.7版。差分は b0ed186bc..6a947ec4a）。行番号は 6a947ec4a のもの。同じ会社の AI どうしの審査で、独立した第三者の審査ではない。

## 1. 前回の指摘が直ったか

| 指摘 | 判定 | 直った行（design.md） | 確かめたこと |
|---|---|---|---|
| R1 固定設定に置く鍵の一覧・置かない物・正本 | ○ | :101-104 | 8 つの鍵を名前で並べた。b5 の固定設定の 7 つ（`docs/handoff/ai-assistant/bin0/out/raw/b13-files/managed-final-config.yaml:2-14`）に `gateway.multiplex_profiles` を足した数で合う。正本を `docs/handoff/ai-assistant/bin0/config.yaml` に決め、写しをやめる行（`docs/handoff/ai-assistant/bin0/setup_profiles.sh:26`・`:35`）も合う。ただし `model:` の置き場に新しい穴がある（R1） |
| R2 K7 の探し方 | ○ | :86 | `-I` 付きは state.db・state.db-wal を出さず、`-I` 無しは 3 部屋の state.db と state.db-wal で 6 件出した（`docs/handoff/ai-assistant/bin0/out/raw/b8-k7.txt:1-22`）。数え方は `docs/handoff/ai-assistant/bin0/out/raw/b13-files/count.sh:5-14`（使い捨て容器・`--network none`・`grep -a -c`・ファイルごと）と同じ形。ただし起点の当たりを扱っていない（R2） |
| R3 K9 の対照 | ○ | :88・:121-124 | 対照①（題づけを入れて回数と会話の数を比べる）と②（台本の番号で GET が 200）を足し、捕まえられなければ止めて設計役に戻すと書いた。③に穴がある（R1） |
| L1 部屋ごとの詰め直し | ○ | :119 | `reconcile: profile=invoice` が 3 回とも出たこと（`docs/handoff/ai-assistant/bin0/out/source-check-b5.md:104`）と、その部屋の行が減らなければ止める、を書いた |
| L2 固定設定だけで効くか | ○ | :104・:105 | まだ確かめていないことに書き、`config get` で違えば止める、を残した |
| L3 本物の AI で何を一致とするか | ○ | :88 | `cache_read_tokens`・`reasoning_tokens` を記録して止め、設計役が決める、と書いた（欄は `docs/handoff/ai-assistant/bin0/out/source-check-b5.md:43`） |
| L4 消す口の答えの数え方 | ○ | :120 | `docs/handoff/ai-assistant/bin0/run_bin0.py:136` が 200 と 404 をどちらも「消せた」と数えることと合う |
| L5 決まった 1 文の置き場 | ○ | :126 | 台本の定数 1 か所・`docs/handoff/ai-assistant/bin0/run_bin0.py:106` の messages の先頭・まとめ役には付けない、を書いた |

## 2. 直しで新しく書いた主張が記録と合うか

| 行 | 主張 | 判定 | 照らした記録 |
|---|---|---|---|
| :101 | 8 つの鍵の一覧 | ○ | `docs/handoff/ai-assistant/bin0/out/raw/b13-files/managed-final-config.yaml:2-14`（7 つ）と `docs/handoff/ai-assistant/bin0/config.yaml:6`（multiplex） |
| :101 | 起動に `-v <固定設定>:/etc/hermes:ro` を足す | ○ | `docs/handoff/ai-assistant/bin0/out/raw/b13-files/start.sh:8` |
| :101 | /opt/data/config.yaml にこの鍵を書かない | △ | Hermes 自身が起動のときに `gateway.multiplex_profiles: true` を書き込む（`docs/handoff/ai-assistant/bin0/out/source-check-b4.md:36`）。固定設定に置いた後も書くかは未確認（L3） |
| :102 | 正本は `docs/handoff/ai-assistant/bin0/config.yaml`。写しは setup_profiles.sh の 26・35 行目 | ○ | `docs/handoff/ai-assistant/bin0/setup_profiles.sh:26`・`:35` |
| :102 | 3 行目の注記 | △ | 中身は合う（`docs/handoff/ai-assistant/bin0/config.yaml:3` は /opt/data/config.yaml と各部屋の計 4 か所）。ただし鉤括弧の中は原文ではなく言い換え（L4） |
| :103 | `API_SERVER_KEY` は各部屋の .env | ○ | `docs/handoff/ai-assistant/bin0/setup_profiles.sh:27-32` |
| :103 | `model`・`provider` は頼みごとに付ける | ○ | `docs/handoff/ai-assistant/bin0/run_bin0.py:106` |
| :103 | 作り物の AI へ向ける `model:` は試し専用の固定設定に入れる | 未確認 | b5 は `model:` を 3 部屋の config と /opt/data/config.yaml に置いた（`docs/handoff/ai-assistant/bin0/out/source-check-b5.md:8`）。固定設定に置いた形は試していない。:104 の「まだ確かめていないこと」にも入っていない（R1） |
| :104 | multiplex を固定設定に置いた形は b5 で試していない・部屋の config にも鍵があった | ○ | `docs/handoff/ai-assistant/bin0/out/raw/b13-files/managed-final-config.yaml:1-14`・`docs/handoff/ai-assistant/bin0/out/source-check-b5.md:64-65` |
| :86 | `grep -a` の数え方・`-I` の件数 | ○ | 上の表 R2 の行 |
| :86 | 全ファイルで 0 件を数える | × | 何も流していない新しい置き場でも、束の文 1 件（5 字の短い文）が完成品の skills の `plugin.js` 1 ファイルに当たる（`docs/handoff/ai-assistant/bin0/out/source-check-b.md:67-70`・`:91`）。7回目も全時点で `plugin.js` が出ている（`docs/handoff/ai-assistant/bin0/out/raw/b8-k7.txt:2-3`・`:10-11`）（R2） |
| :119 | 47.4 秒・`reconcile: profile=invoice` | ○ | `docs/handoff/ai-assistant/bin0/out/source-check-b5.md:85`・`:104` |
| :121 | 作り物の AI は `docs/handoff/ai-assistant/bin0/out/raw/b13-files/fake_ai.py` | ○ | ファイルは在る。送信ごとに fake.log へ 1 行（`docs/handoff/ai-assistant/bin0/out/source-check-b5.md:10`） |
| :122 | 対照①: 題づけを入れると届く回数が 2 になる | ○ | `docs/handoff/ai-assistant/bin0/out/source-check-b5.md:19-20`。ただし題づけは返事の後ろに回る（L1） |
| :123 | 対照②: 台本は自分の番号を `X-Hermes-Session-Id` で渡す | ○ | `docs/handoff/ai-assistant/bin0/run_bin0.py:107` |
| :124 | 対照③: 本物の束と同じ固定設定で作り物の AI へ 1 回届く | × | 本物の束の固定設定には `model:` を入れない（:103）。部屋の config にも置かない。これでは作り物の AI へ向く設定がどこにも無い（R1） |

## 3. 合格の線を変えていないか

○。K1〜K9 の行の 1〜2 列目（基準・合格の線）を b0ed186bc と 6a947ec4a で取り出して比べ、同じだった（`git show <版>:docs/handoff/ai-assistant/design.md | grep "^| K[1-9]" | awk -F'|' '{print $2"|"$3}' | sha256sum` の値が 2 つとも `cf1263c9…`）。変わったのは K7・K9 の「検証方法」の列と §5 だけ。

## 4. 直す点（R）

### R1 design.md :103・:104・:121-124 — 対照の試しで作り物の AI へ届く道を決める

- 事実:
  - b5 は `model:`（provider custom・base_url・default fake-model）を 3 部屋の config と /opt/data/config.yaml に置いた（`docs/handoff/ai-assistant/bin0/out/source-check-b5.md:8`・中身は `docs/handoff/ai-assistant/bin0/out/raw/b13-files/model.yaml:2-6`）。固定設定（`docs/handoff/ai-assistant/bin0/out/raw/b13-files/managed-final-config.yaml`）には入っていない。
  - b5 の頼みは `model` だけを送った（`docs/handoff/ai-assistant/bin0/out/raw/b13-files/body-plain.json`）。台本は `model` と `provider` を両方送る（`docs/handoff/ai-assistant/bin0/run_bin0.py:106`）。台本の形で作り物の AI へ届くかは試していない。
  - :103 は作り物用の `model:` を「試し専用の固定設定」に入れると決めた。:124 の③は「本物の束と同じ固定設定」で作り物の AI へ 1 回届くことを確かめると書いた。本物の束の固定設定には `model:` が無いので、③は書いたとおりには流せない。
  - 対照②は台本の番号で確かめるので、対照は台本（または台本と同じ頼みの形）で送ることになる。そのとき `provider` に何を付けるかが書かれていない。
- 直し方（design.md）:
  - :103 に「試し専用の固定設定 = 正本の 8 つの鍵 ＋ 作り物の AI へ向ける `model:` の塊。①だけ `auxiliary.title_generation.enabled: true` に変える」と書く。置き場は正本の横に差分だけ置く形にし、8 つの鍵を写した 2 つ目の表にしない。
  - :124 の③を「本物の束と同じ 8 つの鍵（題づけ切り・multiplex 入り・部屋の config に鍵なし）に、作り物用の `model:` だけを足した試し専用の固定設定で」と直す。
  - :104 の「まだ確かめていないこと」に「固定設定に置いた `model:` が効くか」と「台本の頼みの形（`model` と `provider`）で作り物の AI へ届くか」を足す。対照のときに作り物の AI へ 1 回も届かなければ止めて設計役に戻す、と書く。そのとき b5 の形（部屋の config に `model:`）に戻すかは設計役が決める。
  - 対照で台本が付ける `provider` の値（または対照では `model` だけを送るか）を決めて書く。

### R2 design.md :86（K7 の検証方法）— 流す前からある当たり（起点）の扱いを決める

- 事実:
  - 何も流していない新しい置き場で、束の文 23 件のうち 1 件（5 字）が、完成品の skills の skills/autonomous-ai-agents/hermes-agent/templates/plugin.js に当たる（`docs/handoff/ai-assistant/bin0/out/source-check-b.md:67-70`・`:91`）。7回目の記録でも `plugin.js` は `-I` の有無にかかわらず出ている（`docs/handoff/ai-assistant/bin0/out/raw/b8-k7.txt:2-3`・`:10-11`）。部屋ごとの写しにも当たり、件数は 1 件と 4 件の 2 通りの記録があって差の理由は未確認（`docs/handoff/ai-assistant/bin0/out/source-check-b.md:71`）。
  - :86 は `/opt/data` 以下の全ファイルで頼みの文を数えると決めた。起点の当たりをどう扱うかは書いていない。このままでは後始末が全部効いても K7 は×になる。カードの書き手か実行役が、外すファイルをその場で決めることになる。
  - b4・b5 の 0 行は、部品に当たらない目印（MARK7735・SYS7735）で数えた（`docs/handoff/ai-assistant/bin0/out/raw/b13-files/count.sh:9`）。束の本物の文で 0 を数えたことはまだ無い。
- 直し方（design.md :86）:
  - 数える時点に「束を流す前（新しい置き場で 3 部屋を作り、起こした後）」を足し、同じ数え方でファイルごとの行数を記録する（起点）。
  - 判定は「起点からファイルごとに増えた行が 0」で数える、と書く。起点に当たりの無いファイルに 1 行でも出たら×。起点に当たりのあるファイルは、行数が起点と同じなら○とする。
  - 合格の線（基準の文）は変えない。合格の線の読み方（流す前から部品にある文字は「流した頼みの文」に数えない）に当たるので、§10 の記録か便0 の判定のときに PO に一言で知らせる、と書くとよい。

## 5. 軽い指摘（L）

- L1 :122: 自前のエンドポイントでは、題づけは返事の後ろに回す作りだった（`docs/handoff/ai-assistant/bin0/out/source-check-b5.md:23`・完成品の中 agent/title_generator.py の 969-970 行目）。返事の直後に GET すると、題づけが届く前の数を読むおそれがある。「fake.log に chat が 2 行そろってから GET する。決めた秒数を待っても 2 行にならなければ、その旨を記録して止める」と書くとよい。
- L2 :122: 対照①が確かめるのは題づけ 1 種類だけ。background_review・memory の分を会話の数が捕まえるかは、この対照では分からない（`docs/handoff/ai-assistant/bin0/out/source-check-b5.md:65`）。K9 の記録に「対照は題づけだけで確かめた」と残す、と書くとよい。
- L3 :101: Hermes は起動のときに /opt/data/config.yaml へ `gateway.multiplex_profiles: true` を書き込む（`docs/handoff/ai-assistant/bin0/out/source-check-b4.md:36`）。固定設定に置いた後もこの書き込みが起きるかを、対照③のときに記録するとよい（合否には使わない）。
- L4 :102: 鉤括弧の中を `docs/handoff/ai-assistant/bin0/config.yaml:3` の原文にするか、鉤括弧を外して言い換えと分かる書き方にする。
- L5 :119: ①〜⑤を台本の中で行うと決めたので、台本が `docker stop`・`docker run` を呼ぶことになる。今の `docs/handoff/ai-assistant/bin0/run_bin0.py` は HTTP だけで docker を呼んでいない。カードに「台本が docker を呼ぶ場所（容器の外）」を書けば足りる。

## 6. 便0-B カードを書ける粒度か

R1・R2 を直せば書ける。前回 §6 で足りないとした 6 つの手順は、次のとおり埋まった。

| 前回の手順 | 判定 | 行 |
|---|---|---|
| 1 固定設定のファイルと中身 | ○（作り物用の `model:` を除く。R1） | :101-102 |
| 2 setup_profiles.sh の写しをやめる | ○ | :102 |
| 3 起動に `-v <固定設定>:/etc/hermes:ro` | ○ | :101 |
| 4 K7 の数え方 | ○（起点の扱いを除く。R2） | :86 |
| 5 K9 の対照と、GET を消す前に行う順 | ○（③を除く。R1） | :119・:121-124 |
| 6 後始末を台本でやるか人がやるか | ○（台本） | :119 |

止めどころは次の 6 つが書かれている。①の回数が会話に入らない（:122）・②が 404（:123）・③が違う（:124）・`config get` が違う（:105）・ある部屋を詰め直しても行が減らない（:119）・本物の AI で量が合わない（:88）。R1 で「作り物の AI へ届かない」、R2 で「起点に当たりの無いファイルに行が出る」を足せば、カードの書き手がその場で決める所は残らない。
