# 秘書 LIVE 設計の審査（architect）

この文書は何か: `origin/release/secretary-live-design`（139054fb4）の設計 4 冊と ADR-1085 草案を、実装に渡してよいか読んで確かめた審査の結果です。製品のコード・DB・本番・secrets は触っていません（読むだけ）。

- 審査日: 2026-11-21（クラウドの審査役）
- 審査した物: `docs/handoff/secretary-live/{kgi,design,recon,research}.md`・`docs/adr/ADR-1085-secretary-live-voice.md`（いずれも `git show origin/release/secretary-live-design:<path>`）
- 照らした物: `AGENTS.md`・`docs/STANDARD-WORKFLOW.md`・`docs/ai-agents/design-partner.md`、ADR-1056・1058・1080・1082・1004・1003・135・136・144 の本文（origin/main）。ADR-027・067 は recon.md 経由で要点のみ（本文は精読していない＝未確認）
- 外部ドキュメント: Context7 MCP はこの実行環境に無かった（ToolSearch で `context7` を探して出ず）。Gemini Live・ephemeral token・Web Speech・AudioWorklet・iOS の挙動は**すべて未確認**。以下の「未確認」はこの意味。

## 判定: **REVISE（直す必要）**

1. 方向（Gemini Live＋秘書の仕事は今の道に任せる）は ADR-1056 の骨格と合うが、**月の上限と使用量の台帳（L12・ADR-1004/1058）が作りとして成り立っていない**。使用量は画面→Google の直通では backend が見られず（設計自身が未確認と認めている）、上限は「始まりを止める」だけで KGI の「LIVE が止まる」と食い違う。
2. **声の「はい」で作る案（L11）は、請求書では今の「作る」の条件（送料なしの人の確認ほか）を声で満たせず、予定でも相づちの「はい」で作る事故の恐れが残る**。
3. 設計の完了定義（維持の仕組み欄・親リンク・素人向け 1 行説明）が欠け、ADR-1056/1058 の改めが不足（道具を渡さない・AI の担当表）。KGI も PO 未再確認。作り直しではなく、下の「直す必要」を直せば APPROVE に近い。

## 0. file:line の突合（design.md が引いた行を origin/main で 1 つずつ確認）

合わない行: **0 件**（下の表は全て実物と一致）。ただし**文面の食い違い**が 2 件ある（表の下）。

| 引用 | 実物（origin/main） | 結果 |
|---|---|---|
| `frontend/src/features/secretary/SecretaryChat.tsx:59`・`:66` | `voiceOn` の state・`voiceOnRef` | 一致 |
| 同 `:83-97` | `onVoiceChange`・`speakFor` | 一致 |
| 同 `:241-244` | 声で返事の `Toggle` | 一致 |
| 同 `:255-265` | `{isMobile && (<IconToggleButton …` | 一致 |
| `useSecretaryListen.ts:115-117` | `lang="ja-JP"`・`interimResults=true`・`continuous=false`（`:117`） | 一致 |
| `secretaryApi.ts:10` | `SECRETARY_MAX_TEXT = 1000` | 一致 |
| `backend/app/schemas/assistant.py:44` | `text: str = Field(min_length=1, max_length=1000)` | 一致 |
| `secretary-agent/server.mjs:131` | `POST /intent` | 一致 |
| `nginx/nginx.conf:96` | CSP `connect-src 'self'` | 一致 |
| 同 `:100` | `microphone=(self)` | 一致 |
| 同 `:294` | `location /api/ {`（Upgrade 無しは recon の読みを採用） | 一致 |
| `backend/app/routers/assistant.py:98-103` | `_SECRETARY_DEPENDENCIES` 4 つ | 一致 |
| `.github/workflows/deploy.yml:570-575` | nginx 作り直しの注記（2〜3 秒の 502） | 一致 |
| `docker-compose.yml:98`・`:246` | `GEMINI_API_KEY`（backend と celery-worker の 2 か所） | 一致 |
| `frontend/src/constants/icons.tsx:416` | `SECRETARY_ICONS = { listen: … }` | 一致 |
| `docs/handoff/secretary-voice-input/design.md:31` | 読み上げの間マイクを閉じる | 一致 |
| `SecretaryChat.test.tsx:501-631` | `describe("SecretaryChat voice reply")`（`:501`）〜V3-g（`:608`）、聞き取りの印は `:633` から | 一致 |
| `migrations/20261117_100100_add_llm_usage_tts_characters.sql` | 「定義に値が無いときだけ作り直す」冪等の型 | 一致 |

