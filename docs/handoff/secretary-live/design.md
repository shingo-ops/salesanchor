# 秘書チャットの「マイク（A）」と「LIVE（B）」— 設計（草案・PO 未承認）

この文書は何か: 秘書のチャットで、話しながら文字が出るマイクと、声どうしで話せる LIVE を作るための設計図です。
親（あるべき姿）: [docs/specs/secretary-chat/README.md](../../specs/secretary-chat/README.md)

- 状態: 設計案作成済み・設計審査 1 回目 REVISE・2 回目 REVISE（[review-architect-2.md](review-architect-2.md)）・3 回目 REVISE（[review-architect-3.md](review-architect-3.md)・小さな直し）・4 回目 REVISE（[review-architect-4.md](review-architect-4.md)・便 A は合格・ADR 番号の衝突ほか）→ 指摘を直した 5 版・PO の決め 3 件済（L5/L7・請求書はボタン・目標の表）・実装未着手
- 書いた人: Claude Opus（設計担当）2026-11-22
- 目標: [kgi.md](kgi.md)（PO 承認済み 2026-11-23）／現在地: [recon.md](recon.md)（docs/handoff/secretary-live/recon.md）／外の事例: [research.md](research.md)
- 決まりの案: `docs/adr/ADR-1087-secretary-live-voice.md`（Proposed・草案）
- 関わる決まり: ADR-1056（秘書・AI に渡すのは文と今だけ・作成は「作る」）、ADR-1058（秘書の AI の選び方）、ADR-1080（読み上げ・台帳・月の上限）、ADR-1082（聞き取り・マイクの許可）、ADR-1004（使用量台帳）、ADR-1062（Gemini の道の自動切替）、ADR-027（翻訳）、ADR-067・ADR-144（金型・デザイントークン）、ADR-135・ADR-136（migration 入り PR の GO）、ADR-1003（GO の委任）

---

## 0. 審査 1 回目の指摘と直した場所

| 指摘（review-architect.md §2） | 直した場所 |
|---|---|
| 1 KGI の測り方が 7 本あいまい | kgi.md §2（L2・L3・L5・L6・L8・L10・L12）|
| 2 声の「はい」の仕様・請求書の安全の条件 | §5-1（請求書は声で作らない・予定だけ・完全一致・窓・否定語の試験・`submit` を外へ出す改修）|
| 3 使用量の入り口・上限の置き場・値段表・失敗の行・費用の画面 | §6 |
| 4 AudioWorklet・札の設定の固定・札の口の回数 | §5-2・§5-3 |
| 5 ADR の改めの不足（1056・1058・1004・1080）| ADR-1087「改める点」|
| 6 便 T を T0・T1 に分ける | §10 |
| 7 維持の仕組み欄・親リンク・1 行説明・ADR-144 の「ある」の過大 | 冒頭・§11・§16 |
| 8 料金の出どころの書き分け | §4 |

### 0-2 審査 2 回目の指摘（review-architect-2.md §2）と直した場所

| 指摘 | 直した場所 |
|---|---|
| 1 読み上げの中身の出どころの矛盾 | §5（予定の読み上げの文は画面が作る・請求書の中身は Gemini に渡さない）・ADR-1087 改める点 |
| 2 請求書は声で作るか | PO 2026-11-23「1」: 請求書はボタンだけ。§5-1・kgi.md L11。予定の声の「はい」は便 T0 で否定語とわざと違う日時を測ってから便 B |
| 3 KGI の L2・L3・L5・L6・L11 | kgi.md §2（L5 と L7 は PO 2026-11-24「1」）|
| 4 台帳の CHECK・列 | §6-3（outcome・error_code・purpose・sdk の作り直しと列の追加）・ADR-1087 改める点に ADR-1058 |
| 5 上限の穴（使わなかった札・競争・合計を読めない・回数の数え先）| §5-2・§6-1・§6-2 |
| 6 `Callout`・LIVE 専用の旗・戻る時刻・鍵が無いとき | §6-6・§6-2・§15 |
| 7 札の期限で切れるか・別人の札の試験 | §5-2・§10・§11 |
| 8 日本語の直書きを止める・守り手の行・親のリンク・照らし合わせの記録先・色の検査 | §9・§11・§16・`docs/specs/secretary-chat/README.md` |
| 9 file:line の a・b・d・f | §3・§12-H・冒頭 |
| 10 使えるのは super admin だけ | ADR-1087 |

### 0-3 審査 3 回目の指摘（review-architect-3.md §2）と直した場所

| 指摘 | 直した場所 |
|---|---|
| R1 予定の「はい」を読み上げた下書きに結ぶ・読み上げに入れる項目・読み上げの忠実さ | §5-1 の 1・5〜7・§10・§11・kgi.md L11 の「確かめずに作る」・ADR-1087 Decision 3 |
| R2 新しい列の読み取りビューの分類 | §6-3・§10・§11 |
| R3 migration の作り方（定義を読んで作り直す・全値＋新値・登録）| §6-3 |
| R4 日本語の直書きの override の便・札の口の試験の便・台本 20 文 | §9・§10・§11 |
| R5 既存の AI の費用の合計に LIVE が混ざるか・Live の単価 | §6-4 |
| R6 読む口は書き換えない | §6-1 |
| R7 file:line 4 件 | §9（検査ごとに分けて引く）・§10・§12-G・§6-2 |

### 0-4 審査 4 回目の指摘（review-architect-4.md §3・§4）と直した場所

| 指摘 | 直した場所 |
|---|---|
| N1 ADR の番号 1085 が main で別の決め（ブラウザ操作の委任）に使われていた | 秘書 LIVE の ADR を **ADR-1087** に付け替え（main の最大は 1086・開いている PR に 1087 以上は無いことを 2026-11-24 に確かめた）。本文・この設計・カード・`docs/specs/secretary-chat/README.md` を揃えた。審査 1〜4 回目の記録の中の古い番号は記録のまま残す |
| N2 読み上げの文の「相手」 | §4 の例外の行・ADR-1087 の改める点を §5-1 の 1 の言い方に揃えた |
| N3 聞き直しの上限・override は試験を除く | §7・§9・§16 |
| a〜c 行番号 3 件・N4 受け口の書き方 | §7（`:716`）・`docs/handoff/secretary-live/card-binA.md`（C1〜C3）|

## 1. 目的と、利用者に見える変化

| | 今 | 後 |
|---|---|---|
| 声で返事 | チェックを入れると返事を読み上げる | チェックは消える（LIVE に置き換わる）|
| マイクの印 | スマホだけ。1 回区切りで止まる（`frontend/src/features/secretary/useSecretaryListen.ts:117` `continuous=false`）| PC とスマホ。押している間、話す端から欄に文字が出続ける。押し直すと止まる |
| 声どうしの会話 | 無い | 入力欄の横の LIVE ボタン。話す・割り込む・黙っても続く・両方の文字が会話に残る・消音・終了 |
| LIVE 中の仕事 | — | 予定・請求書の下書きは今と同じ吹き出しで出る。予定は画面の作る条件が揃った後に、声の「はい」か「作る」ボタンで作る。請求書は「作る」ボタンだけで作る（PO 2026-11-23「1」） |

## 2. 対象と対象外

- 対象:
  - 画面: `frontend/src/features/secretary/`（LIVE の部品・聞き取りの部品・予定の下書きの部品の「作る」の口を外へ出す改修）、`frontend/public/` に音の処理のファイル（§5-3）、翻訳。
  - backend: `backend/app/routers/assistant.py` に LIVE の口 2 つ（札を出す・使用量を受け取る）、backend/app/services/secretary_live.py（新・上限と仮の行）、`backend/app/services/llm_budget.py`（値段表の音声の単価・sdk の対応）、`backend/app/routers/tcg_analysis_dashboard.py`（LIVE の今月の費用を出す）。
  - DB: migration 2 本（どちらも便 T0）: LIVE 専用の旗の行（会社 4 だけ）と、台帳の CHECK の作り直し・列の追加（§6-3）。
  - 設定: LIVE 専用の鍵の環境変数 `GEMINI_LIVE_API_KEY` を backend だけに渡す（`docker-compose.yml`。値を入れるのは PO・§5-2）。
  - nginx: CSP の `connect-src` 1 か所（`nginx/nginx.conf:96`）。
  - 試験。
