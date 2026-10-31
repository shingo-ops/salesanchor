<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# design — リードのカルテで成約しやすさを分析する（テナント001のテスト用データ）

**日付**: 2026-10-31（第4版。第3版 98afc1111 の設計審査 REVISE・直す点14件を受けて直した。審査の全文は origin/release/lead-regression-design-v3-report の docs/handoff/lead-regression/review-design-v3.md。第2版の審査は origin/release/lead-regression-design-v2-report の review-design-v2.md）  
**状態**: 設計の下書き。KGI 承認済み（K2・K3・K5・K6 は第2〜4版で測り方を直したため PO の再確認が要る。§8 #5）・設計審査 第3版 REVISE・PO 実装承認 なし・実装 未着手。本番への書き込みは一切していない。  
**下調べ**: `docs/handoff/lead-regression/recon.md`  
**対象ADR**: ADR-015（リードの土台・返信速度）、ADR-119（lead_channels）、ADR-109（状態の不変コード）、ADR-1049（lead_id を持つ13表）、ADR-1024（本番の読み取り専用の道）、ADR-144（UI ガバナンス・金型）、ADR-067（デザイントークン）、ADR-027（画面の文字は t() 経由）  
**基準**: origin/main 0a48f8172 で照合  
**先行の同じ計算**: docs/handoff/accuracy-measurement/design-regression.md（標準ライブラリだけの自前の計算を statsmodels 0.15.0 と小数4桁で突き合わせる型。57行・105行）

## 0. PO の決定（原文のまま）

- 2026-10-31「1」: 先に下調べ。
- 2026-10-31 方針: 本物の記録が無いならテナント001にテスト用データを入れる。推測禁止・配線と DB の SSOT 厳守・データの分散禁止・画面はデザイントークンと金型を守る・分からないことは聞く。
- 2026-10-31「2」: Instagram・Facebook のやり取りは、決まった入口を通さずやり取りの表に直接書く。
- 2026-10-31「テストデータなのでテナント001では今回は許可する」。
- 2026-10-31「1」: KGI 6つを承認。
- 2026-10-31「1」: シュリンクの扱い・扱う商材は今回は外す。
- 2026-10-31「目的がはっきり決定していない場合は推測で進めない」。

## 1. 目的（PO にとって何が変わるか）

広告でリードが増える前に、「どんなリードが成約しやすいか」「返信の速さで成約が変わるか」を画面で見られる仕組みを用意する。今は本物の成約が 0 件なので、答えが分かっているテスト用データで、仕組みが正しく答えを出すかを先に確かめる。

## 2. KGI・KPI

K1・K4 は PO 承認（2026-10-31「1」）の中身のまま、確かめ方だけ細かくした。K2・K3・K5・K6 は測り方を直した（理由は §2-1。PO の再確認 §8 #5）。

| # | 基準 | 検証方法 |
|---|---|---|
| K1 | テナント001にテスト用リード 400件（うち成約 120件・失注 280件）が入り、400件すべてに目印（lead_code が `TLR-`）がある | 読み取りの道で、目印付きの件数 400・状態 existing_customer 120・lost 280 |
| K2 | テスト用リード 400件すべてで、§4-1 の決まりの「こちらの最初の返信までの時間」と「相手の返信までの時間の平均」が計算できる | 分析の入口の結果で、2つの値の空欄が 0件 |
| K3a | 計算の正しさ（本番の外）: 同じ作り方で乱数の種を 200通り変えたデータで、11項目（§3-2）それぞれ「95%の幅が仕込んだ値を含む回数」が 180〜198回 | 200回分の結果表で項目ごとに数え、11項目すべて範囲内で ○ |
| K3b | 偏りが無い: 同じ 200回で、11項目それぞれの推定の平均（対数で平均して戻す）が仕込んだ値の 0.90倍〜1.11倍 | 200回分の平均を §3-2 の表と突き合わせ、11項目すべて範囲内で ○ |
| K3c | 壊れた仕組みを見逃さない: 成約の印だけを無作為に並べ替えた 200回分で、11項目それぞれ「幅が差なし（1）を含む回数」が 180回以上 | 並べ替えた 200回分の結果表で数え、11項目すべて 180以上で ○ |
| K3d | 本番に入れた後も同じ答え: 本番のテナント001から分析の入口で計算した11項目の推定値と幅が、本番の外で同じ種から同じ計算をした値と小数4桁まで一致 | 2つの結果表を突き合わせ、11項目すべて一致で ○。どちらも §4-1 と同じ時刻の列を読む |
| K4 | ダッシュボードに結果の表が出る。部品はすべて登録済みの金型とデザイントークンだけ（ADR-144・ADR-067）。アイコンは `frontend/src/constants/icons.tsx` からだけ使う（frontend/AGENTS.md 57〜64行）。画面の文字はすべて t() 経由で ja・en 両方にある（ADR-027） | PO が画面で目視 ○×／`npm run check:all`（frontend/AGENTS.md 42行）が通る／i18n の点検（frontend/AGENTS.md 21〜24行）が通る／UI の点検 `scripts/check-ui-governance.js`（docs/adr/ADR-144-ui-component-governance.md 41〜47行）が通る／ダッシュボードの E2E（`frontend/tests-e2e/scene1-dashboard.spec.ts`・見本 `frontend/tests-e2e/fixtures/mock-dashboard.json`）を同じ PR で直して通る（frontend/AGENTS.md 67〜77行） |
| K5 | テスト用データが外へ何も起こさない: ①テナント004・006 の §6-1 の数える表に、テスト用の目印（lead_code `TLR-`、message_id・external_message_id・external_id `tlr-`）の行が 0件 ②テナント001の「Meta への送信の記録」（audit_logs の action が meta_message_sent・meta_message_send_failed）と「翻訳の記録」（message_translations）のうち、書き込みを始めた時刻より後に created_at がある行が 0件 ③テスト用の行のうち、meta_messages の created_at・conversation_logs の occurred_at と created_at が書き込む日以降のものが 0件 | 読み取りの道で、書き込みの直後に数える（ai_ro に tenant_001__audit_logs・tenant_001__message_translations があることを 2026-10-31 15:13 JST に確認済み）。書き込みを始めた時刻は実行の記録に残す。②の meta_messages の送信の行は、テスト用データ自体が入れるので②には含めない |
| K6 | 消す手順を流すと、テスト用の行が §6-1 の表すべてで 0件になり、元からある行は1行も消えない | §6-1 手順0 で元の行の id の一覧（leads・meta_messages・conversation_logs・tenant_sales_form_options）を記録し、手順9 で同じ id がすべて残っていることを突き合わせる。テスト用の行は目印とテスト用リードの id で数えて 0件 |