文面の食い違い:
- design.md §4（`design.md:37`）は料金を「Opus が Context7 で公式資料を確かめた値」と書くが、research.md `:5`・`:6` は「公式ページを直接読めていない・数値は公式で再確認してから設計に使うこと」と書く。どちらが本当かをこの審査では確かめられない。**直す必要**: design.md の料金・待ち時間の各行に「公式を読んだ／第三者」を付け、research.md の注意と矛盾させない。
- design.md §3 `:33` の「Google の有料の契約はすでにある（30 日で $40.55）」の根拠は台帳の `cost_usd`。これは `llm_budget.py:225-250` の `calculate_usage_cost` が価格表から**計算した値**で、請求書ではない。つまり「請求が立つ有料枠の鍵か」「学習に使われない枠か」の証拠にはならない（本番の台帳は審査役は触らないため $40.55 自体も未確認）。→ §4 の (2) と PO が決めること A へ。

## 1. 見る点ごとの判定

### (1) L1〜L12 を本番で○×に一義に判定できるか

**直す必要**（12 本のうち 7 本が曖昧）。

| # | 判定 | 理由・直し方 |
|---|---|---|
| L1 | 問題なし | 画面を見るだけ。 |
| L2 | 直す必要 | 「PC」のブラウザを決めていない。Web Speech は Chrome 系前提（Firefox は対応しない＝一般的な理解・未確認）。**測るブラウザ・OS・版を kgi.md に書く**。iPhone のホーム画面アプリ（research.md §2 の 748048）を含むか外すかも決める。 |
| L3 | 直す必要 | 「1 分話し続けても止まらない」は `continuous=true` だけでは保証されない可能性（ブラウザが一定時間・無音で自動終了することがある＝未確認）。`onend` での再開と文の重複の扱い（design.md §7 に無い）を書き、「止まらない」を「話し始めから終わりまでの文字が欠けず残る（欄の文字数が話した内容と一致）」に言い換える。 |
| L4 | 問題なし | 「触らずに 5 往復」は数えられる。ただし「触らない」に消音・終了を含めないと明記。 |
| L5 | 直す必要 | 「話し終わり」の定義が無い。耳と時計では 18/20 を判定できない。**画面側に計測を入れる**（こちらの最後の音声の送出から、相手の最初の音声の再生開始まで・ミリ秒）。試しの便 T の成果物に「計測ログを残す」を入れる。 |
| L6 | 直す必要 | 「1 秒以内に止まる」は人の耳で測れない。L5 と同じ計測（こちらの声の検出→再生停止）。 |
| L7 | 問題なし | 2 秒黙って打ち切られないは観測できる。 |
| L8 | 直す必要 | 「LIVE を終えた後も会話に残る」は、今の会話が `useState` だけで、窓を閉じると消える（recon.md `:1-8`・`SecretaryChat.tsx:69-81` の `close()`）ことと矛盾しうる。**「窓を開いている間は残る・閉じたら消える（今のまま）」と書く**。 |
| L9 | PO が決めること | 「ゆっくり」は指示文だけで効くか未確認（design.md §5 も「効かなければ試しの便で分かる」）。効かなかったときの扱い（L9 を外す／別の方法）を PO が先に決める。 |
| L10 | 直す必要 | 「声が届かない」を何で見るか無い。**消音中に話した内容が、こちらの発言の文字として出ない・秘書が反応しない**を合格にする。マイクが実際に止まる（ブラウザのマイク使用中の表示が消える）のは終了だけで見る。 |
| L11 | 直す必要 | §(3) 参照。請求書の側は今の条件を声で満たせない。 |
| L12 | 直す必要 | §(4) 参照。「LIVE が止まる」と「始まらない」が別物。費用を見る画面が設計に無い。 |

