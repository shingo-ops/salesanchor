# 引き継ぎメモ（DB設計のSSOT化）2026-07-14時点

> この文書は何か（1行）:
> 次に作業する人（次回セッションの自分・共同編集者）が、記憶ゼロでもDB設計SSOT化の全体像・成果・現在地・次の一手を把握できる資料。

親: ./README.md

---

## 1. このテーマは何を目指すか（30秒で分かる要約）

このアプリのデータを「同じ事実は1か所だけ」に整える。今は同じ情報（顧客名・連絡先・金額など）が複数テーブルに散らばり、分析がずれる恐れがある。それを「正本1か所＋他は背番号で参照」の形に作り直す。本番は未稼働なので、既存データは捨てて理想構造で作り直せる（複雑なデータ移行は不要）。

## 2. 全体像の事実（2026-07-14実測）

- DBは合計112テーブル（tenant_004＝各社ごとのデータ68個、public＝全社共通データ44個）。
- 実際にDBが変更された作業は、2026-07-11のcustomers_legacy削除のみ。それ以外は全て「design.mdへの設計記録」段階であり、実装（migration作成・実行）はまだ0件。
- 進捗率（実装ベース）: 112テーブル中、実際に変更が入ったのは0テーブル（0%）。設計が完了したのは、leads/dealsの一部列に関わる分類マスタ関連のみ。

## 3. これまでの成果（何が終わっているか）

### 設計（紙）— すべてPRマージ済み・origin/mainに存在

- あるべき姿・KGI（K1〜K5）: ./ideal-state.md, ./kgi.md
- 会話データ一元化の設計図: ./conversation-unification/design.md
- 予測値の分離の設計図: ./forecast-separation/design.md
- 金額の集約の設計図: ./money-consolidation/design.md
- 分類値の台帳化の設計図: ./classification-master/design.md（2026-07-14時点で15項目・実装フェーズ着手宣言まで完了）
- 本丸実装の計画: ./implementation-plan/design.md（STEP2に担当者概念廃止の方針を追記済み）

### 2026-07-14セッションでの成果（本日分・詳細）

#### classification-master/design.md の変遷（PR履歴）
1. PR #2897: 15項目（当初）の全面改訂。役割・2階建て要否・新設/統合/削除を確定。
2. PR #2898: テーブル実装方式（「1テーブル＋持ち主の印(owner_tenant_id)」方式）を追記。5項目（流入元・店舗形態・取扱ジャンル・顧客タイプ・チャネル）に持ち主の印方式を適用。
3. PR #2900: 「取扱商材」を削除し、既存product-masterの「取扱ジャンル（大分類流用）」「取扱シリーズ（種別流用）」に置き換え（16項目に）。新規マスタ作成は不要、既存product-category-master.md・product-type-master.mdをそのまま参照する方針。
4. PR #2902: リード状態と商談状態を1つの状態リスト（8状態）に統一。deals.status・deals.stageを廃止し、leads.statusに一本化（15項目に整理）。各状態の自動/手動切替方式を確定。
5. PR #2904: leadsテーブルの未使用疑い7列（english_name, discord_id, ai_collection_state, escalation_flag, first_inquiry_at, first_response_at, first_response_seconds）を、SSOT化完了後の削除候補としてメモ記録（実削除はしていない）。
6. PR #2905: 再発防止策（executor-preamble.mdへのworktree整合性チェック追加）、design-partner.md §6への教訓記録、抜けていた台帳行の復元。
7. PR #2906: active-work.mdの空欄記入（軽微修正）。
8. PR #2909: implementation-plan/design.mdへ「担当者(contacts)概念廃止」方針を追記。classification-master/design.mdに「実装フェーズ着手」宣言を追記。

#### 確定した分類マスタ 全15項目（2026-07-13時点、design.md §1に記載済み）
1. きっかけ（initiative）─ 1テーブル・共有のみ
2. 流入元（lead_source）─ 1テーブル・持ち主の印あり
3. 返信速度（response_speed）─ 1テーブル・共有のみ
4. 国（country）─ 既存countries活用
5. 取扱ジャンル（既存product-masterの大分類マスタ流用）─ 既存テーブル活用・共有のみ
6. 取扱シリーズ（既存product-masterの種別マスタ流用）─ 既存テーブル活用・持ち主の印あり
7. 店舗形態（＝販売形態・旧sales_form。取扱商材の店舗形態案とは別物と当初判定されたが、PO最終判断でsales_formと同一と確定）─ 1テーブル・持ち主の印あり
8. 顧客タイプ（customer_type）─ 1テーブル・持ち主の印あり
9. 見込み規模（estimated_scale）─ 1テーブル・共有のみ
10. 温度感（temperature）─ 1テーブル・共有のみ
11. リード状態（=商談状態・統一。新規／商談中／成約済み／再アプローチ短期／再アプローチ長期／失注／対象外／archive新設の8状態）─ 1テーブル・共有のみ
12. チャネル（channel_type）─ 既存channel_masters拡張・持ち主の印あり
13. 受注状態（orders.status）─ 1テーブル・共有のみ
14. 通貨（currency）─ 1テーブル・共有のみ（deal/quote/invoiceの3列は残すが選択肢は1マスタに統一）
15. 競合確認（competitor_check）─ 1テーブル・共有のみ（boolean→あり/なし/不明の3択に変更）

