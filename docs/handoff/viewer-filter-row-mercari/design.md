# design: 絞り込みの項目の行をお手本に合わせる（便11）

> この文書は何か（1行）: 閲覧ページのスマホの絞り込み画面で、「提供者」「コンディション」の**項目の行**を
> お手本（メルカリ）と同じ高さ・同じ文字の大きさにし、**未選択のときの文字を「指定しない」**にする。

**recon**: docs/handoff/viewer-filter-row-mercari/recon.md
**土台**: `release/viewer-filter-row-mercari`（着手時の `origin/main` = f7bb004b7＝便10 を含む。
PR 作成前に `origin/main` = **0c23808ec** まで早送りして追従した）

## ① 区分：A（見た目と文言の変更）

押せる場所と押した結果は変えない。変えるのは**行の高さ・文字の大きさ・未選択のときの文字**だけ。

## ② KGI（PO が実機で○×を判定できる粒度）

PO 指示「検索欄とプルダウンをお手本（メルカリ）と全く同じ UI/UX にする」＋「完全にお手本通り」（2026-10-27）。
未選択の文言について**案B（PC も含めて「指定しない」に統一）を選択**（同日）。

| # | PO が見て○×を言えること |
|---|---|
| K1 | 絞り込み画面の「提供者」「コンディション」の行が**お手本と同じくらいの高さ**になった |
| K2 | その行の**文字が読みやすい大きさ**になった |
| K3 | 何も選んでいないとき、右側に「**指定しない**」と出る（以前は「すべて」） |
| K4 | 選んだあとは**選んだ名前がそのまま**出る（件数ではない。便10 以前から同じ） |
| K5 | PC の絞り込みでも「提供者: **指定しない**」と出る（案B の確認） |

## ③ KPI（機械で測る値）

| # | 値 | いま | この便の後 |
|---|---|---|---|
| P1 | 項目の行の高さ | 44px | **53px**（お手本 52.7dp） |
| P2 | 左のラベルの文字 | 13.6px | **14.4px**（お手本 17.7dp箱 ÷1.2 ≒14.8dp の最近傍） |
| P3 | 右の現在値の文字 | 13.6px | **14.4px** |
| P4 | 未選択のときの文字 | すべて | **指定しない** |
| P5 | 閲覧ページ JS | 260.9KB | 300KB 以下のまま |

## ④ 設計（How）

### 4-1. 行の高さ ― 新しいトークン1件（お手本の実測値をそのまま置く）

`frontend/src/tokens.css` に **MultiSelect 専用の節を新設**して追加する（独立審査の指摘4）。
`:548-559` の SubMenu 節のあと、`:561` の Status color 節の前に置く
（`:509-531` は DataTable 専用の節なので、そこへ混ぜると用途を取り違える）:

```
  /* ── MultiSelect コンポーネント ─────────────────────────────────────────── */
  /* layout="row" の行の高さ: お手本実測52.7dp。出典 docs/specs/design-system/visual-language/benchmark/ */
  --comp-multiselect-row-h:     53px;
```

**既存トークンで代替できないかを 48〜61px で総なめした**（PR 本文のチェックリストの根拠）:
48px は `--space-12`・`--field-h-tap`・`--icon-xl`・`--size-avatar-lg`・`--schedule-row-height`・`--comp-btn-height-lg`、
54px は `--height-tab-bar`、56px は `--topbar-height`・`--tabbar-height`・`--sidebar-sub-item-indent`・`--comp-table-row-h-relaxed`、
60px は `--size-split-label-min`・`--inbox-textarea-min-h`・`--schedule-time-gutter-width`・`--input-width-month`。
**53px もその近傍も無い**。最も近い 54px は誤差1.3pxかつ用途が受信箱のタブバーなので流用しない。

**先例をそのまま使う**: `frontend/src/tokens.css:276` の `--min-height-conv-item-mobile`（お手本実測76dp・
出典を同じ行のコメントに書く形）。52px 前後の既存トークンは用途が違うので流用しない（recon §6）。

`frontend/src/components/MultiSelect.css:77` の `min-height: var(--size-icon-btn-lg)` を
`min-height: var(--comp-multiselect-row-h)` に変える。