### (2) 秘書の仕事を今の `POST /assistant/messages` に任せる作りで、写しが増えないか・書き込みの道が無いか

**問題なし（骨格）／直す必要（3 点）**。

事実: `POST /assistant/messages` は何も作らない（recon.md §2-1、`backend/app/routers/assistant.py:266-440`）。作成は画面の `POST /invoices`・`POST /calendar/events` を本人のログインで呼ぶ（`SecretaryDraftInvoice.tsx` の `submit`・`SecretaryDraftEvent.tsx:53-69`）。LIVE の道具を「文を渡すだけ」にすれば、データの写し・書き込みの道は増えない。ここは ADR-1056 What `:18` と整合。

直す必要:
1. **ADR-1056 の改めが足りない**。ADR-1085 What は「AI 会社へ送るのは書いた文だけ」だけを改めるが、ADR-1056 `:15`（道具は全部切る）・`:16`（AI に渡すのは利用者が書いた文と今の日時だけ）・Why `:28`（頼みの文に紛れた命令に AI が従っても道具もデータも無い）も崩れる。LIVE では (a) Gemini Live に関数呼び出しの道具がある、(b) 道具の引数の文は**利用者が書いた文ではなく Gemini が言い換えた文**、(c) 道具の結果（相手の会社名・金額）が Gemini に戻って音声になる。ADR-1085 の「ADR-1056 のうち改める点」に 3 点を足し、(c) による「結果の文に紛れた命令」への備え（道具は 1 つだけ・結果は読むだけで次の道具の引数に使わせない・書き込みの道は無い、の試験）を書く。
2. **karte（予定の聞き返し）の状態の置き場**が無い。`POST /assistant/messages` は文＋`karte`（`schemas/assistant.py:44` 以降）を取り、聞き返しは画面が持つ（recon.md `:1-1`・`SecretaryKarteAsk`）。LIVE の道具は「文」しか持たない（design.md §5）。聞き返し中に声で答えるとき、画面が karte を付けて送る前提を一文書く。
3. **AI の担当表（ADR-1058）との整合が無い**。ADR-1058 What `:17`・`:23` は「コードの固定値のモデル名は消す・読むのは `get_ai_assignment(job_key)` だけ・値の一覧の正本は DB の CHECK」。LIVE に新しいモデル（Gemini 2.5 Flash Native Audio）と新しい仕事を足すのに、`job_key`（例 `secretary_live`）の追加（`migrations/20261103_120000_create_ai_job_assignments.sql:32`・`:44`・`:56` の CHECK の作り直し）も、読まない前例の扱い（読み上げ `secretary_tts` は担当表に無く、provider `google_tts` が `llm_budget.py:184` にだけある）も design.md に無い。さらに design.md §4 は「OpenAI へ切り替えは担当表の 1 行で済む」と書くが、ADR-1058 `:18` では選択肢（provider・model）は migration でしか足せない。**どちらの型（担当表に入れる／読み上げ型でコード 1 か所）にするかを決め、「1 行で済む」を直す**。

### (3) 声の書き起こしの一致で作る案の事故の恐れ

**直す必要（重い）**。

事実:
- 請求書の「作る」は `canCreate`（`frontend/src/features/secretary/SecretaryDraftInvoice.tsx:113-114`）が真のときだけ押せる。条件に `shippingNone`（人が「送料を請求しない」にチェック・`:6-7` の冒頭の説明と `:78`）・通貨・支払方法・会社と担当者の選択が入る。`submit`（`:116-`）はその部品の中の state を使う。
- 予定の「作る」は `canCreate`（`SecretaryDraftEvent.tsx:46-51`）と `submit`（`:53-`）が部品の中にある。
- design.md §5-1 は「画面が『作る』と同じ処理を呼ぶ」とだけ書く。

