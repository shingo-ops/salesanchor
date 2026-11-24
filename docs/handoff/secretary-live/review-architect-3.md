# 秘書 LIVE 設計の審査 3 回目（architect）

この文書は何か: `origin/release/secretary-live-design` の設計（直した 3 版）と ADR-1085 草案を、実装に渡してよいか読んで確かめた 3 回目の審査の結果です。製品のコード・DB・本番・secrets は触っていません（読むだけ）。
親（あるべき姿）: [docs/specs/secretary-chat/README.md](../../specs/secretary-chat/README.md)／1 回目: [review-architect.md](review-architect.md)／2 回目: [review-architect-2.md](review-architect-2.md)

- 審査日: 2026-11-23（クラウドの審査役）
- 審査した物: `docs/handoff/secretary-live/{kgi,design,recon,research,research-2,review-architect,review-architect-2}.md`・`docs/adr/ADR-1085-secretary-live-voice.md`（`git show origin/release/secretary-live-design:<path>`）
- 実物の基準: `origin/main` の `bef5a7a8b`（作業場所 `release/secretary-live-design-review3` の起点）。2 回目の基準 `2b4e2c205` との間に、審査した設計が引く backend・画面・nginx・docker-compose・eslint 設定の差は無かった（`git diff --stat` が空）。以下の `パス:行` はこの実物の行。
- 照らした物: `AGENTS.md`・`docs/ai-agents/design-partner.md`（設計の完了の定義）、ADR-1058（`:24`）・ADR-1004（`:24-28`）・ADR-1080（`:12-22`）・ADR-1003（`:28-42`）の本文。ADR-1056・1082・027・067・144・135・136 は本文を読み直していない（2 回目と同じく要点・AGENTS.md 経由。ADR-144 は `:130-136` の追記だけ読んだ）。`docs/STANDARD-WORKFLOW.md` は今回開いていない（未確認）。
- 外部文書: 今回の指示で「つなぎ先の道具は使わない」ため Context7 は使っていない。Gemini Live・ephemeral token・Web Speech・料金など外の事実は**すべて未確認**（設計の【公】【三】【未】の印は検証していない）。
- 本番: 触っていない。`$40.55` 等の本番の値も確かめていない（未確認）。

## 判定: **REVISE（直す必要）** — ただし小さな直しだけで APPROVE に届く

1. 1 回目・2 回目の指摘 10 件は、設計の文面ではすべて直っている（§0）。骨格（Gemini は聞く・話すだけ／作るのは画面／請求書はボタンだけ／台帳の CHECK と列を作り直す／錠・仮の行）は筋が通り、作り直しは要らない。
2. **新しく見つかった穴が 2 つ**。(a) 予定の声の「はい」が、読み上げた下書きの中身に結びついていない（読み上げの後に欄を直す・別の下書きが出る・読み上げに無い項目が送られる、のどれでも「はい」で作られる）。(b) 台帳に足す列（`INTEGER[]`）が、本番の読み取りビューの分類表に無いと CI の分類の漏れの試験が落ち、L5・L6 を読み取り鍵で数える手順（design.md §11・§13）も通らない。
3. 軽い直しが 4 つ（migration の作り方の細部・読む口が書き込む案・既存の費用集計への混ざり方・file:line の合わない行 4 件）。いずれも文面と便 T0 の PR の作業に足せば済み、PO に新しく聞くことは無い（§3）。

## 0. 1 回目・2 回目の指摘 10 件（review-architect-2.md §2）が design.md §0・§0-2 のとおり直っているか

