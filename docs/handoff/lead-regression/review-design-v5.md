HEAD: 59b0c012e870b682a012f3cd1f60f956e973767d（origin/release/lead-regression-recon。指定どおり 59b0c012e）
判定: REVISE

# review — リードのカルテで成約しやすさを分析する（設計 第5版の審査）

- 審査したもの: docs/handoff/lead-regression/design.md（第5版）・docs/handoff/lead-regression/recon.md
- 照合の基準: origin/main 26dec7f26e2f1dd67e0d976f79649d7244f05a2a。design.md:10 の基準 27d1d6fbd から main は進んでいるが、その間の差分（git diff --stat 27d1d6fbd origin/main）は auth・passkey・LoginPage・bots.py・cloud-case-ai の文書などで、design.md が引くファイルは1つも含まない。したがって第5版の引用は今の main でも同じ行を指す
- 前回の審査: origin/release/lead-regression-design-v4-report の docs/handoff/lead-regression/review-design-v4.md（第4版 REVISE・直す点12件）
- 第4版との差分: git diff 1172ecd08 HEAD -- docs/handoff/lead-regression/design.md（40行足し・31行消し）
- 審査役: Claude Opus（設計審査役）。本番には接続していない。本番の中身に関わることは「未確認」と書く
- 行番号の書き方: 「ファイル:行」は origin/main の行。design.md・recon.md は HEAD 59b0c012e の行

## 判定の理由（要約）

第4版の直す点12件のうち11件は直っている。足した引用も、確かめた範囲ではすべて実物と合う（項目2）。統計（項目6）・画面の出し分けの事実（項目7）・消す手順の骨組み（項目5）も筋が通る。

ただし次の1点は、元からある行を消してしまう道なので、実装カードに進める前に直す必要がある。

- (A) **リードの統合の向きが実物と逆。** design.md:131 は「テスト用の行が元のリード（id 4・6）に付け替わる」とするが、本物の統合は「消える方」の状態が lead 以外なら断る（`backend/app/routers/leads.py:3102`〜3109、ADR-1049 22行）。テスト用リード 400件はすべて成約か失注なので、消える方にはなれない。起こり得るのは逆向きで、テスト用リードを残す方・元のリード（状態 lead。recon.md:111）を消える方にすると、元のリードの行がテスト用リードに付け替わり、元のリード 4・6 が消える。そのあと §6-1 手順5（design.md:197）は lead_id がテスト用リードの conversation_logs を消すので、元のリードの会話の記録まで消える。手順1（design.md:193）の止める条件はこの向きを見ていない。

このほか、本物との違いの欄の漏れが2つ（leads.created_at、受信の翻訳の行）と、K6 の audit_logs の数え方で統合の記録が漏れる点がある（項目3・4）。どれも書き足しで直せる。

---

## 項目1 第4版の直す点12件

