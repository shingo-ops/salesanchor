# 秘書 LIVE 設計の審査 2 回目（architect）

この文書は何か: `origin/release/secretary-live-design` の設計（直した 2 版）と ADR-1085 草案を、実装に渡してよいか読んで確かめた 2 回目の審査の結果です。製品のコード・DB・本番・secrets は触っていません（読むだけ）。
親（あるべき姿）: [docs/specs/secretary-chat/README.md](../../specs/secretary-chat/README.md)／1 回目: [review-architect.md](review-architect.md)

- 審査日: 2026-11-23（クラウドの審査役）
- 審査した物: `docs/handoff/secretary-live/{kgi,design,recon,research,research-2,review-architect}.md`・`docs/adr/ADR-1085-secretary-live-voice.md`（`git show origin/release/secretary-live-design:<path>`）
- 実物の基準: `origin/main` の `2b4e2c205`（作業場所 `release/secretary-live-design-review2` の起点）。以下の `パス:行` は特に書かない限りこの実物の行。
- 照らした物: `AGENTS.md`・`docs/STANDARD-WORKFLOW.md`・`docs/ai-agents/design-partner.md`、ADR-1056・1058・1080・1082・1004・1003 の本文。ADR-135・136・027・067・144 は要点だけ（135・136 は AGENTS.md の GO の規則経由。027・067 は recon.md 経由。本文の精読は 144 の `:134` のみ）。
- 外部文書: Context7 MCP はこの実行環境に無い（ToolSearch で `context7` を探して 0 件）。Gemini Live・ephemeral token・Web Speech・AudioWorklet・iOS・料金の外の事実は**すべて未確認**。以下の「未確認」はこの意味。
- 本番: 触っていない。design.md §3 の「$40.55」は本番台帳の値で、この審査では確かめていない（未確認）。

## 判定: **REVISE（直す必要）**

1. 1 回目の指摘 8 件は骨格では直っている（§0）。ただし**直した所に新しい矛盾が出た**: 声の読み上げの中身を Gemini に渡さない（design.md `:105`）のに、Gemini が中身を読み上げて「はい」で作る（`:117`・`:119`）。読み上げが下書きの実物の確認になっていない。
2. **台帳の型が実物と合わない**: 仮の行の `outcome`、Google の印を残す `error_code`、速さ（ms）・音声の内訳の列は、いずれも今の CHECK・列に入らない（`migrations/20261103_120000_create_ai_job_assignments.sql:128-144`・`migrations/20260930_150000_create_llm_usage_events.sql:29-43`）。「値を足すだけの migration 1 本」（design.md `:223`・`:230`）では足りない。上限の判定にも穴がある（使わなかった札の仮の行が上限を食う・同時に取る競争）。
3. **KGI の L5（2 秒以内）と L7（2 秒黙っても切れない）は、黙りの長さで切る方式では同時に満たせない**。それと、請求書の声の「はい」は、画面で人が触るのが「送料を請求しない」の 1 つだけ（`SecretaryDraftInvoice.tsx:114`）で、金額の確認にならない。作り直しではなく、§「直す必要」を直せば APPROVE に近い。

## 0. 1 回目の指摘（review-architect.md §2）が design.md §0 のとおり直っているか

| # | 1 回目の指摘 | design.md の直し場所 | 実物で確かめた結果 |
|---|---|---|---|
| 1 | KGI の測り方が 7 本あいまい | kgi.md §2 | **一部直った**。L8・L10・L12 は一義になった。L2・L3・L5・L7・L11 に残りがある（§1-(1)）|
| 2 | 声の「はい」・請求書の安全 | §5-1 | **骨格は直った**（完全一致・窓・否定語の試験・`canCreate` を飛ばさない・`submit` を外へ出す改修が便 B・§2 に書かれた）。**新しい矛盾**: 読み上げの中身の出どころ（§1-(2)）|
| 3 | 使用量の入り口・上限の置き場・値段表・失敗の行・費用の画面 | §6 | **設計は入った**が、台帳の実物の CHECK・列に合わない（§1-(4)）。費用の画面（`tcg_analysis_dashboard.py:939-941`・`:1050`）は実在 |
| 4 | AudioWorklet・札の設定の固定・札の口の回数 | §5-2・§5-3 | AudioWorklet は `frontend/public/` の普通のファイル（`frontend/public/` は実在）・札の固定は書かれた。**札の口の回数を数える置き場が未定**（§1-(5)）|
| 5 | ADR の改めの不足 | ADR-1085「改める点」 | ADR-1056・1058・1080・1082・1004 は入った。**ADR-1058 の `outcome`・`error_code` の決まり（`docs/adr/ADR-1058-ai-job-assignments.md:24`）を改める点が無い**（§1-(4)）|
| 6 | 便 T を T0・T1 に分ける | §10 | 直った（§1-(7)）|
| 7 | 維持の仕組み欄・親リンク・1 行説明・ADR-144 の「ある」の過大 | 冒頭・§11・§16 | §9 と §11 の ADR-144 の書き方は**直った**（`docs/adr/ADR-144-ui-component-governance.md:134` と一致）。**残り**: 「守り手:」の行が無い・親→子のリンクが無い（§1-(6)）|
| 8 | 料金の出どころの書き分け | §4 | 直った。【公】【三】【未】が付き、research.md `:5-6` の注意と矛盾しない |

## 1. 見る点ごとの判定

### 先に: design.md が引いた file:line の突合

