# 実装カード 段階2 便3（第1組）— 買取相場・ダッシュボード・管理・受信箱など 32件を LoadingBlock へ

- 状態: Opus 作成。PO 承認 2026-10-22 PO「１」（残り87か所を買取相場を含む40か所以下の組から順に）
- 起点: origin/main（調査時 44c34a488）。ブランチ `release/loading-mold-pages-1`
- 根拠: 調査生出力 /tmp/CC報告ファイル/loading-bin3-recon/（targets.tsv・context.txt・keys.txt・css.txt・tests.txt・groups.txt）
- 対象ADR: ADR-144・ADR-067・ADR-027

## 1. 置換の規則（便2の card-3.md §1 と同じ）
- 規則A: 読み込み中の文字だけを持つ要素（`<p>` / `<div>`。style・className・role="status" を含む、複数行も含む）を要素ごと `<LoadingBlock />` に替える
- 規則B: 三項・`&&`・`return` の形は残し、表示部分だけ替える
- 規則C（便3で追加）: 文言が common.loading と違うキーは label で渡し、読み上げの文言を保つ（keys.txt）
  - `admin/InventoryVisibilityPage.tsx:130` → `<LoadingBlock label={t("inventoryVisibility.loadingMatrix")} />`
  - `dashboard/PriorityProspectsSection.tsx:329`・`dashboard/WeeklyAdvisorSection.tsx:289` → `<LoadingBlock label={t("dashboard.weeklyLoading")} />`
- 規則D（便3で追加）: 入力欄の下の小さな注記として出ていた2件は `<LoadingBlock size="sm" />`
  - `inbox/InboxKartePanel.tsx:291`（class comp-field__hint）、`integrations/FedexEtdSetupGuide.tsx:359`（class form-hint）
- import は各ファイルに `import { LoadingBlock } from "<相対>/components/loading";` を1行
- 規則に当てはまらない形が出たら止まって BLOCKED:

## 2. 対象 32件・25ファイル（frontend/src/pages/ 配下。行は origin/main 44c34a488 時点）
- admin: ChannelMastersPage:78、DiscordAnnouncePage:65、DiscordConfigPage:340、InventoryVisibilityPage:113・:130（規則C）、TenantPolicyPage:151、TenantProfilePage:138
- buyback-prices: BuybackAlertModal:274、BuybackByProductPage:234-236、BuybackPendingReviewModal:106-108、BuybackPriceHistoryDrawer:99、BuybackPricesPage:396-398、BuybackProductHistoryDrawer:215
- dashboard: DashboardPage:485・:554・:590・:665、FollowUpsPage:164、FunnelLeadsPage:107-109、FunnelReasonsPage:58、FunnelRevenuePage:43、FunnelSection:498、PriorityProspectsSection:329（規則C）・:395、WeeklyAdvisorSection:289（規則C）・:366
- inbox: InboxConversationRows:60-62、InboxKartePanel:291（規則D）・:319、InboxMessageThread:523-525
- integrations: FedexEtdSetupGuide:359（規則D）
- inventory: OwnInventoryPage:106
- 各件の今のコードは targets.tsv、前後は context.txt

## 3. 触らない範囲
- excluded.tsv の22件（ボタン内三項・prop・InventoryPage:529・ViewerApp:137・SchedulePageImpl:821）と第2組・第3組
- CSS: 置換で使われなくなる規則（.db-loading・.db-priority-loading・.db-weekly-composer-loading・.db-weekly-loading・共用の .fn/.frp/.frr/.fu-loading）も消さない（css 整理の別便）
- 辞書・金型・scripts/

## 4. 検証（生出力を /tmp/CC報告ファイル/loading-stage2-bin3/ へ）
| 基準 | 検証方法 |
|---|---|
| 対象の32件が消える | countLoadingText で対象25ファイルの合計が置換前→後で 32 減る（前後の数を記録） |
| 試験 | `npx vitest run src/pages/buyback-prices src/pages/dashboard src/pages/admin src/pages/inbox src/pages/integrations src/pages/inventory` 全件 pass |
| 型・lint・i18n | tsc 0・eslint（変更ファイル）0・frontend/scripts/check-i18n-missing-keys.js exit 0・scripts/check-ui-governance.js exit 0 |
| 範囲 | `git diff origin/main...HEAD --name-only` が対象25ファイル＋docs/台帳だけ |

## 5. 想定分岐
- 行がずれた → 文面が一致すれば進め、新旧の行を報告。一致しなければ止まる
- 試験が落ちた → 直さず BLOCKED: で試験名と生出力
- tsc で schema.d.ts が無い → `npm run generate:api-types` を先に（便2と同じ）

## 追補1（commit 時の lint 警告4件への対応・Opus 判断）
- 事実: lint-staged の `eslint --max-warnings=0` が、触ったファイルにもともとあった警告4件で止めた（置換した行ではない）。止めたまま進める手は無い（迂回禁止）。表示を変えない直し方が3つとも確認できたので、同じ便で直す
- 直し1 `buyback-prices/BuybackProductHistoryDrawer.tsx:175` `}, [item, open]);` → `}, [item, open, t]);`（t は useTranslation の戻り値。言語を切り替えたときだけ取り直す）
- 直し2 `dashboard/FollowUpsPage.tsx:113`・`:202` `t("common.unitDay", { defaultValue: "日" })` → `t("common.unitDay")`（ja.json:200・en.json:200 にキーがあるので defaultValue は使われない）
- 直し3 `dashboard/FunnelLeadsPage.tsx:25-28` `fmtMoney(n: number)` を `fmtMoney(n: number, man: string)` にし、26行の `万` を `${man}` に。呼び出し :93・:98 は `fmtMoney(row.…, t("common.unitMan"))`（ja/en とも "万"。表示は変わらない）。t が使える位置か確かめ、使えなければ止まる
- 検証の追加: 3ファイルの eslint 警告 0、FunnelLeadsPage・FollowUpsPage・BuybackProductHistoryDrawer を描く試験が pass