| # | 直す点（第4版） | 判定 | 根拠 |
|---|---|---|---|
| 1 | leads の customer_name・meta_messages の platform・写しの original_language | ○ | design.md:61（customer_name を `TLR-00001` 形式、本物との違い③）、design.md:66・67（platform はリードの channel_type と同じ値）、design.md:68（写しの original_language は空）。根拠の行は実物と一致（`backend/app/services/tenant.py:359`・1026、`backend/app/routers/webhook.py:543`・641〜643・681〜688・628、`backend/app/services/conv_log_writer.py:75`〜78） |
| 2 | 本物との違い⑦と限界の言い換え | ○ | design.md:67 ⑦、design.md:74（「アプリの外からの送信（エコー。こちらから営業したリードの最初の送信を含む）」）。根拠 `backend/app/routers/leads.py:1887`〜1896、`backend/app/services/messaging_window.py:145`〜146、`backend/app/routers/webhook.py:816`〜851・536〜550 と一致 |
| 3 | §3-2 の時刻（最初の受信のあとの最初の送信を #3 から取る） | ○ | design.md:109 の (1)(2)。§4-1 design.md:141 と食い違わない。こちらから営業したリードの最初の送信＝最初のメッセージの日時も明記 |
| 4 | K5①(a) 流す前の機械点検と理由 | ○ | design.md:40 ①(a)、理由 design.md:52（`migrations/20260614_100000_create_sales_form_tables.sql:89` を引く） |
| 5 | K5② をテスト用データに関わる行に絞る | ○ | design.md:40 ②、理由 design.md:53（`backend/app/routers/leads.py:1986`・2137、`backend/app/services/inbound_translation.py:21`〜27。Discord から呼ばれることは backend/app/discord_gateway/ticket_channel_writer.py が inbound_translation を読み込むことで確かめた） |
| 6 | リードの統合の道（§3-4・§6-1 手順1） | × | 書き足しはある（design.md:131・133・193）が、付け替わる向きが実物と逆（`backend/app/routers/leads.py:3102`〜3109。項目4-3・直す点1） |
| 7 | ①conv_log_<id> を消す ②audit_logs の扱い ③テスト用リードの id の一覧 | ○ | ① design.md:193（id の記録）・194（手順2）・130 ② design.md:188・41 ③ design.md:192（RETURNING）・201（手順9）。ただし②の数え方に統合の記録が入らない（項目4-4・直す点3） |
| 8 | 画面の出し分けの事実 | ○ | design.md:161〜165・170・218④。事実は実物と一致（項目7） |
| 9 | 旧 customers の根拠と外部キーの一覧 | ○ | design.md:190・192（項目5） |
| 10 | 「テスト用」の注意書きの出し先 | ○ | design.md:114・159・182（テナント001の報告書にだけ書く。「目印で、原因ではない」は全テナント） |
| 11 | §3-4 の優先度の点検の言い過ぎ | ○ | design.md:125（`scripts/check_priority_scoring_state.py:107`・117・142 と一致） |
| 12 | 小さな直し4つ | ○ | ① design.md:152 ② design.md:40 ③（「書き込む日の2日前より後」）③ design.md:39（pages/**/*.tsx だけ・置き場は実装カード・対象外ならレビューと目視）④ design.md:65（「694〜698行は名前が取れたときの補い」） |

## 項目2 第5版で足した・直した引用の照合

照合した引用（すべて origin/main で行の中身を見た）:

| design.md の行 | 引用 | 結果 |
|---|---|---|
| 61 | `backend/app/services/tenant.py:359`（customer_name NOT NULL）・365（type は空を許す） | ○ |
| 61 | `backend/app/routers/webhook.py:536`〜580・547〜550・569〜574・543・577・641〜643・680〜689・628・646〜656・673 | ○（680 は注釈の行で、書き込みは 681〜688。ずれは小さい） |
| 65 | webhook.py:669・694〜698・573 | ○ |
| 66 | `backend/app/services/tenant.py:1026`・1027、webhook.py:611〜619・736・854・711〜721・704〜708 | ○ |
| 67 | `backend/app/routers/leads.py:2092`〜2101・2071・2083・2075〜2076・1887〜1896、`backend/app/services/messaging_window.py:141`〜149・145〜146、webhook.py:816〜851 | ○ |
| 68 | `backend/app/services/conv_log_writer.py:75`〜78・68〜70・43・71、webhook.py:876〜887・881・883・885 | ○ |
| 69 | `backend/app/routers/conv_logs.py:225`・290〜295・306・310〜320 | ○ |
| 40・53 | leads.py:1986・2137、conv_logs.py:149、inbound_translation.py:21〜27 | ○ |
| 51・188 | `backend/app/celery_app.py:80`〜82、`backend/app/tasks/maintenance.py:112`〜132 | ○ |
| 130 | conv_logs.py:129・141〜143・147〜159・310〜320 | ○ |
| 131 | leads.py:3226〜3232、docs/adr/ADR-1049-lead-merge-all-tables-and-fill-blanks.md 18行 | 行は ○。ただし中身の読み方が違う（ADR-1049 22行・leads.py:3102 の決まりを落としている。直す点1） |
| 39 | docs/adr/ADR-144-ui-component-governance.md 41〜47・43・134行、frontend/AGENTS.md 42・21〜24・57〜64・67〜77行 | ○ |
| 162 | `frontend/src/pages/dashboard/DashboardPage.tsx:462`、`frontend/src/api/funnel.ts:23`〜27 | ○ |
| 163 | `frontend/src/components/FeatureGate.tsx`・`frontend/src/hooks/useFeatures.ts`（どちらも実在）、`backend/app/routers/roles.py:148`〜156。FeatureGate を使う画面 0件（git grep で本体以外 0件）、tenant_features を backend/app で読むのは2か所（backend/app/auth/dependencies.py 672行・roles.py 150行） | ○ |
| 166 | docs/adr/ADR-144-ui-component-governance.md 59〜64行、frontend/AGENTS.md 40行 | ○ |
| 190 | migrations/20260601_140000_drop_customers_tables.sql 8〜14行（customers_legacy_{schema_name} を含む） | ○ |
| 193 | migrations/20260902_100000_create_lead_attachments.sql 60行（ON DELETE CASCADE）・63行（file_path）・126行（attachments_data） | ○ |
| 125 | scripts/check_priority_scoring_state.py 107・112〜123・117・142行 | ○ |
| 40・51・53・148 | recon.md:63・68・99・111 | ○ |

