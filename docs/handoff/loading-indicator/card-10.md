# 実装カード 段階3 便3 — pages の残り（admin から）のボタンを「丸＋元の言葉」へ（40 か所以下）

- 状態: Opus 作成・自己審査済み（同一AIの審査）。PO 承認: 方針 2026-10-23「1」、設計 2026-10-24「1」、便3 着手 2026-10-25「1」
- 起点: 最新の origin/main（便2 #4718 合流 293b7472a を含む）。ブランチ `release/loading-button-bin3`
- 根拠: /tmp/CC報告ファイル/loading-button-recon/targets.cjs・targets.tsv（調査時点）、design.md 段階3、card-8・card-9
- 対象ADR: ADR-144・ADR-067・ADR-027・ADR-069

## 1. 対象の決め方（実物で決める）
1. 最新 worktree で /tmp/CC報告ファイル/loading-button-recon/targets.cjs を再実行し、今の対象一覧を作る（生出力を impl/targets-now.tsv）。スクリプトが動かない・列が targets.tsv と違う → BLOCKED:
2. `frontend/src/pages/` 配下で、pages/super-admin・pages/integrations を除いた行を取る
3. 並べ順: pages/admin を先頭、残りはディレクトリ名の辞書順。ディレクトリ単位で足していき、合計が 40 を超える手前のディレクトリまでを対象にする（ディレクトリを途中で切らない）
4. 決めた一覧を impl/bin3-targets.tsv に保存し、PR 本文と card-10.md の §2 に「ファイル:行」で書き写す

## 2-0 決まった対象（実物で決定。生出力 impl/targets-now.tsv・bin3-targets.tsv）
- 方法: targets.cjs を再実行（93 行）→ pages/super-admin・pages/integrations を除く → pages/admin 先頭、残りはディレクトリ辞書順で積み、login（+2 で 41）の手前の pages/invoice-create までの 39 行
- 内訳: admin 10・account-settings 2・bots 1・buyback-prices 1・channels 3・commission-settings 1・companies 1・company-detail 5・conditions 3・contacts 1・erp 1・goal-setting 2・inbox 7・invoice-create 1 = 39
- 直した 34 か所:
  - pages/account-settings/ProfileSection.tsx:207
  - pages/account-settings/SecuritySection.tsx:107
  - pages/admin/DiscordAnnouncePage.tsx:122
  - pages/admin/DiscordConfigPage.tsx:406
  - pages/admin/DiscordConfigPage.tsx:441
  - pages/admin/DiscordConfigPage.tsx:445
  - pages/admin/DiscordConfigPage.tsx:532
  - pages/admin/InventoryVisibilityPage.tsx:168
  - pages/admin/TenantPolicyPage.tsx:317
  - pages/admin/TenantProfilePage.tsx:261
  - pages/bots/BotsPage.tsx:265
  - pages/channels/ChannelsPage.tsx:393
  - pages/channels/ChannelsPage.tsx:443
  - pages/channels/ChannelsPage.tsx:565
  - pages/commission-settings/CommissionSettingsPage.tsx:262
  - pages/companies/CompaniesPage.tsx:558
  - pages/company-detail/CompanyAddressModal.tsx:157
  - pages/company-detail/CompanyBasicTab.tsx:102
  - pages/company-detail/CompanyChannelsTab.tsx:40
  - pages/company-detail/CompanyContactsTab.tsx:217
  - pages/company-detail/CompanyDiscordTab.tsx:95
  - pages/conditions/ConditionImportPage.tsx:120
  - pages/conditions/ConditionImportPage.tsx:96
  - pages/conditions/ConditionsPage.tsx:372
  - pages/contacts/ContactsPage.tsx:359
  - pages/erp/ERPPage.tsx:61
  - pages/goal-setting/GoalSettingPage.tsx:211
  - pages/goal-setting/GoalSettingPage.tsx:377
  - pages/inbox/InboxKartePanel.tsx:847
  - pages/inbox/InboxKartePanel.tsx:905
  - pages/inbox/InboxKartePanel.tsx:948
  - pages/inbox/InboxKartePanel.tsx:956
  - pages/inbox/InboxKartePanel.tsx:963
  - pages/invoice-create/InvoiceCreatePage.tsx:439