合わない行・文面: **6 件**。それ以外は全て実物と一致した（下の「一致」）。

| # | design.md の引用 | 実物（origin/main `2b4e2c205`）| 直し方 |
|---|---|---|---|
| a | §3 `:53`「『送料を請求しない』にチェックすることが条件に入る（`:78`）」の `SecretaryDraftInvoice.tsx:78` | `:78` は `const [notes, setNotes] = useState(draft.notes ?? "")`。`shippingNone` の state は `:76`・条件に入るのは `:114`・チェックの部品は `:252-258` | `:78` を `:76`・`:114` に直す |
| b | §3 `:56`・§6-3 の `calculate_usage_cost`（`llm_budget.py:225-250`）| 関数は `backend/app/services/llm_budget.py:225-241`。`:250` は次の関数の引数 | `:225-241` に直す |
| c | §6-6 `:187`「`components/` に警告の金型は見つからなかった（`Alert`・`Banner` の名前の部品は無い）・新しい部品は作らない」| `frontend/src/components/Callout.tsx:1-10` が「画面に残る注意・案内の枠（ADR-144 金型）」で、`variant: warning`（`role="alert"`）／`info`（`role="status"`）。recon.md `:54` にも `Callout` の存在は書いてある | 上限の知らせは `Callout` を使うと書く。名前でなく用途で探した結果を書く |
| d | §12-H `:260`「Sales Anchor には MCP の口も OAuth の認可の口も無い（`git grep` origin/main `backend/app` で 0 件）」| `git grep -n -i "mcp" -- backend/app` は 0 件。**`oauth` は 0 件ではない**（`backend/app/main.py:52`・`:63`・`:76` に Discord・Google Calendar・Meta の OAuth の routers）。これらは外のサービスへつなぐ側で、Sales Anchor が OAuth の認可を出す側の口があるかは未確認 | 文を「OAuth の認可を出す側の口は未確認」に直すか、検索の語を絞って書く（PO は今は頼まない判断なので実装には響かない）|
| e | §15 `:285`・§6-2 `:156`「`tenant_features` の秘書の行を切れば LIVE のボタンが消え、**文の秘書は今のまま動く**」| 秘書の旗 `secretary_chat` は秘書の全部の口の守り（`backend/app/routers/assistant.py:93`・`:99`）。切ると**文の秘書も使えなくなる**。LIVE だけを切る旗は無い。`tenant_features` は行で持つ旗（`migrations/20261101_120000_enable_secretary_chat_tenant4.sql:10`・`backend/app/auth/dependencies.py:651-668`）| LIVE 専用の旗の行（例 `secretary_live`）を足すと書く。行を足すだけなので CHECK の変更は要らない見込みだが、有効にする行は migration か運用の INSERT になる（§1-(7)）|
| f | design.md `:8` と ADR-1085 `:5` の「kgi.md（PO 再確認待ち）」「目標の表の再確認…が決めるまで」| kgi.md `:11` は「2026-11-23 に PO が『1』と答え、PO 承認済み」 | 古い文を直す（ADR-1085 の「PO が決めるまで」から目標の表の再確認を外す）|

一致（確認した行）: `SecretaryChat.tsx:59`・`:66`・`:69-81`・`:83-97`・`:165-169`・`:241-244`・`:255-265`／`useSecretaryListen.ts:115-117`／`secretaryApi.ts:10`／`backend/app/schemas/assistant.py:44`／`secretary-agent/server.mjs:15`・`:131`／`SecretaryDraftInvoice.tsx:113-114`・`:116-120`・`:252-258`／`SecretaryDraftEvent.tsx:46-51`・`:53-56`・`:66-70`／`nginx/nginx.conf:96`・`:100`／`backend/tests/test_secretary_voice_pg.py:104`／`llm_budget.py:56`・`:174-185`・`:441`・`:498`／`backend/app/services/secretary_voice.py:17`・`:22`／`migrations/20261103_120000_create_ai_job_assignments.sql:32`／`docker-compose.yml:98`・`:246`／`tcg_analysis_dashboard.py:939-941`・`:1050`／`backend/tests/test_super_admin_ai_jobs.py:29`／`.github/workflows/deploy.yml:570-575`／`backend/app/routers/assistant.py:89`・`:98-103`／`frontend/src/constants/icons.tsx:416`／`ADR-144-ui-component-governance.md:134`／`scripts/check-ui-governance.js:16-18`・`:47-48`／`.github/workflows/e2e.yml:87`／`frontend/package.json:15`・`:28`・`:48`・`:58`／`frontend/eslint.config.js:31`／`SecretaryChat.test.tsx:501`・`:633`／`docs/handoff/secretary-voice-input/design.md:31`／`secretary.invoice.shippingNoneHelp`（`frontend/src/locales/ja.json:6365`）。`backend/requirements.txt:35` は `google-genai>=1.0.0`（設計の記述どおり。`auth_tokens.create` が使えるかは未確認）。

### (1) kgi.md L1〜L13（PO 承認済み）が本番で○×を一義に判定できるか

**直す必要**（13 本のうち 5 本）。

