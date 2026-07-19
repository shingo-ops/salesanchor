# recon（現在地の全数調査・page-header-v2）

> この文書は何か（専門用語なしの1行）:
> 全ページのヘッダーの中身と、ページの親子関係を機械で数え切った調査結果。
> 親（あるべき姿＋KGI）: ../../specs/design-system/component-ssot/page-header-v2/README.md

実測SHA: origin/main 022494441c63e39afae8a9fd4c15ea8b79386a5e（第1・2便）/ 8ef5e4fc667abd5c48a57577b604fcebc3a59b72（第3便）
方式: 母集団確定→機械で全件列挙→全件分類→総数＝分類合計の検算（探索型grep禁止）

## 1. 総数（機械実測）
- PageLayout利用: 69ファイル / headerLeft: 2件 / headerAction: 40件（計42出現・38ファイル）
- ルート定義 path=: 106件（frontend/src/App.tsx:142-360）/ navigate(): 86件

## 2. ヘッダー中身の全件仕分け表（42/42・検算一致）
| 型 | 説明 | 件数 | 該当（file:line） |
|---|---|---|---|
| A1 標準型 | page-header-actions＋主ボタン1個 | 16 | bots:197 / purchase-orders:180 / suppliers:102 / invoices:123 / quotes:89 / leads:270 / staff-reports:52 / deals:221 / buddy:48 / teams:174 / staff:214 / erp:52 / shifts:47 / badges:43 / notifications:46 / orders:63(変数46) |
| A2 標準拡張 | 同枠に検索input・件数バッジ・月選択・切替・一括削除等 | 7 | contacts:246 / companies:352 / dashboard:407 / super-admin DiscordInbound:215 / company-detail:154 / design-system:450 / products:460(変数186) |
| B 戻るボタン | 「← 親へ」ボタン。5様式に分裂(fu/frr/frp-back-btn・btn-secondary・backAction) | 11 | FunnelReasons:40 / FunnelRevenue:66 / FollowUps:141 / FunnelLeads:107 / TenantProfile:133,140 / TenantPolicy:147,159 / ParseReview:398 / invoice-create:221 / company-detail:151(headerLeft) |
| C 裸置き | wrapper無し単体ボタン/リンク | 2 | super-admin FxRate:89 / CarrierIntegration:295(aタグ) |
| D 複数アクション | div.actions＋状態依存ボタン群＋インラインstyle | 2 | invoice-detail:189 / quote-detail:128 |
| E 操縦席 | カレンダー専用（今日/‹›/期間・検索/設定/切替） | 2 | schedule:1107(headerLeft) / schedule:1121(headerAction) |
| G 編集アクション | フォームのキャンセル＋保存がヘッダーに居る | 1 | product-edit:198(変数172) |
| H 別ページ導線 | btn-ghostで定型文/FAQへ遷移（ナビの一種） | 1 | inbox:78(変数44) |

検算: 16+7+11+2+2+2+1+1 = 42/42（未分類0）

## 3. ページ階層地図の骨子（全106ルートの層別）
- 層1 サイドメニュー直下(11): / , /schedule , /lead-chat , /inventory , /purchase-orders , /crm , /orders , /sales , /commissions , /management-center（DesktopShell.tsx to=10件）＋条件付き見積請求(salesLinkTo)
- 層2a ハブの子（サブメニュー定義あり）:
  - /crm/* → leads / companies / companies/:id / contacts / archive（CustomerHubPage・SubMenu部品）
  - /management-center/* → teams/staff/shifts/roles/inventory-visibility/commission/tenant-profile/channels/bots/deals/suppliers/purchase-orders/data/integrations×7/notifications/reports/super-admin×4（App.tsx:331-360・約26子）
  - /admin/* → tenant-profile/tenant-policy/discord-config/discord-announce/inventory-visibility/channel-masters（AdminHubPage・画面下部タブ様式）
- 層2b パスの子（URL階層のみ）: /quotes/new,:id / /invoices/new,:id / /dashboard/follow-ups,leads,revenue,reasons / /goals/settings / /schedule/settings / /crm/leads/:id/edit / /contacts/:id/edit / /admin/products/new,:id/edit / /staff/:id/edit / /bots/:id/edit / /teams/:id/edit / /suppliers/:id/edit / /deals/:id/edit / /super-admin/inbound/:id/review
- 層3 ボタン遷移のみ: /templates / /faq（受信箱ヘッダーHから遷移・navigate実測）
- ナビ枠外（パンくず対象外）: /login / /register×3 / /channels/oauth/callback

## 4. 重大発見（設計判断が必要）
1) 二重居住: 同一ページが複数ルートに実装マウントされている。
   - tenant-profile / inventory-visibility: /admin/* と /management-center/* の両方
   - super-admin系4ページ: 単独 /super-admin/* と /management-center/super-admin/* の両方
   - staff/teams/shifts/roles/bots/deals/suppliers/purchase-orders/data/reports/channels/notifications(=/settings)/commission: 単独ルートと /management-center/* の両方
   → パンくずは親が一意である必要があるため、設計①で各ページの「正住所」を決める。
2) サブメニュー様式の3分裂: SubMenu部品(ADR-149・hub-subnav) / AdminHub下部タブ(admin-hub.css) / tab-nav(見積⇔請求)
3) B型11件はパンくず導入で全撤去できる可能性（「親へ戻る」はパンくずの下位互換）
4) 既存SSOT資産: frontend/src/config/routeTitles.ts（route→navキーのSSOT・詳細ページは意図的未登録）。パンくずの親子SSOTはこの拡張または隣接が有力。

## 5. 余剰（keep-or-remove判定は設計で）
- back-btn 5様式のCSS（fu/frr/frp-back-btn等）: B型撤去と同時に削除候補
- schedule-shell__range の font-xl（題名級字体）: KGI⑦対象
