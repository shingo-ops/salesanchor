# review — リードのカルテで成約しやすさを分析する（設計 第2版の審査）

- 審査したもの: docs/handoff/lead-regression/design.md（第2版）・docs/handoff/lead-regression/recon.md
- 審査した枝の HEAD: 07252241fd98418c4c7199ab7c976dbdd7bf5e99（origin/release/lead-regression-recon と同じ）
- 照合の基準: origin/main 21f6a10fe42402559870d9fc5707374ffc3df656
- 審査役: Claude Opus（設計審査役）。本番には接続していない。本番の中身に関わることは「未確認」と書く。
- 判定: **REVISE**

行番号の書き方: 「ファイル:行」は origin/main の行。design.md と recon.md は HEAD 07252241f の行。

---

## 判定の理由（要約）

大筋（既存の表だけに入れる・目印を付ける・時刻を過去にして見張りを動かさない・消す順番を決める）は正しく組めている。ただし次の4点が残り、このままでは実装役が迷うか、K の判定が仕組みと関係なく × になる。

- (A) K5② が、自分で入れるテスト用データと矛盾する（入れれば必ず増える記録を「増えない」としている）。
- (B) §3-4 の優先度の点検の書き方が、今の表の形と合わない（請求書に lead_id が無い・deals は表ごと無い）。行ができる条件も「手で直したとき」だけではない。
- (C) §6-1 の消す手順に抜けがある（13表の外に残る行・13表の中の扱いの食い違い）。
- (D) K2 と K3 の作り方・数え方が未決で、同じ設計から別の答えが出うる。

---

## 項目1 引用 — △

ほとんどの引用は origin/main の行と合っている。合わないもの・弱いものは次の通り。

| design.md の場所 | 引用 | 照合結果 | 判定 |
|---|---|---|---|
| design.md:166 | backend/app/routers/webhook.py:815〜876 | 815行は空行。エコー受信の分かれ目の説明は 816行、条件は 817行（is_echo）。876行の会話の記録への書き込みは合う | × → 816 に直す |
| design.md:59 | backend/app/routers/webhook.py:853 | 853行は説明の行（inbound を2表に書く）。呼び出しは 854行の _persist_meta_message、meta_messages への書き込みの本体は 711〜722行 | △（854 か 711 の方が正確） |
| design.md:107 | backend/app/tasks/dashboard.py:62 | 62行は数える式の中の FROM leads。10分ごとの根拠は backend/app/celery_app.py:74〜77（schedule 600.0） | △（10分の根拠に celery_app.py:77 を足す） |
| design.md:108 | backend/app/tasks/priority_scoring_check.py（行なし） | 毎月1日 2:00 は backend/app/celery_app.py:124〜126 | △（行を付ける） |
| design.md:60 | backend/app/routers/webhook.py:876 | 876行で write_conversation_log を呼ぶ。○ | ○ |
| design.md:54 | backend/app/routers/leads.py:405 | POST /leads の入口。○。ただし Instagram・Facebook の受信で生まれるリードの本物の配線は webhook.py の _persist_meta_message（583行〜）と、エコー時の _create_outbound_lead_for_echo（536〜580行。leads と lead_channels を同時に書く 546〜574行） | △（項目2-5） |
| design.md:57 | backend/app/routers/leads.py:628 | 628行が deal_close_reasons への書き込み。○ | ○ |
| design.md:56・74 | backend/app/routers/leads.py:690・634 | 690行が選択の書き込み、634行が処理の始まり。○ | ○ |
| design.md:46 | backend/app/tasks/sa02_recon_monitor.py:127・126 | 126行の説明・127行の送信。○ | ○ |
| design.md:101 | sa02_recon_monitor.py:74 / translation_monitor.py:61 | 74〜75行 meta_messages を created_at で数える。83〜84行 conversation_logs を occurred_at・inbound で数える。translation_monitor.py:61 直近60分、73行 created_at。○ | ○ |
| design.md:102 | backend/app/tasks/avatar.py:317 | 317行で page_id が空なら飛ばす。○ | ○ |
| design.md:109 | backend/app/routers/customer_priority.py:58 | 58行は手で直す入口（POST /priority-score/override）。○。ただし行ができる入口はほかにもある（項目3-1） | △ |
| design.md:129 | migrations/20260715_100000_add_conversation_logs_lead_fk.sql:21 / backend/app/services/tenant.py:1025 | 21〜22行 ON DELETE RESTRICT、1025行 ON DELETE SET NULL。○ | ○ |
| design.md:136・140 | reactions 48行 / sales_form 60行 | 48行 CASCADE、60行 RESTRICT。○ | ○ |
| design.md:153 | migrations/003_add_phase1_tenant_tables.sql 78・97行、leads.py:469、webhook.py:577 | すべて合う。○ | ○ |
| design.md:71・73・76 | analytics.py:1747、lead.py:148・215、lead.py:31 | 合う。○ | ○ |
| design.md:58 | ADR-119 43行 | platform の値の行。○ | ○ |
| design.md:132 | ADR-1049 18行 | 13表の一覧の行。○ | ○ |
| recon.md の引用（1〜6節） | conv_logs.py:129・247、leads.py:494・800・1770・2406、analytics.py:963・984・1010・1813 など | 抜き取りで照合し、すべて合う | ○ |