- 対象外: kgi.md §3 のとおり。秘書の文の AI（本番は容器 `secretary-codex`・ChatGPT の無料プランのログイン・§4-1 の 2026-11-24 直し）は変えない。AI の担当表（ADR-1058）には LIVE を入れない（§6-5）。

## 3. 現在地の要点（recon.md の事実）

- マイクの印はスマホだけ: `frontend/src/features/secretary/SecretaryChat.tsx:255-265`。声で返事: `:59`・`:66`・`:83-97`・`:241-244`。
- 聞き取りは Web Speech API、日本語固定、1 回区切り: `frontend/src/features/secretary/useSecretaryListen.ts:115-117`。
- 送れる文は 1,000 字まで: 画面 `frontend/src/features/secretary/secretaryApi.ts:10`・backend `backend/app/schemas/assistant.py:44`（`max_length=1000`）。
- 秘書の返事は容器の AI が文 → JSON を一括で返す（`secretary-agent/server.mjs:131`）。流れる声を扱う口は無い。返事まで 5〜8 秒。
- 会話は画面の state だけに持ち、窓を閉じると消える（`frontend/src/features/secretary/SecretaryChat.tsx:69-81` の `close()`）。
- 請求書の「作る」は部品の中の `canCreate`（`frontend/src/features/secretary/SecretaryDraftInvoice.tsx:113-114`）が真のときだけ押せ、人が「送料を請求しない」にチェックすることが条件に入る（state `:76`・条件 `:114`・チェックの部品 `:252-258`）。予定の「作る」は `frontend/src/features/secretary/SecretaryDraftEvent.tsx:46-51`・`:53-69`。
- 本番の画面は `connect-src 'self'`・`script-src 'self'`（`nginx/nginx.conf:96`）。マイクは `microphone=(self)` で許可済み（`:100`）。
- 台帳 `public.llm_usage_events` の purpose・sdk は DB の CHECK で固定。値を足すには CHECK を作り直す migration が要る（型: `migrations/20261117_100100_add_llm_usage_tts_characters.sql`）。CHECK と写しの一致の試験: `backend/tests/test_secretary_voice_pg.py:104`。
- 値段表 `LLM_PRICING`（`backend/app/services/llm_budget.py:56`）は 1 モデルにつき入力・出力の 2 単価。`calculate_usage_cost`（`:225-241`）は音声と文字を分けない。
- 読み上げの月の上限は定数 `MONTHLY_CHAR_CAP = 900_000`（`backend/app/services/secretary_voice.py:22`）。読み上げは AI の担当表に入っておらず（担当表の仕事の一覧は `migrations/20261103_120000_create_ai_job_assignments.sql:32`）、provider `google_tts` は `backend/app/services/llm_budget.py:184` の対応にだけある。
- backend は Gemini の鍵を持つ（`docker-compose.yml:98`・`:246`）。台帳の Gemini の 30 日の合計は $40.55（本番台帳の読み取り 2026-11-22）。**これは値段表から計算した値で、請求書ではない**（`backend/app/services/llm_budget.py:225-241`）。有料枠か・学習に使われないかの証拠にはならない → PO が Google の請求画面で確かめる（§12-A）。

## 4. やり方の比べ（費用・速さ）

為替は 1 ドル = 159 円（XE 2026-11-18 の 159.3 円を丸めた値）。「1 分」は、こちらが 30 秒・秘書が 30 秒話した 1 分。**会話の履歴が毎回のやりとりで入力として数え直されるため、実際の費用はこれより上がる。どれだけ上がるかは便 T0 で測る**（推測で倍率を書かない）。

出どころの印: 【公】= Context7 で Google・OpenAI の公式の文書を読んだ（2026-11-21・11-22）／【三】= 第三者の測定／【未】= 確かめていない。料金の公式ページそのものは直接開けていない（research.md `:5-6`）。料金の値は【公】の文書の中の値で、**便 T0 の前に Google の料金ページで再確認する**。

| | ① Gemini Live（2.5 Flash Native Audio）| ② OpenAI Realtime（gpt-realtime-2）| ③ 無料の組み合わせ |
|---|---|---|---|
| 1 分の費用（履歴の数え直しを除く下限）| 【公】入力 $0.0045/分・出力 $0.018/分 → 約 $0.011（約 1.8 円）| 【公】入力 $0.0192/分・出力 $0.0768/分 → 約 $0.048（約 7.6 円）| 0 円 |
| 返事が出始めるまで | 【三】p50 1,242ms（別の版 Gemini 3.8 Live の値）。2.5 は【未】| 【三】p50 1,022ms | 今の 5〜8 秒 |
| 割り込み | 【公】あり（`serverContent.interrupted`）| 【公】あり | 読み上げ中はマイクを閉じる（ADR-1082 設計 `docs/handoff/secretary-voice-input/design.md:31`）→ 割り込めない |
| 考える間 | 【公】黙りの長さを設定（`silenceDurationMs`）| 【公】`semantic_vad` | 1 回区切りで切れる |
| 1 回の長さ | 【公】1 本のつなぎは約 10 分。声だけの会話は圧縮なしで 15 分 | 【未】| 制限なし |
| 使用量の知らせ | 【公】つないだ側（画面）に `usageMetadata` が時々届く。音声は 1 秒約 25 トークン | 【未】| — |

### 4-1 月額契約の中で使えるか（PO 2026-11-22 の問い・Context7 で公式の文書を確かめた 2026-11-22）

| | 事実（出どころ）| 意味 |
|---|---|---|
| 今の秘書の文の AI | **2026-11-24 直し**: 本番は ChatGPT（codex / gpt-5.6-terra・2026-11-11 21:49 JST から・ADR-1058）。本番 DB `ai_job_assignments` を reader 鍵で読んだ（2026-11-24 10:41 JST）。PO の ChatGPT は無料プラン（PO 2026-11-24「今は無料プランで動作確認や試しをしている」）。前の版の「Claude の月額契約」は古い ADR-1056 `:15` だけを読んだ誤り | 文の秘書は ChatGPT の無料プランのログインの中 |
| Gemini の鍵で使う声の AI | 【公】Google の AI の月額プランの特典は AI Studio の画面の中だけ。鍵で API を使う分は「別に請求・管理」（ai.google.dev/gemini-api/docs/google-ai-plans）| **月額の中ではない。使った分だけ払う** |
| Gemini の無料枠 | 【公】無料枠は料金 0 だが「製品の改善に使う: はい」。有料枠は「いいえ」（ai.google.dev/gemini-api/docs/pricing）| 無料枠だと会話が Google の学習に使われる → 有料枠が要る |
| Gemini の使いすぎの止め | 【公】請求先の段階ごとに月の上限（段階 1 は $250）。届くと翌月 1 日まで全部の API が止まる（ai.google.dev/gemini-api/docs/billing）| 我々の上限とは別に Google 側の上限がある（§6-6）|
| ChatGPT の月額契約 | 【公】2026-10-28 から、ChatGPT の Pro と Business の契約には毎月の API の無料分が付く（Pro $100〜$500・Business 1 席 $20〜$100・会社で月 $500 まで）。Realtime API と GPT-Live に使える。Plus は対象外（developers.openai.com/api/docs/guides/chatgpt-api-credits）| **Pro か Business なら、無料分の中で声の会話を使える。PO の契約の種類は確かめていない（§12-H）** |
| ChatGPT の無料分の細かい決まり | 【公】Pro は $100・$200・$500 の段ごとに同じ額。Business は Standard 1 席 $20・Premium 1 席 $100 を会社でまとめ、月 $500 まで。使わなかった分は翌月に残らない。受け取るのは契約の持ち主で、API の組織の持ち主と同じメールが要る。無料分が尽きて買った分も無いと、`429`・`credit_balance_exhausted` で失敗する（developers.openai.com/api/docs/guides/chatgpt-api-credits）。席の値段は Standard 月 $25（年払い $20）・Premium 月 $125（年払い $100）・最低 2 席（【三】検索の要約。openai.com/business/chatgpt-pricing を便 T0 の前に開いて確かめる）| 無料分は金額で付き、トークンの数では付かない |
| OpenAI の声の値段 | 【公】`gpt-realtime-2.1-mini` 音声 入力 $10・出力 $20（100 万トークンあたり）。GPT-Live は話している間 $0.05/分・待っている間 $0.02/分で、秒で数え、裏の AI と道具は別に数える（developers.openai.com/api/docs/pricing）| 1 分あたりのトークン数は【未】のため、円は便 T0 で測る |