| # | 2 回目の指摘 | 直した場所（design.md）| 実物で確かめた結果 |
|---|---|---|---|
| 1 | 読み上げの中身の出どころの矛盾 | §5 `:122`・§5-1 `:136`・ADR-1085 `:32` | **直った**。読み上げの文は画面が下書きの state から作り、請求書の中身は Gemini に渡さない、で矛盾は消えた。ただし結びつきの穴が新しく残る（§1-(2) の R1）|
| 2 | 請求書は声で作るか | §5-1 `:132-134`・kgi.md L11 | **直った**（PO 2026-11-23「1」・請求書はボタンだけ）。`submit` を外へ出すのは予定だけ（`:139`）|
| 3 | KGI の L2・L3・L5・L6・L11 | kgi.md `:29-38` | **直った**（§1-(1)）|
| 4 | 台帳の CHECK・列 | §6-3 `:187-194`・ADR-1085 `:34` | **骨格は直った**。足りない細部が 3 つ（§1-(3) の R3〜R5）|
| 5 | 上限の穴 | §5-2 `:150`・§6-1 `:169-173`・§6-2 `:178` | **直った**（使わなかった札＝2 分で 0 円・錠・合計を読めなければ出さない・数える先は Redis で逆向きに止める）。細部は §1-(4) |
| 6 | `Callout`・LIVE 専用の旗・戻る時刻・鍵が無いとき | §6-6 `:207-219`・§6-2 `:180`・§15 | **直った**。`frontend/src/components/Callout.tsx:1` の実在を確認 |
| 7 | 札の期限で切れるか・別人の札の試験 | §5-2 `:153`・§10 `:256`・§11 `:276` | **直った**（便 T0 で 11 分つなぐ・画面も 10 分で自分で終える）|
| 8 | 日本語の直書き・守り手の行・親のリンク・記録先・色の検査 | §9 `:249-250`・§11・§16 `:333`・親の README（変更は `docs/specs/secretary-chat/README.md` +1 行）| **直った**（§1-(6)）|
| 9 | file:line の a・b・d・f | §3 `:69`・`:72`・冒頭 | a（`:76`・`:114`・`:252-258`）・b（`:225-241`）・d（`oauth` の文は §12-H で「認可を出す側の口は未確認」）・f（kgi の承認済み）は直った。**別の行が 4 件合わない**（§1 の「file:line の突合」）|
| 10 | 使えるのは super admin だけ | ADR-1085 `:24`・`:152`（design §5-2）| **直った** |

## 1. 見る点ごとの判定

### 先に: design.md が引いた file:line の突合（origin/main `bef5a7a8b`）

合わない行・文面: **4 件**。それ以外の引用（下の「一致」）は実物と合った。

| # | design.md の引用 | 実物 | 直し方 |
|---|---|---|---|
| a | §12-G `:293` の `backend/app/services/secretary_voice.py:17`（4 声の一覧）| 一覧 `SECRETARY_VOICES` は `backend/app/services/secretary_voice.py:18`（`:17` は空行）。2 回目の審査の「一致」の表も `:17` を通していた＝2 回目の見落とし | `:18` に直す |
| b | §10 `:260`「試験 `SecretaryChat.test.tsx:501-631`」| 「声で返事」の describe は `frontend/src/features/secretary/SecretaryChat.test.tsx:501` から `:630` の `});` まで。`:631` は空行で、`:633` から次の describe（聞き取りの印）| `:501-630` に直す |
| c | §9 `:249`「ADR-144 の生の部品の検査は `pages/**` だけを見て、`features/` は日本語の直書きと loading の書き方だけを見る（`ADR-144:134`・`check-ui-governance.js:16-18`・`:47-48`）」| `docs/adr/ADR-144-ui-component-governance.md:134` は checkbox 種別を足した追記で、「features/・components/ は検査しない」と書く（生の checkbox の話）。`scripts/check-ui-governance.js:16` は loading 種別だけが `pages/`・`features/`・`components/` を見ると書く。**日本語の直書きは `check-ui-governance.js` ではなく ESLint**（`frontend/eslint.config.js:31`）の仕事 | 「生の部品の検査（`:47`）は `pages/` だけ・loading の検査（`:16`）は `features/` も見る・日本語は ESLint `eslint.config.js:31`」と、検査ごとに分けて引く（結論の「生の部品は人の審査だけ」は実物と合う）|
| d | §6-2 `:181`「`check_budget`（`llm_budget.py:498`・`:441`）」| `check_budget` の定義は `:498`。`:441` は別の箇所の SQL（`FROM public.tenant_llm_budgets`）で関数の頭ではない | `:498` だけにするか、`:441` が何かを書く（実装には響かない）|

一致（確認した行）: `SecretaryChat.tsx:59`・`:66`・`:69`・`:255`／`useSecretaryListen.ts:117`／`secretaryApi.ts:10`／`SecretaryDraftInvoice.tsx:76`・`:114`・`:252`／`SecretaryDraftEvent.tsx:46`・`:53`／`backend/app/schemas/assistant.py:44`／`secretary-agent/server.mjs:15`（`MAX_BODY = 16 * 1024`）・`:131`／`backend/app/routers/assistant.py:89`（`AGENT_BODY_MAX_BYTES = 15_000`）・`:98-103`／`llm_budget.py:56`・`:159`・`:174`・`:180`・`:225`・`:498`／`backend/app/services/secretary_voice.py:22`／`backend/app/routers/super_admin_ai_jobs.py:184`／`backend/tests/test_super_admin_ai_jobs.py:29`・`:281`／`backend/tests/test_secretary_voice_pg.py:104`／`frontend/src/constants/icons.tsx:416`／`frontend/src/components/Callout.tsx:1`／`.github/workflows/e2e.yml:65`・`:87`／`frontend/package.json:15`・`:28`・`:48`・`:58`／`migrations/20261101_120000_enable_secretary_chat_tenant4.sql:10`／`migrations/20261103_120000_create_ai_job_assignments.sql:32`・`:128-129`・`:133`・`:143-144`／`docs/adr/ADR-1058-ai-job-assignments.md:24`／`backend/app/main.py:52`／`nginx/nginx.conf:96`（`connect-src 'self'`）・`:100`（`microphone=(self)`）／`docker-compose.yml:98`・`:246`／`backend/app/middleware/rate_limit.py:7`（Redis 不通は制限しない）・`:75-76`／`backend/app/routers/tcg_analysis_dashboard.py:939`・`:1050`／`.github/workflows/deploy.yml:570-575`（nginx 作り直しの 2〜3 秒）。

