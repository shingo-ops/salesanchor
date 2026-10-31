HEAD: 98afc111184ad80330435393f2283141b27f0835（origin/release/lead-regression-recon。指定どおり 98afc1111）
判定: REVISE

# review — リードのカルテで成約しやすさを分析する（設計 第3版の審査）

- 審査したもの: docs/handoff/lead-regression/design.md（第3版）・docs/handoff/lead-regression/recon.md
- 照合の基準: origin/main 0a48f81724570018c7db3800521f9f220701637e（design.md:10 の 0a48f8172 と同じ）
- 前回の審査: origin/release/lead-regression-design-v2-report の docs/handoff/lead-regression/review-design-v2.md（第2版 REVISE・直す点14件）
- 審査役: Claude Opus（設計審査役）。本番には接続していない。本番の中身に関わることは「未確認」と書く。
- 行番号の書き方: 「ファイル:行」は origin/main の行。design.md・recon.md は HEAD 98afc1111 の行。

## 判定の理由（要約）

第2版の直す点14件は、すべて直っている（項目1）。引用もほぼ実物と合う（項目2）。統計の組み立て（11項目・180〜198回・引き直し・ワルドの幅）は、自分で計算し直しても筋が通る（項目6）。

ただし次の4点が新しく見つかり、このままでは K の判定が仕組みと関係なく × になるか、実装役が迷う。

- (A) K5① は、本物が動いているテナント004の件数を「前後で同じ」とする。004 は本物の受信や操作で件数が自然に変わるので、テスト用データと関係なく × になりうる（項目4-1）。K6 の「元の行の数が同じ」も同じ形の弱さがある。
- (B) §6-1 の数える表に leads そのものが入っていない（ADR-1049 の13表は leads を含まない）。K1・K6 の数が数える表から出せない（項目5-1）。
- (C) §3 は「Instagram・Facebook は meta_messages に受信と送信がそろっている」とするが、本物のアプリ外の送信（エコー）は conversation_logs にしか書かれない。テスト用データでは困らないが、本物に切り替える（§9）ときに返信の時間がずれる。設計に限界として書かれていない（項目3-2）。
- (D) 分析に入れるリードの範囲（どの状態を成約・失注として数え、それ以外を外すか）が書かれていない。テナント001には元のリード id 4・6（状態 lead）があるので、K3d の「同じ計算」の範囲が決まらない（項目8-1）。

---

## 項目1 第2版の直す点14件 — すべて ○

