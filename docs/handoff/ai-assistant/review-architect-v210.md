# 設計審査 — 第2.10版（審査役 architect・クラウド・読み取りだけ）

判定: **APPROVE**

1. 前回の R1（本体の行を読む順と時刻）と L1〜L6 は、7 件とも設計の行で直っている（§1）。
2. 設計が新しく引いた元ソースの行（6 ファイル・9 か所）は、hermes-agent 8fc03744 の行と全部合う（§2）。合格の線（K1〜K9 の基準の文）は変わっていない（§3）。
3. 残るのは、カードの書き手が手順の中で決められる軽い指摘（L1〜L4）だけで、直さないと作れない・壊れる物は無い。9 回目のカードは書ける（§5）。

対象: origin/release/ai-assistant-bin0b f683b777d の docs/handoff/ai-assistant/design.md（第2.10版）。差分 9fc010eea..f683b777d（2 ファイル・86 行足し・8 行消し。design.md の差分は全部読んだ）と、前回の docs/handoff/ai-assistant/review-architect-v29.md。行番号は f683b777d のもの。この文書の docs/ で始まるパスはすべて release/ai-assistant-bin0b の f683b777d の中のファイルで、この枝（main 起点）には無い物があるので、バッククォートを付けていない。同じ会社の AI どうしの審査で、独立した第三者の審査ではない。

元ソースの読み方（事実）: 公開のリポジトリ NousResearch/hermes-agent から 8fc0374447313e276f6b9a2764bfc750190c966a を git fetch（depth 1）で作業用の一時の置き場に取り、`git rev-parse FETCH_HEAD` がこの番号と一致することを確かめてから、`git show FETCH_HEAD:<path>` で読んだ。写しはリポジトリに置いていない。下の元ソースのパスは hermes-agent の中のパスで、この repo の中には無い。

## 1. 前回の指摘が直ったか

| 指摘 | 直した設計の行 | 判定 |
|---|---|---|
| R1 本体の行を読む順と時刻 | design.md:88「読む順と時刻（第2.10版・審査 R1）」: 待ち行列から仕上げのときに書かれる、と理由を書き、「GET → 明細の表」の順・両方 1 以上になるまで 1 秒ごとに 30 回・30 回とも 0 なら「-」・1 を超えたら×、を決めた。design.md:124 の対照①も「`title_generation` の行と `task` 空の行の両方が出るまで」30 回に直した。design.md:130 の止めどころにも入った | ○（読み直しの決め方に軽い指摘 L1・L2） |
| L1 表の限り | design.md:88「この表の限り」: 番号の渡っていない糸・使った量の無い返事・stream の返事・moa の 2 種類は書かれない、本物の束では見えない、と K9 の記録に残す文まで書いた。合格の線は変えないと明記 | ○ |
| L2 `task` つきでも会話に入る声 | design.md:88「便0 では声を使わないので後ろの処理だけ」「声の `voice_chat` は `task` つきでも会話の数に入る」 | ○ |
| L3 消した後の理由が逆 | design.md:125: 消した後の書き込みは AuthorityRefusal で断られ行は作り直されない、行が残るかは ON DELETE CASCADE が効くか（未確認）、墓標の `state_meta` の行に番号が残ることを K7 の記録に書く | ○ |
| L4 `docker exec` の利用者 | design.md:126「`docker exec -u hermes`（…[bin0/README.md] の 4 番。root では開かない）」。docs/handoff/ai-assistant/bin0/README.md:30 の書き方と同じ | ○ |
| L5 形の指示の 1 文の正本 | design.md:127: 正本は docs/handoff/ai-assistant/bin0/run_bin0.py:44 の `SCHEMA_SYSTEM_LEAD` 1 か所、台本が `/fake` の下の 1 ファイルへ書き出し、作り物の AI はそれを読む、無い・空なら作り物の AI は起動を止める | ○（書き出す時刻に軽い指摘 L3） |
| L6 止めどころ 2 つ | design.md:130 に「容器の中で python が見つからない」「完成品の中の 2 ファイルに `session_model_usage`・`record_auxiliary_usage` の行が無い」が入った（あわせて「形の指示の 1 文のファイルが無い・空」も入った） | ○ |

§10 の履歴（design.md:190）にも第2.9版の REVISE と直した内容が書かれている。

## 2. 新しく引いた元ソースの行（8fc03744）