| # | 判定 | 理由・直し方 |
|---|---|---|
| L1 | 問題なし | 画面を見るだけ |
| L2 | 直す必要 | 「最初の文字が欄に出るまでを見る」とあるが、合格ラインは各 9/10 だけで**何秒以内か・何を出たとみなすか**が無い。待てば出るのも○になる。秒の上限（例: 話し始めから 2 秒）か、「見る」を外して「話し終えるまでに欄に文字が出る」に言い換える。iOS Safari は Siri・音声入力の設定で動かない場合がある（未確認）ので、測る端末の設定を記録する欄を足す |
| L3 | 直す必要 | 「抜けた文」の数え方が無い。ブラウザの聞き間違い（文字が違う）は抜けに数えるのか。**「原稿の文の数と、欄の文の数を比べ、文が欠けた回を×。字の違いは数えない」**と書く |
| L4 | 問題なし | 5 往復＝こちらの 1 発話＋秘書の声の返事 1 回、と 1 行足すとよい（軽い）|
| L5 | **直す必要（重い）** | (a) 「下書きを作らない普通の会話」の中身が無い。Gemini が用事と判断すると道具を呼び 6〜8 秒かかる（design.md `:107`）ので、**道具を呼ばない固定の 20 文の台本**を決める。(b) **L7 と衝突する**（下）|
| L6 | 直す必要（軽い）| 「こちらの声の始まり」を誰が決めるか（画面の音量の検出か Gemini の知らせか）が無い。**測る時刻の取り方を 1 つに決める**。PC のスピーカーで秘書の声をマイクが拾うと自分で割り込む恐れ（未確認）なので、イヤホンなしの PC での測りも 1 回入れる |
| L7 | **直す必要（重い）**| 下の「L5 と L7 の衝突」 |
| L8 | 問題なし | 「窓を開いている間は残る」と一義 |
| L9 | 問題なし | PO の耳で○×（決めること E に結果の扱いがある）|
| L10 | 問題なし | 消音中の文字・反応と、終了後のマイク使用中の印、で一義 |
| L11 | 直す必要（軽い）| 合格ラインに**作られる側の率が無い**（下書きが出る 9/10 のみ）。予定・請求書それぞれ「はい」で作られた回数（例 各 4/5 以上）を足す。部分一致（「はい、続けて」）の 1 語を否定語の試験に足す。「確かめずに作る 0」の定義＝窓の外・足りない間・否定語、と 1 行書く |
| L12 | 問題なし | ただし「続いている LIVE は最長 10 分で切れる」は Google が札の期限で実際に切るかが未確認（§1-(5)）。便 T0 の測りに入れる |
| L13 | 問題なし | 合格ラインは「持ち主を言い当てる」だけ。「いつ戻るか・代わりに何が使えるか」も読めたかを 1 行足すとよい（軽い）|

**L5 と L7 の衝突**（論理）: L7 は「話の途中で 2 秒黙っても打ち切られない」。黙りの長さで話の終わりを決める方式（design.md `:71` の `silenceDurationMs`）では、2 秒の黙りで切れないために 2 秒より長く待つ必要がある。すると、本当に話し終えたときも 2 秒より長く待つので、**「話し終わりから秘書の声が出始めるまで 2 秒以内」（L5）は満たせない**。両方を満たせるのは、黙りの長さでなく「文の意味で終わりを判断する」方式がある場合だけ。OpenAI の `semantic_vad` は【公】（design.md `:71`）だが、Gemini 2.5 Native Audio に同等があるかは未確認。→ **PO が決めること（§3-1）**。便 T0 で L5 と L7 を同じ設定で同時に測る、と書く。

### (2) §5-1 声で作る作り: 請求書を声の「はい」で作ってよいか、画面のボタンだけにすべきか

**直す必要（重い）／PO が決めること**。結論: **請求書は画面の「作る」ボタンだけにし、声の「はい」で作るのは予定だけにすることを推奨する。**

根拠（事実）:
1. **画面で人が必ず触るのは「送料を請求しない」の 1 つだけで、中身の確認にならない**。品目・数量・単価・通貨は AI の下書きの値（`SecretaryDraftInvoice.tsx:66-72`・`:74`）、会社と担当者は候補が 1 件ずつなら自動で選ばれる（`:80-83`・`:99`）、支払い方法は選択肢が 1 つなら自動（`:112`）。`canCreate` は `shippingNone` を含む（`:114`）が、金額・相手を人が見直したことを条件にしてはいない。つまり「画面の条件が揃う」は「人が内容を読んだ」の証拠ではない。
2. **research-2.md §4（`:101`・`:104`）**: 薬局の問診の試作で、ただの読み返しは「はい」の反射で 20 件全部の誤りがすり抜けた。小さな自作の試験で自己申告（同 `:101`）、日本語・請求書の話ではない、と注意が付く。ただし design.md の今の案（中身を読み上げて「作りますか？」→「はい」）はこの「ただの読み返し」の形で、**反射の「はい」を止める仕組みが無い**。完全一致は聞き間違いを止めるだけで、聞き流しの「はい」は止めない。
3. **聞き間違いが 2 回重なる**: こちらの声→Gemini の書き起こし→Gemini が言い換えた文（design.md `:104`）→秘書の AI の下書き。1 回目の審査 (3)-4 の書き起こしの精度は未測定のまま。
4. 得るものが小さい: 請求書は「送料を請求しない」で人が画面を触る必要があるので、ボタンを押すのも 1 回の操作の差。PO の言葉（design.md `:114`「最終的にチャット欄の内容を見て OK だったら作成」）は、画面のボタンでも満たせる。
5. 請求書の作成を取り消せるかは未確認（この審査では `POST /invoices` の取消の道を調べていない）。予定は画面から消せる見込みだが未確認。