| # | 直す点（第2版） | 判定 | 根拠 |
|---|---|---|---|
| 1 | K5② の数える対象 | ○ | design.md:40・49。audit_logs の action は backend/app/routers/leads.py:2135（meta_message_sent）、1984・2001・2031・2053（meta_message_send_failed）。書く関数は backend/app/routers/leads.py:2171 から backend/app/routers/leads.py:2182 で record_audit_log（backend/app/services/audit.py:277）を呼ぶ。meta_messages の送信の行を②から外すと明記（design.md:40） |
| 2 | §3-4 の優先度の点検 | ○ | design.md:120。scripts/check_priority_scoring_state.py:107・112〜123、backend/app/services/tenant.py:860〜885（invoices に lead_id なし）、migrations/20260729_043520_drop_deals.sql:32 と合う。customer_scores の行（scripts/check_priority_scoring_state.py:142）だけ行番号が無い（直す点8で補う） |
| 3 | 行ができる入口 | ○ | design.md:123。backend/app/routers/customer_priority.py:39〜55・58〜89（87〜89 で先に計算）・158〜178、frontend/src/components/PriorityScoreOverride.tsx:54 と合う。印付けは規則だけで外の費用は出ない（backend/app/services/priority_scoring.py:259〜261・296、source 'rule'） |
| 4 | 翻訳の行 | ○ | design.md:124。backend/app/routers/leads.py:1419・1437、migrations/094_create_message_translations.sql:25〜33（外部キーなし）と合う |
| 5 | §6-1 | ○ | design.md:170〜181。手順0、手順2 の message_translations、手順1 の止める条件と PO への質問、quotes→invoices（backend/app/services/tenant.py:864）、手順9 の reactions・translations。止まる理由は design.md:164。残る小さな抜けは項目5 |
| 6 | 本物との違いの列 | ○ | design.md:56〜66 に列を立てた。ただし列の中身に漏れがある（項目3-1） |
| 7 | deals の書き方 | ○ | design.md:72・120 は「表ごと消されている」と書く |
| 8 | K2 の決まり | ○ | design.md:128〜135（読む列・最初の返信・相手の返信の組み方・作り方の決まり・本物で組めないとき）。こちらから営業したリードの扱いは §8 #5 で PO に聞く（design.md:197） |
| 9 | K3 の未決 | ○ | 国（US・GB・AU）と温度の組（design.md:98〜101）、11項目に固定（design.md:47）、配分と時刻の作り方（design.md:88〜105）、2値で使う（design.md:104）、引き直し（design.md:106）、ワルド（design.md:140）、180〜198回（design.md:46）、K3d の読む列（design.md:38） |
| 10 | 画面の置き場 | ○ | design.md:147〜148。frontend/src で conversion-by-attribute の呼び出しが無いこと、置き場の案を §8 #5 に回した |
| 11 | K4 の ADR | ○ | design.md:9・39・150。frontend/AGENTS.md:21〜24・40・42 と合う |
| 12 | leads の行の配線 | ○ | design.md:58。ただし本物の受信の道も type を書くことが抜けている（項目2・項目3-1） |
| 13 | 引用の直し | ○ | design.md:63（webhook.py:854）、design.md:209（webhook.py:816〜887）、design.md:119（celery_app.py:75〜77）、design.md:120（celery_app.py:124〜126）。いずれも実物と合う |
| 14 | §8 #5 | ○ | design.md:197 に3つを1問で聞くと書いた |

## 項目2 ファイル:行 の引用 — △（ずれ3件・内容の抜け2件）

照合したもの（すべて origin/main）: webhook.py 536〜580・583〜725・816〜929、leads.py 405・465〜470・494・626〜636・686〜692・800・1419・1437・1770・1982〜2053・2092〜2101・2133〜2135・2171・2406、conv_logs.py 129・225〜320、conv_log_writer.py 31〜114、tenant.py 365・384〜385・798・835・860〜885・1022〜1054、schemas/lead.py 31・35・42・47・64・115・126・148・178〜189・215、analytics.py 963・984・986〜990・1010・1108〜1111・1747・1813、celery_app.py 74〜78・122〜127、dashboard.py 58〜64、sa02_recon_monitor.py 72〜86・125〜128、translation_monitor.py 59〜75、avatar.py 304〜318、priority_scoring.py 178〜210・255〜300・372・384〜389・411、customer_priority.py 36〜92・155〜180、audit.py 277、PriorityScoreOverride.tsx:52〜56、InboxKartePanel.tsx:590〜593、InboxMessageThread.tsx:350、DashboardPage.tsx:455〜480、migrations（003:78・97、094:25〜33、20260607:18、20260614:50〜62・86〜98、20260621:7、20260715:18〜23、20260721:48・82、20260729:32、20260902:58〜66・124〜128、20260927:46〜49、028:59、029:32、046:56・105〜107）、ADR-1049:18、ADR-119:43、classification-master design 42・48・101、conversation-unification design 4・17、design-regression 57・105、frontend/AGENTS.md 21〜24・40・42。recon.md の引用も抜き取りで照合し、すべて合う。

ずれ・抜け:

| design.md の場所 | 引用 | 実物 | 直し方 |
|---|---|---|---|
| design.md:143 | backend/app/routers/analytics.py:1108〜1110 に dashboard.view | 1108〜1110 は入口の宣言と応答の型。権限 dashboard.view は 1111行 | 1108〜1111 に直す |
| design.md:120 | customer_scores（行なし） | scripts/check_priority_scoring_state.py:142 | 142 を足す |
| design.md:121 | backend/app/services/priority_scoring.py:181〜185「請求書で成約」 | 183行は invoices を i.lead_id で結ぶ。invoices に lead_id は無い（backend/app/services/tenant.py:860〜885）ので、§3-4 の点検の式と同じく今の表の形と合わない | 「この式も invoices.lead_id を使い今の表と合わない（本番の動きは未確認）」と §3-4 と §10 に書き足す |
| design.md:58・211 | 本物で type を書くのはエコーの道（webhook.py:547・550）だけのように読める | 受信で新しいリードを作る道も type に 'Inbound' を書く（backend/app/routers/webhook.py:646〜656） | design.md:58 と §10（design.md:211）に webhook.py:646〜656 を足す |
| design.md:64 | 送信の page_id「本物は入る」 | 本物は messenger だけ入り、instagram は空（backend/app/routers/leads.py:2075〜2076） | 「messenger は入る・instagram は本物も空」に直す |

## 項目3 DB と配線の SSOT — △

### 3-1. 「本物との違い」の欄の漏れ

本物の書き込み（webhook.py・leads.py・conv_logs.py・conv_log_writer.py）と突き合わせると、次の違いが欄に無い。

1. **目印そのものが違いになっている行が「なし」になっている。** lead_channels の external_id は本物では相手の PSID（backend/app/routers/webhook.py:669・573）だが、テスト用は `tlr-`（design.md:62）。欄は「なし」。meta_messages の message_id（本物は Meta の id。backend/app/routers/webhook.py:860、backend/app/routers/leads.py:2083）、conversation_logs の external_message_id（本物は Meta の id。backend/app/routers/webhook.py:885）、leads の lead_code（本物は `LD-`。backend/app/routers/leads.py:469、backend/app/routers/webhook.py:577・673）も、見分け方の欄にはあるが違いの欄に無い。
2. **meta_messages の必須の列・本物が書く列の値が決まっていない。** sender_id は空を許さない（backend/app/services/tenant.py:1027 NOT NULL）。受信の本物は sender_id・original_language・attachment_url・attachment_type を書き（backend/app/routers/webhook.py:711〜721）、送信の本物は sender_id・recipient_id・messaging_type・message_tag を書く（backend/app/routers/leads.py:2092〜2101）。受信の sender_id は lead_channels の external_id と同じ値でないと、本物の受信の道（backend/app/routers/webhook.py:611〜619 の lead_channels で探す）と形がずれる。テスト用に何を入れるかが無い。
3. **conversation_logs の列。** 受信の写しの本物は channel_identity と sender に相手の id を入れ（backend/app/routers/webhook.py:881・883）、contact_id・company_id を補う（backend/app/services/conv_log_writer.py:68〜70）。WhatsApp の手入力の本物は recorded_by_user_id に入れた人を書く（backend/app/routers/conv_logs.py:293・306）。テスト用の値が無い。
4. **本物が同時に書く監査の記録を書かない。** WhatsApp の手入力の入口は会話の記録を書いたあと audit_logs に create の行を書く（backend/app/routers/conv_logs.py:310〜320）。直接書くテスト用データはこれを書かない。違いとして書く必要がある（K5② の数える action とは別なので矛盾はしない）。
5. **leads の type。** 受信の道も type を書く（項目2 の表）。

### 3-2. データを2か所に分ける箇所・読み先

- テスト用データの Instagram・Facebook の受信を meta_messages と conversation_logs の両方に入れるのは、本物の配線（backend/app/routers/webhook.py:854・876）と同じ形なので、新しい分散ではない。分析は meta_messages だけを読む（design.md:70）。○
- ただし design.md:70 の「受信と送信がそろっているのはこちらだけ」は本物では成り立たない。アプリからの送信は meta_messages だけ（backend/app/routers/leads.py:2092〜2101。git grep で leads.py に write_conversation_log の呼び出しは無い）、アプリ外の送信（エコー）は conversation_logs だけ（backend/app/routers/webhook.py:816〜851）。本物のリードでは、meta_messages だけを読むとエコーの送信が抜け、こちらの最初の返信までの時間が実際より長く出る。テスト用データは両方の形を作らないので K には効かないが、§9「本物に切り替える」の前に読み先を決め直す必要があることを、限界として §4-1 と §9 に書く必要がある。
- 仕込んだ値（§3-2 のオッズ比）を画面に並べる（design.md:149）とき、その値をどこに1つだけ持つかが書かれていない。画面と作り方の両方に同じ数を書くと、答えが2か所に分かれる（項目8-2）。

