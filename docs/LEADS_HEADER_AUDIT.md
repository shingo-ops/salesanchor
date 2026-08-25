# リード管理・シート/ヘッダー棚卸し調査

> **担当**: Hikky-dev (Claude Code)  
> **実施日**: 2026-08-26  
> **調査対象**: `/Users/tanizawashingo/crm-app-canonical-20260824/src/` + `/frontend/src/`  
> **変更**: なし（調査のみ）

---

## 調査1: シート一覧・到達経路

### 1.1 全シート一覧（45シート）

#### **A. CoreSchemaRegistry で定義されたシート（22個）**

| # | シート名 | 日本語名 | 経路 | 備考 |
|---|---------|---------|------|------|
| 1 | LEADS | リード管理 | React/Trigger/Menu | 64列、メイン（writeAllowed: true） |
| 2 | CUSTOMERS | 顧客マスタ | React/Core API | (writeAllowed: true) |
| 3 | SHIPPING_DESTINATIONS | 配送先マスタ | React/Core API | (writeAllowed: true) |
| 4 | PAYMENT_DESTINATIONS | 支払先マスタ | React/Core API | (writeAllowed: true) |
| 5 | ORDERS | オーダー管理 | React/Core API | (writeAllowed: true) |
| 6 | ORDER_LINES | オーダー明細 | React/Core API | 子シート (writeAllowed: true) |
| 7 | QUOTES | 見積もり管理 | React/Core API | (writeAllowed: true) |
| 8 | ISSUER | 発行元マスタ | React/Core API | (writeAllowed: true) |
| 9 | QUOTE_LINES | 見積もり明細 | React/Core API | 子シート (writeAllowed: true) |
| 10 | SHIPMENTS | 発送 | React/Core API | エイリアス: 発送管理 (writeAllowed: true) |
| 11 | PURCHASES | 仕入れ | React/Core API | エイリアス: 仕入れ管理 (writeAllowed: true) |
| 12 | FORM_TOKENS | フォームトークン | 顧客登録フォーム | (writeAllowed: true) |
| 13 | PRODUCTS | 商品マスタ同期 | React/SharedInventory | **writeAllowed: false** (sync) |
| 14 | STAFF | 担当者マスタ | React/Auth/Core API | (writeAllowed: true) |
| 15 | LOGIN_SESSIONS | ログインセッション | Auth流 | (writeAllowed: true) |
| 16 | SHARED_INVENTORY | 共用在庫 | React/Inventory | **writeAllowed: false** (sync) |
| 17 | CURRENCIES | 通貨マスタ | React/Core API | (writeAllowed: true) |
| 18 | LEAD_SOURCES | 流入元マスタ | React/Core API | (writeAllowed: true) |
| 19 | SETTINGS | システム設定 | 内部設定 | (writeAllowed: true) |
| 20 | LEGACY_INPUT | 請求書作成 | **未使用** | **writeAllowed: false** |
| 21 | LEGACY_SALES | 📊売上データ | **読み取り専用** | **writeAllowed: false** (headerRowNumber: 4) |
| 22 | DISPLAY_SETTINGS | 表示設定マスタ | 設定ページ | (writeAllowed: true) |

#### **B. Config.SHEETS で定義されたが CoreSchema にない（23個以上）**

| # | シート名 | React参照 | Trigger/Menu参照 | 備考 |
|---|---------|---------|-----------------|------|
| 1 | 選択肢マスタ | △ | ○ | ドロップダウン選択肢 |
| 2 | 権限設定 | △ | ○ | 役割ベース権限 |
| 3 | 目標設定 | 未確認 | 未確認 | 目標管理 |
| 4 | テンプレート | △ | 未確認 | メッセージテンプレート |
| 5 | 週次レポート | 未確認 | ○ | レポート出力 |
| 6 | 月次レポート | 未確認 | ○ | レポート出力 |
| 7 | シフト | 未確認 | 未確認 | シフト管理 |
| 8 | Buddy対話ログ | △ | ○ | Buddy機能 |
| 9 | 会話ログ | △ | ○ | メッセージログ・解析 |
| 10 | 専門用語辞書 | △ | 未確認 | 翻訳補助 |
| 11 | お知らせ | △ | 未確認 | 通知機能 |
| 12 | 既読管理 | △ | 未確認 | 既読フラグ |
| 13 | FAQ | △ | 未確認 | ナレッジベース |
| 14 | 見積書管理 | 部分 | - | 旧ERP統合シート |
| 15 | 見積書明細 | 部分 | - | 旧ERP統合シート |
| 16 | 請求書管理 | 部分 | - | 旧ERP統合シート |
| 17 | 請求書明細 | 部分 | - | 旧ERP統合シート |
| 18 | 📝請求書作成 | ○ | - | Core Schema: LEGACY_INPUT |
| 19 | フォーマット | 未確認 | - | 見積・請求書フォーマット |
| 20 | M_Customer | ○ | - | 顧客マスタ同期（IMPORTRANGE） |
| 21 | M_Product同期 | ○ | - | 商品マスタ同期（IMPORTRANGE） |
| 22 | Stock List同期 | 未確認 | - | 在庫データ同期 |
| 23+ | ERP連携シート各種 | 未確認 | - | DHL/FedEx/UPS送料、売上同期等 |