**新しい矛盾（直す必要）**: design.md `:105`「結果として Gemini Live に返すのは今の秘書の返事の文（`reply`）だけ。下書きの中身（相手・金額）は返さない」と、`:117`・`:119`「Gemini Live が相手・品目・合計・通貨を読み上げる」は両立しない。**中身を渡されていない Gemini は、自分が言い換えた文を読み上げるだけで、下書きの実物の確認にならない**。中身を渡すなら `:105` の「結果の文に命令が紛れても道具が 1 つ」の守り方が変わり、相手の会社名・金額が Google に渡る（ADR-1085 `:28` の改めに「秘書の返事の文」とあるのは `reply` 止まり）。直し方: 読み上げの文は**画面が下書きの state から作る**（Gemini が作らない）。声で読み上げるなら、画面が作った文を Gemini にそのまま読ませる道具の結果として渡すか、`ChatBubble` に画面が出す。どちらでも、ADR-1085 の改めに「下書きの中身の扱い」を 1 行足す。

予定の声の「はい」は、窓・完全一致・否定語の試験が書かれており、`canCreate` が人の確認を要求しない予定（`SecretaryDraftEvent.tsx:46-51`）では声の「はい」が唯一の確認になる点だけ注意（反射の「はい」の恐れは残る。予定は Meet を付けうる `:66-67` ので外への作用がある）。**予定の声の「はい」は、便 T0 で L11 の否定語の試験と、「わざと違う日時を読み上げる」試験（人が気づくか）を各 5 回測ってから、便 B に進む**、と書く。

### (3) §6-6 上限の持ち主の表の穴

**直す必要**。

| 穴 | 事実・直し方 |
|---|---|
| 同じ Google の鍵で動く他の機能への巻き込み | LIVE も翻訳・抽出も同じ `GEMINI_API_KEY`（`docker-compose.yml:98`）。design.md `:82` は「Google の請求先の月の上限に届くと翌月 1 日まで**全部の API が止まる**」と書く。LIVE の使いすぎ（申告漏れで台帳が実際より少ない場合）でお客さんの翻訳が止まる恐れ。直し方: LIVE 専用の Google のプロジェクトと鍵に分ける案を PO に聞く（§3-3）。分ければ Google の請求と台帳の照らし合わせ（§11）も「LIVE の分」だけで比べられる（同じ鍵だと翻訳・抽出と混ざって差の 1 割が測れない）|
| 「いつ戻るか」の時刻 | 表は「来月 1 日」「翌月 1 日」とだけ。社内の上限は日本時間の月初（読み上げは `secretary_tts.py` が日本時間の今月 1 日 0 時から数える。recon.md `:131`）。Google 側の月の区切りの時刻は未確認（太平洋時間の可能性は未確認）。画面の文に出す「戻る日時」は**社内の上限のときだけ日本時間で出し、Google の上限は「来月」とだけ出す**と書く |
| 鍵が未設定・Google が鍵を断る（認証の失敗）| 表に無い。札の口が `503 not_ready` 相当を返す（読み上げは `503 tts_not_configured` が前例）。**「準備ができていません」の文**を表に足す |
| LIVE を切った（旗）| LIVE のボタンが消えるだけで、文は出ない。許容（問題なし）。ただし §1-(2) の e のとおり、LIVE 専用の旗が無いと文の秘書ごと消える |
| 警告の出し方 | `Callout`（`components/Callout.tsx`）の存在を無視している（上の c）。`role="alert"` の warning か `role="status"` の info かを、持ち主ごとに決める |
| 並行の上限 | Google の「同時につなげる数」の上限【未】。表に足さない理由を書く（社内数人のため）か、便 T0 で見る |

### (4) 月の上限と台帳の型が ADR-1004・1080 に合うか

**直す必要（重い）**。型の骨格（1 回＝1 行・上限は backend の定数・毎月 Google の請求と照らす）は ADR-1080 `:14-20`・`:33` と合う。合わないのは次。