## 項目4 安全 — △

確かめて ○ のもの:

- 自動翻訳の依頼は、受け口（backend/app/routers/webhook.py:923〜929）・手入力の入口（backend/app/routers/conv_logs.py:129）・Discord の受け口からだけ出る（backend/app/services/inbound_translation.py:21）。直接の書き込みでは出ない。
- Meta への送信は入口（backend/app/routers/leads.py:1770・2406）を通ったときだけ。
- 毎朝の突合は当日の created_at・occurred_at だけを数え（backend/app/tasks/sa02_recon_monitor.py:74〜75・83〜84）、毎時の翻訳の見張りは直近の created_at だけを数える（backend/app/services/translation_monitor.py:61・73）。2日以上前の時刻なら数えない。
- 顔写真の取り直しは page_id が空なら飛ばす（backend/app/tasks/avatar.py:317）。
- celery の定期作業（backend/app/celery_app.py:67〜220）を全部見た。leads・meta_messages・conversation_logs を読むのは avatar・dashboard・sa02_recon_monitor・translation（見張り）だけ（backend/app/tasks を git grep）。reports・data_deletion は呼ばれたときだけ動く（定期の表に無い）。優先度の点検は §3-4 のとおり。
- DB トリガー: migrations と backend/app/services/tenant.py を git grep した。トリガーは updated_at を直すものと tenant_meta_config の同期（backend/app/services/tenant.py:1511）だけで、leads・meta_messages・conversation_logs・lead_channels・lead_sales_form_selections・deal_close_reasons には無い。pg_notify・LISTEN は 0件。
- テナント004・006 に書く道: 書き込みはテナント001の表名に固定（design.md:162）。分析の入口はテナントごと。○

見落とし:

1. **K5① はテスト用データと関係なく × になりうる。** K5①（design.md:40）は、テナント004・006 の §6-1 の数える表（audit_logs・meta_messages・conversation_logs など）の件数が前後で同じことを求める。004 は本物（recon.md:63・68）で、受信や人の操作で件数が増える。さらに毎日 4:00 に全テナントの 90日より古い audit_logs が消える（backend/app/celery_app.py:81〜82、backend/app/tasks/maintenance.py:112〜132）。件数の比較では、テスト用データのせいかどうかを区別できない。
2. **K5② も同じ消え方の影響を受けうる。** テナント001の audit_logs の2つの action の件数は、90日を過ぎた行があれば 4:00 に減る（backend/app/tasks/maintenance.py:129〜132）。テナント001にそういう行があるかは未確認。
3. **画面の欄は全テナントのダッシュボードに出る。** 新しい欄をダッシュボード（frontend/src/pages/dashboard/DashboardPage.tsx:466〜468 の下）に足すと、テナント004 の画面にも「件数が足りない」（design.md:142）の欄が出る。データには影響しないが、§5「対象: テナント001だけ」（design.md:154）と読み違いうる。ファネルの欄は切り替えの印で出し分けている（frontend/src/pages/dashboard/DashboardPage.tsx:462）。出し分けるか、全テナントに出すかを決める必要がある。
4. **人の操作で起きることの抜け。** テナント001の受信箱でテスト用リードに手で会話の記録（WhatsApp）を足すと、自動翻訳の依頼が出る（backend/app/routers/conv_logs.py:129）と audit_logs に行ができる（同 310行）。受信箱からテスト用リードへ送ろうとすると、送信の入口を通り、設定が無ければ meta_message_send_failed の行ができる（backend/app/routers/leads.py:1982〜2053）ので K5② が動く。§3-4 の「人の操作で行ができる道」（design.md:122〜124）に、この2つが無い。

## 項目5 消す手順 §6-1 — △

外部キーの消え方（origin/main）:

| 表 | leads を消したとき | 根拠 | §6-1 の扱い | 判定 |
|---|---|---|---|---|
| conversation_logs | 止まる（RESTRICT） | migrations/20260715_100000_add_conversation_logs_lead_fk.sql:21〜22 | 手順5で先に消す | ○ |
| meta_messages | lead_id が空になって残る（SET NULL） | backend/app/services/tenant.py:1025 | 手順4で先に消す | ○ |
| meta_message_reactions | meta_messages を消すと一緒に消える | migrations/20260927_100000_create_meta_message_reactions.sql:48 | 手順4 | ○ |
| deal_close_reasons・quotes・companies・contacts | 止まる（指定なし） | migrations/20260721_100000_close_reasons_quotes_add_lead_id.sql:48・82、migrations/028_create_companies.sql:59、migrations/029_create_contacts.sql:32、backend/app/services/tenant.py:446〜457・798・835 | 失注の理由は手順6、ほかは手順1で止める | ○ |
| lead_channels・lead_sales_form_selections・lead_attachments | 一緒に消える（CASCADE） | migrations/20260607_120000_create_lead_channels.sql:18、migrations/20260614_100000_create_sales_form_tables.sql:58、migrations/20260902_100000_create_lead_attachments.sql:60 | 手順7 | ○ |
| tenant_sales_form_options | 選択が残っていると止まる（RESTRICT） | migrations/20260614_100000_create_sales_form_tables.sql:60 | 手順8で最後 | ○ |
| message_translations・customer_scores・message_labels・outbound_translation_drafts・public.registration_tokens | 結び付きなし（残る） | migrations/094_create_message_translations.sql:25〜33、migrations/20260604_180000_analytics_agent_a_tables.sql:37・67、migrations/20260604_220000_create_translation_glossary.sql:109、migrations/20260604_080000_create_registration_tokens.sql:9 | 手順2・3 で消す、下書きと登録の印は手順1で止める | ○ |

元の行を消さないか:

- テナント001のリード id 4・6 は lead_code が `TLR-` ではない（採番は `LD-`。backend/app/routers/leads.py:469）ので、手順7 の条件に当たらない。○（本番の id 4・6 の lead_code の値は未確認。recon.md:111 は状態だけを書く）
- 既存のメッセージ4行（recon.md:68・99。すべて discord）は、手順4 が message_id `tlr-` かつテスト用リードの両方を条件にするので当たらない。○
- 手順2・3・6 はテスト用リードの id か `tlr-` が条件なので、元の行には当たらない。○
- 選択肢は入れる前に 0件（recon.md:70）で、手順8 は記録した id だけ。○

抜け:

1. **数える表に leads が無い。** design.md:170 の一覧は ADR-1049 の13表（docs/adr/ADR-1049-lead-merge-all-tables-and-fill-blanks.md:18。leads 自身は含まない）と5つの表で、leads が入っていない。K1（design.md:33）・K6（design.md:41）の数は leads から出す。
2. **元の行の確かめ方が件数だけ。** K6 は「元の行の数が手順0と同じ」とするが、入れてから消すまでの間に、人の操作や定期の作業（項目4-1・4-2）で件数は変わりうる。リード id 4・6 と既存のメッセージ4行は、id の一覧で残っていることを確かめる方が確実。
3. **添付のファイルの実体を消す手順が無い。** 手順1 は「消す場合はファイルの実体も消します」と PO に聞く（design.md:173）が、実体（attachments_data の置き場。migrations/20260902_100000_create_lead_attachments.sql:63・126）を消す手順が手順2〜9 に無い。
4. **旧 customers の表。** migrations/015_replace_customers_schema.sql:88 は lead_id に指定なしの外部キーを持つ customers を作る。新しいテナントの定義からは消した（backend/app/services/tenant.py:23・194）。テナント001に今もこの表があるか、確かめようとした検索の命令は見張りに止められた（最後の節）ので未確認。あれば手順1 の止める条件に入れる必要がある。

## 項目6 統計 — ○（小さな注意2件）

python3 で自分で計算した（標準ライブラリだけ。作業用の場所に置いた計算で、リポジトリには入れていない）。