- 外した 5 行:
  - pages/admin/ChannelMastersPage.tsx:141: 生 button（金型 Button ではない。便6の対象）
  - pages/admin/DiscordConfigPage.tsx:374: 入れ子の三項
  - pages/buyback-prices/BuybackPricesPage.tsx:302: `t(L)` を使わない文字列「...」の三項で規則1・2の形に当てはまらない
  - pages/inbox/ManualRecordSection.tsx:197: 生 button（金型 Button ではない。便6の対象）
  - pages/inbox/OutboundTranslationPreview.tsx:178: 生 button（金型 Button ではない。便6の対象）
- disabled に X が文字どおりには入っていない 6 行（disabled は別の式で、読み込み中を含む）: DiscordConfigPage:441・532（disabled は ticketSavingSource !== null）、InboxKartePanel:948・956・963（disabled は loading !== null）。ほか 28 行は X が disabled に入っている

## 2. 置き換えの規則（card-9 と同じ）
- 規則1: `{X ? t(L) : t(O)}` → 要素に `loading={X}`、中身は `{t(O)}`
- 規則2: `{t(X ? L : O)}` → `loading={X}`、`{t(O)}`（テンプレート文字列のキーも同じ）
- X は元の式をそのまま使う。disabled は消さない
- 次のどれかに当たる行は直さずに対象から外し、理由を付けて一覧で報告する（全体は止めない）: 要素に既に loading がある／HeaderButton が variant="icon"／上の2形に当てはまらない（入れ子の三項など）

## 3. 押せる・押せないの変化
- disabled に X が入っていない行は、直すと読み込み中に押せなくなる（design.md 段階3 の弊害として承認済み）。直してよいが、該当行を一覧で報告する

## 4. 試験
- 対象の画面の試験が、ボタンの中の読み込み中の言葉を期待して落ちた場合は、期待を「元の言葉のまま・そのボタンが aria-busy="true"」に直してよい。直した試験はファイル:行と前後を報告する
- それ以外の理由で落ちた試験は直さない。単独・`--testTimeout=30000` で再実行して通れば負荷とみなし両方の生出力を残す。それでも落ちれば BLOCKED:

## 5. 触らない範囲
- 対象外の行（features・components・便4以降の pages）、生 `<button>`、辞書（使われなくなるキーも消さない）、CSS、scripts/、金型
- 対象ファイルにもともとある lint 警告で止まったら直さず BLOCKED:

## 6. 文書
- 本カード（§2 の一覧を埋めたもの）を docs/handoff/loading-indicator/card-10.md として同じ PR に入れる。design.md 段階3 の 3-3 の便2の行の下に「便3（card-10）= pages/admin ほか N か所。」と1行足す
- 台帳 .claude-pipeline/active-work.d/release-loading-button-bin3.md（便2 と同じ形）

## 7. 検証（生出力を /tmp/CC報告ファイル/loading-button-bin3/impl/ へ）
| 基準 | 検証方法 |
|---|---|
| 対象が消える | targets.cjs を再実行し、bin3-targets.tsv の行（外した行を除く）が 0 件 |
| 丸＋元の言葉 | 対象の画面の試験が全件 pass（§4 の再実行を含む） |
| 型・lint・i18n・UI | tsc 0・eslint（変更ファイル --max-warnings=0）0・check-i18n-missing-keys.js exit 0・scripts/check-ui-governance.js exit 0（BASE_SHA/HEAD_SHA 指定） |
| 範囲 | `git diff origin/main...HEAD --name-only` が対象ファイル＋直した試験＋§6 の文書・台帳だけ |

## 8. 想定分岐
- 行がずれた → 文面が一致すれば進め、新旧の行を報告
- schema.d.ts が無い → `npm run generate:api-types` を先に
- 対象が 40 を超える1ディレクトリだけになる → そのディレクトリだけで止めず NEEDS_DECISION:
