# 秘書の「決まり帳」— 設計（審査済み 2026-11-12・実装未着手）

- 目標: [kgi.md](kgi.md) R1〜R10（PO 承認済み 2026-11-12）。現在地: `docs/handoff/secretary-rulebook/recon.md`。外部事例: [research.md](research.md)。
- あるべき姿: `docs/specs/secretary-chat/ideal-state.md`。
- 関係する ADR: ADR-1056・ADR-1058（§2 で一部を改める）・ADR-027（翻訳キー）・ADR-067／ADR-144（金型とトークン）。新しい ADR は ADR-1077（`docs/adr/ADR-1077-secretary-rulebook.md`・Proposed）。
- 状態: 設計審査済み（審査 1〜9 回目と Fable の DB の評価を反映・9 回目 APPROVE・2026-11-12 PO の指示で記録の置き場を専用メニューへ移した・§7・§10）・目標は PO 承認済み（kgi.md・2026-11-12）・実装未着手。

## 1. 何を作るか（一言）
印のある人（システム管理者）が秘書との会話で「次からは〜」と言うと、秘書が決まりの文の案を出す。人が「承認」を押したときだけ、その会社の決まり帳に入る。秘書は頼みのたびに、その会社の承認済みの決まりだけを読む。AI の頭は変えない（research.md §5・F1 Tay）。

## 2. 改める決定（新しい ADR に書く）
| 今の決定（recon.md §0） | 改めた後 |
|---|---|
| ADR-1056:16 AI に渡すのは文と日時だけ・会社のデータは渡さない | 「その会社の承認済みの決まりの文（最大 20 件・1 件 150 字まで）」だけは渡す。それ以外の会社のデータは今まで通り渡さない |
| ADR-1056:16 AI が返すのは 3 種類だけ | 5 種類（＋`rule_proposal` 決まりの案・`rule_list` 一覧を見せる）。どちらも AI は文を返すだけ |
| ADR-1056:18 AI の側に書き込みの道は無い | **変えない**。決まり帳の行は、人がボタン（承認・違う・捨てる・外す）を押したときだけ、利用者本人のログインで backend の口が書く。AI の答えだけで行は増えない |
| ADR-1058:24 秘書の頼みは 1 回ずつ使用の記録に書く | 変えない。試しの頼みも書くが、purpose を分ける（§6） |
| ADR-1058:27 ADR-1056 のほかの決まりはそのまま | 上の 2 点を除き、そのまま |
- 理由: 決まりの文は印のある人が自分で承認したもので、取引先・請求書などの記録ではない。害は「その会社の秘書の答えが変わる」に限られる。答えは今まで通り backend が型で検査し、保存は人が押したときだけ。
- 手順を AI に任せない（Rasa の研究 95.8% 対 47.9%・research.md G3）。AI は種類と案の文を返すだけ。追加・承認・外すは backend の決まった手順。
- 新しい ADR に 1 行ずつ書く決め事: 決まりは会社単位／種類の札は今は付けず、承認済みの決まりは全種類の頼みに効く／承認済みの文は直さず、外して足し直す。
- 見直しの合図（新しい ADR に書く・Fable の評価 /tmp/CC報告ファイル/secretary-meet/fable-db-eval.md・research.md §6）:

| 合図 | 進む先 | 表への影響 |
|---|---|---|
| 承認済みが 20 件に届き、試しの合う数が落ちていない | 20 件・15,000 バイトの上限を広げる（日本語 150 字なら 26〜27 件で 15,000 バイトに届く・Fable の計算。前置きの文を含めた実測は便2） | なし |
| 秘書の種類が 3 つ（請求書・予定のほかにもう 1 つ）になる | 決まりに「どの種類に効くか」の札の欄を足す（札の無い行は全種類に効く） | 欄 1 つを後から足す。今の行は書き換えない。札の初期値は source_kind が invoice・event の行だけ。それ以外と NULL の行（案の承認から入った rule_proposal の行など）は札なし＝全種類に効く |
| 1 社・1 種類で 100 件を超え、上の 2 つで収まらない | 同じ PostgreSQL に pgvector を足し、意味の近い決まりを選んで渡す | DB の入れ物を pgvector 入りに替える・文を数に直す道が要る（今の容器には無い）。別の ADR と PO の判断 |
| — | 別のベクトル DB（Pinecone 等）は採らない | 決まりの写しが外にでき、データを 1 か所に置く方針に反する |