**選んだもの: ①**（§12-H の答えで ② に変える場合がある）。理由:
1. L5（2 秒以内）と L6（割り込み）は ③ では作りの上で満たせない。
2. ② と比べて 1 分の下限が約 4 分の 1。Google とは既に Gemini を使っている（請求の確かめは §12-A）。
3. ① の版の速さは測られていない。**便 T0 で本番から実測し、L5 を満たさなければ ② に切り替えるかを PO に聞く**。切り替えはつなぎ方が違うため、画面の LIVE の部品と backend の札の口の作り直しになる（1 行では済まない）。

## 5. LIVE の作り（秘書の仕事は今の道に任せる）

```
[画面] ──声──▶ [Gemini Live]（声の聞き取り・話す・割り込み・書き起こし）
   ▲                  │ 用事だと判断したら道具「秘書に頼む(文)」を呼ぶ
   │                  ▼
   │          [画面] が今の POST /assistant/messages に、その文を本人のログインで送る
   │                  │（名前探し・カルテ・決まり帳・下書きは今のまま）
   │◀─下書きの吹き出し─┘ 返事の文を Gemini Live に返し、Gemini Live が声で伝える
```

- Gemini Live に渡す道具は「秘書に頼む（文）」の 1 つだけ。Gemini Live は会社のデータを読む道も、何かを作る道も持たない。データのある場所は今と同じで、写しを増やさない。
- 道具の引数の文は、利用者が書いた文ではなく **Gemini が言い換えた文**。画面はその文を吹き出しに「秘書に頼んだ内容」として出し、利用者が目で確かめられるようにする。
- 道具の結果として Gemini Live に返すのは、今の秘書の返事の文（`reply`）だけ。下書きの中身（相手・金額の数値の形）は返さない。結果の文に命令が紛れても、Gemini Live には道具が 1 つしか無く、作る道も無い（試験 §11）。
- **例外は予定の確かめの読み上げだけ**（§5-1）。画面が予定の下書きの state から、送る中身の空でない項目を全部入れた文（§5-1 の 1）を作り、道具の結果として Gemini Live にそのまま読ませる。Gemini に中身を作らせない。請求書の中身は Gemini に渡さない（請求書はボタンだけで作るため）。
- 道具の呼び出しは画面が 1 本ずつ順に送る。秘書の容器は同時 1 本（recon.md `:100`）なので、前の頼みの途中で次が来たら待たせ、`429 busy` が返ったら Gemini Live に「少し待ってください」と言わせる文を結果として返す。
- 聞き返し（カルテ・`SecretaryKarteAsk`）の最中に声で答えたときは、画面が今と同じく持っている karte を付けて `POST /assistant/messages` に送る（`backend/app/schemas/assistant.py:44` 以降の形のまま）。
- 道具の結果は 6〜8 秒かかる。その間、Gemini Live は「確かめます」と短く言う（指示文で決める）。
- 両方の発言は、今の会話の吹き出し（`ChatBubble`）で同じ並びに出す。**窓を開いている間は残る。窓を閉じたら消える（今の秘書と同じ）**（L8）。
- 「ゆっくり話して」は指示文と会話の中で効かせる（L9）。効くかは便 T0 で測る。

### 5-1 作る前の確かめ（L11）

- 下書きは今と同じ吹き出しで出て、「作る」ボタンがある（ADR-1056）。**画面のボタンが正本。声の道は足しただけ**で、声の道が壊れても事故にはならない。
- **請求書は声で頼めるが、作るのは画面の「作る」ボタンだけ**（PO 2026-11-23「1」。審査 2 回目 review-architect-2.md §1-(2) の推奨）。理由: 画面で人が必ず触るのは「送料を請求しない」の 1 つだけ（`frontend/src/features/secretary/SecretaryDraftInvoice.tsx:114`）で、金額・相手を人が見た証拠にならない。ただ読み返して「はい」と言わせる確認は、試作で聞き間違い 20 件が全部すり抜けた（research-2.md §4。小さな試作・自己申告）。
  - 請求書の下書きが出たら、Gemini Live は「画面で中身を確かめて、作るボタンを押してください」とだけ言う。声の「はい」「作って」では作らない（請求書の部品の `submit` は外へ出さない）。
  - 「送料を請求しない」は人が画面でチェックする（`:252-258`。説明文は `frontend/src/locales/ja.json` `secretary.invoice.shippingNoneHelp`）。声でチェックを入れる道は作らない。
- **予定の声の「はい」の決まり。** 決めるのは AI ではなく画面:
  1. 下書きが出て作る条件が揃ったら、**画面が予定の下書きの state から読み上げの文を作り**、Gemini Live にそのまま読ませて「作りますか？」と聞く（Gemini に言い換えさせない。審査 2 回目 §1-(2) の矛盾の直し）。同じ文を吹き出しにも出す。**読み上げの文には、送る中身（`frontend/src/features/secretary/SecretaryDraftEvent.tsx:53-69`）のうち空でない項目を全部入れる**: 題名・日時（全日か）・個人か共用のカレンダーか・場所・説明・Meet を付けるか（審査 3 回目 R1 の 2。予定には「相手」の欄が無いので「相手」とは書かない）。読み上げに無い項目が「はい」で一緒に作られる道を残さない。
  2. 一致を見る窓は、**「作りますか？」の声が流れ終わってから、こちらの次の発話 1 つだけ**。秘書が話している間・割り込みの最中・2 つ目以降の発話は見ない。
  3. 一致は**完全一致**で、一覧は「はい」「作って」の 2 つだけ（句読点と前後の空白を除いて比べる）。「はい、続けて」のような部分一致では作らない。一覧の正本は画面の 1 か所。
  4. 一致したら、画面は部品の「作る」ボタンと同じ処理を呼ぶ。そのため**予定の部品（`frontend/src/features/secretary/SecretaryDraftEvent.tsx:46-69`）の `canCreate`・`submit` を、部品の外から呼べる口に出す改修**を便 B に入れる。処理は部品の中の 1 か所のまま（写しを作らない）。`canCreate` が偽なら作らない。
  5. **「はい」を読み上げた下書きに結ぶ**（審査 3 回目 R1）。読み上げの時に、画面は「読み上げた文」と「下書きの識別子」を 1 組持つ。窓が開いている間に、(a) その下書きの欄が 1 つでも変わる (b) 別の下書きが出る (c) 窓の外の発話が来る、のどれかが起きたら窓を閉じる。「はい」に一致した瞬間に、**今の state から読み上げの文を作り直し、持っている文と同じときだけ** `submit` を呼ぶ。対象は最後に読み上げた下書き 1 つだけ。
  6. **`submit` を呼ぶ前に窓を閉じる**（`submit` は `await` を含むので、閉じずに呼ぶと 2 回目の「はい」で二重に作る道が残る。`canCreate` の `!saving` `:50` だけに頼らない）。
  7. **読み上げの忠実さ**: Gemini の読み上げの書き起こしが、画面の文と一致するときだけ窓を開く（空白と句読点を除いた完全一致）。書き起こしが取れるか・一致の見方が足りるかは【未】で、便 T0 で測る（§10）。一致しなければ窓を開けない。画面の文は吹き出しに残るので、「作る」ボタンで作れる（事故にならない側に倒れる）。
  8. Gemini Live に「作る」の道具は渡さない。
  9. 便 B に進む前に、便 T0 で「否定の 3 語」と「わざと違う日時を読み上げる」試験を各 5 回測る（審査 2 回目 §1-(2)）。