### 2-1. K2・K3・K5 を直した理由

- K3（第1版の審査）: 「1回のデータで、仕込んだ項目すべての 95%の幅が当たる」は、正しい仕組みでも半分ほど × になる。そこで 200回作って当たる回数を見る形にした。
- K3 の合格の幅（第2版の審査）: 幅が当たる回数は「200回・確率 0.95」の二項分布に従う。11項目のどれか1つでも外れたら × なので、11項目まとめて「正しい仕組みを誤って × にする確率」を 5%以下にするよう、1項目あたりの許す確率を 5% ÷ 11 ≒ 0.45% にした（ボンフェローニの補正）。この条件で幅を計算すると 180〜198回（下に外れる確率 0.12%・上に外れる確率 0.04%）。正しい仕組み（当たる確率 0.95）なら 11項目すべて合格する確率は 98.3%。当たる確率が 0.94 なら 90.1%、0.93 なら 62.5%、0.92 なら 23.8% まで下がる（計算は 2026-10-31 に標準の Python で二項分布の確率を足し上げた）。少し幅が狭くなる程度の計算のずれなら合格し、大きくずれたら × になる。
- 項目の数（第2版の審査）: 第2版は「9項目」と「14前後」が食い違っていた。第3版は §3-2 の表の 11項目に固定した（国・温度は比べる組ごとに数える）。成約 120件 ÷ 11項目 ≒ 10.9 で、「1項目につき成約 10件以上」（§4-2）を満たす。
- K5（第1版の審査）: 毎朝の突合は差が無くても毎日 Discord に送る（`backend/app/tasks/sa02_recon_monitor.py:127`）ので「知らせ 0件」は守れない。テスト用の行が数えられないこと（③）で測る。
- K5②（第2版の審査）: 「送信の記録」「翻訳の依頼」が何を数えるか決まっておらず、テスト用データ自体が meta_messages に送信の行を入れるので矛盾していた。数える表と列を上の表のとおり固定した。送信の記録は `backend/app/routers/leads.py:2133`〜2135（成功時 meta_message_sent）と同じ関数の失敗時（meta_message_send_failed）で audit_logs に書かれる（書く関数は `backend/app/services/audit.py:277`）。翻訳の記録は message_translations（migrations/094_create_message_translations.sql 25〜33行）。
- K2（第2版の審査）: 時間の測り方と、こちらから営業したリードの扱いが決まっていなかった。§4-1 で決めた。
- K5①・K5②・K6（第3版の審査）: 第3版は「件数が前後で同じ」で測っていた。しかしテナント004は本物が動いていて、受信や人の操作で件数が自然に変わる（recon.md 63行・68行）。さらに毎日 4:00 に全テナントの 90日より古い audit_logs が消える（`backend/app/celery_app.py:80`〜82、`backend/app/tasks/maintenance.py:112`〜132）。件数の比較では、テスト用データのせいかどうかを区別できない。そこで ①は目印の行が 0件か、②は書き込みを始めた時刻より後の行が 0件か、K6 は元の行の id が全部残っているか、で測る形にした。

## 3. 何を入れるか（SSOT: 既存の表だけに入れる。新しい写しの表は作らない）

本物の受け口がどの表に何を書くかに合わせる（配線の SSOT）。本物と形が違うところは「本物との違い」の欄に全部書く。