穴:
1. **請求書は、声の「はい」で `shippingNone` を満たせない**。声で作れるなら今の安全の条件（人のチェック）を迂回する。作れないなら L11 の「請求書 5 回・下書きが出る 9/10」と、声の「はい」で作る機能が請求書では成り立たない。→ **請求書は声では作らず、画面の「作る」だけにする**（推奨）。予定だけ声の「はい」を許す。または、請求書も声で作る場合は `shippingNone` を声で読み上げて確かめる仕様を足す（推奨しない）。
2. `submit` が部品の中なので、声の「はい」から呼ぶには呼び出しの口を部品の外へ出す（ref・コールバック）改修が要る。design.md §10 の便 B の中身にも、§2 の変更ファイルにも書かれていない。**書く**。
3. 「はい」は日本語で最も多い相づち（「はい、続けてください」）。一致する時間が「下書きが出ている間」で、Gemini が中身を読み上げている最中も含む（§5-1 は「読み上げてから作りますか？と聞く」としつつ、一致の窓を閉じる条件を書いていない）。**一致の窓は「確認の質問（作りますか？）の再生が終わってから、次のこちらの発話 1 つ」だけ**にし、「はい」「作って」と**完全一致**（部分一致不可）、複数文・割り込み中・Gemini の発話中は無効、と書く。
4. 書き起こしは Gemini Live の入力の書き起こし（別料金・design.md §4 の表）で、精度の保証が無い。聞き間違い（「いいえ」→「はい」）の確率は未測定。L11 の合格（確かめずに作る 0）の測り方は**予定 5 回だけでは足りない**。**「いいえ」「やめて」「待って」の否定を 10 回ずつ言い、作られた回数 0**の試験を足す（McDonald's の例＝research.md F1 の学びを実際の試験にする）。
5. 同じ吹き出しの「作る」ボタンを人が押す道は残るので、声の道が壊れても事故にはならない。ここを**ADR に明記**（声の道は付加・画面のボタンが正本）。

### (4) 月の上限と台帳の値の追加が ADR-1004・1058・1080 の型に合うか

**直す必要（重い）**。

型に合う点: 値の追加を migration 1 本・「定義に値が無いときだけ作り直す」冪等にする（`migrations/20261117_100100_add_llm_usage_tts_characters.sql`）のは ADR-1058 `:23`（正本は DB の CHECK、写しは CI で一致を確かめる）と合う。一致の試験は既にある（`backend/tests/test_secretary_voice_pg.py:104` が CHECK と `USAGE_PURPOSES` を比べる）。