ずれの一覧: 中身として違うのは design.md:131 の統合の向き（直す点1）だけ。行番号のずれは design.md:61 の「680〜689」（680 は注釈）の1件で、直さなくてよい程度。

## 項目3 DB と配線の SSOT

1. **必須の列と本物の書き込み**: 各行の入れる値は必須の列を満たす（leads.customer_name `backend/app/services/tenant.py:359`、meta_messages.platform・sender_id 同 1026・1027、conversation_logs の channel_type・direction・occurred_at は NOT NULL で、テスト用データは入れる migrations/20260604_090000_create_conversation_logs.sql 41〜53行）。○
2. **customer_name の TLR-00001**（design.md:61 ③）: 本物の2つの道の値と、'Messenger User'／'Instagram User' を使わない理由（取り直しの条件 `backend/app/routers/webhook.py:628`）が書かれている。○
3. **こちらから営業したリードの最初の送信が受信より前**（design.md:67 ⑦）: 本物のアプリが断ること・本物はエコーで conversation_logs だけに入ることが書かれている。○。補足（直す点5）: 本物のエコーの道は、Instagram のエコーでも leads.channel_type と lead_channels.platform を 'messenger' に固定して書く（`backend/app/routers/webhook.py:557`・573。呼び出しは platform を渡さない 824〜829行）。本物のこちらから営業した Instagram のリードは channel_type が 'messenger' になる形で、§10 に記録しておくとよい（今回のテスト用データは channel_type を正しく instagram にするので K には効かない）。
4. **本物との違いの漏れ（×・直す点2）**:
   - (a) leads.created_at（DEFAULT NOW() `backend/app/services/tenant.py` の leads の定義、355行から始まる CREATE TABLE の created_at）。何も書かなければテスト用リードは書き込んだ日に作られたことになり、やり取り（70〜180日前）より後になる。本物はリードが最初のメッセージのとき（受信の道 webhook.py:646〜656、エコーの道 547〜550）に作られる。値を決めるか、本物との違いに書く必要がある。§3-4 のダッシュボード（10分ごとの作り直し）で「新しいリード」として数えられるかにも関わる（ダッシュボードが leads.created_at を読むかは未確認）。
   - (b) 受信の翻訳。本物の Instagram・Facebook の受信は自動翻訳の依頼を出し（`backend/app/routers/webhook.py:923`〜929）、本物の WhatsApp の手入力の受信は翻訳して conversation_logs の translated_text・original_language を書き戻し、message_translations に `conv_log_<id>` の行を作る（`backend/app/routers/conv_logs.py:326`〜327・147〜173）。テスト用データはどれも作らない（§3-3 design.md:120 に「通らない」とはあるが、§3 の本物との違いの欄に無い）。design.md:57 の「本物と形が違うところは全部書く」に合わせ、meta_messages（受信）と conversation_logs（WhatsApp）の行に足す。
5. **データを2か所に分ける箇所**: 新しい写しの表は無い。Instagram・Facebook の受信が meta_messages と conversation_logs の両方にあるのは本物の配線（webhook.py:854・876）に合わせたもので、分析は経路ごとに1つの表だけを読む（design.md:73）。返信の速さは leads に写さない（design.md:72）。○

## 項目4 安全（K5・K6・人の操作の道）