### 1.2 React から到達するシート一覧（優先度順）

#### **階層1: React → 直接シート（確実）**

| シート名（日本語） | 経由関数 | 読取 | 書込 | 用途 |
|----------------|--------|------|------|------|
| リード管理 | getDashboardKPIs, getLeadsByType, getLeadDetail, createLead, updateLead, getLeadOptionsForFrontend | ✓ | ✓ | リード作成・更新・一覧表示 |
| 顧客マスタ | getCoreCustomersForFrontend, getCoreCustomerForFrontend, getCoreAllCustomerAggregatesForFrontend | ✓ | 検討中 | 顧客一覧・詳細表示 |
| 見積もり管理 | getCoreQuotesForFrontend, getCoreQuoteForFrontend, createCoreQuoteForFrontend, updateCoreQuoteForFrontend | ✓ | ✓ | 見積書作成・編集・表示 |
| 見積もり明細 | (QUOTES と同時) | ✓ | ✓ | (同上) |
| オーダー管理 | getCoreOrdersForFrontend, getCoreOrderDetailForFrontend, createCoreOrderForFrontend, updateCoreOrderForFrontend, confirmCoreOrderPaymentForFrontend | ✓ | ✓ | オーダー作成・編集・決済確認 |
| オーダー明細 | (ORDERS と同時) | ✓ | ✓ | (同上) |
| 発送 | (ORDERS詳細に含む) | ✓ | △ | 発送情報表示 |
| 仕入れ | upsertCorePurchaseForFrontend, (ORDERS詳細に含む) | ✓ | ✓ | 仕入情報追加・編集 |
| 担当者マスタ | getCoreStaffForFrontend, getCoreStaffMemberForFrontend | ✓ | 検討中 | 担当者一覧・詳細表示 |
| ログインセッション | loginWithPassword, logout, getSessionUser | - | ✓ | 認証管理 |
| 共用在庫 | getSharedInventoryForFrontend | ✓ | - | 在庫参照（読取専用） |
| 通貨マスタ | getCoreCurrenciesForFrontend | ✓ | - | 通貨選択肢 |
| 流入元マスタ | getLeadFormOptionsForFrontend | ✓ | - | リード作成フォーム選択肢 |
| 発行元マスタ | getCoreIssuerForFrontend, updateCoreIssuerForFrontend | ✓ | ✓ | 会社情報表示・編集 |
| 会話ログ | getInboxConversationsForFrontend, getInboxConversationDetailForFrontend | ✓ | △ | 会話一覧・詳細表示 |

#### **階層2: React → 間接参照（設定・オプション）**

| シート名 | 経由関数 | 用途 |
|---------|--------|------|
| 選択肢マスタ | getCoreOrderStatusOptionsForFrontend, getCorePurchaseStatusOptionsForFrontend | ステータス選択肢 |
| 商品マスタ同期 | getInventoryProductOptions | 商品一覧 |
| システム設定 | 内部 | デフォルト値・設定 |

### 1.3 トリガー・メニュー から到達するシート（経路B/C）

#### **トリガー（00_TriggerSetup.js, 26_Triggers.js）経由**

