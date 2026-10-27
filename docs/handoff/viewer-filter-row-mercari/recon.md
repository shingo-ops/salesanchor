# recon: 絞り込みの項目の行をお手本に合わせる（便11）

> この文書は何か（1行）: 閲覧ページのスマホの絞り込み画面で、「提供者」「コンディション」の**項目の行**を
> お手本（メルカリ）と同じ寸法・同じ文言にするための現物調査。

**土台**: `release/viewer-filter-row-mercari`（`origin/main` = f7bb004b7＝便10 を含む）／調査日 2026-10-27
**対象**: 閲覧ページ `frontend/src/pages/viewer/InventoryView.tsx`（アプリの `frontend/src/pages/inventory/InventoryPage.tsx` とは別コード。ADR-1019）

## 1. お手本（正本からの引用）

`docs/specs/design-system/visual-language/benchmark/mercari-search-filter.md:59-67`（2-1 次の画面へ進む行）:

| 項目 | お手本の実測 |
|---|---|
| 行の高さ | **52.7dp** |
| 左のラベル | 文字 **17.7dp**（箱の高さ） |
| 右の現在値 | 文字 **17.7dp**（箱の高さ）・**右寄せ** |
| 未選択のときの文字 | **「指定しない」** |
| 選択後の文字 | **選んだ名前をカンマでつないで出す**（実測値「IRWIN, AEG」）。件数ではない |

**文字の読み替え**（便10 で確立した規則。同書の「文字○dp」は Android の文字の箱の高さで、
実体は約1.2で割った値。便10 の recon §1）: **17.7 ÷ 1.2 ≒ 14.8dp** →
最も近い既存トークンは `--font-base`（`frontend/src/tokens.css:16` = 0.9rem = **14.4px**）。

## 2. すでにお手本と一致している（直す必要が無い）

| 観点 | 現物 |
|---|---|
| 選択後に**名前をカンマでつないで**出す | `frontend/src/components/MultiSelect.tsx:82`（`selected.map(resolveLabel).join(", ")`）。**件数（`countLabel`）を使うのは PC の浮かぶプルダウンだけ**（同 `:151-155`・2件以上のとき） |
| 行の右端の「>」 | 同 `:119`（`ChevronRight size={18}`） |
| 現在値が右寄せ | `frontend/src/components/MultiSelect.css:100-110`（`text-align: right`） |
| 行まるごと押せる | 同 `:73-87`（`<button>` が行全体） |

**＝便11 で直すのは「未選択の文字」と「行の寸法」の2つだけ**。

## 3. 直す対象の現物

| 何 | 決めている行 | いま | お手本 |
|---|---|---|---|
| 行の高さ | `frontend/src/components/MultiSelect.css:77`（`min-height: var(--size-icon-btn-lg)`） | `frontend/src/tokens.css:163` = **44px** | 52.7dp |
| 左ラベルの文字 | 同 `:93-98`（`font-size: var(--font-sm)`） | `frontend/src/tokens.css:15` = **13.6px** | 約14.8dp |
| 右の現在値の文字 | 同 `:100-110`（`font-size: var(--font-sm)`） | 同 = **13.6px** | 約14.8dp |
| 未選択の文字 | `frontend/src/locales/viewer/ja.json` の `viewer.filter.all` | **「すべて」** | 「指定しない」 |

## 4. 波及範囲（**狭い。メディアクエリも不要**）

`layout="row"` を**実装で使っているのは `frontend/src/pages/viewer/InventoryView.tsx:233`・`:248` の2か所だけ**
（他は `frontend/src/components/MultiSelect.test.tsx`・`frontend/src/components/MultiSelect.stories.tsx`）。
しかもその2か所は `isMobile` の分岐の中にあるので、**`.comp-multiselect__row` の要素は PC には存在しない**
＝スマホ限定のメディアクエリを書く必要が無い（便10 の `field-h-tap` とは事情が違う）。

`viewer.filter.all` の使用は `frontend/src/pages/viewer/InventoryView.tsx` の **6か所すべて**が
`MultiSelect` の `allLabel`（`:210`・`:223`・`:240`・`:255`・`:283`・`:310`）。
金型の中で画面に出るのは**3か所で、どれも「未選択」の意味**（独立審査の指摘2で「2つ」から訂正）:
`frontend/src/components/MultiSelect.tsx:118`（row の現在値）・同 `:142`（**`layout="inline"`＝選択画面の要約欄**）・
同 `:151`（PC の浮かぶプルダウンのボタン文字）。前2つは同 `:82` の `selectedSummary` 経由。
**＝文言を変えても意味が食い違う場所は無い**。ただし**選択画面の要約欄にも「指定しない」が出る**ので、そこも測る。

**PO 決定（2026-10-27）**: 「未選択の文字は PC も含めて『指定しない』に統一する」（案A＝スマホだけ／案B＝PC も、から**案B**を選択）。

## 5. いまある歯止め

| ファイル | 記号 | 何を測っているか | 便11 での扱い |
|---|---|---|---|
| `frontend/tests-e2e/visual-language/viewer-inventory-mobile-filter.spec.ts:183-210` | A7・A9 | 2件選ぶと項目の行に**名前がカンマつなぎ**で出る | **緑のまま**（すでにお手本の形） |
| 同 `:155-180` | A5・A6・A15 | **選択画面**の行が44px以上・一度に8〜20件見える | **無影響**。選択画面の行は別のクラス（`frontend/src/components/MultiSelect.css:42-45` の `.comp-multiselect__option--inline`）で、便11 は触らない |
| `frontend/src/components/MultiSelect.test.tsx:123` | — | 0件のとき `allLabel` が出る／1件以上はカンマつなぎ | **緑のまま**（テストは自前の `allLabel="All"` を渡すので辞書に依存しない） |

**無いもの**: 項目の行の**高さ**を測る検査／**文字の大きさ**を測る検査／**未選択の文言**を測る検査。

## 6. 新しいトークンの先例（そのまま使える型）

`frontend/src/tokens.css:276` に**同じ事情の先例**がある:

```
--min-height-conv-item-mobile: 76px;   /* 会話アイテム最小高（スマホ）: お手本実測76dp。PCは上の92pxのまま。出典 docs/specs/design-system/visual-language/benchmark/ */
```

＝**お手本の実測 dp をそのまま px の値にし、出典を同じ行のコメントに書く**。便11 もこの型に合わせる。
52px 前後の既存トークンは `--height-tab-bar` 54px・`--comp-table-row-h-relaxed` 56px しかなく、
どちらも用途が違う（受信箱のタブバー／表の行）ので**流用しない**。

## 7. 辞書

`frontend/src/locales/viewer/ja.json` と `frontend/src/locales/viewer/en.json` は
`filter` の下が**両方16キーで一致**。「指定しない」に相当するキーは**存在しない**
（`viewer.filter.all` を使い回す＝キーは増えない）。

**取り違え注意**: `viewer.tabAll`（シリーズのタブの「すべて」）は**別のキー**で、便11 では触らない。

## 関連
- 便10 `docs/handoff/viewer-control-tap-size/recon.md`（お手本の文字の読み替え規則の出所）
- 設計は docs/handoff/viewer-filter-row-mercari/design.md