### (1) kgi.md L1〜L13（PO 承認済み）が本番で○×を一義に判定できるか

**問題なし**（13 本とも）。2 回目に指した 5 本は直っている。

| # | 判定 | 理由 |
|---|---|---|
| L2 | 問題なし | 「話し終える前に欄に最初の文字が出たら○」と一義（kgi.md `:29`）。端末の音声入力の設定を記録する欄もある |
| L3 | 問題なし | 「原稿の文の数と欄の文の数を比べ、文が 1 つでも欠けた回を×。字の聞き間違いは数えない」（`:30`）|
| L5 | 問題なし（軽い注意）| 時刻の取り方（画面が測る音量が値を下回った時刻→鳴らし始めた時刻）・「頼みごとをしない 20 文の台本」・PO 2026-11-24 の緩め方（設定が無ければ 3,000ms）が書かれた。**台本の 20 文そのものが repo に無い**。便 T0 の PR で `docs/handoff/secretary-live/` に台本を置くと書く（測り手が替わっても同じ文で測れる）|
| L6 | 問題なし | 時刻の取り方が決まり、イヤホンなしの PC を 1 回入れた（`:33`）|
| L7 | 問題なし | 「2 秒黙っても打ち切られない」9/10。L5 との衝突は PO の決め（`:13`）で解けている |
| L11 | 問題なし | 予定 4/5・請求書が声で作られる 0/5・否定と部分一致 0/40・「確かめずに作る」の定義（`:38`）。**ただし、この定義の「読み上げの前・窓の外・作る条件が揃う前」に、「読み上げの後に下書きが変わった」が入っていない**（§1-(2) の R1）。数え方に足すと L11 の○×が穴を測れる |
| L12・L13 | 問題なし | L12 は「新しい LIVE が始まらない」で一義。L13 の合格ラインは「持ち主・戻る時期・代わりに使えるものを言い当てる」（`:41`）|

### (2) §5-1 請求書はボタンだけ・予定は画面が作る読み上げ＋完全一致の「はい」の穴

**直す必要（R1・重い）**。請求書側は問題なし。予定側の「はい」に穴が 1 つ。

請求書: 「作る」ボタンだけ（`SecretaryDraftInvoice.tsx:114` の `canCreate`）で、声の道が部品の `submit` に届かない。声で「送料を請求しない」を入れる道も無い（`:252` の `Checkbox`）。**問題なし**（PO 決定済み）。

予定（R1）の事実:
- 下書きの欄は部品の中の `useState` で、利用者が読み上げの後でも直せる（`frontend/src/features/secretary/SecretaryDraftEvent.tsx:31-42`）。「作る」の条件 `canCreate` は題名・日付・時刻が空でないことと `!saving` だけ（`:46-51`）。
- 送る中身は題名・日時・全日・`calendar_type`（個人か共用）・説明・場所・`add_meet`（`:53-69`）。設計が読み上げる文は「相手・日時」（design.md `:136`）。**読み上げに無い項目（共用カレンダーか・場所・説明・Meet）も「はい」で一緒に作られる**。予定には「相手」の欄は無い（題名・場所・説明が代わり）ので、読み上げの文に何を入れるかの決めも要る。
- design.md の窓は「声が流れ終わってから次の発話 1 つ」（`:137`）だが、**窓が開いた後に欄が変わった場合・別の下書きが出た場合に、どの下書きの「はい」かを結ぶ決まりが無い**。結ぶ物が無いと、読み上げた内容と作られる内容が食い違う。
- 画面が作った文を Gemini が忠実に声にしたかを、画面は確かめていない。Gemini は言い換えるかもしれず（未確認）、利用者が耳で聞く文と画面の文が違うと、「確かめた」にならない。2 回目の「わざと違う日時を読み上げる」試験（`:141`）は人が気づくかを測るが、**読み上げの忠実さを機械で見る道**は無い。

