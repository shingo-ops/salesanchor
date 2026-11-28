# 設計審査 — 第2.9版（審査役 architect・クラウド・読み取りだけ）

判定: **REVISE**

1. K9 の主の判定を `session_model_usage` に替えた根拠は、元ソース 8fc03744 の行と合う（設計が引いた行番号 9 か所はすべて言っているとおり）。合格の線（基準の文）も変わっていない。
2. ただし、本体の呼び出しの行（`task` 空）が state.db に書かれる時刻が返事の前か後かを、設計は決めていない。元ソースでは、この行は待ち行列に積まれ、後でまとめて書かれる。返事の直後に読むと 0 になり、「×」と誤って判定するおそれがある（R1）。
3. ほかの点（○の形・30 回の読み直し・読み取り専用の読み方・schema_lead・止めどころ）は、カードの書き手が手順の中で足せる軽い指摘（L1〜L6）。R1 を直せば 9 回目のカードは書ける。

対象: origin/release/ai-assistant-bin0b 9fc010eea の docs/handoff/ai-assistant/design.md（第2.9版。差分 2b7c88080..9fc010eea は 16 ファイル・825 行足し・46 行消し。全部読んだ）。あわせて docs/handoff/ai-assistant/bin0/out/opus-check-r8.md・docs/handoff/ai-assistant/review-architect-v28.md・docs/handoff/ai-assistant/card-bin0b-r8.md・docs/handoff/ai-assistant/bin0/out/raw/ の r8- で始まる 6 つも読んだ。行番号は 9fc010eea のもの。この文書の docs/ で始まるパスはすべて release/ai-assistant-bin0b の 9fc010eea の中のファイルで、この枝（main 起点）には無い物や中身の違う物があるので、バッククォートを付けていない。同じ会社の AI どうしの審査で、独立した第三者の審査ではない。

元ソースの読み方（事実）: カードの指示は `gh api` の contents（ref を指定）だったが、この場では `gh` の認証が通らず、GitHub の API も 403 で断られた（NousResearch/hermes-agent はこのセッションの範囲外）。代わりに、公開のリポジトリから同じ番号 8fc0374447313e276f6b9a2764bfc750190c966a を git fetch で取り、`git rev-parse FETCH_HEAD` がこの番号と一致することを確かめてから、`git show FETCH_HEAD:<path>` で読んだ。中身は番号で決まるので、contents で読んだ場合と同じになる。写しはリポジトリに置いていない。下の元ソースのパスは hermes-agent の中のパスで、この repo の中には無い。

## 1. K9 の根拠を元ソースで確かめた（行番号ごと）

| 設計が言っていること（design.md の行） | 元ソース 8fc03744 の行 | 判定 |
|---|---|---|
| 後ろの処理の量は、会話の数に足されない（:88） | persistence/conversation/usage.py:3「auxiliary usage kept off the session counters」。:154「The session counters, cost fields and recent route are untouched」 | ○ |
| 後ろの処理は表 `session_model_usage` に `task` 名つきで書かれる（:88） | persistence/sqlite/conversation/_store/usage.py:238-271（record_auxiliary_usage）。:244-251 に vision・compression・title generation・background_review が挙がっている。:270 で _record_model_usage を呼び、:230-235 で表に書く | ○ |
| background_review も同じ表に書かれる（:124） | 同 :250-251「Background-review forks record an aggregate of N fork API calls in one write with task='background_review'」 | ○（元ソースを読んだだけで、実物では動かしていない、と設計も書いている） |
| 本体の呼び出しも同じ表に `task` 空で書かれる（:88） | 同 :51-59（表に書く SQL。主キーに task がある）。:220-222「'' (empty) is the main agent loop」。:158・:180-181 で、足していく形（absolute でない）のときだけ書く。本体の呼び出しは agent/turn_usage.py:334-352 で `api_call_count=1` の差分を待ち行列に積む。persistence/conversation/usage.py:65-78 の UsageDelta には absolute の欄が無い。8fc03744 の中で `absolute=True` を渡す所は、試験を除くと 0 件（git grep で確かめた） | ○ |
| 表の列は model・task・数だけで、文は入らない（:125） | _store/usage.py:51-57 の列。persistence/sqlite/_schema.py:128-148 の作り。billing_provider・billing_base_url・billing_mode・費用・時刻もあるが、会話の文や題の文の列は無い | ○ |
| 題づけは別の糸から書かれる（:124） | agent/title_generator.py:27-31（daemon の糸が量を会話に付ける）。:822-824（set_accounting_context で task='title_generation' として書く） | ○ |
| 題づけの量は、作り物の AI の返事で記録される | agent/auxiliary_client.py:6596-6611（記録は返事の形を確かめる前に行う。つまり題が JSON でなくても記録される）。agent/aux_accounting.py:117-129（usage が無いとき・すべて 0 のときは記録しない）。作り物の AI は stream でない返事にも usage 11・7 を付けている（docs/handoff/ai-assistant/bin0/control/fake_ai.py:74・`:84-87`） | ○（○の形が成り立つ前提はそろっている） |