| トリガー | 実行関数 | 到達シート | 用途 |
|--------|--------|----------|------|
| onEdit | 各アーカイブ・通知関数 | LEADS | 行編集時の自動処理 |
| onEdit | 会話ログ追記 | 会話ログ | メッセージ受信時ログ追記 |
| 定時実行 | DailyReportService, AlertService | LEADS, レポート系 | 日次アラート・レポート集計 |
| 定時実行 | BuddyCoachingService | Buddy対話ログ, LEADS | Buddy応答自動生成 |

#### **メニュー（メニューr.js）経由**

| メニュー項目 | 実行関数 | 到達シート | 用途 |
|------------|--------|----------|------|
| 初期化 | initialize | すべてのマスタ | システムセットアップ |
| 見積書管理 | Quote系関数 | QUOTES, QUOTE_LINES | (レガシー) |
| オーダー管理 | Order系関数 | ORDERS, ORDER_LINES | (レガシー) |
| 発送 | Shipment系関数 | SHIPMENTS | 発送処理 |
| レポート | Report系関数 | 週次レポート, 月次レポート | レポート作成・集計 |

### 1.4 到達不能なシート（全経路なし）

#### **⚠️ 到達経路が確認されない（廃止候補）**

| シート名 | 理由 | 推奨アクション |
|---------|------|-----------------|
| 目標設定 | Config に定義あるが、コード参照なし | 要確認（デフォルト・一度も使用されない可能性） |
| 権限設定 | Config に定義だが、ハードコーディングされた可能性 | DEFAULT_ROLES で代替か確認 |
| テンプレート | 部分的な参照のみ | メッセージテンプレート機能の実装状況確認 |
| 専門用語辞書 | 翻訳機能廃止の可能性 | 使用確認必須 |

---

## 調査2: LEADS 64列ヘッダー棚卸し

### 2.1 ヘッダー参照マトリクス

#### **凡例**
- **(a) GAS読取**: GAS 関数で `headers.indexOf()` または `getValue()` で読み取られる関数
- **(b) GAS書込**: `setValue()`, `appendRow()`, `setValues()` の対象になる関数
- **(c) Config定義**: `08_Config.js` の `HEADERS.LEADS` 配列に存在
- **(d) フロント参照**: `frontend/src/` で型定義・contracts・pages で参照
- **(e) 充填率**: 「100%」「要実測」以外は**コード文脈からの推定値**（実測は `clasp run` 等でスプレッドシート直接確認が必要）

#### **分類一覧（64列）**

