HEAD: 1172ecd08cab4b9d1b1603ae77df9ba8738aa8a6（origin/release/lead-regression-recon。指定どおり 1172ecd08）
判定: REVISE

# review — リードのカルテで成約しやすさを分析する（設計 第4版の審査）

- 審査したもの: docs/handoff/lead-regression/design.md（第4版）・docs/handoff/lead-regression/recon.md
- 照合の基準: origin/main 27d1d6fbddd21908ec862875061d3c9bdd2ba7a8。design.md:10 の基準 0a48f8172 から main は進んでいるが、その間の差分（git diff --stat 0a48f8172 origin/main）は auth・passkey・LoginPage・backend/requirements.txt などで、design.md が引くファイルは backend/requirements.txt だけ。requirements.txt には今も statsmodels・numpy が無い（grep で 0件）ので design.md:148 は今の main でも成り立つ
- 前回の審査: origin/release/lead-regression-design-v3-report の docs/handoff/lead-regression/review-design-v3.md（第3版 REVISE・直す点14件）
- 第3版との差分: git diff 98afc1111 HEAD -- docs/handoff/lead-regression/design.md（42行足し・30行消し）
- 審査役: Claude Opus（設計審査役）。本番には接続していない。本番の中身に関わることは「未確認」と書く
- 行番号の書き方: 「ファイル:行」は origin/main の行。design.md・recon.md は HEAD 1172ecd08 の行

## 判定の理由（要約）

第3版の直す点14件は、書き足すべき所にはすべて書き足されている（項目1）。足した引用もほぼ実物と合う（項目2）。統計の骨組み（範囲・件数の式・時刻の範囲）も筋が通る（項目6）。

ただし、実物と照らすと次の点が新しく見つかった。どれも書き足しで直せるが、このままだと K5・K6 が仕組みと関係なく × になるか、消し残しが出るか、PO に事実と違う選択肢を示すことになる。

- (A) **K5② はまだテナント001の自然な変化に左右される。** 「始めた時刻より後の行が 0件」は、テスト用データと関係のない行（Discord の受信の自動翻訳、元のリード id 4・6 への送信）も数える（項目4-2）。
- (B) **K5① は目印の無い表を見られない。** 失注の理由・店舗の形の選択・選択肢・WhatsApp の会話の記録は目印を持たないので、間違って 004・006 に書いても 0件のままになる（項目4-1）。
- (C) **§6-1 の消し残し。** 手で足した会話の記録の翻訳は message_id が `conv_log_<id>` で、手順2 の `tlr-` に当たらない（項目5-1）。audit_logs は数える表に入っているのに消す手順も扱いの決まりも無い（項目5-2）。
- (D) **画面の出し分けの根拠が違う。** design.md:158・209 は DashboardPage.tsx:462 の「切り替えの印」でテナント001だけに出せるように書くが、これはビルド時の環境変数で、テナントごとには分けられない（項目7-1）。
- (E) **本物との違いの漏れ。** leads の必須の列 customer_name の値が無い。こちらから営業した Instagram・Facebook のリードは、受信の前にアプリから送る形になるが、本物のアプリはそれを断る（項目3-1）。
- (F) **作り方の矛盾。** こちらから営業したリードでは「2回目の送信」が #3 の「最初の返信」になるのに、§3-2 は 2回目以降の送信を #3 に使わない 5分〜24時間で作るとしている（項目6-3）。

---

## 項目1 第3版の直す点14件

