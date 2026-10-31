<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# design — リードのカルテで成約しやすさを分析する（テナント001のテスト用データ）

**日付**: 2026-10-31（第2版。第1版 8422b3cbb の設計審査 REVISE を受けて直した）  
**状態**: 設計の下書き。KGI 承認済み（K3・K5 は第2版で測り方を直したため PO の再確認が要る）・設計審査 第1版 REVISE・PO 実装承認 なし・実装 未着手。本番への書き込みは一切していない。  
**下調べ**: `docs/handoff/lead-regression/recon.md`  
**対象ADR**: ADR-015（リードの土台・返信速度）、ADR-119（lead_channels）、ADR-109（状態の不変コード）、ADR-1049（lead_id を持つ13表）、ADR-1024（本番の読み取り専用の道）  
**基準**: origin/main 21f6a10fe で照合  
**先行の同じ計算**: docs/handoff/accuracy-measurement/design-regression.md（ロジスティック回帰・オッズ比）

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

K1・K2・K4・K6 は PO 承認（2026-10-31「1」）のまま。K3・K5 は第1版の測り方に欠陥があったため直した（直した理由は §2-1）。

| # | 基準 | 検証方法 |
|---|---|---|
| K1 | テナント001にテスト用リード 400件（うち成約 120件・失注 280件）が入り、400件すべてに目印がある | 読み取りの道で件数と目印付きの件数を数え、両方 400・成約 120・失注 280 |
| K2 | テスト用リード 400件すべてで「こちらの最初の返信までの時間」と「相手の返信までの時間」が計算できる | 計算結果の空欄が 0件 |
| K3a | 計算の正しさ（本番の外で確かめる）: 同じ作り方で乱数の種を 200通り変えて作ったデータで、9項目（国・温度は比べる組ごと）それぞれ「95%の幅が仕込んだ値を含む割合」が 91%以上 99%以下 | 200回分の結果表で、項目ごとに含んだ回数を数える（9項目すべて 182〜198回なら ○） |
| K3b | 偏りが無い: 同じ 200回で、9項目それぞれの推定の平均が仕込んだ値の 0.90倍〜1.11倍に入る | 200回分の推定の平均（対数で平均してから戻す）を仕込みの表と突き合わせる |
| K3c | 壊れた仕組みを見逃さない: 成約の印だけを無作為に並べ替えた 200回分で、9項目それぞれ「幅が差なし（1）を含む割合」が 91%以上 | 並べ替えた 200回分の結果表で数える |
| K3d | 本番に入れた後も同じ答えが出る: 本番のテナント001から読んで計算した結果が、本番の外で同じ種から計算した結果と小数4桁まで一致 | 2つの結果表を突き合わせ、9項目すべて一致で ○ |
| K4 | ダッシュボードに結果の表が出る。部品はすべて登録済みの金型・デザイントークンだけ | PO が画面で目視 ○×／自動の点検（直書きの色・金型外の部品）で 0件 |
| K5 | テスト用データが外へ何も起こさない: ①ほかのテナント（004・006）の件数が書き込み前後で 1件も変わらない ②テナント001の Meta への送信の記録・翻訳の依頼が書き込み前後で増えない ③毎朝の突合が数える「当日の行」にテスト用の行が 0件 | ①前後で件数を比べる ②送信の記録と翻訳の記録の件数を前後で比べる ③テスト用の行のうち created_at・occurred_at が書き込み日以降のものを数え 0件 |
| K6 | 消す手順を流すと目印付きの行と、テスト用リードに結び付いた行が 13表すべてで 0件になり、元からある行（リード2件・やり取り4件など）は残る | 消した後に 13表（ADR-1049 の一覧）と店舗の形の選択肢を数える |

### 2-1. K3・K5 を直した理由（第1版の審査の指摘）