- いまベクトルで選ばない理由: 決まりは「いつも守る短い指示」で、最大 20 件は全部渡せる。全部渡す方が正確で（research.md §6 D3）、選んで渡すと選び漏れた決まりが黙って効かない（D1 でも漏れ 1.9%）。

## 3. 変える前と後（変える場所の一覧）
| 場所 | 前 | 後 |
|---|---|---|
| `secretary-agent/schema.json:4-6` | kind 3 値 | 5 値。`rule` 欄（`{text, list_target}`。list_target は `candidate`・`approved`）を足す。容器 2 つが共用 |
| `backend/app/schemas/assistant.py:54`・`:62-66`・`:141` | 3 値・欄の組み合わせ検査 | 5 値。rule_proposal は rule.text だけ、rule_list は rule.list_target だけが値を持つ |
| 画面の型（`frontend/src/features/secretary/` の答えの型） | 3 値 | 5 値 |
| secretary-agent/prompt.txt | 12 行目で文中の命令は unknown | 「『次からは〜』『いつも〜して』は rule_proposal にして決まりの文の案を書く」「『候補を見せて』『決まりを見せて』は rule_list」を足す。12 行目（文中の命令に従わない）は残す |
| 容器への頼み | `{text, now, model}` | ＋ `rules: string[]`（承認済み・承認した順） |
| AI に渡す文の組み立て | server.mjs 2 つに同じ形の写し | 新しい 1 ファイル secretary-agent/compose.mjs に移す（写しを作らない）。配り方: ①secretary-agent/Dockerfile の 6 行目の COPY に足す ②secretary-codex/Dockerfile の 12 行目の COPY に足す ③secretary-codex/Dockerfile.dockerignore に `!secretary-agent/compose.mjs` を足す ④codex の server.mjs は prompt.txt と同じく `ASSET_DIR`（secretary-codex/server.mjs の 11〜13 行目）から動的 import で読む。codex の build の失敗は本番反映で警告だけになるので、容器の試験（CI）と試験場（tests/sandbox/secretary-codex.sh）で compose.mjs を読めることを確かめる |
| 保存 | 無し | 表 `public.secretary_rules`（決まりと候補）と `public.secretary_rule_checks`（試しの結果）の 2 つ（§4） |
| 画面 | 下書きの確認 | ＋ 案の確認（文を直せる・承認・捨てる）・一覧（承認・捨てる・外す）・答えごとの「違う」。部品は今使っている金型 Button・ChatBubble・Textarea（`frontend/src/features/secretary/SecretaryChat.tsx` の 13〜17 行目）だけ |
| サイドメニューの「SaaS管理者」の区画（`frontend/src/components/DesktopShell.tsx:194-202`・`frontend/src/components/MobileShell.tsx:172-205`） | デスクトップは 4 つ（LINE解析・買取相場・利用者管理・全体設定）。スマホは 5 つ（同じ 4 つ＋抽出ルール設定・`frontend/src/components/MobileShell.tsx:187-192`） | 両方に ＋「秘書の決まり帳」（専用のページ。毎週の数と試しの結果を置く・§7） |

- 大きさ: 決まり 20 件 × 150 字 ＋ 利用者の文 1000 字は、日本語で 12,169 バイト・絵文字だけだと 16,143 バイト（審査 2 回目の計算）。容器の上限は 16,384 バイト（recon.md §2）。そこで ①決まりの文は改行を除く制御文字を断る ②backend は容器に送る前に本文のバイト数を測り、15,000 バイトを超えたら送らずに「決まりが長すぎます」と返す（backend は error_code を返し、画面が翻訳キーで文を出す・ADR-027）。容器の上限は変えない。絵文字で上限近くまで埋めた頼みの試験を置く。