- 否定の試験: 「いいえ」「やめて」「待って」を各 10 回言い、作られた回数 0（L11）。画面の試験でも、一覧以外の文・窓の外の「はい」・請求書の `canCreate` が偽のときの「はい」で作らないことを確かめる（§11）。

### 5-2 鍵を画面に出さない

公式の文書（【公】ephemeral tokens）で確かめた札の決まり: 使える回数 `uses`（既定 1）、つなぎの期限 `expireTime`（既定 30 分）、つなぎ始めの期限 `newSessionExpireTime`（既定 1 分）、`liveConnectConstraints` でモデルと設定を札に固定できる。

- backend の新しい口 `POST /api/v1/assistant/live/session` が札を作って画面に渡す。Gemini の鍵そのものは画面に出さない。守りは秘書と同じ（`_SECRETARY_DEPENDENCIES` `backend/app/routers/assistant.py:98-103`）。
- 札の設定: `uses=1`・つなぎ始め 1 分・つなぎの期限 **10 分**。モデル・指示文・道具の定義・声の種類・書き起こしは `liveConnectConstraints` で **backend が固定**し、画面からは変えさせない（札が漏れても別の使い方をさせない）。
- 札の口の回数の上限: 1 人 1 時間に 20 回まで（上限の逃げ道をふさぐ）。超えたら 429。**数える場所は Redis**（今の回数の上限と同じ数え方・`backend/app/middleware/rate_limit.py:55-76`）。ただし今の回数の上限は Redis が止まると通す（`:7`・`:75-76`）。LIVE は費用が出るので逆にし、**Redis が読めなければ札を出さない**（503）。回数は数えるだけの一時の値で、会社のデータではない。
- Gemini の鍵は LIVE 専用の環境変数 `GEMINI_LIVE_API_KEY` から読み、backend だけに渡す（今の `GEMINI_API_KEY` は backend と celery-worker の両方・`docker-compose.yml:98`・`:246`）。**値が空なら札を出さず、503 と「準備ができていません」の印を返す**。値を別の Google のプロジェクトの鍵にするかは PO が決め、値を入れるのも PO（§12-J）。
- 使えるのは super admin だけ（秘書の守り 4 つ `backend/app/routers/assistant.py:98-103` の `require_super_admin`）。画面が送る使用量の申告を信じる作りは、この条件があって成り立つ。使える人を広げるときは設計を審査し直す（ADR-1087）。
- 札の期限（10 分）で、**つないでいる最中の LIVE が実際に切れるか**は【未】（`expireTime` が「つなぎ始めまで」の意味なら切れない）。便 T0 で 11 分つなぎ続けて確かめる。切れなかったときの備えとして、画面は 10 分で LIVE を自分で終える（同じ 10 分を画面にも持つ。正本は backend の定数で、札の口の返事に入れて画面に渡す）。
- 札・鍵を backend のログ・エラー文・画面のログに出さない（試験 §11）。
- 使う SDK の版: `google-genai`（`backend/requirements.txt` の下限 `>=1.0.0`）で `auth_tokens.create` が使えるかは【未】。**便 T0 で使う版を固定してから作る**。

### 5-3 本番の画面の安全設定

- 画面から Google へ直接つなぐため、CSP の `connect-src` に Gemini Live の接続先（`wss://generativelanguage.googleapis.com`）を足す（`nginx/nginx.conf:96`）。足りるかは便 T0 の実機で確定し、足りなければ足す先を PO に示してから直す。
- マイクの音を取り出して送る処理（AudioWorklet）は、画面の中で作る一時の URL にせず、**同じ場所から出す普通のファイル**（`frontend/public/` に置く）で読み込む。`script-src 'self'` を緩めない。
- nginx を変える配備は 2〜3 秒画面が止まる（`.github/workflows/deploy.yml:570-575`）。
- 代わりの案（backend を中継にする）は、`/api/` の枠に WebSocket の設定と中継の処理が要り、作る量と止まる箇所が増えるため選ばない。費用の確かさは §6 の仮の行で補う。

## 6. 費用・台帳・月の上限（L12）

### 6-1 使用量の入り口（【公】で確かめた事実に合わせた作り）

- 使用量（`usageMetadata`）は、つないだ側＝画面にだけ届く【公】。backend は直接は見られない。
- そこで、**札を出せた時に台帳に仮の 1 行を先に書く**（`outcome = 'pending'`・§6-3）。便 T0 では費用は空のまま。便 T1 からは「この LIVE 1 回の最大の費用」を入れる（最大は便 T0 で 10 分の LIVE を実測して決める。今は推測で書かない）。
- 画面は Google につながった時に、新しい口 `POST /api/v1/assistant/live/usage` に「始めた」を送る（札の行の番号付き）。LIVE を終えたら、最後に受けた使用量と速さの記録を同じ口に送る。backend は仮の行を本当の量で 1 回だけ書き直す（`outcome = 'pending'` の行だけ・本人の札の行だけ）。
- 書き直しが来ない行の扱い（**行を書き直すのは、札を出す口と使用量の口の中だけ**。錠の中で `outcome = 'pending'` の条件つきの UPDATE を 1 回。費用の画面と上限の合計は、同じ決まりで**計算して数えるだけ**で行は書き換えない。審査 3 回目 R6）:
  - 札を出して 2 分たっても「始めた」が来ない行 → 費用 0・`outcome = 'failed'`・`error_code = 'not_started'`。札は 1 回しか使えず、つなぎ始めの期限は 1 分（【公】）なので、その後はつなげず請求も立たない。期限後につなげないことは便 T0 で確かめる。
  - 「始めた」が来て 15 分たっても終わりの報告が来ない行 → 便 T1 からは最大の費用で `ok` にする（多めに数える側に倒す）。便 T0 では費用は空のまま `ok` にし、Google の請求画面で照らす。
- 画面が送る値は「申告」なので、毎月 1 回、Google の請求と台帳の LIVE の合計を照らす（§11）。差が 1 割を超えたら PO に知らせる。

### 6-2 上限の判定

- 札を出す時に、今月の LIVE の合計（仮の行を含む）＋次の 1 回の最大が上限を超えるなら札を出さない。合計を数える前に、同じ取引の中で LIVE の上限用の advisory lock を取る（2 人が同時に札を取って両方が通るのを防ぐ）。**合計を読めなければ札を出さない**（503。読み上げの字数と同じ型・ADR-1080 `:20`）。1 回のつなぎは最長 10 分で切れる（§5-2）ので、**上限に届いた後は、長くても 10 分のうちに LIVE が止まり、新しい LIVE は始まらない**（kgi.md L12）。文の秘書は今のまま使える。
- 黙ったままが 2 分続いたら画面が自動で終える（費用の守り）。
- 上限の置き場: 読み上げと同じ型で、backend/app/services/secretary_live.py の定数 1 か所（`MONTHLY_COST_CAP_USD`）。変えるのは配備。止めたいときは配備を待たず、LIVE 専用の旗（`tenant_features` の `secretary_live` の行）を切って LIVE のボタンを消す（§15）。秘書の旗 `secretary_chat` は秘書の全部の守りなので（`backend/app/routers/assistant.py:93`・`:99`）、それを切ると文の秘書も止まる。だから LIVE 専用の旗を足す。旗の行は表の行を足すだけで、表の作りは変えない（`migrations/20261101_120000_enable_secretary_chat_tenant4.sql:10` と同じ形の migration で会社 4 だけ）。
- 既存の会社ごとの月の予算 `tenant_llm_budgets`・`check_budget`（`backend/app/services/llm_budget.py:498`）は使わない。理由: 秘書から使われているかが【未】（recon.md `:214`）で、使うと他の AI の仕事の予算と混ざる。LIVE は全社で 1 つの上限にする。

### 6-3 値段表と 1 行の形