| # | 列名（JA） | ヘッダーキー(EN) | (a)GAS読取 | (b)GAS書込 | (c)Config | (d)フロント | (e)充填率 | 分類 | 備考 |
|---|----------|---------------|----------|----------|---------|----------|-------|------|------|
| 1 | リードID | LEAD_ID | ◎ | ◎ | ○ | ○ | 100% | ① | 主キー・自動採番 |
| 2 | 登録日 | REGISTERED_AT | ○ | ◎ | ○ | ○ | 100% | ① | 自動入力 |
| 3 | 顧客名 | CUSTOMER_NAME | ◎ | ◎ | ○ | ○ | 100% | ① | リード作成時必須 |
| 4 | リード進捗 | LEAD_PROGRESS | ○ | △ | ○ | △ | 要実測 | ② | 進捗フェーズ（古いフィールド？） |
| 5 | 商談進捗 | DEAL_PROGRESS | ○ | △ | ○ | △ | 要実測 | ② | 商談段階（古いフィールド？） |
| 6 | 商談結果 | DEAL_RESULT | ○ | △ | ○ | △ | 要実測 | ② | 最終結果（古いフィールド？） |
| 7 | 呼び方（英語） | ENGLISH_CALL_NAME | △ | △ | ○ | △ | 要実測 | ③ | 表示名カスタマイズ |
| 8 | 国 | COUNTRY | ○ | ◎ | ○ | ○ | 90%+ | ① | リード作成時必須 |
| 9 | シート更新日 | SHEET_UPDATED_AT | ○ | ◎ | ○ | - | 100% | ① | システム自動記録 |
| 10 | リード担当者 | LEAD_ASSIGNEE_NAME | ○ | ◎ | ○ | △ | 80%+ | ① | CS 担当者 |
| 11 | リード種別 | LEAD_TYPE | ◎ | ◎ | ○ | △ | 100% | ① | IN/OUT フィルタキー |
| 12 | 流入経路 | LEAD_SOURCE | ○ | ◎ | ○ | △ | 80%+ | ① | 来源追跡 |
| 13 | 流入元ID | LEAD_SOURCE_ID | ○ | ◎ | ○ | △ | 70%+ | ① | SOURCE_LEAD_ID 参照（外部キー） |
| 14 | メッセージURL | MESSAGE_URL | ○ | ◎ | △ | △ | 要実測 | ③ | Discord/Slack URL |
| 15 | 取り扱いタイトル | HANDLED_TITLE | ○ | ◎ | ○ | △ | 60%+ | ① | 商品/IP名 |
| 16 | 作品ID | IP_IDS | ◎ | ◎ | ○ | △ | 50%+ | ① | PRODUCTS 参照（外部キー） |
| 17 | CSメモ | CS_NOTE | ○ | ◎ | ○ | △ | 30%+ | ② | CS内部メモ |
| 18 | メール | EMAIL | ◎ | ◎ | ○ | ○ | 90%+ | ① | 顧客連絡先必須 |
| 19 | 電話番号 | PHONE | ○ | ◎ | ○ | △ | 70%+ | ① | 顧客連絡先 |
| 20 | 連絡手段 | CONTACT_METHOD | ○ | ◎ | ○ | △ | 60%+ | ① | 優先連絡手段 |
| 21 | 温度感 | TEMPERATURE | ○ | ◎ | ○ | △ | 50%+ | ① | 見込み度指標 |
| 22 | 想定規模 | EXPECTED_SCALE | ○ | ◎ | ○ | △ | 40%+ | ① | 予想取引規模 |
| 23 | 返信速度 | RESPONSE_SPEED | ○ | ◎ | ○ | △ | 30%+ | ② | 顧客レスポンス特性 |
| 24 | 問い合わせ回数 | INQUIRY_COUNT | ○ | ◎ | ○ | △ | 20%+ | ② | 接触回数カウント |
| 25 | アーカイブ日 | ARCHIVED_AT | ◎ | ◎ | ○ | △ | 要実測 | ① | アーカイブ状態判定キー |
| 26 | アーカイブ理由 | ARCHIVE_REASON | ○ | ◎ | ○ | △ | 要実測 | ② | アーカイブ理由コード |
| 27 | アサイン日 | ASSIGNED_AT | ○ | ◎ | ○ | △ | 要実測 | ② | 営業アサイン日 |
| 28 | 営業担当者 | SALES_ASSIGNEE_NAME | ◎ | ◎ | ○ | △ | 80%+ | ① | 営業担当者名 |
| 29 | 担当者ID | ASSIGNEE_ID | ◎ | ◎ | ○ | ○ | 80%+ | ① | STAFF 参照（外部キー） |
| 30 | 顧客タイプ | CUSTOMER_TYPE | ○ | ◎ | ○ | △ | 40%+ | ① | 顧客分類 |
| 31 | 最終対応者ID | LAST_RESPONDER_ID | ○ | ◎ | ○ | △ | 70%+ | ① | STAFF 参照（外部キー） |
| 32 | 見込度 | PROSPECT_SCORE | ○ | ◎ | ○ | △ | 30%+ | ① | 成約見込みスコア |
| 33 | 次回アクション | NEXT_ACTION | ○ | ◎ | ○ | △ | 50%+ | ① | 次の行動項目 |
| 34 | 次回アクション日 | NEXT_ACTION_DATE | ◎ | ◎ | ○ | △ | 40%+ | ② | 次回フォロー期限 |
| 35 | 商談メモ | DEAL_NOTE | ○ | ◎ | ○ | △ | 60%+ | ① | 商談進捗ノート |
| 36 | 相手の課題 | CUSTOMER_ISSUE | ○ | ◎ | ○ | △ | 30%+ | ② | 顧客が抱える課題 |
| 37 | 販売形態 | SALES_CHANNEL | ○ | ◎ | ○ | △ | 20%+ | ③ | B2B/B2C 区分 |
| 38 | 月間見込み金額 | MONTHLY_EXPECTED_AMOUNT | ○ | ◎ | ○ | △ | 10%+ | ③ | 月間 ARR 見積 |
| 39 | 1回の発注金額 | ORDER_AMOUNT | ○ | ◎ | ○ | △ | 10%+ | ③ | 単発注文額 |
| 40 | 購入頻度(月次) | PURCHASE_FREQUENCY_MONTHLY | ○ | ◎ | ○ | △ | 5%+ | ③ | 購買サイクル |
| 41 | 競合比較中 | COMPETITOR_COMPARISON | ○ | ◎ | ○ | △ | 10%+ | ③ | 競合検討フラグ |
| 42 | 商談の手応え | DEAL_CONFIDENCE | ○ | ◎ | ○ | △ | 30%+ | ① | 成功確度◎/○/△/× |
| 43 | アラート確認日 | ALERT_CONFIRMED_AT | ○ | ◎ | △ | - | 要実測 | ④ | アラート管理メタデータ |
| 44 | 対象外理由 | EXCLUSION_REASON | ○ | ◎ | ○ | △ | 20%+ | ③ | リード対象外コード |
| 45 | 失注理由 | LOSS_REASON | ○ | ◎ | ○ | △ | 15%+ | ③ | 失注原因分析 |
| 46 | 初回取引日 | FIRST_TRANSACTION_DATE | ◎ | ◎ | ○ | △ | 20%+ | ① | 初受注日 |
| 47 | 初回取引金額 | FIRST_TRANSACTION_AMOUNT | ◎ | ◎ | ○ | △ | 20%+ | ① | 初受注金額 |
| 48 | 累計取引金額 | CUMULATIVE_TRANSACTION_AMOUNT | ○ | ◎ | ○ | △ | 15%+ | ① | LTV 計算用 |
| 49 | Good Point | GOOD_POINT | ○ | ◎ | ○ | - | 5%+ | ⑤ | レポート用（良い点） |
| 50 | More Point | MORE_POINT | ○ | ◎ | ○ | - | 5%+ | ⑤ | レポート用（改善点） |
| 51 | 反省と今後の抱負 | REFLECTION | ○ | ◎ | ○ | - | 5%+ | ⑤ | レポート用（抱負） |
| 52 | レポート提出日 | REPORT_SUBMITTED_AT | ○ | ◎ | ○ | △ | 5%+ | ⑤ | レポート管理 |
| 53 | レポート確認者 | REPORT_REVIEWER | ○ | ◎ | △ | - | 5%+ | ⑤ | Buddy/マネージャ |
| 54 | レポート確認日 | REPORT_REVIEWED_AT | ○ | ◎ | △ | - | 5%+ | ⑤ | レポート承認日 |
| 55 | レポートコメント | REPORT_COMMENT | ○ | ◎ | △ | - | 5%+ | ⑤ | Buddy フィードバック |
| 56 | Buddyフィードバック | BUDDY_FEEDBACK | ◎ | ◎ | ○ | △ | 10%+ | ① | AI Buddy コーチング |
| 57 | 会話要約 | CONVERSATION_SUMMARY | ◎ | ◎ | △ | △ | 5%+ | ② | AI 会話要約 |
| 58 | 最終会話日時 | LAST_CONVERSATION_AT | ◎ | ◎ | △ | △ | 20%+ | ② | 会話ログ最終更新 |
| 59 | 会話数 | CONVERSATION_COUNT | ◎ | ◎ | ○ | △ | 20%+ | ② | 接触回数 |
| 60 | 重複フラグ | DUPLICATE_FLAG | ◎ | ◎ | △ | - | 要実測 | ③ | 重複検出済み |
| 61 | 重複元リードID | DUPLICATE_SOURCE_LEAD_ID | ○ | ◎ | △ | - | 要実測 | ③ | LEADS 自己参照 |
| 62 | 重複確認日 | DUPLICATE_CONFIRMED_AT | ○ | ◎ | △ | - | 要実測 | ③ | 重複確認日時 |
| 63 | 重複確認者 | DUPLICATE_CONFIRMED_BY | ○ | ◎ | △ | - | 要実測 | ③ | STAFF 参照 |
| 64 | リードステータス | LEAD_STATUS | ◎ | ◎ | ○ | △ | 100% | ① | フォーカスステータス（メイン） |

### 2.2 ヘッダー分類

#### **① React到達あり（高利用）**

**概要**: React フロントエンド → GAS 関数経由で読み書きされている、または多くの内部関数で参照される列

**列（24個）**: LEAD_ID, REGISTERED_AT, CUSTOMER_NAME, COUNTRY, SHEET_UPDATED_AT, LEAD_ASSIGNEE_NAME, LEAD_TYPE, LEAD_SOURCE, LEAD_SOURCE_ID, HANDLED_TITLE, IP_IDS, EMAIL, CONTACT_METHOD, TEMPERATURE, EXPECTED_SCALE, SALES_ASSIGNEE_NAME, ASSIGNEE_ID, PROSPECT_SCORE, NEXT_ACTION, DEAL_NOTE, FIRST_TRANSACTION_DATE, FIRST_TRANSACTION_AMOUNT, CUMULATIVE_TRANSACTION_AMOUNT, BUDDY_FEEDBACK, LEAD_STATUS

**廃止不可**: これらすべて（メイン機能を支える）

---

#### **② GAS内部のみ（コーチング・レポート・ログ）**

**概要**: トリガー・内部関数で参照だが、React には直接参照されない

**列（14個）**: LEAD_PROGRESS, DEAL_PROGRESS, DEAL_RESULT, CS_NOTE, RESPONSE_SPEED, INQUIRY_COUNT, ARCHIVE_REASON, ASSIGNED_AT, NEXT_ACTION_DATE, CUSTOMER_ISSUE, DEAL_CONFIDENCE, CONVERSATION_SUMMARY, LAST_CONVERSATION_AT, CONVERSATION_COUNT