1. **`outcome` の仮の値が入らない**。design.md `:148`・§6-1 は仮の行の `outcome` を「始めの印」とする。実物は `outcome IN ('ok','failed')`（`migrations/20261103_120000_create_ai_job_assignments.sql:128-129`）で、さらに `(outcome='ok' AND error_code IS NULL) OR (outcome='failed' AND error_code IS NOT NULL)`（同 `:143-144`）。仮の行（`pending` 等）を入れるには `outcome` の CHECK と**組み合わせの CHECK の作り直し**が要る。design.md の migration は「台帳の値の追加」（`:223`）とだけ書く。
2. **`error_code` は 9 つに閉じている**（`:133`・`docs/adr/ADR-1058-ai-job-assignments.md:24`: `auth_failed`・`timeout`・`rate_limited`・`http_error`・`unreadable`・`tool_used`・`not_ready`・`busy`・`other`）。design.md `:186` は「Google からの印をそのまま `error_code` に残す」と書くが、**入らない**。上限で断った・つなげなかった・10 分で切れた等の値を足す CHECK の作り直し、または Google の生の印を入れる別の列（`source_ref` は既存の TEXT。`migrations/20260930_150000_create_llm_usage_events.sql:42`）が要る。ADR-1058 `:24` は「API を呼んでいない失敗と打ち切りは書かない」とも決めていて、design.md §6-3 の「上限で断った」も 1 行にする案と食い違う。ADR-1085 の改める点に ADR-1058 のこの決まりが無い。
3. **列が足りない**。台帳の量の列は 6 種のトークンだけ（`migrations/20260930_150000_create_llm_usage_events.sql:35-40`）。design.md §6-3 の「音声・文字の内訳から計算」に使った内訳と、§11 `:244` の「速さの ms を台帳の行に残す」の**置き場が無い**。計算の根拠（音声の秒・トークン）が行に残らないと、毎月の照らし合わせで差が出たとき原因が追えない。→ 列を足す（`ADD COLUMN IF NOT EXISTS` の型は `migrations/20261117_100100_add_llm_usage_tts_characters.sql:2`）。1 回目の審査 (4)-4 の「1 行に残す量の列」はこの形で未解決のまま。
4. **migration の大きさと GO**: 上の 1〜3 を入れても、`DROP CONSTRAINT IF EXISTS` で作り直す形は既存の型（`migrations/20261117_100100_add_llm_usage_tts_characters.sql:17`・`:35`）と同じで、ADR-1003 の例外（`docs/adr/ADR-1003-go-delegation-to-opus.md:31-39`: DROP TABLE／DROP COLUMN を含む migration 等）には当たらない（読み）。委任の GO で足りるという ADR-1085 `:54` の読みは**妥当**。ただし「値を足すだけ」の文は「CHECK の作り直し＋列の追加」に直す。便 T1 の `migrations/` 入りの PR は、GO まで main に入れない（AGENTS.md）。
5. **仮の行の上限の穴**（設計の直し）:
   - **使わなかった札が上限を食う**: 札を取っただけで LIVE を始めなかった場合、使用量の報告が来ないので仮の行は最大のまま残る（design.md `:149`）。月 1,000 円の案（§12-C）で 1 回の最大が高めなら、札を数回取るだけで上限に届く（札の口は 1 人 1 時間 20 回まで）。直し方: **つないだ時に画面が「始めた」を使用量の口に送る**。札のつなぎ始めの期限（1 分）を過ぎても「始めた」が来ない行は 0 円に直す（札は 1 回しか使えず、期限後はつなげないので請求が立たない。つなぎ始めの期限の仕様は【公】だが実際の挙動は便 T0 で確かめる）。
   - **同時に取る競争**: 「今月の合計＋次の最大が上限を超えるなら出さない」を SELECT して INSERT する間に、別の札の口が割り込むと両方が通る。直し方: 同じ取引の中で合計を数える前に advisory lock を取る（または月ごとの 1 行の集計行を `FOR UPDATE` する）。
   - **合計を読めないとき**: 読み上げは字数を読めなければ 503 で Google を呼ばない（recon.md `:131`・ADR-1080 `:20` の型）。LIVE も**合計を読めなければ札を出さない**と書く（今は書かれていない）。
   - **誰の回数か**: 札の口の「1 人 1 時間 20 回」（design.md `:132`）の数え先が未定。台帳には user の列が無い。直し方: 仮の行を数える（`source_ref` に user id を入れる等）か、別に置く。置き場を書く。
   - 画面が送る申告値は改ざんされうるが、LIVE を使えるのは super admin だけ（`_SECRETARY_DEPENDENCIES`・`assistant.py:98-103` の `require_super_admin`）なので、実際の危険は小さい。この条件は ADR-1085 に書いておく（広げるときに再審査）。
6. **sdk の写し**: `USAGE_SDKS`（`llm_budget.py:174-176`）に `google-genai-live` を足すとき、`USAGE_SDKS_BY_PROVIDER`（`:180-185`）の `gemini` の集合に**入れると**、画面の「AI の担当」タブの Gemini の回数・ログインの○×に LIVE が混ざる。入れないなら `test_super_admin_ai_jobs.py:29`（`USAGE_SDKS`・`USAGE_SDKS_BY_PROVIDER` を読む）の期待を確かめる。どちらにするかを書く（本審査では試験の本文を全部は読んでいない＝未確認）。
7. ADR-1004 Decision 2（`docs/adr/ADR-1004-llm-usage-ledger.md:26`「応答を受け取り usage を読めた時点で、呼び出し元と同じ取引で 1 行書く」）に対し、**仮の行を後から UPDATE する**のは初めて。ADR-1085 `:35` に書いてあるが、「UPDATE できる列の範囲（最大→本当の値の 1 回だけ）」を書く（二重の報告で値が変わらないように）。

### (5) CSP と鍵を画面に出さない札の穴

**直す必要（軽〜中）**。

