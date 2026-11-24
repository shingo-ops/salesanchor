# 秘書 LIVE 設計の審査 4 回目（architect）

この文書は何か: `origin/release/secretary-live-design` の直した 4 版（design.md・kgi.md・ADR 草案）とマイクの便 A の作業指示書（card-binA.md）を、実装に渡してよいか読んで確かめた 4 回目の審査の結果です。製品のコード・DB・本番・secrets は触っていません（読むだけ）。
親（あるべき姿）: [docs/specs/secretary-chat/README.md](../../specs/secretary-chat/README.md)／3 回目: [review-architect-3.md](review-architect-3.md)

- 審査日: 2026-11-23（クラウドの審査役）
- 審査した物: `docs/handoff/secretary-live/{design,kgi,card-binA,review-architect-3}.md`・`docs/adr/ADR-1085-secretary-live-voice.md`（`git show origin/release/secretary-live-design:<path>`）。3 回目からの差は `git log -1 -p origin/release/secretary-live-design`（`5a1281eb4`）で読んだ。
- 実物の基準: `origin/main` の `9019d83e8`。3 回目の基準 `bef5a7a8b` との間に、設計・カードが引く `frontend/src/features/secretary`・`frontend/eslint.config.js`・`frontend/src/locales`・`backend/app/routers/assistant.py`・`backend/app/services`・`backend/tests/ops`・`migrations/20261024_100300_create_ai_cloud_views.sql`・`nginx`・`frontend/package.json` の差は無かった（`git diff --stat bef5a7a8b origin/main -- <それらの道>` が空）。ただし `docs/adr/` には別の ADR-1085 が既にある（§3 の N1）。
- 外部文書: 今回の指示で「つなぎ先の道具は使わない」ため使っていない。Gemini Live・Web Speech の実ブラウザの動き・料金など外の事実は**すべて未確認**。
- 本番: 触っていない。

## 判定: **REVISE（直す必要）**

1. 3 回目の指摘 R1〜R7 は、文面ではすべて直っている（§1）。設計の骨格は作り直し不要。
2. **新しく見つかった重い穴が 1 つ**: ADR の番号 `ADR-1085` が `origin/main` で別の決め（`docs/adr/ADR-1085-browser-operation-delegation.md`）に既に使われている（§3 の N1）。設計・カード・ADR 草案の全部が「ADR-1085」と書くので、このままでは 2 つの別の決めが同じ番号になり、便 A の `FEATURE-INDEX.md` の行も別の ADR を指す。CI の索引検査は止めない（実物で確認）ので、人が直さないと残る。3 回目までの審査も見落としていた。
3. 便 A のカード（card-binA.md）は、引いた file:line が実物と合い（ずれ 3 件・軽い）、触るファイル・変更・試験・止まる条件が足りている。**便 A（マイク）だけの合否は「合格（実装に渡してよい）」。ただし渡す前に §4 の C1〜C3（ADR 番号・行番号・受け口の書き方）をカードに直す**。LIVE（便 T0 以降）は REVISE（N1・N2 を直せば APPROVE に届く）。

### 便ごとの合否

| 対象 | 合否 | 条件 |
|---|---|---|
| 便 A（マイクの印・card-binA.md）| **合格** | 実装役に渡す前に、§4 の C1〜C3 をカードに直す（設計の作り直しは要らない。マイクの便は backend・migration・台帳に触れず、ADR 番号は `FEATURE-INDEX.md` の 1 行と eslint の注釈だけに現れる）|
| LIVE（便 T0 以降）| **REVISE** | N1（ADR 番号の衝突）と N2（読み上げの文の「相手」の食い違い）を直してから。R1〜R7 の中身は直っており、それ以外の新しい重い穴は見つからなかった |

## 1. R1〜R7（review-architect-3.md §2）が design.md §0-3 の表のとおり直っているか