直し方（文面に足す。作り直しは要らない）:
1. 読み上げの時に、画面が**読み上げた文と下書きの識別子**を 1 組持つ。窓が開いている間に、その下書きの欄が 1 つでも変わる・別の下書きが出る・窓の外の発話が来るのいずれかが起きたら窓を閉じる。「はい」に一致した瞬間に、**今の state から読み上げの文を作り直して持っている文と比べ、同じときだけ**部品の `submit` を呼ぶ。
2. 読み上げの文に、共用カレンダーか個人か・場所・Meet の有無を入れるか、入れない項目は「はい」で作る前に窓を閉じる（欄が空でない場合は読み上げに入れる、でもよい）。何を入れるかは設計担当が決めて §5-1 に書く。
3. 窓を開く条件に、Gemini の**読み上げの書き起こし**（design.md §5 は両方の発言を文字にすると書く）が画面の文と一致することを足す。書き起こしが取れるか・一致の見方（空白・句読点を除く完全一致か）は【未確認】のため、便 T0 で測る項目に足す。一致しなければ窓を開けず、画面の文は吹き出しに残るので「作る」ボタンで作れる（事故にならない側に倒れる）。
4. 「同じ下書きで『はい』が 2 回来ても 1 回しか作らない」は、`canCreate` の `!saving`（`:50`）で足りる。ただし声の口が `submit` を呼ぶのは `await` の前なので、**呼ぶ前に窓を閉じる**（二重を作らない）と書く。
5. 試験（§11 の AI が勝手に作らない行）に、「読み上げの後に欄を直すと『はい』で作らない」「下書きが 2 つあるとき最後に読み上げた 1 つだけが対象」「書き起こしが画面の文と違うと窓が開かない」を足す。

### (3) §6-3 台帳の migration（CHECK の作り直し・列）が今の行と今の集計を壊さないか

**骨格は問題なし。足りない細部が 3 つ（R3・R4・R5。R2 は (7) の便の作業にも関わる）**。

今の実物（読んだ）:
- `outcome` は列の定義の中の CHECK `llm_usage_events_outcome_check`（`migrations/20261103_120000_create_ai_job_assignments.sql:126-129`）、`error_code` は同 `:131-133`、組み合わせは `llm_usage_events_outcome_error_code_check`（`:135-146`）。purpose・sdk の CHECK は `:148` 以降で作り直しが既にあり、後の migration（`migrations/20261113_100000_create_secretary_rules.sql:113-119`・`migrations/20261117_100100_add_llm_usage_tts_characters.sql:7-37`）も同じ名前の CHECK を作り直している。
- design.md §6-3 の 5 項目（`pending`・組み合わせ・`not_started`・purpose と sdk・列）は、これらの名前で作り直せる。**今の行は壊れない**: 既存の行は `outcome='ok'`・`error_code` が空（`:122-124` の注）で、作り直した CHECK（`ok`・`pending` は `error_code` が空／`failed` は空でない）を満たす。表や列を消す文は無く、ADR-1003 の例外（`docs/adr/ADR-1003-go-delegation-to-opus.md:33-34` の DROP TABLE／DROP COLUMN を含む migration）に当たらない。委任の GO で足りるという読みは**妥当**（2 回目と同じ）。
- **今の集計は `pending` を数えない**: `tcg_analysis_dashboard.py:455-457`（`_LEDGER_OK_JOIN`・`outcome = 'ok'`）・`:698`（`_LLM_USAGE_WHERE`・`outcome = 'ok'`）・`backend/app/routers/super_admin_ai_jobs.py:45-59`（`ok`／`failed` を別々に数える）で確認した。design.md `:193` の「`pending` の行は今の画面の数を変えない」は実物と合う。