設計が引いていない行で、K9 に関わるもの（事実）:

- agent/aux_accounting.py:104-115: 後ろの処理の量の記録は「best-effort」。会話の番号がその糸に渡っていないとき（ctx が None）と、moa の 2 種類（:25）は書かない。auxiliary_client.py:6596-6597 によると、記録の入口を通るのは stream でない返事だけ。→ L1
- persistence/conversation/usage.py:12・_store/usage.py:113-114: `task` が空でない行には、会話の数に**入る**本体寄りの呼び出し（例: voice_chat）もある。「`task` が空でない＝後ろの処理」とは限らない。→ L2
- persistence/conversation/usage.py:5・agent/turn_usage.py:324-327: 本体の呼び出しの量は待ち行列に積まれるだけで、その場では書かれない（「Enqueued, not written」）。書かれるのは agent/session_persistence.py:529-533 の flush_usage。HTTP の口で、返事を返す前にこれが流れるかは追い切れていない（未確認）。usage.py:5 には、イベントループの糸から呼ばれた SessionRepository.get は待ち行列を待たず、書き終わった数だけを読む、とある。→ R1
- persistence/sqlite/conversation/_store/worker_lifecycle.py:24-29: 会話を消すと、state_meta に墓標（キー 'gateway.retired_session.v1.' ＋番号、retirement.py:11）が残る。消した後に届いた量の書き込みは AuthorityRefusal で断られ、行は作り直されない。→ L3

## 2. 対照①・読み直し・消した後・読み方・schema_lead・止めどころ

| 見る点（design.md の行） | 判定 | 根拠 |
|---|---|---|
| 対照①の○の形（:124）: `task` 空の合計 1、かつ `task`=`title_generation` の行が 1 つ（`api_call_count` 1） | ○（見込みのままではない） | 1 の表の行のとおり。8回目の実測では、作り物の AI に 2 回届いた（docs/handoff/ai-assistant/bin0/out/raw/r8-5-fakelog-c1.txt:19-20）。題の呼び出しは主キー（_store/usage.py:58）の task が違うので、別の行になる。ただし `task` 空の行が書かれる時刻は R1 |
| 30 回の読み直し（:124） | ○（題の行には足りる） | 題の行は、作り物の AI が返事をしたすぐ後に同じ糸の中で書かれる（auxiliary_client.py:6611 → aux_accounting.py:144-161）。b5 の記録でも、題の chat は本の返事と同じ秒に届いた（review-architect-v28.md §2）。30 回の読み直しが「`task` 空の行」にも掛かるかは、書かれていない（R1） |
| 消した後の行の記録（:125） | △ | 何を記録するか（明細の行の数・`sessions` の行の数・合否には使わない）は書けている。ただし、理由に「番号だけの行が作り直される作り」と書いた所は、元ソースと逆。usage.py:154 の「a deleted session is refused」と worker_lifecycle.py:24-29 のとおり、消した後に届いた量は断られる（L3） |
| 読み取り専用の読み方（:126） | ○ | `mode=ro`・走っている容器の中で読む・文の列は読まない・開けなければ止める・2 ファイルを `grep -n` して無ければ止める・外へ写さない。どれも書けている。`docker exec` をどの利用者で流すかは書かれていない（L4） |
| schema_lead の記録（:127） | ○ | 文そのものは書かず 1/0 だけ。③で係 1・まとめ役 0。8回目にこの欄が無かったことは docs/handoff/ai-assistant/bin0/out/opus-check-r8.md:23 と合う。作り物の AI がその 1 文をどこから知るかは書かれていない。今の正本は docs/handoff/ai-assistant/bin0/run_bin0.py:44 の定数 1 か所（L5） |
| 止めどころのまとめ（:130） | △ | :124・:126・:128・:129 とはおおむね 1 対 1 で合う。:126 の「完成品の中の 2 ファイルで `grep -n` して無ければ止める」と「python の場所が見つからない」は、まとめに入っていない（L6） |
| 本物の束での K9 の○×（:88） | △ | ○×・「-」・止めどころは書けている。`task` 空の行を読む時刻が決まっていない（R1） |

## 3. 合格の線を変えていないか

○。`git show <版>:docs/handoff/ai-assistant/design.md | grep '^| K[1-9]' | awk -F'|' '{print $2"|"$3}' | sha256sum` を流した。値は ffda2d93c（第2.8版）・2b7c88080・9fc010eea（第2.9版）の 3 つとも `cf1263c94d74…` で同じ。design.md で変わったのは、頭の版と状態の行（:7・:16）、K9 の「検証方法」の列（:88）、§5 の対照（:124-127・:130）、§10（:189）だけ。「後ろで回る処理の分が 0・69/69」の基準の文は同じ。

## 4. 直す点（R）