| # | 3 回目の指摘 | 判定 | 実物で確かめた結果 |
|---|---|---|---|
| R1 | 予定の「はい」を読み上げた下書きに結ぶ・読み上げの項目・読み上げの忠実さ | **直った**（小さな残りは N2）| design.md §5-1 の 1（空でない項目を全部入れる・`:148`）・5（読み上げた文と下書きの識別子を 1 組持ち、欄が変わる・別の下書き・窓の外で窓を閉じる。「はい」の瞬間に今の state から文を作り直して同じときだけ `submit`・`:152`）・6（`submit` の前に窓を閉じる・`:153`）・7（書き起こしが画面の文と一致するときだけ窓を開く・`:154`）が、3 回目の直し方 1〜4 と同じ中身で入った。試験は §11（`:301`）に 3 つ足された。事実の裏: 欄が部品の中の state で読み上げの後に直せること、`canCreate` が題名・日付・時刻と `!saving` だけであること、送る中身が `add_meet` などを含むことは `frontend/src/features/secretary/SecretaryDraftEvent.tsx:46-51`・`:53-69` で確認した（変わっていない）。ADR 草案 Decision 3（`docs/adr/ADR-1085-secretary-live-voice.md:17`）にも同じ中身が入った |
| R2 | 新しい列の読み取りビューの分類 | **直った** | design.md §6-3 `:212`・§10 `:285`・§11 `:303`。実物: `backend/tests/ops/test_ai_cloud_views.py:52-55`（`_PASS_TYPES` に配列型は無い）・`:494-522`（型が通らず行が無い列は分類の漏れ）・`:486`（1165 固定）・正本 `migrations/20261024_100300_create_ai_cloud_views.sql` の `llm_usage_events` の行（`:155-160`）。整数 2 列（`audio_*_tokens`）は型で通る（`:520`）が、配列 2 列は行が要る。設計は「4 列とも行を足して揃える」ので安全側。列名が `_NAME_RE`（`:46-49`）に当たるものは無い（`audio_prompt_tokens`・`audio_candidates_tokens`・`live_reply_latency_ms`・`live_barge_in_latency_ms` の部分文字列で確認）。`ai_ro` 側は `backend/tests/ops/test_ai_ro_views.py` の試験名一覧（10 件）に分類の漏れの試験は見当たらない（全文は読んでいない＝未確認）。設計は「便 T0 の PR の最初に開いて確かめる」と書いており妥当。**軽い足り**: `migrations/20261024_100300_create_ai_cloud_views.sql:3` の注釈の「1165 行」と、元の `docs/handoff/cloud-case-ai/stage1-column-class.tsv` の更新は設計に書かれていない（試験の対象は SQL 側の `:486` だけ。注釈・tsv は便 T0 の PR で合わせるとよい。実装可否には響かない）|
| R3 | migration の作り方 | **直った** | §6-3 `:208-211`。前例 `migrations/20261117_100100_add_llm_usage_tts_characters.sql:7-37`（`pg_get_constraintdef` と `NOT LIKE` の形）が実在し、`scripts/run_all_migrations.sh:1478` に同 migration の `run_sql` の行がある。値の一覧は `backend/app/services/llm_budget.py:159`（`USAGE_PURPOSES`）・`:174-176`（`USAGE_SDKS`）・`:180-185`（`USAGE_SDKS_BY_PROVIDER`）と合う。`backend/tests/test_secretary_voice_pg.py:104-105` が purpose・sdk の一致を見る |
| R4 | 日本語の直書きの override の便・札の口の試験・台本 | **直った** | §9 `:272`・§10 `:285`・§11 `:297`。override は便 A のカード変更 4 に入った（A を先に出すため）。**実物で 0 件を自分でも確かめた**: `origin/main` の `frontend/src/features/secretary/` の 12 ファイル（テスト 3 本を含む）を、行頭の注釈・ブロック注釈・行末の注釈を除いて日本語の文字を数えたところ 0 件。`frontend/eslint.config.js:31` は warn、`:234-246` の除外塊は stories・design-system・locales だけで `features/secretary` を含まない。台本は `docs/handoff/secretary-live/l5-script.md` に置くと決まった |
| R5 | 既存の AI の費用の合計に LIVE が混ざるか・Live の単価 | **直った** | §6-4 `:220-221`。`backend/app/routers/tcg_analysis_dashboard.py:697-698` は `outcome = 'ok'` で絞り、使いみちでは絞らない。「LIVE も合計に含める・便 T1 の PR で `:698` 以降を全文で読む」は妥当。`calculate_usage_cost` が表に無いモデルで `None` を返す（`backend/app/services/llm_budget.py:230-233`）ことも実物と合う |
| R6 | 読む口は書き換えない | **直った** | §6-1 `:186`。「行を書き直すのは札を出す口と使用量の口の中だけ・費用の画面と上限の合計は計算して数えるだけ」。3 回目の直し方と同じ |
| R7 | file:line 4 件 | **直った** | 実物で 1 件ずつ確認: `backend/app/services/secretary_voice.py:18`（`SECRETARY_VOICES`・`:17` は空行）／`frontend/src/features/secretary/SecretaryChat.test.tsx:501-630`（describe は `:501` から `:630`）／`scripts/check-ui-governance.js:16`（loading の検査は `pages/`・`features/`・`components/`）・`:47`（`PAGES_DIR`）・`frontend/eslint.config.js:31`（日本語は ESLint）／`backend/app/services/llm_budget.py:498`（`check_budget`）。`:441`・`voice.py:17`・`:501-631` は設計から消えている（grep で 0 件）|