| 表 | 入れるもの | 本物の配線（根拠） | 本物との違い | 消すときの見分け方 |
|---|---|---|---|---|
| leads | 400件。状態（成約 120・失注 280）、initiative、channel_type、country、temperature | 作る入口 `backend/app/routers/leads.py:405`（type も書ける）。Instagram・Facebook の本物は、受信で `backend/app/routers/webhook.py:583` から始まる _persist_meta_message がリードを作り（646〜656行。type に 'Inbound'、status に 'lead' を書く）、アプリ外の送信（エコー）では `backend/app/routers/webhook.py:536`〜580 の _create_outbound_lead_for_echo が leads（547〜550行。type に 'Inbound' を書く）と lead_channels（569〜574行）を書く | ①type を書かない（空のまま。列は空を許す `backend/app/services/tenant.py:365`）。本物は受信の道もエコーの道も 'Inbound' を書くが、type は initiative に統合して廃止と決まっている（docs/specs/db-ssot/classification-master/design.md 42行）ので、本物の古い書き方には合わせない ②lead_code が `TLR-00001` 形式（本物は `LD-` と id。`backend/app/routers/leads.py:469`、`backend/app/routers/webhook.py:577`・673） | lead_code が `TLR-00001` 形式（§8 #3） |
| tenant_sales_form_options | テナント001の店舗の形の選択肢（テナント004と同じ5つ） | 選択肢はテナント004にだけ入っている（`migrations/20260614_100000_create_sales_form_tables.sql:89`） | なし | 入れた行の id を記録する |
| lead_sales_form_selections | 400件それぞれの店舗の形（1つ） | カルテの入力画面の書き先（`backend/app/routers/leads.py:690`） | なし | テスト用リードを消すと一緒に消える（`migrations/20260614_100000_create_sales_form_tables.sql:58`） |
| deal_close_reasons | 失注 280件それぞれの主な理由 1件 | 失注は主な理由 1件が必須（`backend/app/schemas/lead.py:183`）。書き先 `backend/app/routers/leads.py:628` | なし | テスト用リードの id（リードを消すと止まる決まり。§6-1） |
| lead_channels | Instagram・Facebook のリードの経路 1件。external_id は `tlr-psid-00001` 形式（リードごとに1つ） | platform は messenger / instagram / discord だけ（docs/adr/ADR-119-lead-channels-and-lead-merge.md 43行）。WhatsApp は入れない。本物は受信の道（`backend/app/routers/webhook.py:669`・694〜698）とエコーの道（573行）で書く | external_id が `tlr-psid-` 形式（本物は相手の PSID） | external_id が `tlr-` で始まる（一緒に消える `migrations/20260607_120000_create_lead_channels.sql:18`） |
| meta_messages（受信） | Instagram・Facebook の受信。sender_id はそのリードの lead_channels.external_id と同じ値（必須の列 `backend/app/services/tenant.py:1027`。本物の受信の道は lead_channels をこの値で探す `backend/app/routers/webhook.py:611`〜619）。original_language は本物と同じ関数 infer_original_language で本文から決める（`backend/app/routers/webhook.py:736`）。attachment_url・attachment_type は空（添付なしの本物と同じ） | `backend/app/routers/webhook.py:854` の _persist_meta_message が書く（列は 711〜721行）。raw_payload は timestamp・has_text・has_attachments の3つ（704〜708行） | ①message_id が `tlr-` 形式（本物は Meta の id）②sender_id が `tlr-psid-` 形式（本物は相手の PSID）③page_id を空にする（本物は入る。毎日の顔写真の取り直しを止めるため §3-3）。raw_payload は本物と同じ3つのキーだけで、目印のキーは足さない | message_id が `tlr-` で始まる（本物は Meta の id が必ず入る） |
| meta_messages（送信） | アプリからの送信。sender_id は `tlr-page`（必須の列）、recipient_id はそのリードの lead_channels.external_id、messaging_type は 'RESPONSE'、message_tag は空（24時間以内の本物の組 `backend/app/services/messaging_window.py:142`〜149） | `backend/app/routers/leads.py:2092`〜2101（列）・2071（sender_id は本物ではページの id か Instagram の事業者 id）。raw_payload と occurred_at は書かない。created_at は NOW() | ①message_id が `tlr-` 形式（本物は Meta の id `backend/app/routers/leads.py:2083`）②sender_id が `tlr-page`（本物はページの id）③created_at を書き込む日の2日以上前にする（本物は今の時刻）④page_id を空にする（本物は messenger は入る・instagram は本物も空 `backend/app/routers/leads.py:2075`〜2076）⑤sent_by_staff_id を空にする（本物は送った人）⑥24時間を過ぎた送信も 'RESPONSE'・タグ空にする（本物は 24時間を過ぎると 'MESSAGE_TAG'・'HUMAN_AGENT' になるか、期限切れで送れない `backend/app/services/messaging_window.py:141`〜148。分析では読まない列） | message_id が `tlr-` で始まる |
| conversation_logs（Instagram・Facebook の受信の写し） | 上の受信と同じもの。channel_identity・sender は受信の sender_id と同じ値（本物と同じ `backend/app/routers/webhook.py:881`・883）。contact_id・company_id は空（本物の書く関数が補う値 `backend/app/services/conv_log_writer.py:68`〜70 は、テスト用リードに会社・担当者が無いので本物でも空になる） | `backend/app/routers/webhook.py:876`〜887 の write_conversation_log（raw_payload は渡さない。書く関数は受け付ける `backend/app/services/conv_log_writer.py:43`・71行） | ①external_message_id が `tlr-` 形式（本物は Meta の id `backend/app/routers/webhook.py:885`）②created_at を occurred_at と同じ過去の時刻にする（本物は今の時刻） | external_message_id が `tlr-` で始まる |
| conversation_logs（WhatsApp の受信と送信） | WhatsApp のやり取り。company_id は空（テスト用リードは会社を持たない）。recorded_by_user_id は空 | 手入力の入口 `backend/app/routers/conv_logs.py:225`。書く列は 290〜295行（external_message_id・raw_payload は書かない）。入口は書いたあと audit_logs に create の行を書く（310〜320行） | ①created_at を occurred_at と同じ過去の時刻にする（本物は今の時刻）②recorded_by_user_id を空にする（本物は入れた人 306行）③audit_logs の create の行を書かない（本物は書く。K5② の数える action とは別） | lead_id がテスト用リード（本物の形に合わせ、目印の列は書かない） |