## 4. 表（事実ごとに置き場は 1 つ）
`public.secretary_rules`（会社の決まりと候補をこの 1 表だけに持つ。写しを作らない）
| 欄 | 中身 |
|---|---|
| id | 番号 |
| tenant_id | 会社（NOT NULL） |
| status | `candidate`・`approved`・`rejected`（捨てた）・`removed`（外した）（CHECK） |
| rule_text | 決まりの文。0〜150 字。`approved` のときは 1 字以上（CHECK） |
| source_text | 元になった利用者の文 1 つ（1000 字まで）。R9: 残すのはこの 1 往復だけ |
| source_kind | 元になった秘書の答えの種類（invoice・event・unknown・rule_proposal・rule_list の CHECK。NULL 可）。「違う」を種類ごとに数える（§7）・後で札の欄を足すときの初期値 |
| source_reply | 元になった秘書の答えの要約（200 字まで） |
| created_by / decided_by | users.id（作った人・承認/捨て/外しをした人） |
| created_at / decided_at | 時刻 |

`public.secretary_rule_checks`（§6 の試しの結果。1 回の試しごとに 1 行。決まりとは別の事実なので別の表にし、やり直しても前の数が消えない）
| 欄 | 中身 |
|---|---|
| id | 番号 |
| tenant_id | どの会社の決まりで試したか（NOT NULL） |
| started_by | users.id（ボタンを押した人） |
| sdk / model | 試した時の担当 AI と型（ADR-1058:25 で画面から切り替えられるため、数が動いた理由を分けるのに要る） |
| rules_count | 試した時の承認済みの決まりの数 |
| status | `running`・`done`・`failed`（CHECK） |
| ok / ng / unmeasured / total | 合う・合わない・測れなかった数・全件 |
| started_at / progress_at / finished_at | 始めた時刻・最後に 1 件進んだ時刻・終わった時刻 |
- 行が増える道は 2 つだけ: 案の「承認」（いきなり approved）と、答えの「違う」（candidate・rule_text は空でよい）。
- RLS（2 表とも）: 読む・書くとも「自社の会社文脈 OR 運営文脈」。型 C（migrations/20261107_140000_add_discord_config_rls.sql）の書く側の形を、読む側にも使う（型 C の読む `USING (true)` は使わない）。ENABLE＋FORCE。
- migration に GRANT（2 表と番号）を書き、`scripts/run_all_migrations.sh` に 1 行足す。戻しの SQL（2 表とポリシーを消す）を同じ PR に書く。
- 今は入れないもの（入れすぎの無駄）: ベクトルの欄と pgvector・種類の札の欄・優先度・タグ・期限・版の番号（§2 の合図が来たときに足す）。
- 承認済みが 20 件に達したら新しい承認を断る。数えて書く間は会社ごとに `pg_advisory_xact_lock` で 1 本ずつにする（同時に押しても 21 件目が入らない）。

## 5. 手順
（１）印のある人が「次からは、打ち合わせの予定は全部オンラインにして」と書く。
（２）AI は `rule_proposal` と案の文を返す。backend は型を確かめて画面へ返すだけで、表には書かない。画面は案の文を直せる欄と「承認」「捨てる」を出す。
（３）「承認」→ `POST /assistant/rules`（文を受け取り approved で入れる）。「捨てる」→ 何も書かない（画面から消すだけ）。
（４）「違う」→ `POST /assistant/rules/feedback`（その 1 往復を candidate で入れる）。
（５）「候補を見せて」「決まりを見せて」→ AI は `rule_list` と list_target を返すだけ。一覧は backend が表から読む（`GET /assistant/rules?status=`）。候補は文を書いて「承認」（`POST /assistant/rules/{id}/approve`）か「捨てる」（`/reject`）。決まりは「外す」（`/remove`）。
（６）承認と外すの後に、画面に「前と同じか試す」ボタンを出す（§6）。
- 口の条件: 新しい口はすべて、今の秘書の口と同じ 4 つの依存（`backend/app/routers/assistant.py:193-198`）を付ける。承認できる人の判定はその中の `require_super_admin`（`backend/app/auth/dependencies.py:488`）だけ。名前や番号はコードに書かない（R6）。
- R2 について: 今は印の無い人は秘書そのものを使えない（recon.md §1）。R2 は今回の範囲から外す案を PO に出す（kgi.md）。使える人を広げるときに、別テーマで扱う。