## 項目2 DB の SSOT（配線の形・正本の欄） — △

正本の欄の選び方（initiative・channel_type・country・lead_sales_form_selections・temperature・status、返信の速さを leads に写さない）は正しい。ただし「本物の受け口がどの表に何を書くかに合わせる（design.md:50）」と言いながら、次の点で本物と形が違う。違うこと自体は目印のために要るが、設計に「ここは形を変える」と明記していない。

1. **WhatsApp の手入力の入口は external_message_id と raw_payload を書かない。** 書く欄は tenant_id・lead_id・company_id・channel_type・direction・content_text・occurred_at・recorded_by_user_id だけ（backend/app/routers/conv_logs.py:290〜295）。design.md:60 は WhatsApp の行に raw_payload の目印と external_message_id の `tlr-` を入れるとしており、本物の形と違う。
2. **Instagram・Facebook の受信の写し（conversation_logs）も raw_payload を渡さない。** 本物は write_conversation_log に tenant_id・lead_id・channel_type・channel_identity・direction・sender・content_text・external_message_id・occurred_at だけを渡す（backend/app/routers/webhook.py:876〜887）。書き込み関数は raw_payload を受け取れる（backend/app/services/conv_log_writer.py:43・71）が、受け口は使っていない。
3. **meta_messages の raw_payload の形も違う。** 本物の受信は timestamp・has_text・has_attachments の3つを入れる（backend/app/routers/webhook.py:704〜708）。アプリからの送信は raw_payload を書かない（backend/app/routers/leads.py:2092〜2101）。design.md:59 は全行に seed の目印を入れる。また本物は meta_messages の occurred_at を書かず（webhook.py:711〜722、leads.py:2092〜2101。送信は created_at に NOW()）、design.md:101 は occurred_at も入れる。
4. **deals は「書かない表」ではなく、表ごと無い。** 全テナントで表を消している（migrations/20260729_043520_drop_deals.sql:32）。統合の試験も消された表として扱う（backend/tests/test_lead_merge_pg.py:76〜78）。design.md:65・76・108・120 は deals を今もある表のように書いている。
5. Instagram・Facebook のリードの作られ方の根拠が POST /leads（leads.py:405）だけになっている。本物は受け口が leads と lead_channels を同時に書く（webhook.py:546〜574）。また本物は leads.type も書く（webhook.py:547・550）。design.md:71 は type を「入れない欄」としており、正本の決定（docs/specs/db-ssot/classification-master/design.md 42行）には合うが、本物の配線とは違う。どちらに合わせたかを書く必要がある。
6. 参考: 状態 existing_customer の説明は「成約済み・会社情報登録済み」（backend/app/schemas/lead.py:35）。テスト用の成約は companies を持たない（design.md:65）。design.md:65 は請求書の画面に出ないことだけを書いており、会社の画面にも出ないことは書いていない。

## 項目3 安全・副作用・テナント004/006 — △

- 004・006 に書かない作り（表名をテナント001に固定し、前後で数える。design.md:127・40）は ○。
- 時刻を2日以上前に明示して入れる（design.md:101）は、毎朝の突合（sa02_recon_monitor.py:74〜75・83〜84）と毎時の翻訳の見張り（translation_monitor.py:61・73）が数えない条件に合う。○
- page_id を空にする（design.md:102）は avatar.py:317 に合う。○
- 送信・翻訳の依頼は入口を通ったときだけ（webhook.py:924、conv_logs.py:129、leads.py:1770・2406）。表への直接の書き込みでは出ない。○

