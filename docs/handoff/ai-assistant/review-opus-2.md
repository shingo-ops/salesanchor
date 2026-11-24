# 設計審査 2回目 — 審査役（Claude Opus・手元）

対象: commit 038beb831 の design.md 第2版ほか。審査日 2026-11-25。読み取りだけ。

設計審査 2回目の結果は REVISE（直してから便0へ）です。作りの骨組みは Hermes の説明書と合っていますが、便0 の実装カードを出す前に直す点が残っています。

理由は2つです。
- 「会話を Hermes に残さない」（design.md:39・:141）は、Hermes の既定では成り立ちません。説明書の上では、会話は Hermes の側に自動で保存されます。止める設定は見つかっておらず、設計にも名前がありません。このままだと K7 が最初から落ちます。
- 「頼むたびに AI を指定する」（design.md:34）は、`model` だけでは効きません。

対象: origin/release/ai-assistant-requirements の 038beb831（手元の HEAD と同じことを確認済み）。ファイルは書き換えていません。

---

１：1回目の必須の指摘の行方

Opus の M1〜M9（必須）

| # | 指摘 | 第2版 | 判定 | 根拠 |
|---|---|---|---|---|
| M1 | AI を決める正本が DB と Hermes に割れる | 担当表を正本にし、アプリが `model` を渡す（design.md:34） | 一部直った | 【事実】`model` は `provider` を一緒に送らないと無視されます。例外は `direct_model_requests` を有効にした場合だけです（Context7 api-server.md「POST /v1/chat/completions」）。設計には `provider` もこの設定も書かれていない |
| M2 | 決まり帳・カルテと二重になる | 覚え書きを切る。決まり帳とカルテは毎回アプリが渡す（design.md:35・:47） | まだ | 【事実】印のない頼みでも、Hermes は文面から会話の番号を作り、再起動の後も同じ会話に積みます（Context7 api-server.md「A Chat Completions request without X-Hermes-Session-Id derives its session…」）。また各回の後に会話は SQLite に保存されます（agent-loop.md「Session Persistence」）。ADR-1077:18「会話の全文は残さない」と食い違う。止め方は設計に無い |
| M3 | 道具を切ると振り分けが動かない | 振り分けをアプリへ移し、道具は全部切る（design.md:32-33） | 直った | 【事実】下の２の(3) |
| M4 | 覚え書きの「はい」は作れない | 覚え書きを切る | 直った | 【事実】2つとも false で覚え書きの道具も消える（Context7 memory.md「Configuration」） |
| M5 | 書き直さずに渡す作り・記録が無い | アプリが係を名指しで呼び、アプリが記録する（design.md:32・:50） | 直った | 【事実】`/p/<部屋名>/` で部屋が決まる（api_server.py profile_prefix_middleware） |
| M6 | 置き場の変更 | PO の判断へ回した（design.md:37・:121・:131） | 回したのは正しい | PO の言葉（ideal-state.md:11）を AI が書き換えないための扱いとして正しい |
| M7 | 禁じられた調べ | 便0 は作り物のデータだけ。本物は PO の判断（design.md:38・:131） | 回したのは正しい | 【事実】束 `backend/app/assistant_regression/cases.json` の中身は作り物の会社名（例「株式会社みなと商事」） |
| M8 | 基準が ○× にならない・緩い | 今の実測を線にした（design.md:73-85） | 一部 | ３で詳しく |
| M9 | 様式 | 6面の分析（design.md:97-106）・7観点（recon.md:65-73）・親からのリンク（docs/specs/secretary-chat/README.md:32）・FEATURE-INDEX（recon.md:21） | ほぼ直った | 「変更箇所＋変更前後＋触らない範囲」は便ごとの設計へ送った（design.md:126）。便0 のカードには要る |

Fable の R1〜R10（直す点）