直す必要:
- **R3（細部・migration の作り方）** 新しい migration は次を守ると文面に書く。(a) 今の型の「無いときだけ作る」は `IF NOT EXISTS (... conname = ...)` で**名前だけ**を見る（組み合わせの CHECK は `:136-146`）。**この形を真似ると、古い定義が残ったまま素通りする**。新しい migration は `pg_get_constraintdef` を読み、`pending`（または `secretary_live`・`google-genai-live`・`not_started`）を含まないときだけ `DROP CONSTRAINT IF EXISTS` → `ADD CONSTRAINT` にする（`20261117_100100_add_llm_usage_tts_characters.sql:7-37` の `NOT LIKE` の形が前例）。(b) 作り直す値の一覧は**今の本番の CHECK の全値**（`secretary_regression`・`secretary_tts` を含む。`llm_budget.py:159-171` の `USAGE_PURPOSES` と一致）に新しい値を足したもの。後から足された値を消さない。一致は `backend/tests/test_secretary_voice_pg.py:104` が見る。(c) `scripts/run_all_migrations.sh` に `run_sql` の行を足す（既存の登録は `:1399`・`:1478`。登録の検査は `scripts/check-migration-registration-exists.sh`）。design.md は登録を書いていない。
- **R2（重い・分類表）** 台帳を本番の読み取り鍵で読む道（design.md §11 の速さ・§13 の「`ai_ro.public__llm_usage_events` の `secretary_live` の行を数える」）には、**列ごとの分類が要る**。分類表 `ai_cloud_meta.column_class` の正本は `migrations/20261024_100300_create_ai_cloud_views.sql` の `TRUNCATE` と `INSERT`（`:1-16`）。`llm_usage_events` の `outcome`・`error_code`・`purpose`・`sdk` は「値の決まりで限られる」として `allow` の行がある（同 `:155-159`）。**列の型が整数・数値・日時・真偽・uuid・enum でない列は、分類の行が無いと CI の分類の漏れの試験が落ちる**（`backend/tests/ops/test_ai_cloud_views.py:52-55` の `_PASS_TYPES`・`:494-519` の `_classification_gaps`）。設計の `live_reply_latency_ms INTEGER[]`・`live_barge_in_latency_ms INTEGER[]` は配列で、`_PASS_TYPES`（`int2`・`int4`・`int8`・`numeric` 等）に当たらない。しかも分類表の行数を試験が 1165 に固定している（`:486`）。直し方: 便 T0 の PR に、(i) 新しい 4 列（音声のトークン 2 列・速さの 2 列）の `allow`（理由つき）の行を `20261024_100300_create_ai_cloud_views.sql` に足す、(ii) 試験の行数 `:486` を更新する、(iii) 値の決まりが変わる `outcome`・`error_code`・`purpose`・`sdk` の `allow` の理由文は変えなくてよい（値の追加だけ）、と書く。別案: 速さを配列でなく**回ごとの数値の列 2 本（中央値でなく 1 回の代表値）**にするか、別の小さな表にする。どちらを選ぶかは設計担当が決める。`ai_ro` 側の分類（`backend/tests/ops/test_ai_ro_views.py`）にも同じ要件があるかは**未確認**（本審査では開いていない）。
- **R5（既存の費用集計への混ざり方）** `tcg_analysis_dashboard.py:698` の `_LLM_USAGE_WHERE` は `outcome = 'ok'` だけで、**使いみちで絞る条件は見当たらない**（`:725`・`:795-919` の合計は `purpose` で絞らない形に見える。全部は読んでいない＝未確認）。便 T1 から「15 分たっても終わりが来ない行」を最大の費用で `ok` にする（design.md `:173`）ので、LIVE の費用は**既存の AI の費用の表の合計に入る**。入れてよいかは設計に書かれていない。直し方: §6-4 に「既存の AI の費用の表に LIVE を含める（または purpose で除く）」を決めて書き、`LLM_PRICING`（`llm_budget.py:56`）に Live のモデル名が無いと費用が空（NULL）になる点（`calculate_usage_cost` は表に無いモデルを `None`・`:228-233`）を、便 T1 の試験に入れる。

### (4) §6-1・6-2 仮の行・錠・読めない時の扱い

**問題なし（骨格）／直す必要（軽・R6）**。

- 2 回目に指した 4 つの穴（使わなかった札・同時に取る競争・合計を読めない・回数の数え先）は、すべて文面で塞がれている（design.md §5-2 `:150`・§6-1 `:169-173`・§6-2 `:178`）。Redis が止まると今の回数の上限は通す（`backend/app/middleware/rate_limit.py:7`・`:75-76`）ので、LIVE は逆に札を出さない、と決めたのは実物と合う（`_check_rate_limit` の戻りを使い回さず、別に書く必要がある。便 T1 の試験の「Redis が読めなければ出さない」で守られる）。
- **R6（軽）** design.md `:171`「書き直しが来ない行の扱い（次に札を出すときと、**費用の画面を読むときに**、同じ処理で直す）」は、**読む口（スーパー管理の画面）が台帳を書き換える**案。読むだけの口が書くと、(a) 読み取りの口に書き込みの権限・取引が要る、(b) 画面を開くたびに競争の元になる、(c) 「画面を見たら数が変わった」の原因になる。直し方: 読む口では「15 分たったら最大の費用で数える」を**計算して見せるだけ**（行は書き換えない）にし、行の書き直しは札を出す口と使用量の口の中だけで行う（錠の中・`outcome = 'pending'` の条件つきの UPDATE の 1 回）。上限の合計も同じ計算を使う。
- 画面が送る使用量は申告で、別人の札の行を書き換えない試験が §11 `:276` にある。LIVE を使えるのは super admin だけ（`assistant.py:98-103`）という前提は ADR-1085 `:24` に書かれた。**問題なし**。

