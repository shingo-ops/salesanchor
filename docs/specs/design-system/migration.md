# 移行計画（design-system・PO承認済 2026-07-06改訂）

> この文書は何か（専門用語なしの1行）: 散らかった今の画面を、1ヵ所直せば全ページ変わる理想形へ、壊さず順番に寄せる工事計画。

> 現行順序（2026-09-10）: 全体設計→共通部品と画面移行→最後にCI追加。旧§1〜3の関所先行/領域ペア計画・古い件数は当時の履歴で、今回の実装順には適用しない。最新の契約はdesign.md §Z/AAと本書末尾の既存PR採否を参照。PO目視は完成後に実施する。

親: [README.md](README.md)／理想: [design.md](design.md)／現状実測: [recon.md](../../handoff/design-system-recon/recon.md)・[網羅recon full-recon.md](../../handoff/design-system-recon/full-recon.md)
PO承認: 2026-07-05初版／2026-07-06改訂（網羅reconで色の真数36・表28件・関所隙間5つが判明し便構成を再編）

## 1. 方針の柱（5本）
1. 関所ファースト（領域ペア版）: 掃除の前に蛇口を閉める。ただし既存debtを一度に全部failさせると全並行便が詰まるため、便0bラチェットと同じ「増分のみ阻止（A案）」で、各領域を掃除し終えた直後にその領域の関所を建てる。掃除と関所を領域ごとにペアにする。
2. 同値置換: 色の集約は値を変えず名前に置き換えるだけ。見た目の質の変更は移行完了後の別テーマ。移行とデザイン変更を混ぜない。
3. 小口バッチ: 部品の金型寄せは1便5〜8ファイルに分割し各バッチで画面確認。
4. 部品台帳が分母: KGI①の分母は §4 の部品台帳の行数（満数方式）。
5. 現物照合（便1破棄の教訓）: reconの数字は必ず3検品（ノイズ除外・既存ADR照合・KGI定義照合）を経てから設計に使う。

## 2. 便構成と受入基準
| 便 | 内容 | 前提 | 受入の芯 |
|---|---|---|---|
| 便0 | 関所ラチェット新設＋部品台帳棚卸し（完了・#2806/#2801） | − | 上限=現状値でfail稼働（済） |
| 便0.5 | 用途トークン新設: 本物色36の受け皿をADR-067準拠で index.css の :root/:root.force-dark に定義（詳細は [design.md §5.3.1](design.md) 参照） | 便0 | 新設トークンがdark-parity通過・36件の対応表確定 |
| 便1a | 色の同値置換①: calendars.config.ts 21件→用途トークン参照 | 便0.5 | config内の生hex 0・visual gate(schedule)一致 |
| 便1b | 色の同値置換②: RolesPage.tsx 13＋schedule-owner 1＋Dashboard 1＝15件 | 便0.5 | 該当生hex 0・見た目一致 |
| 便1c-guard | 色掃除領域に関所: TS色定数の増分をfailさせるガード追加（領域ペア） | 便1a/1b | TS色リテラル増分でfail稼働 |
| 便2 | 素の<table> 28件→DataTable金型（小口バッチ） | 便0.5 | 素の<table>残存0 |
| 便2-guard | 表領域に関所: 素の<table>新規をfail（領域ペア） | 便2 | 素の<table>増分でfail稼働 |
| 便5 | 骨格: 素の<h1> 6件→PageLayout・骨格CSS 2系統→1系統 | 便0 | 素の<h1>残存0・骨格1系統 |
| 便5-guard | 骨格領域に関所: 素の<h1>新規をfail（領域ペア） | 便5 | 素の<h1>増分でfail稼働 |
| 便6 | 空状態独自3件→EmptyState・検索欄/テキスト書式の共通化 | 便0.5 | 空状態独自0・検索/書式1定義 |
| 便6-guard | 空状態・visual範囲の関所拡張（inbox/Karte以外へvisual gate拡張の可否をrecon） | 便6 | 隙間の縮小を実測 |
| 便7 | カタログ満数＋KGI③波及実測（部品定義1件変更→使用全ページ反映を実証） | 便2〜6 | KGI③④の◯/◯判定 |

