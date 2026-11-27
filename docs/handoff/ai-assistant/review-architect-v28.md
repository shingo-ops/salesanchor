# 設計審査 — 第2.8版（審査役 architect・クラウド・読み取りだけ）

判定: **APPROVE**

1. 前回の R1〜R2・L1〜L5 は 7 件とも直っている。合格の線（基準の文）は変わっていない（K1〜K9 の 1〜2 列目は b0ed186bc・6a947ec4a・ffda2d93c で同じ文字列）。
2. 直しで新しく書いた主張（試し専用の固定設定・対照で送る頭・K7 の起点と増えた行の判定・30 秒の待ち・止めどころのまとめ）は、記録と食い違う所が無い。まだ試していない所は「まだ確かめていないこと」に入り、止めどころも書かれている。
3. 便0-B のカードは書ける。残りは軽い指摘（L1〜L5）だけで、カードの書き手が手順の中で足せる。

対象: origin/release/ai-assistant-bin0b ffda2d93c の `docs/handoff/ai-assistant/design.md`（第2.8版。差分は 6a947ec4a..ffda2d93c）。行番号は ffda2d93c のもの。根拠のファイルも ffda2d93c の中身で読んだ。同じ会社の AI どうしの審査で、独立した第三者の審査ではない。

## 1. 前回の指摘が直ったか

| 指摘 | 判定 | 直った行（design.md） | 確かめたこと |
|---|---|---|---|
| R1 対照で作り物の AI へ届く道 | ○ | :104・:105・:106・:126 | :104 で試し専用の固定設定を「正本の 8 つの鍵 ＋ `model:` の塊（`docs/handoff/ai-assistant/bin0/out/raw/b13-files/model.yaml:2-6`）、①だけ題づけを true」と決め、2 つ目の表を置かないと書いた。:105 で送る頭を `custom/fake-model` に決めた。:106 に「固定設定に置いた `model:` が効くか」「`model` と `provider` の両方の形で届くか」と、届かなければ止めて設計役に戻すことを足した。:126 の③を「8 つの鍵に `model:` だけを足した」形に直した |
| R2 K7 の起点 | ○ | :86 | 数える時点の先頭に「束を流す前（新しい置き場で 3 部屋を作って起こした後・起点）」を足し、判定を「起点からファイルごとに増えた行が 0」とした。起点に当たりの無いファイルに 1 行でも出たら×、当たりのあるファイルは起点と同じ行数なら○。読み方を便0 の判定のときに PO に知らせる、と書いた |
| L1 題づけは返事の後ろ | ○ | :124 | chat が 2 行そろってから GET・30 秒で 2 行にならなければ記録して止める |
| L2 対照は題づけだけ | ○ | :124 | K9 の記録に残す、と書いた |
| L3 multiplex の書き込みを記録 | ○ | :126 | 合否に使わない記録として足した |
| L4 3 行目の注記の鉤括弧 | ○ | :102 | 鉤括弧を外し、言い換えと分かる書き方にした。中身は `docs/handoff/ai-assistant/bin0/config.yaml:3`（/opt/data/config.yaml と各部屋）と合う |
| L5 台本が docker を呼ぶ場所 | ○ | :121 | 容器の外から `docker stop`・`docker run`・`docker start` を呼ぶ場所をカードに書く、と足した |

## 2. 直しで新しく書いた主張が記録と合うか

| 行 | 主張 | 判定 | 照らした記録 |
|---|---|---|---|
| :104 | `model:` の塊は b5 と同じ中身 | ○ | `docs/handoff/ai-assistant/bin0/out/raw/b13-files/model.yaml:2-6`（provider custom・base_url 127.0.0.1:18765・default fake-model・作り物の鍵） |
| :104 | 正本の 8 つの鍵を読む | △ | 今の `docs/handoff/ai-assistant/bin0/config.yaml` は 6 つの鍵（:6・:10・:14・:15・:20・:24）で、`logging.level`・`auxiliary.title_generation.enabled` が無い。:102 で次の便のカードで置き換えると決めているので食い違いではないが、順番の前提がある（L1） |
| :105 | 台本は `model` と `provider` を送る・b5 は `model` だけ | ○ | `docs/handoff/ai-assistant/bin0/run_bin0.py:106`・`docs/handoff/ai-assistant/bin0/out/raw/b13-files/body-plain.json:1`。`provider` を body から読む口があること（`docs/handoff/ai-assistant/bin0/out/source-check-b.md:17` の `_request_agent_overrides`）とも合う。`custom` を頼みで渡して効くかは記録に無く、:106 の未確認に入っている |
| :106 | 固定設定の `model:` は未確認・b5 は部屋の config と /opt/data/config.yaml | ○ | `docs/handoff/ai-assistant/bin0/out/source-check-b5.md:8`。固定設定の記録（`docs/handoff/ai-assistant/bin0/out/raw/b13-files/managed-final-config.yaml`）に `model:` は無い |
| :86 | 何も流していない置き場でも plugin.js に 1 件当たる | ○ | `docs/handoff/ai-assistant/bin0/out/source-check-b.md:67-70`・`:91`。7回目も全時点で出ている（`docs/handoff/ai-assistant/bin0/out/raw/b8-k7.txt:2-3`・`:10-11`・`:15`・`:19`） |
| :86 | b4・b5 の 0 行は部品に当たらない目印で数えた | ○ | `docs/handoff/ai-assistant/bin0/out/raw/b13-files/count.sh:9` |
| :86 | 増えた行で数える判定 | ○ | 部屋ごとの写しの件数が 1 件と 4 件の 2 通りある理由は未確認（`docs/handoff/ai-assistant/bin0/out/source-check-b.md:71`）だが、ファイルごとに起点と比べるのでこの差に左右されない |
| :124 | 題づけは返事の後ろで回る | ○ | `docs/handoff/ai-assistant/bin0/out/source-check-b5.md:23`（自前のエンドポイントでは turn の後ろに回す） |
| :124 | 30 秒待つ | ○（決めた値） | 記録の事実ではなく設計の決め。記録では題づけの chat は本の返事と同じ秒に届いた（`docs/handoff/ai-assistant/bin0/out/raw/b13-1-q13-fakelog-base.txt:11-12`・`docs/handoff/ai-assistant/bin0/out/raw/b13-4-q13-fakelog-base-repeat.txt:1-2`）ので、30 秒は足りる側 |
| :126 | 題づけを切ると 1 回の送信で 1 回 | ○ | `docs/handoff/ai-assistant/bin0/out/source-check-b5.md:25` |
| :126 | b4 Q9 で multiplex が書き込まれた | ○ | `docs/handoff/ai-assistant/bin0/out/source-check-b4.md:36` |
| :127 | 止めどころのまとめ | ○ | :106（届かない）・:124（会話の数に入らない・30 秒）・:125（404）・:126（③）と 1 対 1 で合う |