## 6. 前と同じか確かめる試し（R7）
- **段0（作る前に測る・便0）**: 試しの頼み 20 件（請求書 8・予定 8・わからない 4）に正しい種類を付けた表を backend/app/assistant_regression/cases.json に置く（backend の image は ./backend だけを材料に作るため。`.github/workflows/build-images.yml:86`）。決まり無しで今の担当 AI に、20 件と「次からは〜」3 件を 3 回ずつ流す（69 回）。種類が合う数と 1 件の秒数を数え、docs/handoff/secretary-rulebook/baseline.md（便0で作る） に残す。
- **合格の線（PO 2026-11-12「1」・baseline.md §6）: 20 件すべての種類が合ったときだけ合格。合わない・読めない・測れなかったが 1 件でもあれば合格にしない。段0の今の秘書は 69/69 で合った。**
- 流し方: 人が「前と同じか試す」を押したときだけ、backend が裏で 20 件を 1 件ずつ流す。
  - アプリ全体で試しは 1 本だけ。試しは DB 接続を 1 つ取って終わるまで持ち、2 つの数の鍵 `pg_try_advisory_lock(1077, 0)`（1 つ目の数は本件の ADR 番号） を取る（google_webhook の `(1059, 会社)` とぶつからない）。取れなければ「いま試し中です」と返す。finally で rollback の後に `pg_advisory_unlock(1077, 0)` を呼び、接続を閉じる（`backend/app/services/google_webhook.py:247-252` と同じ形）。接続の束へ返すときの後片付けは鍵を外さない（`backend/app/database.py:37-47`）ので、finally の unlock を必ず通す。
  - 試しの行（`secretary_rule_checks`）を書くときは、その会社の文脈を自分で付け、書いた後に戻す。始めるときに sdk・model・rules_count を入れる。
  - 1 件が 429 `busy` か時間切れのときは、合わないに数えず 1 回だけやり直す。それでも取れなければ「測れなかった数」として別に出す（合う数・合わない数・測れなかった数の 3 つ）。
  - 試しの間、容器は利用者の頼みに 429 `busy` を返す（待ち行列は無い・recon.md §2）。画面は今の「混んでいます」の文に、「試し中は約 N 分使えません」を足す（N は段0の秒数 × 20 から出す）。
  - 行に status（running・done・failed）と数を書き、1 件進むたびに progress_at を更新する。progress_at から 10 分進まない running の行は failed と見なす（1 件の上限 85 秒 × やり直し 2 回より長い）。試しが途中で例外を出した後に、鍵が外れていることを `pg_locks` で確かめ、次の試しを始められる試験を置く。
- 使用の記録: purpose に `secretary_regression` を 1 つ足す。①は便1（DB が先に値を 1 つ多く許しても、書くコードが無いので行は増えない）、②〜⑥は `secretary_regression` を書くコードと同じ PR に入れる（手順書 [card-bin1.md](card-bin1.md)「この便で決めたこと」）。書くコードは便3（§12）。直す場所: ①CHECK を広げる migration（migrations/20261103_120000_create_ai_job_assignments.sql の 148〜175 行目と同じ「定義に値が無ければ広げる」形）②`backend/app/services/llm_budget.py:159-169` の一覧 ③照合試験 `backend/tests/test_llm_usage_isolated.py` ④`backend/app/routers/assistant.py:135` の purpose の決め打ちを引数にする ⑤画面の使用量の区画の一覧 KNOWN_PURPOSES（`frontend/src/pages/super-admin/components/LlmUsageSection.tsx:151-159`）と ja.json・en.json の名前のキー ⑥色は 7 色を順に回すので、8 つ目は 1 つ目と同じ色になる。これを許し、トークンも色も足さない（`frontend/src/tokens.css` の `--chart-series-*` は 7 色・ADR-067 で新しい色は足さない）。区別は翻訳キーの名前で付く。AI 担当の画面の集計（`backend/app/routers/super_admin_ai_jobs.py:42-60`）は purpose で絞るので、試しはふだんの回数とログインの○×に混ざらない。
- 基準値より合う数が減ったら、画面に「前より合う数が減りました」と出す。外すかは人が選ぶ（自動では外さない）。