- メッセージの行の目印は、本物が必ず書く列（message_id・external_message_id）にだけ付ける。第2版で raw_payload に足すとしていた目印は、本物の形と違うのでやめた。本物が目印の列を持たない WhatsApp の行は、テスト用リードの id で見分ける（会話の記録はリードと結び付く決まりがあり、リードを残したまま持ち主が変わることは無い §6）。
- 返信の速さは「やり取りの表の受信と送信の時刻」から計算する。リードの表へ写して持たない（データを2か所に分けない）。
- 読む表は経路ごとに1つ: Instagram・Facebook は meta_messages。WhatsApp は conversation_logs（ほかに書き先が無い）。Instagram・Facebook の写しは本物の配線に形を合わせるためだけに入れ、分析では読まない。
- 限界（本物に切り替える前に直す）: 本物では、アプリからの送信は meta_messages だけに書かれ（`backend/app/routers/leads.py:2092`〜2101。leads.py に write_conversation_log の呼び出しは無い）、アプリの外から送った返信（エコー）は conversation_logs だけに書かれる（`backend/app/routers/webhook.py:816`〜851）。そのため本物のリードで meta_messages だけを読むと、アプリの外からの返信が抜け、こちらの最初の返信までの時間が実際より長く出る。テスト用データはアプリの外からの送信を作らないので K には効かない。本物に切り替える前（§9）に、会話の表の統合（docs/specs/db-ssot/conversation-unification/design.md）を待つか、2つの表を合わせて読むかを決め直す。
- 会話の表を1つにまとめる作業は途中（docs/specs/db-ssot/conversation-unification/design.md 4行・17行）。まとまったら分析の読み先もそこへ移す。
- 書かない表: invoices（請求書）・companies・contacts・quotes。deals は表そのものが消されている（migrations/20260729_043520_drop_deals.sql 32行）。成約済みは本来「入金の確認で自動に切り替わる」（docs/specs/db-ssot/classification-master/design.md 48行）が、テスト用の成約 120件は請求書も会社も持たない。そのため、請求書を数える画面（売上・入金）と会社の画面にはテスト用の成約は出ない。今回の分析は leads の状態だけを使うので影響しない。

### 3-1. どの欄に入れるか（正本の確認）

| 分析に使う項目 | 入れる欄（正本） | 根拠 | 入れない欄 |
|---|---|---|---|
| 相手から来たか・こちらから営業したか | leads.initiative（inbound / outbound） | docs/specs/db-ssot/classification-master/design.md 42行（type は initiative に統合して廃止。PO 確定 2026-07-13）。`backend/app/routers/analytics.py:1747` も initiative を使う | leads.type |
| 経路 | leads.channel_type（instagram / messenger / whatsapp）。Instagram・Facebook は lead_channels にも 1件 | channel_masters の6つ（下調べ §4）。lead_channels の platform は ADR-119 43行 | — |
| 国 | leads.country に2文字の国コード（US・GB・AU） | 国の台帳 public.countries の code CHAR(2)（migrations/20260621_010000_create_countries_master.sql 7行）。国コードとして読むのは `backend/app/schemas/lead.py:148`・215行 | 国名の文字 |
| 店舗の形 | lead_sales_form_selections（選択肢は tenant_sales_form_options） | カルテの入力画面が書く先（`frontend/src/pages/inbox/InboxKartePanel.tsx:592`、`backend/app/routers/leads.py:634`）。複数選択はコードの説明（`backend/app/schemas/lead.py:179`）と ADR-1049 の13表の一覧にある | leads.sales_form（§10） |
| 温度 | leads.temperature（Hot / Warm / Cold） | `backend/app/schemas/lead.py:47` | — |
| 成約したか | leads.status（成約 existing_customer・失注 lost） | `backend/app/schemas/lead.py:31`（ADR-109） | — |
| 返信の速さ・やり取りの回数 | Instagram・Facebook は meta_messages.created_at、WhatsApp は conversation_logs.occurred_at から計算（§4-1） | 上の §3 | leads.response_speed・first_response_at |

### 3-2. 仕込む傾向と配分（K3 の答え合わせの表）

各項目は互いに無関係に割り振る（項目どうしの重なりを作らない）。数は 400件に対する割合で、端数は乱数の種で決める。

| # | 項目（比べ方） | 配分 | 仕込む強さ（オッズ比） |
|---|---|---|---|
| 1 | 相手から来た（inbound）／こちらから営業（outbound） | 半々 | 2.0 |
| 2 | 店舗の形が卸／それ以外4つ | 卸 30%・残り4つを 17.5%ずつ | 2.5 |
| 3 | こちらの最初の返信が1時間以内／1時間より遅い | 半々 | 1.8 |
| 4 | 相手の返信の平均が6時間以内／6時間より遅い | 半々 | 1.6 |
| 5 | 経路が WhatsApp／Facebook（messenger） | 3つの経路を 1/3ずつ | 1.5 |
| 6 | 経路が Instagram／Facebook | （同上） | 1.0（仕込まない） |
| 7 | 国が GB／US | 3か国を 1/3ずつ | 1.0（仕込まない） |
| 8 | 国が AU／US | （同上） | 1.0（仕込まない） |
| 9 | 温度が Hot／Cold | 3つを 1/3ずつ | 1.0（仕込まない） |
| 10 | 温度が Warm／Cold | （同上） | 1.0（仕込まない） |
| 11 | やり取りの回数（1回増えるごと） | 4〜20回から等しい確率で | 1.0（仕込まない） |