- 第1版の K3 は「1回のデータで、仕込んだ項目すべての 95%の幅が当たる」だった。1項目が当たる確率は約 95%なので、14前後の幅がすべて当たる確率は約 5割しかない（0.95 を14回かけると約 0.49）。仕組みが正しくても半分は × になり、逆に壊れていても運で ○ になりうる。そこで「200回作って当たる割合を見る（K3a）」「平均がずれていない（K3b）」「答えを壊したデータでは何も見つけない（K3c）」「本番に入れても同じ答え（K3d）」の4つに分けた。
- 第1版の K5 は「見張りの知らせ 0件」だった。毎朝の突合は、差が無くても毎日 Discord に送る作り（`backend/app/tasks/sa02_recon_monitor.py:127`、すぐ上の126行に「差異ゼロ・差異あり問わず毎日 Discord に通知」）。そのため 0件は守れない。知らせの中身にテスト用の行が入らないこと（③）で測る形に直した。

## 3. 何を入れるか（SSOT: 既存の表だけに入れる。新しい写しの表は作らない）

本物の受け口がどの表に何を書くかに合わせる（配線の SSOT）。

| 表 | 入れるもの | 本物の配線（根拠） | 目印 |
|---|---|---|---|
| leads | 400件。状態（成約 120・失注 280）、きっかけ、経路、国、温度 | 作る入口 `backend/app/routers/leads.py:405` | lead_code を `TLR-` で始める（§8 #3） |
| tenant_sales_form_options | テナント001の店舗の形の選択肢（テナント004と同じ値） | 選択肢はテナント004にだけ入っている（`migrations/20260614_100000_create_sales_form_tables.sql:89`） | 入れた行の id を記録し、消す手順で消す |
| lead_sales_form_selections | 400件それぞれの店舗の形（1つ） | カルテの入力画面の書き先（`backend/app/routers/leads.py:690`） | テスト用リードを消すと一緒に消える（`migrations/20260614_100000_create_sales_form_tables.sql:58`） |
| deal_close_reasons | 失注 280件それぞれの主な理由 1件（テナント001の失注理由の選択肢 15個から） | 失注は主な理由 1件が必須（`backend/app/schemas/lead.py:183`）。書き先 `backend/app/routers/leads.py:628` | テスト用リードの id で消す（一緒には消えない） |
| lead_channels | Instagram・Facebook のリードの経路 1件 | platform は messenger / instagram / discord だけ（docs/adr/ADR-119-lead-channels-and-lead-merge.md 43行）。WhatsApp は入れない | external_id を `tlr-` で始める（一緒に消える `migrations/20260607_120000_create_lead_channels.sql:18`） |
| meta_messages | Instagram・Facebook の受信と、アプリからの送信 | 受信は meta_messages（`backend/app/routers/webhook.py:853`）。アプリからの送信も meta_messages だけ（`backend/app/routers/leads.py:2070`） | raw_payload に `{"seed":"lead-regression-v1"}`、message_id を `tlr-` で始める |
| conversation_logs | ①Instagram・Facebook の受信の写し（上と同じ受信） ②WhatsApp の受信と送信 | ①本物の受け口は受信を conversation_logs にも書く（`backend/app/routers/webhook.py:876`）。②WhatsApp は手入力の入口の書き先（`backend/app/routers/conv_logs.py:225`） | raw_payload に同じ目印。external_message_id を `tlr-` で始める |

- 返信の速さは「やり取りの表の受信と送信の時刻」から計算する。リードの表へ写して持たない（データを2か所に分けない）。
- 読む表は経路ごとに1つに決める: Instagram・Facebook は meta_messages（受信と送信がそろっているのはこちらだけ。アプリからの送信は conversation_logs に書かれない）。WhatsApp は conversation_logs（ほかに書き先が無い）。①の写しは本物の配線に形を合わせるためだけに入れ、分析では読まない。
- 会話の表を1つにまとめる作業は途中（docs/specs/db-ssot/conversation-unification/design.md 4行・17行）。まとまったら分析の読み先もそこへ移す。
- 書かない表: invoices（請求書）・deals・companies・contacts・quotes。成約済みは本来「入金の確認で自動に切り替わる」（docs/specs/db-ssot/classification-master/design.md 48行）が、テスト用の成約 120件は請求書を持たない。そのため、請求書を数える画面（売上・入金の画面）にはテスト用の成約は出ない。今回の分析は leads の状態だけを使うので影響しない。

