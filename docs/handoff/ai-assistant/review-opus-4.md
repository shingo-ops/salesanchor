# 設計審査 4回目 — 審査役（Claude Opus・手元）

対象: HEAD 0412be773 の design.md 第2.2版ほか。審査日 2026-11-25。読み取りだけ。

設計審査 4回目（審査役・Opus・読み取りだけ）

判定は REVISE です。前回の直す点7つは、ほぼ本文に入りました。残っているのは、次の4つが本文で食い違っている点です。
- 頭の指定の持ち方
- 容器の守り
- PO の決定 Q8 が設計に入っていないこと
- 試しの場所（クラウド）と入れ方（Docker）の組み合わせ

どれも小さい直しで、便0 のカードは直した後に書けます。

対象は worktree の HEAD 0412be773（design.md 第2.2版・requirements.md Q8 まで）です。ファイルの書き換え・commit・push はしていません。

１：review-opus-3 の直す点 1〜7 の行方（行番号は design.md）

| # | 判定 | 根拠 |
|---|---|---|
| 1 会話の消し方・K4 | ○ | :105 に入った。中身は `X-Hermes-Session-Id` を頼みごとに新しく付ける、mutation-snapshot→DELETE、session_busy はやり直し、文の無い記録が残る。:82 の K4 は「消す前に数える」と `hermes.tool.progress` に直った |
| 2 response_format | ○（ただし Q8 と食い違う） | :106「説明書に無い・便0 の最初に実物で確かめる」。一方で :106 の「やり直すか止めるかを PO が決める」は、requirements.md:40 Q8 で決まっている（「形がくずれたらアプリで1回だけやり直す」） |
| 3 :34 と :98 をそろえる・provider の置き場 | △ | :36 は「`model` と `provider` を組で渡す」、:101 は「両方付ける」。ところが :97 は「担当表の model 欄に `model_routes` の別名を入れる」で、provider をどこから出すかが書かれていない。別名と違う provider を送ると 400 になる（下の２）。3か所がまだ1つの形になっていない |
| 4 入れ方 | ○ | :108 に入った（Docker の完成品・pip は非対応・3.14・1〜4GB）。ログインは :110。版の番号は便0 で決める（:98） |
| 5 sdk の migration・台帳の単位・容器の守り | ○／○／△ | :96 に 20261117:35-37 が入った。実物の :35-37 は sdk の CHECK で、合っている。:52 の「1 行＝応答 1 回・頼み 1 回で 2 行・頼みの番号で結ぶ」は ADR-1004:25 の単位と合う。:109「`docker-compose.secretary-agent.yml:19`〜25 と同じ形」は Hermes の起動の仕方と合わない恐れがある（下の２（５）） |
| 6 K3 正解表・K9 の読み先 | ○／△ | :81 に「便0 の担当が作り、Opus が PR で 1 件ずつ確かめる」が入った。:87 の K9 は「読み先は便0 の最初に実物で決める」で、先送りのまま |
| 7 §0 に Q6・Q7、:6 の文 | ○ | :27・:28 に Q6・Q7、:6 は「審査 4 件」に直った。ただし requirements.md:40 の Q8 が §0 に無い。:16 の状態は「設計案第2版作成済み」のまま古い |

２：新しく書いた Hermes の項目と説明書の照合（Context7 /nousresearch/hermes-agent の main。版は分からない）

（１）会話の消し方（:105）
- 【事実】合っている。DELETE には mutation-snapshot の request_id・expected_revision・expected_generation が要る。欠けると 409 mutation_identity_required。動いている最中は 409 session_busy。再起動で失われた回は 409 unknown_execution。消した後も state_meta に文を外した記録が残り、ずっと消えない（1 回あたり数百バイト）。出典は website/docs/user-guide/features/web-dashboard.md「DELETE /api/sessions/{session_id}」。
- 設計に足りないのは unknown_execution の扱い（再起動をまたいだとき）。
- 【未確認】この口が `/p/<部屋名>/` と部屋ごとの API_SERVER_KEY で通るか。web-dashboard.md の口なので、ダッシュボードを動かさないと無い可能性もある。
- 【未確認】K7 の探す範囲。:85 は「部屋ごとの会話の記録」だけを探す。ログ（agent.log など）に頼みの文が出るかは確かめていない。データの置き場全体を語で探す形にした方が漏れが無い。

（２）X-Hermes-Session-Id（:105）
- 【事実】合っている。
  - 自分で付けた番号はそのまま使われ、付け替えられない（api-server.md「Idempotency keys」）。
  - 返事にもその番号が返る。
  - 付けなければ system prompt と最初の文から番号を作る（api-server.md「API Server」）。
  - 消した番号は二度と使われない。
- 頼みごとに新しい番号を付ける設計は、これと合う。