1. **11項目の数**: 2値の項目 1〜4 で4つ、経路・国・温度がそれぞれ基準との組2つで6つ、回数1つ、合計11（design.md:90〜102）。基準（design.md:139）とも合う。○
2. **180〜198回**: 二項分布 n=200・p=0.95 で、片側 0.05÷11÷2 ≒ 0.227% 以下になる境は下 180・上 198。下に外れる確率 P(X≦179)=0.00116、上に外れる確率 P(X≧199)=0.00040。1項目で入る確率 0.99844、11項目同時 0.9829。当たる確率 0.94 で 0.9013、0.93 で 0.6249、0.92 で 0.2377。design.md:46 の数（0.12%・0.04%・98.3%・90.1%・62.5%・23.8%）とすべて一致。K3c（180回以上）も p=0.95 で 11項目同時 0.9873。○
3. **ワルドの幅が本当に 95%当たるか（設計の条件での試し）**: design.md:88〜106 の作り方（配分・オッズ比・基準の高さを合わせて成約ちょうど120件になるまで引き直す）を自前で組み、反復で解くロジスティック回帰とワルドの幅（±1.96×標準誤差）で 3000回試した。項目ごとの当たる割合は 0.940〜0.955（誤差の目安 ±0.004）、並べ替え（K3c の形）では 0.940〜0.956。この割合で K3a の合格の確率は約 0.970、K3c は約 0.977。設計の 98.3% より少し下がるが、正しい仕組みが × になる確率は 3%前後にとどまる。引き直しの回数の平均は 21.7〜22.2回（design.md:106 の「20回ほど」と合う）。statsmodels はこの環境に入っておらず、statsmodels の conf_int の既定（design.md:140）は確かめていない（未確認）。
4. **引き直しの方法**: 成約の合計は基準の高さ（切片）だけに関わる量なので、合計で条件を付けても項目ごとの強さの条件付きの分布は基準の高さに左右されない（ロジスティックの形の性質）。上の試しでも、推定の平均は仕込んだ値の 0.989〜1.036倍で、K3b の 0.90〜1.11 に十分入る（1500回試した。200回の平均のばらつきは対数で 0.017〜0.022）。○
5. **事象数/項目**: 120÷11 ≒ 10.9（design.md:47）。ただし §4-2 の「1つの項目につき成約が 10件以上」（design.md:142）は、「成約の件数÷項目の数」なのか「各項目の値ごとに成約 10件以上」なのかが読み分けられない。本物のデータで画面の出し分けに使うので、式で書く必要がある（直す点7）。
6. **返信時間の作り方と §3-2 の2値**: 最初の返信は 1〜59分か 61分〜48時間（design.md:104）で、1時間で2つに分ける決まりと矛盾しない。相手の返信は各返信を 5分〜6時間か 6時間1分〜72時間から取るので、平均は必ず決めた側に入る。こちらから営業したリードも、送信→受信→送信と並ぶので最初の受信のあとの送信がある（design.md:134、最少4回）。○
   - 注意: 2回目以降のこちらの送信の間隔、最初のメッセージの日時の範囲が決まっていない。K3d（小数4桁の一致）は2値しか使わないので効かないが、作り方を同じ種で再現するために実装カードで決める必要がある。
   - 注意: 項目11（回数1回ごと）は1回あたりの強さのばらつきが小さく（1回の推定で対数 0.025）、K3b の 0.90〜1.11 は約4倍の広さになり、偏りを見逃す力が弱い。合格の判定を壊すものではないので、記録だけ。

## 項目7 画面 §4-3 — △