#### 状態統一の詳細（PR #2902で確定）
- leads.statusを正本とし、deals.status・deals.stageを廃止する。
- 各状態の切替方式:
  - 新規: リード作成時に自動で初期値
  - 商談中: 営業担当が「商談化」ボタンを押した時に自動で切替（既存convert_lead処理をほぼ流用可能、2026-07-14 recon確認済み）
  - 成約済み: 入金確認時（invoice.paid_at）に自動で切替（現状この自動更新経路は存在せず、新設が必要。2026-07-14 recon確認済み）
  - 再アプローチ短期/長期: 担当者の手動判断。アクション日・次回アクション入力を必須にする
  - 失注/対象外/archive: 手動
- 「提案中」相当の進捗は状態として持たず、見積(quote)送付済みという事実から別途判定する方針（状態は保存せず事実から導出。transaction-flow/ssot-allocation.md S8/S9と同思想）。

#### 状態統一の影響範囲（2026-07-14 recon確定）
- 直接影響: backend/app/schemas/deal.py, backend/app/routers/deals.py, backend/app/tasks/reports.py, frontend/src/pages/deals/DealsPage.tsx, DealFormFields.tsx, DealEditPage.tsx, frontend/src/utils/statusPresentation.ts, statusPresentation.test.ts, frontend/src/pages/design-preview/sections/StatusSection.tsx（9ファイル）
- 追加で判明した影響: backend/app/routers/analytics.py（12箇所でdeals.status参照。書き換え規模大）、backend/app/services/priority_scoring.py（d.status='lost'を使用）
- 現状、dealsテーブルからleads.statusを参照する経路（JOIN/API）は存在しない。新設が必要。
- 実データ確認: tenant_004.dealsは0件。tenant_006.dealsは18件あり、実際に「成約(won)なのに進行中(open)のまま」という食い違いが3件実在した（status='won'かつstage='open'）。この食い違いが、stage側を正本にすべき根拠の一つ。

#### 全112テーブルの棚卸し結果（2026-07-14実施）
- tenant_004: 68テーブル（営業CRM18・受発注請求11・商品在庫物流7・メッセージ通知翻訳6・管理認証組織人事18・ログ監査3・スケジューリング2・社内交流その他3）
- public: 44テーブル（商品在庫マスタ10・国際配送取込3・仕入サプライヤ4・認証監査テナント統制10・外部連携10・文書ルーティング翻訳5・補助設定2）
- 詳細確認済み: leads, deals, companies, orders, invoices, countries, channel_masters, tcg_type_master, product_attribute_masters（9テーブル）
- 営業CRM系18テーブルは追加で詳細確認済み（下記5参照）
- 残り103テーブル中、営業CRM18を除く85テーブルは未確認（名前からの機械分類のみ）

### 5. 営業CRM系18テーブルの詳細（2026-07-14 recon確定）

| テーブル | 役割 | 実データ件数(tenant_004) | 備考 |
|---|---|---|---|
| companies | 契約会社の一覧 | 3行（実データ） | 25列 |
| company_addresses | 会社の住所（複数可） | 101行 | 実際に1社2〜4件の複数保持あり |
| company_discord | 会社のDiscord連携設定 | 8行 | contact_discordとは別情報（guild_id等が異なる） |
| company_sales_channels | 会社の販売チャネル | 26行 | 実際に1〜4件の複数保持あり |
| contact_contact_channels | 担当者の連絡手段（複数可） | 60行 | 実際に複数保持あり |
| contact_discord | 担当者個人のDiscord連携設定 | 8行 | company_discordとは別情報 |
| contact_emails | 担当者のメール（複数可） | 0行 | 未使用 |
| contacts | 会社の担当者（人） | 実データあり（49社中3社が2人、46社が1人） | 17列。受信箱は単独表示だが、contacts API/UI・deals.contact_idは複数担当者前提で実装済み |
| conversation_logs | 全会話ログ | 実データあり | 22列 |
| customer_scores | 顧客優先度スコア（AI自動采配用） | 0行 | ADR-015想定と別に、優先度専用の入れ物が別途存在。未実装・未使用 |
| deal_close_reasons | 商談の成約/失注理由（複数可） | 0行 | 未使用 |
| close_reasons | 理由の選択肢マスタ | 15行 | |
| channel_masters | 連絡手段の選択肢マスタ | 6行 | |
| lead_channels | リードの連絡先（プラットフォーム別） | 4行 | 現データでは各lead_idが1件のみ。複数構造の必要性が実データ上は弱い |
| lead_playbook | AI営業台本（挨拶文・質問・引き継ぎ条件） | 0行 | 未使用 |
| lead_sales_form_selections | リードが選んだ販売形態（複数可） | 0行 | 未使用 |
| deals | 商談の一覧 | 0行（tenant_004）/18行（tenant_006） | 20列 |
| leads | 見込み客の一覧 | 56行 | 51列 |