## 3. ラチェット運用
- 色ラチェット: .github/workflows/design-token-guard.yml（便0bで新設・稼働中）
- hex上限の推移（真の分母ベース）: 36（便0.5時点）→ 便1a後に config分減 → 便1b後 0
- 領域ペア関所（便1c-guard/便2-guard/便5-guard/便6-guard）は各領域の掃除完了直後に増分阻止で追加
- 正当な例外は許可リストで管理（変更はPO承認必須）

## 4. 部品台帳（KGI①の分母の源泉・満数方式）
| # | 部品 | 金型（1ヵ所定義） | 現状（網羅recon実測 cbaee61） | 直書き残存の測り方 |
|---|---|---|---|---|
| 1 | プルダウン | components/Select.tsx | 採用19・pages自前<select>は別途 | pages配下<select>出現数 |
| 2 | 検索欄 | components/InventorySearchBar.tsx | 採用11・共通化弱い | placeholder=検索/type=search |
| 3 | ボタン | components/Button.tsx | 採用7 | ^\.btn 定義CSS数 |
| 4 | アイコン | constants/icons.tsx + iconSizes.ts | 採用27 | アイコン供給源 |
| 5 | テキスト書式 | 共通金型なし（便6で新設） | 43ファイル分散・未集約 | toLocaleDateString等 |
| 6 | ページ骨格 | components/PageLayout.tsx | 採用62・素の<h1> 6・骨格CSS 2系統 | pages配下<h1>数・骨格CSS系統数 |
| 7 | カード | components/Card.tsx | 採用2・独自CSS 0 | pages配下 .card |
| 8 | データ表 | components/DataTable.tsx | 採用22・素の<table> 28 | pages配下<table> |
| 9 | バッジ | components/Badge.tsx | 採用2・独自CSS 0 | pages配下 .badge |
| 10 | 空状態 | components/EmptyState.tsx | 採用1・独自3 | pages配下 empty-state/EmptyState |

## 5. 手当て漏れ対応表（網羅reconで露見・全て便に割当済）
| 露見した差分 | 現状 | 担当便 |
|---|---|---|
| 素の<table> | 28件 | 便2＋便2-guard |
| 素の<h1> | 6件 | 便5＋便5-guard |
| 空状態独自 | 3件 | 便6 |
| TS色定数の関所穴 | ガード無し | 便1c-guard |
| visual gateがinbox/Karteのみ | 他画面穴 | 便6-guard(拡張可否recon) |
| 検索欄・テキスト書式の共通化弱 | 未集約 | 便6 |

## 6. ADR整合（設計トラック内で扱う）
- ADR-067（色SSOT・:root/:root.force-dark・直書き禁止）: 便0.5でトークン正本化、便1a/1bで直書き解消。
- ADR-073（KGI 100%ルーブリック・中）: 本移行完了でKGI①〜⑤達成を目指す。設計トラック内。
- ADR-144（pages/生UI増殖防止・高）: 便2/便5/便6の金型寄せ＋領域ペア関所で対応。設計トラック内。

## 7. 弊害・トレードオフ（空欄不可）
1. 領域ペア関所は便数が増える（guard便が4つ）。ただし各領域を閉じてから次へ進むので逆流ゼロ。
2. 便0.5の用途命名は判断作業。既存用途名パターンに倣い、生値命名（便1旧版の失敗）は繰り返さない。
3. config.ts 21件は表示専用と確認済（JS分岐依存なし）だが、便1aは念のためvisual gate(schedule)で確認。
4. visual gateがinbox/Karteのみ＝他画面の掃除は自動検知外。便で手動画面確認を補う。
5. 便数が多く完了まで時間がかかる。安全優先の意図的選択。

## 8. 外部・過去事例
ラチェット漸減方式はESLint警告削減等の定石。前例ADR-067。

## 9. 受入基準
便別受入は§2。テーマ完了は kgi.md ①〜⑤が○（⑥達成済）。KGI③実証は便7。

## 10. 接触面分析（6面走査）
①人: PO承認＋各便の画面確認。②エージェント: select系並行便と便1系の衝突は該当時に状態実測。③機械: 領域ペア関所を順次新設。④データ: 影響なし。⑤本番: 便0.5〜6はUI直結（同値置換で緩和）。⑥外部: 影響なし。