### (5) CSP と鍵を画面に出さない札の穴

**問題なし**（2 回目の指摘は直った。外の事実は便 T0 で確かめる前提）。

- CSP: 本番は `connect-src 'self'`・`script-src 'self'`（`nginx/nginx.conf:96`）。`connect-src` に `wss://generativelanguage.googleapis.com` を足す案は筋が通る。AudioWorklet は `frontend/public/` の普通のファイルにして `script-src` を緩めない案も合う（`frontend/public/` は実在。`default-src 'self'` のため `worker-src` は `script-src 'self'` に倣う）。足りるかは便 T0 の実機で確定する、は妥当。nginx の配備で 2〜3 秒の 502 の窓（`deploy.yml:566-575`）の注意も合う。
- 札: `uses=1`・つなぎ始め 1 分・期限 10 分・モデル・指示文・道具を backend が固定・口は super admin だけ・鍵の環境変数は LIVE 専用で空なら 503。`GEMINI_API_KEY` が backend と celery-worker の両方に渡る（`docker-compose.yml:98`・`:246`）のに対し、LIVE 専用の鍵は backend だけに渡す、と書かれた。**札・鍵が backend のログ・エラー文・画面のログに出ない試験**も §11 `:278` にある。
- **注意（軽・新しい事実）**: `frontend/public/sw.js` がある。AudioWorklet のファイルを `public/` に置くと、service worker のキャッシュの対象になる可能性がある（`sw.js` の中身は読んでいない＝未確認）。便 T0 の実機で、worklet の更新が古いまま残らないか（配備後に別の版を読まないか）を測りに足すとよい。実装可否には響かない。
- Google の側の事実（札の期限で切れるか・`auth_tokens.create` が `google-genai>=1.0.0` で使えるか・Google の請求先の月の上限の返事）は**未確認**だが、いずれも便 T0 で測る項目に入っている（`design.md:153`・`:155`・`:211`）。

### (6) §11・§16 続けるための機械の仕組み（機械で止まる／人の審査だけ／手作業）

**直す必要（軽）**。区分は design.md の書き方が実物と合う。足りない所が 3 つ。

| 守るもの | 区分 | 実物の確認 | 足りない所・足し方 |
|---|---|---|---|
| 翻訳の鍵の食い違い | **機械で止まる** | `frontend/package.json:28`（`check:i18n-missing-keys`）が `:48` の `check:all` に入り、CI の `lint-run`（`.github/workflows/e2e.yml:65`・`:87`）が走る | なし。必須チェックに入っているかは Ruleset が読めないため未確認（2 回目と同じ）|
| 日本語の直書き | **今は warn だけ → 便 A で機械に格上げ**（design.md §9・§11・§16）| `frontend/eslint.config.js:31` が `warn`。`frontend/package.json:15` の `lint` は `eslint src` で警告では落ちない。手元の commit だけ `:58` の `--max-warnings=0` で止まる | **「便 A の PR に入れる」では、便 T0 の LIVE の部品（`SecretaryLive.tsx` 等）が先に出る間は warn のまま**（design.md `:250` は「先に出る便のため」と書くが、便の順序は T0 → T1 → B → C で、A は T0 と別に先でも後でもよい＝`:262`）。直し方: override を**便 T0 の PR に入れる**（LIVE の部品を足す最初の便）。さらに、**今の `features/secretary/` の既存ファイルが 0 件か**を便の前に確かめる（日本語を含むファイルが 10 件ある。コメントだけか文字列かは本審査では見ていない＝未確認。試験は `String.fromCharCode` で日本語の直書きを避けている＝`SecretaryChat.test.tsx` 冒頭付近の `JP_TEXT`）。0 件でなければ、override が入った瞬間に `lint-run` が落ちる。override の置き場所は `:31` より後・`:236-250` の例外（stories・design-system）より前か後かで効き方が変わる（設定は後ろの物が勝つ）ので、PR で `eslint src/features/secretary` を実際に流して確かめる |
| 金型外の見た目 | 色・寸法は**機械**（ADR-067 の検査・`frontend/package.json:48` の `check:all`）／生の部品は**人の審査だけ**（`check-ui-governance.js:47` が `pages/` だけ）| §9 の書き方（`:249`）は実物と合う（上の c の引用の直しは別）| 審査役の点検の文面に「生の部品（`<select>`・`<input>` 等）が無いこと」を足す、は書かれた。**足りない所: 点検の置き場**。`docs/ai-agents/executor-checklist.md` の画面の行に 1 行足す（足すかは設計担当が決める。未確認＝このファイルは今回開いていない）|
| 台帳の値の取り違え | **機械**（DB 付き試験）| `backend/tests/test_secretary_voice_pg.py:104` が purpose の一致を見る。sdk の一致を見る行があるかは `:104` の近く（全文は読んでいない＝未確認）| 足す値は `USAGE_PURPOSES`・`USAGE_SDKS`・`USAGE_SDKS_BY_PROVIDER`（`llm_budget.py:159`・`:174`・`:180`）と CHECK の両方。`backend/tests/test_super_admin_ai_jobs.py:281` の期待の集合に `gemini_live` を足す（設計に書かれた）|
| 読み取りビューの分類 | **機械**（CI の分類の漏れの試験）| §1-(3) の R2 | **設計に無い**。便 T0 の PR に入れる（上の R2）|
| 月の上限・仮の行・札・鍵 | **まだ無い（便 T1 で新しく作る）** | `backend/tests/test_secretary_live.py` は今は無い | **T0 で札の口と仮の行を本番に出すのに、その試験の置き場は T1**（design.md §16 `:337`）。T0 の「鍵と札が漏れない」「札の口の守り」「回数の上限で 429」「鍵が空なら 503」の試験は T0 の PR に入れる。T1 に回すのは「月の上限・錠・合計を読めない」だけにする |
| AI が勝手に作らない | **まだ無い（便 T0 で新しく作る）** | `SecretaryLive.test.tsx` は今は無い | R1 の試験（§1-(2)）を足す。Gemini を偽物に差し替える |
| 費用の照らし合わせ | **手作業・関所なし** | §11 `:281`・§16 `:343` に正直に書かれた | 足りないのは「忘れたとき」。design.md は「便 T1 の後に PO に聞く」と書く。**今の設計で足りる**（手作業と明記した）。実装の便に入れず、運用の決めとして残してよい |
| 維持の仕組み欄 | **機械（警告モード）** | `scripts/check-process-artifacts.js` の関所は「守り手:」の行を探す。design.md §16 `:333` に行がある（`.github/workflows/e2e.yml`）| 問題なし。表の中の未来のファイル（`test_secretary_live.py`・`SecretaryLive.test.tsx`）は便ごとに足した時に並べる、と書かれた |