見落とし3件:

1. **customer_scores・message_labels は「手で直したとき」以外にもできる。** 優先度を見る入口（GET /leads/{lead_id}/priority-score、backend/app/routers/customer_priority.py:39〜55）は、まだ無ければ計算して保存する（backend/app/services/priority_scoring.py:372・384〜389・411）。その計算はやり取りに印を付けて message_labels に書く（priority_scoring.py:261・296）。印を見る入口（customer_priority.py:158〜178）も書く。手で直す入口も最初に計算を呼ぶ（customer_priority.py:87〜89）。今の画面から呼んでいるのは手で直す入口だけ（frontend/src/components/PriorityScoreOverride.tsx:54。frontend/src を git grep して priority-score の呼び出しはこれだけ）。design.md:109 は条件を「画面で手で直すと」だけにしている。
2. **画面で翻訳を押すと message_translations に行ができ、リードとも、やり取りとも結び付きの決まりが無い。** 画面の翻訳（frontend/src/pages/inbox/InboxMessageThread.tsx:350）は backend/app/routers/leads.py:1437 で message_translations に書く。この表は message_id を文字で持つだけで外部キーが無い（migrations/094_create_message_translations.sql:25〜33）。13表にも入っていない（ADR-1049 18行）。テスト用のやり取りで翻訳が押されると、消した後に残る。さらに Gemini の費用が出る（recon.md:97）。design.md は触れていない。
3. **毎月1日の優先度の点検は、今の表の形では数えられない可能性が高い（(B) の詳細は項目5）。** design.md:108 は「点検の数は変わらない」とするが、点検の式そのものが今の表と合わない。点検が失敗したときは Discord に知らせる（backend/app/tasks/priority_scoring_check.py:137〜140）。テスト用データが原因ではないが、K5 の「外へ何も起こさない」を確かめるときに、この知らせをテスト用データのせいと取り違えないよう記録が要る。本番で実際に失敗しているかは未確認。

## 項目4 消す手順（§6-1・K6） — ×

正しい点: 会話の記録の RESTRICT（20260715 migration:21〜22）・meta_messages の SET NULL（tenant.py:1025）・選択肢の RESTRICT（sales_form migration:60）に合わせた順番、リアクションの CASCADE（reactions migration:48）、先に数えて止める段（design.md:134）、消す手順を PO 本人が流すこと（design.md:154）は ○。

抜け・食い違い:

1. **13表の外に残る行。** message_translations（項目3-2。外部キー無し）が手順にも K6 の数える対象にも無い。leads を消しても残る。meta_message_reactions は CASCADE で消えるが、K6 の「消した後に数える」の対象に入っていない（design.md:41・141 は13表と選択肢だけ）。
2. **13表の中の扱いが2か所で食い違う。** 手順1は lead_attachments に1件でもあれば止める（design.md:134）のに、手順6は lead_attachments が一緒に消えるとする（design.md:139）。添付はリードを消すと CASCADE で消える（migrations/20260902_100000_create_lead_attachments.sql:60）が、表の行が消えても保存先のファイル（file_path、backend/tests/test_lead_merge_pg.py:246 の列）が残るかは未確認。止めるのか消すのかを1つに決める必要がある。
3. **quotes 等で止まる理由が書かれていない。** quotes と deal_close_reasons の外部キーは ON DELETE の指定が無く（migrations/20260721_100000_close_reasons_quotes_add_lead_id.sql:48・82）、companies・contacts も同じ（migrations/028_create_companies.sql:59、migrations/029_create_contacts.sql:32）。つまり1件でもあると leads を消す段で止まる。止める判断自体は正しいが、「止めた後に PO が何を決めるか（その行を消すのか、テスト用リードを残すのか）」が書かれていない。請求書は quotes を参照する（backend/app/services/tenant.py:864）ため、見積から請求書まで作られた場合の連鎖も書かれていない。
4. **customer_scores・message_labels の結び付き。** 「外部キーが無い」（design.md:109・135）は正しい（migrations/20260604_180000_analytics_agent_a_tables.sql:36〜37・67 は lead_id を INTEGER で持つだけ）。message_labels は message_id で meta_messages の id を指すので、手順2で lead_id で消せば足りる。○
5. **元の行が残ることの確かめ方。** K6 は「元の行の数が入れる前と同じ」（design.md:141）とするが、入れる前に数える表の一覧（13表＋選択肢＋reactions＋message_translations）を手順の前にも置いていない。