1. **K5①(a)**（design.md:40）: 書き込み先の表名が `tenant_001.` で始まる・他テナントの名前・public の表名・search_path の切り替えが 0件を、流す前に文字で点検する形。目印の無い表（design.md:52）を守るのに筋が通る。public.tenant_features の1行は名前付きの例外にすると書いてある（design.md:164）。○
2. **K5①(b)**: テナント004・006 を目印の行で数えるので、004 の受信や人の操作で増える行には左右されない。○
3. **K5②**: 送信の記録は action と new_data の lead_id（`backend/app/routers/leads.py:1986`・2137）、翻訳の記録は `tlr-` と `conv_log_<id>`（`backend/app/routers/conv_logs.py:149`）で絞るので、テナント001の Discord の翻訳や元のリード 4・6 への送信には左右されない。audit_logs の毎日の消し込みは 90日より古い行だけ（`backend/app/tasks/maintenance.py:129`〜132）で、書き込みの直後に数える行は消されない。○
4. **K5③**: 「書き込む日の2日前より後が 0件」で §3-3 とそろった。○。ただし leads.created_at は数える対象に無い（項目3-4(a)。毎朝の突合 `backend/app/tasks/sa02_recon_monitor.py:74`〜88 は leads を数えないので K5③ そのものは成り立つ）。
5. **K6 の audit_logs**（design.md:41・188・201）: 消さずに件数を報告する形は、監査の記録の役目と 90日の消し込みに合う。ただし「new_data の lead_id がテスト用リードの id の行」で数えると、統合の記録が漏れる。統合は action が merge_absorb（record_id は残す方の id、new_data は統合のまとめ）と merge_delete（record_id は消える方の id、new_data は merged_into と reason）で書かれ（`backend/app/routers/leads.py:3278`〜3289）、new_data に lead_id のキーが無い。table_name が leads で record_id がテスト用リードか元のリードの id の行も数える（直す点3）。
6. **人の操作の道 §3-4**（design.md:127〜133）: 優先度・翻訳・会話の記録を手で足す・送ろうとする、は実物と合う。**統合の道は向きが違う（×・直す点1）**:
   - 本物の統合は、消える方の状態が lead 以外なら 400 で断る（`backend/app/routers/leads.py:3102`〜3109、docs/adr/ADR-1049-lead-merge-all-tables-and-fill-blanks.md 22行）。テスト用リードはすべて existing_customer か lost なので、消える方にはなれない。テスト用リードどうしの統合もできない。
   - 起こり得るのは、テスト用リードを残す方（状態は問わない ADR-1049 22行・leads.py:3241）、元のリード 4・6（状態 lead。recon.md:111）を消える方にする統合。このとき元のリードの13表の行がテスト用リードへ付け替わり、元のリードは消える（leads.py:3237〜3249）。
   - その後 §6-1 を流すと、手順5（design.md:197）が lead_id がテスト用リードの conversation_logs を消すので、付け替わった元のリードの会話の記録も消える。meta_messages は手順4 が `tlr-` に絞るので元の行は消えないが、手順7 でリードが消えると持ち主が空になる（`backend/app/services/tenant.py:1025`）。どちらも K6 の「元の行は1行も消えない」を破る。
   - 手順1（design.md:193）の止める条件「元のリードに `tlr-` の行がある・元のリードの件数が増えた」はこの向きを見つけられない（元のリードそのものが無くなるため）。
   - 人が画面でテスト用リードの状態を lead に戻した場合だけは、設計の書いた向き（テスト用リードが消える方）も起こり得る。

## 項目5 消す手順 §6-1

| 点 | 判定 | 根拠 |
|---|---|---|
| 手順0 のテスト用リードの id の記録（RETURNING） | ○ | design.md:192 |
| 外部キーの一覧（pg_catalog.pg_constraint）と表の一覧の突き合わせ | ○ | design.md:190・192。一覧に無い表で止める決まりもある |
| 手順1 の統合の兆しで止める | × | 項目4-6。元のリード 4・6 が残っているか、手順0 で記録した元の meta_messages・conversation_logs の行の lead_id が今も 4・6 か、を見る条件が無い（直す点1） |
| 手順2 の conv_log_<id> の翻訳を消す | ○ | design.md:193（id を記録）・194。キーの形は `backend/app/routers/conv_logs.py:149` と一致 |
| 手順9 の id の一覧で数える形 | ○ | design.md:201 |
| audit_logs を消さず件数を報告し 90日で消える | ○（数え方は直す点3） | design.md:188、`backend/app/tasks/maintenance.py:112`〜132 |
| customers の表が無い根拠 | ○ | migrations/20260601_140000_drop_customers_tables.sql 8〜14行で customers・customers_legacy_{schema_name} を含む6表を全テナントから取り除く。本番の検索（design.md:190）は名前が customers と同じ表だけで、customers_legacy_tenant_001 のような名前は当たらない形だが、手順0 の外部キーの一覧で拾えるので妥当。本番の検索結果そのものは未確認（審査役は本番に接続していない） |