| # | 判定 | 根拠 |
|---|---|---|
| R1 新規テーマか延長か・基準の PO 承認 | 区分は PO へ回した（正しい）。承認はまだ | 計画のステップ0（design.md:119）は「便0 に進むか」だけで、K1〜K9 の承認がない。基準は「PO 承認前」のまま（design.md:71）。Fable 1-1 の関所が残る |
| R2 | M1 と同じ（一部） | |
| R3 足りない変更を全部書く | ほぼ直った | 移行と変換部品が書かれた（design.md:36・:94）。sdk の決まりを置く migration（`migrations/20261117_100100_add_llm_usage_tts_characters.sql:38`）は名前が出ていない |
| R4 会社ごとの分け隔て | 方針は直った（design.md:39・K8）。成り立つかは未確認 | 上の M2 のとおり、文面から作った会話に積まれるなら、会社 A と B で書き出しが同じ頼みが同じ会話に入るおそれがある【推測】 |
| R5 ADR-1077・1078・1004・091 との関係 | 対象には入った（design.md:13）。台帳の1行の単位はまだ | ADR-1004:25 は「1行＝AI の応答1回」。1回の頼みで2回呼ぶ分を2行にするか1行にまとめるかが無い（design.md:50「1回ごと」があいまい） |
| R6 ADR-1056 の変更 | 置き場と鍵は PO へ回した。容器の守りと料金の形はまだ | 容器の守り（read_only など、ADR-1056:19）の扱いと、月額か使った分払いか（ADR-1056:15）の記載が無い。今の秘書は月額の契約で `--json-schema` を使って形を固定している（secretary-agent/server.mjs:69-70） |
| R7 | M8 と同じ | |
| R8 Discord | 便3 へ送った（design.md:124） | 範囲として正しい |
| R9 外部事例と説明書の写し | 事例は直った（research.md）。Hermes の版の固定と説明書の写しはまだ | recon.md:44 は文書の場所だけで、版の番号も取得日の写しも無い |
| R10 | ほぼ直った | 便0 の「試しの場所」は PO 待ち（design.md:119） |

２：中心の作りと Hermes の説明書の照合

Context7 の /nousresearch/hermes-agent で確かめました。どの版の説明書かは分かりません（main を見ています）。

（１）部屋の名指し（/p/）に multiplex_profiles が要るか
- 【事実】要ります。`multiplex_profiles` が切れていると、`/p/` で通るのは自分自身の部屋の名前だけで、他の名前は 404 になります（api_server.py `_resolve_request_profile`）。
- 【事実】設定は `gateway.multiplex_profiles: true` です（multi-profile-gateways.md）。
- 【事実】2026年7月の変更で、部屋ごとに別の `API_SERVER_KEY` が要ります。共通の鍵だと 401 で断られます（api-server.md「Multi-profile routing」）。
- 設計（design.md:93）にはどちらも書かれていません。鍵が 3 本になるので、PO が決める鍵の件数（ADR-1003）にも関わります。
- 【事実】知らない部屋名が 404 で断られるのは設計のとおりです。

（２）1回ごとの model の指定が効くか
- 【事実】`model`・`provider`・`model_options` で1回ごとに指定できます。ただし `provider` なしの `model` は無視されます。例外は `direct_model_requests` を有効にした場合だけです（api-server.md）。
- 【未確認】今の秘書の頭（codex・gpt-5.6-terra を月額のログインで使う形）に当たる provider の名前が Hermes にあるか。

（３）全部の部屋で道具を空にできるか
- 【事実】部屋ごとの設定で決まり、1回ごとには変えられません（tools_config.py `_get_platform_tools`）。
- 【事実】道具が1つも無いときは、会話だけで動きます（agent_init.py「No tools loaded」）。
- 【事実】空の一覧なら外の部品（MCP）も入りません（toolsets-reference.md「An explicitly empty list (`email: []`) gets no MCP servers」）。
- 【未確認】`api_server: []` が「空と明示した一覧」として扱われ、標準の道具一式に戻らないこと。コードの読み方では空になりますが、実物では確かめていません。K4 で測ることになります。

（４）memory_enabled: false
- 【事実】`user_profile_enabled: false` と一緒にすれば、覚え書きは完全に切れます（memory.md）。
- 【事実】ただし各回の後の振り返り（自分を直すための処理）は別のスイッチです。`auxiliary.background_review.enabled: false` で止めます（memory.md）。
- 【事実】この振り返りは1回で約3万トークン使います（turn_finalizer.py のコメント）。手順書を学ぶ振り返りは、覚え書きを切っても残ります（`review_skills`）。
- 設計にはこのスイッチがありません。K7 にも K9 にも関わります。