## 3. 合格の線を変えていないか

○。`git show <版>:docs/handoff/ai-assistant/design.md | grep "^| K[1-9]" | awk -F'|' '{print $2"|"$3}' | sha256sum` の値が b0ed186bc・6a947ec4a・ffda2d93c の 3 つとも `cf1263c94d74…`。変わったのは K7 の「検証方法」の列（:86）と §5（:102・:104-106・:121・:124・:126-127）と §10（:184）と頭の状態の行だけ。:86 の「流す前から部品にある文字は数えない」は読み方の決めで、基準の文は同じ。PO に知らせると書いてある。

## 4. 直す点（R）

無し。

## 5. 軽い指摘（L）

- L1 :102・:104: 試し専用の固定設定は「正本の 8 つの鍵」を読んで作るが、今の正本 `docs/handoff/ai-assistant/bin0/config.yaml` は 6 つの鍵（`logging.level` と `auxiliary.title_generation.enabled` が無い）。カードでは :102 の正本の置き換えを先に行い、台本は正本を読んだときに 8 つの鍵がそろっていなければ止める、と書くとよい。
- L2 :86・:121-127: 対照と本物の束が同じ置き場（`/opt/data` の volume）を使うかが書かれていない。起点は「新しい置き場で 3 部屋を作って起こした後」なので、対照は別の使い捨ての volume で行い、本物の束は新しい volume で起点から始める、とカードに書くとよい（対照で束の文を送らない限り K7 の数は変わらないが、置き場を分けたほうが起点の意味がはっきりする）。
- L3 :124: 題づけが新しい会話の最初の送信で走ると分かったのは、会話の番号を Hermes が作った形（`docs/handoff/ai-assistant/bin0/out/source-check-b5.md:21`・`docs/handoff/ai-assistant/bin0/out/raw/b13-1-q13-send-base.txt:3`）での記録。台本が自分の番号を付けて送った形（`docs/handoff/ai-assistant/bin0/run_bin0.py:107`）で題づけが走るかは記録に無い。30 秒で止まったときは、番号を台本が付けたことを記録に残すとよい。
- L4 :124・:126: 作り物の AI は容器の中の 127.0.0.1:18765 で動き、記録は容器の中の /tmp/fake.log（`docs/handoff/ai-assistant/bin0/out/raw/b13-files/fake_ai.py:2`・`:12`）。b5 の起動は /tmp を tmpfs にしている（`docs/handoff/ai-assistant/bin0/out/raw/b13-files/start.sh:7`）ので、止めると記録は消える。①・③の回数は止める前に `docker exec` で読む、と書くとよい。起動に作り物の AI の置き場を差し込み、容器の中で動かす形（`docs/handoff/ai-assistant/bin0/out/raw/b13-files/start.sh:8-9`）もカードに書く。
- L5 :105: `provider: custom` を頼みで渡したときに Hermes がどう扱うか（固定設定の `model.provider` と同じなら効くか、無視されるか）は記録に無い。:106 の止めどころで足りるが、対照の記録に「返事の model と、作り物の AI に届いた model の値」を残すと、§5「頭の渡し方」の①の確かめにも使える。

## 6. 便0-B カードを書ける粒度か

書ける。前回 §6 の 6 つの手順と、前回足りなかった 2 つは次のとおり埋まった。

| 手順 | 判定 | 行 |
|---|---|---|
| 1 固定設定のファイルと中身（本物・試し専用） | ○（正本の置き換えを先に。L1） | :101-102・:104 |
| 2 setup_profiles.sh の写しをやめる | ○ | :102 |
| 3 起動に `-v <固定設定>:/etc/hermes:ro` | ○ | :101 |
| 4 K7 の数え方・起点・判定 | ○ | :86 |
| 5 K9 の対照（送る頭・待ち・3 つの確かめ）と止めどころ | ○（記録の読み方。L4） | :105・:124-127 |
| 6 後始末を台本で・docker を呼ぶ場所 | ○ | :121 |

止めどころは、作り物の AI へ届かない（:106・:127）・①の回数が会話に入らない（:124）・30 秒で 2 行にならない（:124）・②が 404（:125）・③が違う（:126）・`config get` が違う（:107）・ある部屋を詰め直しても行が減らない（:121）・起点に当たりの無いファイルに行が出る／当たりのあるファイルの行が増える（:86）・本物の AI で量が合わない（:88）。カードの書き手がその場で決める所は残っていない。