## 項目5 KGI K1〜K6 と K3 の統計 — ×

| K | 判定 | 根拠 |
|---|---|---|
| K1 | ○ | 件数と目印で数えられる（design.md:33）。lead_code の目印は VARCHAR(20)・テナント内で重複不可（migrations/003_add_phase1_tenant_tables.sql:78・97） |
| K2 | × | 作り方・数え方が未決（下の D-1） |
| K3a〜K3d | × | 項目の数・作り方・幅の出し方が未決。合格の幅の確率は下の D-2 |
| K4 | △ | 項目6 |
| K5 | × | ② が自分のデータと矛盾（下の A） |
| K6 | × | 項目4 |

### (A) K5② の矛盾

- K5② は「テナント001の Meta への送信の記録・翻訳の依頼が書き込み前後で増えない」（design.md:40）。
- ところが design.md:59 は「アプリからの送信」を meta_messages に入れる。本物のアプリの送信が書く記録はまさに meta_messages の outbound 行（backend/app/routers/leads.py:2070・2092〜2101）なので、「送信の記録」を meta_messages と読むと、テスト用データを入れた時点で必ず増え、K5② は必ず × になる。
- 「送信の記録」が何の表のどの行かを書いていない。実際に送れたとき・失敗したときの記録は監査の記録（backend/app/routers/leads.py:2133〜2135 の meta_message_sent、1982〜2053 の meta_message_send_failed。書き先は 2171〜2188 の record_audit_log）にある。翻訳の依頼の記録も、表の名前が無い（翻訳の結果は message_translations。migrations/094_create_message_translations.sql:25、backend/app/tasks/translation.py:74）。

### (B) §3-4 の優先度の点検の書き方

- 点検の数え方（scripts/check_priority_scoring_state.py:112〜123）は leads に invoices を i.lead_id で、deals を d.lead_id で結ぶ。
- invoices の表の定義に lead_id は無い（backend/app/services/tenant.py:860〜885。migrations を git grep しても invoices に lead_id を足すものは無い）。lead_id を持つ表は13表で、invoices は入っていない（ADR-1049 18行、backend/tests/test_lead_merge_pg.py:123〜143 の見張り）。
- deals は表ごと消されている（migrations/20260729_043520_drop_deals.sql:32）。
- したがって design.md:108 の「成約を請求書で、失注を deals で数える。テスト用データはどちらも持たないので、点検の数は変わらない」は、今の表の形と合わない。今の形のまま読むと、この式は数を返す前に止まる可能性が高い（本番の実際の列は未確認）。
- 同じ点検は message_labels の行数（check_priority_scoring_state.py:107）と customer_scores（同 142）も数える。項目3-1 のとおり、テスト用リードの優先度を見ると両方に行ができるので、「点検の数は変わらない」は条件付きでしか言えない。
- 較正の計算でも、成約は invoices を i.lead_id で結び（backend/app/services/priority_scoring.py:181〜185）、失注は leads.status = 'lost' で数える（同 204〜207）。テスト用の失注 280件は、message_labels ができれば較正の失注側に入る。

### (D-1) K2 の作り方・数え方が未決

1. 「こちらの最初の返信までの時間」の定義が無い。きっかけが「こちらから営業した（outbound）」リードは最初の1通がこちらなので、「相手の最初の受信 → こちらの最初の送信」の形では計算できない。K2 は「400件すべてで計算できる」とするので、outbound のリードの扱いを決めないと K2 は作り方次第で × になる。
2. 「相手の返信までの時間」（平均）の組み方（こちらの送信 → 次の相手の受信、の組ごとか）が書かれていない。
3. 読む時刻の欄が決まっていない。本物の meta_messages は受信も送信も created_at だけを持つ（webhook.py:711〜722、leads.py:2095・2100。本番の今の行も occurred_at が空 recon.md:99）。conversation_logs は occurred_at（突合も occurred_at を数える sa02_recon_monitor.py:83〜84）。design.md:101 は両方の欄に値を入れるが、計算がどちらを読むかを書いていない。K3d（小数4桁まで一致）にも効く。
4. 400件すべてが「受信と送信が少なくとも1通ずつ、順番どおりにある」ことを作り方の決まりとして書いていない。

### (D-2) K3 の作り方・数え方が未決、合格の幅の確率

1. 項目の数が合わない。K3a は「9項目（国・温度は比べる組ごと）」（design.md:35）、§2-1 は「14前後の幅」（design.md:45）。§3-2 の表は9行（design.md:85〜93）だが、温度は Hot・Warm・Cold で比べる組が2つ、国は使う国の数が設計のどこにも無い（組の数が決まらない）。
2. 作り方が未決: きっかけ・店舗の形・経路・国・温度の割合、返信の時間の分布、やり取りの回数の分布、失注理由の割り当て方。
3. 返信の速さを計算に入れる形が未決。仕込みは「1時間以内か」「平均6時間以内か」の2択（design.md:87〜88）だが、§4（design.md:113）は「返信の速さ」とだけ書く。続きの値で入れると、仕込んだオッズ比と比べられない。
4. 「成約がちょうど 120件になるよう基準の高さを合わせる」（design.md:81）のやり方が未決。毎回の基準の高さを合わせるのか、上位120件を成約にするのかで、データの作られ方がロジスティックの形から外れ、K3a の当たる割合が 95%から動きうる。
5. 95%の幅の出し方（Wald か、尤度の形から出すか）が未決。件数 400・成約 120 では出し方で当たる割合が変わりうる。
6. K3c の並べ替えで成約 120件を保つか、何回並べ替えるかは書いてある（200回）が、並べ替えの種の決め方が無い。

合格の幅の確率（python の二項分布で計算。1項目あたり 200回中の当たる回数を数える）:

| 真の当たる割合 | 182〜198回に入る確率（1項目） | 9項目同時 | 18項目同時 | 182回以上（K3c の形・1項目） | 9項目同時 | 18項目同時 |
|---|---|---|---|---|---|---|
| 0.95 | 0.9938 | 0.9453 | 0.8936 | 0.9942 | 0.9488 | 0.9002 |
| 0.94 | 0.9671 | 0.7403 | 0.5481 | 0.9672 | 0.7407 | 0.5486 |
| 0.93 | 0.8907 | 0.3528 | 0.1245 | 0.8907 | 0.3529 | 0.1245 |

- 仕組みが完全に正しくても、9項目なら約 5.5%、18項目なら約 10.6% の確率で K3a は × になる。
- 件数の少ない計算では、95%の幅が実際には 93〜94% しか当たらないことがある（一般的な性質。この設計の条件で何%になるかは未確認）。その場合、9項目同時の合格は 0.35〜0.74 まで下がり、仕組みの誤りと区別できない。
- 参考: 第1版の形（1回で14項目すべて当たる）は 0.95 の14乗で 0.4877。

## 項目6 画面（ADR-144・ADR-067・ADR-027） — ×

1. **「既存の属性ごとの成約率と同じダッシュボード」（design.md:114）の画面が見つからない。** frontend/src を git grep しても conversion-by-attribute を呼ぶ所は 0件（当たるのは backend/tests/test_analytics.py:665〜768 と文書だけ）。入口（backend/app/routers/analytics.py:1108）はあるが、画面は無い可能性が高い。足す場所（どの画面のどの部分か）を決め直す必要がある。
2. **ADR-144・ADR-067 を番号で引いていない。** K4（design.md:39）は「登録済みの金型・デザイントークン」と書くが、根拠の ADR（docs/adr/ADR-144-ui-component-governance.md、docs/adr/ADR-067-design-token-enforcement.md）と、自動の点検の名前（frontend/AGENTS.md:42 の npm run check:all）が無い。色のトークンを足すときは明暗の両方に足す決まり（frontend/AGENTS.md:40）も書かれていない。
3. **ADR-027（画面の文字は t() 経由・ja.json と en.json に同じキー）に触れていない。** frontend/AGENTS.md:21〜24。design.md:97・115 は「画面にもそう書く」とするが、その文と表の見出し・項目名を言語の辞書に入れることが K4 にも §4 にも無い。

## 項目7 第1版の指摘 (a)〜(h) の直り具合と新しい抜け — △

第1版の審査の記録（(a)〜(h) の中身）は、リポジトリの中にも、この枝の commit の説明（07252241f は「delete order, K3/K5 measures, dual-write wiring, citations」とだけ書く）にも無く、どれが (a)〜(h) のどれに当たるかは未確認。第1版 8422b3cbb と第2版 07252241f の差分から、直したものを照合した結果は次の通り。

| 第2版で直したもの（差分） | 直り具合 |
|---|---|
| 消す順番を決めた（§6-1 を新設） | △ 大筋 ○、抜けは項目4 |
| K3 を 200回の当たる割合などに分けた（K3a〜K3d） | △ 形は良くなったが未決が残る（D-2） |
| K5 の「見張りの知らせ 0件」を「当日の行 0件」に直した | ○（③。sa02_recon_monitor.py:126〜127 に合う）。ただし ② が新しく矛盾（A） |
| 受信が2表に書かれる配線を表に書いた（design.md:60・63・166） | △ 形の違いの明記が無い（項目2-1〜3）・行番号 815（項目1） |
| 失注理由（deal_close_reasons）を入れる表に足した | ○（lead.py:183、leads.py:628） |
| 引用を行番号付きに直した（analytics.py:963 → 1108、lead.py:28 → 148・215、ADR-108 の扱い） | ○ |
| recon の翻訳・送信の入口の記述を訂正（conv_logs.py:129、leads.py:2406） | ○ |
| 請求書・商談・会社・担当者の表を対象外と明記 | △ deals は表ごと無い（項目2-4） |
| §3-4 を新設（入れた後に変わること） | × 優先度の点検の記述が表と合わない（B）・行ができる条件の抜け（項目3-1） |

新しい抜け: (A)・(B)・message_translations（項目3-2・4-1）・既存画面の不在（項目6-1）・ADR-027（項目6-3）。

---

## 直す点

1. **§2 K5②（design.md:40）**: 「Meta への送信の記録」を「監査の記録のうち action が meta_message_sent・meta_message_send_failed の行（backend/app/routers/leads.py:2133〜2135・1982〜2053）」に、「翻訳の依頼」を「テナント001の message_translations の行数（migrations/094_create_message_translations.sql:25）」に書き換える。meta_messages の outbound 行はテスト用データで増えるものなので、② の数える対象から外すと明記する。
2. **§3-4 二つ目の文（design.md:108）**: 「成約を請求書で、失注を deals で数える…点検の数は変わらない」を消し、次の事実に置き換える: 点検の式（scripts/check_priority_scoring_state.py:112〜123）は invoices.lead_id と deals を使うが、invoices の定義に lead_id は無く（backend/app/services/tenant.py:860〜885）、deals は消されている（migrations/20260729_043520_drop_deals.sql:32）。本番でこの点検が今動いているかは読み取りの道で確かめる（未確認）。テスト用データが点検に入るのは message_labels（同 107行）と customer_scores（同 142行）に行ができたときだけ。行番号は 104〜126 ではなく 107・112〜123・142 を引く。
3. **§3-4 三つ目の文（design.md:109）**: 「画面で手で直すと」を「優先度を見る・印を見る・手で直す入口（backend/app/routers/customer_priority.py:39〜55・158〜178・58〜89）のどれかを通ると」に直す。今の画面から通るのは手で直す入口だけ（frontend/src/components/PriorityScoreOverride.tsx:54）と添える。
4. **§3-4 に1行足す**: 画面で翻訳を押すと message_translations に行ができ（backend/app/routers/leads.py:1437）、結び付きの決まりが無い（migrations/094_create_message_translations.sql:25〜33）ので一緒には消えない。押すと Gemini の費用が出る。
5. **§6-1（design.md:132〜141）**:
   - 手順2に message_translations（テスト用のやり取りの message_id `tlr-` で）を足す。
   - 手順1と手順6の lead_attachments の扱いを1つに決める（止めるなら手順6から外す。消すなら保存先のファイルの扱いを書く）。
   - 手順1に「止めた後に PO に何を聞くか」（その行を消すか、テスト用リードを残すか）と、quotes から invoices への連鎖（backend/app/services/tenant.py:864）を足す。止まる理由として、quotes・deal_close_reasons・companies・contacts の外部キーが ON DELETE 指定なし（migrations/20260721_100000_close_reasons_quotes_add_lead_id.sql:48・82、migrations/028_create_companies.sql:59、migrations/029_create_contacts.sql:32）と書く。
   - 手順8と K6（design.md:41）の数える対象に meta_message_reactions と message_translations を足し、入れる前にも同じ一覧で数える手順を手順0として置く。