| # | 直す点（第3版） | 判定 | 根拠 |
|---|---|---|---|
| 1 | K5① を目印の行が 0件で測る | ○ | design.md:40①・51。理由として recon.md:63・68、`backend/app/celery_app.py:80`〜82、`backend/app/tasks/maintenance.py:112`〜132 を書いた（実物と一致）。ただし第3版の直す点で例に挙げた後半（書き込みの間に作られた行を書き込みの道具の側から 0件と確かめる）は入っていない。目印の無い表を見られない件は項目4-1 で新しい指摘とする |
| 2 | K5② を始めた時刻より後の行で測る | ○ | design.md:40②・51、design.md:183（始めた時刻を手順0で記録）。指示どおりに直っている。ただし測る範囲がテスト用データに絞られていない件は項目4-2 で新しい指摘とする |
| 3 | 数える表に leads を足し、元の行を id の一覧で確かめる | ○ | design.md:179（leads が先頭）、design.md:41・183・192（leads・meta_messages・conversation_logs・tenant_sales_form_options の id の一覧を手順0で記録、手順9で突き合わせる） |
| 4 | 添付のファイルの実体を消す手順・旧 customers の表 | ○ | design.md:184（file_path の一覧を手順7の前に記録）・193（手順10）・181（旧 customers の確認）。書き方の注意は項目5-3・5-4 |
| 5 | §3 の「本物との違い」5点と page_id | ○ | ①目印: design.md:59②・63・64①・65①・66①。②meta_messages の sender_id・original_language・recipient_id・messaging_type・message_tag: design.md:64・65。③conversation_logs の channel_identity・sender・contact_id・company_id・recorded_by_user_id: design.md:66・67。④audit_logs の create: design.md:67③。⑤受信の道の type: design.md:59①・223。page_id: design.md:65④。残る漏れは項目3-1 |
| 6 | 限界（アプリ外の送信が conversation_logs だけ） | ○ | design.md:72・215・221。§4-1（design.md:134〜141）には書かれていないが、§3 と §9 にあり読み落とすおそれは小さい。書き方の小さな直しは項目3-3 |
| 7 | 分析の範囲と件数の式 | ○ | design.md:145・149 |
| 8 | 優先度の計算の成約の側・customer_scores の行番号 | ○ | design.md:123（同 142行）・124・222。`backend/app/services/priority_scoring.py:183` は invoices を i.lead_id で結ぶ（実物と一致） |
| 9 | 人の操作の道2つと PO への報告 | ○ | design.md:128〜130。残る漏れは項目4-3 |
| 10 | 全テナントに出るか | ○ | design.md:158・163・209④ に書き、PO に聞く形にした。ただし出し分けの手段の根拠が事実と違う（項目7-1） |
| 11 | 仕込んだ値の置き場 | ○ | design.md:157（画面に出さない。正本は作り方の定義1か所。答え合わせは報告書） |
| 12 | K4 の検証方法 | ○ | design.md:39・159。frontend/AGENTS.md:57〜64・67〜77、docs/adr/ADR-144-ui-component-governance.md:41〜47・59〜64 と一致 |
| 13 | analytics.py:1108〜1111 | ○ | design.md:150。`backend/app/routers/analytics.py:1111` が dashboard.view |
| 14 | 2回目以降の送信の間隔・最初の日時の範囲 | ○ | design.md:107。ただし、こちらから営業したリードで §4-1 と食い違う（項目6-3） |

## 項目2 ファイル:行 の引用

照合したもの（すべて origin/main。第4版で足した・直した引用は全部、第3版で合っていた引用は抜き取り）:
webhook.py 536〜550・569〜580・583・609〜620・622〜643・644〜700・704〜708・711〜721・736・816〜851・854〜887・923〜929、leads.py 405・469・626〜636・688〜692・1419・1437・1870〜1900・1980〜1992・2066〜2104・2131〜2143、messaging_window.py 134〜149、tenant.py 357〜365・1022〜1056、conv_log_writer.py 31〜114、conv_logs.py 129〜165・280〜322、celery_app.py 74〜83・122〜127、maintenance.py 50〜85・110〜133、priority_scoring.py 179〜210・259〜261・296・372・411、check_priority_scoring_state.py 105〜124・140〜143、analytics.py 986〜989・1108〜1111・1747、dashboard.py 58〜64、DashboardPage.tsx 458〜476、InboxKartePanel.tsx 590〜593、schemas/lead.py 31・47・148・179・183・215、migrations/20260614_100000_create_sales_form_tables.sql 58・60・89、migrations/20260902_100000_create_lead_attachments.sql 55〜66・122〜128、migrations/20260604_090000_create_conversation_logs.sql 34〜55、frontend/AGENTS.md 21〜25・38〜43・55〜78、docs/adr/ADR-144-ui-component-governance.md 1〜12・40〜48・58〜65・108〜145、docs/specs/db-ssot/classification-master/design.md 42・48・101。ファイルの有無: frontend/tests-e2e/scene1-dashboard.spec.ts・frontend/tests-e2e/fixtures/mock-dashboard.json・frontend/src/components/DataTable.tsx・frontend/src/constants/icons.tsx・scripts/check-ui-governance.js・backend/app/tasks/priority_scoring_check.py・docs/specs/db-ssot/conversation-unification/design.md はすべてある。