- **R1 docs/handoff/ai-assistant/design.md:88・`:124`・`:126`（本体の行を読む時刻）**
  - 事実: 本体の呼び出しの量は、待ち行列に積まれるだけでその場では書かれない（agent/turn_usage.py:324-327・persistence/conversation/usage.py:5）。会話の数（`sessions`）と明細の行（`task` 空）は、同じ書き込みの中で一緒に書かれる（_store/usage.py:177-181）。8回目の GET が 1 を返したのは、題の 2 行目を待った後だった（docs/handoff/ai-assistant/bin0/out/raw/r8-5d-probe-c1.txt:1-2）。題を切った本物の束では待たないので、返事のすぐ後に読んで 1 になっているかは、まだ確かめていない。
  - 壊れ方: 返事の直後に state.db を読むと `task` 空の合計が 0 になる。:88 の決めでは「合わなければ×」なので、K9 が誤って不合格になる（または対照③で止まる）。
  - 直し方: :126 の読み方に次を足す。①順番は「GET → 明細の表」。②GET の `api_call_count` と、明細の表の `task` 空の合計が両方 1 以上になるまで、1 秒ごとに読み直す（上限の回数を決める。例: 対照①と同じ 30 回）。③上限まで 0 のままなら「×」ではなく「-」（読めない）にして、:88 のとおり K9 は判定せずに止める。④1 を超えたら×のまま。:124 の 30 回の読み直しも、「題の行」と「`task` 空の行」の両方が出るまで、と書く。

## 5. 軽い指摘（L）

- L1 :88: 「Hermes は後ろの処理の量を…明細の表に `task` 名つきで書く仕組み」に、元ソースの限りを書き添える。書かれないのは、会話の番号が渡っていない糸からの呼び出し・usage の無い返事・stream の返事・moa の 2 種類（agent/aux_accounting.py:104-129・agent/auxiliary_client.py:6596-6597）。K9 の記録には、「対照は題づけだけで確かめた」に続けて「表に書かれない後ろの処理は、この方法では見えない」と残す。合格の線は変えない。
- L2 :88: 「`task` が空でない行: title_generation・background_review・vision・compression など」の言い方。voice_chat のように、会話の数に入る `task` もある（usage.py:12）。便0 では声を使わないので害は無い。記録の言い方を「`task` が空でない行（便0 では声を使わないので後ろの処理だけ）」にするとよい。
- L3 :125: 理由の「番号だけの行が作り直される作り」は、元ソースと逆（worker_lifecycle.py:24-29・usage.py:9・:154: 消した後は墓標があり、書き込みは断られる）。正しい理由に直す: 「消した後に届いた量は断られて消える。消した後に表の行が残るかは、表の作り（_schema.py:129 の ON DELETE CASCADE）が効くかによる（未確認）」。あわせて、墓標の state_meta の行に会話の番号が残ることを K7 の記録に一言書く（文は入らない）。
- L4 :126: `docker exec` の利用者を決める（例: `-u hermes`。容器の外の手順の書き方は docs/handoff/ai-assistant/bin0/README.md の 4 番の `docker exec -u hermes` と同じ）。root で開くと、WAL のそばのファイルの持ち主が変わるおそれがある（未確認）。
- L5 :127: 作り物の AI が「形の指示の頭の 1 文」をどこから知るかを決める。docs/handoff/ai-assistant/bin0/run_bin0.py:44 の定数を写すと、同じ物が 2 か所になる。たとえば起動のときに、台本がその 1 文を `/fake` の下の 1 ファイルに書き出し、作り物の AI はそれを読む、など。
- L6 :130: 止めどころのまとめに 2 つ足す。「完成品の中の 2 ファイルに `session_model_usage`・`record_auxiliary_usage` の行が無い」（:126）と、「容器の中で python が見つからない」（:126）。

## 6. 9回目のカードを書ける粒度か

R1 を直せば書ける。

| カードの手順 | 判定 | 行 |
|---|---|---|
| 台本に「明細の表を読む」部分を足す（`docker exec`・`mode=ro`・`task` ごとの合計と行の数だけ） | ○（読む時刻は R1、利用者は L4） | :126 |
| `k9_ok` を表で決め、GET は添えにする（今は GET だけで決めている: docs/handoff/ai-assistant/bin0/run_bin0.py:396） | ○（「-」と「×」の分け方は R1） | :88 |
| 対照①の○の形・30 回の読み直し・GET の記録 | ○（R1） | :124 |
| ①の続きの「消した後の数」 | ○（理由は L3） | :125 |
| 完成品の中の 2 ファイルの `grep -n` | ○ | :126 |
| 作り物の AI に `schema_lead` を足す（今の docs/handoff/ai-assistant/bin0/control/fake_ai.py:67-73 には無い） | ○（1 文をどこから知るかは L5） | :127 |
| 対照③の○の形 | ○ | :129・:130 |
| 8回目の実装の足し（docs/handoff/ai-assistant/bin0/out/opus-check-r8.md:25-26 の c・d）をカードに正式に書く | ○ | opus-check-r8.md §2 |