- 返信の速さ（#3・#4）は「1時間以内か」「6時間以内か」の2つに分けた値で仕込み、分析でも同じ2つに分けて使う。時刻は、決めた側の範囲から作る（1時間以内なら 1〜59分、遅いなら 61分〜48時間。相手の返信は、6時間以内の組なら各返信を 5分〜6時間、遅い組なら 6時間1分〜72時間から取り、平均が必ず決めた側に入るようにする）。
- 時刻の範囲（第3版の審査 直す点14）: 最初のメッセージの日時は、書き込む日の 180日前〜70日前から等しい確率で取る。こちらの2回目以降の送信は、すぐ前の受信から 5分〜24時間で取る（#3・#4 の2値には使わない）。1つのリードは最長 20回 × 72時間 = 60日に収まるので、最後のメッセージも書き込む日の 10日以上前になり、§3-3 の「2日以上前」を必ず満たす。乱数の種と時刻の作り方は実装カードで固定し、同じ種で同じデータが再現できることを試験で確かめる。
- 失注の理由: 失注 280件に、テナント001の失注理由の選択肢 15個（下調べ §4）を番号順に繰り返し 1件ずつ割り当てる（280 ÷ 15 で 18〜19件ずつ）。分析には使わない。
- 成約をちょうど 120件にする方法: 項目を割り振った後、仕込んだ強さで各リードの成約の確率を計算し、平均がちょうど 120件になる基準の高さを求める。成約するかを乱数で決め、合計がちょうど 120件になるまで成約するかの乱数だけを引き直す（項目はそのまま）。引き直した回数を記録する。合計が 120±9.2件ほどに散らばるので、平均で 20回ほどの引き直しになる。合計で条件を付けても、項目ごとの強さの推定は変わらない（成約の合計は基準の高さだけに関わるため）。正しいかは K3a〜K3c で実際に確かめる。
- K3a〜K3c は本番に入れる前に本番の外で確かめる。1つでも × なら本番には入れず、結果を PO に報告する。
- 1回のデータ（400件）では、強さが小さい項目（1.5 など）は「差がある」と言い切れないことがある。これは件数の限界で、仕組みの誤りではない。画面には推定の幅を出し、仕込んだ値との答え合わせは報告書で行う（§4-3）。
- これは「計算と画面が正しく動くか」を確かめるためのもので、本物の傾向ではない。画面と報告にもそう書く。

### 3-3. 自動で動くものを止める条件（下調べ §6 の事実）

- 時刻（meta_messages の created_at、conversation_logs の occurred_at・created_at）は、すべて書き込む日の2日以上前の値を明示して入れる。meta_messages の occurred_at は本物と同じく空にする。→ 毎朝の突合（meta_messages は created_at、conversation_logs は occurred_at で当日の行を数える。`backend/app/tasks/sa02_recon_monitor.py:74`）と、毎時の翻訳の見張り（直近60分。`backend/app/services/translation_monitor.py:61`）が数えない。
- page_id は空にする → 毎日の顔写真の取り直しが Meta に問い合わせない（`backend/app/tasks/avatar.py:317`）。
- 送信の入口・受け口・翻訳の依頼の入口は通らない → Meta への送信・自動翻訳の費用は出ない（下調べ §6）。

### 3-4. 入れたあとに変わること（止めない・知っておくこと）

- テナント001のダッシュボードの数字（10分ごとに作り直す。`backend/app/celery_app.py:75`〜77、`backend/app/tasks/dashboard.py:62`）に、テスト用リード 400件が入る。テナント001はテスト用なので止めない。
- 毎月1日 2:00 の優先度の点検（`backend/app/celery_app.py:124`〜126、`backend/app/tasks/priority_scoring_check.py`）: 数え方（scripts/check_priority_scoring_state.py 112〜123行）は invoices.lead_id と deals を結び付けて数えるが、invoices に lead_id の列は無く（`backend/app/services/tenant.py:860`〜885）、deals は表が消されている（migrations/20260729_043520_drop_deals.sql 32行）。そのため、この数え方は今の表の形と合っていない。本番でこの点検が今どう動いているか（失敗しているか）は未確認で、今回の設計の外（§10 に記録）。テスト用データがこの点検に入る道は、message_labels の件数（同 107行）と customer_scores（同 142行）だけで、どちらもテスト用データは入れない（下の項目で人が操作したときだけできる）。
- 優先度の計算の中の、成約と失注の傾向の数え方（`backend/app/services/priority_scoring.py:181`〜185 は請求書で成約、204〜207行は leads.status = 'lost' で失注）は、message_labels に行があるリードだけを数える。テスト用データは message_labels を持たないので数に入らない。なお成約の側（同 183行）も invoices.lead_id で結び付けており、上の点検と同じく今の表の形と合っていない（本番の動きは未確認。§10 に記録）。
- 人の操作で行ができる道（入れたあと、画面でテスト用リードを触った場合）:
  - 優先度: customer_scores と message_labels は、リードの優先度を見る・ラベルを付ける・手で直す、のどれかの入口で作られる（`backend/app/routers/customer_priority.py:39`〜55・58〜89・158〜178。計算と保存は `backend/app/services/priority_scoring.py:261`・296・372・384〜389・411）。今の画面から呼ばれているのは手で直す入口だけ（`frontend/src/components/PriorityScoreOverride.tsx:54`）。どちらもリードと結び付く決まりが無いので一緒には消えない。§6-1 で数えて消す。
  - 翻訳: 画面の翻訳を押すと message_translations に行ができる（`backend/app/routers/leads.py:1437`。キーは meta_messages の message_id `backend/app/routers/leads.py:1419`）。この表はリードやメッセージと結び付く決まりが無い（migrations/094_create_message_translations.sql 25〜33行）ので、メッセージを消しても残る。押すたびに Gemini を使う（費用が出る）。§6-1 で message_id が `tlr-` で始まる行を消す。テスト用のやり取りの翻訳は押さないよう、PO への報告に書く。
  - 会話の記録を手で足す: 受信箱でテスト用リードに WhatsApp の会話の記録を足すと、自動翻訳の依頼が出て（`backend/app/routers/conv_logs.py:129`）、audit_logs に create の行ができる（同 310〜320行）。足した行はテスト用リードの id で §6-1 手順5 が消す。翻訳の費用は戻らない。
  - 送ろうとする: 受信箱からテスト用リードへ送ろうとすると送信の入口を通る。失敗すれば audit_logs に meta_message_send_failed の行ができ（`backend/app/routers/leads.py:1982`〜2053）、成功すれば Meta へ実際に送られて meta_message_sent の行ができる（2133〜2135行）。どちらになるかはテナント001の Meta の設定しだいで未確認。どちらの行も K5② を × にする。
  - PO への報告に「テスト用リードには送らない・会話の記録を足さない・翻訳を押さない」と書く。

