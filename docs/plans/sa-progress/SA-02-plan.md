# SA-02 計画票 — 会話ログ＋会社集計ビュー（contact粒度）

| 項目 | 内容 |
|------|------|
| 対応ADR | ADR-096（顧客マスタ／CRMデータモデル）、前提: ADR-095 |
| ステータス | ④ 実装中（段階1・3・4/4完了・進捗 80%・KGI承認済み 2026-06-11） |
| 担当 | PO: Shingo ／ Planner: Web Claude ／ recon・実装: Terminal CC |
| 最終更新 | 2026-06-11（Generator・Stage 4完了） |

---

## 1. 計画票（スケジュール）

| # | ステップ | 担当 | 状態 | 完了日 |
|---|---------|------|------|--------|
| 1 | KGI承認 | Shingo | ✅ 完了 | 2026-06-11 |
| 2 | recon brief作成（調査指示書） | Planner | ✅ 完了 | 2026-06-11 |
| 3 | architect recon（file:line差分表の記入） | Terminal CC | ⏳ 実施待ち | |
| 4 | 差分レビュー＋KPI数値確定 | Shingo＋Planner | 未 | |
| 5 | 設計確定（What/Why、recon相互参照） | Planner | 未 | |
| 6 | 実装 | Generator（Terminal CC） | 未 | |
| 7 | 検証ゲート（CI・ビジュアル差分・process-artifacts） | 自動＋Reviewer | 未 | |
| 8 | 本番反映＋KGI実測＋SA-01横断チェック | Terminal CC／Shingo | 未 | |

---

## 2. KGI定義（案 — Shingo承認待ち）

> KGI＝「本番でこれが観測できたら成功」という最終ゴール。数えられる形で書く。

| # | KGI | 種別 |
|---|-----|------|
| G1a | API/Webhook連携済みチャネルで受信したメッセージの**100%**が自動で会話ログに保存され、1人の連絡先（contact）に紐づく。取りこぼしは自動検知（アラート）できる | データフロー（自動） |
| G1b | 未連携チャネルのやり取りはスレッド欄から**チャット感覚（1分以内）**で手動記録でき、自動取り込みと**同じログ・同じ集計・同じ翻訳/解析・同じスレッド表示**に乗る | データフロー（手動） |
| G2 | 会話数・最終会話日時・会話要約は**自動計算のみ**。手入力できる画面・カラムが**0箇所** | 派生値（ADR-095原則） |
| G3 | 会社（company）を開くと、所属する各連絡先の会話が**1画面に集約表示**され、**3クリック以内**で個別の原文＋訳文に到達できる | UI/UX |
| G4 | 会話に関する同じ事実（要約・最終会話日時など）を手入力で二重に持つ場所が**0箇所** | SSOT |

**承認欄**: ☑ **承認（Shingo / 2026-06-11）**

### 手動記録（G1b）の確定要件 — 2026-06-11 Shingo決定

| 項目 | 決定内容 |
|------|---------|
| 入力単位 | **1メッセージずつ**（会話数・解析の粒度を自動取り込みと揃える） |
| 編集・削除 | **手動記録のみ編集可、編集履歴を残す**。自動取り込み分は従来どおり原文不変 |
| 編集時の挙動 | 原文を編集したら翻訳・商談解析を**自動で再実行**（古い訳が残るズレを防ぐ） |
| 翻訳・商談解析 | **自動取り込みと同じく必ず適用** |
| 識別 | 各ログに手動／自動のフラグを保持（後からチャネル連携が増えても区別できる） |
| スレッド表示 | 手動記録も受信箱のスレッド欄に自動取り込みと**時系列で混在表示**（手動バッジで区別） |
| 入力方法 | スレッド欄に常設のチャット風入力（送/受トグル＋本文＋日時は既定＝今・変更可）。別フォームを開かせない |

**Planner既定（recon・設計で覆し可）**: 記録できる人＝顧客情報の編集権限と同じ／チャネルに「電話」「対面」など手動用を追加できる／v1はテキスト入力のみ（スクショ読み取りはv2候補）。

### 自動／手動の使い分け — 混同防止の構造（2026-06-11追加）