**実高が「53px ちょうど」になることの検算**（便10 で設計担当がここを踏んだので必ず書く）:
`line-height` は **1.6**（`frontend/src/index.css:426` の body から継承。`font: inherit` は line-height も継承する。
`--line-height-base` 1.5 ではない）。`box-sizing: border-box`（同 `:413-417` の `*`）。
中身の高さ = max(14.4×1.6, 山形18) = **23.04px**、固有の高さ = 23.04 ＋ 余白8×2 ＋ 下線1 = **40.04px** ≤ 53
→ **min-height が勝って実高は 53px**。変更前は 13.6×1.6 ＋ 17 = 38.76 ≤ 44 → **44px**（＝B1 は直す前は赤）。

### 4-2. 文字の大きさ ― 既存トークンに差し替えるだけ（新規0）

`frontend/src/components/MultiSelect.css:95`（左ラベル）と `:107`（右の現在値）の
`font-size: var(--font-sm)` を `var(--font-base)` に変える。

### 4-3. 未選択の文字 ― 辞書の値だけ変える（キーは増やさない）

`viewer.filter.all` の値を変える。**キーは増えない**ので ja/en のキー数は16のまま一致する。

| 辞書 | いま | この便の後 |
|---|---|---|
| `frontend/src/locales/viewer/ja.json` | すべて | **指定しない** |
| `frontend/src/locales/viewer/en.json` | All | **Unspecified** |

**英語は "Unspecified" にする**（独立審査の指摘3）。社内の既存訳は「未指定」＝**"Unspecified" が2件**
（`frontend/src/locales/en.json:2273`・`:2831`）、「未設定」＝"Not set" が2件（同 `:136`・`:4056`）で、
**"Not specified" は1件も無い**。同じ意味に3つ目の表記を作らない（ADR-027 の趣旨）。

**PO 決定（案B）で PC も変わる**。金型の中で画面に出るのは**3か所で、どれも「未選択」の意味**
（`frontend/src/components/MultiSelect.tsx:118` の row の現在値・同 `:142` の**選択画面の要約欄**・
同 `:151` の PC のボタン文字）＝意味が食い違う場所は無い（recon §4）。

**キー名は変えない**。`all` という名前と「指定しない」という値は一見ずれるが、
キー名を変えると6か所の呼び出しと金型のプロパティ名（`allLabel`）まで波及する。
**意味は「未選択のときに出す文字」で一貫している**ので、名前は据え置き、辞書にコメントは書けない（JSON）ため
本書 4-3 を根拠として残す。

### 4-3b. CSS のコメントに裸の PR 番号を書かない

`scripts/check-design-token-ratchet.sh:44-60` は `frontend/src/**/*.css` を対象にし（**`frontend/src/tokens.css` だけ除外**）、
同 `:29` が `(#123)` の形は消すが**裸の `#4819` は色コードとして数える**。本便は
`frontend/src/components/MultiSelect.css` を触るので、**出典や便番号のコメントは `frontend/src/tokens.css` 側に書く**
（除外対象）か、番号を括弧で囲む（独立審査の指摘8。便6 の `guard-hex-increase` と同じ罠）。

### 4-4. 触らないもの（この便の境界）

| 触らない | 理由 |
|---|---|
| 選択画面（チェックボックス一覧）の行 | 別のクラス（`frontend/src/components/MultiSelect.css:42-45`）。お手本は 60.7dp で、**パネル幅83%と一緒に**便12 で変える（一度に見える件数の基準が二度動くのを避ける） |
| 選択肢が少ない項目の横並び化 | 便12 |
| パネルの幅 | 便12 |
| 右端の「>」の大きさ | お手本に実測が無い（`docs/specs/design-system/visual-language/benchmark/mercari-search-filter.md` に記載なし）＝合わせる相手がいない |
| `viewer.tabAll`（シリーズのタブの「すべて」） | **別のキー**。シリーズの「すべて」は未選択ではなく「全シリーズ」の意味 |
| メディアクエリ | **不要**。`layout="row"` は `isMobile` の分岐の中だけ＝PC にこの要素は存在しない（recon §4） |

## ⑤ Acceptance Criteria

`B` は画面検査（本物の Chromium）。スマホは **360px と 390px の両方**、PC は 1280px。