## 維持の仕組み
- 守り手: design-token-guard.yml/check-design-token-ratchet.sh（便0b稼働中）＋領域ペア関所（便1c/2/5/6-guardで順次）＋部品台帳満数方式
- 対象: 生値ベタ書き・部品重複定義・台帳未登録の新部品・素の<table>/<h1>/空状態の新規
- 未確立（正直な明記）: 領域ペア関所は各guard便完了まで人が守る。


## 2026-09-10 表39か所の移行対応案

基準6e133572。origin/main=864ace729fe45a1b254fa2c3b8f66baa547d57faを取得し、frontend全体・design-system既存文書・UI検査本体との差分0を確認。製品未変更。

移行方式: 既存DataTableは公開propsを維持して内部を共通Table表示部品へ接続。他の38か所は行構造とコールバックを維持したままTable表示部品へ置換する案。全てをDataTableのcolumns形式へ組み替えない。新規の通常一覧はDataTableを優先する。外観CSSは下層の一つを共有するため、入口が2つでも外観の正本は増えない。

根拠: [全表コールバック](../../handoff/design-system-recon/evidence-20260910/table-behaviors.json)。全on属性を構文抽出し、onSelectも対象。表外の操作・呼出関数内部・権限判定の網羅的動作検証ではない。下表は移行対応の設計案で、移行完了表ではない。