## 7. 毎週の数と試しの結果の置き場（R7・R8）
- PO の言葉（2026-11-12）: 「置き場所だが専用のメニューを作成してほしいサイドメニューのSaas管理メニュー内に作ってくれ」。前の版の「AI の担当タブに 1 区画足す」はやめた。
- メニュー: サイドメニューの「SaaS管理者」の区画に 1 行足す。名前の翻訳キーは `nav.superAdminSecretaryRules`（ja「秘書の決まり帳」・en「Secretary rulebook」）。行き先は `/super-admin/secretary-rules`。並びは「LINE解析」の次（AI の仕事が並ぶ）。
  - 足す場所: ①`frontend/src/components/DesktopShell.tsx:197-202` の `saasAdminItems` に 1 行（同じファイル 196 行目の並びの説明も直す）②`frontend/src/components/MobileShell.tsx:172-205` の `isSuperAdmin` の一覧に `resolveItem` 1 つ（アイコンは今と同じ `NAV_ICONS.saasAdmin`）③`frontend/src/config/routeTitles.ts:13-22` に 3 行（親と子 2 つ）④`frontend/src/App.tsx` の `/super-admin/users` の経路（395〜397 行目）と同じ形で、親は子の「毎週の数」へ転送、子 2 つ（`weekly`・`checks`）⑤`frontend/src/locales/ja.json`・`frontend/src/locales/en.json` の `nav` にキー 3 つ（親・毎週の数・試しの結果）。
  - アイコンも色も足さない。新しい部品も作らない。
- ページの部品（金型だけ）: 外枠 `PageLayout`（`navKey` に上のキー）・ページの中の小さなメニュー `SubMenu`（前例 `frontend/src/pages/super-admin/users/UserManagementSubMenu.tsx`。項目は「毎週の数」「試しの結果」の 2 つ）・表 `DataTable`・状態の印 `Badge`・空のとき `EmptyState`・読み込み中 `LoadingBlock`（すべて `frontend/src/components/` にある金型。前例 `frontend/src/pages/super-admin/ViewerAccountsPage.tsx:15-28`）。
- 見られる人: メニューは `isSuperAdmin` のときだけ出す（今の区画と同じ）。ページは `useSuperAdmin` で印が無ければ見せない。読む口は backend で `require_super_admin` を付ける（R6 の判定 1 か所のまま）。
- 「前と同じか試す」ボタンは、今の設計どおりチャットの承認・外すの後に出す（§5（６））。このページの「試しの結果」でも同じ口を押せるようにする（口は 1 つ・2 本目は断る §6）。どちらから押しても、試すのは押した人のログインの会社の決まり（§6 の会社の文脈と同じ）。ほかの会社を選んで試す道は作らない。
- 今ある `LlmUsageSection` の使用量の区画（§6 の purpose）は動かさない。
- 毎週の数を出す区画の元: 使用の記録・決まり帳・試しの結果の 3 つだけ（新しい集計の表は作らない）。
- 決まり帳と試しの結果は RLS がかかるので、運営文脈を付けて 2 表を読み、読んだ後に `reset_operator_context`（`backend/app/auth/dependencies.py:471`）を呼ぶ。前例 `backend/app/routers/fx_rate_admin.py:135-149`（set_operator_context → try → finally reset）と同じ形。
- 出す数（直近 7 日・会社ごと）: 頼みの数・「違う」の数（source_kind ごと）・候補の数・承認の数・外した数・最後の試しの合う数と、その時の担当 AI。

## 8. 外部・過去事例の参照と我々への応用
- バディカダイレクト「中野愛作」（research.md §1）: 答えの元を自社のデータと代表の発信に絞り、判断は人へ渡した。→ 決まりは会社が承認したものだけ・保存は人が押す。
- Intercom Fin 55%→75%（G1・二次）／ Intercom 公式手順（G1'）: AI ではなく AI が読む資料を直し、毎週数えた。→ §7。
- Tay（F1・24 時間以内に停止）: 利用者の言葉を人の確認なしに取り込んだ。→ 承認しないと効かない。
- DPD（F3・二次）: 更新の後に確かめなかった。→ §6。
- DB の作り（research.md §6）: ベクトルで探す仕組みは資料が多いとき向き（D1 Anthropic 探し漏れ 5.7%→1.9%・D6 社内ヘルプデスク 17 分→7 分）。少ない量なら全部渡す方が正確（D3・63% の頼みで答えが同じ）。渡す量が増えると取りこぼす（D2）。ベクトルを足すなら同じ PostgreSQL が安い（D4・77%／65% 減、9,000 万件では差が小さく専用のまま）。→ 今は表 1 つで全部渡し、§2 の合図で進む。
- 当てはまらない点: どれも客向け。本件は社員 2 人が使う社内の秘書。成功を数で約束できる一次資料は無い（research.md §4）。だから段0で自社の数を先に取る。

