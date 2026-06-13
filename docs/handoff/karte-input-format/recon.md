# カルテ入力項目・入力形式 Recon

**目的**: カルテ入力項目改修の実装前 recon。実装はしない。  
**日付**: 2026-06-14  
**ブランチ**: feature/morimoto/karte-input-format-recon  
**次フェーズ**: design.md 作成

---

## ADR 検索結果

| ADR | タイトル | ステータス | 関連度 |
|-----|---------|-----------|-------|
| ADR-027 | UI 国際化（i18n 強制） | Accepted | 全 UI 文字列 t() 必須 |
| ADR-094 | CRM 定義・deals 再編 | Accepted | company/lead 概念整理 |
| ADR-108 | Inbox カルテパネル再設計 | **Proposed** | タブ構成・フィールド配置の正本 |
| ADR-109 | leads status SSOT・不変コード化 | Proposed | status enum + i18n ラベル分離 |
| ADR-110 | カルテ reference alignment | Accepted | karte_reference.html が visual 真実 |

`git grep -il "temperature\|karte\|lead\|contact" docs/adr/` で確認済み。  
`assigned_to` に関するカルテ専用 ADR なし（ADR-108 §scope-out に「担当者は対象外」明記）。

---

## Table 1: カルテ入力項目一覧

### 商談タブ（deal tab）

| UI表示名 | フィールド名 | 入力形式 | enum/制約 | i18n キー | 未入力表示 | 問題・違和感 | file:line |
|---------|------------|---------|----------|----------|-----------|------------|-----------|
| 次のアクション | `next_action` | textarea | max 1000 | `leads.nextAction` | placeholder: `inbox.emptyField` | — | InboxKartePanel.tsx:495,498 |
| 次回アクション日 | `next_action_date` | date input | — | `leads.nextActionDate` | 空欄 | — | InboxKartePanel.tsx:500,504 |
| レスポンス速度 | `response_speed` | select | LeadResponseSpeed enum | `leads.responseSpeed` | `---` | 選択肢ラベルは t() 経由（OK） | InboxKartePanel.tsx:507-513 |
| 温度感 | `temperature` | select | LeadTemperature enum | `leads.temperature` | `---` | **⚠️ option value "Hot"/"Warm"/"Cold" が t() 未使用（ハードコード）** | InboxKartePanel.tsx:520-526 |
| 課題 | `challenge` | textarea | max 2000 | `leads.challenge` | placeholder: `inbox.emptyField` | — | InboxKartePanel.tsx:529,532 |
| 競合確認 | `competitor_check` | select (bool) | true/false | `leads.competitorCheck` | `leads.competitorUnconfirmed` | onChange+setTimeout(blur,0) で即保存（他フィールドと挙動差異） | InboxKartePanel.tsx:534-539 |
| 見込み規模 | `estimated_scale` | select | LeadScale enum | `leads.estimatedScale` | `---` | **⚠️ option value "Small"/"Medium"/"Large" が t() 未使用（ハードコード）** | InboxKartePanel.tsx:550-556 |
| 月間予測売上 | `monthly_forecast` | number input | Decimal(15,2) ge=0 | `leads.monthlyForecast` | 空欄 | `prospect_rank` 自動再計算のトリガー（leads.py:336） | InboxKartePanel.tsx:560,562 |
| 1件単価 | `per_order_amount` | number input | Decimal(15,2) ge=0 | `leads.perOrderAmount` | 空欄 | — | InboxKartePanel.tsx:566,568 |
| 月間取引頻度 | `monthly_frequency` | number input | Decimal(10,2) ge=0 | `leads.monthlyFrequency` | 空欄 | — | InboxKartePanel.tsx:572,574 |
| 商談メモ | `meeting_memo` | textarea | max 2000 | `leads.meetingMemo` | placeholder: `inbox.emptyField` | — | InboxKartePanel.tsx:580,583 |

### 顧客タブ（company tab）

