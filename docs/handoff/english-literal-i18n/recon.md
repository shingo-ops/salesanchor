# recon: 画面に出る英語の直書き（english-literal-i18n）

- 親: [ADR-027 UI 国際化](../../adr/ADR-027-ui-internationalization.md) ／ [design-system](../../specs/design-system/README.md)
- ひとこと: 日本語の画面に、辞書を通らない英語がそのまま出ている所を数え、出どころを確かめた記録。
- 基準: `origin/main` c350824c4（調査時）。作業ブランチ起点 d9b0c1771348e9c740eeff1eb662221d029436a6。
- 生出力: `/tmp/CC報告ファイル/english-literal-recon/`（round2/final_fix_list.txt・db_values_list.txt・datatable_callers.tsv ほか）
- ラベル: 【事実】は file:line かコマンド結果あり。【未確認】は確かめていない。推測は書かない。

## 1. 既存 ADR・仕様の検索結果

| 検索語 | 当たり | 内容 |
|---|---|---|
| i18n / 国際化 | `docs/adr/FEATURE-INDEX.md:40` → ADR-027 | 全 UI 文字列 `t()` 経由・キー同期必須 |
| ADR-027 | `docs/adr/ADR-027-ui-internationalization.md:30` `:62` `:70` | 「全 UI ラベルの i18n 化」「既定言語は日本語」 |
| 金型 / ui-allow | `docs/adr/ADR-144-ui-component-governance.md` | 例外は `ui-allow: <理由> (#番号)` |
| DataTable | `docs/adr/ADR-1019-inventory-viewer-separate-accounts.md:27` | 金型として名前が並ぶのみ。`docs/CC_UI_GOVERNANCE.md` に記載なし |
| 公開フォームの言語 | `docs/adr/ADR-126-registration-form-input-contract-v2.md:83-87` | 「公開フォームのみ英語デフォルト」 |
| 仕様索引 | `docs/specs/README.md:27` `:32` | design-system・design-tokens-ssot。英語直書きの専用テーマは無い |

【事実】英語の固有名詞（BOX・Discord 等）の扱いを決めた ADR は見つからなかった（上の検索語で当たり無し）。

## 2. 今ある守り

- 【事実】`frontend/scripts/eslint-rules/no-japanese-literal.cjs`（82行）は日本語だけを見る。判定は `:20` `/[ぁ-ゖァ-ヶ一-鿿]/`。対象ノードは JSXText `:39-43`・Literal `:46-72`・TemplateElement `:75-79`。除外は import・SwitchCase・TSLiteralType・`<option value>`。
- 【事実】`frontend/eslint.config.js:31` で 'warn'、lint-staged は `--max-warnings=0`。対象 `src/**/*.{ts,tsx}`。off: `:232-245`（stories・design-system・locales・.storybook）、`:247-253`（design-preview）。
- 【事実】英語を拾う仕組み（eslint-plugin-i18next 等）は入っていない（`frontend/package.json` に無し）。
- 【事実】`scripts/check-ui-governance.js`（848行）は差分方式。`getChangedFiles :69`・`showFile :55`・`countAll :707`・`main :723`。判定 `:773` `headCounts>baseCounts`。対象は pages の .tsx（loadingTernary だけ features・components も）。ui-allow 書式 `:130` `/ui-allow:\s+\S+.*\(#\d+\)/`、同じ行か直前の行 `:144`。
- 【事実】`frontend/scripts/check-i18n-missing-keys.js` は辞書のキー抜けだけを見る。

## 3. 直すべき英語の直書き（画面に出ると確かめた所）

### 3-1. DataTable（11行）
- 【事実】`frontend/src/components/DataTable.tsx:257,269,290,292,321,350,355,404,434,468,482`。aria-label の英語と `emptyState ?? 'No data'`。`useTranslation` を使っていない。
- 【事実】既定の表示 `String(row[key])` は `frontend/src/components/DataTable.tsx:39`。
- 【事実】使っている所 76か所（60ファイル）。emptyState を渡す 34・渡さない 42（`datatable_callers.tsv`）。渡さない 42か所は ja でも「No data」が出る。