## 9. 弊害と対処
| 弊害 | 対処 |
|---|---|
| 決まりで AI の答えが崩れる | 型の検査は今のまま。§6 の試し。外せば次の頼みから戻る |
| 決まりに「ほかの会社の〜」と書いても | AI は会社のデータを持たない。名前を探すのは backend の自社の範囲だけ（ADR-1056 のまま） |
| 試しの間、全社の秘書が使えない | 押したときだけ流す・画面に分数を出す・1 本だけ。1 件 6〜8 秒（`docs/handoff/secretary-chatgpt/design.md:262` の試験の値）なら 20 件で約 2〜3 分、全件が 85 秒の打ち切りとやり直しなら最悪約 57 分。同時 1 本（ADR-1056:19）は変えず、新しい ADR のリスク欄にこの分数と「秘書を使う会社が 2 社を超えたら見直す」を書く |
| 試しは種類が合うかだけを数え、決まりが効いたかは測らない | 便3で cases.json に「決まりが効いたか」を見る頼みを足すかを決める（今は種類の判定が壊れていないことだけを守る） |
| 2 つの容器で組み立てがずれる | compose.mjs 1 ファイルを両方が読む。容器の試験を CI で流す（§11） |
| 戻し方 | backend が `rules` を空で送れば前と同じ答えに戻る。表は戻しの SQL で消せる |

## 10. 審査（Architect）
- 1 回目（2026-11-12・reviewer opus・/tmp/CC報告ファイル/secretary-meet/rb-review1.md）: **REVISE**・13 件。
  - 反映: 1 大きさ（§3・20 件×150 字）／2 改める決定 3 つと行番号（§2）／3 試しの記録（§6 purpose を足す）／4 待たせず断る（§6）／5 状態と口（§4・§5）／6 答えの形と指示文の場所（§3）／7 関所の形（recon の引用・本欄の全パス・維持の仕組み）／8 R2（§5・PO へ）／9 置き場と運営文脈（§6・§7・§12）／10 migration の作業（§4）／11 上限の同時押し（§4）／12 維持の仕組み（末尾）／13 軽い指摘（R6 の文・親へのリンク・テナント 1 は入口が閉じている＝recon.md §1）。
  - 反映しないもの: ideal-state.md への PO の言葉の追記は PO だけが書く（STANDARD-WORKFLOW §1.5）。PO の言葉は kgi.md に残してある。
- 2 回目（2026-11-12・同じ審査役・/tmp/CC報告ファイル/secretary-meet/rb-review2.md）: **REVISE**・7 件。1 回目の 13 件は照合し直して直っていた。
  - 反映: N1 compose.mjs の配り方（§3）／N2 鍵の外し方（§6）／N3 purpose の一覧を持つ場所（§6）／N4 試しの表の置き場（§6）／N5 大きさの余裕（§3）／N6 busy と時間切れの数え方（§6・§11）／N7 回数・混ざり・判定の時刻・前例（§6・§7・§12）。
- 3 回目（2026-11-12・同じ審査役・/tmp/CC報告ファイル/secretary-meet/rb-review3.md）: **REVISE（軽い）**・3 件。N1〜N7 は照合し直して直っていた。
  - 反映: M1 表の欄を §6 とそろえた（§4）／M2 束の接続を使い finally の unlock を必須にし、`pg_locks` で確かめる試験にした（§6）／M3 8 つ目の色は 1 つ目と同じを許し、色を足さない（§6）。補足 2 件（試験の名前・error_code と翻訳キー）も反映。
  - 審査役の見立て: この 3 か所が直れば全体の読み直しは要らない。
- 4 回目（2026-11-12・同じ審査役・/tmp/CC報告ファイル/secretary-meet/rb-review4.md）: **APPROVE**。M1〜M3 と補足が入り、§4 と §6 に食い違いが無いことを照合。
- DB の作りの評価（2026-11-12・Fable・PO の依頼「fableにも評価させて」・/tmp/CC報告ファイル/secretary-meet/fable-db-eval.md）: **条件付きで足りる**。ベクトル DB は今は要らない。先に来る限界は 20 件・16KB・同時 1 本。
  - 反映: source_kind の欄（§4・§7）／試しの結果を別の表にし担当 AI と型を残す（§4・§6）／ADR に書く決め事と見直しの合図（§2）／試しで全社が止まる分数（§9）／20 件付けたときの秒数を便2で測る（§12）。
  - 反映しないもの: 種類の札の欄・ベクトルの欄は今は入れない（§4）。