足りない所の要約: (a) 日本語の直書きの override は**便 T0 の PR**（LIVE の部品を足す最初の便）に入れ、今の 0 件を確かめる、(b) 読み取りビューの分類の行（R2）、(c) T0 で出す札の口の試験は T0 の PR、(d) 台本の 20 文を repo に置く。

### (7) 便 T0〜C の分け方と migration の GO

**問題なし（分け方）／直す必要（軽）**。

- 分け方（T0 → T1 → B → C・A は独立）は筋が通る（2 回目と同じ判断）。T0 は費用が出る本番の試作で、PO の了承と旗（PO の会社だけ）で抑える、と書かれた（`design.md:263`）。
- **便 T0 の migration は 2 本**: 旗の行と台帳（`design.md:56`・`:256`）。旗の行は `tenant_features` への INSERT で、前例は `migrations/20261101_120000_enable_secretary_chat_tenant4.sql:10`。`scripts/migration-guard/protected-tables.txt` に `tenant_features` は無く、保護の対象外（grep で 0 件）。**問題なし**。
- **GO**: 台帳の migration は CHECK の作り直し（`DROP CONSTRAINT IF EXISTS`）と列の追加だけで、ADR-1003 の例外（DROP TABLE／DROP COLUMN）に当たらない。PR 本文に「構造を消す文ではない」と書く（design.md `:264`）。AGENTS.md の「`migrations/` を含む PR は GO まで main に入れない」は T0 に当てはまる。**問題なし**。
- 直す所（軽）: (a) 便 T0 の PR に、R2（分類表の行）・R3（登録の行）を入れる。(b) 便 T0 の中身の欄に「日本語の直書きの override」を足す（§1-(6)）。(c) 便 C が「声で返事」を消す前の条件（L4・L5 の合格・`design.md:265`）は書かれた。**問題なし**。

### (8) 未確認の点が実装可否を左右するか