補足: 手順0（design.md:192）の元の行の一覧に、元の行の lead_id も一緒に記録すると、直す点1 の止める条件にそのまま使える。

## 項目6 統計（§3-2・§3-3・K3d・§4-2）

- 時刻の作り方（design.md:108〜109）: 受信後の最初の送信は #3 の範囲（1〜59分か 61分〜48時間）、ほかの送信は直前の受信から 5分〜24時間、相手の返信はすべて #4 の範囲（5分〜6時間 か 6時間1分〜72時間）。#3 は §4-1（design.md:141）の「最初の受信のあとの最初の送信」と同じものを指し、#4 の平均は「すぐ前がこちらの送信である受信」（design.md:142）だけで、こちらから営業したリードの最初の送信の後の受信もこれに入る。2つに分けた値が必ず決めた側に入る。○
- 1リード最長: 間は最長 72時間・最多 19個で 57日。最初のメッセージは 180〜70日前なので、最後のメッセージは少なくとも 13日前で、design.md:109 の「10日以上前」（多めに見た 60日で計算）も §3-3 の「2日以上前」も満たす。○
- 交互に並べ、4〜20回なので、どちらの始まり方でも「受信→送信」「送信→受信」が1組以上ある（design.md:143）。K2 の空欄は出ない。○
- K3d: 本番・本番の外とも §4-1 と同じ列（meta_messages.created_at・conversation_logs.occurred_at）を読み、元のリード 4・6 は状態 lead で §4-2 の範囲から外れる（design.md:148、recon.md:111）ので、どちらも 400件で計算する。○
- §4-2 の件数の決まり: 「範囲に入り、回帰に使えたリードで数える」（design.md:152）。○

## 項目7 画面 §4-3

- 注意書き: 「成約しやすさの目印で、原因ではない」などは全テナントに出し、「テスト用」はテナント001の報告書だけ（design.md:159・114）。○
- 出し分けの手段の事実: FUNNEL_MODE は画面を作るときの設定 VITE_FUNNEL_DASHBOARD（`frontend/src/api/funnel.ts:23`〜27）で、テナントごとには変えられない。FeatureGate と public.tenant_features（`backend/app/routers/roles.py:148`〜156）はテナントごとに変えられるが、書く画面・入口は無い（backend/app で tenant_features を読むのは backend/app/auth/dependencies.py 672行と roles.py 150行だけ、書く所は 0件）。design.md:162〜163 と一致。○
- テナント001だけに出すなら public.tenant_features に1行が要り、K5①(a) の名前付きの例外・§6-1 で消すか残すかを決める（design.md:164）。○
- K4（design.md:39）: UI の点検の対象は `frontend/src/pages/**/*.tsx` の変更ファイルだけ（docs/adr/ADR-144-ui-component-governance.md 43行・134行）。ADR-144 は CI で全部は保証せず「対応表とコードレビューで補う」（同 128行）としているので、対象外に置くときにレビューで金型の使用を確かめ PO の目視と合わせる形は ADR-144 と矛盾しない。金型が無いときは止めて PO に報告（同 59〜64行・design.md:166）も合う。色トークンの明暗両方（frontend/AGENTS.md 40行、ADR-067）、t() と ja・en（frontend/AGENTS.md 21〜24行、ADR-027）、アイコン（同 57〜64行）、E2E（同 67〜77行）も矛盾しない。○。補足: 既存の並びの欄 PriorityProspectsSection は frontend/src/pages/dashboard/PriorityProspectsSection.tsx にあり、同じ置き場にすれば UI の点検の対象に入る。「レビュー」をだれが行うか（審査役か）は design.md:39 に書かれていない（直す点4。小さな点）。

## 項目8 新しい抜け・矛盾・不明点と §8