- 5 回目（2026-11-12・同じ審査役・変わった所だけ・/tmp/CC報告ファイル/secretary-meet/rb-review5.md）: **REVISE（軽い）**・3 件。鍵・会社文脈・RLS・欄名・出典・分数の計算は合っていた。
  - 反映: P1 表 2 つに §3・§7 を合わせた／P2 札の初期値は invoice・event の行だけ（§2）／P3 冒頭の状態の行（§0）。
- 6 回目（2026-11-12・同じ審査役・P1〜P3 だけ・/tmp/CC報告ファイル/secretary-meet/rb-review6.md）: **APPROVE**。補足 1 語（冒頭の目標の行を「承認済み」に）も反映。
- 7 回目（2026-11-12・同じ審査役・PO の指示で専用メニューへ移した所だけ・/tmp/CC報告ファイル/secretary-meet/rb-review7.md）: **REVISE（軽い）**・3 件。行番号・金型・印の判定 1 か所・前の版との食い違いは問題なし。
  - 反映: Q1 デスクトップ 4 つ・スマホ 5 つと書き分けた（§3）／Q2 試験の題と説明を 5 つに直す（§11）／Q3 試すのは押した人のログインの会社（§7）。
- 8 回目（2026-11-12・同じ審査役・Q1〜Q3 と ADR-1077・/tmp/CC報告ファイル/secretary-meet/rb-review8.md）: **REVISE（軽い）**・3 件。Q1〜Q3 は直っていた。ADR と設計・引用の食い違いは無し。
  - 反映: 冒頭の ADR 番号／鍵の 1 つ目の数を ADR-1076 と重ならない 1077 に／ADR の索引を作り直す。
- 9 回目（2026-11-12・同じ審査役・/tmp/CC報告ファイル/secretary-meet/rb-review9.md）: **APPROVE**。軽い指摘 3 件（この行の版数・kgi.md の「（案）」の残り・仕様索引の「承認待ち」）は便0の手順書の作業で直した。

## 11. 受け入れ基準と確かめ方
| 基準 | 検証方法 |
|---|---|
| R1 承認で決まり帳に入る | pytest（`POST /assistant/rules` で approved・決めた人が入る。AI の答えだけでは行が増えない）＋PO が本番で 1 件 |
| R3 候補の一覧 | pytest（自社の候補だけ返る）＋PO が本番で 1 回 |
| R4 外すと次から効かない | pytest（外した後の容器への頼みの `rules` に入らない） |
| R5 自社の承認済みだけ | RLS 試験（2 社 × 承認済み/候補 の 4 マス・本物の migration を当てる）＋pytest（送る `rules` は承認済みだけ） |
| R6 判定 1 か所 | pytest（印を外した人は新しい口すべてで 403）＋grep（新しい口に名前・番号の直書きが無い） |
| R7 試しの数 | pytest（試しの後に数と sdk・model が `secretary_rule_checks` の行に入る・やり直しても前の行が残る・2 本目は断る・途中の例外の後も次の試しを始められる・busy は 1 回やり直して「測れなかった数」に入る・10 分進まないと failed）＋段0の基準値（baseline.md） |
| R8 毎週の数 | pytest（6 つの数・運営文脈を戻す）＋PO が画面で 1 回 |
| 専用メニュー（§7） | vitest（`frontend/src/components/DesktopShell.test.tsx:124` の印なしで出ない一覧に足す・同じファイル 122 行目の説明 K1「四つだけ」と 123 行目の題 "exactly four" を 5 つに直す・印ありで行き先が `/super-admin/secretary-rules`）＋PO がサイドメニューで 1 回 |
| R9 全文を残さない | 試験（2 表の欄が §4 の一覧と同じ） |
| R10 金型・トークン・翻訳キー | 既存の必須チェック（ui-governance-gate・design-token-guard・frontend-check） |
| 上限いっぱいでも届く | 容器を直接たたく試験（絵文字で 20 件×150 字＋1000 字近くまで埋めて 200）＋pytest（15,000 バイトを超えたら送らない・制御文字の決まりは断る） |
| 組み立てが 2 つで同じ | 容器の試験を CI で流す（便2で workflow を足す） |
| 21 件目が入らない | pytest（同時に 2 本承認しても approved は 20 件） |