## 2. 直しで新しく足した file:line の突合（origin/main `9019d83e8`）

一致した行: `frontend/src/features/secretary/SecretaryChat.tsx:63`（受け口）・`:69-81`・`:83-97`・`:232`（`aboveTabbar={isMobile}`）・`:241-244`・`:249`（`maxLength`）・`:255-265`・`:267-273`・`:274`／`frontend/src/features/secretary/useSecretaryListen.ts:104-153`・`:117`／`frontend/src/features/secretary/SecretaryDraftInvoice.tsx:113-114`・`:252-254`／`frontend/src/features/secretary/SecretaryDraftEvent.tsx:46-51`・`:53-69`／`backend/app/routers/assistant.py:89`・`:93`・`:98-103`／`backend/app/routers/tcg_analysis_dashboard.py:698`・`:939`・`:1050`／`frontend/src/locales/ja.json:6324` と `en.json:6324`（`secretary.listen`）／`docs/adr/FEATURE-INDEX.md:78`／`frontend/scripts/check-i18n-missing-keys.js`・`frontend/vitest.unit.config.ts` の実在／`scripts/run_all_migrations.sh:1478`。

合わない行: **3 件（軽い）**

| # | 引用 | 実物 | 直し方 |
|---|---|---|---|
| a | design.md §7 `:253`・card-binA.md 変更 2-1 の `SecretaryChat.test.tsx:715` | 聞き取りの無いブラウザの試験は `frontend/src/features/secretary/SecretaryChat.test.tsx:716`（`it(`）〜`:721`。`:715` は空行 | `:716` に |
| b | card-binA.md「触るファイル」4 の「`describe("SecretaryChat listen mark"` の塊 :633-722」 | 塊は `:633` から `:729`（最後の `it("aborts the recognition when the window is closed"` が `:723-728`）| `:633-729` に（`:722` までと読むと最後の試験が範囲の外）|
| c | card-binA.md 変更 2-2 の「欄（:245 の `Textarea`）」 | `Textarea` は `frontend/src/features/secretary/SecretaryChat.tsx:246`（`:245` は入力行の `div`）| `:246` に |

## 3. 新しく見つかったこと

### N1（重い・LIVE の合否に関わる）ADR の番号 `ADR-1085` が `origin/main` で別の決めに使われている