### 6. leadsテーブル51列の役割（2026-07-14 recon確定・省略なし）

#### リード編集画面で使用（2列)
- monthly_forecast（月間見込金額。prospect_rank再計算にも使用）
- discord_user_id（Discordユーザー番号。一覧バッジ表示、DM送信・チケットチャンネル作成のキー）

#### 受信箱（inbox）の顧客カルテで使用（7列)
- target_titles（対象タイトル）
- cs_memo（CS向け引き継ぎメモ）
- per_order_amount（1回あたり取引金額）
- monthly_frequency（月あたり取引頻度）
- challenge（課題・ニーズ）
- nickname（呼び名）
- meeting_memo（商談メモ）

#### Discord連携の裏側で使用（3列)
- discord_dm_channel_id（DM送受信のキー）
- discord_role_sync_status／discord_role_sync_at（ロール同期の状態・時刻）
- discord_guild_channel_id（専用チャンネル番号）

#### 削除候補（未使用・PR #2904でメモ済み。実削除はSSOT化完了後）
- english_name（nicknameへの改名痕跡あり、現行コード不使用）
- discord_id（discord_user_idとは別物、現行コード不使用、削除注記あり）
- ai_collection_state（ADR-015のAI自動収集機能用。未実装。tenant_004実データ0件）
- escalation_flag（ADR-015のエスカレーション機能用。未実装。tenant_004実データで真値0件）
- first_inquiry_at・first_response_at・first_response_seconds（ADR-015の返信速度自動計測機能用。未実装。tenant_004実データ0件）

#### その他・基本情報・分類系
- id, tenant_id, lead_code, customer_name, company_name, email, phone, type（きっかけ統合先で廃止予定）, status（統一後の正本）, temperature, estimated_scale, customer_type, response_speed, prospect_rank（自動計算）, assigned_to, converted_deal_id, notes, created_at, updated_at, country, sales_form, competitor_check, monthly_forecast_source（company側の同名列が実際に使われており、leads側は実質未消費）, meeting_impression（入力欄なし・未使用）, next_action, next_action_date, initiative, channel_type

### 7. dealsテーブル20列の役割（2026-07-14 recon確定）
id, tenant_id, deal_code, lead_id（必須・出自）, title, amount, currency, status（廃止予定）, stage（廃止予定→leads.statusに統合）, probability, assigned_to, expected_close_date, notes, created_at, updated_at, company_id（必須）, contact_id, lead_source, closed_at, close_reason_memo

## 4. 現在地（いまどこにいるか）

- 分類マスタ(classification-master)の**設計**は完了（15項目・役割・2階建て要否・テーブル方式・状態統一まで）。
- **実装（migration作成・実行）はまだ0件**。design.mdへの記録のみで、実際のDB変更はまだ1つも行っていない。
- STEP2（戸籍：lead→deal→company→contact）について、「担当者(contacts)概念を廃止し、会社(company)に連絡チャネルを直接持たせる」という大方針をPOが決定。ただし、あるべき姿→KGI→設計の正式な手順はまだ経ていない（今回は方針の記録のみ）。

## 5. 次にやること（次の一手・優先順位順）

### 最優先（次回セッション冒頭で選択）
1. **分類マスタ(classification-master)の実装着手**: §8「まだ決めていない」に残る以下3点を先に詰めてから、または並行してmigration作成に入る:
   - リード状態・商談状態統一の実装手順詳細（影響ファイル: backend 5＋frontend 6の計11ファイル、規模大）
   - 「商談化」ボタン押下時の自動切替ロジックの実装箇所（convert_lead相当の処理拡張）
   - 再アプローチ短期/長期の「アクション日・次回アクション入力必須」バリデーション実装方法