## 4. 分析と画面

### 4-1. 返信の時間の決まり（K2・K3d が同じものを読む）

- 読む時刻の列: Instagram・Facebook は meta_messages.created_at（本物は occurred_at を書かない）。WhatsApp は conversation_logs.occurred_at（手入力の入口が書く日時）。
- 1つのリードのメッセージを時刻の順に並べる。
- こちらの最初の返信までの時間: 最初の受信から、その後の最初の送信までの時間。こちらから営業したリード（最初がこちらの送信）も同じ決まりで測る（最初の受信のあとの最初の送信）。この扱いは PO に確認する（§8 #5）。
- 相手の返信までの時間の平均: 「すぐ前の行がこちらの送信である受信」それぞれについて、その送信からの時間を出し、平均する。
- テスト用データはすべて「受信→送信」と「送信→受信」を少なくとも1組ずつ持ち、受信と送信を交互に並べる（相手から来たリードは受信から、こちらから営業したリードは送信から始め、4〜20回）。そのため K2 の空欄は作りの上で出ない。
- 本物のデータで上の組が作れないリード（受信だけ・送信だけ）は、その項目を空欄とし、回帰の計算から外した件数を画面に出す。

### 4-2. 計算

- 分析に入れるリードの範囲: 状態が成約（existing_customer）か失注（lost）のリードだけ。それ以外の状態（lead など）は外し、外した件数を画面に出す。テナント001の元のリード id 4・6（状態 lead。recon.md 111行）はこの決まりで外れるので、K3d は本番でも本番の外でも 400件で計算する。
- 成約したか（はい/いいえ）を、§3-2 の 11項目で同時に見る（ロジスティック回帰）。基準は US・Cold・Facebook・こちらから営業・卸以外・遅い返信。
- 95%の幅は、推定値 ± 1.96 × 標準誤差（対数の上で計算して戻す。ワルドの方法）。statsmodels 0.15.0 の Logit の conf_int は既定で標準正規分布を使う同じ方法（公式説明書 statsmodels.org の LogitResults.conf_int、2026-10-31 確認。Context7 は月の上限で使えなかったため公式説明書を直接読んだ）。
- 計算の道具: backend の requirements に statsmodels・numpy は無い（git show origin/main:backend/requirements.txt を grep して 0件）。先行の設計と同じく、本番の計算は標準ライブラリだけで書き（反復で解く方法）、試験では作り物のデータで statsmodels 0.15.0 と小数4桁まで一致することを確かめる（クラウドで実行）。依存を増やさない。
- 件数の決まり（先行の設計と同じ「1項目につき 10件以上」を式にした）: min(成約の件数, 失注の件数) ÷ 項目の数（11）≧ 10。件数は上の範囲に入ったリードで数える。テスト用データは min(120, 280) ÷ 11 ≒ 10.9 で満たす。本物のデータでこれを満たさない間は、画面に「件数が足りない」と出して結果を出さない。
- 入口: 新しい読み取りの入口を analytics に足す（権限は既存の「属性ごとの成約率」と同じ dashboard.view。`backend/app/routers/analytics.py:1108`〜1111）。書き込みはしない。入口の名前と応答の形は実装カードで決める。

### 4-3. 画面