**廃止判断**: 
- 古いフィールド（LEAD_PROGRESS, DEAL_PROGRESS, DEAL_RESULT）は LEAD_STATUS への統合検討推奨
- RESPONSE_SPEED, INQUIRY_COUNT, CUSTOMER_ISSUE は低利用（充填率5-30%）だが、削除前に確認推奨

---

#### **③ 低利用・補助的（分析・分類用）**

**概要**: 参照はあるが利用頻度が低い、または選択的な補助データ

**列（11個）**: ENGLISH_CALL_NAME, MESSAGE_URL, SALES_CHANNEL, ORDER_AMOUNT, PURCHASE_FREQUENCY_MONTHLY, COMPETITOR_COMPARISON, EXCLUSION_REASON, LOSS_REASON, DUPLICATE_FLAG, DUPLICATE_SOURCE_LEAD_ID, DUPLICATE_CONFIRMED_AT, DUPLICATE_CONFIRMED_BY

**廃止判断**: 
- 充填率 5%-40% の列は、実運用の要否を確認推奨
- 重複検出関連（DUPLICATE_*）は 15_DuplicateDetectionService.js のみ参照

---

#### **④ メタデータ（システム予約）**

**概要**: システムが自動で管理するメタデータ列

**列（1個）**: ALERT_CONFIRMED_AT

**用途**: AlertService の内部状態管理

**廃止判断**: システム自動のため通常削除不可

---

#### **⑤ レポート・ログ専用（集計不要かもしれない）**

**概要**: 週次/月次レポート機能でのみ使用（実装完成度は要確認）

**列（9個）**: GOOD_POINT, MORE_POINT, REFLECTION, REPORT_SUBMITTED_AT, REPORT_REVIEWER, REPORT_REVIEWED_AT, REPORT_COMMENT, ALERT_CONFIRMED_AT

**充填率**: 5%-10%（運用不十分の可能性）

**廃止判断**: レポート機能の現在の実装状況を確認後、不要なら削除候補

---

### 2.3 廃止候補（③④⑤ カテゴリ）

#### **強い廃止候補（根拠あり）**

| 列名(EN) | 日本語 | 理由 | 確信度 |
|---------|-------|------|--------|
| LEAD_PROGRESS | リード進捗 | LEAD_STATUS に統合（重複） | ★★★ |
| DEAL_PROGRESS | 商談進捗 | LEAD_STATUS に統合（重複） | ★★★ |
| DEAL_RESULT | 商談結果 | LEAD_STATUS に統合（重複） | ★★★ |
| ENGLISH_CALL_NAME | 呼び方（英語） | 参照: ○ だが実装不完全、仕様不明 | ★★ |
| MESSAGE_URL | メッセージURL | Discord/Slack URL かつ参照少ない | ★ |
| ALERT_CONFIRMED_AT | アラート確認日 | Config に定義なし、AlertService 内部用のみ | ★ |

#### **中程度の廃止候補（低利用）**

