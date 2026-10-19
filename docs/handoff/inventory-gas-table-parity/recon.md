# recon: GAS 在庫一覧の表を閲覧ページと同じ形にする

基準: origin/main 9c7bbb917（design.md 冒頭）。GAS の土台は ~/CC報告ファイル-keep/inventory-sort-3choices/gas/test_stage/index.html（テスト GAS @26）。
元資料: /tmp/CC報告ファイル/inventory-gas-table-parity/recon/（diff-table.md ほか）。

## 1. 変更前の GAS 列定義
- gas test_stage/index.html:1531-1543（列順）: 投稿日時/マーク/商品名/コンディション/単価/数量/備考/発送日/提供者/ステータス/発売日（diff-table.md:3）
- セル描画: gas test_stage/index.html:1564-1588、`badgeCondition`・`badgeStatus` は :1696-1711、`formatPostedAt` は :959-964
- 見出し・セルは中央揃え（:406-416, :436-443）、左固定は商品名（:427-434, :446）

## 2. 閲覧ページ（正本）の列定義
- /Users/tanizawashingo/salesanchor/frontend/src/pages/viewer/viewerColumns.tsx:28（`buildViewerColumns`）、`formatPrice` :17、`formatPostedAt` :24
- 閲覧の列順: ステータス(stickyLeft)/型番/タイトル/状態/単価/数量/備考/発送/提供者/発売日（diff-table.md:2 は在庫表 frontend/src/features/inventory/inventoryColumns.tsx:51-207 の順）
- 文字色: frontend/src/features/inventory/conditionBadge.ts:16-37、frontend/src/features/inventory/inventoryColumns.css:1-50
- トークン: frontend/src/index.css:55（warning-text）・:125（purple-text）、frontend/src/tokens.css:392-393（offer-*-text）
- ステータス対応: backend/app/services/tcg_distribution_svc.py:277（OFFER_TYPE_TO_STATUS）

## 3. 差の一覧（design.md 2〜3章）
| 項目 | 変更前（GAS） | 変更後 | design.md |
|---|---|---|---|
| 列順 | 投稿日時が先頭、ステータスが後ろ | 閲覧と同じ（ステータス先頭） | 3-6 |
| 見出し | 「価格」「投稿日時」等 | 閲覧の viewer-ja.json "col" と同じ（「単価」「発送」等） | 3-6 |
| 揃え | th/td とも中央 | 左（数字列は右） | 3-2 |
| 左固定 | 商品名 | ステータス（`col-sticky`） | 3-3 |
| 商品名 | 英語が上 | 日本語が上・英語が下 | 3-4 |
| 文字色 | `.badge` 系 | `inventory-cell__offer--*`・`__condition--*` | 3-5 |
| 単価 | 数字のみ | 「¥」＋3桁区切り | 3-7 |
| 投稿日時 | 独立列 | 提供者の下の段 | 3-6, 3-7 |
| トークン | 4つ欠け | 正本と同じ値で追加 | 3-1 |
対象外・GAS で出せないもの: design.md 2章。

## 4. 既存 ADR 検索（git grep）
- 実行: `git grep -il "ADR-1014\|ADR-1023\|ADR-067\|ADR-027" -- docs/adr/FEATURE-INDEX.md` ほか
- ADR-1014（docs/adr/ADR-1014-inventory-view-shows-distribution-rows.md）: 在庫表・GAS の揃え。改訂（3）で「GAS は未実装」と記録 → 本件で改訂（7）を追記
- ADR-1023（docs/adr/ADR-1023-condition-value-rank.md）: 状態の価値順。conditionBadge の値の表の根拠
- ADR-067（docs/adr/ADR-067-design-token-enforcement.md）: トークン。GAS の写しも正本と同じ値
- ADR-027（docs/adr/ADR-027-ui-internationalization.md）: ADR-027 は GAS に触れていない（Scope 外の節にも記載なし）。今回 GAS の文字列は直書きのまま、アプリ側コードは変更なし。GAS を i18n の対象にするかは未決定
- FEATURE-INDEX.md には ADR-027 の行のみ（:37）