（３）model_routes の別名を model 欄に入れる案（:97）。依頼の要点「provider を付けずに効くか」
- 【事実】優先の順番は「会話の /model → `model_routes` の別名（頼みの model が別名と一致したとき）→ 頼みの model/provider → 全体の既定」。別名とぶつかる provider を送ると 400（api-server.md「Per-request model selection」）。
- 【事実】`/v1/chat/completions` では「provider の無い model は無視される。`direct_model_requests: true` のときは別」（同じ所）。
- 【未確認】provider を付けずに別名を送ったとき、どちらが先に効くか。説明書は次のどちらとも読める。
  - 別名が先に照合される
  - 「provider の無い model は無視」が先に効いて全体の既定に落ちる
- 【未確認】`model_routes` の設定の書き方。説明書の例は見つからなかった（3回の問い合わせ）。出てきたのは別の仕組みの `model_aliases`（website/docs/user-guide/configuring-models.md・website/docs/reference/slash-commands.md）で、こちらは `/model <別名>` 用。API の口の `model_routes` と同じものかは書かれていない。
- 結論。この案は説明書だけでは「効く」と言えない。便0 の最初に、次の4通りを流して確かめる手順を設計に書く必要がある。
  - 別名だけ
  - 別名＋合う provider
  - 別名＋違う provider（400 になるはず）
  - `direct_model_requests: true` で別名だけ
  - どの頭で動いたかは、返事の model と Hermes の記録で確かめる
- 実物で読むなら gateway/platforms/api_server.py。
- 効かなかったときの別の案（これは設計の判断）は2つ。
  - 担当表の model 欄に「provider/頭」の組で入れ、アプリが分けて送る
  - 部屋ごとの既定の頭（優先の4番目）に任せ、担当表は記録用にする

（４）入れ方・容器の守り（:108・:109）
- 【事実】公式の容器は root で立ち上がる。そのあと UID を付け替え（usermod/groupmod）、持ち主を直し、権限を 0600/0640 にそろえ、s6-setuidgid で利用者 hermes（UID 10000）に落とす（docker/stage2-hook.sh）。
- 【事実】今の秘書の容器は `read_only: true`・`cap_drop: ALL`・`no-new-privileges:true`・`mem_limit: 512m`（docker-compose.secretary-agent.yml:19-26 の実物）。
- 【未確認】`cap_drop: ALL` と `read_only: true` のまま Hermes が立ち上がるか。立ち上がりの持ち主の直しと利用者の切り替えには、それに当たる権限が要る作り。「同じ形」と言い切らず、便0 で「同じ形で立つか／立たなければ最小でどの権限を戻すか」を測る項目にすべき。
- 【事実】データの置き場は `/opt/data` の bind mount（website/docs/user-guide/docker.md）。
- 【未確認】Q8 の試しの場所は「クラウドの作業場所」（requirements.md:40）。そこで Docker の完成品が動くかは書かれていない。動かなければ、公式の入れる台本で入れることになり、:108 と変わる。

（５）openai-codex のログイン（:110）
- 【事実】前回（review-opus-3.md:68-70）の照合と変わらない。`hermes auth add openai-codex`・device code・従量の鍵は不要。
- 【事実】:110 の「分け合ってよいかは PO が決める」は Q8 で決まっている。中身は「試し用に別に1回」ログインする（requirements.md:40）。本文が古い。
- 【未確認】`gpt-5.6-terra` が選べるか。部屋ごとにログインが要るか。

３：便0 の実装カードを今書けるか

今のままでは書けません。§0・§5・§9 に Q8 を入れて、:97・:101・:109 の食い違いを直せば書けます。足りないのは次のとおりです。

調べれば分かること（カードの最初の「確かめ」の段に入れればよい）
- (a) クラウドの作業場所で Docker の完成品が動くか。動かないときの入れ方。版の番号。
- (b) model_routes の書き方と、上の２（３）の4通りの結果。
- (c) response_format が API の口で通るか（:106）。
- (d) 消す口（snapshot・DELETE）が `/p/` と部屋ごとの鍵で通るか。ダッシュボードが要るか。unknown_execution の扱い。
- (e) AI 会社の自動の切り替えを切る設定（:107）。
- (f) K9 の総使用量の読み先（:87）。
- (g) `cap_drop`・`read_only` で立ち上がるか。書き込む場所の一覧（:109）。
- (h) `gpt-5.6-terra` が選べるか。部屋ごとのログインが要るか。
- (i) K7 の探す範囲を、データの置き場全体（ログを含む）にするか。
- (j) 同じ日の今の秘書の測りの台本。docs/handoff/secretary-rulebook/bin0/run_baseline.py は本番の backend の image の中から `/intent` を呼ぶ形（baseline.md:10-11）なので、こちらは使い回せる。Hermes の側は OpenAI 互換の口なので、新しい台本が要る。
- (k) やり直しの数え方。Q8 の「形がくずれたら1回だけやり直す」を、便0 の台本でもするか。K2（:80）の 69/69 をやり直しの前で数えるか後で数えるか。