- 値段表の正本は `backend/app/services/llm_budget.py` の 1 か所のまま。Gemini Live の音声と文字の単価が違うので、`LLM_PRICING` に音声の入力・出力の単価を足し、`calculate_usage_cost` が `usageMetadata` の種類ごとの内訳（音声・文字）から計算するよう広げる。
- 1 行＝LIVE 1 回（ADR-1080 の読み上げ 1 回＝1 行と同じ粒度）。行を書くのは Google の口を呼んだ時だけ（札を作る呼び出し）。上限・回数・鍵が無いで断ったときは Google を呼んでいないので書かない（ADR-1058 `docs/adr/ADR-1058-ai-job-assignments.md:24`「API を呼んでいない失敗は書かない」のまま）。札を作る呼び出しが失敗したら、今の 9 つの `error_code` で `failed` の 1 行にする。
- **migration（便 T0・1 本・今の型 `migrations/20261117_100100_add_llm_usage_tts_characters.sql` と同じく冪等）**。値を足すだけでは足りず、次を作り直す・足す（表や列を消す文は入れない。CHECK だけを「あれば外して」から作り直す）:
  1. `outcome` の CHECK（`migrations/20261103_120000_create_ai_job_assignments.sql:128-129`）に `pending` を足す。
  2. 組み合わせの CHECK（同 `:143-144`）を「`ok`・`pending` は `error_code` が空／`failed` は空でない」に作り直す。
  3. `error_code` の CHECK（同 `:133`）に `not_started` を足す（10 個になる）。
  4. `purpose` の CHECK に `secretary_live`、`sdk` の CHECK に `google-genai-live` を足す。
  5. 列を足す（`ADD COLUMN IF NOT EXISTS`・既存の行は空）: `audio_prompt_tokens INTEGER`・`audio_candidates_tokens INTEGER`（音声の内訳。費用の計算の根拠を行に残す）、`live_reply_latency_ms INTEGER[]`・`live_barge_in_latency_ms INTEGER[]`（L5・L6 の 1 回ごとのミリ秒。中央値を出すには 1 回ごとの値が要るので配列のまま）。
- **migration の作り方の決まり（審査 3 回目 R3）**:
  - CHECK は**名前だけでなく定義を読んで**作り直す。`pg_get_constraintdef` が新しい値（`pending`・`not_started`・`secretary_live`・`google-genai-live`）を含まないときだけ `DROP CONSTRAINT IF EXISTS` → `ADD CONSTRAINT`（前例 `migrations/20261117_100100_add_llm_usage_tts_characters.sql:7-37` の `NOT LIKE` の形）。`IF NOT EXISTS (... conname = ...)` の名前だけの形（`migrations/20261103_120000_create_ai_job_assignments.sql:136-146`）は真似ない（古い定義が残ったまま素通りする）。
  - 作り直す値の一覧は**今の CHECK の全値＋新しい値**。後から足された `secretary_regression`・`secretary_tts` 等を消さない（`backend/app/services/llm_budget.py:159-171` の `USAGE_PURPOSES` と一致。一致は `backend/tests/test_secretary_voice_pg.py:104` が見る）。
  - `scripts/run_all_migrations.sh` に `run_sql` の行を足す（登録の検査 `scripts/check-migration-registration-exists.sh`）。
- **読み取りビューの分類（審査 3 回目 R2）**: 新しい 4 列は、本番の読み取りビューの分類表の正本 `migrations/20261024_100300_create_ai_cloud_views.sql` に `allow`（理由つき。数のみで名前・本文を含まない）の行を足す。整数の 2 列は `_PASS_TYPES`（`backend/tests/ops/test_ai_cloud_views.py:52-55`）の `int4` に当たるが、配列の 2 列は通らず分類の漏れの試験（`:494-519`）が落ちるため、4 列とも行を足して揃える。分類表の行数の試験（`:486` の 1165）を足した数に直す。`ai_ro` 側（`backend/tests/ops/test_ai_ro_views.py`）に同じ要件があるかは便 T0 の PR の最初に開いて確かめ、あれば同じく足す。これらは便 T0 の台帳の migration と同じ PR に入れる。
- 今の集計は `outcome = 'ok'` だけを数える（ADR-1058 `:24`）ので、`pending` の行は今の画面の数を変えない。
- 写しの更新: `USAGE_PURPOSES`・`USAGE_SDKS`（`backend/app/services/llm_budget.py:174-176`）に足す。`USAGE_SDKS_BY_PROVIDER`（`:180-185`）には **`gemini` に入れず**、読み上げ（`google_tts`）と同じ形で新しい鍵 `gemini_live` を足す。`gemini` に入れると「AI の担当」タブの Gemini の回数とログインの○×に LIVE が混ざる（`backend/app/routers/super_admin_ai_jobs.py:184`）。試験 `backend/tests/test_super_admin_ai_jobs.py:281` の期待の集合に `gemini_live` を足す。CHECK と写しの一致は `backend/tests/test_secretary_voice_pg.py:104` が見る。
- ② OpenAI に切り替える場合の sdk の値は、そのときの migration で足す（切り替えは作り直しの別の便になるため）。

### 6-4 今月の費用を見る画面

- 読み上げの今月の字数を出しているスーパー管理の解析ダッシュボード（`backend/app/routers/tcg_analysis_dashboard.py:939-1050` の `secretary_tts_month`）に、LIVE の今月の費用と上限を並べて出す。新しい画面は作らない。
- **既存の AI の費用の合計との関係**（審査 3 回目 R5）: 既存の合計（`backend/app/routers/tcg_analysis_dashboard.py:698` の `_LLM_USAGE_WHERE`）は `outcome = 'ok'` で絞り、使いみちでは絞っていない（審査 3 回目が読んだ範囲）。読み上げ（`secretary_tts`）も同じく入っている前例に合わせ、**LIVE も「AI に払った費用」として合計に含める**（除くと合計が実際の請求より少なく見える）。便 T1 の PR で `:698` 以降の合計を全文で読み、使いみちで絞る所があればその決まりに合わせる。
- `LLM_PRICING`（`backend/app/services/llm_budget.py:56`）に Live のモデル名が無いと、`calculate_usage_cost` が空（`:228-233`）を返し費用が数えられない。便 T1 の試験で、Live のモデル名の単価があり費用が空にならないことを確かめる。

### 6-6 上限に届いたとき、誰の上限かを画面に出す（L13・PO 2026-11-22）

使う人はエンジニアではない。止まったときに「どこの上限か」「いつ戻るか」「代わりに何が使えるか」を画面の文で出す。

| 上限の持ち主 | 何の上限か（事実）| 画面がどう知るか | 画面の文の中身 |
|---|---|---|---|
| Sales Anchor（社内で決めた額）| LIVE の月の上限（§6-2）| backend の札の口が決まった失敗の印を返す | 社内で決めた今月の上限に達した・日本時間の来月 1 日 0 時に戻る・文字の秘書は使える |
| Sales Anchor（準備）| LIVE 専用の鍵が入っていない・Redis が読めない・合計が読めない（§5-2・§6-2）| backend が 503 と決まった印を返す | 声の会話の準備ができていない・文字の秘書は使える・管理者に知らせる |
| Sales Anchor（使いすぎの止め）| 札の口の 1 人 1 時間 20 回（§5-2）| backend が 429 と決まった印を返す | 短い間に何度も始めた・◯分後にまた使える |
| Google（声の AI）の 1 回の長さ | 1 本のつなぎは約 10 分。終わる前に知らせ（GoAway・残り時間つき）が届く【公】| Google からの知らせ | あと◯秒で区切れる・押し直せば続けられる |
| Google の請求先の月の上限 | 段階ごとの月の上限。届くと翌月 1 日まで止まる【公】（区切りの時間帯は【未】のため、画面は「来月」とだけ出し時刻は出さない）| 札を作るときの Google の失敗の返事を backend が見分ける。**どの返事で届くかは【未】** → 便 T0 で Google の文書と実際の返事を確かめ、見分けられた印だけを画面の文にする | Google 側の今月の上限で止まった・PO に知らせる |
| Google の回数の上限 | 決まった時間あたりの回数【公】（数は請求先の段階で違う）| 同上【未】 | Google 側の回数の上限で止まった・少し待つ |
| ブラウザ（マイクの印 A の聞き取り）| ブラウザが聞き取りを止めることがある【未】| Web Speech の失敗の印 | ブラウザの聞き取りが止まった・押し直す |
| 送れる文の長さ | 1,000 字（`frontend/src/features/secretary/secretaryApi.ts:10`）| 画面が数える | 1,000 字を超えた・今◯字 |