- 事実: `docs/adr/ADR-1085-browser-operation-delegation.md` が `origin/main` にある（コミット `4b2d8572a` 2026-11-23「design browser operation delegation to Opus (ADR-1085 draft)」。3 回目の基準 `bef5a7a8b` にも入っていた）。`docs/adr/FEATURE-INDEX.md:50` と `docs/specs/README.md:11` が「ADR-1085 = ブラウザ操作の Opus への委任」と書く。`origin/main` の `docs/adr/` の最大は `ADR-1086-inbox-pc-column-width.md`。
- 設計の側: `origin/release/secretary-live-design` は古い枝（`git merge-base` が `2560f963f`）で、`docs/adr/ADR-1085-secretary-live-voice.md` を持つ。「ADR-1085」の出現数は design.md 9・card-binA.md 4・ADR 草案 1（`grep -c`）。`docs/specs/secretary-chat/README.md:31`（設計の枝側）にも同じ番号がある。kgi.md には無い。
- 影響: (a) 2 つの別の決めが同じ番号になり、「ADR-1085 に従え」が一義でなくなる。(b) 便 A のカード変更 5 は `docs/adr/FEATURE-INDEX.md:78` の秘書の行に「ADR-1085」を足すが、同じ表の `:50` の行が既に ADR-1085（別の決め）なので、読み手が取り違える。(c) CI の索引検査 `scripts/ci/check_feature_index.py:60-90` は「番号が 1 つの行に載っていれば足りる」作りで、同じ番号の 2 つ目のファイルは止めない（`missing_adr`・`dup` の条件を読んだ）。**機械では止まらない**ので人が直す。
- 直し方（設計担当）: 秘書 LIVE の ADR を、`origin/main` の最新で空いている番号に付け替える（本審査の基準では 1087 以降が空いているが、**付け替えの時点で `git ls-tree origin/main docs/adr/` を見直して決める**。他の枝が先に取る恐れがある）。ファイル名・ADR 本文・design.md の 9 か所・card-binA.md の 4 か所・`docs/specs/secretary-chat/README.md:31`・FEATURE-INDEX の行・ADR 一覧（`node scripts/generate-adr-index.js`）を揃える。便 A のカードの ADR 番号は、付け替えた番号を使う。

### N2（軽い・LIVE）読み上げの文の「相手」が、予定には無い項目

- design.md `:134`（「画面が予定の下書きの state から「相手・日時」の文を作り」）と ADR 草案 `docs/adr/ADR-1085-secretary-live-voice.md:32`（「予定の確かめの読み上げの文（相手・日時）」）が、3 回目の直しの後も古いまま。同じ設計の `:148` は「予定には「相手」の欄が無いので「相手」とは書かない」「送る中身の空でない項目を全部入れる」と書く。**同じ設計の中で食い違っている**。実物の予定の送る中身は題名・日時・全日・個人か共用・説明・場所・Meet（`SecretaryDraftEvent.tsx:53-69`）。直し方: `:134` と ADR `:32` を `:148` の言い方（空でない項目を全部）に揃える。

### N3（軽い・便 A のカード）カードが設計 §7 に無い決めを 1 つ足している

- card-binA.md 変更 1 は「何も取れないまま聞き直す回数の上限 `LISTEN_MAX_IDLE_RESTARTS = 5`、届いたら止まって `noSpeech` を出す」を足す（無限に聞き直さないための安全弁）。design.md §7 `:252` には聞き直しの上限が無い。逆に design §7 `:254`「聞いている時間に上限は付けない」とは矛盾しない（時間ではなく、何も取れない聞き直しの回数）が、設計に 1 行足して揃えるとよい。
- 同じく、カードの override は試験ファイルを除く（`ignores: ['src/features/secretary/**/*.test.{ts,tsx}']`）が、design.md §9 `:272`・§16 `:366` は `src/features/secretary/**` と書く。試験は `String.fromCharCode` で日本語を作る（`SecretaryChat.test.tsx:635`）ので 0 件だが、設計側にも「試験は除く」を足す。

### N4（軽い・便 A のカード）1,000 字の受け口の書き方が曖昧