| UI表示名 | フィールド名 | 入力形式 | enum/制約 | i18n キー | 未入力表示 | 問題・違和感 | file:line |
|---------|------------|---------|----------|----------|-----------|------------|-----------|
| 呼び名 | `nickname` | text input | — | `leads.nickname` | placeholder: `inbox.emptyField` | — | InboxKartePanel.tsx:431-433 |
| 国 | `country` | **text input（自由入力）** | max 255? | `leads.country` | placeholder: `inbox.emptyField` | **⚠️ プルダウンでない。入力揺れ発生リスク（"Japan" vs "日本" vs "JP"）** | InboxKartePanel.tsx:437-439 |
| 顧客タイプ | `customer_type` | select | LeadCustomerType enum | `leads.customerType` | `---` | 選択肢 "信頼重視"/"価格重視" は DB 値・eslint-disable 付き（i18n 対象外） | InboxKartePanel.tsx:443-448 |
| 取り扱いタイトル | `target_titles` | text input | max 500 | `leads.targetTitles` | placeholder: "Pokemon, One Piece, ..." | **⚠️ placeholder がハードコード英語**（t() 未使用） | InboxKartePanel.tsx:455-458 |
| 販売形態 | `sales_form` | **text input（自由入力）** | — | `leads.salesForm` | placeholder: `inbox.emptyField` | **⚠️ 制御語彙なし。何を入れるか定義なし** | InboxKartePanel.tsx:461-463 |
| CS メモ | `cs_memo` | textarea | max 2000 | `leads.csMemo` | placeholder: `inbox.emptyField` | — | InboxKartePanel.tsx:477-479 |
| 実績サマリー（読み取り専用） | — | display only | — | `inbox.sectionPerformance` | `inbox.performanceNoHistory` | 非編集。/leads/{id}/messages + /invoices?lead_id={id} から非同期取得 | InboxKartePanel.tsx:599-708 |

### 連絡先タブ（contact tab）

| UI表示名 | フィールド名 | 入力形式 | enum/制約 | i18n キー | 未入力表示 | 問題・違和感 | file:line |
|---------|------------|---------|----------|----------|-----------|------------|-----------|
| メール | `email` | email input | validate_email_loose | `leads.email` | 空欄 | backend 422 のフロント表示箇所未確認（⚠️ 未調査） | InboxKartePanel.tsx:373-376 |
| 電話 | `phone` | tel input | validate_phone | `leads.phone` | 空欄 | backend 422 のフロント表示箇所未確認（⚠️ 未調査） | InboxKartePanel.tsx:380-383 |
| Discord チャンネル | `discord_guild_channel_id` | 表示のみ / ボタン | read-only | `leads.discordTicketChannel` | リンクなし | 招待ボタンは別コンポーネント（DiscordInviteButton） | InboxKartePanel.tsx:354-366 |
| Meta チャンネル | — | 表示のみ（バッジ） | read-only | `inbox.metaChannelLabel` | `inbox.metaChannelBadge`("未連携") | 編集不可 | InboxKartePanel.tsx:389-394 |
| Discord ユーザー | `discord_user_id` | 表示のみ | read-only | `leads.discordUserId` | — | _UPDATABLE_COLUMNS に含まれない | InboxKartePanel.tsx:398-404 |

### 非表示フィールド（CardForm に存在するが UI 未レンダリング）

| フィールド名 | LeadDetail 型 | _UPDATABLE_COLUMNS | 備考 |
|------------|-------------|-------------------|------|
| `messenger_link` | `string \| null` | ✅ | deprecated。UI 削除済み。DB・API には残存 |
| `discord_id` | `string \| null` | ✅ | deprecated。UI 削除済み |
| `instagram_link` | `string \| null` | ✅ | deprecated。UI 削除済み |
| `whatsapp_link` | `string \| null` | ✅ | deprecated。UI 削除済み |
| `prospect_rank` | `number \| null` | ❌ | auto-calculated。payload から除外（useInboxState.ts:389） |
| `assigned_to` | `number \| null` | ✅ | ADR-108 scope-out。「担当者」は表示禁止（karte-visual-gate.spec.ts:360） |

---

## Table 2: 保存経路一覧