合わない・不足の点:
1. **使用量の入り口が無い**。ADR-1004 Decision 2 は「応答を受け取り usage を読めた時点で、呼び出し元と同じ取引で 1 行書く」（`docs/adr/ADR-1004-llm-usage-ledger.md:26`）。LIVE は画面→Google の直通で、backend は応答を見ない。design.md §6 は「画面を通らずに backend が使用量を受け取れるか**未確認**」と書く。受け取れなければ、台帳の行は画面が送る値になる（利用者の端末が改ざん・未送信・閉じて送れない）。すると**月の上限が数字として信用できない**（行が無い LIVE は上限に数えられない）。**実装可否を左右する**（(8) 参照）。直し方の候補: (a) 札を出す時点で「1 回 15 分ぶんの最大費用」を先に台帳へ仮の行として書く（確認できた使用量で後から直す／直らなければ最大のまま）、(b) backend 中継に倒す（design.md §5-3 で退けた案を、費用の確かさと引き替えに再検討）、(c) 画面が終わりに送る値を「申告」と明記し、Google の請求との月 1 回の照らし合わせ（§11）で補う（上限の守りは弱い）。どれにするかは PO が決めること。
2. **「LIVE が止まる」（kgi.md L12）と設計の食い違い**。design.md §6 は「超えたら札を出さない（LIVE が始まらない）」。始まった後に 15 分走る間は止まらない。ephemeral token の期限は design.md §5-2 で「開始まで 1 分」で、開始後の失効はこの設計では未確認。**L12 を「上限に届いた後は新しい LIVE が始まらない」に書き直す**か、途中停止を設計する（札の期限・画面の自動終了・上限までの残り分の計算）。
3. **上限の値の置き場が無い**。読み上げの上限は定数 `MONTHLY_CHAR_CAP = 900_000`（`backend/app/services/secretary_voice.py:22`）。LIVE の上限は「PO が決める額」（§12）だが、(a) 保存先（定数なら変えるのに配備が要る。§15 の戻し方「上限 0 円にする」と L12 の「上限を小さくした試し」は配備無しでは出来ない）、(b) 既存の `tenant_llm_budgets`・`check_budget`（`backend/app/services/llm_budget.py:498`・`:441`）との関係が書かれていない。recon.md `:214` は「秘書から使われているか未確認」。**既存の月の予算の仕組みを使うか使わないかを理由付きで決める**。
4. **値段表が音声に合わない**。`LLM_PRICING`（`llm_budget.py:56`）は 1 モデルにつき入力・出力の 2 単価で、`calculate_usage_cost`（`:225-250`）は音声と文字を分けない。Gemini Live は音声と文字で単価が違う（design.md §4・research.md の表の「版の食い違い」）。**式の拡張（音声・文字を別単価にする）と、1 行に残す量の列（音声の秒・トークン）を設計する**。「正本は `llm_budget.py` の 1 か所」は正しいが、そこに式の変更が要ることが書かれていない。design.md §2 の対象にも無い。
5. **粒度の食い違い**。ADR-1004 は 1 行＝応答 1 回、ADR-1058 `:24` は成功も失敗も 1 行（`outcome`・`error_code` 9 種）、ADR-1080 は読み上げ 1 回＝1 行。design.md §6 は「LIVE 1 回を終えるごとに 1 行」。失敗（札を出せない・つなげない・途中で切れた）の行と、ADR-1004 の改め（Decision 1 を LIVE にも広げる）が ADR-1085 の「改める点」に無い。**足す**。
6. **L12 の「今月の費用を画面で見られる」の画面が無い**。読み上げの字数を見る画面は、スーパー管理の解析ダッシュボード（`backend/app/routers/tcg_analysis_dashboard.py:694`・`:939-:1050` の `secretary_tts_month`）。LIVE の費用をそこに足すのか別の画面かが設計に無く、§2 の対象にも `tcg_analysis_dashboard.py` が無い。**足す**。
7. `sdk` に新しい値 `google-genai-live` を入れるなら、`USAGE_SDKS`（`llm_budget.py:174`）と `USAGE_SDKS_BY_PROVIDER`（`:180-185`）の対応（画面のログインの○×と回数が引く・`backend/tests/test_super_admin_ai_jobs.py:29` が見ている）も要る。design.md §6 に無い。OpenAI に切り替える場合の sdk の値も要るので、**migration を 1 本で済ませたいなら今のうちに両方の値を入れるか、二つ目の migration を認める**（(6) 参照）。

### (5) CSP の `connect-src` に Google を足す案と、鍵を画面に出さない札の案の穴

**直す必要**。

事実: CSP は `script-src 'self'`・`connect-src 'self'`・`default-src 'self'`・`media-src` 無し（`nginx/nginx.conf:96`）。`frontend/src` に `AudioWorklet`・`getUserMedia` は 0 件（recon.md `:216` の検索を再確認: `git grep -n "AudioWorklet\|getUserMedia"` は 0 件）。

穴:
1. **「CSP 1 行」では足りない可能性**。マイクの音を取り出して送るには一般に AudioWorklet（または同等の処理）が要り、その読み込みは `script-src` の対象になると理解している（**未確認**・Context7 無し）。ブラウザ内で作る blob の URL の worklet は `script-src 'self'` で止まりうる。**静的なファイルとして同じ origin から出す（Vite の公開物）と書く**。`wss://` の `connect-src` を足すだけの設計は、最初の実機で動かない恐れ。便 T で最初に確かめる項目にする。
2. **接続先の指定が広すぎる/狭すぎる**かが未確認（`wss://generativelanguage.googleapis.com` のみで足りるか、ephemeral token の取得先は backend 側で画面は使わないか）。ADR-1085 に「接続先は便 T の実測で確定」と書く。
3. **短い期限の札の守り**が design.md §5-2 に「1 回だけ使える・開始まで 1 分」とあるが、(a) 札に紐づく設定（モデル・指示文・道具の定義・音声の種類）を**札を作る側（backend）で固定して画面から変えさせない**（札が漏れたとき他の用途に使われない）、(b) 札を出す口の**呼び出し回数の上限**（1 人が何度でも札を出せると上限が回避される）、(c) 札の期限・開始後の延長の仕様は未確認、(d) 画面のログに札を出さない、が無い。ephemeral token は Live API の version 限定（v1alpha）の記述が research.md `:30` にあり、`google-genai>=1.0.0`（`backend/requirements.txt`）の下限で作れるかは**未確認**。実装前に使う版を固定する。
4. §11「札の口の返事に Gemini の鍵が無い」試験は**必要条件**。**足りない部分**: backend のログ・エラー文に鍵や札が出ない試験、`docker-compose.yml:98`・`:246` が既存の鍵を celery-worker にも渡している点（LIVE に使うのは backend だけ）の確認。
5. 守りは `_SECRETARY_DEPENDENCIES`（`assistant.py:98-103`）を使い回す、は正しい。札の口が `feature` と `super admin` を見る試験を足す。