### 3-1. どの欄に入れるか（正本の確認）

| 分析に使う項目 | 入れる欄（正本） | 根拠 | 入れない欄 |
|---|---|---|---|
| 相手から来たか・こちらから営業したか | leads.initiative（inbound / outbound） | docs/specs/db-ssot/classification-master/design.md 42行（type は initiative に統合して廃止。PO 確定 2026-07-13）。`backend/app/routers/analytics.py:1747` も initiative を使う | leads.type |
| 経路 | leads.channel_type（instagram / messenger / whatsapp）。Instagram・Facebook は lead_channels にも 1件 | channel_masters の6つ（下調べ §4）。lead_channels の platform は ADR-119 43行 | — |
| 国 | leads.country に2文字の国コード | 国の台帳 public.countries の code CHAR(2)（migrations/20260621_010000_create_countries_master.sql 7行）。国コードとして読むのは `backend/app/schemas/lead.py:148`・215行 | 国名の文字 |
| 店舗の形 | lead_sales_form_selections（選択肢は tenant_sales_form_options） | カルテの入力画面が書く先（`frontend/src/pages/inbox/InboxKartePanel.tsx:592`、`backend/app/routers/leads.py:634`）。複数選択はコードの説明（`backend/app/schemas/lead.py:179`）と ADR-1049 の13表の一覧にある（ADR-108 の本文には無い） | leads.sales_form（§10） |
| 温度 | leads.temperature（Hot / Warm / Cold） | `backend/app/schemas/lead.py:47` | — |
| 成約したか | leads.status（成約 existing_customer・失注 lost） | `backend/app/schemas/lead.py:31`（ADR-109） | deals |
| 返信の速さ・やり取りの回数 | Instagram・Facebook は meta_messages、WhatsApp は conversation_logs の時刻から計算 | 上の §3 | leads.response_speed・first_response_at |

### 3-2. 仕込む傾向（K3 の答え合わせの表）

テスト用データは、乱数の種を固定した作り方で作る。下の「仕込む強さ」で成約しやすさを決め、成約がちょうど 120件になるよう基準の高さを合わせる。

| 項目 | 比べ方 | 仕込む強さ（オッズ比） |
|---|---|---|
| 相手から来た | こちらから営業した、と比べて | 2.0 |
| 店舗の形が卸・代理店 | それ以外と比べて | 2.5 |
| こちらの最初の返信が1時間以内 | 1時間より遅い、と比べて | 1.8 |
| 相手の返信が平均6時間以内 | 6時間より遅い、と比べて | 1.6 |
| 経路が WhatsApp | Facebook と比べて | 1.5 |
| 経路が Instagram | Facebook と比べて | 1.0（仕込まない） |
| 国 | 比べる国どうし | 1.0（仕込まない） |
| 温度 | Hot・Warm・Cold どうし | 1.0（仕込まない） |
| やり取りの回数 | 回数が多いほど | 1.0（仕込まない） |

- K3a〜K3c は本番に入れる前に、本番の外で確かめる。1つでも × なら本番には入れず、結果を PO に報告する。
- 1回のデータ（400件）では、仕込んだ強さが小さい項目（1.5 など）は「差がある」と言い切れないことがある。これは件数の限界で、仕組みの誤りではない。画面には仕込んだ値と推定の幅を並べて出す。
- これは「計算と画面が正しく動くか」を確かめるためのもので、本物の傾向ではない。画面と報告にもそう書く。

### 3-3. 自動で動くものを止める条件（下調べ §6 の事実）