| 項目 | 内容 | file:line |
|-----|------|-----------|
| UI イベント | `onBlur`（全フィールド共通） / `competitor_check` のみ `onChange+setTimeout(handleCardFieldBlur,0)` で即保存 | InboxKartePanel.tsx:433,439,445,504,509,522,532,539,552,562,568,574,583 |
| state 更新 | `handleCardFieldChange("field", value)` → `setCardForm` + `localStorage.setItem(DRAFT_KEY(id), ...)` | useInboxState.ts:370 |
| 保存トリガー | `handleCardFieldBlur()` ← `useCallback` | useInboxState.ts:382 |
| payload 生成 | `Object.entries(cardForm).filter(k != "id" && k != "lead_code" && k != "prospect_rank").map("" → null)` | useInboxState.ts:387-391 |
| API 呼び出し | `PATCH /leads/{leadDetail.id}` with 全フィールド payload | useInboxState.ts:392 |
| backend endpoint | `PATCH /leads/{lead_id}` → `_UPDATABLE_COLUMNS` whitelist filter → DB UPDATE | backend/app/routers/leads.py:336-430 |
| _UPDATABLE_COLUMNS | 22フィールド（`discord_user_id` / `discord_guild_channel_id` 等の read-only フィールドは除外） | backend/app/routers/leads.py:68-81 |
| 副作用 | `estimated_scale` 変更 → Discord role sync trigger（leads.py:380〜）。`rank_fields` 変更 → `prospect_rank` 再計算（leads.py:345〜） | backend/app/routers/leads.py:345,380 |
| 成功後処理 | `setLeadDetail(updated)` + `setCardForm({...updated})` + `localStorage.removeItem(DRAFT_KEY)` + `setCardSaveStatus("saved")` | useInboxState.ts:393-397 |
| エラー表示 | `cardSaveStatus="error"` + `cardSaveError` 文字列をヘッダー右に表示 | InboxKartePanel.tsx:174 |
| retry | なし（エラーメッセージのみ表示・再試行ボタンなし） | — |
| **⚠️ 問題** | **毎 blur で全フィールドを送信（dirty のみでない）→ 並行セッションで他フィールドを上書くリスク** | useInboxState.ts:387-391 |

---

## Table 3: 視覚ゲート影響

### Phase 5b toHaveScreenshot テスト（直接影響）

| テスト名 | セレクタ | フィクスチャ | baseline ファイル | file:line |
|---------|---------|------------|-----------------|-----------|
| `[visual] karte-lead-deal` | `.inbox-right-panel` | `karte-lead-shinki-with-deal.json` (deal tab) | `karte-lead-deal.png` | karte-visual-gate.spec.ts:390-395 |
| `[visual] karte-customer-company` | `.inbox-right-panel` | `karte-lead-kisonkosaku-with-deal.json` (company tab) | `karte-customer-company.png` | karte-visual-gate.spec.ts:397-403 |

**baseline 生成制約**: ubuntu-latest で `workflow_dispatch --update-snapshots` のみ。Mac ローカル生成禁止（フォント描画差異による誤検知防止）。

### 機能テスト（構造変更で壊れる）

| テスト名 | 検証内容 | 壊れる変更例 |
|---------|---------|------------|
| ADR-110-1: Tab order | deal / company / contact 順 | タブ順変更 |
| ADR-110-2: Stage badge | `data-testid="karte-stage-badge"` 可視 | ヘッダー構造変更 |
| ADR-110-2: Last contact | `data-testid="karte-last-contact"` 可視 | ヘッダー構造変更 |
| ADR-110-3: Action bar overflow | `data-testid="karte-action-overflow"` 可視 | ActionBar 削除・変更 |
| ADR-110-6: Lock icon | `data-testid="karte-lock-icon"` 可視（company tab） | PerformanceSummary 変更 |
| ADR-108-1: Deal tab exclusion (5件) | nickname/country/customer_type/target_titles/sales_form が deal tab に**ない** | これら 5 フィールドを deal tab に追加すると fail |
| ADR-110-4: Section headings (4件) | karte-section-basic/deal-profile/ro/handover-heading 可視 | セクション見出し変更・削除 |
| ADR-108-4: Default tab (4件) | status 別のデフォルトタブ選択 | defaultTab ロジック変更 |
| ADR-108-8: No URL input | contact tab に `input[type="url"]` なし | URL 入力欄を追加すると fail |
| ADR-108-8: Meta badge | "未連携" 表示 | badge 削除・文言変更 |
| ADR-110-8/9: Forbidden text | "追加予定" / "担当者" が画面に**ない** | これら文字列を追加すると fail |

### CSS トークン（視覚ゲートに直結）

| CSS 変数 | 用途 | file:line |
|---------|------|-----------|
| `--karte-panel-width` | `.inbox-right-panel` の幅 | InboxPage.css:747 |
| `--karte-h-pad` | ヘッダー水平パディング | InboxPage.css:868 |
| `--karte-hd-gap` | ヘッダー gap/margin | InboxPage.css:876,891 |
| `--right-panel-avatar-size` | アバターサイズ | InboxPage.css:774-775 |

上記トークン値変更 → karte-lead-deal.png / karte-customer-company.png 両方に diff 発生 → **baseline 更新必須**。

---

## 変更候補分類

### 即実装可能（スクショ diff は出るが baseline 更新で対応）