| ルール | 内容 |
|--------|------|
| 入口の排他 | **1チャネル＝1入口**。連携済みチャネルは手動入力ボックスを表示しない（自動のみ）。未連携チャネルは手動のみ。排他の単位は顧客でなく**チャネル**：手動入力のチャネル選択肢には未連携チャネルだけが出る（全チャネル未連携の顧客は常に手動入力可）。チャネルが1つもない顧客は手動チャネル（電話・対面等）を追加した時点でスレッドと入力ボックスが生まれる |
| 取りこぼし | 連携済みチャネルの欠落は手動で補わない。自動検知→後追い取り込み（sweeper）で回収 |
| 連携の昇格 | チャネルが後から連携されたら入力ボックスは消える。過去の手動ログはフラグ付きでそのまま残す |
| 見た目 | 手動メッセージは手動バッジ＋記録者名を表示 |
| 重複ガード | 同一チャネル・近接日時・同一本文の保存時に「似た記録があります」と警告 |
| AI分割（**v2に延期**） | まとめ貼り付け→AI自動分割は**v2で導入**（2026-06-11 Shingo決定。v1はチャット風入力のみ）。導入時も手動入力の補助であり第3の経路ではない。分割結果はプレビューで人が確認してから保存。AI単独で保存しない |
※ 手動チャネルの「記録し忘れ」は機械で検知できない（運用ルールの領域）。

---

## 3. 現状調査結果と差分（recon記入欄 — Terminal CCが file:line 付きで埋める）

> **ルール**: 推測禁止。「現状」列は必ず実コードの file:line を引用。確認できなければ「不明」と書く。
> recon無しでこの先のフェーズへ進めない（在るだけの書類は成果物でない）。

### 調査観点