| 設計が言っていること（design.md の行） | 元ソースの行 | 判定 |
|---|---|---|
| 本体の量はその場では書かれず待ち行列に積まれる「Enqueued, not written」（:88） | agent/turn_usage.py:324-327（:326 に「Enqueued, not written」、:327「drained at finalize via _persist_session」）。:334-352 で `queue_usage(… api_call_count=1 …)` | ○ |
| 仕上げのときにまとめて書かれる（:88） | agent/session_persistence.py:529-531（:529「Drain async token-accounting deltas at every persist point」・:531 `store.usage.flush_usage()`） | ○ |
| 会話の数と明細の `task` 空の行は同じ書き込みで書かれる（:88） | persistence/sqlite/conversation/_store/usage.py:177（sessions への書き込み）・:180-181（`_record_model_usage`）が同じ conn の中で続く | ○ |
| 消した後の書き込みは AuthorityRefusal で断られる（:125） | persistence/sqlite/conversation/_store/worker_lifecycle.py:24-29（:24-26 の注記「must not recreate a deleted session beside its durable tombstone」・:27-29 で sessions に無く state_meta に墓標があれば `raise AuthorityRefusal('not_found')`） | ○ |
| 同じ理由（:125） | persistence/conversation/usage.py:9「a deleted session is not recreated (the apply fails and the delta is dropped)」・:154「a deleted session is refused」 | ○ |
| ON DELETE CASCADE（:125） | persistence/sqlite/_schema.py:129 `session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE`。表の列は :129-146、主キーは :147（task を含む）。文の列は無い | ○（効くかは設計どおり未確認） |
| 声の `voice_chat` は `task` つきでも会話の数に入る（:88） | persistence/conversation/usage.py:12。本体側で `task` が空でなくなるのは agent/turn_usage.py:350 の `getattr(agent, "_turn_route_task", "")` で、これを空以外にする所は試験を除くと agent/voice_turn_route.py:169 だけ（:207 で空に戻す）。git grep で確かめた | ○ |
| 表の限り（:88） | agent/aux_accounting.py:104-129（:104「Strictly best-effort」、:111 task 無し・moa、:113-115 ctx が None、:117-119 usage 無し、:124-129 すべて 0 のときは return）。moa の 2 種類は :25。agent/auxiliary_client.py:6596-6597「every successful non-streaming response passes here exactly once」 | ○ |

補足（事実・指摘ではない）: `record_aux_usage` を呼ぶ所は、試験を除くと agent/auxiliary_client.py:6611 のほかに plugins/image_gen/_common.py:270 もある。便0 では絵を作らないので K9 に害は無い。

## 3. 合格の線を変えていないか

○。`git show <版>:docs/handoff/ai-assistant/design.md | grep '^| K[1-9]' | awk -F'|' '{print $2"|"$3}' | sha256sum` を流した。値は 9fc010eea（第2.9版）と f683b777d（第2.10版）の 2 つとも `cf1263c94d74…` で同じ（前回の審査で ffda2d93c・2b7c88080 とも同じ値だった）。design.md で変わったのは、頭の版と状態の行（:4・:16）、K9 の「検証方法」の列（:88）、§5 の対照（:124-127・:130）、§10（:190）だけ。

## 4. 直す点（R）

無し。

## 5. 軽い指摘（L）（カードの書き手が手順の中で決める）

- L1 design.md:88 の読み直しの終わり方: 「両方 1 以上になるまで」「30 回とも 0 なら -」は、片方だけ 1 で片方が 0 のまま 30 回終わったときの扱いを書いていない。元ソースでは両方は同じ書き込み（_store/usage.py:177-181）なので起きにくいが、カードでは「30 回後に片方でも 0 なら -（K9 は判定せず止める）」と書くとよい。
- L2 design.md:88 の後ろの処理の行を数える時刻: 本物の束では、`task` 空の行が出た時点で `task` が空でない行を数える形になる。後ろの処理が本体より後に書かれる作り（題づけは別の糸: agent/title_generator.py:27-31）だと、その時点では 0 でも後から行が出るおそれがある（本物の束で後ろの処理が何時に書かれるかは未確認）。カードでは、後始末の①（K9）の最後、DELETE の直前にもう一度だけ明細の表を読み、その値で判定し、両方の値を記録する、と書くとよい。合格の線は変えない。
- L3 design.md:127 の 1 文のファイルを書き出す時刻: 8回目は control を `/fake` に読み取り専用で付けて容器を起動し、作り物の AI はその後 `docker exec -d` で起動した（docs/handoff/ai-assistant/bin0/out/measure-b-r8.md:11）。`/fake` は容器の中から書けないので、台本は容器の外の control の置き場へ、`docker run` の前に書き出す、とカードに書く。書き出したファイルは commit しない（.gitignore に足すか、台本の終わりで片付ける）。
- L4 design.md:130 の③の `task` 空 1・`task` あり 0 行: ③にも design.md:88 の「読む順と時刻」（GET → 明細の表・30 回）を使う、とカードで一言書く。

## 6. 9回目のカードを書ける粒度か

書ける。

| カードの手順 | 判定 | 行 |
|---|---|---|
| 台本に「明細の表を読む」部分を足す（`docker exec -u hermes`・`mode=ro`・`task` ごとの合計と行の数だけ） | ○ | :126 |
| 読む順（GET → 明細の表）・1 秒ごと 30 回・0 なら「-」・1 超で× | ○（片方だけ 0 の扱いは L1、最後の読み直しは L2） | :88 |
| `k9_ok` を表で決め、GET は添えにする（今は GET だけで決めている: docs/handoff/ai-assistant/bin0/run_bin0.py:396） | ○ | :88 |
| 対照①の○の形・両方の行が出るまでの読み直し・GET の記録 | ○ | :124 |
| ①の続きの「消した後の数」・墓標の記録 | ○ | :125 |
| 完成品の中の 2 ファイルの `grep -n`・python の場所の確かめ | ○ | :126・:130 |
| 1 文のファイルを台本が書き出し、作り物の AI が読む（今の docs/handoff/ai-assistant/bin0/control/fake_ai.py には無い） | ○（書き出す時刻は L3） | :127 |
| 対照③の○の形 | ○（読む時刻は L4） | :129・:130 |
| 8回目の実装の足し（docs/handoff/ai-assistant/bin0/out/opus-check-r8.md の c・d）をカードに正式に書く | ○ | opus-check-r8.md §2 |