（５）/v1/chat/completions は会話を保存するか・切れるか
- 【事実】説明書には「Stateless」と書かれています。一方で、印のない頼みでも Hermes が会話の番号を作り、その会話に積みます。各回の後には会話の記録へ保存されます（api-server.md・agent-loop.md）。
- 【事実】会話を消した場合、その番号は使い回されません（api-server.md）。
- 【未確認】保存そのものを切る設定があるか。Context7 では見つかりませんでした。無ければ、K7 は「毎回アプリが会話を消して 0 件」に書き直すか、ADR-1077:18 の改めを PO に聞くことになります。

（６）返事に使った量が入るか
- 【事実】`usage.prompt_tokens`・`completion_tokens`・`total_tokens` が入ります（api-server.md の返事の例）。
- 【未確認】後ろで回る振り返りの分は、返事の量に入りません（返事を返した後に動くため。turn_finalizer.py）。今の K9 は「返事に量が入る」だけを見るので、振り返りが動いていても合格してしまいます。

３：基準 K1〜K9 の点検

- 【事実】束は 23 件です（cases.json の cases の件数を数えた）。今の秘書の 69 件は、23 件を 3 回流したものです（baseline.md:13）。設計の「束 69 件」（design.md:73・:120）はこのとおりに書き直すべきです。
- K1：【事実】23 件のうち 7 件は正解が「わからない」です（unknown 4・rule 3）。まとめ役がこれをどの係と答えれば正しいのか、対応表に無いので ○× が決まりません（design.md:77 は「予定→予定係・請求書→請求書係」だけ）。
- K2：○× で決まります。【事実】今の秘書は `--json-schema` で形を固定しています（server.mjs:69-70・:112）。【未確認】Hermes の口が `response_format` に対応するか。対応しないと 69/69 は運しだいです。
- K3：【事実】今の回帰の道具が見るのは「種類が合うか」と形の検査だけで、会社名・金額・日時の中身は見ていません（baseline.md:47）。K3 は「中身の当たり」という名前なのに中身は K1・K2 と同じで、中身は測れていません。名前を直すか、物差しを足す必要があります。
- K4：「Hermes の記録」の名前と場所がありません。「全部の部屋で 5 件」が 5 件なのか 3 部屋×5 件なのかもあいまいです。
- K5：「2 回呼ぶ分の上乗せ」と「声の会話の待ちが延びるので PO 承認の対象」という理由は書かれています（design.md:81）。ただし理由は半分です。
  - 真ん中 10 秒は約 2 倍で説明がつきます。最長 30 秒は約 3.8 倍で、根拠がありません。
  - 【事実】線の元にした値は決まり帳を付けない実測です。決まり帳を付けたときの実測は、真ん中 7.88 秒・最長 12.42 秒です（baseline.md:99）。設計では毎回決まり帳を渡す（design.md:35）ので、比べる元はこちらの値です。
  - 【事実】日によって値が変わるので、比べるときは同じ日の値と並べる決まりです（baseline.md:110）。便0 で同じ日に今の秘書も流す手順がありません。
- K6：合否ではなく記録だけです。今の段階ではこれで構いません。
- K7：調べる保存場所の名前が無く、２の（５）のとおり今のままでは落ちます。
- K8：○× で決まります。ただし２の（５）の会話の積み方を考えると、合格の条件に「会話を残さない」が前提として要ります。
- K9：「量が入るか」だけを見ていて、振り返りの分を数えていません。
- 止めどころ（design.md:113）に K3 と K5 が入っていません。K3 が今より悪くても便1 へ進めてしまいます。

緩さのまとめ：K1・K2 は今の秘書と同じ線です。K5 は今より緩く、その理由の説明は一部だけです。K3 は今の点と同じ線ですが、中身を測っていません。

４：便0 に進めるか・カードの前に残る穴