2. **STEP2（戸籍・担当者概念廃止）の正式着手**: あるべき姿→KGI→設計の手順から。影響範囲は61ファイル（recon済み、2026-07-14実測）。受信箱の会社単位集約という前提で設計する。

### 中期
3. 分類マスタ実装完了後、leadsテーブルの7列削除（PR #2904でメモ済みの候補）の実施検討。
4. 全112テーブルのうち、営業CRM18以外の94テーブル（受発注・商品在庫・管理認証等）の詳細棚卸し。

### 積み残し（本丸実装と並行 or 事前に）
- customer_scores（優先度自動采配の入れ物、0件・未実装）と、design-partner.mdで「将来機能待ち」と判断したpriority_focusとの関係整理（同じ機能を指している可能性）。
- lead_channelsが実データ上「1lead=1件」しか無く、複数構造の必要性が薄い点の要否判断。
- monthly_forecast_source（leads側は実質未消費、companies側の同名列が実際に使われている）の重複整理。

## 6. この作業の鉄則（外すと事故る前提）

- 本番未稼働＝既存データは捨ててよい。現状のデータ分布に設計を引きずらない。
- 本番の破壊的変更は必ず：バックアップ→dry-run（BEGIN→変更→確認→ROLLBACK）→PO自筆GO→本実行→実測確認。自己申告でなく測定で確認。
- 実DB確認は本番tenant_004・読み取り専用（PGOPTIONS="-c default_transaction_read_only=on"）。SQLはファイル転送してpsql -f（クォート崩れ回避）。**2026-07-14時点、ローカル環境からのDB直結手段は無く、SSH prod1経由→docker compose exec postgresでのVPS内実行が唯一の確認済み経路。**
- 疲労時・深夜に本番の重い変更を始めない。
- **2026-07-14 新規追加ルール**: 編集を始める前（新規worktreeでも既存worktreeへの追加コミットでも）、対象ファイルの現在の内容を`git diff origin/main -- <対象ファイル>`で確認し、直前に本店へマージされた変更が土台に反映されているか確かめること。PRマージ前は`.claude-pipeline/active-work.md`にこの作業の行が存在するか確認し、無ければ完了報告に明記し追記すること（executor-preamble.mdに追記済み・PR #2905）。
- **2026-07-14 新規追加ルール**: 「ファイルが無い」と報告する前に、ローカルのls/find/catだけで判定せず、必ず`git show origin/main:<path>`で本店に直接確認すること（PR #2891）。

## 7. 範囲外（このテーマで扱わない）

- 人事（スタッフ・シフト・ロール）、送料は別テーマ。
- 商品マスタ（product-master）自体の設計は別テーマ。分類マスタは既存product-masterのtcg_type/tcg_category等を「流用」するのみで、product-master自体には手を入れない。
- 在庫（inventory-management）は別テーマ。

## 8. 既知の問題と解決の方向（次回の独立テーマ候補）

### 問題A: worktreeの土台ズレ（2026-07-13/14に3パターン実害・design-partner.md §6に記録済み）
- ①ファイル不在誤報告 ②巻き戻り編集（前便の内容が古い版に戻る） ③台帳記帳漏れ
- 対策済み: executor-preamble.mdへのdiff確認ルール追加（PR #2905）。ただし人手ルールであり、機械強制はまだ無い。

### 問題B: active-work.md（台帳）のDONE化が競合で戻る問題（2026-07-11に特定・根治未実装）
- 原因: 1ファイルを全並列セッションが編集する構造。new-worktree.shがworktree作成のたびに自動追記。
- 根治案（未実装）: 1ブランチ=1ファイルの追記専用にし、台帳ビューは機械集計で生成する。開発プロセス改善テーマとして別途着手。

## 9. 用語ミニ辞典（記憶ゼロでも読めるように）

- lead=見込み客 / deal=商談 / company=顧客の会社 / contact=その会社の担当者(人。※2026-07-14 PO方針でこの概念自体を廃止予定) / order=受注。
- SSOT=同じ事実を1か所だけに持ち、他は参照する考え方。
- 背番号(参照)=中身をコピーせずID等で正本を指すこと（正当）。／ コピー=中身を書き写すこと＝重複（悪い）。
- 台帳(マスタ)=選択肢の正本リスト。フロントはここから選ぶ（自由入力しない）。
- 持ち主の印方式=1つのテーブルに共有値とテナント独自値を同居させ、owner_tenant_id列（NULL=共有／値あり=そのテナント専用）で判別する方式。product-master/product-type-masterで実績あり。今回classification-masterでも採用。
