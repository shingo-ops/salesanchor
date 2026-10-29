# recon: 種別／シリーズの名前が読めない（在庫表・閲覧ページ）

一次情報は **本番の実機**（Android・幅360・dpr3・`app.salesanchor.jp/inventory`・配布物 `main-CDzTgcs`）を
Chrome DevTools Protocol で直読みした値と、**作業ツリーのファイルそのもの**。
この端末では Playwright のブラウザが入らないため、画面検査の合否は CI ログだけが一次情報。

## 1. 不具合の実測（本番実機・2026-10-29）

便2（PR #4848）の実機確認 K1〜K10 のうち **K2 だけ ✗**。画面には「ポ ⌄」しか出ていない。

| 測った値 | 結果 |
|---|---|
| `inventory-tab-select` 配下の `.inventory-toolbar__label` の `clientWidth` | **13px** |
| 同 `scrollWidth`（「ポケモン」） | 52px |
| 同（「ヴァイスシュヴァルツ」） | 129px |
| 同（「マジック：ザ・ギャザリング」） | 168px |
| 並び替えに「価格が安い順」を選んだときの `clientWidth` | **0px** |
| 操作台 `.inventory-toolbar` の内側の幅 | 312px |
| 2段目の内訳 | 種別 62.5 ＋ 並び替え 101.7 ＋ 詳細フィルタ (1) 123.8 ＋ すき間 24 |
| 操作台の高さ | 108px |

種別だけ `flex: 1 1 0; min-width: 0` なので**残り物の 62.5px に押し込まれ**、
左右の余白24・山形16・すき間8 を引いた **13px** しか文字に残らない。

## 2. 閲覧ページ（お手本）も同じ

- `frontend/src/pages/viewer/viewer.css` の `.viewer-toolbar > .viewer-toolbar__series` は
  **在庫表とまったく同じ** `flex: 1 1 0; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap`。
- 並びも同じ（検索が1行を独り占め → シリーズ・並び替え・絞り込みが2段目）。
- **文言だけが違う**: 閲覧ページ `frontend/src/locales/viewer/ja.json` は「絞り込み ({{count}})」、
  在庫表 `frontend/src/locales/ja.json` は「詳細フィルタ ({{count}})」で**3文字長い**。
- 本番実機で文言だけ閲覧用に差し替えて測ると、種別の `clientWidth` は 13px → **38px**。
  いちばん短い「ポケモン」（52px）にも足りない＝**文言を揃えるだけでは直らない**。

## 3. 形の候補を本番実機で実測（CSS を差し替えて測定）

| 形 | 種別の文字 | 並び替えの文字 | 段数・高さ |
|---|---|---|---|
| いまの本番 | 13px ✗ | 全部出る | 2段 108px |
| 文言だけ閲覧用 | 38px ✗ | 全部出る | 2段 108px |
| 案1 種別も並び替えも縮む側 | 45px ✗ | 45px ✗ | 2段 108px |
| **案2 種別が1行を独り占め** | **全部出る** | **全部出る** | 3段 168px |
| 案3 種別を優先し並び替えが縮む | 全部出る | 32〜38px ✗ | 長い名前だと結局3段 |

案2 を当てたときの実測: ボタン幅 **312px**＝`.inventory-toolbar` の `clientWidth` と一致／
ラベルの `clientWidth` 52（中身なり）／名前に使える余地 **262px**／高さ **168px**。
`justify-content: flex-start` を足さないと名前の左端が **x=142.2**（中央寄せ）、足すと **x=37** で
下の行の「並び替え」のラベル（x=37）と揃う。

## 4. 既存の検査の棚卸し（ファイルを直接読んだ）

### 「名前が切れていないこと」を測る検査
- **在庫表には無い**。`frontend/src/pages/inventory/InventoryToolbar.css` のコメントが
  「長い種別名を … で切る」と書いており、切れること自体が仕様として通っていた。
- 閲覧ページには `frontend/tests-e2e/visual-language/viewer-control-tap-size.spec.ts` の
  B7a（切れていない）・B7c/B7d（壊すと切れる）がある。

### 段が増えると赤になるもの
- `frontend/tests-e2e/visual-language/inventory-series-sort-panel.spec.ts` の `MAX_TOOLBAR_HEIGHT = 120`（E11）
- `frontend/tests-e2e/visual-language/inventory-toolbar-mercari.spec.ts` の `MAX_TOOLBAR_HEIGHT = 120`（D10）
- `frontend/tests-e2e/visual-language/viewer-top-compact.spec.ts` の `MAX_TOP_Y = 132`（A1）と
  A2〜A4 の「シリーズ・並び替え・絞り込みの y が同じ」
- `frontend/tests-e2e/visual-language/viewer-choice-sheet.spec.ts` の `MAX_TOP_Y = 132`（B11）と B1〜B3 の同様の判定
- `frontend/tests-e2e/visual-language/viewer-header-remove.spec.ts` の `MAX_TOP_Y = 132`（C1）
- `frontend/tests-e2e/visual-language/viewer-control-tap-size.spec.ts` の B8（y が同じ）と
  B7c/B7d（**逆向きに**赤。直すと壊しても切れなくなるため）

### 触ってはいけないもの
- `frontend/tests-e2e/visual-language/inventory-helpers.ts` の種別 mock（3件）。
  1件足すと `inventory-series-sort-panel.spec.ts` の E5（`toHaveCount(4)`）が赤になり、
  `frontend/src/pages/inventory/InventoryPage.tsx` が PC に「その他」のプルダウンを足すので PC の DOM も変わる。

## 5. CI の持ち時間

`npx playwright test --list` を3つの project で数えて **789件**（変更前）。
画面検査は1ジョブ・10分で、`npm ci` と Playwright の導入を含む。
便1 の時点が655件・7.4分だったので 789件はおよそ 8.9分。**足せるのは20実行程度**。
