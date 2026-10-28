# recon: 絞り込みパネルの仕上げ（便13a）

> この文書は何か（1行）: 閲覧ページ（/viewer/）の絞り込みパネルを「お手本（メルカリ）と同じ寸法」に
> するにあたり、**いまのコードが何をどこで決めているか**を実ファイルから確かめた記録。すべて現物を読んで確認した。

調査日: 2026-10-28 / 土台: `origin/main` = `d10aff603`

## 1. お手本の実測（一次情報・既にリポジトリにある）

`docs/specs/design-system/visual-language/benchmark/mercari-search-filter.md` の §2・§3（2026-10-25 に実機の
`uiautomator dump` の `bounds` から機械集計したもの）。本便に関係する行をそのまま引く。

| 出どころ | 項目 | 実測 |
|---|---|---|
| §2 | パネルの左端 | x=180px ＝ 画面の左から **60dp** を残す |
| §2 | パネルの幅 | 900px = **300dp**（画面 360dp の 83%） |
| §3 | チェックボックスの行 | **幅 300dp（パネル全幅）× 高さ 68.7dp**。2段のとき 68.7dp／1段のとき **60.7dp** |
| §3 | 行の押せる範囲 | **行まるごと** |
| §3 | チェックボックスの左端 | 行の左から **48dp** の幅を占める（文字は x=48dp から始まる） |
| §3 | 主ラベル / 副ラベル | 17.7dp / 16.3dp |
| §3-1 | 選んだ合図 | **チェックの四角の中が塗られる1か所だけ**。行の背景は変えない |

**dp の読み方**（便10 で確立・`docs/handoff/viewer-control-tap-size/design.md`）: **高さ・幅は箱の実測なのでそのまま
px として使う**。**文字だけは「箱の高さ」なので行送り約1.2 で割る**＝17.7dp 箱 → 約14.8px ≒ `--font-base`（14.4px）。

## 2. いまの絞り込みパネル（現物）

| 何を | どこで決まっているか | いまの値 |
|---|---|---|
| スマホのパネル幅 | `frontend/src/components/Drawer.css:121-124`（`@media (max-width: 767px)` の中の `.comp-drawer-panel { width: 100% }`） | **画面いっぱい** |
| パネル本文の左右余白 | `frontend/src/components/Drawer.css:97-101`（`.comp-drawer-body { padding: var(--space-5) var(--space-6) }`） | 上下20px・左右24px |
| 選択画面のチェック行の高さ | `frontend/src/components/MultiSelect.css:42-45`（`.comp-multiselect__option--inline { min-height: var(--size-icon-btn-lg) }`） | **44px** |
| チェック行の余白 | `frontend/src/components/MultiSelect.css:28-36`（`.comp-multiselect__option { gap: var(--space-2); padding: var(--space-1) var(--space-2) }`） | 左右8px・印との間8px |
| チェック行の文字 | 同上（`font-size: var(--font-sm)`） | **13.6px** |
| チェックの四角 | `frontend/src/tokens.css:229`（`--size-checkbox: 16px`） | 16px |
| 選択画面の中身の組み立て | `frontend/src/pages/viewer/InventoryView.tsx:303-352`（`providerOptionsView` / `conditionOptionsView`） | 検索欄 ＋ `layout="inline"` の `MultiSelect` |
| 絞り込みドロワー | `frontend/src/pages/viewer/InventoryView.tsx:783-864` | `filterView` で root / provider / condition を出し分け |

**チェック行の DOM**（`frontend/src/components/MultiSelect.tsx:93-107`）: `<label class="comp-multiselect__option comp-multiselect__option--inline">`
の中に `CheckboxControl`（`frontend/src/components/CheckboxControl.tsx` ＝ 素の `<input type="checkbox">` 1つ）と
文字がそのまま並ぶ。**文字を包む要素が無い**ので、いまのままでは「印だけ48pxの枠に入れる」ができない。

**いまの文字の左端**: 行の padding 8px ＋ 印16px ＋ gap 8px = **行の左から32px**（お手本は48px）。

## 3. 他の `Drawer` への波及