一致したもの（抜粋）: webhook.py:547〜550（type 'Inbound'）・577・646〜656・669・673・611〜619・704〜708・711〜721・736・816〜851・876〜887・881・883・885、leads.py:469・628・690・2071・2075〜2076・2083・2092〜2101・2133〜2135、messaging_window.py:141〜149、tenant.py:365・1025・1027、conv_log_writer.py:43・68〜70・71、conv_logs.py:290〜295・306・310〜320、celery_app.py:80〜82、priority_scoring.py:181〜185・183・204〜207、check_priority_scoring_state.py:107・142、migrations/20260902_100000_create_lead_attachments.sql:60・63・126。

ずれ・内容の食い違い:

| design.md の場所 | 書いてあること | 実物 | 直し方 |
|---|---|---|---|
| design.md:158・209④ | ファネルの欄のような切り替えの印（DashboardPage.tsx:462）でテナント001だけに出すかを聞く | 462行の FUNNEL_MODE はビルド時の環境変数 VITE_FUNNEL_DASHBOARD（frontend/src/api/funnel.ts:23〜27）。全テナントで同じ値になり、テナントごとには分けられない。テナントごとの印は `frontend/src/components/FeatureGate.tsx`・`frontend/src/hooks/useFeatures.ts` で、値は public.tenant_features（`backend/app/routers/roles.py:148`〜156） | 直す点8 |
| design.md:123 | この点検にテスト用データが入る道は message_labels と customer_scores だけ | 同じ点検の 112〜123行は leads を読む（scripts/check_priority_scoring_state.py:117 の FROM leads）。今の表の形では invoices.lead_id・deals が無いので成り立たない式だが、「入る道は2つだけ」は言い過ぎ | 直す点11 |
| design.md:63 | 本物の受信の道が lead_channels を書く（669・694〜698） | 669行が新しいリードを作ったときの書き込み。694〜698行は名前が取れたとき（690行の if の中）の補いの書き込み | ずれは小さい。「694〜698（名前が取れたときの補い）」と書き添えるとよい（直す点12） |

確かめられないもの（未確認）: design.md:147 の statsmodels 0.15.0 の conf_int の既定（外の説明書。この審査では読んでいない）、design.md:40 の ai_ro の2つの表の有無（本番）、design.md:181 の pg_catalog の検索の結果（本番）。

## 項目3 DB と配線の SSOT

### 3-1. 必須の列・本物との違いの漏れ

1. **leads の customer_name（必須）の値が無い。** customer_name は空を許さない（`backend/app/services/tenant.py:359` VARCHAR(255) NOT NULL）。design.md:59 の「入れるもの」に無い。本物は受信の道で 'Messenger User'／'Instagram User'（`backend/app/routers/webhook.py:641`〜643）を入れたあと Meta から名前を取り直し（同 680〜689行）、エコーの道で `Messenger:` と相手の id の末尾8文字（同 543行）を入れる。テスト用に何を入れるか（例: `TLR-00001` と同じ文字）と、本物との違いを書く必要がある。なお 'Messenger User'／'Instagram User' を入れると、本物の受信が来たときに名前を取り直す決まり（同 628行）の形と同じになるので避けた方がよい（テスト用の sender_id には本物の受信は来ないので実害は無い）。
2. **こちらから営業した Instagram・Facebook のリードの最初の送信。** design.md:140 は、こちらから営業したリードを「送信から始める」。Instagram・Facebook では、これは「受信が1件も無いのにアプリから送った行」になる。本物のアプリは受信が無いと送れない（`backend/app/routers/leads.py:1887`〜1896、`backend/app/services/messaging_window.py:145`〜146 の NO_INBOUND）。本物でこちらから営業した Instagram・Facebook のリードは、アプリの外から送った最初の送信（エコー）で作られ、その送信は conversation_logs だけに書かれる（`backend/app/routers/webhook.py:816`〜851、`backend/app/routers/webhook.py:536`〜550 で initiative 'outbound'）。design.md:65 の⑥は「24時間を過ぎた送信」だけを書き、この形が無い。経路 3つ × こちらから営業 半々なので、400件のうち約 133件がこの形になる（§3-2 の配分からの計算）。
3. **列の細かい値。** meta_messages の platform（必須。`backend/app/services/tenant.py:1026`）はリードの channel_type と同じ値、conversation_logs の Instagram・Facebook の写しの original_language は空（本物の書く関数は書かない。`backend/app/services/conv_log_writer.py:75`〜78）、と明記するとよい。design.md:66 の「上の受信と同じもの」は original_language も写すと読めてしまう。

ほかの列（sender_id・recipient_id・messaging_type・message_tag・channel_identity・sender・contact_id・company_id・recorded_by_user_id）は、必須の列（`backend/app/services/tenant.py:1027`、migrations/20260604_090000_create_conversation_logs.sql 36・41・43・53行）と本物の書き込みと矛盾しない。○

