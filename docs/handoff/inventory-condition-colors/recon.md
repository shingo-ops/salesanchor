# recon: 在庫表・閲覧ページ「状態」列の色分け

- 実測時の origin/main SHA: 472c172973795181b38728da0b01d57d818339a0
- 生出力: /tmp/CC報告ファイル/condition-colors/recon-raw.txt ・ checks-raw.txt ・ contrast.js
- 事実のみ。評価・提案は design.md

## 1. 状態バッジの現状（フルパス:行番号は origin/main 時点）
- frontend/src/features/inventory/conditionBadge.ts:1-4 冒頭コメント「GAS 在庫一覧 H:1591-1605 と同じ規則」「sealed→success / damaged→danger / case→info / 他→neutral」
- frontend/src/features/inventory/conditionBadge.ts:7-18 `conditionBadgeVariant`。trim・小文字化の完全一致。"sealed"→success / "damaged"→danger / "case"→info / default→neutral
- 呼び出し元（2か所）
  - frontend/src/features/inventory/inventoryColumns.tsx:114 `<Badge variant={conditionBadgeVariant(it.condition)}>{it.condition}</Badge>`
  - frontend/src/pages/viewer/viewerColumns.tsx:70 同形
- 関連試験
  - frontend/src/features/inventory/conditionBadge.test.ts:4-16
  - frontend/src/features/inventory/inventoryColumns.test.tsx:37-40（"sealed"→success / "damaged"→danger / "case"→info / "New"→neutral）
  - frontend/src/pages/viewer/viewerColumns.cells.test.tsx:48-50（["sealed","damaged","case","New"]）
  - frontend/src/pages/inventory/InventoryPage.tablelayout.test.tsx:14,48（fixture condition 'sealed'、期待 comp-badge--success）
  - 他に condition: "sealed" を fixture に持つだけの試験（色は見ない）: frontend/src/pages/viewer/InventoryView.test.tsx:19 / frontend/src/pages/inventory/InventoryPage.rowdrawer.test.tsx:26 / frontend/src/pages/viewer/viewerFilter.test.ts:35-37

## 2. Badge の金型
- frontend/src/components/Badge.tsx:4 冒頭コメントの variant 一覧「neutral / info / success / warning / danger」
- frontend/src/components/Badge.tsx:16 `export type BadgeVariant = 'neutral' | 'info' | 'success' | 'warning' | 'danger';`
- frontend/src/components/Badge.css:58-62 soft（neutral/info/success/warning/danger の5行）
- frontend/src/components/Badge.css:65-69 solid（同5行。success は --comp-badge-success-solid、danger は --comp-badge-danger-solid、他は --neutral/--info/--warning）
- frontend/src/components/Badge.stories.tsx:21-43 AllVariantsSoft / AllVariantsSolid（各5種）
- frontend/src/pages/design-preview/sections/BadgeSection.tsx:3 と :14 に「variant 5」、:18 に配列 ["neutral","info","success","warning","danger"]
- BadgeVariant を import する他ファイル（型の拡張のみ影響）: frontend/src/features/tcg-import-workflow/ImportWorkflowPanel.tsx:4 / frontend/src/pages/admin/DiscordConfigPage.tsx:20,64,72 / frontend/src/pages/super-admin/ViewerAccountsPage.tsx:14,45 / frontend/src/pages/super-admin/components/ExtractionErrorLogPanel.tsx:22,75,87,220 / frontend/src/pages/super-admin/components/LineWorkflowGuidePanel.tsx:3,16（いずれも Record<…, BadgeVariant> は Record<string|列挙, …> 形で、BadgeVariant をキーにした網羅型は無い）

## 3. 紫トークン（既存）
- ライト frontend/src/index.css:124-125 `--purple-bg: #e9d8fd;` `--purple-text: #553c9a;`（コメント :123「purple バッジ（保留・発送済み）」）
- ダーク frontend/src/index.css:313-314 `--purple-bg: #3b1f6e;` `--purple-text: #d8b4fe;`
- 既存の利用: frontend/src/pages-layout.css:465-466 / frontend/src/components.css:246,252
- 塗り用（solid）の紫トークン: 無し

## 4. ADR-1023 の12値（docs/adr/ADR-1023-condition-value-rank.md:36-38）
- box: Sealed box 1 / Damaged sealed box 2 / No shrink box 3 / Opened box 4 / Searched box 5
- case: Case 1 / Damaged case 2 / Opened case 3
- pack: Unsearched pack 1 / Searched pack 2 / AR confirmed pack 3
- 対象外（NULL）: Empty box / FLAG_SINGLE / Error / Bulk / 空箱 Case
- 状態マスタの正本は DB public.line_conditions（同 ADR :25-26）

## 5. 本番頻度（design.md の数値を引用。2026-10-17 14:03Z・873 行）
Sealed box 527 / Case 153 / Damaged sealed box 84 / No shrink box 43 / Damaged case 28 / Searched pack 17 / Bulk 10 / Opened box 7 / Unsearched pack 4。旧小文字値 "sealed"/"damaged" は 0 件。

## 6. コントラスト比（/tmp/CC報告ファイル/condition-colors/contrast.js の出力。checks-raw.txt）
| | neutral | info | success | warning | danger | purple |
|---|---|---|---|---|---|---|
| ライト | 6.10 | 4.01 | 7.30 | 7.86 | 5.70 | 6.28 |
| ダーク | 4.04 | 6.38 | 9.28 | 10.47 | 9.67 | 7.39 |

## 7. 検査が要求するもの
- scripts/check-design-token-ratchet.sh:7-10 BASE_SHA と HEAD_SHA が必須。:49-72 の対象は frontend/src 配下の *.css/*.tsx/*.jsx/*.ts（tokens.css 除く）で、ファイルごとの hex 数が base より増えたら FAIL
- frontend/scripts/check-new-tokens.js:13-22 GITHUB_BASE_REF 未設定（ローカル）は常に exit 0。:36 の対象は src/tokens.css と src/index.css の新規トークン
- frontend/scripts/check-dark-parity.js 実行結果: 「PASSED (130 変数すべて対応済み)」（checks-raw.txt）

## 8. 既存 ADR 検索
- `git grep -il "condition\|badge" docs/adr/` の該当（ADR 本体）: ADR-009 / 050 / 057 / 065 / 067 / 090 / 093 / 099 / 1001 / 1004 / 1007 / 1014 / 1019 / 1021 / 1023 / 105 / 120 / 138 / 143 / 154 / 156 / 158（ほか README.md・FEATURE-INDEX.md・karte_reference.html）
- 関係が確認できたもの
  - docs/adr/ADR-1023-condition-value-rank.md: 状態 12 値と価値順
  - docs/adr/ADR-067-design-token-enforcement.md:33,52-53: バッジの padding トークン化。色トークン追加の統制
  - docs/adr/ADR-120-status-presentation-ssot.md:1-3,15-30: ステータス（lead 等のドメイン状態）→ bucket 5分類の中央対応表（frontend/src/utils/statusPresentation.ts）。在庫の「状態（condition）」は対象ドメインに含まれていない（同 ADR の構造例・バケット表に condition の記載なし）
- docs/adr/FEATURE-INDEX.md: 「状態」「condition」を含む行は 2 行（:53 と :62）で、いずれも deploy・migration の項目。状態バッジの色に関する行は無い