| # | 基準 | 測り方 |
|---|---|---|
| B1 | 絞り込み画面の「提供者」「コンディション」の行の高さが **53px ちょうど** | 画面検査・2幅（**直す前は赤**＝44px） |
| B2 | その行の左ラベルの文字が **14.4px** | 画面検査・2幅（**直す前は赤**＝13.6px） |
| B3 | 同 右の現在値の文字が **14.4px** | 画面検査・2幅（**直す前は赤**＝13.6px） |
| B4 | 未選択のとき、右の現在値が「**指定しない**」 | 画面検査・2幅（**直す前は赤**＝「すべて」） |
| B5 | 1件選ぶと**その名前**が、2件選ぶと**カンマつなぎ**が出る（退行防止） | 画面検査・2幅（直す前も緑＝既存 A7・A9 と同趣旨。本便は文言変更が要約の組み立てを壊していないことの確認） |
| B5b | **選択画面の要約欄**（`.comp-multiselect__inline-summary`）が、未選択のとき「**指定しない**」・**1行のまま**（折り返していない） | 画面検査・2幅（**直す前は赤**＝「すべて」。独立審査の指摘2。既存 A7 が2件選択時に同じ要素を測っているので0件版を足す形） |
| B6 | **PC（1280px）の浮かぶプルダウンのボタンに「指定しない」が出る**（右端が画面内） | 画面検査（**直す前は赤**。案B の固定）。**spec 側で `gotoViewer(page, { width: 1280, height: 900 })` を明示する**＝3つの project すべてがこの spec を収集するため（`frontend/playwright.config.ts:63-75`）、幅を書かないと vl-mobile-390 の回で赤になる（独立審査の指摘7） |
| B7 | 一覧の先頭カードの y が **132px 以内のまま** | CI（既存3本の `MAX_TOP_Y`。便11 は絞り込み画面の中だけを変えるので動かないはず） |
| B8 | **既存 `frontend/tests-e2e/visual-language/viewer-inventory-mobile-filter.spec.ts` の A1（`:112-125`＝数量の下限欄の下端が画面内）と A4（`:145-153`＝コンディションの行が画面内）が緑のまま** | CI（**変更しない・確認のみ**。**行が2本で計18px 伸びるので、位置が動くのはこの2本**。初版は A5・A6（別画面）を挙げていた＝独立審査の指摘1で差し替え） |
| B8b | 同 A5・A6・A7・A9・A15（**選択画面**側）が緑のまま | CI（確認のみ。選択画面の行は別クラス `.comp-multiselect__option--inline` で本便は触らない） |
| B9 | 閲覧ページ JS が 300KB 以下 | CI（`frontend/scripts/check-viewer-bundle.js`） |

**空振り対策**: B1〜B4・B6 は直す前が赤なので空振りの余地が無い。
**唯一の「直す前も緑」は B5** なので、**要約の組み立てを壊した状態を spec の中で作らない**代わりに、
**1件・2件の両方を実際に選んで文字列を突き合わせる**（0件・1件・2件の3状態をすべて測る）。
0件が「指定しない」・1件が名前そのもの・2件がカンマつなぎ、の3つが同時に成り立つことは
`frontend/src/components/MultiSelect.tsx:82` の1行の全分岐を覆う。

**置き場**: `frontend/tests-e2e/visual-language/` の中に viewer-filter-row-mercari.spec.ts として置く
（`frontend/playwright.config.ts` の `testMatch` が `visual-language/` 配下に限るため、直下に置くと CI で1本も走らない）。
疑似応答は既存の `frontend/tests-e2e/visual-language/viewer-helpers.ts` の `gotoViewer` を使う。
**道順**: 絞り込みを開く → 行を測る（`viewer-provider-row`・`viewer-condition-row`）。
選ぶときは行を押して選択画面へ入り、選んで **`drawer-back`（←）で戻る**（既存 `frontend/tests-e2e/visual-language/viewer-inventory-mobile-filter.spec.ts` の A2・A7 と同じ形。
選択は押した瞬間に `onChange` で親の state に入るので、「決定する」でも ← でも結果は同じ＝`frontend/src/pages/viewer/InventoryView.tsx:329-336` の `viewer-filter-apply` も `backToFilterRoot()` を呼ぶだけ）。

## ⑥ 触るファイル