`<Drawer` を使っているファイルは **35件**（`grep -rl "<Drawer" frontend/src --include=*.tsx` からテストと見本帳を除いた数）。
閲覧ページ自身も3枚使っている（`frontend/src/pages/viewer/InventoryView.tsx` の絞り込み・シリーズ/並び替え・検索）。
→ **幅を変える規則は、既定を1px も動かさない修飾クラスに閉じ込める**必要がある。

既存の幅の仕組み: `frontend/src/components/Drawer.css:48-50` の `.comp-drawer-panel--wide`（`size="wide"`）。
同じ形の修飾クラスをもう1つ足すのが社内の先例どおり。

## 4. これを壊すと CI が赤になる検査（現物で確認）

| spec | 行 | いま何を固定しているか | 本便との関係 |
|---|---|---|---|
| `frontend/tests-e2e/visual-language/viewer-inventory-mobile-filter.spec.ts` | 26-27 | `MIN_VISIBLE_OPTIONS = 8` / `MAX_VISIBLE_OPTIONS = 20` | **行が44→61pxになると8件見えなくなる＝必ず同時に更新する** |
| 同上 | 155-181 | A5: 選択画面の行が44px以上・`x >= 0` かつ `x + width <= 画面幅` | 61px・x=60・幅300 なので通る |
| `frontend/tests-e2e/visual-language/viewer-choice-sheet.spec.ts` | 306-331 | B10: **シリーズ/並び替えのパネルが全幅**（`Math.round(panelBox.width)` が画面幅と一致） | **絞り込みパネルだけ狭める**ので通る。ここを一緒に狭めると赤 |
| `frontend/tests-e2e/visual-language/viewer-filter-row-mercari.spec.ts` | 54-85 | B1: 項目の行 53px / B2・B3: 文字 14.4px | 項目の行（root）は触らないので通る |
| `frontend/tests-e2e/mobile-bp-token-g5.spec.ts` | 61-66 | 素の `.comp-drawer-panel` を注入して全幅を確かめる（修飾クラス無し） | 修飾クラスに閉じ込めるので通る |

### ★ 初版で見落としていたもの（独立審査の指摘で追記・2026-10-28）

上の表は「判定の中身」だけを見ていて、**spec が絞り込みドロワーを開くときの待ち方**を見落としていた。
viewer 系の5本は `openFilterDrawer` という同じ名前のヘルパーを**各ファイルに複製**して持ち、
いずれも「**パネルの左端 x が 0 になるまで待つ**」形になっている。

| ファイル | ヘルパーの位置 |
|---|---|
| `frontend/tests-e2e/visual-language/viewer-inventory-mobile-filter.spec.ts` | 36-49 |
| `frontend/tests-e2e/visual-language/viewer-filter-row-mercari.spec.ts` | 32-44 |
| `frontend/tests-e2e/visual-language/viewer-control-tap-size.spec.ts` | 56-70（同ファイル 78-86 の `waitPanelSlidIn` はシリーズ/並び替え用＝全幅のまま） |
| `frontend/tests-e2e/visual-language/viewer-header-remove.spec.ts` | 53-65 |
| `frontend/tests-e2e/visual-language/viewer-top-compact.spec.ts` | 59-71 |

原文（`frontend/tests-e2e/visual-language/viewer-inventory-mobile-filter.spec.ts`:41-47・5本とも同文）:

```
  // スライドインの途中で測ると x が 0 でない（画面外からアニメーション中）ため収まるまで待つ
  await expect
    .poll(async () => {
      const box = await panel.boundingBox();
      return box ? Math.round(box.x) : null;
    })
    .toBe(0);
```

**パネルを狭めると x は 61/66 になるので、この待ちは必ず時間切れになる**＝5本すべて赤。
手当ては design.md 4-7(1)。**教訓: 「判定の中身」だけでなく「前提を作る段取り（開き方・待ち方）」も数える。**

## 5. 社内に無いもの

- **横並びの選べるボタン（chip / segmented control）の金型は社内に存在しない**
  （`frontend/src/components/` を総当たりして該当なし）。便13b で新設するか、既存 `Button` の
  `variant` の切り替えで表すかを別便で決める。
- **60.7px / 68.7px に相当するトークンは無い**。近いのは `--comp-search-row-h: 69px`
  （`frontend/src/tokens.css:168`＝お手本68.7dp を便12a で整数に丸めた先例）。