- やり取りの時刻（meta_messages の created_at・occurred_at、conversation_logs の occurred_at・created_at）は、すべて書き込む日の2日以上前の値を明示して入れる。既定値（今の時刻）に任せない → 毎朝の突合（meta_messages は created_at、conversation_logs は occurred_at で当日の行を数える。`backend/app/tasks/sa02_recon_monitor.py:74`）と、毎時の翻訳の見張り（直近60分。`backend/app/services/translation_monitor.py:61`）が数えない。
- page_id は空にする → 毎日の顔写真の取り直しが Meta に問い合わせない（`backend/app/tasks/avatar.py:317`）。
- 送信の入口・受け口・翻訳の依頼は通らない → Meta への送信・翻訳の費用は出ない（下調べ §6）。

### 3-4. 入れたあとに変わること（止めない・知っておくこと）

- テナント001のダッシュボードの数字（10分ごとに作り直す。`backend/app/tasks/dashboard.py:62`）に、テスト用リード 400件が入る。テナント001はテスト用なので止めない。
- 毎月1日 2:00 の優先度の点検（`backend/app/tasks/priority_scoring_check.py`、数え方は scripts/check_priority_scoring_state.py 104〜126行）は、成約を請求書で、失注を deals で数える。テスト用データはどちらも持たないので、点検の数は変わらない。
- 画面でテスト用リードの優先度を手で直すと、customer_scores と message_labels に行ができる（`backend/app/routers/customer_priority.py:58`）。これらはリードと結び付く決まり（外部キー）が無いので一緒には消えない。消す手順で必ず数えて消す。

## 4. 分析と画面

- 計算: 成約したか（はい/いいえ）を、きっかけ・経路・国・店舗の形・温度・こちらの返信の速さ・相手の返信の速さ・やり取りの回数で同時に見る（ロジスティック回帰）。1つの項目につき成約が 10件以上の決まり（先行の設計と同じ）。
- 画面: 既存の「属性ごとの成約率」（入口 `backend/app/routers/analytics.py:1108`）と同じダッシュボードに結果の表を足す。部品は登録済みの金型だけを使う（どの金型を使うかは実装カードで file:line まで決める）。
- 読み方の注意（画面にも出す）: これは「成約しやすさの目印」で原因ではない。こちらの返信の速さには「見込みの高い相手ほど急いで返す」逆向きの影響が混ざる。

## 5. 対象と対象外

- 対象: テナント001だけ。今回のテスト用データだけ。
- 対象外: テナント004（本物）・006（Meta の審査用）。決まった入口の作り替え。シュリンクの扱い・扱う商材・成約日の項目（§8 #1・#2）。請求書・商談・会社・担当者の表。

## 6. リスクと対処

| リスク | 対処 |
|---|---|
| テスト用データが本物と混ざる | 目印を全行に付け、K6 の消す手順を先に用意して試し流しで確かめてから入れる |
| 他テナントに書いてしまう | 書き込みはテナント001の表名を固定し、前後で他テナントの件数を比べる（K5①） |
| 決まった入口を通さない約束を破る | PO 許可はテナント001・今回だけ。この設計の外では使わない |
| 消す順番を誤って止まる・持ち主の無い行が残る | §6-1 の順番で消す。会話の記録はリードを消そうとすると止まる（`migrations/20260715_100000_add_conversation_logs_lead_fk.sql:21`、ON DELETE RESTRICT）。meta_messages はリードを消すと持ち主が空になって残る（`backend/app/services/tenant.py:1025`、ON DELETE SET NULL） |
| 仕込んだ傾向をそのまま返すだけで「分析が当たった」と誤解する | 目的は「仕組みが正しく動くか」の確認だけと画面と報告に書く |

### 6-1. 消す順番（K6。lead_id を持つ13表は ADR-1049 18行の一覧）