## 12. 便の分け方
- 便0: 段0の測定（本番の秘書に 69 回。足すのは cases.json・測る台本・baseline.md だけで、動く部分は変えない）→ PO が合格の線を決める。流す時刻を記録し、PO に先に伝える。道は [card-bin0.md](card-bin0.md) で決めた: 本番の backend の image の使い捨ての容器から秘書の容器を直接呼ぶ（口の検査と同じ関数を使う・ログインの札は使わない）。この道では使用の記録に行が入らないので、69 回は秘書の 24 時間の回数に混ざらない。
- 便1: 表・RLS・purpose の CHECK（§6 の①）を足す migration と、相談係の読み取り用の分類（`migrations/20261024_100300_create_ai_cloud_views.sql`）に 2 表の 8 列を足す（危険 PR・GO 記録）。手順は [card-bin1.md](card-bin1.md)。
- 便2（決定 PO 2026-11-13「1」: 「次からは〜」の聞き分けは便3 で画面と一緒に出す。便2 では画面の見た目は何も変わらない）: 決まりを秘書に渡す仕組み・決まりを出し入れする裏側の窓口・決まり 20 件での速さの試しだけ。種類 2 つ（rule_proposal・rule_list）・prompt.txt・schema.json・画面の型は便3 へ移す（便2 で種類だけ先に出すと、画面が知らない答えが空の吹き出しになるため）。2 つに分ける（Opus の決定）:
  - 便2a: compose.mjs・容器 2 つが `rules` を受け取る・容器の試験を CI へ・測る台本に `--rules`。手順は [card-bin2a.md](card-bin2a.md)。本番に出した後、便0 と同じ道で仮の決まり 20 件（[bin2/dummy-rules.json](bin2/dummy-rules.json)・種類を変えない中身だけの決まり）を付けて 23 件 × 3 回を流し、1 件の秒数と合う数を baseline.md に足す。
  - 便2b: backend が承認済みの決まりを送る（15,000 バイト・制御文字の検査）・§5 の口。§6 の試しの仕組みと②〜⑥の使いみちは便3 へ移す（PO の決定は便2 を 3 つ「だけ」に限っている。試しを始めるボタンも便3 にある。Opus の決定・2026-11-13 審査の指摘 D）。毎週の数を読む口（§7）は、それを見せるページと同じ便3 に置く。
- 便3: 種類 2 つ・prompt.txt・schema.json・画面の型・画面（案・一覧・「違う」・試すボタン）・§6 の試しの仕組みと②〜⑥の使いみちと、SaaS管理者のメニューの「秘書の決まり帳」のページ（毎週の数とそれを読む口・試しの結果・§7）。聞き分けと画面が同時に使えるようになる。
  - 注記（2026-11-14 Opus）: 秘書の「予定のカルテ」（ADR-1078・[../secretary-event-karte/design.md](../secretary-event-karte/design.md)）も prompt.txt・schema.json・画面の型を変える。カルテを先に出し、便3 の手順書はその合流後の origin/main から作る。

## 維持の仕組み
- 守り手: .github/workflows/test.yml
- 対象: 承認できる人が印のある人だけであること・ほかの会社の決まりを読まないこと・AI の答えだけで行が増えないこと（pytest と RLS 試験）。
- ほかの守り手（PR ごと・機械）: `.github/workflows/migration-test.yml`（便1の表と RLS）・`.github/workflows/ui-governance-gate.yml`・`.github/workflows/design-token-guard.yml`・`.github/workflows/frontend-check.yml`（画面）。
- 今は無く便2で足す: 容器 2 つの `node --test` を流す CI（recon.md §4）。
- 今は無く便3で足す: §6 の試し（人がボタンを押したとき）。
- 人手で守る: 毎週の数を PO が見ること。理由: 数を見て決まりを足すか外すかを決めるのは人の判断で、機械に任せない（Tay の教訓）。見忘れを知らせる仕組みは便3の後に、今ある週次の知らせに足すかを決める。