| ID | 使用箇所（frontend/src以下） | 移行先 | 維持・確認する内容 | 状態 |
|---|---|---|---|---|
| TB-01 | components/CommissionPanel.tsx:186 | Table共通表示・既存行構造維持 | 担当割当の空値→null/数値変換、割当解除 | 設計対応済・実表示未検証 |
| TB-02 | components/DataTable.tsx:168 | DataTable内部→Table共通表示 | 既存sort/全選択/行選択/行クリック・キー操作を維持。ページ送りはtable外なので別途既存propsを維持 | 設計対応済・実表示未検証 |
| TB-03 | components/FedExRateModal.tsx:329 | Table共通表示・既存行構造維持 | 料金・通貨・service_typeを選択してモーダルを閉じる | 設計対応済・実表示未検証 |
| TB-04 | components/MergeCompanyModal.tsx:197 | Table共通表示・既存行構造維持 | 会社IDと選択時snapshotを行/ラジオ双方で更新 | 設計対応済・実表示未検証 |
| TB-05 | components/MergeContactModal.tsx:195 | Table共通表示・既存行構造維持 | 連絡先IDと選択時snapshotを行/ラジオ双方で更新 | 設計対応済・実表示未検証 |
| TB-06 | components/MergeLeadModal.tsx:184 | Table共通表示・既存行構造維持 | リードIDと選択時snapshotを行/ラジオ双方で更新 | 設計対応済・実表示未検証 |
| TB-07 | features/tcg-analysis-review/DiagnosticsDrawer.tsx:115 | Table共通表示・既存行構造維持 | 表内のonイベントなし。表示値・見出し・空状態を比較 | 設計対応済・実表示未検証 |
| TB-08 | features/tcg-distribution/DistributionTargetList.tsx:81 | Table共通表示・既存行構造維持 | 配信先編集・実行確認・無効化確認へ同じtargetを渡す | 設計対応済・実表示未検証 |
| TB-09 | pages/admin/ChannelMastersPage.tsx:80 | Table共通表示・既存行構造維持 | 同じchannel IDで削除処理を呼ぶ | 設計対応済・実表示未検証 |
| TB-10 | pages/admin/InventoryVisibilityPage.tsx:132 | Table共通表示・既存行構造維持 | role IDと項目キーで切替、当該roleを保存 | 設計対応済・実表示未検証 |
| TB-11 | pages/badges/BadgesPage.tsx:76 | Table共通表示・既存行構造維持 | 表内のonイベントなし。表示値と列順を比較 | 設計対応済・実表示未検証 |
| TB-12 | pages/buddy/BuddyPage.tsx:75 | Table共通表示・既存行構造維持 | 対象pair IDで終了処理、空状態の結合列を維持 | 設計対応済・実表示未検証 |
| TB-13 | pages/buddy/BuddyPage.tsx:91 | Table共通表示・既存行構造維持 | 表内のonイベントなし。空状態の結合列を維持 | 設計対応済・実表示未検証 |
| TB-14 | pages/commission-settings/CommissionSettingsPage.tsx:189 | Table共通表示・既存行構造維持 | role別typeと数値valueを更新 | 設計対応済・実表示未検証 |
| TB-15 | pages/company-detail/CompanyAddressesTab.tsx:30 | Table共通表示・既存行構造維持 | 住所編集と削除確認へ同じ住所を渡す | 設計対応済・実表示未検証 |
| TB-16 | pages/company-detail/CompanyContactsTab.tsx:102 | Table共通表示・既存行構造維持 | 連絡先のチャンネル追加・編集・統合・削除確認を維持 | 設計対応済・実表示未検証 |
| TB-17 | pages/inventory/InventoryPage.tsx:501 | Table共通表示・既存行構造維持 | 在庫IDによる選択と条件付き列・空状態を維持 | 設計対応済・実表示未検証 |
| TB-18 | pages/invoice-create/InvoiceCreatePage.tsx:257 | Table共通表示・既存行構造維持 | 請求作成に使う見積IDを読み込む | 設計対応済・実表示未検証 |
| TB-19 | pages/invoice-create/InvoiceCreatePage.tsx:322 | Table共通表示・既存行構造維持 | 明細の入力・単位変更時の重量更新・削除・数値/null変換を維持 | 設計対応済・実表示未検証 |
| TB-20 | pages/invoice-detail/InvoiceDetailPage.tsx:243 | Table共通表示・既存行構造維持 | 表内のonイベントなし。表示値と列順を比較 | 設計対応済・実表示未検証 |
| TB-21 | pages/invoice-detail/InvoiceDetailPage.tsx:305 | Table共通表示・既存行構造維持 | 合計/重量/送料/税/通貨と条件付き換算行を維持 | 設計対応済・実表示未検証 |
| TB-22 | pages/products/ProductsPage.tsx:286 | Table共通表示・既存行構造維持 | 商品2行・同一商品ゼブラ・名前sort・選択伝播停止・権限付き編集・drag順変更 | 設計対応済・実表示未検証 |
| TB-23 | pages/purchase-orders/PurchaseOrdersFormModal.tsx:165 | Table共通表示・既存行構造維持 | 発注明細の商品名/数量/原価更新と削除を維持 | 設計対応済・実表示未検証 |
| TB-24 | pages/quote-create/QuoteCreatePage.tsx:170 | Table共通表示・既存行構造維持 | 見積明細の入力・単位連動重量・削除・数値/null変換を維持 | 設計対応済・実表示未検証 |
| TB-25 | pages/quote-detail/QuoteDetailPage.tsx:175 | Table共通表示・既存行構造維持 | 小計/重量/送料/税/合計とcolSpan6を維持 | 設計対応済・実表示未検証 |
| TB-26 | pages/staff-reports/StaffReportsPage.tsx:99 | Table共通表示・既存行構造維持 | 表内のonイベントなし。表示値・空状態を比較 | 設計対応済・実表示未検証 |
| TB-27 | pages/super-admin/DexTab.tsx:343 | Table共通表示・既存行構造維持 | 表内のonイベントなし。表示値と列順を比較 | 設計対応済・実表示未検証 |
| TB-28 | pages/super-admin/FxRatePage.tsx:123 | Table共通表示・既存行構造維持 | 表内のonイベントなし。表示値と列順を比較 | 設計対応済・実表示未検証 |
| TB-29 | pages/super-admin/KnowledgeAliasesTab.tsx:352 | Table共通表示・既存行構造維持 | ルールIDの有効切替と編集を維持 | 設計対応済・実表示未検証 |
| TB-30 | pages/super-admin/KnowledgeAliasesTab.tsx:430 | Table共通表示・既存行構造維持 | 別名IDの有効切替と編集を維持 | 設計対応済・実表示未検証 |
| TB-31 | pages/super-admin/LLMBudgetTab.tsx:120 | Table共通表示・既存行構造維持 | 当該予算の編集開始と空状態を維持 | 設計対応済・実表示未検証 |
| TB-32 | pages/super-admin/ParseReviewPage.tsx:494 | Table共通表示・既存行構造維持 | draftのskipped/condition/unit/offer_type/ship_timing/数量/単価/別名/メモ、商品onSelectを維持 | 設計対応済・実表示未検証 |
| TB-33 | pages/super-admin/ProductMastersTab.tsx:267 | Table共通表示・既存行構造維持 | canDrag条件・drag ID・drop順変更・編集・削除を維持 | 設計対応済・実表示未検証 |
| TB-34 | pages/super-admin/SuppliersAdminTab.tsx:241 | Table共通表示・既存行構造維持 | 仕入元IDの選択と編集を維持 | 設計対応済・実表示未検証 |
| TB-35 | pages/super-admin/SuppliersAdminTab.tsx:348 | Table共通表示・既存行構造維持 | ルーティングIDの削除を維持 | 設計対応済・実表示未検証 |
| TB-36 | pages/super-admin/TcgLineImportPage.tsx:515 | Table共通表示・既存行構造維持 | 表内のonイベントなし。表示値と列順を比較 | 設計対応済・実表示未検証 |
| TB-37 | pages/super-admin/TcgParallelReportPage.tsx:156 | Table共通表示・既存行構造維持 | 表内のonイベントなし。colSpanの集計/空状態を比較 | 設計対応済・実表示未検証 |
| TB-38 | pages/super-admin/TcgParallelReportPage.tsx:201 | Table共通表示・既存行構造維持 | sp_code/total/diffのsortキーを維持 | 設計対応済・実表示未検証 |
| TB-39 | pages/super-admin/TcgSeriesTab.tsx:331 | Table共通表示・既存行構造維持 | 当該シリーズの編集・IDによる削除を維持 | 設計対応済・実表示未検証 |