| ファイル | 変更 |
|---|---|
| `frontend/src/tokens.css` | `--comp-multiselect-row-h: 53px` を1件追加 |
| `frontend/src/components/MultiSelect.css` | 行の `min-height` を新トークンへ・左ラベルと右の現在値の `font-size` を `--font-base` へ（3行） |
| `frontend/src/locales/viewer/ja.json` | `viewer.filter.all` の値を「指定しない」へ |
| `frontend/src/locales/viewer/en.json` | 同 "Unspecified" へ（4-3 のとおり。社内の既存訳に合わせる） |
| frontend/tests-e2e/visual-language/viewer-filter-row-mercari.spec.ts | 新規（B1〜B6）。この便で作るのでパスの囲みを付けない |
| `docs/handoff/viewer-filter-row-mercari/recon.md` | 新規 |
| `docs/handoff/viewer-filter-row-mercari/design.md` | 新規（本書） |
| `docs/handoff/viewer-filter-row-mercari/review-opus.md` | 新規（実装後・PR 前の独立審査の記録） |

**既存行を削るファイル**（書き換えを含む）: `frontend/src/components/MultiSelect.css`・
`frontend/src/locales/viewer/ja.json`・`frontend/src/locales/viewer/en.json`。

## ⑦ 戻し方

1コミットなので `git revert` 1回。新トークンは追加だけなので、戻しても参照が消えるだけ。

## ⑧ 削除するファイル

無し。

## ⑨ 外部・過去事例の参照と我々への応用

- **お手本（一次情報）**: `docs/specs/design-system/visual-language/benchmark/mercari-search-filter.md:59-67`。
  行 52.7dp・文字17.7dp（箱）・未選択「指定しない」・選択後は名前のカンマつなぎ。
- **社内の先例（そのまま使う）**: `frontend/src/tokens.css:276` の `--min-height-conv-item-mobile`
  ＝**お手本の実測 dp を px の値にし、出典を同じ行のコメントに書く**形。便11 はこれに合わせる。
- **社内の先例（便10 で確立した読み替え規則）**: 同書の「文字○dp」は**文字の箱の高さ**で、
  実体は約1.2で割る。17.7 ÷ 1.2 ≒ 14.8dp → `--font-base` 14.4px。
  この規則が無いと 17.7px（存在しない大きさ）を作ろうとして誤る。
- **WCAG 2.5.5（Target Size）**: 下限44px。44→53px は上回る方向。

## ⑩ 弊害・トレードオフ

- **絞り込み画面（root）の中身が 18px 高くなる**（2行 × 9px）。**収まる余裕を先に計算した**（独立審査の指摘1）:
  帯81（20＋44＋16＋1）＋上余白20＋24時間44＋隙間16×4＋提供者44＋コンディション44＋価格65.2＋数量65.2
  = **427.4px**。検査の画面高は 700px（`frontend/tests-e2e/visual-language/viewer-inventory-mobile-filter.spec.ts:110`）
  ＝**余裕 272.6px**。18px 増えても 445.4px なので A1・A4 は赤にならない。B8 で機械確認する。
- **アプリの在庫表は「すべて」のまま残る**（別キー＝`frontend/src/pages/inventory/InventoryFilterPanel.tsx:126`・`:141`、
  `frontend/src/pages/inventory/InventoryToolbar.tsx:165`・`:175`）。**同じ操作の文言が製品内で2通りになる**が、
  横展開（⑫ H3）までの既知の不一致。PO が K5 を見るときの混乱を避けるため明記する（独立審査の助言5）。
- **同じドロワーの中で文字の大きさが混ざる**。項目の行は 14.4px になるが、**選択画面の行は 13.6px のまま**
  （`frontend/src/components/MultiSelect.css:28-36`）＝便12 でそろえる。K2 を見るときの前提（独立審査の助言6）。
- **新規トークン1件**（`--comp-multiselect-row-h`）。PR 本文のチェックリスト4項目が必要。
- **「指定しない」は PC にも出る**（PO 決定の案B）。PC の浮かぶプルダウンのボタン文字が
  「提供者: すべて」→「提供者: 指定しない」になる。**文字数が増えるのでボタンが広がる**
  （PC は幅に余裕があるが、B6 で右端が画面内に収まることも一緒に測る）。
- **キー名 `all` と値「指定しない」がずれる**。キー名を変えると6か所＋金型のプロパティ名に波及するため据え置いた（4-3）。

## ⑪ 維持の仕組み

守り手:
- 新設する画面検査 viewer-filter-row-mercari.spec.ts（`frontend/tests-e2e/visual-language/` 配下。CI の画面検査で毎 PR）
  — 行の高さ・2か所の文字・未選択の文言・0件/1件/2件の3状態・PC の文言を機械で固定する。