- ② を選んだら、OpenAI の `credit_balance_exhausted`（無料分の使い切り・公式に印がある）を「OpenAI の今月の無料分を使い切った」の文にする。
- ChatGPT は、§12-H で ② を選ばない限り使わないので、ChatGPT の上限の文は作らない。② を選んだら、同じ表に「OpenAI の無料分を使い切った」を足す。
- 見分けられない止まり方は推測で分類しない。「原因が分からない止まり方」の文を出し、台帳の `error_code` は `other` にする（`error_code` は決まった 10 個だけ・§6-3）。Google の生の印は backend のログに残す。便 T0 で出た印を数え、見分けられたものから表に足す。
- 印→文の対応の正本は画面の 1 か所（翻訳キー・ADR-027）。backend の失敗の印の正本は secretary_live.py の 1 か所。文は、注意の金型 `Callout`（`frontend/src/components/Callout.tsx:1-10`・ADR-144）で出す。社内と Google の上限・準備ができていないは `variant="warning"`（`role="alert"`）、10 分の区切りの予告・1,000 字は `variant="info"`（`role="status"`）。新しい部品は作らない。2 回目の審査の前は名前で探して見落としていた（用途で探し直した）。
- Google の同時につなげる数の上限は【未】。使う人が数人なので表に足さず、便 T0 で出たら足す。

### 6-5 AI の担当表（ADR-1058）に入れない理由

- 担当表は「同じ形で呼べる文の AI を画面で選ぶ」ためのもの。LIVE は声の流れで、② に変えるにはつなぎ方の作り直しが要り、画面で選んで切り替えられない。
- 読み上げ（`secretary_tts`）も担当表に入れず、コード 1 か所でモデルを決めている前例がある（§3）。LIVE も同じにし、モデル名は secretary_live.py の 1 か所だけに書く。ADR-1087 で ADR-1058 の例外として明記する。

## 7. (A) マイクの印

- 今の Web Speech の部品を、話している間ずっと聞く形にする（`continuous=true`・途中の文字を欄に出す）。PC にも出す（`isMobile` の条件を外す）。0 円で台帳に書かない（ADR-1082 What 1 のまま）。
- ブラウザは無音などで聞き取りを自分で終えることがある【未】。そのため、押している間に聞き取りが終わったら画面がすぐ聞き直し、**それまでに決まった文字は欄に残したまま、新しい文字を後ろに足す**（同じ文字を二重に足さない: 決まった文字と途中の文字を分けて持つ）。何も聞き取れないまま聞き直すのは 5 回まで（`LISTEN_MAX_IDLE_RESTARTS`）。届いたら止めて「声が聞き取れませんでした」と出す（無限に聞き直さない安全弁。時間の上限ではない・審査 4 回目 N3）。
- 対象のブラウザ: PC は Chrome と Edge の最新版、スマホは Android の Chrome と iPhone の Safari（kgi.md L2）。Web Speech の聞き取りが無いブラウザでは、今と同じく印は出て、押すと「この画面では声の聞き取りが使えません」と出る（`frontend/src/features/secretary/SecretaryChat.test.tsx:716` の動き。審査 3 回目の前に Opus が実物で確かめて直した）。
- 長さ: 聞いている時間に上限は付けない。送れる文の 1,000 字を変えるかは PO の決定（§12-F）。変えない間は 1,000 字を超えたら欄の下に字数を出して知らせる。長い文を秘書に送ったときの動き（容器 80 秒・body の上限 `backend/app/routers/assistant.py:89`・`secretary-agent/server.mjs:15`）は、1,000 字を変えるときに測る。便 A は送れる字数を変えない（今も手で 1,000 字まで打てる: `frontend/src/features/secretary/SecretaryChat.tsx:249` の `maxLength`）ので、便 A の前には測らない。便 A の作りは `docs/handoff/secretary-live/card-binA.md`。
- iPhone のホーム画面のアプリで Web Speech が動かない報告がある（Apple フォーラム 748048・research.md §2）。対象に入れるかは PO の決定（§12-D）。入れる場合は便 T0 で実機を測り、動かなければマイクの印は Gemini Live の書き起こしに切り替える（有料・台帳は §6）。

## 8. iPhone の注意と対処

| 報告 | 対処 |
|---|---|
| 音は利用者の操作の中で鳴らし始める必要（WebKit 177292）| LIVE ボタンを押した処理の中で音の準備をする |
| 消音スイッチで Web Audio が鳴らない（WebKit 237878）| LIVE の画面に「消音スイッチを確かめて」の案内（翻訳キー）。便 T0 で実機確認 |
| 画面を消すと音が止まる（Apple フォーラム 774239）| 画面が隠れたら LIVE を止めて会話を残す |
| ホーム画面のアプリで聞き取りが動かない（748048）| §7 |
| 出力先の切り替えが効かない（WebKit 320087）| 出力先は選ばせない |

## 9. 守る決まり（画面）

- 文字は全部 `t("key")`（ADR-027）。`frontend/src/locales/ja.json`・`frontend/src/locales/en.json` に同じキー。
- 見た目は金型だけ（ADR-144）。LIVE の画面は `Sheet`・`Stack`・`IconToggleButton`・`ChatBubble`・`Button` を使う（recon.md 1-2）。絵柄は `frontend/src/constants/icons.tsx` の `SECRETARY_ICONS`（`:416`）に、LIVE・消音・終了を足す。色・余白はデザイントークンだけ（ADR-067）。新しい金型が要るときは作る前に PO に聞く。
- **機械が見る範囲の注意**（検査ごとに分けて引く・審査 3 回目 R7）: 生の部品の検査は `frontend/src/pages/` だけを見る（`scripts/check-ui-governance.js:47`）。loading の書き方の検査は `features/` も見る（同 `:16`）。日本語の直書きは ESLint の `local/no-japanese-literal`（`frontend/eslint.config.js:31`）の仕事。色・寸法の直書きは ADR-067 の検査（`check:css-colors`・`check:css-values`・`frontend/package.json:48`）が CI で見る。**人の審査に残るのは生の部品（`<select>`・`<input>` 等）と金型の選び方**。マージ前の審査役の点検に「生の部品が無いこと」を入れる。
- **日本語の直書きは機械で止める**: `frontend/eslint.config.js` に `src/features/secretary/**` だけ（試験ファイル `*.test.{ts,tsx}` は除く。試験は日本語を `String.fromCharCode` で作る）`local/no-japanese-literal` を `error` にする override を足す（前例: 同じファイルの `:244`・`:252` の override）。CI の `lint-run`（`.github/workflows/e2e.yml:65`・`:87`）が落ちる。**便 A と便 T0 のうち先に出す便の PR に入れる**。便 A を先に出すので `docs/handoff/secretary-live/card-binA.md` の変更 4 に入れた。origin/main `bef5a7a8b` の `features/secretary/` の日本語は注釈の中だけ（Opus が 12 ファイルを確かめた）なので、入れた瞬間に落ちる行は無い。PR で `eslint src/features/secretary` を実際に流して 0 件を確かめる（設定は後ろの塊が勝つため、置き場所の効き方も実物で確かめる）。

## 10. 便の分け方（一度に 1 つ）

| 便 | 中身 | 合格を見る目標 | migration |
|---|---|---|---|
| T0（試作）| 札の口（回数の上限つき・専用の鍵）・LIVE 専用の旗・台帳の仮の行と使用量の口（費用は空）・LIVE の画面の最小形（話す・聞く・割り込み・両方の文字・消音・終了・10 分で自分で終える）・速さの記録。**月の上限なし・旗は PO の会社だけ**。料金ページの再確認・SDK の版の固定・CSP の接続先の確定・iPhone 実機・10 分の最大の費用の実測・札の期限で切れるか（11 分つなぐ）・文の意味で話し終わりを見る設定があるか（L5/L7）・予定の声の「はい」の否定語とわざと違う日時（各 5 回）もここ | L4〜L7・L10 の測り・最大の費用の実測 | 2 本（旗の行・台帳）→ GO まで main に入れない |
| T1 | 月の上限（仮の行の最大・錠・読めないとき出さない）・費用の画面 | L12 | なし |
| A | マイクの印を PC にも・聞き続ける形・聞き直し | L2・L3 | なし |
| B | LIVE で秘書に頼む（道具）・予定の声の「はい」（請求書はボタンだけ）・上限の持ち主の文・文字を会話に残す・ゆっくり | L8・L9・L11 | なし |
| C | 「声で返事」を消す（試験 `frontend/src/features/secretary/SecretaryChat.test.tsx:501-630` も）・読み上げの口と声の設定の扱い（§12-G）| L1 | なし |