### 3-2. 受信箱（12行＋時刻の言葉）
- 【事実】`frontend/src/pages/inbox/InboxConversationList.tsx:175`、`frontend/src/pages/inbox/InboxConversationListMobile.tsx:198`、`frontend/src/pages/inbox/InboxConversationRows.tsx:123`、`frontend/src/pages/inbox/InboxConversationRows.tsx:133`（"You: "）、`frontend/src/pages/inbox/InboxMessageThread.tsx:445`（Lead #）、`:563`（Send failed）、`:569`（Human Agent）、`:574`、`:614`（(no body)）、`frontend/src/pages/inbox/InboxProfileModal.tsx:176`、`frontend/src/pages/inbox/InboxThreadHeaderMobile.tsx:116`、`frontend/src/pages/inbox/useInboxState.ts:387`（"Lead not found." → `frontend/src/pages/inbox/InboxMessageThread.tsx:527` に出る）。
- 【事実】`frontend/src/pages/inbox/inbox.types.ts:132-144` relativeTime が "just now"／"Nm ago" 等と `toLocaleDateString("en-US")` を返す。使用先 `frontend/src/pages/inbox/InboxConversationRows.tsx:128`・`frontend/src/pages/inbox/InboxMessageThread.tsx:636`。
- 【事実】`frontend/src/pages/inbox/inbox.types.ts:150` formatAbsolute が `toLocaleString("en-US")`。使用先 `frontend/src/pages/inbox/InboxMessageThread.tsx:564` の title。
- 行番号注記: 調査一覧の `InboxMessageThread:443/561`・`InboxThreadHeaderMobile:114` は再読で `445/563`・`116` が正（2行ずれ）。

### 3-3. その他の画面（9行）
- 【事実】`frontend/src/pages/notifications/NotificationsPage.tsx:128,155,183`、`frontend/src/pages/badges/BadgesPage.tsx:86`（User #）、`frontend/src/pages/channels/ChannelsPage.tsx:493`（Page ID:）、`frontend/src/pages/integrations/FedexLabelValidationTab.tsx:51`（done）、`frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx:310`（ERP Key:）、`frontend/src/pages/schedule/schedule-utils.ts:188`（Holiday/Shift → `frontend/src/pages/schedule/SchedulePageImpl.tsx:638`・`:708`・`:791`）、`frontend/src/pages/company-detail/CompanyBasicTab.tsx:92`（pending_dedup_review）。

### 3-4. 直さなくてよいと判定した1件
- 【事実】「BOX」: `frontend/src/locales/ja.json:5337` でも BOX と呼んでいる。→ design §3-4 で扱いを決める。

## 4. 選択肢の言葉（28行・すべて手書きの固定語）

- 【事実】前の報告「保存値をそのまま見せている」は誤り。28行すべて画面用に手書き（`db_values_list.txt`）。
  - 会社・連絡先の状態: `frontend/src/pages/companies/CompaniesPage.tsx:511-514`、`frontend/src/pages/company-detail/CompanyBasicTab.tsx:89-91`、`frontend/src/pages/contacts/ContactsPage.tsx:348-350`、`frontend/src/pages/company-detail/CompanyContactsTab.tsx:199-201`、`frontend/src/pages/contacts/ContactEditPage.tsx:189-191`（`:192` だけ t 経由）
  - 温度・規模: `frontend/src/pages/inbox/InboxProfileModal.tsx:222-224`（Hot/Warm/Cold）、`:233-235`（Small/Medium/Large）
  - 照合方法: `frontend/src/pages/note-master/NoteMasterPage.tsx:85-87`・`frontend/src/pages/super-admin/components/NoteMasterPanel.tsx:82-84`（LITERAL/REGEX/DEFAULT）
- 【事実】同じ値をすでに辞書で見せている所:
  - `frontend/src/pages/companies/CompanyFormFields.tsx:29-32`（customers.status_*）、`frontend/src/pages/contacts/ContactFormFields.tsx:40-43`、Staff 系
  - `frontend/src/pages/inbox/InboxKartePanel.tsx:638-640`・`:668-670`（ja 高/中/低・小/中/大）
  - `frontend/src/pages/leads/LeadEditPage.tsx:236-249`・`frontend/src/pages/leads/LeadsPage.tsx:386-399`（leads.temp_*。ja も Hot/Warm/Cold）
  - 照合方法 `frontend/src/pages/status-master/StatusMasterPage.tsx:124-126`・`frontend/src/pages/super-admin/components/ConditionsMasterPanel.tsx:237-239`・`frontend/src/pages/super-admin/components/RuleDrawer.tsx:270-273`（ja が「完全一致」と「文字列一致」で食い違う）