6. **§3 の表（design.md:59・60）と §3-3（design.md:101）**: 目印のために本物の形を変える所を明記する。①WhatsApp の手入力の入口は external_message_id・raw_payload を書かない（backend/app/routers/conv_logs.py:290〜295）、②受信の写しも raw_payload を渡さない（backend/app/routers/webhook.py:876〜887）、③本物の meta_messages の受信の raw_payload は timestamp・has_text・has_attachments（webhook.py:704〜708）で、送信は raw_payload も occurred_at も書かない（leads.py:2092〜2101）。テスト用は seed の目印と occurred_at を足す、と「本物との違い」の列か注を立てる。
7. **deals の書き方（design.md:65・76・108・120）**: 「書かない表」「入れない欄」ではなく「表ごと消されている（migrations/20260729_043520_drop_deals.sql:32）」と書く。
8. **§2 K2（design.md:34）と §4（design.md:113）**: (i) こちらの最初の返信までの時間の定義（相手の最初の受信からこちらの最初の送信まで）と、outbound のリードの扱い（計算しない・別の定義にする・作り方で必ず相手から始める、のどれか）、(ii) 相手の返信までの時間の組み方、(iii) 読む欄（meta_messages は created_at、conversation_logs は occurred_at、など1つに）、(iv) 全リードに受信と送信が順番どおり1通以上ある作り方の決まり、を書く。outbound の扱いは推測で決めず PO に聞く項目として §8 に足す。
9. **§2 K3a〜K3d（design.md:35〜38）と §2-1（design.md:45）と §3-2（design.md:79〜97）**: (i) 使う国の一覧と割合、温度の比べる組（例: Warm 対 Hot・Cold 対 Hot）を決め、項目の数を1つの数で書き、§2-1 の「14前後」とそろえる。(ii) 各項目の割合・返信の時間の分布・やり取りの回数の分布・失注理由の割り当てを表にする。(iii) 返信の速さを2択で計算に入れると書く。(iv) 成約 120件の合わせ方を決める。(v) 95%の幅の出し方を決める。(vi) 合格の幅を項目の数に合わせて決め直す（上の表のとおり、0.95 が真でも 9項目で約 5.5%、18項目で約 10.6% は × になる。許す誤りの率を決めて、その率から1項目あたりの幅を逆算した数を書く）。(vii) K3d で読む欄を D-1 の (iii) と同じにする。
10. **§4 画面（design.md:114）**: 既存の成約率の画面が frontend に見つからない（frontend/src に conversion-by-attribute の呼び出し 0件）ことを書き、足す画面と場所を決め直す（決まらないなら §8 の未決に足す）。
11. **§2 K4（design.md:39）と §4**: 根拠に ADR-144・ADR-067・ADR-027 を番号で足し、自動の点検として frontend の npm run check:all（frontend/AGENTS.md:42）と、言語の辞書の点検（frontend/AGENTS.md:21〜24）を検証方法に足す。画面に出す注意書き（design.md:97・115）は t() のキーで ja・en の両方に入れると書く。
12. **§3 の leads の行（design.md:54）**: Instagram・Facebook のリードの本物の配線として webhook.py の _persist_meta_message（583行〜）と _create_outbound_lead_for_echo（536〜580行）を足し、本物は leads.type も書く（webhook.py:547・550）が正本の決定に合わせて書かない、と理由を書く。
13. **引用の直し**: design.md:166 の webhook.py:815 を 816 に。design.md:59 の webhook.py:853 を 854（または 711）に。design.md:107 に backend/app/celery_app.py:77 を、design.md:108 に backend/app/celery_app.py:126 を足す。
14. **§8 #5（design.md:155）**: PO に聞くとき、K2 の outbound の扱い（直す点8）と、画面の置き場所（直す点10）を同じ回で聞くと書き足す。