- 順番: T0 → T1 → B → C。A は T0 と別に先に出せる（A を先に出す）。
- **便 T0 の PR に必ず入れるもの**（審査 3 回目 R2・R4）: 台帳の migration と同じ PR に、新しい 4 列の読み取りビューの分類の行と試験の行数（§6-3）・`scripts/run_all_migrations.sh` の登録。札の口の試験（鍵と札が漏れない・札の口の守り・回数の上限で 429・鍵が空なら 503）は T0 の PR に入れ、T1 に回すのは月の上限・錠・合計を読めないの試験だけ。L5 を測る「頼みごとをしない 20 文の台本」を docs/handoff/secretary-live/l5-script.md に置く（測り手が替わっても同じ文で測る）。
- **便 T0 で測りに足すもの**（審査 3 回目）: Gemini の読み上げの書き起こしが取れるか・画面の文と一致するか（§5-1 の 7）。`frontend/public/sw.js` が AudioWorklet のファイルを古いまま持ち続けないか（配備の後に新しい版を読むか）。
- **T0 の前に PO の了承が要る**: T0 でも本番で声の AI を使うので費用が出る（§12-A）。T0 の間の費用は、札の口の回数の上限と PO の会社だけの旗で抑える。T0 の費用は台帳に入らないため、Google の請求画面で PO と照らす。
- GO: T0 は migration を含むので、PR 全体を GO（ADR-135・ADR-136）まで main に入れない。この migration は CHECK の作り直しと列の追加だけで、表や列を消さないため ADR-1003 の例外に当たらず、委任の GO で足りる。PR 本文に「CHECK を外す文は作り直しのためで、表や列を消す文ではない」と書く。
- 便 C（「声で返事」を消す）は、便 T0 と B の本番の測りで L4・L5（決め直した線）が合格してから出す。画面・backend だけの便も、GO の記録を PR に残す（`docs/STANDARD-WORKFLOW.md` の完了の定義）。
- T0 で L5 を満たさないときは、② OpenAI に切り替えるかを PO に聞く。

## 11. 続けるための機械の仕組み

| 何を守るか | 仕組み | 今あるか |
|---|---|---|
| 画面の文字の翻訳漏れ（ja と en の鍵の食い違い）| CI の `npm run check:all` の中の `check:i18n-missing-keys`（`.github/workflows/e2e.yml:87`・`frontend/package.json:28,48`）| ある（必須チェック「Lint & Dark Mode Check (ADR-067)」）|
| 画面の日本語の直書き | `local/no-japanese-literal` は `frontend/eslint.config.js:31` で warn。CI の `eslint src`（`frontend/package.json:15`）は warn で落ちない | **便 A で機械にする**: `src/features/secretary/**` だけ `error` の override（§9）。CI の `lint-run` で止まる |
| 金型外の見た目 | 色・寸法の直書きは ADR-067 の検査（CI）。生の部品は `features/` を機械が見ない（§9）→ マージ前の審査役の点検 | 色・寸法は機械・**生の部品は人の審査だけ** |
| 台帳の値の取り違え | DB の CHECK・`backend/tests/test_secretary_voice_pg.py:104` の一致の試験・`backend/tests/test_super_admin_ai_jobs.py:29` | ある（値の追加で更新）|
| 月の上限を超えない | backend の試験: 合計＋次の最大が上限を超えると札を出さない・仮の行が使用量の報告で 1 回だけ書き直される・「始めた」が来ない行は 2 分で 0 円・2 本同時に取っても上限を超えない・合計や Redis が読めなければ出さない・使用量の口は別人の札の行を書き換えない | **新しく作る** |
| AI が勝手に作らない | 試験: 札に固定する道具が「秘書に頼む」1 つだけ／請求書は声では作らない／予定は窓の中の完全一致だけで作る／否定語・窓の外・部分一致では作らない／読み上げの後に欄を直すと「はい」で作らない／下書きが 2 つあるとき最後に読み上げた 1 つだけが対象／書き起こしが画面の文と違うと窓が開かない／「はい」が 2 回来ても 1 回しか作らない | **新しく作る** |
| 鍵と札が漏れない | 試験: 札の口の返事に鍵が無い・backend のログとエラー文に鍵も札も出ない・札の口は LIVE の旗と秘書の守りを見る・回数の上限で 429・鍵が空なら 503 | **新しく作る**（便 T0 の PR）|
| 読み取りビューの分類 | CI の分類の漏れの試験（`backend/tests/ops/test_ai_cloud_views.py:494-519`・行数 `:486`）が、分類の無い新しい列で落ちる | ある（新しい 4 列の行を便 T0 の PR で足す・§6-3）|
| 道具の結果 | 画面の試験: 道具の結果は秘書の返事の文と、画面が作った予定の読み上げの文だけ（請求書の中身を渡さない）・Gemini は偽物に差し替えて CI で測る（本物の Gemini は本番の人の測り L11 が正本）| **新しく作る** |
| 速さ（L5・L6）| 画面が LIVE 1 回ごとに「こちらの声の終わり→秘書の声の始まり」「こちらの声→秘書の声の停止」のミリ秒を使用量の口に一緒に送り、台帳の列 `live_reply_latency_ms`・`live_barge_in_latency_ms` に残す（§6-3）。本番の読み取り鍵で数える | **新しく作る**（便 T0）|
| 費用の照らし合わせ | 毎月 1 回、Google の請求と台帳の LIVE の合計を比べる（ADR-1080 の字数の照らしと同じ日に）。差が 1 割を超えたら PO へ。結果は docs/handoff/secretary-live/monthly-reconcile.md に月ごとに 1 行足す | **手作業**。忘れたときに気づく仕組みは便 T1 の後に、週次の点検（週次点検の Discord の知らせ）に「前の月の行が無い」を足すかを PO に聞く |
| 決まりの索引 | `docs/adr/FEATURE-INDEX.md` の秘書の行に ADR-1087 を足す | 設計の PR で足した（CI の索引検査が新しい ADR を索引に求めるため・審査 4 回目 N1）|
| 親から子へのリンク | `docs/specs/secretary-chat/README.md` に `docs/handoff/secretary-live/` へのリンクを足す | この設計の PR で足した |

## 12. PO に決めてもらうこと

- **A. 有料の声の AI を使うか**。費用が出る（下限 1 分約 1.8 円）。Google の請求画面で、Gemini の鍵が請求の立つ有料枠であること（＝学習に使われない枠）を確かめてもらう。台帳の $40.55 は計算値で証拠にならない。
- **B. ADR-1056 を改めてよいか**。LIVE ではこちらの声と秘書の返事の文（相手の会社名・金額を含むことがある）が Google に送られ、Gemini に道具が 1 つ付く。
- **C. 月の上限の額**。案: 便 T1 は月 1,000 円（約 $6.3）で始め、T0 で測った 1 回の最大の費用を見て決め直す。使用量の取り方は §6-1（仮の行＋申告で書き直し）を推奨。
- **D. iPhone のホーム画面のアプリを対象に含めるか**。推奨: 含めない（Safari のみ）。含めると有料の書き起こしになる恐れがある。
- **E. 「ゆっくり」（L9）が効かなかったときの扱い**。推奨: 効かなければ L9 を外し、PO に結果を報告する。
- **F. 1,000 字の上限を変えるか**。推奨: 変えない（超えたら字数を出す）。
- **G. 「声で返事」を消した後の、設定の「秘書の声」と読み上げの口**。推奨: LIVE の声に同じ 4 声（`backend/app/services/secretary_voice.py:18`）が使えるかを T0 で確かめ、使えれば設定を LIVE の声として残す。読み上げの口は便 C の後 30 日使われていないことを台帳で確かめてから、別の便で消す。