| 未確認の点 | 左右するか | 判定 |
|---|---|---|
| Gemini 2.5 Native Audio の遅さ・文の意味で話し終わりを見る設定・割り込み | **左右する**（L5・L7・L6。② への切り替えは作り直し）| 問題なし（便 T0 で測る・PO の決め 2026-11-24 がある）|
| `auth_tokens.create` が使える版か・札の期限で切れるか・使用量の届き方・つなぎ始めの期限の挙動 | **左右する**（札の口が作れるか・L12 の「最長 10 分」）| 問題なし（便 T0 の最初の項目に入っている）|
| Google の鍵が有料枠か | **左右する**（ADR-1056 の改めの根拠）| **PO が決めること A**（設計に既にある。新しい決めではない）|
| 読み上げの書き起こしが取れるか・画面の文との一致の見方（R1 の 3）| 窓を開く条件に使う場合は**左右する**（取れなければ 1・2 の直しだけで足りる）| **直す必要（便 T0 の測りに足す）**|
| 読み取りビューの `ai_ro` 側の分類（R2）| 便 T0 の PR の CI が通るかを左右する | 直す必要（開いて確かめる。実装可否は左右しない）|
| service worker が worklet をキャッシュするか | 実装可否は左右しない | 問題なし（便 T0 の実機の測りに足す）|
| 請求書・予定の取り消しの道 | 実装可否は左右しない | 問題なし（予定の声の「はい」は R1 の直しで守る）|

## 2. 「直す必要」の一覧（設計担当が直すもの）

| # | 重さ | 直す場所 | 直す中身 |
|---|---|---|---|
| R1 | 重い | design.md §5-1・kgi.md L11・§11・ADR-1085 `:17` | 予定の声の「はい」を、読み上げた文と下書きの識別子に結ぶ（欄が変わる・別の下書きが出る・窓の外で窓を閉じる）。読み上げに入れる項目（共用・場所・Meet）を決める。読み上げの書き起こしが画面の文と一致するときだけ窓を開く（取れるかは便 T0 で測る）。L11 の「確かめずに作る」の定義に「読み上げの後に下書きが変わった」を足す |
| R2 | 重い | design.md §6-3・§10 の便 T0・§13 | 新しい列の分類（`migrations/20261024_100300_create_ai_cloud_views.sql` の分類表の行・`backend/tests/ops/test_ai_cloud_views.py:486` の行数）を便 T0 の PR に入れる。`INTEGER[]` の型は `_PASS_TYPES` に無いので行が要る（または数値の列に変える）。`ai_ro` 側も確かめる |
| R3 | 軽い | design.md §6-3 | migration の作り方: 定義を読んで古いときだけ作り直す（名前だけを見る形を真似ない）・値の一覧は今の本番の全値＋新値・`scripts/run_all_migrations.sh` に登録 |
| R4 | 軽い | design.md §9・§11・§16・§10 | 日本語の直書きの override は便 T0 の PR に入れる。今の `features/secretary/` が 0 件かを先に確かめる。T0 で出す札の口の試験を T0 の PR に入れる。台本の 20 文を repo に置く |
| R5 | 軽い | design.md §6-4 | 既存の AI の費用の表（`tcg_analysis_dashboard.py:698`・purpose で絞らない）に LIVE を含めるか除くかを決める。Live のモデルの単価が表に無いと費用が空になる試験を足す |
| R6 | 軽い | design.md §6-1 | 読む口は計算して見せるだけにし、書き直しは札の口・使用量の口の中だけにする |
| R7 | 軽い | design.md §3・§6-2・§9・§10 | file:line の 4 件（`secretary_voice.py:18`・`SecretaryChat.test.tsx:501-630`・ADR-144 と検査の引き分け・`llm_budget.py:441`）|

## 3. PO が決めること

**新しく PO に聞くことは無い**。R1〜R7 は設計担当が決めて書き直せる。既存の決めること（design.md §12 の A〜K）は、PO 決定済みの H・I・K を除き、便 T0 の前に PO の了承が要る A（有料の声の AI）・B（ADR-1056 の改め）・C（月の上限の額。便 T0 の実測の後）・J（LIVE 専用の鍵）のまま。R1 の 2（読み上げに入れる項目）は PO の業務の判断（共用カレンダーの予定を声だけで作ってよいか）を含むので、**設計担当が案を書き、PO に 1 行で確認する**のがよい。

## 4. 問題なしと確認した点

- 2 回目の指摘 10 件は文面で直っている（§0）。骨格は変えなくてよい。
- 台帳の migration は、今の行・今の集計（`outcome = 'ok'` だけを数える `tcg_analysis_dashboard.py:455-457`・`:698`、`super_admin_ai_jobs.py:45-59`）を壊さない。ADR-1003 の例外に当たらず、委任の GO で足りる（`docs/adr/ADR-1003-go-delegation-to-opus.md:33-34`）。
- `tenant_features` への旗の行の INSERT は前例どおりで、`scripts/migration-guard/protected-tables.txt` の対象外。
- 請求書は画面のボタンだけ（`SecretaryDraftInvoice.tsx:114`・`:252`）。声の道が `submit` に届かない。
- CSP・マイク・nginx の配備の注意・札の固定・鍵が backend だけ・super admin だけの条件は、実物の行と合う。
- 製品のコード・DB・本番・secrets には触っていない。本番の読み取りも行っていない。