- 【事実】保存値を生で出す所: `frontend/src/pages/note-master/NoteMasterPage.tsx:229`、`frontend/src/pages/super-admin/components/NoteMasterPanel.tsx:193`、`frontend/src/pages/status-master/StatusMasterPage.tsx:197`・`frontend/src/pages/super-admin/components/ConditionsMasterPanel.tsx:257`（DataTable 既定）、`frontend/src/pages/companies/CompaniesPage.tsx:408`、`frontend/src/pages/contacts/ContactsPage.tsx:396`、`frontend/src/pages/company-detail/CompanyContactsTab.tsx:123`、`frontend/src/pages/company-detail/CompanyDetailPage.tsx:96`（`{c.status}`）、`frontend/src/pages/leads/LeadsPage.tsx:486`。
- 【事実】同じ値に訳が2通り以上ある（温度: 高/中/低 と Hot/Warm/Cold、照合: 完全一致 と 文字列一致）。

## 5. もうある辞書のキー
- 【事実】`inbox.noLead`、`dashboard.priorityFallbackLead`（'Lead #{{id}}'）、`schedule.holiday`・`schedule.shiftLabel`、`inbox.elapsedJustNow`・`elapsedMinutesAgo` 等、`leads.estimatedScale_*`、`matchTypeRegex/Literal/Default`。
- 新しいキーが要る: Send failed・(no body)・Human Agent・User #・Page ID・ERP Key・Filter by Page・You:・DataTable の aria 系・Pokemon の例の placeholder。
- 見積もり（手数え・機械集計ではない）: 既存キーで直せる約15行、新キーが要る約59行。
- 【事実】言語に合わせた時刻の共通関数は無い。局所: `frontend/src/pages/inbox/InboxKartePanel.tsx:86` elapsedLabel(iso,t)（export なし）、`frontend/src/features/tcg-analysis-review/formatDateTime.ts:2`、`frontend/src/pages/schedule/schedule-utils.ts:108`・`:112`・`:121`。

## 6. エラーの言葉
- 【事実】行き先不明だった6か所は英語のまま画面に出ない: `frontend/src/contexts/AuthContext.tsx:104` は非表示（ErrorBoundary 無し・grep 確認）、`frontend/src/lib/firebase-auth.ts:177` は firebaseError.default に置換、register の resolveErrorCode 3か所は全枝が辞書語、ViewerApiError は `t("viewer.error.*")` に置換。
- 【事実】画面側で書いた英語の throw が err.message 表示（296か所）に届く組は 0組。
- 【事実】届くのは `frontend/src/lib/api.ts` の `HTTP ${status}`（`:95,:107,:148,:153,:190`）だけ。
- 【事実】`String(e)` 11か所。tcg-distribution などで画面に出る。

## 7. 試験への影響
- 【事実】言葉で探している試験: `frontend/src/components/DataTable.test.tsx:83,89,97,104,113`、`frontend/src/pages/super-admin/components/ProductMasterPanel.test.tsx:51,68,77`、`frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.timing.test.tsx:131`（next page）、`frontend/tests-e2e/scene7-human-agent-tag.spec.ts:109`、`frontend/src/components/BotFormButtonMigration.test.tsx:30`（Discord Bot ID）。
- 【事実】`frontend/src/pages/inventory/InventoryPage.rowdrawer.test.tsx:156-157` は「無いこと」を確かめる試験。言葉を変えると何も確かめずに通る。

## 8. 対象外と判断の材料
- 登録フォームの国名 190件（`frontend/src/constants/countries.ts`、使用 RegisterPage・RegisterChangeBillingPage・RegisterAddressPage の displayFn）。【事実】ADR-126 `:83-87` 公開フォームは英語既定、`?lang` 既定 "en"、招待 URL（`backend/app/routers/registration_tokens.py:148-152`）に lang 無し。
- 【未確認】本番マスタに "Paper"/"Playing card" があるか（`frontend/src/pages/products/products.types.ts:92` emptyForm、`ProductEditPage.tsx:104-116・338-349` で生表示）。
- 【未確認】ADR-126 に英語既定の理由の明文があるか。
- 【未確認】手で `?lang=ja` を付けて案内している運用があるか。
- 【未確認】バックエンドが返す detail の英語。