- CSP（`nginx/nginx.conf:96`）: `connect-src` に `wss://generativelanguage.googleapis.com` を足す案と、AudioWorklet を `frontend/public/` の同じ場所のファイルにして `script-src 'self'` を緩めない案は、設計として筋が通る。足りるかは便 T0 の実機で確定、と書いてあり（design.md `:138`）妥当。マイクの許可は `:100` で済み。
- 札の設定（`uses=1`・つなぎ始め 1 分・期限 10 分・モデルと指示文と道具を `liveConnectConstraints` で固定・回数の上限）は、1 回目の指摘を満たす。残り:
  1. **札の期限（10 分）で、つないでいる最中の LIVE が実際に切れるか**は未確認。「つなぎの期限 `expireTime` の意味」が「つなぎ始めまで」か「切れるまで」かで、L12 の「最長 10 分で切れる」（kgi.md `:36`）が成り立つかが変わる。成り立たないと、画面が閉じない LIVE は札を渡した後に backend が止められない（直通のため）。**便 T0 の測りに「期限で切れるか」を入れる**。成り立たない場合の備え（画面の 10 分の自動終了＋Google の使用量の見張り）も書く。
  2. 札を取る口 `POST /api/v1/assistant/live/session` が `google-genai>=1.0.0` で使えるか・版固定（design.md `:134`）は便 T0 の最初に確かめる。使えない版で T0 が止まるのは、便 T0 の最初の 1 日の作業として計画に入れる。
  3. 札が漏れても、モデル・指示文・道具が固定なので別用途には使えないが、**固定された道具「秘書に頼む」の中身は Gemini が決める文**で、画面が本人のログインで秘書の口に送る。Gemini が 1 回の会話で道具を何度も呼ぶと、秘書の容器は同時 1 本・80 秒（ADR-1056、recon.md `:100`）なので `429 busy` になる。画面で道具の呼び出しを 1 本ずつ直列にし、`busy` は声で「少し待って」と返す、と書く。
  4. 札の口・使用量の口の試験（§11 `:243`）に、**使用量の口が別人の札の番号を受けても書き換えない**（本人の札の行だけ）を足す。
  5. 鍵は backend と celery-worker の両方に渡っている（`docker-compose.yml:98`・`:246`、1 回目の審査 (5)-4）。LIVE は backend だけが使う、と書く。分けるかは §3-3。

### (6) §11・§16 続けるための機械の仕組み（機械で止まる／人の審査だけ／手作業）

**直す必要**。分けると次のとおり（実物で確かめたもの）。

| 守るもの | 今の仕組み | 区分 | 足りない所と足し方 |
|---|---|---|---|
| ja・en の鍵の食い違い | `check:i18n-missing-keys`（`frontend/package.json:28`）が `check:all`（`:48`）に入り、CI の `lint-run`（`.github/workflows/e2e.yml:65`・`:87`）が走らせる。必須チェック名は「Lint & Dark Mode Check (ADR-067)」（同 `:130`。コメント `:24-25` に必須チェックの記載）| **機械で止まる**（実物どおり）| なし。ただし必須チェックに入っているかは Ruleset の実物で確かめていない（Ruleset は読めない＝未確認）|
| 日本語の直書き | `local/no-japanese-literal` は warn（`frontend/eslint.config.js:31`）。CI の `lint` は `eslint src`（`frontend/package.json:15`）で警告では落ちない。手元の commit は lint-staged `--max-warnings=0`（`:58`）で止まるが、`frontend/node_modules` が無いと飛ばす（`frontend/.husky/pre-commit:46-50`）| **warn だけ・手元は条件付き**（design.md の記述どおり）| design.md は「便 T0 の画面の試験に 0 件を足す」とする。より確実な足し方: **`frontend/eslint.config.js` に `src/features/secretary/**` だけ `error` にする override を足す**（`eslint.config.js:244`・`:252` に `off` の override の前例がある）。CI の `lint-run` が落ちるので必須チェックで止まる。便 T0 の PR に入れる。画面の試験で数えるより軽い |
| 金型外の見た目（生の部品・色の直書き）| ADR-144 の検査は `pages/` だけ（`docs/adr/ADR-144-ui-component-governance.md:134`・`scripts/check-ui-governance.js:47-48`）。色・寸法の直書きは ADR-067 の検査（`check:css-colors`・`check:css-values` が `check:all` に入る・`frontend/package.json:48`）| **色・寸法は機械で止まる／生の `<select>`・`<input>` などの部品は人の審査だけ** | design.md は「色の直書き」まで人の審査と書く（§9 `:216`）が、**色と寸法の直書きは ADR-067 の検査が見る**（`check:css-colors`・`check:css-values`。見る範囲の実物は本審査で全部は読んでいない＝未確認）。人の審査に残るのは生の部品と金型の選び方。審査役の点検の文面を「生の部品が無いこと」に絞る |
| 台帳の値の写し | `test_secretary_voice_pg.py:104` が CHECK と `USAGE_PURPOSES` を比べる（CI 専用の DB。`needs_ci_pg`）| **機械で止まる** | sdk の集合の比べもある（`:104` 付近）かは本審査で全文を読んでいない。足す値は両方の写しを更新する |
| 月の上限・仮の行・札の口・鍵の漏れ | 便 T1 で新しく作る `backend/tests/test_secretary_live.py` | **まだ無い（機械にする予定）** | §1-(4)-5 の穴（使わなかった札・同時の競争・合計を読めない）の試験を足す |
| AI が勝手に作らない・声の一致 | 便 T0 で新しく作る `SecretaryLive.test.tsx` | **まだ無い（機械にする予定）** | §1-(2) の「読み上げの文は画面が作る」の試験を足す。画面の試験は Gemini を偽物に差し替える、と書く（本物の Gemini では CI で測れないため、L11 は本番の人の測りが正本）|
| 速さ（L5・L6）| 画面が ms を記録して台帳へ | **まだ無い** | 台帳に列が無い（§1-(4)-3）。便 T0 は記録だけ、でよいが、記録の置き場（列か別の記録）を決める |
| 費用の照らし合わせ | 毎月 1 回、手作業（ADR-1080 と同じ日）| **手作業・関所なし** | 差の許容幅（1 割）は書かれた。**照らした記録の残し先**（例 `docs/handoff/secretary-live/` に月ごと）と、忘れたときの気づき方（未実施を見つける仕組み）が無い。毎月の予定を `docs/runbooks/` の既存の定期の手順（`runbooks/weekly-stale-tasks.md`）の型に載せるか、手作業と書く |
| 決まりの索引 | `docs/adr/FEATURE-INDEX.md:77` に ADR-1085 を足す | **人が足す** | 便 T0 の PR の作業に入っている。ADR の索引は `node scripts/generate-adr-index.js` で機械が直す |
| 維持の仕組み欄 | process-artifacts の関所（`scripts/check-process-artifacts.js:1443-1474`）| **警告モード**（`:1617-1625`）| 関所は `## …維持の仕組み…` の見出し（`:1448`）の下の**「守り手:」の行**（`:1458`）を探し、そのパスの実在を見る（`:1474`）。design.md §16 は表で、**「守り手:」の行が無い**。しかも表のファイルは便 T0・T1 で作る未来のファイル。今あるファイル（例 `.github/workflows/e2e.yml`）を「守り手:」の行に 1 本書き、表は残す |
| 親→子のリンク | 文章規約（`docs/STANDARD-WORKFLOW.md:43-50`。機械強制ではない）| **人の規約** | `docs/specs/secretary-chat/README.md` に `docs/handoff/secretary-live/` へのリンクが無い（`git show origin/release/secretary-live-design:docs/specs/secretary-chat/README.md` で LIVE の語は 0 件）。**親に子の一覧を足す**（1.6 の双方向）。`ideal-state.md` に LIVE のあるべき姿を足すかも PO に聞く（1 回目の審査から未解決）|