- ADR-144（docs/adr/ADR-144-ui-component-governance.md）・ADR-067・ADR-027 と frontend/AGENTS.md:21〜24・34〜42 に、design.md:150 の書き方は矛盾しない。○
- 置き場の案（design.md:148）は実物と合う。frontend/src/pages/dashboard/DashboardPage.tsx:465〜468 が「今やること」の2つ（PriorityProspectsSection・WeeklyAdvisorSection）で、その下は固定の欄（同 469〜475）。○
- 表の金型は frontend/src/components/DataTable.tsx がある。ADR-144 は金型が無いときは実装を止めて PO に報告すると決めている（docs/adr/ADR-144-ui-component-governance.md:59〜64）。design.md:150 の「使う金型は実装カードで決める」に、この止め方を書き添えるとよい。
- 抜け: frontend/AGENTS.md:57〜64 のアイコンの決まり、同 67〜77 の E2E の更新の決まり（ダッシュボードの見本 frontend/tests-e2e/fixtures/mock-dashboard.json・frontend/tests-e2e/scene1-dashboard.spec.ts）が K4 にも §4-3 にも無い。UI の点検（docs/adr/ADR-144-ui-component-governance.md:41〜47 の scripts/check-ui-governance.js）も K4 の検証方法に無い。
- 全テナントに出るかどうか（項目4-3）。

## 項目8 新しい抜け・矛盾・不明点

1. **分析に入れるリードの範囲が無い。** 成約＝existing_customer、失注＝lost（design.md:83）とあるが、それ以外の状態のリードを外すとは書いていない。テナント001には状態 lead のリード id 4・6（recon.md:111）がある。K3d（design.md:38）の「同じ計算」が、本番では 402件、本番の外では 400件にならないよう、範囲を書く必要がある。
2. **仕込んだ値の置き場。** 画面に「仕込んだ値の列」（design.md:149）を出すには、どれがテスト用か・仕込んだ値がいくつかを画面か入口が知る必要がある。§3-2 の表と同じ数を画面の側にもう1つ書くと答えが2か所になる。作り方の定義（1か所）から入口が返す形にするのか、報告書だけに載せるのかを決める必要がある。
3. **K5① と K6 の測り方（項目4-1・5-2）。**
4. **旧 customers の表（項目5-4）。**
5. **実装カードに進めるか**: 上の (A)〜(D) と直す点を直せば進めると判断する。統計と消す順番の骨組みは固まっており、直す点はどれも書き足しで済む。PO への §8 #5 の質問は、第4版の審査が通ってから。

---

## 直す点