### 3-2. 仕込んだ値の置き場・データの分散

- 仕込んだ値の正本は作り方の定義1か所（design.md:157）。画面・入口に出さないので2か所に分かれない。○
- 返信の速さはやり取りの表から計算し、leads に写さない（design.md:70・86）。○
- 読む表は経路ごとに1つ（design.md:71）。Instagram・Facebook の受信を2表に書くのは本物の配線（`backend/app/routers/webhook.py:854`・876）と同じ形。○
- 画面の出し分けをテナントごとの印（public.tenant_features）で行うことにした場合、その行は public の表への書き込みになり、テナント001の表だけに書くという前提（design.md:171）と §6-1 の数える表の外になる（直す点8）。

### 3-3. 「限界」の書き方

design.md:72 は実物と合う（アプリからの送信は meta_messages だけ `backend/app/routers/leads.py:2092`〜2101、アプリ外の送信は conversation_logs だけ `backend/app/routers/webhook.py:816`〜851）。ただし「アプリの外から送った返信」と書くと、こちらから営業したリードの最初の送信（3-1 の2）が入らないように読める。「返信」を「送信（こちらから営業したリードの最初の送信を含む）」に直し、本物では、こちらから営業した Instagram・Facebook のリードの最初の送信が meta_messages に無いことを書くとよい（直す点2）。

## 項目4 安全

確かめて ○ のもの:

- K5①の目印（lead_code `TLR-`・message_id／external_message_id／external_id `tlr-`）は本物の採番（`LD-`。`backend/app/routers/leads.py:469`、`backend/app/routers/webhook.py:577`・673）と重ならず、004 の本物の受信・操作で増えることは無い。毎日 4:00 の消し込み（`backend/app/tasks/maintenance.py:129`〜132）は目印の行の数に効かない。○
- K6 の元の行の id の一覧（design.md:41・183・192）は、件数と違い、004 の変化にも、テナント001に新しい行が足されることにも左右されない。○
- 古い行を消す定期の作業は audit_logs・data_access_events・auth_events・viewer などだけで（`backend/app/celery_app.py:80`〜117 の maintenance の5つ）、leads・meta_messages・conversation_logs は消さない（backend/app/tasks を INTERVAL で git grep）。180日前のテスト用の時刻は消されない。○

見落とし:

1. **K5① は目印の無い表を見られない。** §6-1 の数える表のうち、deal_close_reasons・lead_sales_form_selections・tenant_sales_form_options・WhatsApp の conversation_logs（design.md:67 で目印の列を書かない）は目印を持たない。間違って 004・006 に書いたとき、K5① は 0件のまま ○ になる。特に tenant_sales_form_options は 004 に同じ5つが既にある（`migrations/20260614_100000_create_sales_form_tables.sql:89`、recon.md:70）。失注の理由・店舗の形の選択・WhatsApp の会話の記録は、テスト用リードの id と同じ id のリードが 004・006 にあれば外部キーを通って本物のリードに付く（004 のリードは 56件・006 は 74件 recon.md:63・76。id の範囲は未確認）。後から数える方法では見つけられないので、書き込みの前に SQL ファイルを機械で点検する形（書き込み先がすべて `tenant_001.` で始まる表名で、ほかのテナントの名前・search_path の切り替えが無い）を K5① の検証方法に足す必要がある（直す点4）。
2. **K5② はテナント001の自然な変化に左右される。** design.md:40② は「始めた時刻より後に created_at がある行」を全部数える。しかしテナント001には Discord の経路があり（recon.md:68・99 のメッセージ4行はすべて discord）、Discord の受け口も自動翻訳の依頼を出す（`backend/app/services/inbound_translation.py:21`、翻訳の書き先は `backend/app/tasks/translation.py:73`〜76）。元のリード id 4・6 への送信も meta_message_sent・meta_message_send_failed の行を作る。どれもテスト用データと関係なく ②を × にする。送信の記録は new_data に lead_id を持つ（`backend/app/routers/leads.py:1986`・2137）ので、「new_data の lead_id がテスト用リードの id」に絞れる。翻訳の記録は message_id で絞れる（`tlr-` か、テスト用リードの会話の記録の `conv_log_<id>`。項目5-1）（直す点5）。
3. **人の操作の道の漏れ。**
   - リードの統合: 受信箱・カルテから統合（`backend/app/routers/leads.py:3226` の POST /leads/{master_id}/merge。13表を付け替えてから消える方を消す docs/adr/ADR-1049-lead-merge-all-tables-and-fill-blanks.md:18）を、テスト用リードと元のリード id 4・6 の間で行うと、テスト用の行が元のリードに付け替わる。§6-1 はテスト用リードの id で消すので、付け替わった WhatsApp の会話の記録・失注の理由・店舗の形の選択は消えず、元のリードにテスト用データが混ざる。design.md:125〜130 に無い。PO への報告に「テスト用リードを統合しない」を足し、§6-1 手順1 の止める条件に「元のリードに `tlr-` の行が付いている」を足す必要がある（直す点6）。
   - 画面の出し分けをテナントごとの印で行う場合の public.tenant_features への書き込み（直す点8）。
   - 第3版で足した2つ（会話の記録を手で足す・送ろうとする design.md:128〜129）は実物と合う。ただし手で足した記録の翻訳の行が §6-1 で消えない（項目5-1）。