| 観点 | 現状（file:line） | ADR-096の理想 | 差分 |
|------|-------------------|---------------|------|
| 会話ログの保存先テーブルと構造（原文・言語・翻訳・解析の各列） | **2テーブル混在**。①旧: `meta_messages`（`migrations/041_extend_meta_messages.sql`, test定義 `backend/tests/test_messages.py:111`）— `original_language` / `translated_text` / `analysis` 列なし。②新: `migrations/20260604_090000_create_conversation_logs.sql:34` — `conversation_logs`（id/tenant_id/lead_id/contact_id/company_id/deal_id/channel_type/channel_identity/direction/sender/content_text/original_language/external_message_id/raw_payload/status/translated_text/analysis JSONB/occurred_at/created_at）RLS適用済み。③翻訳キャッシュ: `migrations/094_create_message_translations.sql:26` — `message_translations`（message_id/target_language/translated_text/engine） | 1テーブルに原文・言語・翻訳・解析を全て持つ | `conversation_logs` はスキーマ完備だが**実データは0件**。`meta_messages` から `conversation_logs` への移行パイプラインが未実装 |
| 受信チャネル→会話ログへの取り込み経路（チャネル別の網羅率） | Messenger/Instagram: `backend/app/routers/webhook.py:665-758` → `meta_messages` に保存。Discord: `backend/app/discord_gateway/dm_writer.py:225` → `meta_messages` に保存。WhatsApp/Telegram/Email: 未実装。**全チャネルとも `conversation_logs` への書き込みは未実装** | 全連携チャネルの受信が `conversation_logs` に入る | `conversation_logs` への取り込みルート（webhook→conv_logs）が全チャネル未配線。既存は全て `meta_messages` 止まり |
| 会話数・最終会話日時・会話要約の算出方法 | `migrations/20260604_100000_create_company_stats_view.sql:39` — `v_company_stats` VIEW作成済み（`SELECT COUNT(DISTINCT cl.id), MAX(cl.occurred_at) FROM conversation_logs`）。`backend/app/routers/companies.py:188` — `_fetch_company_stats()` がビューを参照してレスポンスに含める。**会話要約は `conversation_logs.analysis` JSONB内だが集計ビューに未含有** | 集計ビューのみ（書き込み可能カラム禁止） | ビューは実装済み・APIも接続済みだが、`conversation_logs` に実データがないため `conversation_count=0` / `last_conversation_at=NULL` が返る。会話要約の集計定義は未設計 |
| 派生値への手入力経路の有無（UI・API・DB権限） | `v_company_stats` はVIEW（SELECT専用）。`backend/app/routers/companies.py` のPATCH/POST に `conversation_count` / `last_conversation_at` フィールドなし。`backend/app/schemas/company.py` にも該当フィールドなし | 手入力経路 0箇所 | **現状で手入力経路なし**（G2に対してOK）。`conversation_logs.analysis` フィールドへの書き込みAPIは未実装のため同様に問題なし |
| 会社（companies）と連絡先（contact）の紐づけ構造 | `backend/app/schemas/contact.py:95` — `company_id: int`（必須）。`contacts` テーブルは `company_id` で親会社に紐づく。`conversation_logs` は `company_id` と `contact_id` を直接持つ（`migrations/20260604_090000_create_conversation_logs.sql:39`）。`v_company_stats` は `company_id` で集計（contact経由なし） | 会社集計はcontact粒度の会話を集約 | 構造上は `contact_id` で会話を絞り込んで会社に集約できる。ただし `v_company_stats` は `company_id` 直接集計のみ（contact_id粒度の内訳表示は未実装） |
| カルテUI（受信箱）での会話表示の現状 | `frontend/src/pages/inbox/InboxKartePanel.tsx:1` — 存在するがADR-108の3タブ再編は Status=Proposed（未実装）。`frontend/src/pages/inbox/InboxMessageThread.tsx:1` — スレッド表示コンポーネント存在（`meta_messages` ベース）。**会社→contact→会話への階層ナビなし。手動メッセージ入力UI・手動バッジ・チャネル選択なし** | 会社→contact→原文＋訳文へ3クリック以内 | G3 未達。company画面→contact粒度の会話集約ページが存在しない。スレッド欄は `lead_id` ベースで会社横断表示不可 |
| 既知関連実装の被覆率: カルテ再編（ADR-108/110）／翻訳（ADR-088/110/SA-17）／lead_channels（ADR-119） | ADR-108: Status=Proposed・未実装。翻訳基盤: `backend/app/services/message_translator.py:1`（グロッサリ適用・確信度スコアリング・`translate_inbound()`実装済み）。即時翻訳未実装（Celeryバッチのみ: `backend/app/tasks/translation.py:29`）。sweeper: `backend/app/services/translation_monitor.py:1` 実装済み。lead_channels: `migrations/20260607_120000_create_lead_channels.sql` + `webhook.py:489` で活用中 | — | 翻訳コア関数（`translate_inbound()`）・sweeper・lead_channels は流用可能。即時翻訳発火の配線未実装。`conversation_logs` への翻訳結果書き込みパスなし |
| 編集履歴（監査ログ）の既存パターンの有無 | `backend/app/services/audit.py:1` — `record_audit_log(db, tenant_id, user_id, action, table_name, record_id, old_data, new_data)` 実装済み。副テーブル差分（`build_subtable_diff`）も実装済み。`contacts.py:458`、`deals.py:217` などで利用中 | 手動記録の編集履歴を残せる土台 | **流用可能なパターン存在**。`audit_logs` テーブルに旧値/新値JSONを記録する仕組みは既存。`conversation_logs` の手動記録編集時にこれを呼べる |
| 手動メッセージを翻訳・解析パイプラインに乗せる経路（即時翻訳発火の流用可否） | `backend/app/services/message_translator.py` の `translate_inbound()` 関数が存在。現在は `backend/app/tasks/translation.py:72-80` のバッチが `meta_messages` を対象に呼ぶ設計。**手動保存時の即時発火配線なし** | 手動も自動と同じ翻訳/解析が走る | `translate_inbound()` 自体は流用可。手動メッセージ保存APIに翻訳タスクをenqueueするhookを追加すれば実現可能。`conversation_logs` を対象とした翻訳バッチの再配線も必要 |
| チャネル定義の現状（「電話」「対面」等の手動チャネルを追加できる構造か） | `lead_channels.platform` は `VARCHAR(30)` 文字列型（`migrations/20260607_120000_create_lead_channels.sql:19`）。ENUMではない。`conversation_logs.channel_type` も `VARCHAR(30)`（`migrations/20260604_090000_create_conversation_logs.sql:41`）。現状値は 'messenger'/'instagram'（`webhook.py:481`）。**チャネルマスタテーブルは存在しない** | 手動チャネルをマスタで追加可能 | VARCHAR自由値のためアプリ制御で追加可能。ただし**チャネルマスタテーブルがない**ため許可値の管理・UI選択肢の提供には別途テーブル or 定数リストが必要 |
| スレッド欄の描画構造（手動メッセージの混在表示・手動バッジ・入力ボックス常設に対応できるか） | `frontend/src/pages/inbox/InboxMessageThread.tsx:1` — `MessagesResponse` 型を受け取りメッセージ一覧を描画。現状は `meta_messages` ベースの自動取り込みのみ。**`is_manual` フラグ対応なし・手動バッジなし・チャネル選択UIなし・手動用入力常設なし** | 手動／自動が時系列で1本のスレッドに混在表示 | コンポーネント自体は存在するが手動記録の混在表示には**大幅改修が必要**。`is_manual`フラグ・バッジ・入力ボックス常設・チャネル選択を追加実装する必要あり |
| 連携済みチャネルで「アプリ外から送った送信分」がwebhookで自動取得できる範囲（チャネル別） | Messenger/Instagram: Meta webhook は受信（inbound）を処理（`webhook.py:655`）。スタッフが外部から送った送信分（echo）はMeta側でエコー設定が必要で現状未設定。Discord: `dm_writer.py` でoutbound送信をmeta_messagesに記録あり。WhatsApp/Telegram: webhook未実装 | 取得できない分の扱いをShingo判断 | **Messenger/Instagram のエコー受信は未設定**。取得できない送信分が会話ログに欠落するか、手動補完の対象か → Shingo判断が必要 |