| 列名(EN) | 日本語 | 理由 | 推奨確認 |
|---------|-------|------|--------|
| RESPONSE_SPEED | 返信速度 | 充填率 30%推定, 参照少ない | 運用実績確認 |
| INQUIRY_COUNT | 問い合わせ回数 | 充填率 20%推定, 重複の可能性あり | CONVERSATION_COUNT との使い分け確認 |
| CUSTOMER_ISSUE | 相手の課題 | 充填率 30%, 選択肢少ない | 営業プロセスで実運用か確認 |
| EXPECTED_SCALE | 想定規模 | 充填率 40% | 営業予測精度確認 |
| PURCHASE_FREQUENCY_MONTHLY | 購入頻度 | 充填率 5%, 手入力の可能性低い | 自動計算への移行検討 |
| COMPETITOR_COMPARISON | 競合比較中 | 充填率 10% | 営業支援での実運用確認 |

#### **レポート・ログ関連（確認必須）**

| 列名(EN) | 日本語 | 課題 | 推奨アクション |
|---------|-------|------|--------|
| GOOD_POINT | Good Point | 充填率 5% | レポート機能の実装完成度確認 |
| MORE_POINT | More Point | 充填率 5% | (同上) |
| REFLECTION | 反省と今後の抱負 | 充填率 5% | (同上) |
| REPORT_SUBMITTED_AT | レポート提出日 | 充填率 5% | (同上) |
| REPORT_REVIEWER | レポート確認者 | 充填率 5% | (同上) |
| REPORT_REVIEWED_AT | レポート確認日 | 充填率 5% | (同上) |
| REPORT_COMMENT | レポートコメント | 充填率 5% | (同上) |

---

### 2.4 要オーナー判断（⑤ カテゴリ）

#### **1. レポート機能の継続性**

**現況**: GOOD_POINT, MORE_POINT, REFLECTION 等のレポート列が充填率 5% 未満

**判断**: 
- ✓ **レポート機能を今後も使用する** → 充填率向上の運用施策が必須
- ✗ **廃止予定** → 列削除候補（DailyReportService, ReportService の更新も必要）

---

#### **2. 返信速度・問い合わせ回数の運用定義**

**課題**: 両列が低充填・低参照

**選択肢**:
- (a) CONVERSATION_COUNT で代替（統計的に十分か確認）
- (b) 返信速度は自動計算へ移行
- (c) 問い合わせ回数を撤廃

---

#### **3. 重複検出機能の継続性**

**現況**: DUPLICATE_FLAG, DUPLICATE_SOURCE_LEAD_ID 等が 15_DuplicateDetectionService.js のみで参照

**判断**:
- ✓ **継続** → 機能は必要（廃止不可）
- ✗ **機能廃止** → 列削除可能（ただし既存重複マークは保持の要否確認）

---

## まとめ

### **強く廃止推奨**

| 列名 | 理由 | 移行先 |
|-----|------|--------|
| LEAD_PROGRESS | リード進捗 | → LEAD_STATUS に統合済み（重複） |
| DEAL_PROGRESS | 商談進捗 | → LEAD_STATUS に統合済み（重複） |
| DEAL_RESULT | 商談結果 | → LEAD_STATUS に統合済み（重複） |

### **要確認事項**

1. **レポート機能**（9列）：現運用状況 ← 最優先確認
2. **古いステータス列（3列）**：LEAD_STATUS への統合完了か確認
3. **低充填列（5-10%）**：実運用の要否確認

### **実施推奨プロセス**

```
Step 1: レポート機能の運用状況ヒアリング
Step 2: 古いステータス列の参照コード検査（削除前に）
Step 3: 低充填列の営業プロセス適合性確認
Step 4: 段階的な廃止（公式なマイグレーション公示）
```

---

## 参考資料

- **CoreSchemaRegistry**: `/Users/tanizawashingo/crm-app-canonical-20260824/src/00_CoreSchemaRegistry.js` L1-274
- **Config**: `/Users/tanizawashingo/crm-app-canonical-20260824/src/08_Config.js` L226-348
- **GAS 関数群**: `/Users/tanizawashingo/crm-app-canonical-20260824/src/27_WebApp.js`, `28_*.js`
- **フロントエンド型定義**: `/Users/tanizawashingo/crm-app-canonical-20260824/frontend/src/features/leads/contracts.ts`

---

**作成日**: 2026-08-26  
**調査者**: Hikky-dev (Claude Sonnet 4.6)