足りない仕組みの要約: (a) 日本語の直書きを `features/secretary/` だけ error にする（機械に格上げ）、(b) 上限・札の口の試験に使わなかった札・競争・合計を読めない場合を入れる、(c) 照らし合わせの記録先、(d) 維持の仕組み欄の「守り手:」の行、(e) 親の README に子へのリンク。

### (7) 便 T0〜C の分け方と migration の GO

**問題なし（分け方）／直す必要（軽い・migration の中身と GO の表現）**。

- 分け方（T0 試作・台帳と上限なし・migration なし → T1 台帳・上限・migration → B → C。A は独立）は、1 回目の指摘 (6) を満たし、筋が通る。
- 直す所: (a) T1 の migration は「値を足すだけ」でなく **CHECK の作り直し（outcome・error_code・purpose・sdk）＋列の追加**（§1-(4)）。DROP TABLE／DROP COLUMN は含まないので ADR-1003 の委任の GO で足りる見込み（上のとおり）。ただし `DROP CONSTRAINT` を含むので、PR 本文で「構造を消す文ではない」と明記する。(b) T0 の「機能の旗は PO の会社だけ」: 秘書の旗は今 tenant 4 だけ（`migrations/20261101_120000_enable_secretary_chat_tenant4.sql:10`）で、使える人も super admin だけ。T0 は**新しい LIVE 専用の旗**（行）を足し、その有効化の INSERT の置き場（運用の INSERT か migration か）を決める。migration にするなら T0 は「migration なし」でなくなる。直し方: 旗の行は運用の INSERT（開発フェーズでは継続できる。AGENTS.md「本番運用フェーズ移行後に effective」）と書くか、T0 の migration 1 本を認める。(c) 便 C が `声で返事` を消す前に、L1 の前提（LIVE が実用になる）を T0 の実測の結果で確かめる条件を書く（C は B の後、は書かれている）。
- **便 T0 の前の PO の了承**（有料の声の AI・費用）は §10 `:229` に書かれ、妥当。T0 の費用は台帳に入らず Google の請求画面で照らす、も妥当。ただし **T0 は札の口を本番に出す**ので、「便 T0 の PR は backend の口を含む＝ユーザーに影響する変更の GO 記録が必要」（`docs/STANDARD-WORKFLOW.md` の完了の定義）も §10 `:230` のとおり。

### (8) 未確認の点が実装可否を左右するか

| 未確認の点 | 左右するか | 判定 |
|---|---|---|
| Gemini 2.5 Native Audio の遅さ（【未】`design.md :69`）| **左右する**（L5。② への切り替えは作り直し）| 問題なし（便 T0 で測る前提）。ただし L7 との衝突（§1-(1)）が先 → **PO が決めること**（§3-1）|
| 札の期限で実際に切れるか・`auth_tokens.create` が `google-genai>=1.0.0` で使えるか | **左右する**（L12・L13 の「10 分」・札の口が作れるか）| 問題なし（便 T0 で測る前提）。**測りの項目に「期限で切れるか」を入れる**（§1-(5)）|
| Google の鍵が有料枠（学習に使われない枠）か | **左右する**（ADR-1056 の改めの根拠）| **PO が決めること A**（design.md `:250`。台帳の $40.55 は計算値で証拠にならない、の書き方は正しい）|
| 同じ鍵・同じ請求先で他の機能（翻訳・抽出）が巻き込まれる | 実装は左右しない。**運用の事故の大きさを左右する** | **PO が決めること**（§3-3）|
| iPhone のホーム画面アプリの聞き取り・消音スイッチ | (A) の対象を左右 | 問題なし（PO の決め D・便 T0 の実機）|
| ChatGPT の無料分・契約（§12-H）| ① か ② かを左右するが、PO は「Business を使う予定・席は T0 で測ってから」と答え済み | 問題なし。ただし**両方の速さ・費用を同じ台本で測る**ため、便 T0 の作りが ① と ② で 2 回分になる恐れ。T0 を ① だけにし、L5 が満たされないときに ② の T0' を作る、と書いてあるので（design.md `:231`）それで足りる |
| 長い文の動作（容器 80 秒・body 15,000 バイト）| (A) の長さ | 問題なし（便 A の前に測る、と書かれている）|