受入の共通条件: 移行前後で同じfixtureの列順/表示値/行キー/結合セル/空状態が一致。上表の各操作は同じ対象ID・値で同じ処理を呼ぶ。機能を持たない行に架空の操作試験を足さない。light/dark・390/767/768/1279/1280pxで共通外観と折り返し・スクロールを確認。

未解決を明示: 初期の38か所分の行外観（ゼブラ・警告・無効化・強調等）を共通の許可propsへ対応させるCSS照合と、実表示は未完。構文の対応表39/39を、実装可能39/39・検証完了39/39とは宣言しない。代表の固定表示契約はdesign.md §Sを参照。


### 表示属性の移管先

[239属性の対応表](../../handoff/design-system-recon/evidence-20260910/table-appearance-mapping.json)にstyle180/className59を登録。Table共通props・列指定・外側配置・子部品へ移す案。対象239件の移管先未割当0、実装未着手。


## 2026-09-10 既存PRの採用・分離計画

POはSSOT関連を統合可能、原因を追えるものは分離して順番マージと指定。読み取り担当2名の報告を設計担当が照合して採用範囲を定める。基準main: 3bdf33d55d1dc7ee90a7eea7fd112dc76d51b1fe。旧PRの直接マージは行わず、最新mainから必要差分を再構成する。

| PR | 扱い | 根拠・保持する内容 |
|---|---|---|
| #2668 | Select部品は既反映。再適用しない | Select.tsx/FormField.css/Select.stories.tsxの3blobがmainとHEADで一致。main履歴4c670259。InvoicesPageの現在のContentToolbarを維持し旧filter-barへ戻さない |
| #2895 | アイコン専用色の同値aliasを材料便で再利用 | components.cssのicon-btn、EmptyState.css、icons.tsx/platform-icon.cssの対、DashboardPage.cssの装飾、InboxPage.cssの検索/ロック。16用途全てを無条件追加しない |
| #2911 | #2895との重複は1回のみ。用途を保つaliasと未使用色整理だけ再利用 | サイドバーの背景と文字を全てaccentにする変更は不採用。影の色変換は同値保証確認後の別材料便。CLAUDE.md削除や不整合なrecon参照は採らない |
| #2914 | 同値alias5件を材料便へ統合 | indicator明暗・sidebar active border明暗・light active color。linkを#1a73e8へ変更する1件は色変更なので不採用 |
| #2919 | 同値alias4件を同じ材料便へ統合 | sidebar-bg→bg-surface、accent-bg→accentの明暗。#2911の重複は再適用しない |
| #2889 | カレンダーの21用途を別PRで再構成 | 7分類×color/tint/text、ID/ラベル/業務処理を保持。未定義color-blue-800参照、releaseの前景/背景同色化、既存色からの変更は採らず現行値から用途表を作る |
| #2926 | 実装は不採用。目的を最後のCI便へ | タイトルwarnに対してexit1。列挙失敗exit0/読取失敗skip/同じ行のvar参照で別の直色を見逃すため完成品として再利用しない |