PO が決めること（新しく出たもの）
- 確かめの結果、(a) Docker が動かない、または (g) 守りを弱めないと立たない場合に、続けるか止めるか。Q8 の「動かなければ止めて相談」が当てはまるので、新しく聞くことは無いとも読める。カードの止めどころとして書いておけば足りる。
- 本番を読む回は、制限の無い鍵で Opus が流した前回の形（baseline.md:10）。Q8 で PO は「同じ日に本番を1回読む」を承認済み。実行のときはその日の同意票（permit）を1回取る運用になる。

４：判定

REVISE です。
- 理由1（本文の食い違い）。§0 に Q8 が無い。そのため :106・:110・§9-1（:146）が、決まったことをまだ「PO が決める」と書いている。
- 理由2（説明書と合わない恐れ）。:97 の model_routes の別名案は、provider を付けずに効くかが説明書で確かめられない。:101「両方付ける」とも食い違う。:109 の「今の秘書と同じ守り」は、root で立ち上がる公式の容器（docker/stage2-hook.sh）と合わない恐れがある。
- 理由3。試しの場所（クラウド）と入れ方（Docker）の組み合わせが確かめられていない。

骨組みと、前回の大きな直し（消し方・response_format・入れ方・台帳の単位・sdk の migration・K3 の正解表）は入っています。REJECT にする理由はありません。

判定
REVISE（直す点 1〜6 を入れれば、次は便0 のカードに進める見込み）

直す点
1. §0（:20-28）に Q8（requirements.md:40）を足す。:106・:110・§9-1（:146）を Q8 の決定どおりに書き直す（形がくずれたら1回だけやり直す／試し用に別にログイン／会話は毎回消して全文を残さないを満たす）。:16 の状態を第2.2版に直す。
2. :36・:97・:101 を1つの形にする。model_routes の別名を provider なしで送って効くかは説明書に無い（api-server.md「Per-request model selection」）。便0 の最初に4通りで確かめる手順と、効かなかったときの代わりの案を書く。
3. :109 の「同じ形」を「同じ形で立つか便0 で測る」に直す。理由は、公式の容器が root で立ち上がり、UID の付け替え・持ち主の直し・利用者の切り替えをするため（docker/stage2-hook.sh）。戻す権限は最小の一覧にする。
4. :108 に、Q8 の試しの場所（クラウドの作業場所）で Docker が使えるかの確かめと、使えないときの入れ方を足す。
5. :105 に unknown_execution（409）の扱いを足す。消す口が `/p/` と部屋の鍵で通るか（ダッシュボードが要るか）を便0 の確かめに入れる。
6. :85 の K7 の探す範囲を、Hermes のデータの置き場全体（ログを含む）にする。:80 の K2 を、やり直しの前で数えるか後で数えるか決めて書く。

PO が決めること
決めることはありません。Q8（requirements.md:40）で、便0 の場所・ログイン・合格の線・本番の読み取り・会話の消し方・やり直しは決まっています。本番を読む日には、その日の同意票（permit）が1回だけ要ります。

出典のファイル
- 審査対象: /Users/tanizawashingo/worktrees/salesanchor/release-ai-assistant-requirements/docs/handoff/ai-assistant/design.md、/Users/tanizawashingo/worktrees/salesanchor/release-ai-assistant-requirements/docs/handoff/ai-assistant/requirements.md、/Users/tanizawashingo/worktrees/salesanchor/release-ai-assistant-requirements/docs/handoff/ai-assistant/review-opus-3.md
- 確かめた実物:
  - /Users/tanizawashingo/worktrees/salesanchor/release-ai-assistant-requirements/migrations/20261103_120000_create_ai_job_assignments.sql:26-33
  - /Users/tanizawashingo/worktrees/salesanchor/release-ai-assistant-requirements/migrations/20261117_100100_add_llm_usage_tts_characters.sql:35-37
  - /Users/tanizawashingo/worktrees/salesanchor/release-ai-assistant-requirements/docker-compose.secretary-agent.yml:19-26
  - /Users/tanizawashingo/worktrees/salesanchor/release-ai-assistant-requirements/backend/app/routers/assistant.py:201
  - /Users/tanizawashingo/worktrees/salesanchor/release-ai-assistant-requirements/backend/app/services/llm_budget.py:180
  - /Users/tanizawashingo/worktrees/salesanchor/release-ai-assistant-requirements/docs/adr/ADR-1004-llm-usage-ledger.md:25
  - /Users/tanizawashingo/worktrees/salesanchor/release-ai-assistant-requirements/docs/handoff/secretary-rulebook/baseline.md:10-11
- Hermes の説明書（Context7・main）: website/docs/user-guide/features/api-server.md、website/docs/user-guide/features/web-dashboard.md、website/docs/user-guide/sessions.md、website/docs/user-guide/configuring-models.md、website/docs/user-guide/docker.md、docker/stage2-hook.sh