- card-binA.md 変更 2-5 は、受け口（`SecretaryChat.tsx:63`）を「足した後の長さが 1,000 以上なら先頭 1,000 字を残し `setTooLong(true)` と `listen.stop()` を呼ぶ」に変えると書く。今の受け口は `setText((prev) => (prev + heard).slice(...))` の更新関数の中で長さが決まる。**更新関数の中で `setTooLong`・`stop` を呼ぶ**と、更新関数は純粋でなければならない（開発時の二重呼び出しで 2 回 `stop` する）。カードは「今の text をどこから読むか」を書いていない。直し方: 「今の text を `useRef` で持ち、受け口の中で `prev` を使わず `ref + heard` で長さを決め、`setText` は値で渡す。`setTooLong`・`stop` は更新関数の外で呼ぶ」と 1 行足す。
- 聞き取りを `stop()` した後に最後の決まった文が届いても、受け口が先頭 1,000 字で切る（今の `slice`）ので壊れない。ここは問題なし。

### N5（注意・便 A のカード）偽物の試験で守れないブラウザの動き

- 聞き直し（`continuous=true` と `onend` での再開）が、実ブラウザで二重の文字・再開の拒否（特に iPhone の Safari）を起こさないかは、カードの試験（偽の `SpeechRecognition`）では測れない。**実ブラウザの動きは未確認**で、カードの「本番の確かめ」（L2・L3 を PO と測る）がその関所。カードの「想定される分岐」には実機の失敗が無いが、配備後の測りで見る前提なので、実装を止める条件には足さなくてよい。便 A の合否に響かない。
- 参考（本審査で確かめた事実）: `frontend/public/sw.js`（16 行）に `fetch` の処理が無い（`grep -c fetch` が 0）。3 回目が「未確認」とした AudioWorklet の service worker のキャッシュは、少なくとも今の `sw.js` では起きない。便 T0 の測りに足した項目（design.md §10 `:286`）は残してよいが、重さは下がる。

## 4. card-binA.md（便 A）の審査

### 4-1 design.md §7・§9 と合うか

合う。マイクを PC にも出す（変更 2-1）・話している間ずっと聞く（変更 1・`continuous=true`）・決まった文字を残して後ろに足す（変更 1 の「二重に足さない」）・1,000 字は変えず字数を出す（変更 2-5・変更 3）・0 円で台帳に書かない（「backend・migration・台帳は触らない」）・override を便 A に入れる（変更 4）・索引に足す（変更 5）が、design.md §7 `:251-254`・§9 `:272`・§11 `:307` と合う。差は N3 の 2 件だけ（設計に足せば足りる）。

### 4-2 引いた file:line が実物と合うか

§2 のとおり、合わないのは 3 件（a・b・c）で、いずれも 1〜7 行のずれ。実装役が実物を開けば直せる程度だが、カードの範囲指定（b）は試験の置き換えの範囲を決めるので直しておく。変更 1 の「今（:104-153）」は実物と一致（`continuous = false` は `useSecretaryListen.ts:117`）。

### 4-3 実装役が迷わず作れるか

作れる。確認した点:

- **触るファイル**: 7 種 8 ファイルで、変更 1〜5 と試験の節に対応する。「確かめ」の 5（`git diff --stat origin/main`）が数を縛る。`isMobile` は `SecretaryChat.tsx:232`（`aboveTabbar`）でも使われるので、`:255` の条件を外しても未使用の引数にならない（確認した）。
- **変更**: `begin()`・`wantRef`・`idleRestartsRef` の分け方は具体的で、`stop()`・`abort()`・`onend`・`onerror` の分岐が書かれている。N4 のとおり受け口の書き方だけ 1 行足りない。
- **試験**: 今の試験のうち直す物の見立てが当たっている。`frontend/src/features/secretary/useSecretaryListen.test.ts:92`（`continuous` が `false` の期待）・`:147-155`（`no-speech` を出してから `emitEnd` する試験。新しい動きでは `noSpeech` を表に出さず聞き直すので、期待が変わる）・`:169-177`（`network` は表に残る）・`:211-220`（`stop` の後の `end` で止まる。新しい動きでも通る）。カードは「(d)(f) に合わせて直す・必要が無ければ触らない」と書き、足す試験 (a)〜(h) と (i)〜(iii) が動きを網羅する。`SecretaryChat.test.tsx:685`（`has no listen mark when isMobile is false`）を反転する指示も実物と合う。
- **止まる条件**: `ignores` を足した塊の設定の誤り・今の試験が書いていない理由で落ちる・`Textarea` が `readOnly` を受けない・見張りに止められた、の 4 つ。`Textarea` は `frontend/src/components/Textarea.tsx` で `TextareaHTMLAttributes` を受ける型なので `readOnly` は通る見込み（実際の流しは未確認）。
- **override の効き方**: `frontend/eslint.config.js:232-246` の除外塊は `features/secretary` に当たらず、カードの置き場所（最後の `...storybook.configs[...]` の前）は後ろの塊が勝つ決まりに合う。日本語の直書きは実物で 0 件（§1 の R4）。
- **実機で確かめる分**: N5 のとおり。カードの「本番の確かめ」に書かれている。

### 4-4 カードに直す点

- **C1**: 変更 5 と変更 4 の注釈の ADR 番号を、N1 の付け替え後の番号にする（`FEATURE-INDEX.md:78` の行が別の ADR を指さないように）。
- **C2**: §2 の a〜c の行番号を直す。
- **C3**: N4 の 1 行を変更 2-5 に足す。

## 5. kgi.md L11 の数え方の足しが合格の線を変えていないか

**変えていない**。`5a1281eb4` の kgi.md の差は L11 の 1 行だけ（`git log -1 -p` で確認）。足された文言は「確かめずに作る」の定義に「**読み上げの後に下書きが変わった後**」を加えたもの（kgi.md `:38`）。合格の線は前と同じ: 下書きが出る 9/10 以上・予定が声の「はい」で作られる 4/5 以上・確かめずに作る 0・否定と部分一致で作る 0/40（3 語と「はい、続けて」を各 10 回）・請求書が声で作られる 0/5。測る回数も増えていない。

軽い注意: 「読み上げの後に下書きが変わった」状態を起こす回は、kgi.md の測り方にも design.md の便 T0 の測り（否定語と違う日時を各 5 回）にも無い。この項目の「0」は、本番の人の測りでは自然に起きた回だけを数えるので、実際の守りは画面の試験（design.md §11 `:301` の「読み上げの後に欄を直すと「はい」で作らない」）が担う。数え方の足しは害にならず、合格の線も変えていないので、直す必要は無い。

## 6. 問題なしと確認した点

- 骨格（Gemini は聞く・話すだけ／作るのは画面／請求書はボタンだけ／台帳の CHECK と列／錠・仮の行）は変えなくてよい。
- R1〜R7 に対する直しは、3 回目の直し方と同じ中身で入り、新しい矛盾を生んでいない（N2 の「相手」を除く）。
- 3 回目が引いた実物の行は、`origin/main` の今も同じ（差が空）。
- 製品のコード・DB・本番・secrets には触っていない。本番の読み取りも行っていない。

## 7. 未確認

- `docs/STANDARD-WORKFLOW.md`・`docs/ai-agents/executor-checklist.md` は今回開いていない。
- `backend/tests/ops/test_ai_ro_views.py` に分類の漏れの試験があるかは全文を読んでいない（試験名 10 件の一覧だけ）。
- 実ブラウザの聞き直し・Gemini の書き起こし・Google の札の期限・料金は外の事実で、今回は確かめていない（design.md の【未】のまま）。
- `eslint`・`vitest` は作業場所に `node_modules` が無く流していない。日本語の直書き 0 件は、注釈を除いた文字の数えで確かめた（ESLint の実行ではない）。