1. 先に数える: テスト用リードの id に結び付く行を13表すべてで数え、companies・contacts・quotes・outbound_translation_drafts・public.registration_tokens・lead_attachments に 1件でもあれば止めて PO に報告する（人が画面で何かを作った印）。
2. customer_scores・message_labels（テスト用リードの id で。結び付きの決まりが無いため）
3. meta_messages（目印で。リアクションは一緒に消える `migrations/20260927_100000_create_meta_message_reactions.sql:48`）
4. conversation_logs（目印で）
5. deal_close_reasons（テスト用リードの id で）
6. leads（lead_code が `TLR-` で始まる行。lead_channels・lead_sales_form_selections・lead_attachments は一緒に消える）
7. tenant_sales_form_options（記録した id で。選択が残っていると止まる決まり `migrations/20260614_100000_create_sales_form_tables.sql:60` のため最後）
8. 消した後に 13表と選択肢を数え、目印付き 0件・元の行の数が入れる前と同じことを確かめる。

## 7. 外部事例

不要。仕組みの確認は「答えを仕込んだデータで取り戻せるか」（K3）で直接測るため、外部の数値を根拠に使わない。

## 8. 未決（PO に聞く・調べる）

| # | 未決 | 解消方法 |
|---|---|---|
| 1 | シュリンク付き/ノーシュリンクの扱い・扱う商材をどう持つか | 解決（PO 2026-10-31「1」）: 今回は外す。欄を足す作業はあとで別に設計する |
| 2 | 成約した日（状態が変わった履歴）の表が無い | 今回の分析（成約したか）には要らない。成約までの日数を見たいなら別の設計 |
| 3 | 目印を lead_code に入れてよいか | 解決: lead_code は VARCHAR(20)・テナント内で重複不可（migrations/003_add_phase1_tenant_tables.sql 78・97行）。採番は `LD-` と id（`backend/app/routers/leads.py:469`・`backend/app/routers/webhook.py:577`）。`LD-` を前提に読む処理は backend・frontend に無い（git grep、試験と見本を除く）。`TLR-00001` 形式を使える |
| 4 | 本番のテナント001へ書く手段 | 既存の決まり（PO 2026-09-30「意思決定までは私が行い合意した内容についてはopusに権限委譲する」）に合わせる: SQL ファイルを本フォルダに置く → 想定件数・戻しの SQL を PO に示し合意 → 読み取りで事前確認 → 試し流し（最後に取り消す）→ 件数が合えば本番 → 読み取りで事後確認。消す手順（K6）は大量の削除に当たるため PO 本人が流す。実行の道具は実装カードで決める |
| 5 | K3・K5 の測り方を第2版に直してよいか | PO に確認する（第2版の審査が通ってから1問で聞く） |

## 9. 維持の仕組み

- 消す手順（K6）は実装と同じ PR に入れ、試し流しで確かめてから本番に入れる。
- 本物のリードが成約 120件を超えたら、同じ計算を本物に切り替える（目安。PO 判断）。

## 10. 見つけた食い違い（今回は直さない・記録だけ）

- 店舗の形が2か所にある。カルテの入力画面は lead_sales_form_selections に書く（`frontend/src/pages/inbox/InboxKartePanel.tsx:592`）。一方で既存の「属性ごとの成約率」は leads.sales_form を読む（`backend/app/routers/analytics.py:988`）。そのため、画面で入れた店舗の形は既存の成約率に出ない。今回の分析は入力画面と同じ lead_sales_form_selections を読む。既存の成約率の直しは別の設計にする。
- 将来の正本は「店舗形態の台帳1つ（共有＋テナント独自）」と決まっている（docs/specs/db-ssot/classification-master/design.md 101行）が、まだ作られていない。台帳ができたら、今回の分析の読み先もそこへ移す。
- 会話の記録が2つの表にある（統合の途中）。Instagram・Facebook の受信は両方、アプリからの送信は meta_messages だけ、アプリ外からの送信（エコー）は conversation_logs だけに書かれる（`backend/app/routers/webhook.py:815`〜876）。