#2911/#2895共通10ファイルの製品変更行は同一（読み取り担当がgh pr diffとmerge-base→HEAD diffを対照）。5色PRの製品変更は延べ28ファイル/重複除外14ファイル。元の変更行の既反映0、ただし別PRである#2668の3blob一致とは区別する。詳細の全changed product file照合は追加調査記録に残す。

Badgeの文字全体、sidebar/mobileのナビ項目全体、GoogleCalendarStatusBarのバー文字はアイコン専用用途へ付け替えない。各部品の用途色を保持する。GoogleCalendarStatusBarのuseEffect依存追加は色移行と分離し、本テーマでは採らない。

legacy --cal-*21名前×明暗の削除は参照0の最終全域調査が通ってから材料便で扱う。var参照0だけで動的参照なしと断定しない。

戻しやすさ: 同値alias/アイコン数値生成/カレンダー色/部品本体/使用先移行/CIを別の変更単位にし、各PRのmain SHAと検証ログを記録する。後継の採用結果が確定する前に旧PRをcloseしない。

### 次便の実行条件確認（2026-09-10）

PR #3420はmerge a5e5a250aabe2e244ebf64c24bef40b5db40541c、最終HEADc3f8668eのCI38成功/8対象外、公式merge/cleanup完了を直接確認。次便はこのmain起点。カレンダー21値/20固有色の移管と既存ファイル単位hex増加禁止が衝突し、限定契約を自己審査REVISE。製品未変更。根拠: docs/handoff/design-system-recon/evidence-20260910/calendar-source-audit.md。推奨は色移管保留→共通部品先行、POの順序判断待ち。CIを変更・迂回しない。


### 2026-09-11 現在の実装順序・検収記録

上記「POの順序判断待ち」は2026-09-10時点の履歴。その後の続行指示に基づき、design.md§AC/ADの共通部品先行を実施。カレンダー色は保留、新CIは全画面移行後。

| 変更単位 | 保存済み根拠 | 現在状態 |
|---|---|---|
| ICON5数値生成 | PR3412 merge6d3e3486 / icon-source-implementation.md | マージ済み、数値同値 |
| カラー同値alias | PR3420 mergea5e5a250 / color-source-implementation.md | マージ済み、静的25/色50/表示60比較 |
| Button ref/処理中Spinner | PR3423 merge76c6dff9 / button-contract-implementation.md | マージ済み、操作/Spinner各18・reduced9、最終CI38成功/8対象外 |
| 通常Icon API | design.md§AE / icon-contract-recheck.md | PR3426反映後main5de8afa1で4ファイル再検収済み。厳格lint/179試験/表示8条件成功、PR提出へ |

根拠ファイルはdocs/handoff/design-system-recon/evidence-20260910配下。各便の既存部品所有元は継承し、通常Iconはfrontend/src/constants/icons.tsxのhiと公開Icon各export、値はtokens.css/生成iconSizes.ts、色は既存用途CSS。唯一の配置移管先はGoogleCalendarStatusBar.cssの同SVG配置2宣言。これは全画面移行完了やclassName入口全閉鎖の証拠ではない。型監査の152 JSX/118実運用分類はIconProps経路の分母で、全アイコン種別の総数ではない。


2026-09-11再開: 前提callback修正PR3426をmerge5de8afa1でマージ済み。Icon便を同mainへ復元して再検証へ進む。旧「別PR修正の順序PO判断待ち」は履歴、現在は最新基準の検証/PRが次の一手。新CIは全画面移行後。