- 事実: 既存の「属性ごとの成約率」の入口（`backend/app/routers/analytics.py:1108`）を呼ぶ画面は無い（git grep conversion-by-attribute を frontend/src で 0件、2026-10-31）。第2版の「同じダッシュボードに足す」は根拠が無かったので取り消す。
- 案: ダッシュボード（`frontend/src/pages/dashboard/DashboardPage.tsx`）の「今やること」の2つ（466行・468行）の下に、新しい欄「成約しやすさの分析」を足す。既存の欄（PriorityProspectsSection・WeeklyAdvisorSection）と同じ並べ方。置き場は PO に確認する（§8 #5）。
- 表に出すもの: 11項目それぞれの名前・推定の強さ・95%の幅・「差があると言えるか」、分析に入れた件数と外した件数。上に「成約しやすさの目印で、原因ではない」「こちらの返信の速さには、見込みの高い相手ほど急いで返す逆向きの影響が混ざる」と出す。
- 仕込んだ値は画面に出さない（第3版の「仕込んだ値の列」は取り消す）。仕込んだ値の正本は §3-2 の表を写した作り方の定義1か所（実装で作る試験用の作り方のコード）だけにし、答え合わせ（K3a〜K3d）は報告書の中で行う。画面や入口にもう1つ同じ数を書くと、答えが2か所に分かれるため。
- どのテナントに出すか: 新しい欄は全テナントのダッシュボードに出る形になる（DashboardPage は全テナント共通）。テナント004（本物）では、件数の決まりを満たさないので「件数が足りない」と出る。ファネルの欄のような切り替えの印（`frontend/src/pages/dashboard/DashboardPage.tsx:462`）で出し分けるかは PO に確認する（§8 #5）。
- 部品は登録済みの金型だけ（ADR-144。表の金型の候補は `frontend/src/components/DataTable.tsx`。使う金型は実装カードで file:line まで決める）。合う金型が無いときは実装を止めて PO に報告する（docs/adr/ADR-144-ui-component-governance.md 59〜64行）。アイコンは `frontend/src/constants/icons.tsx` からだけ使う（frontend/AGENTS.md 57〜64行）。色・余白はデザイントークンだけ（ADR-067）。新しい色のトークンが要るときは明るい画面と暗い画面の両方の値を決める（frontend/AGENTS.md 40行）。注意書きを含む画面の文字はすべて t() のキーで ja・en 両方に入れる（ADR-027）。ダッシュボードの E2E と見本（`frontend/tests-e2e/scene1-dashboard.spec.ts`・`frontend/tests-e2e/fixtures/mock-dashboard.json`）を同じ PR で直す（frontend/AGENTS.md 67〜77行）。確かめ方は K4。

## 5. 対象と対象外

- 対象: データを入れるのはテナント001だけ。今回のテスト用データだけ。分析の読み取りの入口1つと、ダッシュボードの欄1つ（欄は全テナントの画面に出る形。出し分けは §8 #5）。
- 対象外: テナント004（本物）・006（Meta の審査用）。決まった入口の作り替え。シュリンクの扱い・扱う商材・成約日の項目（§8 #1・#2）。請求書・会社・担当者・見積の表。既存の「属性ごとの成約率」の直し（§10）。優先度の点検の数え方の直し（§10）。

## 6. リスクと対処

| リスク | 対処 |
|---|---|
| テスト用データが本物と混ざる | 目印（§3 の見分け方）を付け、§6-1 の消す手順を先に用意して試し流しで確かめてから入れる |
| 他テナントに書いてしまう | 書き込みはテナント001の表名を固定し、書き込みの後に他テナントの表で目印の行が 0件かを数える（K5①） |
| 決まった入口を通さない約束を破る | PO 許可はテナント001・今回だけ。この設計の外では使わない |
| 消す順番を誤って止まる・持ち主の無い行が残る | §6-1 の順番で消す。会話の記録はリードを消そうとすると止まる（`migrations/20260715_100000_add_conversation_logs_lead_fk.sql:21`、ON DELETE RESTRICT）。meta_messages はリードを消すと持ち主が空になって残る（`backend/app/services/tenant.py:1025`、ON DELETE SET NULL）。見積・失注の理由・会社・担当者はリードとの結び付きに消し方の指定が無く、残っているとリードを消せない（`migrations/20260721_100000_close_reasons_quotes_add_lead_id.sql:48`・82行、migrations/028_create_companies.sql 59行、migrations/029_create_contacts.sql 32行） |
| 人が画面で翻訳を押して費用が出る・消えない行が残る | §3-4。PO への報告に「テスト用のやり取りの翻訳は押さない」と書く。押した行は §6-1 手順2で消す |
| 仕込んだ傾向をそのまま返すだけで「分析が当たった」と誤解する | 目的は「仕組みが正しく動くか」の確認だけと画面と報告に書く |

### 6-1. 消す順番（K6。lead_id を持つ13表は ADR-1049 18行の一覧）

数える表: leads、ADR-1049 の13表（leads 自身は含まない）、tenant_sales_form_options、message_translations、meta_message_reactions、customer_scores、message_labels、audit_logs（K5②の2つの action）。テナント001は目印・テスト用リードの id・元の行の id で、テナント004・006 は目印で数える（件数の前後比較はしない。§2-1）。

旧 customers の表（migrations/015_replace_customers_schema.sql 88行。lead_id に消し方の指定なしの結び付き）は、テナント001・004・006 のどれにも無いことを確かめた（pg_catalog.pg_class を読み取りの道で検索して 0行、2026-10-31 15:53 JST。同じ検索で tenant_001 の leads・meta_messages・conversation_logs・invoices は見つかるので、検索の形は正しい）。止める条件には入れない。