## 2. 「直す必要」の一覧（設計担当が直すもの）

1. design.md §5・§5-1: 声で読み上げる中身の出どころの矛盾（`:105` と `:117`・`:119`）を直す。読み上げの文は画面が下書きの state から作る。ADR-1085 に「下書きの中身の扱い」を足す。
2. design.md §5-1・kgi.md L11: 請求書の「作る」は画面のボタンだけにするかを PO に聞き、**推奨を書く**（§3-2）。予定の声の「はい」は便 T0 で否定語とわざと違う日時の読み上げを測ってから便 B に進む。
3. kgi.md: L2（秒の上限）・L3（抜けの数え方）・L5（台本・L7 との両立）・L6（時刻の取り方）・L11（作られる側の率・部分一致）を一義にする。
4. design.md §6・ADR-1085: 台帳の `outcome`（仮の値）・`error_code`（足す値）・列（音声の内訳・ms）・組み合わせの CHECK を migration に入れる。ADR-1058 `:24` の決まりを改める点に足す。「値を足すだけ」の文を直す。
5. design.md §6-1・§6-2: 使わなかった札の仮の行（「始めた」の報告）・同時に取る競争の錠・合計を読めないとき札を出さない・回数を数える置き場。
6. design.md §6-6・§15・§6-2: `Callout` を使う・LIVE 専用の旗の行・「来月 1 日」の時刻の書き方・鍵が未設定の行。
7. design.md §5-2・§10 の便 T0: 札の期限でつないでいる LIVE が切れるかを測りに入れる。使用量の口は別人の札で書き換えない試験。
8. design.md §11・§16: 日本語の直書きを `features/secretary/**` だけ error にする（機械に格上げ）・「守り手:」の行・親の README に子へのリンク・照らし合わせの記録先。色・寸法の直書きは ADR-067 の検査が見る、と書き直す。
9. file:line: 上の a（`:78`→`:76`・`:114`）・b（`:225-250`→`:225-241`）・d（OAuth の 0 件の文）・f（PO 承認済みの文）。
10. ADR-1085: 「LIVE を使えるのは super admin だけ（広げるときは再審査）」を書く。

## 3. PO が決めること

1. **L5（2 秒）と L7（2 秒の黙りで切れない）のどちらを優先するか**。黙りの長さで切る方式では両立しない。案: L7 を優先して L5 を「話し終わりから 3 秒以内」に緩める／便 T0 で Gemini に文の意味で終わりを判断する設定があるかを測り、あればそれで両立／無ければ L5 を緩める。推奨: 便 T0 で先に測り、無ければ L7 を優先（考える間で打ち切られないが PO の願い、kgi.md `:17`）。
2. **請求書を声の「はい」で作るか、画面のボタンだけにするか**。推奨: **画面のボタンだけ**（根拠は §1-(2) の 1〜4）。予定は声の「はい」を残してよい（便 T0 で測ってから）。PO が声の「はい」を請求書にも使うと決めるなら、読み上げの文を画面が作る・反射の「はい」を止める仕組み（読み上げ後に金額を声で言い直させる等）を設計に足す。
3. **LIVE 専用の Google のプロジェクト・鍵を作るか**。推奨: 作る（翻訳・抽出が巻き込まれず、請求の照らし合わせが LIVE の分だけでできる）。作るなら鍵の置き方（`docker-compose.yml:98` の外・secrets の入れ方）は PO 本人の作業（AGENTS.md の secrets の決まり）。
4. 既存の決めること A〜H（design.md §12）は審査の前提どおり。C（月の上限）は §1-(4)-5 の直しの後に、便 T0 で測った 1 回の最大の費用で決め直す。

## 4. 問題なしと確認した点

- design.md が引いた file:line は、§1 の表の 6 件（a〜f）以外は origin/main の実物と一致した。
- 骨格（Gemini Live は聞く・話す・割り込み・書き起こしだけ・秘書の仕事は今の `POST /assistant/messages` に任せる・作成は画面）は、データの写しも AI の書き込みの道も増やさない（ADR-1056 `:18`）。
- 秘書の口の守り 4 つ（`assistant.py:98-103`）を札の口にも使い回す案、`microphone=(self)` が既にある（`nginx/nginx.conf:100`）点、AudioWorklet を `frontend/public/` の普通のファイルにする点、nginx の配備の注意（`deploy.yml:570-575`）は妥当。
- 台帳の値の追加を、既存の型の冪等な migration（`migrations/20261117_100100_add_llm_usage_tts_characters.sql`）に沿わせる方針と、ADR-1003 の例外に当たらず委任の GO で足りるという読みは妥当（中身の大きさは §1-(4) 4）。
- 便の分け方（T0 → T1 → B → C・A は独立）、戻し方（旗・便ごとの revert・冪等 migration・上限の定数）の方向、外の事例の正直な書き方（失敗の 3 件目が見つからなかったと書いた・research-2.md の数値は検索要約と明記）は妥当。
- 製品のコード・DB・本番・secrets には触っていない。審査役の本番の読み取りも行っていない。