- 新しい抜け: 統合の向き（直す点1）、本物との違いの漏れ2つ（直す点2）、K6 の audit_logs の数え方（直す点3）、エコーの道の Instagram の固定値の記録（直す点5）。
- 不明点（未確認のまま残してよいもの）: テナント001の Meta の設定で送信が成功するか（design.md:132）、ダッシュボードが leads.created_at を読むか、本番の優先度の点検の動き（design.md:125）。
- §8 の PO に聞く点（design.md:218）: ①K の測り方の再確認（KGI の承認者として PO が要る）②こちらから営業したリードの「最初の返信」の測り方 ③欄の置き場 ④全テナントに出すか、public の表に1行書いて001だけに出すか。どれも事業・承認の判断で、技術で決められる点は入っていない。#4（design.md:217）は既存の委譲の決まりに合わせた手順の記録で、新しく聞く点ではない。○
- 実装カードに進めるか: 直す点1 は元のリードの会話の記録を消す道を塞ぐもので、§6-1 の消す手順の中身に関わるため、このままでは APPROVE しない。直す点1〜3 を書き足せば、次の版で APPROVE できる見込み（ほかの骨組みは今回の照合で崩れていない）。

## 直す点

1. **統合の向き（design.md:131・133・193・197）**: §3-4 の統合の項目を実物に合わせて書き直す。「本物の統合は消える方の状態が lead 以外なら断る（`backend/app/routers/leads.py:3102`〜3109、docs/adr/ADR-1049-lead-merge-all-tables-and-fill-blanks.md 22行）ので、テスト用リード（成約・失注）は消える方になれず、テスト用リードどうしの統合もできない。起こり得るのは、テスト用リードを残す方、元のリード 4・6 を消える方にする統合で、元のリードの行がテスト用リードへ付け替わり、元のリードが消える。人がテスト用リードの状態を lead に戻した場合だけ、逆向きも起こる」。§6-1 手順0 で元の meta_messages・conversation_logs（ほか元のリードに結び付く行）の id と lead_id を記録し、手順1 の止める条件に「元のリード 4・6 が残っていない」「手順0 で記録した元の行の lead_id が 4・6 でなくなっている」「audit_logs に merge_absorb・merge_delete の行（record_id がテスト用リードか 4・6）がある」を足す。逆向き（テスト用の行が元のリードに付く）の今の条件も残す。手順5 を流す前にこの条件で止まることを書き、K6 の「元の行は1行も消えない」との結び付きを §6-1 に書く。
2. **本物との違いの漏れ（design.md:61・66・69）**: ① leads に「created_at（DEFAULT NOW()）に入れる値」を決めて書く（推奨: 最初のメッセージの日時。本物はリードが最初のメッセージのときに作られる webhook.py:646〜656・547〜550）。NOW() のままにするなら本物との違いに書き、§3-4 にダッシュボードの数への影響を書く。updated_at も同じ扱いを決める。② meta_messages（受信）の本物との違いに「自動翻訳の依頼を出さない（本物は出す `backend/app/routers/webhook.py:923`〜929）」、conversation_logs（WhatsApp）の本物との違いに「受信の翻訳をしないので translated_text・original_language は空で、message_translations の `conv_log_<id>` の行も無い（本物は作る `backend/app/routers/conv_logs.py:326`〜327・147〜173）」を足す。
3. **K6・§6-1 の audit_logs の数え方（design.md:41・188・201）**: 報告する件数に「table_name が leads で record_id がテスト用リードか元のリード 4・6 の id の行（統合の merge_absorb・merge_delete は new_data に lead_id を持たない `backend/app/routers/leads.py:3278`〜3289）」と「table_name が conversation_logs で new_data の lead_id がテスト用リードの行（手入力の create `backend/app/routers/conv_logs.py:310`〜320）」も含める、と書く（後者は今の「new_data の lead_id」で拾えるが、表の名前で分けて報告すると読みやすい）。
4. **K4 のレビュー役（design.md:39。小さな点）**: 点検の対象外に置く場合に金型の使用を確かめる人を「設計審査役（Opus）がレビューで確かめる」と名前で書く。置き場を既存の並びと同じ frontend/src/pages/dashboard/ にすれば UI の点検の対象に入ることも書き添えるとよい。
5. **§10 の記録（design.md:226〜232。小さな点）**: 本物のエコーの道は Instagram のエコーでも leads.channel_type と lead_channels.platform を 'messenger' に固定して書く（`backend/app/routers/webhook.py:557`・573・824〜829）、を見つけた食い違いとして足す。本物に切り替える前（§9）の読み先の決め直しに関わる。

## 見張りに止められた文面

なし（この審査では止められなかった）。