## 項目5 消す手順 §6-1

- leads は数える表に入った（design.md:179）。○
- 元の行は id の一覧で確かめる形になった（design.md:41・183・192）。○
- 手順10（design.md:193）: 一覧に無いものを消さない・一覧と件数を PO に示す・PO 本人が流す、が書かれ、本番の不可逆の操作を PO 本人に限る決まり（AGENTS.md「不可逆操作は必ず PO 確認」）と矛盾しない。○。file_path の一覧は手順7（leads を消すと lead_attachments の行も消える migrations/20260902_100000_create_lead_attachments.sql:60）の前に取る順番になっており正しい（design.md:184）。

見落とし:

1. **手で足した会話の記録の翻訳が消えない。** 会話の記録を手で入れる入口の翻訳は、message_translations に message_id `conv_log_<会話の記録の id>` で書かれる（`backend/app/routers/conv_logs.py:147`〜159）。手順2（design.md:185）は `tlr-` で始まる行だけを消すので、これに当たらない。message_translations は結び付きの決まりが無い（migrations/094_create_message_translations.sql 25〜33行）ので、手順5 で会話の記録を消しても残る。design.md:128 の「足した行は手順5 が消す」も翻訳の行には当てはまらない。手順5 の前にテスト用リードの conversation_logs の id を記録し、手順2 で `conv_log_<id>` の行も消す必要がある（直す点7）。
2. **audit_logs の扱いが決まっていない。** design.md:179 は audit_logs（K5②の2つの action）を数える表に入れ、K6（design.md:41）は「§6-1 の表すべてでテスト用の行が 0件」とする。しかし手順2〜8 に audit_logs を消す手順は無い。人が送ろうとした・会話の記録を足した（design.md:128〜129）ときの行は残るので、K6 は 0件にならない。監査の記録を手で消すかどうかは決まりの問題なので、「audit_logs は消さない。K6 の 0件の対象から外し、件数だけを報告する」のように決めて書く必要がある（直す点7）。
3. **テスト用リードの id の一覧を残す時点。** 手順3・6 と手順9 の「テスト用の行が 0件」は、目印の無い表（customer_scores・message_labels・deal_close_reasons・lead_sales_form_selections）をテスト用リードの id で数える。手順7 で leads を消すと id は表から引けなくなるので、手順9 のために id の一覧を書き込みのとき（RETURNING）か手順1 で記録する、と書く必要がある（直す点7）。
4. **旧 customers の表の記載（design.md:181）。** 形は、日時・道（読み取りの道）・対象（3テナント）・結果（0行）・同じ検索で見つかるべき表が見つかったという確かめ（陽性の対照）を書いており、妥当。ただし次の2点が足りない。①リポジトリの側の根拠: migrations/20260601_140000_drop_customers_tables.sql が全テナントから customers と関連の表（015 で退避した customers_legacy_<id> を含む。同 8〜14行）を取り除く。これを引けば、0行の理由が分かる。②検索の条件（表の名前を何で当てたか。customers だけか、customers で始まる名前か）が書かれていないので、customers_legacy_<id> を見たかが読み取れない。名前で探すより、テナント001の leads を指す外部キーを pg_catalog.pg_constraint から全部挙げ、§6-1 の表の一覧と突き合わせる形にすると、名前を知らない表も漏れない（直す点9）。本番での結果は未確認。

## 項目6 統計