0. 入れる前に記録する: テナント001の元の行の id の一覧（leads・meta_messages・conversation_logs・tenant_sales_form_options。リード id 4・6、既存のメッセージ4行を含む）と、書き込みを始める時刻（K5②・K6 の基準）。
1. 消す前に数える: テスト用リードの id に結び付く行を数える。quotes・companies・contacts・outbound_translation_drafts・public.registration_tokens・lead_attachments のどれかに 1件でもあれば、消す手順を止めて PO に報告する（人が画面で何かを作った印）。見積がある場合は、見積→請求書の結び付き（`backend/app/services/tenant.py:864`）も数えて報告する。lead_attachments がある場合は、行はリードと一緒に消える（migrations/20260902_100000_create_lead_attachments.sql 60行、ON DELETE CASCADE）が、ファイルの実体（attachments_data の置き場。同 63行・126行）は残る。PO に聞くこと:「テスト用リードに人が付けた〇〇（件数と作られた日時）があります。一緒に消してよいですか。消す場合はファイルの実体も消します」。PO が「消す」と答えた場合は、手順7 の前に lead_attachments の file_path の一覧を読み取りで記録し、手順10 で消す。
2. message_translations（message_id が `tlr-` で始まる行）
3. customer_scores・message_labels（テスト用リードの id で。結び付きの決まりが無いため）
4. meta_messages（message_id が `tlr-` で始まり、lead_id がテスト用リードの行。リアクションは一緒に消える `migrations/20260927_100000_create_meta_message_reactions.sql:48`）
5. conversation_logs（lead_id がテスト用リードの行）
6. deal_close_reasons（テスト用リードの id で）
7. leads（lead_code が `TLR-` で始まる行。lead_channels・lead_sales_form_selections・lead_attachments は一緒に消える）
8. tenant_sales_form_options（記録した id で。選択が残っていると止まる決まり `migrations/20260614_100000_create_sales_form_tables.sql:60` のため最後）
9. 消した後に上の表すべてを数え、テスト用の行が 0件（meta_message_reactions・message_translations を含む）で、手順0 で記録した元の行の id がすべて残っていることを確かめる。
10. （手順1 で PO が「消す」と答えたときだけ）添付のファイルの実体を、手順1 で記録した file_path の一覧だけ消す。本番のファイルの操作なので、一覧と件数を PO に示し、PO 本人が流す。一覧に無いファイルは消さない。

消す手順は大量の削除に当たるため PO 本人が流す（§8 #4）。

## 7. 外部事例

不要。仕組みの確認は「答えを仕込んだデータで取り戻せるか」（K3）で直接測るため、外部の数値を根拠に使わない。

## 8. 未決（PO に聞く・調べる）

| # | 未決 | 解消方法 |
|---|---|---|
| 1 | シュリンク付き/ノーシュリンクの扱い・扱う商材をどう持つか | 解決（PO 2026-10-31「1」）: 今回は外す。欄を足す作業はあとで別に設計する |
| 2 | 成約した日（状態が変わった履歴）の表が無い | 今回の分析（成約したか）には要らない。成約までの日数を見たいなら別の設計 |
| 3 | 目印を lead_code に入れてよいか | 解決: lead_code は VARCHAR(20)・テナント内で重複不可（migrations/003_add_phase1_tenant_tables.sql 78・97行）。採番は `LD-` と id（`backend/app/routers/leads.py:469`・`backend/app/routers/webhook.py:577`）。`LD-` を前提に読む処理は backend・frontend に無い（git grep、試験と見本を除く）。`TLR-00001` 形式を使える |
| 4 | 本番のテナント001へ書く手段 | 既存の決まり（PO 2026-09-30「意思決定までは私が行い合意した内容についてはopusに権限委譲する」）に合わせる: SQL ファイルを本フォルダに置く → 想定件数・戻しの SQL を PO に示し合意 → 読み取りで事前確認（§6-1 手順0）→ 試し流し（最後に取り消す）→ 件数が合えば本番 → 読み取りで事後確認。消す手順は PO 本人が流す。実行の道具は実装カードで決める |
| 5 | 次の4つをこの形で進めてよいか（1問にまとめて聞く）: ①K2・K3・K5・K6 の測り方（§2）②こちらから営業したリードの「最初の返信」を、最初の受信のあとの最初の送信で測る（§4-1）③分析の表をダッシュボードの「今やること」の下に新しい欄として置く（§4-3）④その欄を全テナントに出す（本物のテナント004では「件数が足りない」と出る）か、切り替えの印でテナント001だけに出すか（§4-3） | 第4版の審査が通ってから、推奨と影響を添えて PO に1問で聞く |

## 9. 維持の仕組み

- 消す手順（§6-1）は実装と同じ PR に入れ、試し流しで確かめてから本番に入れる。
- 自前の計算が statsmodels と一致し続けることを試験で守る（§4-2）。
- 本物のリードが成約 120件を超えたら、同じ計算を本物に切り替える（目安。PO 判断）。切り替える前に、アプリの外からの返信が conversation_logs だけにある件の読み先を決め直す（§3 の限界）。

## 10. 見つけた食い違い（今回は直さない・記録だけ）

- 店舗の形が2か所にある。カルテの入力画面は lead_sales_form_selections に書く（`frontend/src/pages/inbox/InboxKartePanel.tsx:592`）。一方で既存の「属性ごとの成約率」は leads.sales_form を読む（`backend/app/routers/analytics.py:988`）。そのため、画面で入れた店舗の形は既存の成約率に出ない。今回の分析は入力画面と同じ lead_sales_form_selections を読む。既存の成約率の直しは別の設計にする。
- 将来の正本は「店舗形態の台帳1つ（共有＋テナント独自）」と決まっている（docs/specs/db-ssot/classification-master/design.md 101行）が、まだ作られていない。台帳ができたら、今回の分析の読み先もそこへ移す。
- 会話の記録が2つの表にある（統合の途中）。Instagram・Facebook の受信は両方、アプリからの送信は meta_messages だけ、アプリ外からの送信（エコー）は conversation_logs だけに書かれる（`backend/app/routers/webhook.py:816`〜887）。
- 優先度の点検の数え方（scripts/check_priority_scoring_state.py 112〜123行）が、消された deals と、lead_id の無い invoices を前提にしている（§3-4）。優先度の計算の成約の側（`backend/app/services/priority_scoring.py:183`）も invoices.lead_id で結び付けている。本番での動きはどちらも未確認。
- 本物のリードの作り方は、廃止と決まった type に 'Inbound' を書いている。エコーで作る道（`backend/app/routers/webhook.py:547`・550。initiative は 'outbound'）と、受信で作る道（`backend/app/routers/webhook.py:646`〜656）の両方。