便0 の流れそのもの（試しの場所に 3 部屋を置き、束を流す台本で測り、終わったら消す）は、この作りの範囲で実行できます。【事実】部屋の名指し・道具を空にする・覚え書きを切る・使った量の返事は、どれも説明書にあります。

カードを出す前に埋める穴（順番に意味があります）:
（１）PO が K1〜K9 を承認する（R1。今は草案）。
（２）Hermes の設定を全部書き出す。
- `gateway.multiplex_profiles: true`
- 部屋ごとの `API_SERVER_KEY`（3 本）
- `provider` を指定するか、`direct_model_requests` を有効にするか
- `auxiliary.background_review.enabled: false`
- 会話を残さない方法（設定が無ければ、毎回の削除と、K7 の書き直し）
（３）Hermes の版を固定し、説明書の写しをリポジトリに置く（R9）。
（４）便0 で使う AI 会社と頭を決める。今の秘書（codex・月額のログイン）と頭が違うと、K3・K5 の差が Hermes のせいなのか頭のせいなのか分かりません。使った分払いの鍵を使うなら、費用の上限と鍵を置く人を PO が決める（ADR-1003）。
（５）同じ日に今の秘書も流す手順を決める。今の秘書は本番にしか無いので、本番に触る許可が要ります【事実: baseline.md:10-11】。決まり帳を付けるか付けないかも、両方でそろえる。
（６）K1 の「わからない」7 件の正解を決める。K2 の形を `response_format` で固定できるか確かめる。K4・K7 で調べる記録と保存場所の名前を書く。
（７）試しの場所（どの機械か・本番と別のつなぎ方か・終わったら消す手順）を PO が決める（design.md:119）。【未確認】クラウドの作業場所で Hermes を立ち上げて、AI 会社につなげるか。

５：未確認の一覧
- U1: `platform_toolsets.api_server: []` が実物で道具 0 になるか（K4 で測る）。
- U2: 会話の保存を切る設定があるか。
- U3: 今の秘書の頭に当たる provider が Hermes にあるか。
- U4: Hermes の口が `response_format`（形の固定）に対応するか。
- U5: Hermes の使用の許諾と、使う版の番号。
- U6: クラウドの作業場所で便0 を動かせるか。

６：Hermes でこの作り替えができるか（非エンジニア向け 3 行）
1. 骨組み（アプリがまとめ役に係の名前だけ聞き、係の AI を名指しで呼び、AI には道具も覚え書きも持たせない）は、Hermes の説明書にある機能で組めます。
2. ただし Hermes は初めの設定のままだと会話を自分の中に保存し、後ろで自分を直す処理（1回で約3万トークン）も回すので、この2つを止める設定を設計に書き足す必要があります。
3. 本当に今の秘書と同じ速さと正しさで動くかは、まだ誰も確かめていません。作り物のデータで試す便0 で数えて決めることになります。

読んだファイル:
- /Users/tanizawashingo/worktrees/salesanchor/release-ai-assistant-requirements/docs/handoff/ai-assistant/design.md
- /Users/tanizawashingo/worktrees/salesanchor/release-ai-assistant-requirements/docs/handoff/ai-assistant/recon.md
- /Users/tanizawashingo/worktrees/salesanchor/release-ai-assistant-requirements/docs/handoff/ai-assistant/requirements.md
- /Users/tanizawashingo/worktrees/salesanchor/release-ai-assistant-requirements/docs/handoff/ai-assistant/research.md
- /Users/tanizawashingo/worktrees/salesanchor/release-ai-assistant-requirements/docs/handoff/ai-assistant/review-opus-1.md
- /Users/tanizawashingo/worktrees/salesanchor/release-ai-assistant-requirements/docs/handoff/ai-assistant/review-fable-1.md
- /Users/tanizawashingo/worktrees/salesanchor/release-ai-assistant-requirements/docs/handoff/secretary-rulebook/baseline.md
- /Users/tanizawashingo/worktrees/salesanchor/release-ai-assistant-requirements/backend/app/assistant_regression/cases.json
- /Users/tanizawashingo/worktrees/salesanchor/release-ai-assistant-requirements/secretary-agent/server.mjs