### (6) 便 T・A・B・C の分け方と migration の GO の扱い

**直す必要（軽い）**。

- 分け方（T→B 依存・A 独立・C は B の後）は筋が通る。
- **便 T が重すぎる**。台帳・上限・migration・backend の口・画面・nginx の変更を 1 便に入れつつ「試し」。migration が入るので PR 全体が PO の「GO #番号」まで main に入らず（ADR-135・ADR-136。GO は ADR-1003 で Opus に委譲されるが、例外 7 項目＝DROP TABLE/COLUMN を含む migration など＝には当たらない。当てはまらないので委譲の GO で足りる、が本審査の読み）、**試しの実測（L5 の速さ）が migration の GO を待つ**。かつ L5 を満たさず OpenAI へ切り替えると、台帳の値を足す migration の二度目が要る（(4)-7）。
- 直し方: **便 T0（試作・台帳と上限なし・migration なし・PO だけ・本番の機能の旗は切ったまま・費用は札を出す口の回数の上限のみ）→ 便 T1（台帳・上限・migration）** に分ける。T0 は L5・L6・L7・iPhone の実機だけを測る。T0 でも本番に出すと費用が出るので、**PO への「有料の声の AI」の了承（下の A）が T0 の前に要る**。
- 便 A（マイクを PC にも）は T から独立なので先に出せる。ただし (1)-L3 の再開の仕様が先。
- 便 C は、`声で返事`を消すと設定の「秘書の声」（`frontend/src/pages/account-settings/PreferencesSection.tsx:9-16`・ADR-1080 What 2 の `public.users.secretary_voice`）と `POST /assistant/speech` が使い道を失う。**LIVE の声に同じ 4 声を使うのか・読み上げの口を残すか消すか**を決めて書く（design.md に無い）。
- nginx の変更（CSP）は `migrations/`・`deploy.yml`・本番 `scripts/` に当たらないが、画面・backend の変更はユーザーに影響する変更の GO の対象（`docs/STANDARD-WORKFLOW.md` の「完了の定義」）。各便に GO 記録を付ける旨を書く。

### (7) §11「続けるための機械の仕組み」が足りるか

**直す必要**。