- 既存 `frontend/tests-e2e/visual-language/viewer-inventory-mobile-filter.spec.ts`（A5〜A15）— 選択画面側の退行を見る。
- `frontend/scripts/check-new-tokens.js`（CI）— トークン追加の理由を PR 本文に残させる。
  **`check:new-tokens` は `frontend/package.json` の `check:all` に含まれていない**＝手元では空振りするので、
  PR 作成後の CI が初出になる（独立審査が指摘）。**4項目すべてを `[x]` にする**（本文に在る行が `[ ]` だと赤。
  色に関する項目も、本件が色トークンでなくてもチェックを付ける）。

  **実際に踏んだ罠（PR #4821 の1回目・CI の一次情報）**: この関所は4つの語
  （`新しいトークンを追加した場合、その` / `色トークンは` / `check:dark-parity` / `既存トークンで代替できないか確認`）
  について **本文の中で最初に現れた1行だけ**を見て `- [x]` かを判定する（同スクリプト `:112-117` の
  `lines.find(line => line.includes(item))`）。説明文に「…色トークンは0件。」と書いていたため、
  **チェック欄は `[x]` でも「未チェック」と誤認して fail した**。
  → **4つの語をチェックリスト以外の場所で一度も書かない**（言い換える）。
  さらに **`gh run rerun --failed` では直らない**: 本文は `PR_BODY: ${{ github.event.pull_request.body }}`
  （`.github/workflows/frontend-check.yml:58`）＝**起動時のイベントに凍結された本文**を読むため、
  本文を直したら**新しいコミットを push して `synchronize` を起こす**必要がある。
- `frontend/scripts/check-i18n-missing-keys.js:101-113`（`check:all`）— **辞書のキー集合の一致を見る関所はここ**。
  本便は値のみ変更なので緑（キーは16のまま）。

## ⑫ 継続（この便の後）

| # | 内容 |
|---|---|
| H1 | **便12＝選択肢の出し方をお手本の2通りに**。①選択肢が少ない項目（2〜6件）はその場に横並びボタン（48dp・間隔8dp・折り返す）②チェックボックス一覧の行を **60.7dp（1段）/68.7dp（2段）**・印が行の左48dpを占める形へ ③**パネル幅を画面の83%（左に60dp残す）**へ。**既存の「一度に8〜20件見える」の基準は必ず同時に更新する**（行が44→60.7pxで見える件数が約3割減る。PO 決定「完全にお手本通り」で承知済み） |
| H2 | **G1（便10 から持ち越し）シリーズ名の幅の優先順**。並び替えに最長の項目を選ぶと 360px で約19px 足りない。**PO 判断が必要** |
| H3 | **アプリの在庫表への横展開**（`frontend/src/pages/inventory/InventoryPage.tsx` と `InventoryToolbar`）。便10 の `tap`・`field-h-tap` と便11・便12 の寸法がそのまま使える |
| H4 | **お手本の一覧（商品カード）側は未実測**。D2② に進むなら撮影・実測が先（実機の ADB は現在未接続） |
| H5 | 便6〜便8 の持ち越し: **C-up**・**C-out**・**C-sb**・**C-perf**・**C-tap**／**E1**・**E2**・**E3**・**E5**・**E6**（調査済み）・**E7**／**F5**・**F6**・**F7**・**F8** |
| H6 | **`frontend/src/pages/super-admin/ViewerTemplatesPage.test.tsx` の非同期の後始末**（便10 の CI で `ReferenceError: window is not defined` の未処理エラーとして一度出た。全件合格でも終了コード1になる。放置するとどの PR でも一定割合で赤が出る） |

## 対象 ADR

- **ADR-144**（UI 共通部品の遵守ガバナンス）: 既存金型の寸法を正本のトークン経由で変えるだけ。金型新設ではない。
- **ADR-067**（デザイントークン強制）: 直値を書かず、追加する `--comp-multiselect-row-h` と既存 `--font-base` を参照する。
- **ADR-140**（タップ領域の下限 44px）: 44→53px は下限を上回る方向。
- **ADR-027**（i18n 強制）: 文言は**キーを増やさず値だけ変える**。ja/en のキー数16は変わらない。
- **ADR-1019**（閲覧ページはアプリと別コード）: 本便はアプリ側に触らない。ただし `MultiSelect` は共通金型で、
  `layout="row"` の実装利用が閲覧ページの2か所だけであることを recon §4 で確認済み。