1. **§2 K5①（design.md:40）**: 「テナント004・006 の §6-1 の数える表の件数が前後で同じ」をやめ、「テナント004・006 の表に、テスト用の目印（lead_code `TLR-`・message_id／external_message_id／external_id `tlr-`）の行が 0件、かつ書き込みの間（始めた時刻〜終えた時刻）に作られた行が、書き込みの道具からは 0件」のように、テスト用データだけを数える形に直す。004 は本物が動いていて件数が自然に変わること（recon.md:63・68）、audit_logs が毎日 4:00 に 90日より古い行を消すこと（backend/app/tasks/maintenance.py:112〜132、backend/app/celery_app.py:81〜82）を理由に書く。
2. **§2 K5②（design.md:40）**: 件数の前後比較を「書き込みを始めた時刻より後に created_at がある行の数が 0件」に直す（90日の消し込みで減る分と区別するため）。
3. **§6-1 の数える表（design.md:170）と K6（design.md:41）**: 一覧に leads を足す。元の行は件数ではなく id の一覧（リード id 4・6、既存のメッセージ4行の id）で、手順0 と手順9 で同じことを確かめる形にする。
4. **§6-1 手順1・手順7（design.md:173・179）**: PO が「消す」と答えた場合に、添付のファイルの実体を消す手順（誰がどこで消すか。本番のファイルの操作は PO の GO が要る）を足す。旧 customers の表（migrations/015_replace_customers_schema.sql:88）がテナント001にあるかを読み取りの道で確かめ、あれば手順1 の止める条件に足す。
5. **§3 の表の「本物との違い」（design.md:58〜66）**: 項目3-1 の5点を足す。①目印（lead_code・message_id・external_message_id・external_id）を違いの欄にも書く ②meta_messages の sender_id（必須。受信は lead_channels の external_id と同じ値）・original_language・recipient_id・messaging_type・message_tag に何を入れるか ③conversation_logs の channel_identity・sender・contact_id・company_id・recorded_by_user_id に何を入れるか ④手入力の本物が書く audit_logs の create の行（backend/app/routers/conv_logs.py:310〜320）を書かないこと ⑤受信の道も type を書く（backend/app/routers/webhook.py:646〜656）。あわせて design.md:64 の page_id を「messenger は本物も入る・instagram は本物も空（backend/app/routers/leads.py:2075〜2076）」に直す。
6. **§3（design.md:70）・§4-1・§9（design.md:203）**: 「受信と送信がそろっているのは meta_messages だけ」を直し、「本物ではアプリからの送信は meta_messages だけ（backend/app/routers/leads.py:2092〜2101）、アプリ外の送信は conversation_logs だけ（backend/app/routers/webhook.py:816〜851）。テスト用データはアプリ外の送信を作らない。本物に切り替える前に、読み先を決め直す（会話の表の統合 docs/specs/db-ssot/conversation-unification/design.md を待つか、2表を合わせて読むか）」と限界を書く。
7. **§4-2（design.md:139・142）**: 分析に入れるリードの範囲を書く（例: 状態が existing_customer か lost のリードだけ。それ以外は外し、外した件数を出す）。「1つの項目につき成約が 10件以上」を式で書く（成約と失注の少ない方の件数 ÷ 項目の数 ≧ 10、など）。
8. **§3-4・§10（design.md:120〜121・210）**: 優先度の計算の成約の側（backend/app/services/priority_scoring.py:183）も invoices.lead_id を使っていて今の表と合わないことを書き足す。customer_scores の行番号 scripts/check_priority_scoring_state.py:142 を足す。
9. **§3-4 の人の操作の道（design.md:122〜124）**: ①テスト用リードに手で会話の記録を足すと自動翻訳の依頼と audit_logs の行ができる（backend/app/routers/conv_logs.py:129・310）②受信箱から送ろうとすると meta_message_send_failed の行ができ K5② が動く（backend/app/routers/leads.py:1982〜2053）、の2つを足し、PO への報告に「テスト用リードには送らない・記録を足さない」を足す。
10. **§4-3・§5（design.md:147〜150・154）**: 新しい欄が全テナント（004 を含む）のダッシュボードに出るのか、切り替えの印で出し分けるのか（例 frontend/src/pages/dashboard/DashboardPage.tsx:462 の形）を書く。決まらないなら §8 #5 の質問に足す。
11. **§4-3（design.md:149）**: 「仕込んだ値の列」の値をどこに1つだけ持つか（作り方の定義から入口が返す、または画面に出さず報告書だけに載せる）を決めて書く。
12. **§2 K4（design.md:39）と §4-3（design.md:150）**: 検証方法に UI の点検（scripts/check-ui-governance.js、docs/adr/ADR-144-ui-component-governance.md:41〜47）を足す。アイコンは frontend/src/constants/icons.tsx から使う決まり（frontend/AGENTS.md:57〜64）、ダッシュボードの E2E と見本（frontend/tests-e2e/scene1-dashboard.spec.ts・frontend/tests-e2e/fixtures/mock-dashboard.json）を同じ PR で直す決まり（frontend/AGENTS.md:67〜77）、金型が無いときは止めて PO に報告する決まり（docs/adr/ADR-144-ui-component-governance.md:59〜64）を書く。
13. **引用の直し**: design.md:143 の analytics.py:1108〜1110 を 1108〜1111 に。
14. **§3-2 の作り方（design.md:104）**: 2回目以降のこちらの送信の間隔と、最初のメッセージの日時の範囲（書き込む日の2日以上前に収まる範囲）を決める。実装カードに回すならそう書く。

## 見張りに止められた文面

旧 customers の表が今もあるかを確かめるため、migrations を git grep で検索しようとしたところ、次の文面で止められた（検索の命令の中に表を消す語が入っていたため）。言い換えての再実行はしていない。

```
PreToolUse:Bash hook error: [[ "$CLAUDE_CODE_REMOTE" = "true" ] || exit 0; exec bash "$CLAUDE_PROJECT_DIR/scripts/agent-hooks/cloud/dispatch.sh"]: BLOCKED(cloud): 'DROP TABLE' は不可逆操作です。クラウドでは行えません。手元で PO の承認を得て実行してください。
```
