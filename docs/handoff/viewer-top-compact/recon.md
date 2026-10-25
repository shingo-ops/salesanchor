# recon: 閲覧ページ上部の現在地（便3「24時間を奥へ／シリーズを並び替えの左へ」）

> この文書は何か（1行）: PO 指示「24時間のフィルタを詳細画面に移動、中分類の絞り込み機能を並び替えの左側に配置」を実装する前の、現在地の一次情報。

**日付**: 2026-10-25
**対象**: 閲覧ページ `frontend/src/pages/viewer/`（**アプリ本体の `frontend/src/pages/inventory/` とは別コード・別辞書**。正本は ADR-1019）
**前便**: 便1 `docs/handoff/viewer-inventory-mobile-filter/design.md`（PR #4731）／便2 `docs/handoff/viewer-filter-subscreen/design.md`（PR #4740・本番反映済み）

## 1. PO 指示（原文・2026-10-25）

> 24時間のフィルタを詳細画面に移動、中分類の絞り込み機能を並び替えの左側に配置

**言葉の対応**（取り違え防止のため実物で確認した）:

| PO の言葉 | 実物 | 根拠 |
|---|---|---|
| 24時間のフィルタ | 「{{hours}}時間以内」の切り替えボタン（既定**オン**） | `frontend/src/pages/viewer/InventoryView.tsx:335-346`（`freshButton`）・`:67`（`useState(true)`）・文言キー `viewer.freshOnly`（`frontend/src/locales/viewer/ja.json`） |
| 詳細画面 | 絞り込みドロワー（便2 で「項目をタップ→次の画面」にした画面）の最初の画面 | `frontend/src/pages/viewer/InventoryView.tsx:536-556` 付近の `Drawer`・便2 design `docs/handoff/viewer-filter-subscreen/design.md` 4-4 |
| 中分類の絞り込み機能 | 「シリーズ」の選択（スマホは全幅の選択部品1つ） | `frontend/src/pages/viewer/InventoryView.tsx:407-418`・文言キー `viewer.tabSelect` = 「シリーズ」。データは `series`（`frontend/src/pages/viewer/types.ts` の `ViewerRow.series`）。アプリ本体の語彙では「中分類（作品カテゴリ）」に当たる（`frontend/src/locales/ja.json` の `typeMaster` = 「中分類マスタ」・`subtitle` = 「中分類（作品カテゴリ）を管理します」）。**閲覧ページのデータに中分類そのものの列は無い**ので、新しい絞り込みを作るのではなく既にある「シリーズ」を動かす、と解釈した |
| 並び替え | 並び替えの選択部品 | `frontend/src/pages/viewer/InventoryView.tsx:347-371`（`sortMenu`）・文言キー `viewer.sort.placeholder` |

## 2. 上部 236px の内訳（便1 の実機実測。**便2 のマージ後も有効**）

出典は `docs/handoff/viewer-inventory-mobile-filter/recon.md:98-113`（実機 Chrome の DevTools で `getBoundingClientRect` を直読み。360px 幅）。

| 範囲 | 高さ | 正体 |
|---|---|---|
| 0 → 68 | **68** | ヘッダー（題28／最終更新22／言語44）。`frontend/src/pages/viewer/viewer.css:7-13` |
| 68 → 112 | 44 | シリーズの選択（全幅・自分の行を1つ占める） |
| 112 → 124 | 12 | 操作台の `margin-top`（`frontend/src/pages/viewer/viewer.css:31`） |
| 124 → 168 | 44 | 検索欄 |
| 168 → 180 | 12 | 操作台の `gap`（同 `:30`）＝**360px では操作台が2行に折り返している** |
| 180 → 224 | 44 | 24時間以内84／並び替え108／絞り込み72 |
| 224 → 236 | 12 | 操作台の `margin-bottom` |

**便2 で上部を触っていないことの確認**: 便2 の触るファイル一覧（`docs/handoff/viewer-filter-subscreen/design.md` ⑥）に上部の markup は含まれず、現物も一致した
（ヘッダー = `frontend/src/pages/viewer/InventoryView.tsx:388-404`／シリーズ = `:407-418`／操作台 = `:420-428`／CSS = `frontend/src/pages/viewer/viewer.css:7-13`・`:26-32`）。