1. **分析の範囲（design.md:145）**: 成約と失注だけに絞り、外した件数を出す。元のリード id 4・6（状態 lead。recon.md:111）は外れ、K3d は本番でも本番の外でも 400件で計算する。○
2. **件数の式（design.md:149）**: min(成約, 失注) ÷ 11 ≧ 10。テスト用は min(120, 280) ÷ 11 ≒ 10.9 で満たす。成約と失注の少ない方で数えるのは、先行の「1項目につき 10件以上」の考え方（docs/handoff/accuracy-measurement/design-regression.md）と合う。○。ただし §4-1（design.md:141）で返信の時間が空欄のリードを回帰から外すので、「件数は上の範囲に入ったリードで数える」を「範囲に入り、回帰に使えたリードで数える」に直すとよい（テスト用データは空欄 0件なので K には効かない。直す点12）。
3. **時刻の範囲（design.md:106〜107）**:
   - 最初のメッセージは 180〜70日前。メッセージは最多 20回で間の数は 19、1つの間は最長 72時間なので、最後のメッセージは最初から 57日以内（design.md の「20回 × 72時間 = 60日」は上に余裕のある見積もりで、結論は変わらない）。最後のメッセージは書き込む日の 10日以上前になり、§3-3 の「2日以上前」（design.md:116）と K5③ を満たす。○
   - **食い違い**: §4-1（design.md:138）は「こちらの最初の返信」を「最初の受信のあとの最初の送信」とし、こちらから営業したリードもこれで測る。こちらから営業したリードは送信→受信→送信と並ぶので、この「最初の返信」は2回目の送信になる。一方 design.md:107 は「こちらの2回目以降の送信は、すぐ前の受信から 5分〜24時間で取る（#3・#4 の2値には使わない）」とする。こちらから営業したリード（約 200件）では、#3 の時刻を 1〜59分か 61分〜48時間から作る（design.md:106）のか 5分〜24時間から作るのかが決まらず、5分〜24時間で作ると #3 の2値が仕込んだ側に入らない（61分〜24時間なら遅い側に入るが、5分〜59分なら速い側に入る）。「最初の受信のあとの最初の送信（相手から来たリードは1回目、こちらから営業したリードは2回目の送信）は design.md:106 の範囲から取り、それ以外の送信は 5分〜24時間」と書く必要がある（直す点3）。
   - 180日前の時刻: 古い行を消す定期の作業は meta_messages・conversation_logs に無い（項目4）。毎日の顔写真の取り直しは過去30日の行を見るが page_id が空なので飛ばす（`backend/app/tasks/avatar.py:311`・317）。○
4. **K3d**: K3d は #3・#4 の2値だけを使い、2値は作り方の範囲で決まるので、上の食い違いを直せば同じ種で同じ値になる。○（直さないと、本番の外と本番で同じ作り方のコードを使う限り一致はするが、仕込んだ答えと合わず K3a・K3b が × になりうる）
5. **K5③ と §3-3 の言い方**: K5③（design.md:40）は「書き込む日以降が 0件」、§3-3（design.md:116）は「2日以上前」。見張りを止めるには K5③ で足りるが、作り方の約束（2日以上前）を確かめる形にそろえると読み違いが無い（直す点12）。

## 項目7 画面 §4-3

1. **出し分けの手段の事実が違う（項目2 の表）。** DashboardPage.tsx:462 の印はビルド時の環境変数（frontend/src/api/funnel.ts:23〜27）で、テナントごとには分けられない。テナントごとに出し分けるなら FeatureGate（`frontend/src/components/FeatureGate.tsx`、`frontend/src/hooks/useFeatures.ts`）と public.tenant_features（`backend/app/routers/roles.py:148`〜156）を使う形になり、本番の public の表への書き込みが要る。§8 #5④（design.md:209）の選択肢をこの事実に直し、選んだ場合の書き込みを §5・§6-1・K5 の範囲に入れる必要がある（直す点8）。
2. **画面の注意書きと全テナント表示の矛盾。** design.md:112 は「これは仕組みの確認でテスト用、と画面と報告にも書く」、design.md:175 は「目的は仕組みの確認だけと画面と報告に書く」とする。一方 design.md:156 の「表に出すもの」にこの注意書きは無く、design.md:158 では欄は全テナント（本物の 004 を含む）に出る。全テナントに出す場合、004 の画面に「テスト用データ」と出すのは事実と違う。テスト用の注意書きはテナント001の報告だけに書くのか、画面に出すならどの条件で出すのかを決める必要がある（直す点10）。
3. **仕込んだ値を画面に出さない形（design.md:157）**: 正本1か所・答え合わせは報告書。○
4. **金型が無いときに止める決まり（design.md:159）**: docs/adr/ADR-144-ui-component-governance.md:59〜64 と一致。○
5. **アイコン・E2E・UI の点検（K4 design.md:39）**: frontend/AGENTS.md:57〜64・67〜77、ADR-144:41〜47 と一致。○。ただし UI の点検 scripts/check-ui-governance.js が見るのは `frontend/src/pages/**/*.tsx` だけ（docs/adr/ADR-144-ui-component-governance.md:43・134。components/・features/ は見ない）。新しい欄を components/ に置くと点検は何も見ずに通る。欄のファイルの置き場を実装カードで決めるときに、点検の対象かどうかを書き、対象外なら PO の目視とレビューで金型を確かめる、と K4 に書き添えるとよい（直す点12）。
6. ADR-067（デザイントークン）・ADR-027（t() と ja・en）・frontend/AGENTS.md:40（色のトークンは明るい画面と暗い画面の両方）とは矛盾しない。○