- **H. ChatGPT の契約の種類**（Plus／Pro／Business）。Pro か Business なら、毎月の API の無料分の中で声の会話を使える（§4-1）。その場合は ② OpenAI を第一の候補にし直し、便 T0 で ① と並べて速さと 1 分の費用を測って選ぶ。Plus なら ① のまま。
  - **PO 2026-11-23「1」**: ChatGPT は Business を使う予定。席（Standard 2 席か Premium を含めるか）は、便 T0 で 1 分の費用を測ってから決める。Business は最低 2 席で、2 席分が毎月かかる（【三】値段の画面で T0 前に確かめる）。
  - **PO 2026-11-24**: 今は ChatGPT の無料プランで試している。動くと見込めたら Business を契約する。LIVE は ChatGPT の無料分（契約の API の無料分）の中だけで作る（「1」）。→ **LIVE（便 T0 から先）は Business の契約まで作らない**。
  - 2026-11-24 に確かめた事実（Context7 で OpenAI の公式の文書）: ChatGPT の声の会話（GPT-Live）は Plus 以上の ChatGPT のパソコンのアプリの中の機能で、API の鍵では使えない。Codex のログイン（ChatGPT のログイン）からは声の会話を呼べない（Codex の `codex-rs/core/src/realtime_conversation.rs` の `realtime_api_key()` が「realtime conversation requires API key auth」を返す）。API は ChatGPT の契約なしで使えるが、先払いの別の請求。毎月の API の無料分は Pro と Business だけ。無料の段（Free tier）は使える額の上限で、無料のお金ではない。
  - 代わりに、0 円で作れる「交代で話す型」（ブラウザの聞き取り・Google の読み上げの無料枠・ChatGPT の無料プラン）を先に作る（PO 2026-11-24「1」・予定と請求書だけで小さく）。設計は `docs/handoff/secretary-voice-input/design.md` §15・目標は同 `kgi.md` §5。LIVE の L5（2 秒以内の返事）・L6（割り込み）はこの型では満たさない（LIVE の目標は変えない）。
  - 別の問い（PO 2026-11-23）: ChatGPT のスマホアプリから Sales Anchor を動かすこと。Sales Anchor には MCP の口が無い（`git grep -i mcp` origin/main `backend/app` で 0 件）。`oauth` は外のサービスへつなぐ側の口だけがある（`backend/app/main.py:52`・`:63`・`:76` の Discord・Google カレンダー・Meta）。Sales Anchor が OAuth の認可を出す側の口があるかは未確認。公式の文書では文字の会話から読み書きできる（Business は書き込みも可・作る前に毎回確認）。声の会話の中では使えないという利用者の報告が複数（community.openai.com/t/1382072・/t/1376009。公式の記載は無し）。**PO 2026-11-23「1」: 今は頼まず、このテーマに集中する。**

- **I. 請求書を声の「はい」で作るか**（審査 2 回目 §3-2）。**PO 2026-11-23「1」: 請求書は画面の「作る」ボタンだけで作り、予定は声の「はい」で作る。** §5-1 と kgi.md L11 を直した。

- **J. LIVE 専用の Google の鍵**（審査 2 回目 §3-3）。推奨: LIVE 専用の Google のプロジェクトを作り、その鍵を `GEMINI_LIVE_API_KEY` に入れる。分ければ、LIVE の使いすぎで翻訳・抽出が止まらず、毎月の照らし合わせも LIVE の分だけで比べられる。作りはどちらでも同じ（専用の環境変数を読む・§5-2）。値を入れるのは PO 本人。
- **K. L5 と L7**（審査 2 回目 §3-1）。**PO 2026-11-24「1」: 便 T0 で、文の意味で話し終わりを見る設定が Gemini にあるかを先に測る。無ければ考える間（L7）を優先し、L5 は 3 秒以内に緩める。** kgi.md L5 を直した。

- 外の事例の数値は電話・ドライブスルーの規模で、我々の社内の数人の使い方にそのまま当てはまらない（research.md §4-1）。だから便 T0 を本番で測ってから先へ進む。

## 13. 合格の確かめ方

| 基準 | 検証方法 |
|---|---|
| L1〜L12 | kgi.md §2 の「測り方」を本番で行い、結果を `docs/handoff/secretary-live/` に記録 |
| 道具は 1 つ・AI は作らない | backend と画面の試験（§11）が CI で緑 |
| 鍵が画面に出ない | 試験＋本番で札の口の返事を目で確かめる |
| 費用が台帳に残る | 本番の読み取り鍵で `ai_ro.public__llm_usage_events` の `secretary_live` の行を数える |
| 月の上限で止まる | 上限を小さくした試験が CI で緑・本番は便 T1 で一時に上限を小さくして配備し、札が出ないことを見て戻す |
| 翻訳・トークン | CI の既存の検査が緑 |
| 金型 | マージ前の審査役が生の部品・色の直書きが無いことを確かめた記録 |

## 14. 外部・過去事例の参照と我々への応用（research.md の要約）

- 成功（数値あり・すべてベンダーの自己申告）: Landry's 初日の封じ込め 87%／Hello Sugar 応答 100%・封じ込め 56%／米国の銀行 解決 30%・満足度 96%／Wendy's 22 秒速い・正確さ 99% は店員の補助込み。
- 失敗（数値あり）: McDonald's×IBM 正確さ 80% 台前半（必要 95%）・100 店超・約 3 年で停止／Presto 人の介入なしの完了は 30% 以下（SEC の書類）。
- **失敗の 3 件目は、数値の取れる事例が見つからなかった**（Taco Bell・Kinney Drugs は数値なしで数えない）。
- 我々に当てはめる学び: ①成果は「AI だけで正しく終えた割合」と「人の補助込み」を分けて測る（Presto）。②聞き間違いがそのまま事故になる操作の前に、中身を読み上げて確かめる（McDonald's）→ §5-1。③同じ製品でも仕事の種類で封じ込めが 5%〜87% と開く（PolyAI の各社）→ 便 T0 の本番の実測で決める。

## 15. 戻し方

- 画面: LIVE のボタンは LIVE 専用の旗（`tenant_features` の `secretary_live` の行）が有効なときだけ出す。止めるときはその行を切れば、配備なしで LIVE のボタンが消え、文の秘書は今のまま動く（秘書の旗 `secretary_chat` は触らない）。
- コード: 便ごとの PR を戻す。台帳の migration は「無いときだけ」の冪等な形で、コードを戻しても今の行は壊れない（足した値・列は残るが使われないだけ）。
- 上限: 定数を 0 にして配備すれば札を出さない。

## 16. 維持の仕組み

守り手: .github/workflows/e2e.yml（画面の検査 `lint-run`・翻訳の鍵の検査。今ある必須チェック）。下の表の新しい試験は便ごとに足し、足したらこの行に並べる。

| 守り手 | 対象 | 関所 |
|---|---|---|
| backend の試験 backend/tests/test_secretary_live.py（便 T1 で新しく作る）| 月の上限・仮の行・札の口の守り・鍵と札が漏れない | CI の backend の試験（必須チェック）|
| 画面の試験 frontend/src/features/secretary/SecretaryLive.test.tsx（便 T0 で新しく作る）| 道具が 1 つ・声の一致の窓と完全一致・請求書は声で作らない・上限の文の持ち主 | CI の画面の試験（必須チェック）|
| 台帳の一致の試験 `backend/tests/test_secretary_voice_pg.py`（既存）| CHECK と写しの一致 | CI の DB 付き試験 |
| i18n の検査（既存）| 翻訳漏れ | CI |
| 画面の検査 `frontend/eslint.config.js` の override（便 A で足す）| `features/secretary/` の日本語の直書き（試験ファイルを除く）| CI の `lint-run`（必須チェック）|
| マージ前の審査役（人の審査）| `features/secretary/` の生の部品 | 関所なし（ADR-144 の機械が `features/` を見ないため）|
| 毎月の照らし合わせ（手作業・ADR-1080 と同じ日）| Google の請求と台帳の差。記録は monthly-reconcile.md | 関所なし（手作業）|