### 2026-09-11 PR3432完了と次便AH

通常Icon PR3427はmergeb16a4224、Button外観PR3432はmerge7606ca9a041e315b81040373e8f4ddebbc562133、両便の最終CI38成功/8対象外をroot直接確認済み。Button本体外観のownerはButton.tsx/Button.css、材料tokens.css/index.css。AGの既存70利用を移管済み、操作維持の詳証はbutton-appearance-implementation.md。全raw移行完了ではない。

旧raw352の表記は広い正規表現の集合。再監査で先頭btn-*332/専用20へ分解。次便AHはBSA002–006/025–035の16利用（6共通部品）。設計自己審査済み、実装/検収は未完。新CIは全画面移行後。


EV-20260911-FRONTEND-MOLD-27: AH移管で390px発送footerの画面外欠けをroot実測（ja左端-30.140625、en-20.484375、旧24）。AH提出条件REVISE、未検証7ファイルを退避予定。先行AIはModal footer折返し＋見本の2製品に限定。通常footer実運用3/見本2を監査し、局所wrap28条件の左右欠け0を確認。詳細design.md§AIとraw-shared-footer-probe/全利用監査。実装/最終検収/新PR未完。

2026-09-11 AI先行実装検収済み: 共通Modal footer wrapと見本2製品。560前後比較/輪郭448/Story4、root189unit等品質5項目成功、限定レビューAPPROVE。PR提出準備中。AH16移管は退避した未検証案、旧通常btn332の減少はまだ0。新CI最後。根拠: [AI検収](../../handoff/design-system-recon/evidence-20260910/modal-footer-implementation.md)。

2026-09-11 AI PR #3435提出済み https://github.com/shingo-ops/salesanchor/pull/3435 （ready、HEAD3935e17d）。main ec173b7e通常統合、今回製品差分Modal2のみ・hash不変。root統合unit200件成功。CI確認中、番号付きGO/マージ/PO目視未完。AH16保留、新CI最後。

2026-09-11 18:01 JST（受領後記録）: PO原文「GO #3435」を受領。対象はPR3435の共通Modal footer修正。製品2hashは検収版と同一。最新CI確認後に正式merge、PO目視/本番確認は未実施。AH16移管はこの前提のマージ後に再開、新CIは最後。


### 2026-09-11 AH再開（PR3435マージ後）

先行PR #3435は2026-09-11T09:07:09Zにmerge adc8bc4d67a94e8ede45a1e9c0ee9f28d28bb70bでマージ済み。rootがGitHub APIのMERGEDと最終HEAD9780f1dcのCI38成功/8対象外を直接確認。PO目視・本番反映は未確認。

PO原文「進めてくれ」を受領し、同mergeを起点にrelease/frontend-shared-button-migrationを公式手順で作成。AHの6TSXは退避基準7606ca9aから差分0、Button本体とModal.tsxも差分0、Modal.cssは先行wrap1行だけを確認。再監査でも旧先頭btn332/専用20、AH16原文一致。7退避案は未検証扱いで復元後の操作/表示検収へ進む。新CIは全画面統一後、最後。

CARD-RAW-SHARED-RESUME-02は正式card-lint exit0（長行警告のみ）。Generatorは6TSXと回帰試験の7製品のみ、rootは設計・検収・記録を担当する。AHの製品契約変更なし。Planner追補後、同一AI Architectとして再開前提の整合を自己審査APPROVE。AHの提出合格は実検証と限定第二レビュー後に別途判定し、現時点で未完。新PR番号付きGOは未受領。


2026-09-11 AJ分割: CommissionPanel3利用は390px英語の横overflow528→537pxと輪郭欠けを実測したため、表統一便へ保留。残5部品13利用を先行、目標Button70→83/旧btn332→319。20単独操作試験は成功、全体coverageとbuildは未合格。詳細design.md§AJ。新CI最後、PO目視未確認。


PO再起動指示により中断保存。現コード16移管WIP、AJ13分離は未適用。再開入口: [ah-restart](../../handoff/design-system-recon/evidence-20260910/ah-restart.md)。本便PR/GO/最終検収未完。