1. 設計の完了定義 `docs/STANDARD-WORKFLOW.md §1.7`: design.md の末尾に「## 維持の仕組み」（守り手・対象・関所なしの場合）が必須（空欄不可）。design.md に**この見出しは無い**（`grep -n "維持の仕組み\|守り手"` で 0 件）。§11 は表で同等のことを書くが、**守り手のファイルパス（関所の実在するファイル）を書いていない**。process-artifacts の関所が見るのは欄と守り手パスの非空・実在（初期は警告）。**足す**。
2. 同 §1.6: design.md 冒頭に親（`docs/specs/secretary-chat/README.md`）へのリンクと「この文書は何か」の素人向け 1 行が必須。design.md の冒頭（`:1-7`）には KGI・現在地・ADR へのリンクはあるが、**親の仕様書のリンクと 1 行説明が無い**（kgi.md `:3-5` にはある）。同 §1.5 の「ideal-state.md」（`docs/specs/secretary-chat/` に既にある）に、LIVE のあるべき姿の追記が要るかを PO に確かめる。
3. §11 の「今あるか」欄の誤り・過大:
   - 「金型外の見た目: CI の ADR-144 の検査・デザイントークンの検査 **ある**」は過大。ADR-144 の生の `<select>`・`<input>`・checkbox の検査は `frontend/src/pages/**` の変更だけを見て、`features/`・`components/` は検査しない（`docs/adr/ADR-144-ui-component-governance.md:134`・`scripts/check-ui-governance.js:47-48`・同 `:16-18` で `features/` も見るのは `loadingTernary` と `englishUiLiteral` だけ）。LIVE の画面は `features/secretary/` に作るので、**金型を守る機械は日本語の直書き禁止と loading の書き方だけ**。人の審査（`docs/CC_UI_GOVERNANCE.md`）に頼ることを**書く**。
   - 「台帳の値の取り違え: ある」は正しい（`backend/tests/test_secretary_voice_pg.py:104`）。ただし `USAGE_SDKS_BY_PROVIDER` との整合（`test_super_admin_ai_jobs.py:29`）も更新が要る。
4. 足りない仕組み: 
   - 「道具は 1 つだけ・作るはこちらの書き起こしの一致だけ」の試験は §11 にあるが、**一致の仕様（完全一致・窓・否定語）の試験**（(3)-3,4）が無い。
   - **LIVE の途中の費用の見張り**（上限に近づいたときの通知）が無い。月の照らし合わせは手作業（ADR-1080 と同じ）で、「Google の請求と台帳の合計の差」の許容幅も無い。
   - **計測ログ**（L5・L6 の時間）の保存先と見方が無い。
   - 守り手の関所に、`docs/adr/FEATURE-INDEX.md:77` の行（ADR-1085 を足す）を更新する作業が無い（`docs/INDEX.md` の「新しいテーマ」の運用）。
5. 仕様書の索引: ADR 番号 1085 は origin/main に無く（ADR-1084 まで）重複しないが、**起案ブランチと同時に他が 1085 を取る可能性**は `node scripts/generate-adr-index.js` と CI で止まる。問題なし。

### (8) 未確認の点が実装可否を左右するか

| 未確認の点 | 実装可否を左右するか | 判定 |
|---|---|---|
| 使用量の受け取り方（画面を通らず backend が受け取れるか） | **左右する**。(4)-1 のとおり、上限と台帳の信頼性の土台。 | **PO が決めること**（候補 (a)(b)(c)）。T0 の前に使用量の返り方を Google の公式で読む（Context7 が使える環境で）。 |
| 15 分の続け方 | 左右する（LIVE が 15 分で切れて続けるとき、会話を引き継ぐ再接続が要る・秘書は 1 回の用事が短いので影響は小さいが、「黙って 2 分で終える」と別に、15 分到達の見せ方と引き継ぎが要る）。 | **直す必要**: 「15 分で終わる・文字は会話に残る・必要なら押し直す」を最初の仕様にして、続ける機能は後にする（T0 で測る）。 |
| 1,000 字の上限（`schemas/assistant.py:44`・`secretaryApi.ts:10`） | (A) のマイクが長い文を出す設計なので、左右する。 | **直す必要**: 変えるかの判断は PO（design.md §7 も PO 確認と書く）。変えない場合は 1,000 字超で欄の下に字数を出す案（§7）で足りる。容器 80 秒・body 15,000 バイトの上限（`assistant.py:89`・`secretary-agent/server.mjs:15`）から**長い文の動作は便 A の前の試しで測る**と書いてあり、それで足りる。 |
| iPhone（ホーム画面アプリの聞き取り・音・消音スイッチ） | **左右する**。(A) の Web Speech がホーム画面アプリで動かないなら、(A) は有料の書き起こしに倒れ、費用と台帳が変わる（design.md §7 も「有料」と書く）。 | **PO が決めること**: iPhone を「ブラウザ（Safari）のみ対象」とするか、ホーム画面アプリを含めるか。含めるなら便 T0 で実機を先に測る。 |
| ephemeral token の仕様（版・1 回・期限）・Gemini Live の日本語・割り込みの精度・L9 の指示文 | 左右する（T0 で測る） | 問題なし（T0 で測る前提）。ただし**公式を読んで版を固定してから T0**。 |
| Google 鍵が有料枠・学習に使わない設定か | **左右する**（ADR-1056 の改めの根拠）。 | **PO が決めること A**（下）。 |

## 2. 「直す必要」の一覧（設計担当が直すもの）

1. kgi.md: L2・L3・L5・L6・L8・L10・L12 の測り方を一義にする（§1）。PO の再確認（kgi.md `:9-11`）が済むまで設計は「合格の条件」に使えない。
2. design.md §5-1: 声の「はい」の仕様（請求書は声で作らない／予定のみ・完全一致・窓の閉じ方・否定語の試験）。`submit` を部品の外へ出す改修を便 B に書く。
3. design.md §6: 使用量の入り口（候補 (a)(b)(c)）・上限の置き場・既存の `tenant_llm_budgets` との関係・音声の値段表・失敗の行・LIVE の費用を見る画面。
4. design.md §5-3・§5-2: AudioWorklet を静的ファイルで出す・札の設定を backend で固定・札の口の回数の上限。
5. ADR-1085: ADR-1056（道具・書いた文だけ・Why の命令の話）・ADR-1058（担当表）・ADR-1004（1 行の粒度）・ADR-1080（読み上げの口を残すか）の改めを全部書く。
6. design.md §10: 便 T を T0（試作）と T1（台帳・上限・migration）に分ける。migration を 1 本にするか 2 本を認めるか。
7. design.md §11: 「維持の仕組み」欄（守り手の実在パス）・親リンク・素人向け 1 行。§11 の ADR-144 の「ある」を訂正（`features/` は見ない）。
8. design.md §4: 料金・待ち時間の各値に「公式を読んだ／第三者」を付けて research.md と矛盾させない。

## 3. PO が決めること

- **A. 有料の声の AI を使うか・Google の鍵が有料枠か**（請求が立つこと・学習に使われないこと）。台帳の `cost_usd` は計算値で請求の証拠ではない。PO が Google の請求画面で確認する。
- **B. ADR-1056 を改めてよいか**（こちらの声と秘書の返事の文＝会社名・金額を含みうる＝が Google に渡る・Gemini に道具が付く）。
- **C. 月の上限の額と、使用量の取り方**（(4)-1 の (a)(b)(c)）。
- **D. iPhone のホーム画面アプリを対象に含めるか**。
- **E. L9（ゆっくり）が効かなかったときの扱い**。
- **F. 1,000 字の上限を変えるか**（design.md §7 の確認事項）。
- **G. 「声で返事」を消した後、設定の「秘書の声」と読み上げの口をどうするか**。

## 4. 問題なしと確認した点

- design.md が引いた file:line は origin/main の実物と全て一致（§0）。
- 秘書の仕事を今の `POST /assistant/messages` に任せ、作成は画面の既存の「作る」（本人のログイン）に任せる骨格は、データの写しも AI の書き込みの道も増やさない（ADR-1056 `:18`）。
- マイクの許可は既に開いている（`nginx/nginx.conf:100` `microphone=(self)`）。LIVE のために Permissions-Policy を変える必要は無い。
- 台帳の値の追加は「定義に値が無いときだけ」の冪等 migration の型（`migrations/20261117_100100_add_llm_usage_tts_characters.sql`）に沿う。CHECK と `USAGE_PURPOSES` の一致の試験が既にある（`test_secretary_voice_pg.py:104`）。
- 外の事例（research.md §3）に成功 4 件・失敗 2 件の数値があり、3 件目の失敗が見つからなかったことを正直に書いている。design.md §14 の「事例の参照と我々への応用」欄は空欄ではない（完了定義を満たす）。
- 戻し方（design.md §15）の方向（画面の機能の旗・台帳の冪等・便ごとに戻す）は妥当。ただし「上限 0 円」の置き場は (4)-3 のとおり未定。
- 製品のコード・DB・本番・secrets には触っていない。審査役の本番の読み取りも行っていない（$40.55 などの本番の値は確かめていない）。