| 変更内容 | 対象 | 理由 |
|---------|------|------|
| `temperature` 選択肢を `t()` 経由に変更 | InboxKartePanel.tsx:524-526 | "Hot"/"Warm"/"Cold" が英語ハードコード。i18n キー `leads.temperature_hot/warm/cold` を追加すれば OK。DB 値は変えない |
| `estimated_scale` 選択肢を `t()` 経由に変更 | InboxKartePanel.tsx:554-556 | "Small"/"Medium"/"Large" が英語ハードコード。i18n キー `leads.estimatedScale_small/medium/large` を追加すれば OK。DB 値は変えない |
| `target_titles` placeholder を `t()` 経由に変更 | InboxKartePanel.tsx:458 | "Pokemon, One Piece, ..." がハードコード英語。ja.json/en.json にキー追加 |

### PO 確認必要

| 変更内容 | 理由 |
|---------|------|
| `country` をプルダウン化（国リスト） | 自由入力では "Japan" / "日本" / "JP" の揺れが発生。正規値の定義とリストの出所（ISO 3166 等）の合意が必要 |
| `sales_form` を選択肢化 | 現在フリーテキストで制御語彙がない。何が正規値かの業務定義が必要 |
| `handleCardFieldBlur` を dirty-only 送信に変更 | 全フィールド毎 blur 送信は並行セッション競合リスク。実装変更は useInboxState.ts:387-391 だが、副作用（rank 再計算・Discord sync）との整合も要確認 |
| `competitor_check` の select/bool 整合 | UI は "true"/"false" 文字列 select、backend は `bool | None`。変換処理あり（leads.py）。現状動いているが型の不一致感あり |

### 対象外（改修不要）

| 項目 | 理由 |
|-----|------|
| `customer_type` / `response_speed` の DB 値（日本語/英語） | ADR-109 §enum 化待ち。現在 eslint-disable で除外済み。手を出さない |
| `assigned_to` | ADR-108 scope-out 明記。karte-visual-gate.spec.ts:360 で「担当者」表示禁止を自動検証済み |
| deprecated フィールド（messenger_link 等 4 件） | UI 非表示・_UPDATABLE_COLUMNS 残存。削除は別 ADR 起案が必要（PO 確認必須）。今回スコープ外 |
| `prospect_rank` | auto-calculated。payload 除外は正しい。UI 表示なし（設計通り） |
| ActionBar の status 判定 | "lead"/"existing_customer" のみ表示。ADR-109 の status コード化後に影響が出る可能性あり（design.md で言及要） |

---

## 未調査・不明点（design フェーズで決める）

1. **email / phone の 422 エラー表示**: backend で validate_email_loose / validate_phone が 422 を返した場合、フロントのどこで表示されるか未確認（`cardSaveError` に入るか否か）
2. **保存失敗時の retry**: 現在 retry ボタンなし（エラーメッセージのみ）。UX 改善が必要か PO 確認
3. **PerformanceSummary のローディング状態**: "..." が表示される間の UX（karte-visual-gate.spec.ts:273 で `await expect(perfSection.getByText("...")).not.toBeVisible()` を待機中）
4. **cs_memo の onBlur**: line 479 での `onBlur={handleCardFieldBlur}` は次行にあるため grep では見えにくい（実装は正常）
5. **ActionBar の status="商談中" 等での非表示**: 現状 null 返却（InboxKartePanel.tsx:221-330）。ADR-109 status コード化後にどう影響するか design.md で要検討

---

## 参照ファイル一覧

| ファイル | 内容 |
|---------|------|
| `frontend/src/pages/inbox/InboxKartePanel.tsx` | カルテパネル本体（866行）|
| `frontend/src/pages/inbox/useInboxState.ts:370-402` | cardForm state + handleCardFieldBlur 実装 |
| `frontend/src/pages/inbox/inbox.types.ts:43-84` | LeadDetail 型定義 |
| `frontend/src/pages/inbox/InboxPage.css:746-960` | `.inbox-right-panel` および `.right-panel-*` CSS |
| `frontend/src/locales/ja.json` | i18n キー（leads.* / inbox.*） |
| `backend/app/schemas/lead.py:41-135` | LeadTemperature / LeadScale / LeadCustomerType / LeadResponseSpeed enum + LeadUpdate |
| `backend/app/routers/leads.py:68-81,336-430` | _UPDATABLE_COLUMNS whitelist + PATCH endpoint |
| `frontend/tests-e2e/karte-visual-gate.spec.ts` | 視覚ゲート + 機能テスト（全 404 行） |
| `docs/adr/ADR-108-inbox-karte-panel-redesign.md` | タブ構成・フィールド配置の正本（Proposed） |
| `docs/adr/ADR-110-karte-reference-alignment.md` | karte_reference.html が visual 真実（Accepted） |
| `docs/adr/ADR-027-ui-internationalization.md` | i18n 強制ルール（Accepted） |