### recon結論（2026-06-11 Terminal CC記入）

#### 流用できるもの（file:line付き）

| 資産 | 場所 | 流用内容 |
|------|------|---------|
| `conversation_logs` テーブル | `migrations/20260604_090000_create_conversation_logs.sql:34` | ADR-096が求める全列を持つ。RLS済み。**このテーブルが目標の保存先** |
| `v_company_stats` ビュー | `migrations/20260604_100000_create_company_stats_view.sql:39` | 会話数・最終会話日時の自動集計。APIも接続済み（`companies.py:188`） |
| `translate_inbound()` 関数 | `backend/app/services/message_translator.py` | 手動メッセージの翻訳に流用可（グロッサリ・確信度スコア込み） |
| sweeper（翻訳取りこぼし拾い） | `backend/app/services/translation_monitor.py:1` | 手動記録の翻訳失敗検知にも流用可 |
| `lead_channels` テーブル | `migrations/20260607_120000_create_lead_channels.sql` + `webhook.py:489` | チャネル識別・名寄せ基盤として流用可 |
| `record_audit_log()` | `backend/app/services/audit.py:1` | 手動記録の編集履歴に流用可 |
| `InboxMessageThread.tsx` | `frontend/src/pages/inbox/InboxMessageThread.tsx:1` | 改修ベースとして流用可 |

#### 不足しているもの（＝今回作るもの）

1. **webhook → `conversation_logs` 取り込みパイプライン**（Messenger/Instagram/Discord の受信を `meta_messages` ではなく `conversation_logs` に書く、または両方に書いて移行）
2. **手動メッセージ保存API**（`POST /conversation_logs`・`is_manual=true`・チャネル選択）
3. **手動メッセージ編集API + 編集履歴**（`PATCH /conversation_logs/{id}`・audit_log連携・翻訳再実行hook）
4. **即時翻訳発火の配線**（保存API → Celeryタスクenqueue。`conversation_logs` を対象とした翻訳バッチ再配線）
5. **チャネルマスタテーブル or 定数リスト**（手動チャネル（電話・対面等）の許可値管理）
6. **重複ガード**（同一チャネル・近接日時・同一本文の警告）
7. **会社→contact粒度の会話集約ページ**（G3: 3クリック以内達成）
8. **`InboxMessageThread.tsx` 改修**（`is_manual` バッジ・入力ボックス常設・チャネル選択）
9. **会話要約の集計定義**（`conversation_logs.analysis` からの要約抽出仕様）
10. **受信取りこぼし検知**（sweeper が `conversation_logs` を対象に欠落を検知・通知）

