# 設計: 在庫表・閲覧ページの既定の並びを「発売日の新しい順」にする

- recon: docs/handoff/inventory-sort-release-date-desc/recon.md
- 対象ADR: ADR-1014（既定の並び。2026-10-18 改訂の向き asc を desc に改める）、ADR-1023（同じ商品の中の価値順。変えない）
- 前便: #4499（docs/handoff/inventory-sort-release-date-groups/design.md）

## PO の言葉
- 「発売日の新しい順にしてほしい、いまは古い順になっている」（2026-10-18）

## 目的（利用者に見える変化）
在庫表と閲覧ページを開いたとき、商品のまとまりが発売日の新しい順に並ぶ。並び替えのプルダウンの発売日の選択肢は「発売日が新しい順」になる。
- 同じ発売日の中は今と同じ（英語タイトル → 日本語タイトル → 商品ID）
- 同じ商品の中は今と同じ（状態の価値の高い順 → 安い順、#4502）
- 発売日が空の商品は今と同じく最後

## 変更前 → 変更後
| 箇所 | 変更前 | 変更後 |
|---|---|---|
| frontend/src/pages/inventory/InventoryPage.tsx:54 | `"release_date:asc"` | `"release_date:desc"` |
| InventoryPage.tsx:112 既定 sortDir | `"asc"` | `"desc"` |
| InventoryPage.tsx:332 resetAll | `setSortDir("asc")` | `setSortDir("desc")` |
| InventoryPage.tsx:454 付近 選択肢 | 値 `release_date:asc`、ラベル `inventory.sortMenu.releaseAsc` | 値 `release_date:desc`、ラベル `inventory.sortMenu.releaseDesc` |
| frontend/src/pages/viewer/viewerFilter.ts:13 | `DEFAULT_SORT_DIR = "asc"` | `"desc"` |
| viewerFilter.ts:15 | `"release_date:asc"` | `"release_date:desc"` |
| frontend/src/pages/viewer/InventoryView.tsx:210-213 | 値 `release_date:asc`、ラベル `viewer.sort.releaseAsc` | 値 `release_date:desc`、ラベル `viewer.sort.releaseDesc` |
| frontend/src/locales/ja.json:1561 | `releaseAsc`「発売日が早い順」 | キーを `releaseDesc`、文言「発売日が新しい順」 |
| frontend/src/locales/en.json:1561 | `releaseAsc` "Release date (oldest first)" | `releaseDesc` "Release date (newest first)" |
| frontend/src/locales/viewer/ja.json:30 | `releaseAsc`「発売日が早い順」 | `releaseDesc`「発売日が新しい順」 |
| frontend/src/locales/viewer/en.json:30 | `releaseAsc` "Release date (oldest first)" | `releaseDesc` "Release date (newest first)" |
| backend/app/routers/inventory_offers.py:354 API 既定 order | `"asc"` | `"desc"`（画面は必ず order を送るので画面の挙動は変わらない。API の既定を画面の既定と揃える） |

- 使わなくなる `releaseAsc` キーは ja/en の両方から消す（同一キー必須 ADR-027）
- 試験: recon の「試験」節の各箇所を新しい既定（desc）に合わせる。backend の ORDER BY の文字列試験は、API 既定の変更で期待が変わるものだけ直す

## 触らない範囲
- backend の ORDER BY の組み立て（inventory_offers.py:264-279）。order=desc を受けると既に商品のまとまりが新しい順になる
- 同じ商品の中の並び（sort_ord、tcg_result_order.py）、配信 SQL、GAS 在庫一覧（リポジトリ外）
- プルダウンの他の3択（価格・在庫・投稿）とその文言
- 画面の部品・色・レイアウト（金型の変更なし）

## 代替案
- A. プルダウンに「早い順」「新しい順」を両方置く: PO の指示は既定の向きの変更のみで、選択肢を増やす指示はないため不採用
- B. API 既定は asc のまま: 画面と API の既定が逆になり、次の変更で取り違える元になるため不採用

## リスクと対処
- 他の試験やリンクが order=asc を前提にしている: recon で列挙した試験を全部直し、`git grep -n "release_date:asc\|releaseAsc"` が 0 件になることを確かめる
- i18n キーの片側漏れ: ja/en の同一キー検査（CI）で検出

## 受入条件
| 基準 | 検証方法 |
|---|---|
| 在庫表の既定が発売日の新しい順 | InventoryPage.tablelayout.test.tsx で既定のプルダウン値が release_date:desc、API 呼び出しが order=desc |
| 閲覧ページの既定が発売日の新しい順 | viewerFilter.test.ts・InventoryView.test.tsx で既定 desc、新しい発売日の商品が先 |
| 同じ商品の中・空の発売日の扱いが変わらない | 既存の viewerFilter.test.ts の該当試験 pass |
| 旧キー・旧値が残らない | `git grep -n "release_date:asc\|releaseAsc" -- frontend backend` 0 件 |
| i18n・lint・型 | frontend の lint・tsc・vitest、backend の ruff・関連 pytest、CI 全緑 |
| ADR 索引 | CI「ADR index is up to date」pass |
| 本番反映 | デプロイ success、本番の配信 JS に「発売日が新しい順」と "Release date (newest first)" があること。画面は PO 目視 |

## 外部・過去事例の参照と我々への応用
- 過去事例（社内）: #4499 で既定を asc にしたとき、CommerceNavigationButtonMigration.test.tsx の order 値の取り残しで CI が落ちた。今回は旧値の grep 0 件を受入条件に入れて取り残しを防ぐ
- 外部事例: 使わない。理由: 並びの向きは PO の決定が正本で、外部の数値で決める性質のものではないため

## 維持の仕組み
- 守り手: InventoryPage.tablelayout.test.tsx・viewerFilter.test.ts・InventoryView.test.tsx が既定の向き desc を固定する。向きの決定は ADR-1014 の改訂節に記録する

## 追補1（2026-10-18）: API の契約ファイル
- CI「API contract is up to date」が frontend/api-contract/openapi.json の /inventory の order 既定 `"asc"` と、コードの既定 `"desc"` が食い違うとして fail（生出力 /tmp/CC報告ファイル/inventory-sort-desc/api-contract.txt）
- 対処: openapi.json の該当1行（name "order"、title "Order" の default）を `"desc"` に直す。手元で作り直すと Python の版の違いで無関係な差分が出るため、作り直しはしない。正しさは同じ CI の検査が確かめる
- 変更の対象に frontend/api-contract/openapi.json（1行）を加える

## ADR-1014 への追記（実装担当が行う）
- 「改訂 2026-10-18（2）」節を足す: 既定の向きを desc（発売日の新しい順）に改める。PO「発売日の新しい順にしてほしい、いまは古い順になっている」（2026-10-18）。前の改訂節の本文は書き換えない
- `node scripts/generate-adr-index.js` を実行する