## 項目8 新しい抜け・矛盾・不明点

1. 上の (A)〜(F)（項目3-1・4-1・4-2・4-3・5-1・5-2・5-3・6-3・7-1・7-2）。
2. **元の行を確かめる表の範囲**: K6 の id の一覧は leads・meta_messages・conversation_logs・tenant_sales_form_options の4つ（design.md:41・183）。元のリード id 4・6 に付いている lead_channels・lead_sales_form_selections・deal_close_reasons の行は一覧に無いが、手順3・6 はテスト用リードの id、手順7 は lead_code `TLR-` で消すので、元の行には当たらない。○（統合されていなければ。項目4-3）
3. **実装カードに進めるか**: まだ進めない（REVISE）。直す点はどれも書き足し・書き直しで済み、骨組み（表・目印・消す順番・統計）は固まっている。直す点8（出し分け）は PO の選択肢そのものを直すので、§8 #5 の質問の前に直す必要がある。

---

## 直す点

1. **§3 の leads の行（design.md:59）**: customer_name（必須 `backend/app/services/tenant.py:359`）に入れる値を決めて書く。本物の値（受信の道 'Messenger User'／'Instagram User' のあと名前を取り直す `backend/app/routers/webhook.py:641`〜643・680〜689、エコーの道 `Messenger:` と id の末尾 同 543行）との違いを「本物との違い」に足す。あわせて design.md:64〜66 に、meta_messages の platform（必須 `backend/app/services/tenant.py:1026`）はリードの channel_type と同じ値、Instagram・Facebook の写しの conversation_logs の original_language は空（`backend/app/services/conv_log_writer.py:75`〜78 は書かない）と書く。
2. **§3 の meta_messages（送信）の行（design.md:65）と限界（design.md:72）**: 「本物との違い」に⑦「こちらから営業した Instagram・Facebook のリードは、受信の前のアプリからの送信で始まる。本物のアプリは受信が無いと送れない（`backend/app/routers/leads.py:1887`〜1896、`backend/app/services/messaging_window.py:145`〜146）。本物のこちらから営業したリードは、アプリの外からの最初の送信（エコー）で作られ、その送信は conversation_logs だけにある（`backend/app/routers/webhook.py:816`〜851・536〜550）」を足す。限界の「アプリの外から送った返信」を「アプリの外からの送信（こちらから営業したリードの最初の送信を含む）」に直す。
3. **§3-2 の時刻（design.md:106〜107）**: 「最初の受信のあとの最初の送信（相手から来たリードは1回目、こちらから営業したリードは2回目の送信）は #3 の範囲（1〜59分か 61分〜48時間）から取る。それ以外のこちらの送信は、すぐ前の受信から 5分〜24時間」と書き、§4-1（design.md:138）と食い違わないようにする。こちらから営業したリードの最初の送信の時刻（＝最初のメッセージの日時）も明記する。
4. **K5①（design.md:40）**: 検証方法に「書き込みの SQL ファイルを流す前に機械で点検し、書き込み先の表名がすべて `tenant_001.` で始まり、ほかのテナントの名前と search_path の切り替えが無いことを確かめる」を足す。理由（目印の無い表 deal_close_reasons・lead_sales_form_selections・tenant_sales_form_options・WhatsApp の conversation_logs は後から数えて見つけられない。004 には同じ選択肢5つがある `migrations/20260614_100000_create_sales_form_tables.sql:89`）を §2-1 に書く。
5. **K5②（design.md:40）**: 数える行を、テスト用データに関わる行に絞る。audit_logs は「action が meta_message_sent・meta_message_send_failed で、new_data の lead_id がテスト用リードの id」（`backend/app/routers/leads.py:1986`・2137）、message_translations は「message_id が `tlr-` で始まるか、テスト用リードの会話の記録の `conv_log_<id>`」（`backend/app/routers/conv_logs.py:149`）。始めた時刻より後、の条件は残してよい。理由（テナント001の Discord の受信の自動翻訳 `backend/app/services/inbound_translation.py:21`、元のリード id 4・6 への送信）を §2-1 に書く。
6. **§3-4 の人の操作の道（design.md:125〜130）と §6-1 手順1（design.md:184）**: リードの統合（`backend/app/routers/leads.py:3226`、ADR-1049 18行）でテスト用の行が元のリードに付け替わる道を足す。PO への報告に「テスト用リードを統合しない」を足し、手順1 の止める条件に「元のリード（手順0 の id）に `tlr-` の行・テスト用リードからの付け替えの印がある」を足す。
7. **§6-1（design.md:179・183〜193）と K6（design.md:41）**: ①手順5 の前にテスト用リードの conversation_logs の id を記録し、手順2 で message_id が `conv_log_<id>` の message_translations も消す（`backend/app/routers/conv_logs.py:147`〜159）。design.md:128 の「足した行は手順5 が消す」に翻訳の行も手順2 で消すと書き足す。②audit_logs を消すか消さないかを決めて書く（推奨: 監査の記録は消さない。K6 の 0件の対象から外し、テスト用リードの id を new_data に持つ行の件数だけを報告する）。③テスト用リードの id の一覧を書き込みのとき（または手順1）に記録し、手順9 で目印の無い表を数えるのに使う、と書く。
8. **§4-3（design.md:158）・§5（design.md:163）・§8 #5④（design.md:209）**: DashboardPage.tsx:462 の印はビルド時の環境変数（frontend/src/api/funnel.ts:23〜27）でテナントごとには分けられない、と事実を直す。テナント001だけに出す選択肢は FeatureGate（`frontend/src/components/FeatureGate.tsx`）と public.tenant_features（`backend/app/routers/roles.py:148`〜156）を使う形になり、本番の public の表への書き込みが1行要ること、その行を K5・§6-1（消すか残すか）に入れることを書いてから PO に聞く。
9. **§6-1 の旧 customers の記載（design.md:181）**: リポジトリの側の根拠 migrations/20260601_140000_drop_customers_tables.sql（同 8〜14行。customers_legacy_<id> を含む）を引く。検索の条件（名前の当て方）を書く。できれば名前で探すのではなく、テナント001の leads を指す外部キーを pg_catalog.pg_constraint から全部挙げ、§6-1 で扱う表の一覧と突き合わせる形に直す（読み取りだけ・本番の結果は実装のときに記録）。
10. **画面の注意書き（design.md:112・156・175）**: 「テスト用データで仕組みを確かめるもの」という注意書きを、どこに出すか決めて書く（テナント001の報告書だけにする、または出し分けの印が立っているテナントだけに出す、など）。全テナントに出す欄に「テスト用」と出さないこと。「成約しやすさの目印で、原因ではない」の注意書き（design.md:156）は全テナントに出してよい。
11. **§3-4（design.md:123）**: 「テスト用データがこの点検に入る道は message_labels と customer_scores だけ」を、「112〜123行は leads も読む（scripts/check_priority_scoring_state.py:117）が、今の表の形では成り立たない式なので数に入るかは未確認。テスト用データが確実に入る道は message_labels・customer_scores で、どちらもテスト用データは入れない」に直す。
12. **小さな直し**: ①design.md:149 の「件数は上の範囲に入ったリードで数える」を「範囲に入り、回帰に使えたリード（§4-1 の空欄を外した後）で数える」に直す。②K5③（design.md:40）を §3-3 と同じ「書き込む日の2日前より後の時刻が 0件」にそろえる。③K4（design.md:39）に、UI の点検は `frontend/src/pages/**/*.tsx` だけを見る（docs/adr/ADR-144-ui-component-governance.md:43）ので、欄のファイルの置き場を実装カードで決め、点検の対象外なら PO の目視とレビューで金型を確かめる、と書き添える。④design.md:63 の webhook.py:694〜698 に「名前が取れたときの補い」と書き添える。

## 見張りに止められた文面

なし（この審査では止められなかった。旧 customers の表を消す migration は、表を消す語を命令に入れない検索 `git grep -ln '\bcustomers\b' origin/main -- migrations` で見つけた）。