## 3. 使えるトークン（実値）

| トークン | 値 | 出典 |
|---|---|---|
| `--space-3` | 12px | `frontend/src/tokens.css:71` |
| `--space-4` | 16px | `frontend/src/tokens.css:72` |
| `--space-12` | 48px | `frontend/src/tokens.css:78` |
| `--field-h-sm` | 28px | `frontend/src/tokens.css:164` |
| `--field-h-lg` | 44px | `frontend/src/tokens.css:166` |
| `--size-icon-btn-lg` | 44px | `frontend/src/tokens.css:163` |
| `--comp-btn-height-lg` | 48px | `frontend/src/tokens.css:462` |

**48px の高さトークンは既に2つある**（`--space-12` は余白用・`--comp-btn-height-lg` はボタン用）。
便2 design ⑫ で「48px トークンの新設は便3 で起案」としていたが、**新設は不要**（既存を使えばよい）。

## 4. 幅の制約（1行に収まるか）

360px 幅で `frontend/src/pages/viewer/viewer.css:24`（`.viewer-main` の `padding: 0 var(--space-4)`）を引くと**中身に使えるのは 328px**。
便1 の実測値（並び替え108／絞り込み72）と `gap: var(--space-3)`（12px）×2 から、
**シリーズに残るのは 328 − 108 − 72 − 24 = 124px**。
現在のシリーズ選択は全幅（328px）なので、**そのまま置くと必ず折り返す**。幅を詰める指定が必要（§設計で扱う）。

## 5. お手本（メルカリ）の3行目は同じ並び

`docs/specs/design-system/visual-language/benchmark/mercari-search-filter.md:41` の実測:
3行目は `status_check_box`「販売中のみ」98.7x48 ／ `sort_menu`「おすすめ順」90.7x48 ／ `filter`「絞り込み」77.3x48。
**「絞り込みの種類＋並び替え＋絞り込み」が1行に並ぶ形**＝本便で作る形と同じ。
同 `:43` のとおり、お手本は3行目のボタンに**枠線が無く**、同じ 48dp の中に文字がゆったり入る。

## 6. 既存の守り手

| spec | 何を測っているか | 上部の高さを測っているか |
|---|---|---|
| `frontend/tests-e2e/visual-language/viewer-inventory-mobile-filter.spec.ts` | 絞り込み副画面 A1〜A18（便2） | **いいえ** |
| `frontend/tests-e2e/visual-language/viewer-helpers.ts` | mock と `gotoViewer()` | 上部を測るヘルパーは**無い** |

→ **閲覧ページ上部の高さを測る検査は1本も無い**。CI で走る Playwright は `frontend/playwright.config.ts:64`・`:69`・`:74` の `testMatch` により
`visual-language/` 配下に限られる（`tests-e2e/` 直下に置くと1本も走らない。`docs/handoff/viewer-filter-subscreen/design.md` ⑪ と同じ注意）。

## 7. 24時間フィルタを奥へ移すときの落とし穴（実装前に分かっていること）

- **既定がオン**（`frontend/src/pages/viewer/InventoryView.tsx:67`）。今はボタンが `variant="primary"` で強調されるため、
  絞り込みが効いていることが**一目で分かる**（`:337`）。奥へ移すと**既定で絞られているのに画面に手がかりが無くなる**。
- 判定に使う「今」は `data` が差し替わるたびに取り直している（`:58`・`frontend/src/pages/viewer/InventoryView.tsx:106-107`）。移しても同じ仕組みを使う。
- 絞り込みドロワーの中身は便2 で「項目1行ずつ」の形になっている。チェック欄の金型は `frontend/src/components/CheckboxControl.tsx:1-9`（`div`/`label` を増やさない設計）。
- 件数の札を出すなら金型は `frontend/src/components/Badge.tsx` が既にある。

## 8. この端末の制約

実機の ADB は**未接続**（2026-10-25 夕方時点。`adb devices` が空）。`docs/handoff/viewer-filter-subscreen/design.md` の便2 と同じく、
**寸法の一次情報は CI の Playwright ログだけ**になる（この端末では Playwright のブラウザが入らない）。
本番に出た後の確認は `https://app.salesanchor.jp/viewer/` の配布ファイルの照合で代替できる（便2 で実施）。