#### 設計前にShingo判断が必要な事項

| # | 論点 | 事実 |
|---|------|------|
| J1 | Messenger/Instagramのエコー受信（アプリ外から送った送信分）を取得するか | Meta側でエコー設定が必要。現状未設定（`webhook.py:655`参照）。設定すると全送信メッセージがwebhookに届くがMeta申請が必要な可能性あり |
| J2 | `meta_messages` から `conversation_logs` への移行方針 | 既存データ（highlife-jpn本番の `meta_messages` 蓄積分）をconversation_logsに移行するか、移行せず新規取り込みからconversation_logsに切り替えるか |
| J3 | 手動記録の削除を許可するか | ADR-096・G1bには削除可否の定義なし。削除可なら論理削除（`deleted_at`）か物理削除か |
| J4 | 会話要約の集計仕様 | `analysis` JSONB内の要約フィールドをどう集約するか（最新N件の要約、全件、AIでまとめ直すか）|

---

## 4. KPI設定（recon後に数値確定）

> KPI＝KGIに向かう途中の測定指標。**システムが自動計測できる形**にする（手集計禁止）。

| # | KPI候補 | 目標 | 測り方（recon後確定） |
|---|---------|------|----------------------|
| K1 | 会話ログ取り込み率（受信数に対する保存数） | 100% | `meta_messages`の受信件数 vs `conversation_logs`の件数を突合（移行完了後）。sweeper検知で欠落をアラート |
| K2 | 派生値（conversation_count/last_conversation_at）への手入力上書き件数 | 0件 | `v_company_stats` がVIEWのためDB層で保証。PATCH APIにフィールドなし（`companies.py`スキーマ確認）|
| K3 | 会社集計ビューの到達クリック数 | 3以内 | Playwright E2E: 会社ページ→会話表示→原文+訳文 のクリック数計測 |
| K4 | 取りこぼし検知→通知までの時間 | ≤15分（sweeper周期内） | sweeper実行→Discord通知までの時刻差（`translation_monitor.py` 参考に実装） |
| K5 | 手動記録の翻訳自動適用率 | 100% | 手動保存後の `conversation_logs.translated_text` がNULLの件数（sweeper周期内でゼロ） |

---

## 5. 実装記録

| 日付 | PR | 内容 | 状態 |
|------|----|------|------|
| 2026-06-11 | #1932 | 段階1: channel_masters + webhook→conv_logs 配線 + エコー受信 + 冪等 | マージ・本番デプロイ済み |
| 2026-06-11 | #1937 | 段階3: 手動記録 API + スレッドUI + 翻訳発火 + 論理削除 + 重複ガード + チャネル管理UI + 集計ビュー論理削除除外 | マージ・本番デプロイ済み |
| 2026-06-11 | #1945 | 段階4: 会社詳細→会話履歴タブ（contact集約・混在表示）+ GET /companies/{id}/conv-logs API | マージ・本番デプロイ済み |
| 2026-06-11 | #1952/#1965 | 段階2: 移行キット準備完了（migrate script・verify script・rollback手順・analysis マーカー方式）| **Shingo GO待ち（本番未実行）** |

---

## 6. チェックシート（完了条件）

- [x] ① KGI承認（Shingo 2026-06-11）
- [x] ② recon完了（差分表が file:line で埋まっている）— 2026-06-11 Terminal CC
- [x] ③ 設計doc完成（reconとADR-096を相互参照・外部事例欄記入）— 2026-06-11 Planner
- [x] ④ 実装PRマージ（process-artifactsゲート通過）— PR #1932/#1937/#1945 2026-06-11
- [x] ⑤ 本番反映（CI緑＋smoke通過）— 2026-06-11 段階1・3・4 全デプロイ済み
- [ ] ⑥ KGI G1〜G4を本番で実測確認
- [ ] SA-01横断チェックシート記入（✅のみ）
- [x] 総合進捗表（00-SA-OVERVIEW.md）の更新
